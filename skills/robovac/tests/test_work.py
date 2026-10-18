#!/usr/bin/env python3
"""
test_work — feeds runs.py the hook events of turns that leave background work running, ask the
person a question or a form, or end with no Stop hook, in the orders the probes of 2026-10-17
recorded, and checks the robot is out exactly while the agent works and nothing waits on the person.

Run it with `python3 test_work.py`. It runs runs.py with ROBOVAC_RUNS pointing at a log in one
temporary folder, which it removes after. The exit code is the number of failed checks.

B1 to B9 keep a run going past its turn's Stop while background tasks run: B1 a shell the Stop
names, ended by its task notification's turn, B2 an agent, B3 tasks no longer running, B4 a shell
seen starting when the Stop names none, B5 and B6 an Esc, which a shell outlives and an agent does
not, B7 an API error, B8 a close, B9 twelve silent hours, a work row counting as heard. B10 starts a
turn at a prompt while the work keeps the robot out, B11 lets the main agent's call past such a Stop
open the turn again and a subagent's not, B12 sends a wait an Esc ends out to a shell still running,
and B13 starts no task at a foreground agent's or shell's result. Q1 and Q2 dock at a question or a
form as it opens; Q3 to Q8 let a background agent's wait give way to the turn's own work and
outrank the background work once the turn ends; Q9 sends the main agent's answer out past a
background prompt, Q10 lets a Stop past a prompt of no running agent go out to the shell, and Q11
one past a notice or a form. X1 to X6 end a turn whose last reply ended it with no Stop hook after
it: at the next prompt at once, else six seconds on, never while a tool or a think runs, never at
its own Stop, and never a turn already closed with background work going on.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from harness import ESC, Log, call, check, iso, main, notice, reply, running, said, transcript



BG    = {'command': 'sleep 20; echo done', 'run_in_background': True}
ASK   = {'questions': [{'question': 'Proceed?', 'options': [{'label': 'yes'}, {'label': 'no'}]}]}
BASH  = {'command': 'touch a', 'description': 'make a'}
OTHER = {'command': 'touch b', 'description': 'make b'}
WAIT  = ['start', 'ask', 'end:waiting on you']


def live(log: Log) -> list:
    """the sessions `runs.py live` shows out, with their lines."""
    return [(r['session'], r.get('say')) for r in json.loads(log.run('live', '--json'))]


def shell(log: Log, task: str, sid: str = 'a', **fields) -> None:
    """a background shell started: its call's result names its task."""
    log.hook('PostToolUse', sid=sid, tool_name='Bash', tool_input=BG,
             tool_response={'stdout': '', 'backgroundTaskId': task}, **fields)


def agent(log: Log, task: str, sid: str = 'a', **fields) -> None:
    """a background agent launched: its Agent call returns at once, naming it."""
    log.hook('PostToolUse', sid=sid, tool_name='Agent', tool_input={'run_in_background': True},
             tool_response={'isAsync': True, 'status': 'async_launched', 'agentId': task}, **fields)


# ── background work keeps it out ────────────────────────────────────────────


def b1_a_background_shell_outlives_the_turn(tmp: Path) -> None:
    log = Log(tmp, 'b1')
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.run('say', 'binning leftovers', sid='a')
    shell(log, 'b1')
    log.hook('Stop', background_tasks=running(('b1', 'shell')))
    kept = log.events(), live(log)
    log.hook('UserPromptSubmit', prompt=notice('b1'))
    told = log.events(), live(log)
    log.hook('Stop', background_tasks=[])
    check('B1 a turn ending with a background shell running stays out, its task notification\'s turn '
          'goes on with its line, and that turn\'s Stop with nothing running docks it',
          kept == (['start', 'say'], [('a', 'binning leftovers')])
          and told == (['start', 'say', 'start'], [('a', 'binning leftovers')])
          and log.events() == ['start', 'say', 'start', 'end:finished']
          and log.work() == [(True, []), (True, [('b1', 'shell')]), (False, [('b1', 'shell')]),
                             (True, [])],
          f'{kept} {told} {log.events()} {log.work()}')


def b2_a_background_agent_outlives_the_turn(tmp: Path) -> None:
    log = Log(tmp, 'b2')
    log.hook('UserPromptSubmit', prompt='/robovac')
    agent(log, 'ag1')
    log.hook('PreToolUse', tool_name='Bash', tool_input=BASH, agent_id='ag1')
    log.hook('Stop', background_tasks=running(('ag1', 'subagent')))
    log.hook('PostToolUse', tool_name='Bash', tool_input=BASH, agent_id='ag1')
    log.hook('PostToolBatch', tool_calls=[], agent_id='ag1')
    kept = log.events()
    log.hook('UserPromptSubmit', prompt=notice('ag1'))
    log.hook('Stop', background_tasks=[])
    check('B2 a turn ending with a background agent running stays out while the agent works, and '
          'docks at the end of the turn its notification starts',
          kept == ['start'] and log.events() == ['start', 'start', 'end:finished'],
          f'{kept} {log.events()}')


def b3_tasks_no_longer_running(tmp: Path) -> None:
    log = Log(tmp, 'b3')
    log.hook('UserPromptSubmit', prompt='/robovac')
    shell(log, 'b1')
    log.hook('Stop', background_tasks=[{'id': 'b1', 'type': 'shell', 'status': 'completed'}])
    check('B3 a Stop naming only tasks that are no longer running docks the robot',
          log.events() == ['start', 'end:finished'], str(log.events()))


def b4_a_stop_that_names_no_tasks(tmp: Path) -> None:
    log = Log(tmp, 'b4')
    log.hook('UserPromptSubmit', prompt='/robovac')
    shell(log, 'b1')
    log.hook('Stop')
    log.hook('UserPromptSubmit', sid='b', prompt='/robovac')
    log.hook('Stop', sid='b')
    check('B4 a Stop with no background_tasks keeps the shells the session was seen starting, and '
          'with none seen it docks', log.events() == ['start'] and log.events('b') == ['start', 'end:finished'],
          f'{log.events()} {log.events("b")}')


def b5_a_shell_outlives_an_esc(tmp: Path) -> None:
    log = Log(tmp, 'b5')
    t = transcript(log.dir / 't.jsonl', said('/robovac'))
    log.hook('UserPromptSubmit', prompt='/robovac', transcript_path=str(t))
    shell(log, 's1', transcript_path=str(t))
    agent(log, 'ag1', transcript_path=str(t))
    transcript(t, said('[Request interrupted by user for tool use]'))
    shown = live(log)
    log.hook('Notification', notification_type='idle_prompt', transcript_path=str(t))
    log.hook('UserPromptSubmit', prompt=notice('s1'), transcript_path=str(t))
    told = log.events()
    log.hook('Stop', background_tasks=[], transcript_path=str(t))
    check('B5 an Esc leaves the robot out while a background shell it outlives still runs, the next '
          'hook drops the agent it kills, and the shell\'s notification turn docks it at its Stop',
          shown == [('a', None)] and told == ['start', 'start']
          and log.events() == ['start', 'start', 'end:finished']
          and log.work()[3:] == [(False, [('s1', 'shell')]), (True, [])],
          f'{shown} {told} {log.events()} {log.work()}')


def b6_an_esc_kills_a_background_agent(tmp: Path) -> None:
    log = Log(tmp, 'b6')
    t = transcript(log.dir / 't.jsonl', said('/robovac'))
    log.hook('UserPromptSubmit', prompt='/robovac', transcript_path=str(t))
    agent(log, 'ag1', transcript_path=str(t))
    transcript(t, said(ESC))
    shown = live(log)
    log.hook('UserPromptSubmit', prompt='go on', transcript_path=str(t))
    check('B6 an Esc with only a background agent running docks the robot, since the Esc stops the '
          'agent too', shown == [] and log.events() == ['start', 'end:interrupted', 'start'],
          f'{shown} {log.events()}')


def b7_an_api_error_with_a_shell_running(tmp: Path) -> None:
    log = Log(tmp, 'b7')
    log.hook('UserPromptSubmit', prompt='/robovac')
    shell(log, 's1')
    log.hook('StopFailure', error='overloaded')
    kept = log.events()
    log.hook('UserPromptSubmit', sid='b', prompt='/robovac')
    log.hook('StopFailure', sid='b', error='overloaded')
    check('B7 an API error ending the turn leaves the robot out while a background shell runs, and '
          'with none it docks naming the error', kept == ['start']
          and log.events('b') == ['start', 'end:error: overloaded'], f'{kept} {log.events("b")}')


def b8_a_close_ends_background_work(tmp: Path) -> None:
    log = Log(tmp, 'b8')
    log.hook('UserPromptSubmit', prompt='/robovac')
    shell(log, 's1')
    log.hook('Stop', background_tasks=running(('s1', 'shell')))
    log.hook('SessionEnd')
    check('B8 a session closing while its background work runs docks the robot as closed',
          log.events() == ['start', 'end:session closed'], str(log.events()))


def b9_background_work_goes_quiet(tmp: Path) -> None:
    log = Log(tmp, 'b9')
    old = time.time() - 13 * 3600
    log.path.write_text(json.dumps({'t': old, 'session': 'a', 'project': 'p', 'event': 'start',
                                    'via': 'prompt'}) + '\n'
                        + json.dumps({'t': old + 5, 'session': 'a', 'project': 'p', 'event': 'work',
                                      'turn': False, 'tasks': {'s1': 'shell'}}) + '\n')
    with log.path.open('a') as f:
        f.write(json.dumps({'t': old, 'session': 'b', 'project': 'p', 'event': 'start', 'via': 'prompt'})
                + '\n' + json.dumps({'t': old + 7200, 'session': 'b', 'project': 'p', 'event': 'work',
                                      'turn': False, 'tasks': {'s1': 'shell'}}) + '\n')
    gone = live(log)
    log.hook('UserPromptSubmit', prompt='go on')
    check('B9 a run kept out by background work and unheard from for twelve hours goes quiet, and '
          'its work row counts as hearing from it', gone == [('b', None)]
          and log.events() == ['start', 'end:went quiet', 'start'], f'{gone} {log.events()}')


def b10_a_prompt_while_the_work_runs(tmp: Path) -> None:
    log = Log(tmp, 'b10')
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.run('say', 'binning leftovers', sid='a')
    shell(log, 's1')
    log.hook('Stop', background_tasks=running(('s1', 'shell')))
    log.hook('UserPromptSubmit', prompt='and the README?')
    turned = log.events(), log.work()[-1], live(log)
    log.hook('Stop', background_tasks=running(('s1', 'shell')))
    check('B10 a prompt while a background shell keeps the robot out starts a turn that keeps its '
          'line and the shell, and its Stop with the shell still running leaves it out',
          turned == (['start', 'say', 'start'], (True, [('s1', 'shell')]), [('a', 'binning leftovers')])
          and log.events() == turned[0] and log.work()[-1] == (False, [('s1', 'shell')]),
          f'{turned} {log.events()} {log.work()}')


def b11_a_main_call_past_a_stop_with_work_running(tmp: Path) -> None:
    log = Log(tmp, 'b11')
    t = transcript(log.dir / 't.jsonl', said('/robovac'))
    log.hook('UserPromptSubmit', prompt='/robovac', transcript_path=str(t))
    shell(log, 's1', transcript_path=str(t))
    transcript(t, reply('launched', time.time() - 60))
    log.hook('Stop', background_tasks=running(('s1', 'shell')), transcript_path=str(t))
    log.hook('PreToolUse', tool_name='Bash', tool_input=BASH, agent_id='ag1', transcript_path=str(t))
    closed = log.work()[-1]
    log.hook('PreToolUse', tool_name='Bash', tool_input=BASH, transcript_path=str(t))
    reopened = log.work()[-1]
    transcript(t, reply('done', time.time() - 10))
    log.hook('Notification', notification_type='idle_prompt', transcript_path=str(t))
    check('B11 a main-agent call past a Stop that left a shell running opens the turn again, a '
          'subagent\'s call does not, and a reply that ends the reopened turn with no Stop leaves '
          'the robot out with the shell', closed == (False, [('s1', 'shell')])
          and reopened == (True, [('s1', 'shell')]) and log.events() == ['start']
          and log.work()[-1] == (False, [('s1', 'shell')]), f'{closed} {reopened} {log.events()} {log.work()}')


def b12_an_esc_at_a_wait_with_a_shell_running(tmp: Path) -> None:
    log = Log(tmp, 'b12')
    t = transcript(log.dir / 't.jsonl', said('/robovac'))
    log.hook('UserPromptSubmit', prompt='/robovac', transcript_path=str(t))
    shell(log, 's1', transcript_path=str(t))
    log.hook('PermissionRequest', tool_name='Bash', tool_input=BASH, transcript_path=str(t))
    log.hook('Notification', notification_type='permission_prompt', transcript_path=str(t))
    docked = log.events()
    transcript(t, said('[Request interrupted by user for tool use]'))
    log.hook('Notification', notification_type='idle_prompt', transcript_path=str(t))
    check('B12 an Esc at the main agent\'s own wait, with a background shell running, sends the '
          'robot out to the shell', docked == WAIT and log.events() == WAIT + ['start']
          and log.work()[-1] == (False, [('s1', 'shell')]) and live(log) == [('a', None)],
          f'{docked} {log.events()} {log.work()}')



def b13_a_foreground_agents_result_starts_no_task(tmp: Path) -> None:
    log = Log(tmp, 'b13')
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.hook('PostToolUse', tool_name='Agent', tool_input={'prompt': 'look'},
             tool_response={'status': 'completed', 'agentId': 'fg1', 'content': []})
    log.hook('PostToolUse', tool_name='Bash', tool_input=BASH, tool_response={'stdout': 'ok'})
    log.hook('Stop')
    check('B13 a foreground agent\'s result, which names its agent, and a foreground shell\'s start no '
          'background task, so the turn\'s Stop docks the robot',
          log.events() == ['start', 'end:finished'] and log.work() == [(True, [])], f'{log.events()} {log.work()}')


# ── waits ───────────────────────────────────────────────────────────────────


def q1_a_question_docks_as_it_opens(tmp: Path) -> None:
    log = Log(tmp, 'q1')
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.hook('PreToolUse', tool_name='AskUserQuestion', tool_input=ASK)
    log.hook('PermissionRequest', tool_name='AskUserQuestion', tool_input=ASK)
    opened = log.events()
    log.hook('Notification', notification_type='permission_prompt')
    log.hook('PostToolUse', tool_name='AskUserQuestion', tool_input=dict(ASK, answers={'Proceed?': 'yes'}))
    check('Q1 a question docks the robot as it opens, before any notice, and its answer sends it out; '
          'the wait leaves the turn open, so it logs no work row', opened == WAIT
          and log.events() == WAIT + ['answered', 'start'] and log.work() == [(True, [])] * 2,
          f'{opened} {log.events()} {log.work()}')


def q2_a_form_docks_as_it_opens(tmp: Path) -> None:
    log = Log(tmp, 'q2')
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.hook('PreToolUse', tool_name='mcp__s__ask', tool_input={})
    log.hook('Elicitation', mcp_server_name='s', mode='form')
    opened = log.events()
    log.hook('ElicitationResult', mcp_server_name='s', mode='form', action='accept')
    check('Q2 an MCP form docks the robot as it opens, with no notice, and its result sends it out',
          opened == WAIT and log.events() == WAIT + ['answered', 'start'], f'{opened} {log.events()}')


def q3_a_background_agents_question(tmp: Path) -> None:
    log = Log(tmp, 'q3')
    log.hook('UserPromptSubmit', prompt='/robovac')
    agent(log, 'ag1')
    log.hook('PermissionRequest', tool_name='AskUserQuestion', tool_input=ASK, agent_id='ag1')
    log.hook('Notification', notification_type='permission_prompt')
    working = log.events()
    log.hook('Stop', background_tasks=running(('ag1', 'subagent')))
    stopped = log.events()
    log.hook('PostToolUse', tool_name='AskUserQuestion', tool_input=dict(ASK, answers={'Proceed?': 'yes'}),
             agent_id='ag1')
    check('Q3 a background agent\'s question leaves the robot out while the turn works, docks it '
          'once the turn stops, and its answer sends it out to the agent\'s work',
          working == ['start', 'ask'] and stopped == working + ['end:waiting on you']
          and log.events() == stopped + ['answered', 'start'], f'{working} {stopped} {log.events()}')


def q4_a_background_agents_prompt(tmp: Path) -> None:
    log = Log(tmp, 'q4')
    log.hook('UserPromptSubmit', prompt='/robovac')
    agent(log, 'ag1')
    log.hook('PermissionRequest', tool_name='Bash', tool_input=BASH, agent_id='ag1')
    log.hook('Notification', notification_type='permission_prompt')
    working = log.events()
    log.hook('Stop', background_tasks=running(('ag1', 'subagent')))
    log.hook('PostToolUse', tool_name='Bash', tool_input=BASH, agent_id='ag1')
    out = log.events()
    log.hook('UserPromptSubmit', prompt=notice('ag1'))
    log.hook('Stop', background_tasks=[])
    check('Q4 a known background agent\'s prompt docks nothing while the turn works, docks the robot '
          'at the turn\'s Stop, and its approval sends it out until the agent\'s notification turn ends',
          working == ['start', 'ask'] and out == working + ['end:waiting on you', 'answered', 'start']
          and log.events() == out + ['start', 'end:finished'], f'{working} {out} {log.events()}')


def q5_an_unknown_background_agents_prompt(tmp: Path) -> None:
    log = Log(tmp, 'q5')
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.hook('PermissionRequest', tool_name='Bash', tool_input=BASH, agent_id='bg1')
    log.hook('Notification', notification_type='permission_prompt')
    log.hook('PreToolUse', tool_name='Bash', tool_input={'command': 'sleep 2'})
    out = log.events()
    log.hook('Stop', background_tasks=running(('bg1', 'subagent')))
    stopped = log.events()
    log.hook('PostToolUse', tool_name='Bash', tool_input=BASH, agent_id='bg1')
    check('Q5 an unknown subagent\'s prompt docks at its notice, the main agent\'s next call sends '
          'the robot out past it, the turn\'s Stop docks it again while the prompt waits, and the '
          'approval sends it out', out == WAIT + ['start'] and stopped == out + ['end:waiting on you']
          and log.events() == stopped + ['answered', 'start'], f'{out} {stopped} {log.events()}')


def q6_a_stop_while_docked_on_a_background_prompt(tmp: Path) -> None:
    log = Log(tmp, 'q6')
    for sid in 'ab':
        log.hook('UserPromptSubmit', sid=sid, prompt='/robovac')
        log.hook('PermissionRequest', sid=sid, tool_name='Bash', tool_input=BASH, agent_id='bg1')
        log.hook('Notification', sid=sid, notification_type='permission_prompt')
    log.hook('Stop', background_tasks=running(('bg1', 'subagent')))
    log.hook('Stop', sid='b', background_tasks=running(('bg1', 'subagent')))
    stopped = log.events(), log.events('b')
    log.hook('PostToolUse', tool_name='Bash', tool_input=BASH, agent_id='bg1')
    log.hook('PostToolBatch', sid='b', tool_calls=[], agent_id='bg1')
    check('Q6 a turn that stops while docked on its background agent\'s prompt stays docked waiting, '
          'and the answer, approved or denied, sends the robot out to the agent\'s work',
          stopped == (WAIT, WAIT) and log.events() == WAIT + ['answered', 'start']
          and log.events('b') == WAIT + ['answered', 'start'], f'{stopped} {log.events()} {log.events("b")}')


def q7_a_prompt_after_the_turn(tmp: Path) -> None:
    log = Log(tmp, 'q7')
    log.hook('UserPromptSubmit', prompt='/robovac')
    agent(log, 'ag1')
    log.hook('Stop', background_tasks=running(('ag1', 'subagent')))
    log.hook('PermissionRequest', tool_name='Bash', tool_input=BASH, agent_id='ag1')
    asked = log.events()
    log.hook('Notification', notification_type='permission_prompt')
    docked = log.events()
    log.hook('PostToolUse', tool_name='Bash', tool_input=BASH, agent_id='ag1')
    check('Q7 once the turn has stopped, a background agent\'s prompt docks the robot at its notice, '
          'not before, and its approval sends it out', asked == ['start', 'ask']
          and docked == asked + ['end:waiting on you'] and log.events() == docked + ['answered', 'start'],
          f'{asked} {docked} {log.events()}')


def q8_a_new_turn_outranks_a_background_prompt(tmp: Path) -> None:
    log = Log(tmp, 'q8')
    log.hook('UserPromptSubmit', prompt='/robovac')
    agent(log, 'ag1')
    log.hook('Stop', background_tasks=running(('ag1', 'subagent')))
    log.hook('PermissionRequest', tool_name='Bash', tool_input=BASH, agent_id='ag1')
    log.hook('Notification', notification_type='permission_prompt')
    log.hook('UserPromptSubmit', prompt='what is it doing?')
    turned = log.events()
    log.hook('Stop', background_tasks=running(('ag1', 'subagent')))
    check('Q8 a new turn sends the robot out past a background agent\'s waiting prompt, and its Stop '
          'docks the robot again while the prompt still waits',
          turned == ['start', 'ask', 'end:waiting on you', 'start']
          and log.events() == turned + ['end:waiting on you'], f'{turned} {log.events()}')



def q9_the_main_agents_answer_beside_a_background_prompt(tmp: Path) -> None:
    log = Log(tmp, 'q9')
    log.hook('UserPromptSubmit', prompt='/robovac')
    agent(log, 'ag1')
    log.hook('PermissionRequest', tool_name='Bash', tool_input=OTHER, agent_id='ag1')
    log.hook('PermissionRequest', tool_name='Bash', tool_input=BASH)
    log.hook('Notification', notification_type='permission_prompt')
    docked = log.events()
    log.hook('PostToolUse', tool_name='Bash', tool_input=BASH)
    check('Q9 the main agent\'s approved prompt sends the robot out past a known background agent\'s '
          'prompt still open, which holds nothing while the turn works',
          docked == ['start', 'ask', 'ask', 'end:waiting on you']
          and log.events() == docked + ['answered', 'start'], f'{docked} {log.events()}')


def q10_a_stop_past_a_prompt_of_no_running_agent(tmp: Path) -> None:
    log = Log(tmp, 'q10')
    log.hook('UserPromptSubmit', prompt='/robovac')
    shell(log, 's1')
    log.hook('PermissionRequest', tool_name='Bash', tool_input=BASH, agent_id='bg1')
    log.hook('Notification', notification_type='permission_prompt')
    docked = log.events()
    log.hook('Stop', background_tasks=running(('s1', 'shell')))
    check('Q10 a Stop while docked on the prompt of an agent its list no longer names sends the '
          'robot out to the shell still running', docked == WAIT
          and log.events() == WAIT + ['start'] and log.work()[-1] == (False, [('s1', 'shell')]),
          f'{docked} {log.events()} {log.work()}')



def q11_a_stop_while_docked_on_a_notice_or_a_form(tmp: Path) -> None:
    log = Log(tmp, 'q11')
    for sid in 'ab':
        log.hook('UserPromptSubmit', sid=sid, prompt='/robovac')
        shell(log, 's1', sid=sid)
    log.hook('Notification', notification_type='permission_prompt')
    log.hook('Elicitation', sid='b', mcp_server_name='s', mode='form')
    for sid in 'ab':
        log.hook('Stop', sid=sid, background_tasks=running(('s1', 'shell')))
    check('Q11 a Stop while docked on a notice or a form, which name no agent, so none left running, '
          'ends the wait and goes out to the shell still running',
          log.events() == WAIT + ['start'] and log.events('b') == WAIT + ['start'],
          f'{log.events()} {log.events("b")}')


# ── a turn that ends with no Stop hook ──────────────────────────────────────


def x1_a_reply_with_no_stop_then_a_prompt(tmp: Path) -> None:
    log = Log(tmp, 'x1')
    t = transcript(log.dir / 't.jsonl', said('/robovac'))
    log.hook('UserPromptSubmit', prompt='/robovac', transcript_path=str(t))
    replied = time.time() - 2
    transcript(t, reply('done', replied))
    log.hook('UserPromptSubmit', prompt='next', transcript_path=str(t))
    ends = [r['t'] for r in log.rows() if r['event'] == 'end']
    check('X1 a reply that ended its turn with no Stop hook after it ends the run at the reply, '
          'interrupted, once the next prompt arrives, however soon',
          log.events() == ['start', 'end:interrupted', 'start'] and len(ends) == 1
          and abs(ends[0] - replied) < 0.002, f'{log.events()} {ends} {replied}')


def x2_a_reply_with_no_stop_six_seconds_on(tmp: Path) -> None:
    log = Log(tmp, 'x2')
    seen = {}
    for sid, age in (('a', 5), ('b', 7)):
        t = transcript(log.dir / f'{sid}.jsonl', said('/robovac'))
        log.hook('UserPromptSubmit', sid=sid, prompt='/robovac', transcript_path=str(t))
        transcript(t, reply('done', time.time() - age))
        seen[sid] = [s for s, _ in live(log) if s == sid]
        log.hook('SessionEnd', sid=sid, transcript_path=str(t))
    check('X2 such a reply leaves the run out for six seconds, then ends it interrupted, in live and '
          'at the next hook of any kind', seen == {'a': ['a'], 'b': []}
          and log.events('a') == ['start', 'end:session closed']
          and log.events('b') == ['start', 'end:interrupted', 'end:session closed'],
          f'{seen} {log.events("a")} {log.events("b")}')


def x3_a_reply_and_its_stop(tmp: Path) -> None:
    log = Log(tmp, 'x3')
    t = transcript(log.dir / 't.jsonl', said('/robovac'))
    log.hook('UserPromptSubmit', prompt='/robovac', transcript_path=str(t))
    transcript(t, reply('done', time.time() - 30))
    log.hook('Stop', transcript_path=str(t))
    check('X3 a turn\'s own Stop hook ends it finished, however long after the reply it runs',
          log.events() == ['start', 'end:finished'], str(log.events()))


def x4_a_long_silent_tool_or_think(tmp: Path) -> None:
    log = Log(tmp, 'x4')
    t = transcript(log.dir / 'a.jsonl', said('/robovac'))
    log.hook('UserPromptSubmit', prompt='/robovac', transcript_path=str(t))
    transcript(t, reply('first, a look round', time.time() - 3600, stop='tool_use'),
               call('Bash', time.time() - 3600))
    u = transcript(log.dir / 'b.jsonl', said('/robovac'))
    log.hook('UserPromptSubmit', sid='b', prompt='/robovac', transcript_path=str(u))
    transcript(u, reply('done', time.time() - 3600), said('now think hard about the next one'))
    log.hook('UserPromptSubmit', sid='b', prompt='now think hard about the next one',
             transcript_path=str(u))
    shown = sorted(s for s, _ in live(log))
    log.hook('Notification', notification_type='idle_prompt', transcript_path=str(t))
    log.hook('Notification', sid='b', notification_type='idle_prompt', transcript_path=str(u))
    check('X4 a turn whose last line is a tool call an hour old, or a new turn thinking after an old '
          'reply, stays out: a long build or a long think writes nothing until it ends',
          shown == ['a', 'b'] and log.events() == ['start']
          and log.events('b') == ['start', 'end:interrupted', 'start'],
          f'{shown} {log.events()} {log.events("b")}')


def x5_a_turn_closed_with_background_work(tmp: Path) -> None:
    log = Log(tmp, 'x5')
    t = transcript(log.dir / 't.jsonl', said('/robovac'))
    log.hook('UserPromptSubmit', prompt='/robovac', transcript_path=str(t))
    shell(log, 's1', transcript_path=str(t))
    transcript(t, reply('launched', time.time() - 60))
    log.hook('Stop', background_tasks=running(('s1', 'shell')), transcript_path=str(t))
    u = transcript(log.dir / 'u.jsonl', said('/robovac'))
    log.hook('UserPromptSubmit', sid='b', prompt='/robovac', transcript_path=str(u))
    agent(log, 'ag1', sid='b', transcript_path=str(u))
    transcript(u, reply('launched', time.time() - 60))
    log.hook('Stop', sid='b', background_tasks=running(('ag1', 'subagent')), transcript_path=str(u))
    shown = live(log)
    log.hook('Notification', notification_type='idle_prompt', transcript_path=str(t))
    log.hook('Notification', sid='b', notification_type='idle_prompt', transcript_path=str(u))
    check('X5 a turn closed with background work still running, a shell or an agent, is never ended '
          'by its last reply', shown == [('a', None), ('b', None)] and log.events() == ['start']
          and log.events('b') == ['start'], f'{shown} {log.events()} {log.events("b")}')


def x6_an_esc_line_after_the_reply(tmp: Path) -> None:
    log = Log(tmp, 'x6')
    t = transcript(log.dir / 't.jsonl', said('/robovac'))
    log.hook('UserPromptSubmit', prompt='/robovac', transcript_path=str(t))
    pressed = time.time() - 2
    transcript(t, reply('done', pressed - 1), dict(said(ESC), timestamp=iso(pressed)))
    log.hook('UserPromptSubmit', prompt='next', transcript_path=str(t))
    ends = [r['t'] for r in log.rows() if r['event'] == 'end']
    check('X6 an Esc line after a reply ends the run at the Esc, not the reply',
          log.events() == ['start', 'end:interrupted', 'start'] and len(ends) == 1
          and abs(ends[0] - pressed) < 0.002, f'{log.events()} {ends} {pressed}')


if __name__ == '__main__':
    raise SystemExit(main((b1_a_background_shell_outlives_the_turn, b2_a_background_agent_outlives_the_turn,
                           b3_tasks_no_longer_running, b4_a_stop_that_names_no_tasks,
                           b5_a_shell_outlives_an_esc, b6_an_esc_kills_a_background_agent,
                           b7_an_api_error_with_a_shell_running, b8_a_close_ends_background_work,
                           b9_background_work_goes_quiet, b10_a_prompt_while_the_work_runs,
                           b11_a_main_call_past_a_stop_with_work_running,
                           b12_an_esc_at_a_wait_with_a_shell_running,
                           b13_a_foreground_agents_result_starts_no_task, q1_a_question_docks_as_it_opens,
                           q2_a_form_docks_as_it_opens, q3_a_background_agents_question,
                           q4_a_background_agents_prompt, q5_an_unknown_background_agents_prompt,
                           q6_a_stop_while_docked_on_a_background_prompt, q7_a_prompt_after_the_turn,
                           q8_a_new_turn_outranks_a_background_prompt,
                           q9_the_main_agents_answer_beside_a_background_prompt,
                           q10_a_stop_past_a_prompt_of_no_running_agent,
                           q11_a_stop_while_docked_on_a_notice_or_a_form,
                           x1_a_reply_with_no_stop_then_a_prompt, x2_a_reply_with_no_stop_six_seconds_on,
                           x3_a_reply_and_its_stop, x4_a_long_silent_tool_or_think,
                           x5_a_turn_closed_with_background_work, x6_an_esc_line_after_the_reply)))
