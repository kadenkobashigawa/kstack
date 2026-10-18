#!/usr/bin/env python3
"""
test_verify — checks the guarantee lines of verify-robovac's helpers without the app or a model.

Run it with `python3 test_verify.py`. Everything it makes lives in one temporary folder, which it
removes after, except a test of stop, which starts and stops one /bin/sleep of its own. The exit
code is the number of failed checks.

I1 to I4 hold the drive's isolation: the settings run the revision's runs.py and nothing under
~/.claude, the session's environment carries none of the running session's variables, and cleanup
reaches only the test copy's own ~/Library files and this claim's transcript folders. I5 to I7 break
each isolation line in turn: doctor's log check, the test copy's and the session's ROBOVAC_RUNS,
`--setting-sources local` and `--model haiku`. I7 to I9 hold the app's quit when the recording ends,
and its reopening for the next drive, I10 gives a scenario with a form form.py as its session's only
MCP server, and I11 holds the observer and a scenario's continue-once to this folder's verify.py. P1
to P7 hold the host protocol against a fake Claude Code: the desktop's flags, initialize first, each
answer after its hold, the account kept out of the stream, an unknown request refused, the anchors
in order, a question answered with its first options, and a form filled in, or declined. F1 and F2
hold form.py's MCP exchange, C1 the clock's form server, C2 its work rows, in the diff's rows too,
and C3 its notification type. R1 to R3 hold one test copy per commit per round, reused by every
claim and removed by end-round. D1 holds the docs to the ROBOVAC_ variables the app still reads. B1
holds the test copy's swiftc line to build.sh's, B2 picks the newest Claude Code, B3 and B4 export a
commit and a working tree, and B5 holds the mac helper's compile to the mac.swift beside the
scripts. S1 to S3 check scenarios, K1 and K2 stop only what was started, and H1 to H3 the two hooks.
E1 to E5 hold the commands as a person runs them: claim makes its folder, also from a linked
worktree, a launch or an unknown command is refused with the usage, and diff and the clock print the
same text from a drive recorded in tests/recorded/, which holds every key its recorders wrote and
no local path.
"""

from __future__ import annotations

import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager, redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'scripts'))

import common  # noqa: E402
import host as host_module  # noqa: E402
import session  # noqa: E402
import testcopy  # noqa: E402
import verify  # noqa: E402
from host import Host  # noqa: E402



REPO    = Path(subprocess.run(['git', '-C', str(HERE), 'rev-parse', '--show-toplevel'],
                              capture_output=True, text=True).stdout.strip())
RESULTS = []


def check(name: str, ok: bool, detail: str = '') -> None:
    RESULTS.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f'  ({detail})' if not ok and detail else ''))


@contextmanager
def patched(obj, **names):
    """set module attributes for a block and put them back after, however the block ends."""
    saved = {k: getattr(obj, k) for k in names}
    for k, v in names.items():
        setattr(obj, k, v)
    try:
        yield
    finally:
        for k, v in saved.items():
            setattr(obj, k, v)


def tree_with_hooks(tmp: Path, hooks: dict) -> Path:
    """an exported tree holding only a hooks.json and an executable runs.py."""
    tree = tmp / 'tree'
    (tree / 'hooks').mkdir(parents=True)
    (tree / 'hooks' / 'hooks.json').write_text(json.dumps({'hooks': hooks}))
    return tree


# ── isolation ───────────────────────────────────────────────────────────────


def i1_settings_run_the_revisions_hooks(tmp: Path) -> None:
    hooks = json.loads((REPO / 'hooks' / 'hooks.json').read_text())['hooks']
    tree  = tree_with_hooks(tmp / 'i1', hooks)
    extra = {'Stop': [{'hooks': [{'type': 'command', 'command': '{verify} continue-once x y'}]}]}
    got   = session.hook_settings(tree, extra, {'verify': '/bin/v'})['hooks']
    cmds  = [h['command'] for entries in got.values() for e in entries for h in e['hooks']]
    runs  = str(tree / 'skills' / 'robovac' / 'scripts' / 'runs.py')
    robo  = [c for c in cmds if 'runs.py' in c]
    check('I1 every robovac hook runs the revision\'s runs.py, SessionStart is dropped, the '
          'observer sees every clock event and a scenario hook is filled',
          robo and all(runs in c and '$HOME' not in c for c in robo)
          and 'SessionStart' not in got
          and all(any('observe' in h['command'] for e in got.get(ev, []) for h in e['hooks'])
                  for ev in session.OBSERVED)
          and '/bin/v continue-once x y' in cmds, f'{len(robo)} robovac hooks')
    unseen = set(hooks) - {'SessionStart'} - set(session.OBSERVED)
    check('I1 the clock observes every event the revision\'s robovac hooks run on', not unseen,
          str(unseen))
    stray = tree_with_hooks(tmp / 'i1b', {'Stop': [{'hooks': [
        {'type': 'command', 'command': '"$HOME/.claude/skills/vet/scripts/vet.sh" status'}]}]})
    try:
        session.hook_settings(stray, {}, {})
        refused = False
    except SystemExit:
        refused = True
    check('I1 a hook that would still run the person\'s own ~/.claude setup is refused', refused)
    old   = json.loads(json.dumps(hooks).replace('${CLAUDE_PLUGIN_ROOT}/skills/', '$HOME/.claude/skills/'))
    otree = tree_with_hooks(tmp / 'i1c', old)
    ogot  = session.hook_settings(otree, {}, {})['hooks']
    orobo = [h['command'] for es in ogot.values() for e in es for h in e['hooks'] if 'runs.py' in h['command']]
    check('I1 a revision from before the plugin, its hooks on $HOME/.claude/skills/, runs its own runs.py',
          orobo and all(str(otree / 'skills' / 'robovac' / 'scripts' / 'runs.py') in c and '$HOME' not in c
                        for c in orobo), f'{len(orobo)} robovac hooks')
    left  = tree_with_hooks(tmp / 'i1d', {'Stop': [{'hooks': [
        {'type': 'command', 'command': '"${CLAUDE_PLUGIN_ROOT}/skills/vet/scripts/vet.sh" status'}]}]})
    try:
        session.hook_settings(left, {}, {})
        refused = False
    except SystemExit:
        refused = True
    check('I1 a hook still naming the plugin root after the rewrite is refused', refused)


def i2_the_session_carries_none_of_ours(tmp: Path) -> None:
    os.environ['CLAUDE_CODE_SESSION_ID'] = 'outer'
    os.environ['ANTHROPIC_BASE_URL'] = 'http://outer'
    env = common.clean_env(ROBOVAC_RUNS='/x')
    check('I2 the drive\'s environment drops every CLAUDE* and ANTHROPIC* variable',
          not any(k.startswith(('CLAUDE', 'ANTHROPIC')) for k in env)
          and env['ROBOVAC_RUNS'] == '/x'
          and env.get('PATH') == os.environ.get('PATH'))


def i3_leftovers_never_the_installed_app(tmp: Path) -> None:
    mine = testcopy.leftovers('com.kstack.robovac.verify-20261017140805-baseline')
    check('I3 a test copy\'s own defaults, WebKit and caches are named, and nothing for the '
          'installed com.kstack.robovac or a prefix with a path in it',
          [p.name for p in mine] == ['com.kstack.robovac.verify-20261017140805-baseline.plist',
                                     'com.kstack.robovac.verify-20261017140805-baseline',
                                     'com.kstack.robovac.verify-20261017140805-baseline']
          and testcopy.leftovers('com.kstack.robovac') == []
          and testcopy.leftovers('com.kstack.robovac.verify-../x') == [], str(mine))


def i4_only_this_claims_transcripts(tmp: Path) -> None:
    claim = tmp / 'i4' / '2026-10-17-140805-x'
    slug  = re.sub(r'[^A-Za-z0-9]', '-', str(common.scratch(claim)))
    saved = verify.PROJECTS
    verify.PROJECTS = tmp / 'i4' / 'projects'
    ours, other, outside, sibling = (verify.PROJECTS / f'{slug}-baseline-w',
                                     verify.PROJECTS / 'other', tmp / 'i4' / f'{slug}-baseline-w',
                                     verify.PROJECTS / f'{slug}2-baseline-w')
    for folder in (ours, other, outside, sibling):
        folder.mkdir(parents=True)
    got = [verify.trashable(claim, f) for f in (ours, other, outside, sibling)]
    verify.PROJECTS = saved
    check('I4 cleanup trashes a transcript folder only in ~/.claude/projects and named for this '
          'claim\'s scratch, not the folder of a claim whose name only starts the same',
          got == [True, False, False, False], str(got))


class Done:
    """what a stubbed mac helper returns."""

    def __init__(self, out: str = ''):
        self.stdout, self.stderr, self.returncode = out, '', 0


def setup_for(tmp: Path, name: str, **extra) -> tuple[Path, dict]:
    """a claim folder whose baseline holds a setup.json, the app and its log inside the claim."""
    claim = tmp / name / '2026-10-17-140805-x'
    (claim / 'baseline').mkdir(parents=True)
    app = claim / 'App.app'
    (app / 'Contents' / 'Resources').mkdir(parents=True)
    (app / 'Contents' / 'Info.plist').write_text(
        '<?xml version="1.0" encoding="UTF-8"?><plist version="1.0"><dict>'
        '<key>CFBundleIdentifier</key><string>com.kstack.robovac.verify-x-baseline</string>'
        '</dict></plist>')
    (app / 'Contents' / 'Resources' / 'verify.json').write_text('{"sha": "abc"}')
    setup = {'side': 'baseline', 'rev': 'abc', 'sha': 'abc', 'tree': str(claim / 'src'),
             'app': str(app), 'id': 'com.kstack.robovac.verify-x-baseline',
             'log': str(claim / 'baseline' / 'runs.jsonl'), 'later': True, 'claude': None,
             'claude_version': None, **extra}
    (claim / 'baseline' / 'setup.json').write_text(json.dumps(setup))
    return claim, setup


def i5_doctor_keeps_the_real_log_out(tmp: Path) -> None:
    claim, setup = setup_for(tmp, 'i5')
    path = claim / 'baseline' / 'setup.json'

    def log_line(log: Path, **more) -> tuple[bool, str]:
        path.write_text(json.dumps(dict(setup, log=str(log), **more)))
        with patched(common, mac=lambda *a: Done('yes')):
            return next(c for c in verify.doctor(claim, 'baseline') if c[1].startswith('log '))

    inside = claim / 'baseline' / 'runs.jsonl'
    ok, elsewhere = log_line(inside), log_line(tmp / 'i5' / 'runs.jsonl')
    with patched(verify, REAL_LOG=inside):
        real = log_line(inside)
    check('I5 doctor passes a log inside the claim\'s side folder, and fails one outside it or '
          'the person\'s own', ok[0] and not elsewhere[0] and not real[0],
          f'{ok} {elsewhere} {real}')
    path.write_text(json.dumps(dict(setup, later=False, closed=True, pid=None)))
    with patched(common, mac=lambda *a: Done('yes')):
        shut = verify.doctor(claim, 'baseline')[0]
    check('I5 doctor takes a side whose app a drive closed as not open yet', shut[0], str(shut))


def i6_the_app_gets_the_claims_log(tmp: Path) -> None:
    claim, setup = setup_for(tmp, 'i6', later=False)
    os.environ['CLAUDE_CODE_SESSION_ID'] = 'outer'
    seen = tmp / 'i6' / 'env'
    exe  = Path(setup['app']) / 'Contents' / 'MacOS' / 'Robovac'
    exe.parent.mkdir(parents=True)
    exe.write_text(f'#!/bin/sh\nenv > {seen}\nexec /bin/sleep 30\n')
    exe.chmod(0o755)
    with patched(common, mac=lambda *a: Done(), window=lambda c, pid: [1, 0, 0, 1, 1]):
        testcopy.open_app(claim, 'baseline')
    pid = json.loads((claim / 'baseline' / 'setup.json').read_text())['pid']
    os.kill(pid, 15)
    os.waitpid(pid, 0)
    env = dict(x.split('=', 1) for x in seen.read_text().splitlines() if '=' in x)
    check('I6 the test copy starts with the claim\'s log in ROBOVAC_RUNS, a fixed house and none '
          'of the running session\'s variables',
          env.get('ROBOVAC_RUNS') == setup['log'] and env.get('ROBOVAC_HOUSE') == '1'
          and not any(k.startswith(('CLAUDE', 'ANTHROPIC')) for k in env), str(sorted(env))[:200])


def session_in(tmp: Path, name: str, **extra) -> tuple[session.Drive, Path, subprocess.Popen]:
    """a Drive on the fake Claude Code, with a sleep standing for the test copy's app."""
    claim, setup = setup_for(tmp, name, later=False, **extra)
    d = tmp / name
    (d / 'fake.py').write_text(FAKE)
    (d / 'claude').write_text(f'#!/bin/sh\nenv > {d / "env"}\n'
                              f'exec {sys.executable} {d / "fake.py"} "$@" {d / "log"}\n')
    (d / 'claude').chmod(0o755)
    hooks = json.loads((REPO / 'hooks' / 'hooks.json').read_text())['hooks']
    tree_with_hooks(d, hooks)
    app = subprocess.Popen(['/bin/sleep', '60'])
    common.record(claim, 'procs', {'pid': app.pid, 'exe': '/bin/sleep'})
    setup.update(claude=str(d / 'claude'), tree=str(d / 'tree'), pid=app.pid, window=[1, 0, 0, 1, 1])
    (claim / 'baseline' / 'setup.json').write_text(json.dumps(setup))
    scenario = {'name': 'x', 'steps': [{'prompt': 'hi'}]}
    with patched(common, scratch=lambda c: tmp / 'scratch' / c.name):
        return session.Drive(claim, 'baseline', scenario), d, app


def stubbed_film(drive: session.Drive):
    """a start_film that films nothing, so the order of the film's end and the app's quit shows."""
    def start() -> None:
        drive.film = subprocess.Popen(['/bin/sleep', '60'])
        drive.mark('film started')
    return start


def i7_the_session_is_isolated(tmp: Path) -> None:
    os.environ['CLAUDE_CODE_SESSION_ID'] = 'outer'
    drive, d, app = session_in(tmp, 'i7')
    drive.start_film = stubbed_film(drive)
    with patched(common, scratch=lambda c: tmp / 'scratch' / c.name,
                 window=lambda c, pid: [1, 0, 0, 1, 1] if common.alive(pid) else None):
        drive.run()
    argv = json.loads((d / 'log').read_text().splitlines()[0])
    env  = dict(x.split('=', 1) for x in (d / 'env').read_text().splitlines() if '=' in x)

    def pair(a: str, b: str) -> bool:
        return a in argv and argv[argv.index(a) + 1:argv.index(a) + 2] == [b]

    check('I7 the session loads only local settings, the drive\'s own settings file, no other '
          'MCP server, and the haiku model',
          pair('--setting-sources', 'local') and '--strict-mcp-config' in argv
          and '--mcp-config' not in argv
          and pair('--model', 'haiku') and pair('--settings', str(drive.place / 'settings.json')),
          str(argv))
    check('I7 the session\'s hooks write to the claim\'s log, not the person\'s, and it carries none '
          'of the running session\'s variables',
          env.get('ROBOVAC_RUNS') == drive.setup['log'] and env.get('VERIFY_HOOKS')
          and not any(k.startswith(('CLAUDE', 'ANTHROPIC')) for k in env), str(sorted(env))[:200])
    kept = [t for _, t in drive.marks]
    quit_ = next((i for i, t in enumerate(kept) if 'quit, window gone' in t), None)
    saved = json.loads((drive.out / 'setup.json').read_text())
    check('I7 the app is quit by its pid right after the film stops, its window is confirmed gone '
          'and the side is marked closed',
          app.poll() is not None and quit_ is not None and kept.index('film stopped') < quit_
          and saved['pid'] is None and saved['closed'] is True, str(kept))
    app.kill()


def i8_a_closed_side_opens_for_its_next_drive(tmp: Path) -> None:
    drive, d, app = session_in(tmp, 'i8')
    app.kill()
    app.wait()
    drive.setup.update(pid=None, window=None, closed=True)
    (drive.out / 'setup.json').write_text(json.dumps(drive.setup))
    opened = []

    def reopen(claim: Path, side: str) -> list:
        again = subprocess.Popen(['/bin/sleep', '60'])
        common.record(claim, 'procs', {'pid': again.pid, 'exe': '/bin/sleep'})
        opened.append(again)
        text = json.loads((claim / side / 'setup.json').read_text())
        text.update(pid=again.pid, window=[1, 0, 0, 1, 1], closed=False)
        (claim / side / 'setup.json').write_text(json.dumps(text))
        return text['window']

    drive.start_film = stubbed_film(drive)
    with patched(testcopy, open_app=reopen), patched(
            common, scratch=lambda c: tmp / 'scratch' / c.name,
            window=lambda c, pid: [1, 0, 0, 1, 1] if common.alive(pid) else None):
        drive.run()
    check('I8 a side a drive closed is opened again by its next drive, filmed, and closed after',
          len(opened) == 1 and any(t == 'film started' for _, t in drive.marks)
          and opened[0].poll() is not None, str(drive.marks))
    for p in opened:
        p.kill()



def i9_an_app_that_stays_open_is_reported(tmp: Path) -> None:
    drive, d, app = session_in(tmp, 'i9')
    (drive.claim / 'started.json').unlink()
    common.record(drive.claim, 'procs', {'pid': app.pid, 'exe': '/usr/bin/true'})
    drive.start_film = stubbed_film(drive)
    with patched(common, scratch=lambda c: tmp / 'scratch' / c.name,
                 window=lambda c, pid: [1, 0, 0, 1, 1] if common.alive(pid) else None):
        drive.run()
    saved = json.loads((drive.out / 'setup.json').read_text())
    check('I9 an app still open after the quit is marked STILL OPEN, and its side is not marked '
          'closed', app.poll() is None and saved['pid'] == app.pid and not saved.get('closed')
          and any('STILL OPEN' in t for _, t in drive.marks), str(drive.marks))
    app.kill()
    app.wait()


def i10_a_form_scenario_adds_only_the_form_server(tmp: Path) -> None:
    drive, d, app = session_in(tmp, 'i10')
    drive.scenario = dict(drive.scenario, form=True)
    drive.start_film = stubbed_film(drive)
    with patched(common, scratch=lambda c: tmp / 'scratch' / c.name,
                 window=lambda c, pid: [1, 0, 0, 1, 1] if common.alive(pid) else None):
        drive.run()
    argv  = json.loads((d / 'log').read_text().splitlines()[0])
    given = Path(argv[argv.index('--mcp-config') + 1]) if '--mcp-config' in argv else None
    found = json.loads(given.read_text())['mcpServers'] if given and given.exists() else {}
    check('I10 a scenario with a form gives its session one MCP server, the form, still under '
          '--strict-mcp-config, from a file in the drive\'s scratch',
          '--strict-mcp-config' in argv and list(found) == ['form']
          and found['form']['args'][-1] == str(HERE.parent / 'scripts' / 'form.py')
          and given.parent == drive.place, f'{argv} {found}')
    app.kill()


def i11_the_hooks_run_this_verify_py(tmp: Path) -> None:
    script = HERE.parent / 'scripts' / 'verify.py'
    drive, d, app = session_in(tmp, 'i11')
    shipped = HERE.parent / 'scenarios' / 'stop-hook-continues.json'

    #hook_settings fills a scenario's hooks in place, so the template is read from its own load...
    template = session.load_scenario(shipped)['hooks']['Stop'][0]['hooks'][0]['command']
    drive.scenario = dict(drive.scenario, hooks=session.load_scenario(shipped)['hooks'])
    drive.start_film = stubbed_film(drive)
    with patched(common, scratch=lambda c: tmp / 'scratch' / c.name,
                 window=lambda c, pid: [1, 0, 0, 1, 1] if common.alive(pid) else None):
        drive.run()
    got      = json.loads((drive.place / 'settings.json').read_text())['hooks']
    observer = f'{sys.executable} {script} observe'
    seen     = {e: [h['command'] for x in got[e] for h in x['hooks']
                    if h['command'].endswith(' observe')] for e in session.OBSERVED}
    once     = template.replace('{verify}', f'{sys.executable} {script}').replace(
        '{scratch}', str(drive.place))
    check('I11 the observer on every clock event, and the scenario\'s continue-once, run this '
          'folder\'s verify.py with the drive\'s own interpreter',
          script.is_file() and all(c == [observer] for c in seen.values())
          and once in [h['command'] for x in got['Stop'] for h in x['hooks']]
          and ' continue-once ' in once, f'{seen} {once}')
    app.kill()


# ── the host protocol ─────────────────────────────────────────────────────


FAKE = r'''
import json, sys, time
log = open(sys.argv[-1], 'a')
log.write(json.dumps(sys.argv[1:-1]) + '\n')
def out(o):
    sys.stdout.write(json.dumps(o) + '\n'); sys.stdout.flush()
for line in sys.stdin:
    msg = json.loads(line)
    log.write(json.dumps({'got': msg, 't': time.time()}) + '\n'); log.flush()
    if msg.get('request', {}).get('subtype') == 'initialize':
        out({'type': 'control_response',
             'response': {'request_id': 'init', 'response': {'account': {'email': 'a@b'}}}})
    elif msg.get('type') == 'user':
        out({'type': 'control_request', 'request_id': 'r1', 'request': {
            'subtype': 'can_use_tool', 'tool_name': 'Bash', 'input': {'command': 'touch x'}}})
        out({'type': 'control_request', 'request_id': 'r2', 'request': {
            'subtype': 'can_use_tool', 'tool_name': 'AskUserQuestion', 'input': {'questions': [
                {'question': 'Proceed?', 'options': [{'label': 'yes'}, {'label': 'no'}]}]}}})
        out({'type': 'control_request', 'request_id': 'r3', 'request': {
            'subtype': 'elicitation', 'mcp_server_name': 'form', 'message': 'Type one word.',
            'mode': 'form', 'requested_schema': {'type': 'object', 'properties': {
                'word': {'type': 'string'}, 'count': {'type': 'integer'},
                'sure': {'type': 'boolean'}, 'pick': {'type': 'string', 'enum': ['b', 'c']}}}}})
        out({'type': 'control_request', 'request_id': 'r4',
             'request': {'subtype': 'hook_callback'}})
    elif msg.get('type') == 'control_response' and msg['response']['request_id'] == 'r4':
        out({'type': 'result', 'subtype': 'success', 'result': 'done'})
'''


def p_host_against_a_fake(tmp: Path) -> None:
    d = tmp / 'p'
    d.mkdir()
    (d / 'fake.py').write_text(FAKE)
    fake = f'#!/bin/sh\nexec {sys.executable} {d / "fake.py"} "$@" {d / "log"}\n'
    (d / 'claude').write_text(fake)
    (d / 'claude').chmod(0o755)
    marks, anchors = [], []
    host = Host(str(d / 'claude'), ['--model', 'haiku'], d, dict(os.environ), d / 'stream.jsonl',
                lambda text: marks.append((time.time(), text)))
    host.start()
    t0  = time.time()
    plan = [{'hold': 1.5, 'behavior': 'deny', 'interrupt': True}, {'hold': 0, 'behavior': 'allow'},
            {'hold': 0.5, 'behavior': 'allow'}]
    got  = host.turn('hello', plan, 1, 20, lambda a: anchors.append((a, time.time())))
    host.close()
    lines  = [json.loads(x) for x in (d / 'log').read_text().splitlines()]
    sent   = [x['got'] for x in lines[1:]]
    replies = {x['got']['response']['request_id']: x for x in lines[1:]
               if x['got'].get('type') == 'control_response'}
    answer  = replies['r1']
    check('P1 the session starts with the desktop app\'s own flags and the drive\'s',
          lines[0] == ['--output-format', 'stream-json', '--input-format', 'stream-json',
                       '--verbose', '--permission-prompt-tool', 'stdio', '--model', 'haiku'],
          str(lines[0]))
    check('P2 initialize goes first, and the prompt after it as the person\'s message',
          sent[0].get('request', {}).get('subtype') == 'initialize'
          and sent[1].get('message', {}).get('content') == 'hello', str(sent[:2]))
    check('P3 a permission request is answered after its hold, here denied with Esc',
          answer['got']['response']['response'] == {'behavior': 'deny',
                                                    'message': 'The user rejected this.',
                                                    'interrupt': True}
          and answer['t'] - t0 >= 1.5, str(answer))
    stream = (d / 'stream.jsonl').read_text()
    check('P4 the account the session opens with stays out of stream.jsonl, the rest goes in',
          'a@b' not in stream and '"result"' in stream and got == 1, stream[:200])
    question = replies['r2']['got']['response']['response']
    check('P6 a question allowed is answered with each question\'s first option, its input kept',
          question == {'behavior': 'allow', 'updatedInput': {
              'questions': [{'question': 'Proceed?',
                             'options': [{'label': 'yes'}, {'label': 'no'}]}],
              'answers': {'Proceed?': 'yes'}}}, str(question))
    form = replies['r3']
    check('P7 an MCP form is filled in and accepted after its own hold, a value for each field '
          'by its type, an enum\'s first choice',
          form['got']['response'] == {'subtype': 'success', 'request_id': 'r3', 'response': {
              'action': 'accept', 'content': {'word': 'yes', 'count': 1, 'sure': True,
                                              'pick': 'b'}}}
          and form['t'] - replies['r2']['t'] >= 0.5, str(form))
    asked = [t for _, t in marks if t.startswith('asked: ')]
    check('P7 the clock\'s asked lines name a form by its server and a question by its agent',
          len(asked) == 3 and asked[1].startswith('asked: AskUserQuestion agent=main {"questions"')
          and asked[2] == 'asked: form server=form "Type one word."', str(asked))
    check('P7 a form denied is declined', host_module.REPLIES['elicitation'](
        {'requested_schema': {'properties': {'word': {'type': 'string'}}}},
        {'behavior': 'deny'}) == {'action': 'decline'})
    refused = replies.get('r4', {}).get('got', {})
    check('P5 an unknown request is refused by name, and the anchors come ask and answer for each '
          'request answered, then result',
          refused.get('response', {}).get('subtype') == 'error'
          and [a for a, _ in anchors] == ['ask', 'answer'] * 3 + ['result'], f'{refused} {anchors}')


def f_the_form_server(tmp: Path) -> None:
    proc = subprocess.Popen([sys.executable, '-I', str(HERE.parent / 'scripts' / 'form.py')],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)

    def say(msg: dict) -> None:
        proc.stdin.write(json.dumps(msg) + '\n')
        proc.stdin.flush()

    def heard() -> dict:
        return json.loads(proc.stdout.readline())

    say({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
         'params': {'protocolVersion': '2025-06-18', 'capabilities': {'elicitation': {}}}})
    hello = heard()
    say({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
    say({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'})
    tools = heard()
    say({'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {'name': 'ask',
                                                                      'arguments': {}}})
    asked = heard()
    say({'jsonrpc': '2.0', 'id': asked.get('id'),
         'result': {'action': 'accept', 'content': {'word': 'yes'}}})
    done = heard()
    proc.stdin.close()
    proc.wait(timeout=10)
    check('F1 the form server answers initialize in the client\'s version with tools, lists one '
          'tool, ask, and answers no notification',
          hello.get('id') == 1 and hello['result']['protocolVersion'] == '2025-06-18'
          and 'tools' in hello['result']['capabilities']
          and tools.get('id') == 2 and [t['name'] for t in tools['result']['tools']] == ['ask'],
          f'{hello} {tools}')
    check('F2 a call of ask opens an MCP form, and the call\'s result carries what came back',
          asked.get('method') == 'elicitation/create'
          and asked['params']['requestedSchema']['properties']
          and done.get('id') == 3 and 'accept' in done['result']['content'][0]['text']
          and '"yes"' in done['result']['content'][0]['text'], f'{asked} {done}')


def c_the_clock(tmp: Path) -> None:
    out = tmp / 'c'
    out.mkdir()
    (out / 'hooks.jsonl').write_text(json.dumps({'hook_event_name': 'Elicitation', 't': 101.0,
                                                 'mcp_server_name': 'form'}) + '\n')
    rows = [{'t': 102.0, 'session': 'a', 'event': 'end', 'why': 'waiting on you'},
            {'t': 103.0, 'session': 'a', 'event': 'work', 'turn': False,
             'tasks': {'s1': 'shell', 'ag1': 'subagent'}},
            {'t': 104.0, 'session': 'a', 'event': 'start', 'via': 'again',
             'tasks': {'s1': 'shell'}},
            {'t': 105.0, 'session': 'a', 'event': 'work', 'turn': True, 'tasks': {}}]
    (out / 'runs.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
    drive = type('Drive', (), {'marks': [(100.0, 'prompt: hi')], 'out': out, 'side': 'baseline',
                               'scenario': {'name': 'x'},
                               'setup': {'rev': 'abc', 'sha': 'abc', 'claude_version': '1'}})()
    lines = session.clock(drive)
    check('C1 the clock names a form\'s server at its hook, on one time line with the log',
          '    1.0  hook    Elicitation server=form\n' in lines
          and '    2.0  log     end waiting on you\n' in lines, lines)
    check('C2 the clock prints a work row with its turn and its tasks, none when it has none, and '
          'a start with the tasks it carries',
          '    3.0  log     work turn=False tasks=s1:shell,ag1:subagent\n' in lines
          and '    4.0  log     start via=again tasks=s1:shell\n' in lines
          and '    5.0  log     work turn=True tasks=none\n' in lines, lines)
    claim = tmp / 'c' / 'claim'
    for side in common.SIDES:
        (claim / side).mkdir(parents=True)
        (claim / side / 'runs.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
    (claim / 'diff').mkdir()
    with redirect_stdout(io.StringIO()):
        verify.cmd_diff(claim)
    table = (claim / 'diff' / 'rows.md').read_text()
    check('C2 the diff\'s rows print a work row the same way', table.count(
        '    1.0  work turn=False tasks=s1:shell,ag1:subagent\n') == 2, table)


    #the recorded drive holds no Notification row, so this one is made by hand, and named so...
    synthetic = tmp / 'c3'
    synthetic.mkdir()
    (synthetic / 'hooks.jsonl').write_text(json.dumps({
        'hook_event_name': 'Notification', 'notification_type': 'idle_prompt', 't': 201.0}) + '\n')
    drive = type('Drive', (), {'marks': [(200.0, 'prompt: hi')], 'out': synthetic,
                               'side': 'baseline', 'scenario': {'name': 'x'},
                               'setup': {'rev': 'abc', 'sha': 'abc', 'claude_version': '1'}})()
    check('C3 the clock names a Notification by its notification_type (a synthetic row: the '
          'recorded drive has none)', '    1.0  hook    Notification idle_prompt\n'
          in session.clock(drive))


# ── the round's test copies ───────────────────────────────────────────────


def r_one_copy_per_version(tmp: Path) -> None:
    root, repo = tmp / 'r', tmp / 'r' / 'repo'
    repo.mkdir(parents=True)

    def git(*a: str) -> str:
        return subprocess.run(['git', '-C', str(repo), *a], capture_output=True, text=True,
                              ).stdout.strip()

    def commit(text: str) -> str:
        (repo / 'a.txt').write_text(text)
        git('add', '.')
        git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', text)
        return git('rev-parse', 'HEAD')

    git('init', '-q')
    first, second = commit('one\n'), commit('two\n')
    built, dying = [], [True]

    def fake_build(tree: Path, app: Path, bundle: str, stamp: dict) -> None:
        app.mkdir(parents=True)
        if dying:
            dying.clear()
            raise SystemExit('the first build dies')
        built.append(bundle)

    claims = []
    for n in range(3):
        claims.append(root / f'2026-10-17-14080{n}-x')
        claims[-1].mkdir()
    unregistered = []
    with patched(testcopy, BUILDS=root / 'builds', build=fake_build, images=lambda t, r: None,
                 unregister=lambda app, bundle_id: unregistered.append(bundle_id)), patched(
            common, scratch=lambda claim: root / 'scratch' / claim.name):
        try:
            testcopy.obtain(claims[0], first, repo, 'baseline')
        except SystemExit:
            pass
        a = testcopy.obtain(claims[0], first, repo, 'baseline')
        b = testcopy.obtain(claims[1], first, repo, 'treatment')
        c = testcopy.obtain(claims[1], second, repo, 'treatment')
        w1 = testcopy.obtain(claims[0], 'WORKTREE', repo, 'baseline')
        w2 = testcopy.obtain(claims[1], 'WORKTREE', repo, 'baseline')
        check('R1 a commit builds once per round, after a build that died is made again, and a '
              'second claim reuses it under the same tree, app and id',
              len(built) == 4 and (a[4], b[4], c[4]) == (False, True, False)
              and a[:4] == b[:4] and a[3].startswith(testcopy.PREFIX)
              and a[3] != c[3] and testcopy.leftovers(a[3]), f'{built} {a} {b}')
        check('R2 a working tree is built again for every claim, in its own claim\'s scratch',
              not w1[4] and not w2[4] and w1[1] != w2[1]
              and all(str(x[1]).startswith(str(root / 'scratch')) for x in (w1, w2)), f'{w1} {w2}')
        with redirect_stdout(io.StringIO()):
            verify.cmd_cleanup(claims[0])
        kept = a[2].exists() and a[3] not in unregistered
        with redirect_stdout(io.StringIO()):
            code = verify.cmd_end_round()
    check('R3 cleanup leaves the round\'s copies, and end-round removes them and unregisters each',
          kept and code == 0 and not list((root / 'builds').iterdir())
          and {a[3], c[3]} <= set(unregistered), f'{kept} {code} {unregistered}')


# ── the docs ──────────────────────────────────────────────────────────────


def d_docs_name_only_what_the_app_reads(tmp: Path) -> None:
    skill = HERE.parent
    docs  = [skill / 'SKILL.md', *(skill / 'features').glob('*.md'),
             *(skill / 'scripts').glob('*.py')]
    named = set()
    for doc in docs:
        named |= set(re.findall(r'ROBOVAC_[A-Z]+', doc.read_text()))
    app = ''
    for root in (REPO / 'apps' / 'robovac-widget', REPO / 'skills' / 'robovac'):
        for path in root.rglob('*'):
            if path.suffix in ('.swift', '.sh', '.py', '.js', '.md') and path.is_file():
                app += path.read_text(errors='ignore')
    missing = sorted(n for n in named if n not in app)
    check('D1 every ROBOVAC_ variable the skill names is one the app or the robovac scripts '
          'still read', named and not missing, str(missing))


# ── building and exporting ────────────────────────────────────────────────


def b1_swiftc_line_is_build_sh(tmp: Path) -> None:
    shell  = (REPO / 'apps' / 'robovac-widget' / 'mac' / 'build.sh').read_text()
    words  = shlex.split(re.search(r'^swiftc .*?(?<!\\)$', shell.replace('\\\n', ' '), re.M)[0])
    flags  = tuple(w for w in words[1:words.index('-o')] if not w.startswith('$here/'))
    source = tuple(w.removeprefix('$here/') for w in words if w.startswith('$here/'))
    check('B1 the test copy compiles with build.sh\'s own swiftc flags and sources',
          flags == testcopy.SWIFTC and source == testcopy.SOURCES, f'{flags} {source}')


def b2_newest_claude(tmp: Path) -> None:
    saved = verify.APPS
    verify.APPS = tmp / 'b2'
    for version in ('2.1.30', '2.1.299', '2.1.295', 'latest'):
        exe = verify.APPS / version / 'abc' / 'claude.app' / 'Contents' / 'MacOS' / 'claude'
        exe.parent.mkdir(parents=True)
        exe.write_text('')
    got = verify.claude_binary()
    verify.APPS = saved
    check('B2 the newest Claude Code is picked by version number, not by name',
          got is not None and got.relative_to(tmp / 'b2').parts[0] == '2.1.299', str(got))


def b3_b4_export(tmp: Path) -> None:
    repo = tmp / 'b3' / 'repo'
    repo.mkdir(parents=True)

    def git(*a: str) -> subprocess.CompletedProcess:
        return subprocess.run(['git', '-C', str(repo), *a], capture_output=True, text=True)

    git('init', '-q')
    (repo / '.gitignore').write_text('ignored.txt\n')
    (repo / 'a.txt').write_text('one\n')
    git('add', '.')
    git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'one')
    first = git('rev-parse', 'HEAD').stdout.strip()
    (repo / 'a.txt').write_text('two\n')
    (repo / 'new.txt').write_text('untracked\n')
    (repo / 'ignored.txt').write_text('ignored\n')
    sha = testcopy.export(first, tmp / 'b3' / 'commit', repo)
    check('B3 a commit exports as committed, whatever the checkout holds now',
          sha == first and (tmp / 'b3' / 'commit' / 'a.txt').read_text() == 'one\n'
          and not (tmp / 'b3' / 'commit' / 'new.txt').exists())
    label = testcopy.export('WORKTREE', tmp / 'b3' / 'tree', repo)
    out   = tmp / 'b3' / 'tree'
    check('B4 WORKTREE exports the checkout as it stands, less what git ignores',
          label == f'WORKTREE on {first}' and (out / 'a.txt').read_text() == 'two\n'
          and (out / 'new.txt').exists() and not (out / 'ignored.txt').exists(), label)


def b5_the_mac_helper_compiles_the_real_source(tmp: Path) -> None:
    source = HERE.parent / 'scripts' / 'mac.swift'
    calls  = []

    def fake(*argv, cwd=None):
        calls.append([str(a) for a in argv])
        return subprocess.CompletedProcess(argv, 0, '', '')

    claim = tmp / 'b5' / '2026-10-17-140805-x'
    with patched(common, run=fake, scratch=lambda c: tmp / 'b5' / 'scratch'):
        common.mac(claim, 'preflight')
    binary = str(tmp / 'b5' / 'scratch' / 'bin' / 'mac')
    check('B5 the mac helper is compiled from the mac.swift beside the scripts, into the claim\'s '
          'scratch, and then run with its arguments',
          source.is_file() and calls == [['swiftc', '-O', str(source), '-o', binary],
                                         [binary, 'preflight']], str(calls))


# ── scenarios ─────────────────────────────────────────────────────────────


def s_scenarios(tmp: Path) -> None:
    shipped = sorted((HERE.parent / 'scenarios').glob('*.json'))
    loaded  = [session.load_scenario(p)['name'] == p.stem for p in shipped]
    check('S1 every shipped scenario loads and is named for its file',
          shipped and all(loaded), str(list(zip(shipped, loaded))))
    bad = {'steps': [{'prompt': 'x', 'answers': [{'behavior': 'maybe'}],
                      'shots': [['later', 1, 'a'], ['ask', 1, 'a'], ['ask', 1, 'Bad Name']],
                      'interrupt': ['soon', 1]}, {'wait': 3}]}
    (tmp / 'bad.json').write_text(json.dumps(bad))
    try:
        session.load_scenario(tmp / 'bad.json')
        said = ''
    except SystemExit as e:
        said = str(e)
    check('S2 a bad scenario is refused naming each problem',
          all(w in said for w in ('not allow or deny', 'anchored to later', 'a is used twice',
                                  'Bad Name is not lowercase', 'interrupt is anchored to soon',
                                  'neither a prompt nor a pause')), said)
    check('S3 fill replaces the names it holds and leaves other braces',
          session.fill('{runs} say "{x}"', {'runs': '/r'}) == '/r say "{x}"')


# ── the commands, run as a person runs them ────────────────────────────────

RECORDED = HERE / 'recorded' / '2026-10-18-023438-background-work'


#every key a recorder writes whose value is a local path, and what the recording holds in its place...
PATH_KEYS   = ('transcript_path', 'cwd', 'transcript', 'tree', 'app', 'log', 'claude')
PLACEHOLDER = '<path>'
ABSOLUTE    = re.compile(r'(?:^|[^\w/])(?:~|/[\w.-]+)/|^[~/]|(?<!\w)-(?:Users|private|var|tmp|home|'
                         r'Applications|Volumes|opt|usr|etc|Library)-')


def recorded_values(folder: Path) -> list[tuple[str, str, str]]:
    """every value in a recorded drive as (file, key, text); a text file's lines have no key."""
    out = []

    def walk(name: str, value, key: str = '') -> None:
        if isinstance(value, dict):
            for k, v in value.items():
                walk(name, v, k)
        elif isinstance(value, list):
            for v in value:
                walk(name, v, key)
        else:
            out.append((name, key, str(value)))

    for path in sorted(folder.rglob('*')):
        name = str(path.relative_to(folder))
        if path.suffix == '.jsonl':
            for line in path.read_text().splitlines():
                walk(name, json.loads(line))
        elif path.suffix == '.json':
            walk(name, json.loads(path.read_text()))
        elif path.is_file():
            out.extend((name, '', line) for line in path.read_text().splitlines())
    return out


def local_paths(folder: Path) -> list[str]:
    """where a recorded drive holds a local path: a path key that is not the placeholder, a value
    starting with / or ~, or one holding an absolute path or a dash-encoded one."""
    return [f'{name} {key}: {value[:60]}' for name, key, value in recorded_values(folder)
            if key in PATH_KEYS and value != PLACEHOLDER or ABSOLUTE.search(value)]


def placeholders_hold(folder: Path) -> bool:
    """the recorded hooks, log rows and setup carry the keys the recorders wrote, each path key
    present with the placeholder, and the session key present."""
    seen = {(name.split('/')[-1], key) for name, key, _ in recorded_values(folder)}
    return all(('hooks.jsonl', key) in seen for key in ('session_id', 'transcript_path', 'prompt',
                                                   'tool_use_id', 'tool_input')) \
        and all(('runs.jsonl', key) in seen for key in ('session', 'project', 'cwd', 'transcript',
                                                    'mark')) \
        and all(('setup.json', key) in seen for key in ('side', 'tree', 'app', 'id', 'log',
                                                        'claude'))


def scripts_in_a_repo(tmp: Path) -> tuple[Path, Path]:
    """a copy of the scripts folder inside a throwaway git repository, and that repository."""
    repo = tmp / 'repo'
    repo.mkdir(parents=True)
    subprocess.run(['git', '-C', str(repo), 'init', '-q'], check=True)
    shutil.copytree(HERE.parent / 'scripts', repo / 'scripts')
    return repo / 'scripts' / 'verify.py', repo


def e_commands(tmp: Path) -> None:
    script, repo = scripts_in_a_repo(tmp / 'e')
    (tmp / 'e' / 'tmp').mkdir()

    def command(*argv, stdin: str = '') -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, script, *argv], input=stdin, capture_output=True,
                              text=True, env=dict(os.environ, TMPDIR=str(tmp / 'e' / 'tmp')))

    made = command('claim', 'a-claim')
    folder = Path(made.stdout.strip())
    timeline = (folder / 'timeline.md').read_text() if folder.exists() else ''
    check('E1 claim makes <git-common-dir>/verify-robovac/<time>-<slug>/ with baseline, treatment '
          'and diff, notes it in timeline.md and prints the folder',
          made.returncode == 0 and folder.parent == repo.resolve() / '.git' / 'verify-robovac'
          and re.fullmatch(r'\d{4}-\d\d-\d\d-\d{6}-a-claim', folder.name)
          and all((folder / part).is_dir() for part in ('baseline', 'treatment', 'diff'))
          and timeline.endswith(' claim folder made for a-claim\n'), str(made))
    bad = command('claim', 'Not Kebab')
    check('E1 claim refuses a slug that is not lowercase kebab-case and makes nothing',
          bad.returncode == 1 and 'lowercase kebab-case' in bad.stderr
          and len(list(folder.parent.iterdir())) == 1, str(bad))

    shapes = [(), ('launch',), ('launch', str(folder)), ('launch', str(folder), 'middle', 'abc'),
              ('launch', str(folder), 'baseline'), ('launch', str(folder), 'baseline', 'abc', '--soon'),
              ('launch', str(folder), 'baseline', 'abc', '--later', 'extra'),
              ('doctor', str(folder)), ('drive', str(folder), 'baseline'), ('diff',), ('cleanup',),
              ('end-round', 'extra'), ('continue-once', 'flag'), ('claim',), ('mystery',)]
    said = [command(*shape) for shape in shapes]
    check('E2 a launch or any other command with the wrong arguments, or an unknown command, prints '
          'the usage and exits 2',
          all(r.returncode == 2 and r.stdout == verify.__doc__ + '\n' for r in said),
          str([(s, r.returncode) for s, r in zip(shapes, said) if r.returncode != 2]))
    check('E2 the usage names every command',
          all(f'    {name}' in verify.__doc__ for name in (
              'claim <slug>', 'launch <E> <side> <rev> [--later]', 'doctor <E> <side>',
              'drive <E> <side> <scenario>', 'diff <E>', 'cleanup <E>', 'end-round', 'observe',
              'continue-once <flag> <reason>')))

    shutil.copytree(RECORDED, tmp / 'e' / 'again')
    again = command('launch', str(tmp / 'e' / 'again'), 'baseline', 'abc')
    unknown = command('launch', str(folder), 'baseline', 'no-such-rev')
    check('E3 launch refuses a side launched already, and a revision git cannot name, before '
          'building anything',
          again.returncode == 1 and 'baseline was launched for this claim already' in again.stderr
          and unknown.returncode == 1 and 'git cannot name no-such-rev' in unknown.stderr
          and not (folder / 'baseline' / 'setup.json').exists(), f'{again} {unknown}')


def e_claim_from_a_linked_worktree(tmp: Path) -> None:
    _, main = scripts_in_a_repo(tmp / 'w')
    linked  = tmp / 'w' / 'linked'

    def git(*a: str) -> subprocess.CompletedProcess:
        return subprocess.run(['git', '-C', str(main), '-c', 'user.name=t', '-c', 'user.email=t@t',
                               *a], capture_output=True, text=True)

    git('add', '.')
    git('commit', '-qm', 'scripts')
    git('worktree', 'add', '-q', str(linked))
    made   = subprocess.run([sys.executable, linked / 'scripts' / 'verify.py', 'claim', 'a-claim'],
                            capture_output=True, text=True, env=dict(os.environ, TMPDIR=str(tmp)))
    folder = Path(made.stdout.strip())
    own    = subprocess.run(['git', '-C', str(linked), 'rev-parse', '--path-format=absolute',
                             '--git-dir'], capture_output=True, text=True).stdout.strip()
    check('E1 claim run from a linked worktree makes its folder under the main repository\'s .git, '
          'not under the worktree\'s own git directory',
          made.returncode == 0 and own != str(main.resolve() / '.git')
          and folder.parent == main.resolve() / '.git' / 'verify-robovac'
          and (folder / 'diff').is_dir(), f'{made} {own}')


def e_recorded_drive(tmp: Path) -> None:
    claim = tmp / 'e' / 'claim'
    shutil.copytree(RECORDED, claim)
    for side in common.SIDES:
        (claim / side / 'clock.md').rename(claim / side / 'recorded-clock.md')
    for name in ('both', 'only-baseline'):
        for side in common.SIDES:
            if name == 'both' or side == 'baseline':
                subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i',
                                'color=c=red:s=4x4', '-frames:v', '1', claim / side / f'{name}.png'],
                               check=True)
    notes = io.StringIO()
    with redirect_stdout(notes):
        code = verify.cmd_diff(claim)
    shown = sorted(p.name for p in (claim / 'diff').iterdir())
    check('E4 diff writes each still both sides took, and rows.md the same text the drive recorded',
          code == 0 and notes.getvalue() == f'{claim / "diff"}\n'
          and shown == ['both.png', 'rows.md']
          and (claim / 'diff' / 'rows.md').read_text() == (RECORDED / 'diff' / 'rows.md').read_text(),
          f'{shown} {notes.getvalue()}')
    same = []
    for side in common.SIDES:

        #marks.json is the driver's marks, rebuilt from the recorded clock.md so the order matches...
        marks = json.loads((RECORDED / side / 'marks.json').read_text())
        drive = type('Drive', (), {
            'marks': [(t, text) for t, text in marks], 'out': RECORDED / side, 'side': side,
            'scenario': {'name': 'background-work'},
            'setup': json.loads((RECORDED / side / 'setup.json').read_text())})()
        same.append(session.clock(drive) == (RECORDED / side / 'clock.md').read_text())
    check('E5 the clock prints a recorded drive\'s marks, hooks and log rows as it was recorded',
          same == [True, True], str(same))
    check('E5 the recorded drive holds every key its recorders wrote, with each local path, session '
          'id and transcript path as a fixed placeholder and no local path in any value',
          local_paths(RECORDED) == [] and placeholders_hold(RECORDED), str(local_paths(RECORDED)))
    planted = tmp / 'e' / 'planted'
    shutil.copytree(RECORDED, planted)
    hooks = planted / 'baseline' / 'hooks.jsonl'
    rows  = hooks.read_text().splitlines()
    caught = {}
    for what, key, value in (('a path', 'transcript_path', '/tmp/x'), ('a dash-encoded path',
                             'prompt', 'run in -Users-someone-x'), ('a home path', 'cwd', '~/x'),
                             ('a path inside a value', 'prompt', 'see /Volumes/x/y')):
        row = json.loads(rows[0])
        hooks.write_text(json.dumps({**row, key: value}) + '\n')
        caught[what] = local_paths(planted) != []
    hooks.write_text('\n'.join(rows) + '\n')
    check('E5 the path check fails on a planted /tmp path, a dash-encoded path, a ~ path and a '
          'path inside a value, and passes on the recording',
          all(caught.values()) and local_paths(planted) == [], str(caught))


# ── stop and the hooks ────────────────────────────────────────────────────


def k_stop_only_what_was_started(tmp: Path) -> None:
    claim = tmp / 'k'
    claim.mkdir()
    proc = subprocess.Popen(['/bin/sleep', '30'])
    check('K1 a pid the claim never recorded is left running',
          not common.stop(claim, proc.pid) and proc.poll() is None)
    common.record(claim, 'procs', {'pid': proc.pid, 'exe': '/usr/bin/true'})
    check('K2 a recorded pid running another executable is left running',
          not common.stop(claim, proc.pid) and proc.poll() is None)
    (claim / 'started.json').unlink()
    common.record(claim, 'procs', {'pid': proc.pid, 'exe': '/bin/sleep'})
    stopped = common.stop(claim, proc.pid)
    proc.wait(timeout=10)
    check('K2 a recorded pid still running what it started is stopped', stopped)


def h_hooks(tmp: Path) -> None:
    script = HERE.parent / 'scripts' / 'verify.py'
    env    = dict(os.environ, VERIFY_HOOKS=str(tmp / 'hooks.jsonl'))
    big    = {'hook_event_name': 'PreToolUse', 'tool_name': 'Bash', 'secret_field': 'x',
              'tool_input': {'command': 'y' * 500}, 'mcp_server_name': 'form'}
    a = subprocess.run([sys.executable, script, 'observe'], input=json.dumps(big), env=env,
                       capture_output=True, text=True)
    b = subprocess.run([sys.executable, script, 'observe'], input='not json', env=env,
                       capture_output=True, text=True)
    row = json.loads((tmp / 'hooks.jsonl').read_text().splitlines()[0])
    check('H1 the observer prints nothing and exits 0, also on input it cannot read',
          (a.returncode, a.stdout, b.returncode, b.stdout) == (0, '', 0, ''))
    check('H2 the observer keeps the named fields, a form\'s server among them, and cuts a tool '
          'input to 160 characters',
          row['tool_name'] == 'Bash' and row.get('mcp_server_name') == 'form'
          and 'secret_field' not in row and len(row['tool_input']) == 160,
          str(row)[:120])
    flag = tmp / 'once'
    first, second = io.StringIO(), io.StringIO()
    with redirect_stdout(first):
        verify.continue_once(flag, 'go on')
    with redirect_stdout(second):
        verify.continue_once(flag, 'go on')
    check('H3 continue-once blocks the first Stop with its reason and lets the next one go',
          json.loads(first.getvalue()) == {'decision': 'block', 'reason': 'go on'}
          and second.getvalue() == '')


def main() -> int:
    """run each case in one temporary folder, print the tally, and return how many checks failed."""
    cases = (i1_settings_run_the_revisions_hooks, i2_the_session_carries_none_of_ours,
             i3_leftovers_never_the_installed_app, i4_only_this_claims_transcripts,
             i5_doctor_keeps_the_real_log_out, i6_the_app_gets_the_claims_log,
             i7_the_session_is_isolated, i8_a_closed_side_opens_for_its_next_drive,
             i9_an_app_that_stays_open_is_reported, i10_a_form_scenario_adds_only_the_form_server,
             i11_the_hooks_run_this_verify_py,
             p_host_against_a_fake, f_the_form_server, c_the_clock, r_one_copy_per_version,
             d_docs_name_only_what_the_app_reads,
             b1_swiftc_line_is_build_sh, b2_newest_claude, b3_b4_export,
             b5_the_mac_helper_compiles_the_real_source, s_scenarios,
             k_stop_only_what_was_started, h_hooks, e_commands,
             e_claim_from_a_linked_worktree, e_recorded_drive)
    with tempfile.TemporaryDirectory() as t:
        for case in cases:
            case(Path(t).resolve())
    failed = RESULTS.count(False)
    print(f'{len(RESULTS) - failed}/{len(RESULTS)} passed')
    return failed


if __name__ == '__main__':
    sys.exit(main())
