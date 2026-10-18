"""
harness — the run log, hook and transcript helpers that test_runs and test_waits share.

Each test builds a `Log` in one temporary folder and sends runs.py hook events and commands against
it with ROBOVAC_RUNS pointing there; `check` records each result, and `main` runs a list of cases
and returns the number that failed. `events` lists the rows that move the robot and the asks, and
`work` how the session's turn and background tasks stand at each row that says so: a start, which
opens the turn with the tasks it carries, and a work row.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path



HERE    = Path(__file__).resolve().parent
SCRIPT  = HERE.parent / 'scripts' / 'runs.py'
ESC     = '[Request interrupted by user]'
RESULTS = []


def check(name: str, ok: bool, detail: str = '') -> None:
    RESULTS.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f'  ({detail})' if not ok and detail else ''))


class Log:
    """one run log, and the hook events and commands sent against it."""

    def __init__(self, tmp: Path, name: str):
        self.dir = tmp / name
        self.dir.mkdir()
        self.path = self.dir / 'runs.jsonl'
        self.env  = {**os.environ, 'ROBOVAC_RUNS': str(self.path)}

    def run(self, *args: str, stdin: str = '', sid: str = '') -> str:
        env = dict(self.env, CLAUDE_CODE_SESSION_ID=sid) if sid else self.env
        return subprocess.run([sys.executable, str(SCRIPT), *args], input=stdin, env=env,
                              capture_output=True, text=True).stdout

    def hook(self, event: str, sid: str = 'a', **fields) -> None:
        payload = dict(hook_event_name=event, session_id=sid, cwd=str(self.dir), **fields)
        self.run('hook', stdin=json.dumps(payload))

    def rows(self, sid: str = 'a') -> list[dict]:
        if not self.path.exists():
            return []
        return [r for r in map(json.loads, self.path.read_text().splitlines()) if r['session'] == sid]

    def events(self, sid: str = 'a') -> list[str]:
        return [r['event'] + (f":{r['why']}" if r.get('why') else '') for r in self.rows(sid)
                if r['event'] != 'work']

    def work(self, sid: str = 'a') -> list[tuple]:
        return [(r.get('turn', True), sorted((r.get('tasks') or {}).items())) for r in self.rows(sid)
                if r['event'] in ('start', 'work')]


def transcript(path: Path, *lines: dict) -> Path:
    """a transcript holding these lines, appended to whatever it already has."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as f:
        for line in lines:
            f.write(json.dumps(line) + '\n')
    return path


def said(text: str) -> dict:
    return {'type': 'user', 'message': {'role': 'user', 'content': [{'type': 'text', 'text': text}]}}


def iso(t: float) -> str:
    """a time as Claude Code stamps a transcript line, to the millisecond."""
    return time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(t)) + f'.{int(t * 1000) % 1000:03d}Z'


def reply(text: str, at: float, stop: str = 'end_turn') -> dict:
    """the agent's reply as its transcript line, stamped `at`, with how its message stopped."""
    return {'type': 'assistant', 'timestamp': iso(at), 'message': {
        'role': 'assistant', 'stop_reason': stop, 'content': [{'type': 'text', 'text': text}]}}


def call(tool: str, at: float) -> dict:
    """the agent's tool call as its transcript line, stamped `at`."""
    return {'type': 'assistant', 'timestamp': iso(at), 'message': {
        'role': 'assistant', 'stop_reason': 'tool_use',
        'content': [{'type': 'tool_use', 'id': 't1', 'name': tool, 'input': {}}]}}


def notice(task: str, status: str = 'completed') -> str:
    """the prompt Claude Code submits when a background task ends, as the probes recorded it."""
    return (f'<task-notification>\n<task-id>{task}</task-id>\n<tool-use-id>toolu_1</tool-use-id>\n'
            f'<output-file>/tmp/{task}.output</output-file>\n<status>{status}</status>\n'
            f'<summary>Background command finished</summary>\n</task-notification>')


def running(*tasks: tuple) -> list[dict]:
    """a Stop hook's background_tasks: each (id, type) still running."""
    return [{'id': i, 'type': kind, 'status': 'running', 'description': i} for i, kind in tasks]


def tool_result(text: str) -> dict:
    return {'type': 'user', 'message': {'role': 'user', 'content': [
        {'type': 'tool_result', 'tool_use_id': 't1', 'content': text}]}}


def main(cases: tuple) -> int:
    """run each case in one temporary folder, print the tally, and return how many checks failed."""
    with tempfile.TemporaryDirectory() as t:
        for case in cases:
            case(Path(t))
    failed = RESULTS.count(False)
    print(f'{len(RESULTS) - failed}/{len(RESULTS)} passed')
    return failed
