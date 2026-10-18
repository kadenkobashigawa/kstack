'''
host — a Claude Code session driven the way the Claude desktop app hosts one: stream-json in and
out, and each permission request, question and MCP form sent back to the host over stdio, which
answers it after the hold a scenario gives, as the person's click arrives from the app's own prompt.

Methods
-------
    permission :
        the answer to one permission request, a question's included.
    form :
        the answer to one MCP form.
    Host :
        one session, its output read on a thread, its prompts sent and its requests answered.
'''

from __future__ import annotations

import json
import queue
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Callable



#the flags the desktop app starts Claude Code with, as `ps` shows them, less its model and resume...
DESKTOP = ('--output-format', 'stream-json', '--input-format', 'stream-json', '--verbose',
           '--permission-prompt-tool', 'stdio')

#what a form's field is filled with, by its type, when it offers no choices...
FILLED = {'string': 'yes', 'number': 1, 'integer': 1, 'boolean': True}


def permission(req: dict, step: dict) -> dict:
    '''
    the answer to one permission request: allow with its input, or deny, with Esc when `interrupt`.

    Notes
    -----
    a question (AskUserQuestion) allowed answers each of its questions with its first option, as a
    person's click on it, under the input's `answers`, the shape its PostToolUse carried when the
    desktop host mode was probed on 2026-10-18.
    '''
    if step['behavior'] != 'allow':
        return {'behavior': 'deny', 'message': 'The user rejected this.',
                'interrupt': step.get('interrupt', False)}
    given = dict(req.get('input') or {})
    if req.get('tool_name') == 'AskUserQuestion':
        given['answers'] = {q.get('question'): (q.get('options') or [{}])[0].get('label')
                            for q in given.get('questions', [])}
    return {'behavior': 'allow', 'updatedInput': given}


def form(req: dict, step: dict) -> dict:
    '''the answer to one MCP form: accepted with each field filled by its type, or declined.'''
    if step['behavior'] != 'allow':
        return {'action': 'decline'}
    fields = (req.get('requested_schema') or {}).get('properties') or {}
    return {'action': 'accept', 'content': {
        k: f['enum'][0] if f.get('enum') else FILLED.get(f.get('type'), 'yes')
        for k, f in fields.items()}}


#each request the host answers, by its control request's subtype...
REPLIES = {'can_use_tool': permission, 'elicitation': form}


class Host:
    '''one session in the desktop host mode: its prompts sent and its requests answered.'''

    def __init__(self, binary: str, flags: list, cwd: Path, env: dict, stream: Path,
                 mark: Callable[[str], None]):
        self.argv   = [binary, *DESKTOP, *map(str, flags)]
        self.cwd    = cwd
        self.env    = env
        self.stream = stream
        self.mark   = mark
        self.q      = queue.Queue()
        self.proc   = None

    def start(self) -> int:
        '''start the session, read its output on a thread, and initialize it as the app does.'''
        self.proc = subprocess.Popen(self.argv, cwd=self.cwd, env=self.env, text=True, bufsize=1,
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=open(self.stream.with_name('stderr.txt'), 'w'))
        threading.Thread(target=self.read, args=(open(self.stream, 'w'),), daemon=True).start()
        self.send({'type': 'control_request', 'request_id': 'init',
                   'request': {'subtype': 'initialize'}})
        return self.proc.pid

    def read(self, stream) -> None:
        '''copy the output to the stream file, less the account it opens with, and queue it.'''
        for line in self.proc.stdout:
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            if msg.get('response', {}).get('request_id') != 'init':
                stream.write(line)
                stream.flush()
            self.q.put(msg)

    def send(self, obj: dict) -> None:
        try:
            self.proc.stdin.write(json.dumps(obj) + '\n')
            self.proc.stdin.flush()
        except (BrokenPipeError, ValueError):
            self.mark(f"could not send {obj.get('type')}: the session has gone")

    def esc(self) -> None:
        '''interrupt the turn, as the app does when the person presses Esc or its stop button.'''
        self.mark('interrupt sent, as the app sends Esc')
        self.send({'type': 'control_request', 'request_id': f'esc-{uuid.uuid4().hex[:6]}',
                   'request': {'subtype': 'interrupt'}})

    def answer(self, msg: dict, plan: list) -> None:
        '''answer one permission request or form after its planned hold, as `REPLIES` says.'''
        req  = msg['request']
        step = plan.pop(0) if plan else {'hold': 0, 'behavior': 'allow'}
        if req['subtype'] == 'elicitation':
            self.mark(f"asked: form server={req.get('mcp_server_name')} "
                      f"{json.dumps(req.get('message'))[:70]}")
        else:
            self.mark(f"asked: {req.get('tool_name')} agent={req.get('agent_id') or 'main'} "
                      f"{json.dumps(req.get('input'))[:70]}")
        time.sleep(step['hold'])
        reply = REPLIES[req['subtype']](req, step)
        self.send({'type': 'control_response', 'response': {
            'subtype': 'success', 'request_id': msg['request_id'], 'response': reply}})
        esc = ' with interrupt' if step.get('interrupt') else ''
        self.mark(f"answered: {step['behavior']}{esc} after {step['hold']} s")

    def turn(self, prompt: str, plan: list, want: int, timeout: float,
             on: Callable[[str], None]) -> int:
        '''
        send one prompt and answer the session until `want` results arrive or `timeout` passes.

        Parameters
        ----------
        prompt : str
            what the person types.
        plan : list of dict
            the answers to give, one per permission request or form in the order they come:
            `hold` seconds, `behavior` allow or deny, and `interrupt` for a denial made with Esc;
            a request past the plan is allowed at once.
        want : int
            how many results end the turn: one, or more where a background agent reports later.
        timeout : float
            seconds before the turn is given up as timed out.
        on : callable
            told 'ask' before each answer's hold, 'answer' after it, and 'result' at each result.

        Returns
        -------
        int
            the results that arrived.
        '''
        got = 0
        self.mark(f'prompt: {prompt[:90]}')
        self.send({'type': 'user', 'message': {'role': 'user', 'content': prompt},
                   'parent_tool_use_id': None, 'session_id': ''})
        deadline = time.time() + timeout
        while time.time() < deadline and got < want:
            try:
                msg = self.q.get(timeout=0.5)
            except queue.Empty:
                continue
            kind = (msg.get('request', {}).get('subtype')
                    if msg.get('type') == 'control_request' else None)
            if kind in REPLIES:
                on('ask')
                self.answer(msg, plan)
                on('answer')
            elif kind:
                self.mark(f'control request {kind} answered as unsupported')
                self.send({'type': 'control_response', 'response': {
                    'subtype': 'error', 'request_id': msg['request_id'],
                    'error': 'the verify host does not handle this request'}})
            elif msg.get('type') == 'result':
                got += 1
                self.mark(f"result: {msg.get('subtype')} {str(msg.get('result') or '')[:60]!r}")
                on('result')
        if got < want:
            self.mark(f'turn timed out after {timeout} s')
        return got

    def close(self) -> None:
        '''close the session's input, as the app does when its session closes, and wait for it.'''
        self.proc.stdin.close()
        try:
            self.proc.wait(timeout=60)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        self.mark('session closed by the host')
