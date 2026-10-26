'''
session — a scenario driven against one side: the scenario file checked, the session's settings from
the revision's hooks, the film and the stills, and the clock the drive leaves behind.

Methods
-------
    fill :
        a scenario's text with its placeholders filled.
    load_scenario :
        a scenario file, checked.
    hook_settings :
        the drive session's settings, from the exported tree's hooks.json.
    Drive :
        one scenario driven against one side.
    described :
        one log row as the clock and the diff print it.
    clock :
        the side's clock: driver marks, hooks and log rows on one time line.
'''

from __future__ import annotations

import json
import signal
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

import common
import testcopy
from host import Host



FILM     = '/usr/sbin/screencapture'
OBSERVED = ('UserPromptSubmit', 'PreToolUse', 'PostToolUse', 'PostToolUseFailure', 'PostToolBatch',
            'PermissionRequest', 'Elicitation', 'ElicitationResult', 'Notification', 'Stop',
            'StopFailure', 'SubagentStart', 'SubagentStop', 'SessionEnd')
ANCHORS  = ('prompt', 'ask', 'answer', 'result')


# ── the scenario and the session's settings ───────────────────────────────────

def fill(text: str, values: dict) -> str:
    '''a scenario's text with each {name} that `values` holds replaced by its value.'''
    for name, value in values.items():
        text = text.replace('{' + name + '}', value)
    return text


def load_scenario(path: Path) -> dict:
    '''
    a scenario file, checked.

    Parameters
    ----------
    path : Path
        a JSON file: `steps`, each a prompt (with optional `answers`, `shots`, `interrupt`, `open`,
        `results` and `timeout`) or a `pause` in seconds; optional `files` to put in the session's
        folder first, `hooks` to add to the drive's settings, and `form`, true for a session with
        form.py's MCP server, whose one tool opens a form.

    Returns
    -------
    dict
        the scenario as written.

    Raises
    ------
    SystemExit
        naming every problem: no steps, an unknown step or answer, an anchor not in ANCHORS, or a
        still name used twice or not lowercase kebab-case.
    '''
    scenario, problems, names = json.loads(path.read_text()), [], set()
    for n, step in enumerate(scenario.get('steps', []), 1):
        if 'pause' in step:
            continue
        if 'prompt' not in step:
            problems.append(f'step {n} is neither a prompt nor a pause')
            continue
        for answer in step.get('answers', []):
            if answer.get('behavior') not in ('allow', 'deny') or answer.get('hold', 0) < 0:
                problems.append(f'step {n} has an answer not allow or deny, held 0 s or more')
        for anchor, secs, name in step.get('shots', []):
            if anchor not in ANCHORS or secs < 0:
                problems.append(f'step {n} shot {name} is anchored to {anchor}, not {ANCHORS}')
            if name in names:
                problems.append(f'shot {name} is used twice')
            if not common.NAME.match(name):
                problems.append(f'shot {name} is not lowercase kebab-case')
            names.add(name)
        for action in ('interrupt', 'open'):
            if step.get(action) and step[action][0] not in ANCHORS:
                problems.append(f'step {n} {action} is anchored to {step[action][0]}, '
                                f'not {ANCHORS}')
    if not scenario.get('steps'):
        problems.append('no steps')
    if problems:
        raise SystemExit(f'verify: {path.name}: ' + '; '.join(problems))
    return scenario


def hook_settings(tree: Path, extra: dict, values: dict) -> dict:
    '''
    the drive session's settings, from the exported tree's hooks.json.

    Parameters
    ----------
    tree : Path
        the exported tree, whose hooks.json and runs.py the session runs.
    extra : dict
        a scenario's own hooks, by event, added after the tree's, with their placeholders filled.
    values : dict
        what a scenario's placeholders stand for.

    Returns
    -------
    dict
        settings whose hooks are the tree's robovac hooks with runs.py pointed at the tree, less
        SessionStart (an older revision's, not robovac's, which would run the person's own
        setup), plus the observer on every event the clock reads, logging to the VERIFY_HOOKS the
        session's environment names.

    Raises
    ------
    SystemExit
        when a hook of the tree's would still run anything under ~/.claude, the person's own setup,
        or still names a plugin root no drive fills in.
    '''
    runs  = tree / 'skills' / 'robovac' / 'scripts' / 'runs.py'
    hooks = json.loads((tree / 'hooks' / 'hooks.json').read_text())['hooks']
    hooks.pop('SessionStart', None)
    for entries in hooks.values():
        for h in (h for entry in entries for h in entry['hooks']):
            #the plugin form hooks.json has used since kstack became a plugin, and the linked form
            #before it, so a baseline from an older revision drives too...
            for form in ('${CLAUDE_PLUGIN_ROOT}/skills/robovac/scripts/runs.py',
                         '$HOME/.claude/skills/robovac/scripts/runs.py'):
                h['command'] = h['command'].replace(form, str(runs))
            if '.claude/' in h['command'].replace(str(tree), ''):
                raise SystemExit(f"verify: a hook would run the person's own setup: {h['command']}")
            if 'CLAUDE_PLUGIN_ROOT' in h['command']:
                raise SystemExit(f"verify: a hook names a plugin path the drive can't fill in: {h['command']}")
    observer = f'{sys.executable} {common.VERIFY} observe'
    for event in OBSERVED:
        hooks.setdefault(event, []).append(
            {'hooks': [{'type': 'command', 'command': observer, 'timeout': 5}]})
    for event, entries in extra.items():
        for h in (h for entry in entries for h in entry['hooks']):
            h['command'] = fill(h['command'], values)
        hooks.setdefault(event, []).extend(entries)
    return {'hooks': hooks}


# ── the drive ─────────────────────────────────────────────────────────────────

class Drive:
    '''one scenario driven against one side: its session, the film and the stills.'''

    def __init__(self, claim: Path, side: str, scenario: dict):
        self.claim, self.side, self.scenario = claim, side, scenario
        self.setup  = json.loads((claim / side / 'setup.json').read_text())
        self.out    = claim / side
        self.place  = common.scratch(claim) / side
        self.marks  = []
        self.timers = []
        self.film   = None
        self.values = {'verify': f'{sys.executable} {common.VERIFY}',
                       'scratch': str(self.place),
                       'runs': str(Path(self.setup['tree']) / 'skills' / 'robovac' / 'scripts'
                                   / 'runs.py')}

    def mark(self, text: str) -> None:
        self.marks.append((time.time(), text))

    def still(self, name: str) -> None:
        '''photograph the app's window alone, covered or not, as <name>.png.'''
        found = common.window(self.claim, self.setup.get('pid'))
        if found:
            common.run(FILM, '-x', '-o', '-l', found[0], self.out / f'{name}.png')
        self.mark(f'still {name}' + ('' if found else ' MISSED: no window on screen'))

    def start_film(self) -> None:
        '''bring the window forward and film its frame until the drive ends.'''
        common.mac(self.claim, 'front', self.setup['pid'])
        time.sleep(1)
        w = common.window(self.claim, self.setup['pid'])
        if not w:
            raise SystemExit(f'verify: the {self.side} app has no window on screen to film')
        self.film = subprocess.Popen([FILM, '-v', '-x', '-R', ','.join(map(str, w[1:])),
                                      str(self.out / 'video.mov')], stdin=subprocess.DEVNULL,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        common.record(self.claim, 'procs', {'pid': self.film.pid, 'exe': FILM})
        self.mark(f'film started: window {w[0]} at {w[1]},{w[2]} {w[3]}x{w[4]}')

    def close_app(self) -> None:
        '''quit the side's test copy by the pid the drive started, and confirm its window is gone.'''
        pid = self.setup.get('pid')
        if not pid:
            return
        common.stop(self.claim, pid)
        if common.alive(pid) or common.window(self.claim, pid):
            self.mark(f'app pid {pid} STILL OPEN after the quit')
            return
        self.setup.update(pid=None, window=None, closed=True)
        (self.out / 'setup.json').write_text(json.dumps(self.setup, indent=1) + '\n')
        self.mark(f'app pid {pid} quit, window gone')

    def open_now(self) -> None:
        '''open the side's app mid-turn, as the person opens it while a run goes, and film it.'''
        testcopy.open_app(self.claim, self.side)
        self.setup = json.loads((self.out / 'setup.json').read_text())
        self.mark('app opened mid-run')
        self.start_film()

    def at(self, anchor: str, step: dict, seen: set, host: Host) -> None:
        '''start this step's shots, interrupt and open anchored to `anchor`, the first time.'''
        if anchor in seen:
            return
        seen.add(anchor)
        for where, secs, name in step.get('shots', []):
            if where == anchor:
                self.timers.append(threading.Timer(secs, self.still, (name,)))
        if step.get('interrupt', [None])[0] == anchor:
            self.timers.append(threading.Timer(step['interrupt'][1], host.esc))
        if step.get('open', [None])[0] == anchor:
            self.timers.append(threading.Timer(step['open'][1], self.open_now))
        for t in self.timers:
            if not t.is_alive() and not t.finished.is_set():
                t.start()

    def run(self) -> None:
        '''film the window, run every step, close the session, stop the film, then quit the app.'''
        cwd = self.place / 'w'
        cwd.mkdir(parents=True, exist_ok=True)
        for name, text in self.scenario.get('files', {}).items():
            (cwd / name).write_text(text)
        settings = hook_settings(Path(self.setup['tree']), self.scenario.get('hooks', {}),
                                 self.values)
        (self.place / 'settings.json').write_text(json.dumps(settings, indent=1) + '\n')

        #a scenario's form comes from form.py, the session's only MCP server...
        servers = []
        if self.scenario.get('form'):
            (self.place / 'mcp.json').write_text(json.dumps({'mcpServers': {'form': {
                'type': 'stdio', 'command': sys.executable,
                'args': ['-I', str(common.HERE / 'form.py')]}}}) + '\n')
            servers = ['--mcp-config', self.place / 'mcp.json']

        #a side closed by its last drive is opened again, unless the scenario opens it mid-turn...
        if (self.setup.get('closed') and not self.setup.get('pid')
                and not any('open' in s for s in self.scenario['steps'])):
            testcopy.open_app(self.claim, self.side)
            self.setup = json.loads((self.out / 'setup.json').read_text())
        if self.setup.get('pid'):
            self.start_film()
        sid  = str(uuid.uuid4())
        host = Host(self.setup['claude'], ['--settings', self.place / 'settings.json',
                                           '--setting-sources', 'local', '--strict-mcp-config',
                                           *servers, '--session-id', sid, '--model', 'haiku'],
                    cwd, common.clean_env(ROBOVAC_RUNS=self.setup['log'],
                                          VERIFY_HOOKS=str(self.out / 'hooks.jsonl')),
                    self.out / 'stream.jsonl', self.mark)
        common.record(self.claim, 'procs', {'pid': host.start(), 'exe': self.setup['claude']})
        self.mark(f'session {sid} started in the desktop host mode')
        for step in self.scenario['steps']:
            if 'pause' in step:
                self.mark(f"pause {step['pause']} s")
                time.sleep(step['pause'])
            else:
                seen = set()
                self.at('prompt', step, seen, host)
                host.turn(fill(step['prompt'], self.values), list(step.get('answers', [])),
                          step.get('results', 1), step.get('timeout', 120),
                          lambda anchor, step=step, seen=seen: self.at(anchor, step, seen, host))

                #a step's late stills land before the next step starts...
                for t in self.timers:
                    t.join()
                self.timers = []
        host.close()
        time.sleep(3)
        if self.film:
            self.film.send_signal(signal.SIGINT)
            self.film.wait(timeout=30)
            self.mark('film stopped')

        #the person does not want the window left open once the recording is done...
        self.close_app()
        self.mark('session folder holds: '
                  + (', '.join(sorted(p.name for p in cwd.iterdir())) or 'nothing'))


def described(row: dict) -> str:
    '''
    one log row as the clock and the diff print it.

    Parameters
    ----------
    row : dict
        a line of the side's runs.jsonl.

    Returns
    -------
    str
        its event, why, via, kind, tool and line, then for a work row whether the turn is open,
        and for a work row or a start carrying any, the background tasks running, by id and kind.
    '''
    work  = row.get('event') == 'work'
    tasks = ','.join(f'{k}:{v}' for k, v in (row.get('tasks') or {}).items()) or work and 'none'
    bits  = [row.get('event'), row.get('why'), row.get('via') and f"via={row['via']}",
             row.get('kind') and f"kind={row['kind']}", row.get('tool') and f"tool={row['tool']}",
             row.get('text') and repr(row['text']), work and f"turn={bool(row.get('turn'))}",
             tasks and f'tasks={tasks}']
    return ' '.join(b for b in bits if b)


def clock(drive: Drive) -> str:
    '''
    the side's clock: every driver mark, observed hook and log row on one time line.

    Parameters
    ----------
    drive : Drive
        a drive that has run.

    Returns
    -------
    str
        markdown naming the revision, the Claude Code version and the scenario, then one line per
        moment in seconds from the drive's first mark: a hook as its event, tool, notice, form
        server and agent, a log row as `described` gives it.
    '''
    def lines_of(path: Path) -> list[dict]:
        return [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []

    t0    = drive.marks[0][0]
    lines = [(t, f'driver  {text}') for t, text in drive.marks]
    for h in lines_of(drive.out / 'hooks.jsonl'):
        bits = [h.get('hook_event_name'), h.get('tool_name'), h.get('notification_type'),
                h.get('mcp_server_name') and f"server={h['mcp_server_name']}",
                h.get('agent_id') and f"agent={h['agent_id']}"]
        lines.append((h['t'], 'hook    ' + ' '.join(b for b in bits if b)))
    for r in lines_of(drive.out / 'runs.jsonl'):
        lines.append((r['t'], 'log     ' + described(r)))
    s = drive.setup
    return (f"# {drive.side} clock\n\n{s['rev']} = {s['sha']}; {s['claude_version']}; scenario "
            f"{drive.scenario.get('name')}; seconds from the drive's start; the film's second 0 is "
            "its film started line, within a second.\n\n```\n"
            + ''.join(f'{t - t0:7.1f}  {text}\n' for t, text in sorted(lines)) + '```\n')
