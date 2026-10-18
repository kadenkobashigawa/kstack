#!/usr/bin/env python3
"""
test_waits — feeds runs.py the hook events of turns that wait on the person, in every order the
probes saw them arrive, and checks that the robot docks while any ask is open after a waiting
notice and goes out when the last one is answered.

Run it with `python3 test_waits.py`. It runs runs.py with ROBOVAC_RUNS pointing at a log in one
temporary folder, which it removes after. The exit code is the number of failed checks.

T1 to T3 dock a turn at a permission prompt, a form or a link notice, and leave it going on any
other notice; T4 keeps a turn a Stop hook continues going, and T5 and T10 keep an Esc's dock. T6
logs no ask outside a run, and T7 holds that hooks.json sends runs.py every event this needs. T8
and T11 carry the run's line through a wait. T9, T12 to T16 and T19 to T31 close each ask on its
own call's result, its agent's batch, a subagent's interrupt line, a form's result or a notice's
closers, in the orders the probes recorded, and start the run when the last open ask closes. T17
and T18 hold a main agent's batch beside a subagent's prompt, T32 drops an Esc'd turn's asks at the
next start, T33 runs on settings that predate the newer hooks, T34 ends a wait on an error or a
close, and T35 keeps a command out of the log. T24 and T36 send the run out at the main agent's
call or batch while only subagents' prompts wait, and T37 lets such a prompt hold no later wait.
T38 lets an answer found at a turn's end, a prompt or a notice start no run of its own. T39 lets
nothing start a run an Esc ended while docked, T40 and T41 close one ask per result of two equal
prompts or two forms, T42 closes a notice at a form's result, and T43 reads a subagent's interrupt
line only past where its transcript stood at the ask. L7 starts one run from two answers landing at
once.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

from harness import ESC, HERE, SCRIPT, Log, check, main, said, transcript



BASH  = {'command': 'touch a', 'description': 'make a'}
OTHER = {'command': 'touch b', 'description': 'make b'}
WAIT  = ['start', 'ask', 'end:waiting on you']


def after(log: Log, sid: str = 'a') -> list[str]:
    """the session's events since its last wait docked it."""
    got = log.events(sid)
    cut = max((n for n, e in enumerate(got) if e == 'end:waiting on you'), default=-1)
    return got[cut + 1:]


def sub(t: Path, agent: str) -> Path:
    """where Claude Code keeps a subagent's own transcript beside its session's."""
    return t.with_suffix('') / 'subagents' / f'agent-{agent}.jsonl'


# ── docking ─────────────────────────────────────────────────────────────────


def t1_permission_prompt_docks_until_the_tool_runs(tmp: Path) -> None:
    log = Log(tmp, 't1')
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.hook('PreToolUse', tool_name='Bash', tool_input=BASH)
    log.hook('PermissionRequest', tool_name='Bash', tool_input=BASH)
    log.hook('Notification', notification_type='permission_prompt', message='Claude needs your permission')
    waiting = log.events()
    log.hook('PostToolUse', tool_name='Bash', tool_input=BASH)
    ran = log.events()
    log.hook('PostToolBatch', tool_calls=[])
    log.hook('Stop')
    ends = [r for r in log.rows() if r['event'] == 'end']
    check('T1 a turn waiting on a permission prompt docks, and the approved call\'s own result sends '
          'it out, before its batch', waiting == WAIT and ran == waiting + ['answered', 'start']
          and log.events() == ran + ['end:finished'] and not any('asker' in r for r in ends),
          f'{waiting} {ran} {log.events()}')


def t2_elicitation_waits_too(tmp: Path) -> None:
    log = Log(tmp, 't2')
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.hook('Notification', notification_type='elicitation_dialog')
    log.hook('UserPromptSubmit', sid='b', prompt='/robovac')
    log.hook('Notification', sid='b', notification_type='elicitation_url_dialog')
    check('T2 a turn waiting on an MCP form or link docks the same way',
          log.events() == WAIT and log.events('b') == WAIT, f'{log.events()} {log.events("b")}')


def t3_other_notifications_change_nothing(tmp: Path) -> None:
    log = Log(tmp, 't3')
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.hook('Notification', notification_type='idle_prompt')
    log.hook('Notification', notification_type='auth_success')
    log.hook('Stop')
    log.hook('Notification', notification_type='permission_prompt')
    check('T3 other notifications leave a run going, and a prompt with no run going logs nothing',
          log.events() == ['start', 'end:finished'], str(log.events()))


def t4_stop_hook_continuation_keeps_going(tmp: Path) -> None:
    log = Log(tmp, 't4')
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.hook('Stop', stop_hook_active=False)
    log.hook('PreToolUse', tool_name='Bash', tool_input={'command': 'echo second'})
    out = log.events()
    log.hook('PostToolBatch', tool_calls=[])
    log.hook('Stop', stop_hook_active=True)
    check('T4 a turn another Stop hook keeps going goes out again as its next tool starts',
          out == ['start', 'end:finished', 'start']
          and log.events() == ['start', 'end:finished', 'start', 'end:finished'], f'{out} {log.events()}')


def t5_tools_after_esc_stay_docked(tmp: Path) -> None:
    log = Log(tmp, 't5')
    t = transcript(log.dir / 't.jsonl', said('/robovac'))
    log.hook('UserPromptSubmit', prompt='/robovac', transcript_path=str(t))
    transcript(t, said('[Request interrupted by user for tool use]'))
    log.hook('PreToolUse', tool_name='Read', tool_input={}, transcript_path=str(t))
    log.hook('PostToolBatch', tool_calls=[], transcript_path=str(t))
    check('T5 a denied prompt or an Esc ends the run, and tool calls after it leave it docked',
          log.events() == ['start', 'end:interrupted'], str(log.events()))


def t6_tools_elsewhere_log_nothing(tmp: Path) -> None:
    log = Log(tmp, 't6')
    log.hook('UserPromptSubmit', sid='b', prompt='fix the bug')
    log.hook('PreToolUse', sid='b', tool_name='Bash', tool_input={})
    log.hook('PermissionRequest', sid='b', tool_name='Bash', tool_input={})
    log.hook('Elicitation', sid='b', mcp_server_name='s', mode='form')
    log.hook('Notification', sid='b', notification_type='permission_prompt')
    log.hook('PostToolUse', sid='b', tool_name='Bash', tool_input={})
    log.hook('PostToolBatch', sid='b', tool_calls=[])
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.hook('Stop')
    log.hook('PermissionRequest', tool_name='Bash', tool_input={}, agent_id='bg1')
    log.hook('Elicitation', mcp_server_name='s', mode='form')
    log.hook('SessionEnd')
    log.hook('PermissionRequest', tool_name='Bash', tool_input={})
    log.hook('PreToolUse', tool_name='Bash', tool_input={})
    log.hook('PostToolBatch', tool_calls=[])
    check('T6 tool calls, asks and forms in a session that never ran robovac, or with no run open '
          'or waiting, log nothing',
          log.events('b') == [] and log.events() == ['start', 'end:finished', 'end:session closed'],
          f'{log.events("b")} {log.events()}')


def t7_hooks_json_sends_every_event(tmp: Path) -> None:
    hooks = json.loads((HERE.parents[2] / 'hooks' / 'hooks.json').read_text())['hooks']
    sent = {ev: [e.get('matcher', '') for e in entries
                 if any('robovac/scripts/runs.py' in h['command'] for h in e['hooks'])]
            for ev, entries in hooks.items()}
    every = all(sent.get(ev) == [''] for ev in ('UserPromptSubmit', 'PreToolUse', 'PostToolUse',
                                                 'PostToolUseFailure', 'PostToolBatch',
                                                 'PermissionRequest', 'Elicitation',
                                                 'ElicitationResult', 'Stop', 'StopFailure',
                                                 'SessionEnd'))
    waits = sent.get('Notification', [])
    check('T7 hooks.json sends runs.py every tool call and result, every ask and form, and the '
          'three notifications that wait on you',
          every and len(waits) == 1 and all(re.fullmatch(waits[0], n) for n in
                                            ('permission_prompt', 'elicitation_dialog',
                                             'elicitation_url_dialog'))
          and not re.fullmatch(waits[0], 'idle_prompt'), str(sent))


def t8_a_run_going_on_keeps_its_line(tmp: Path) -> None:
    log = Log(tmp, 't8')
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.run('say', 'binning leftovers in skills/', sid='a')
    log.hook('Notification', notification_type='permission_prompt')
    log.hook('PostToolBatch', tool_calls=[])
    resumed = [r.get('say') for r in json.loads(log.run('live', '--json'))]
    log.hook('Stop')
    log.hook('PreToolUse', tool_name='Bash', tool_input={})
    continued = [r.get('say') for r in json.loads(log.run('live', '--json'))]
    log.hook('Stop')
    log.hook('UserPromptSubmit', prompt='next')
    fresh = [r.get('say') for r in json.loads(log.run('live', '--json'))]
    log.hook('Stop')
    log.hook('PreToolUse', tool_name='Bash', tool_input={})
    later = [r.get('say') for r in json.loads(log.run('live', '--json'))]
    check('T8 a run that goes on after a wait or a Stop hook keeps its line; a new turn starts blank',
          resumed == continued == ['binning leftovers in skills/'] and fresh == later == [None],
          f'{resumed} {continued} {fresh} {later}')


def t9_a_subagent_does_not_send_it_out(tmp: Path) -> None:
    log = Log(tmp, 't9')
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.hook('Notification', notification_type='permission_prompt')
    log.hook('PreToolUse', tool_name='Bash', tool_input={}, agent_id='bg1', agent_type='general-purpose')
    log.hook('PostToolBatch', tool_calls=[], agent_id='bg1', agent_type='general-purpose')
    waiting = log.events()
    log.hook('PostToolBatch', tool_calls=[])
    log.hook('UserPromptSubmit', sid='b', prompt='/robovac')
    log.hook('PermissionRequest', sid='b', tool_name='Bash', tool_input={})
    log.hook('Notification', sid='b', notification_type='permission_prompt')
    log.hook('PreToolUse', sid='b', tool_name='Bash', tool_input={}, agent_id='bg1')
    log.hook('PostToolBatch', sid='b', tool_calls=[], agent_id='bg1')
    asked = log.events('b')
    log.hook('PostToolBatch', sid='b', tool_calls=[])
    check('T9 a subagent\'s call or batch leaves a waiting turn docked; the main agent\'s batch sends '
          'it out', waiting == WAIT and log.events() == waiting + ['answered', 'start']
          and asked == WAIT and log.events('b') == asked + ['answered', 'start'],
          f'{waiting} {log.events()} {asked} {log.events("b")}')


def t10_the_last_end_decides(tmp: Path) -> None:
    log = Log(tmp, 't10')
    t = transcript(log.dir / 't.jsonl', said('/robovac'))
    log.hook('UserPromptSubmit', prompt='/robovac', transcript_path=str(t))
    transcript(t, said(ESC))
    log.hook('UserPromptSubmit', prompt='go on', transcript_path=str(t))
    log.hook('Stop', transcript_path=str(t))
    log.hook('PreToolUse', tool_name='Bash', tool_input={}, transcript_path=str(t))
    check('T10 an Esc in an earlier turn does not keep a later turn\'s robot in',
          log.events() == ['start', 'end:interrupted', 'start', 'end:finished', 'start'], str(log.events()))


def t11_a_line_given_while_waiting_is_kept(tmp: Path) -> None:
    log = Log(tmp, 't11')
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.hook('Notification', notification_type='permission_prompt')
    noted = log.run('say', 'binning leftovers in skills/', sid='a').strip()
    log.hook('PostToolBatch', tool_calls=[])
    shown = [r.get('say') for r in json.loads(log.run('live', '--json'))]
    check('T11 a line the agent gives in the tool a person approved is kept and shown as it goes on',
          noted == 'noted' and shown == ['binning leftovers in skills/'], f'{noted!r} {shown}')


# ── which call answers which ask ────────────────────────────────────────────


def t12_the_subagent_that_asked_sends_it_out(tmp: Path) -> None:
    log = Log(tmp, 't12')
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.run('say', 'binning leftovers in skills/', sid='a')
    log.hook('PreToolUse', tool_name='Agent', tool_input={})
    log.hook('PreToolUse', tool_name='Bash', tool_input=BASH, agent_id='fg1')
    log.hook('PermissionRequest', tool_name='Bash', tool_input=BASH, agent_id='fg1')
    log.hook('Notification', notification_type='permission_prompt')
    waiting = log.events()
    log.hook('PostToolUse', tool_name='Bash', tool_input=BASH, agent_id='fg1')
    shown = [r.get('say') for r in json.loads(log.run('live', '--json'))]
    log.hook('PostToolBatch', tool_calls=[], agent_id='fg1')
    log.hook('PostToolBatch', tool_calls=[])
    log.hook('Stop')
    check('T12 a foreground subagent\'s approved call sends a waiting turn out at its own result, '
          'with the run\'s line', waiting == ['start', 'say', 'ask', 'end:waiting on you']
          and log.events() == waiting + ['answered', 'start', 'end:finished']
          and shown == ['binning leftovers in skills/'], f'{waiting} {log.events()} {shown}')


def t13_another_subagent_leaves_a_subagents_wait_docked(tmp: Path) -> None:
    log = Log(tmp, 't13')
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.hook('PermissionRequest', tool_name='Bash', tool_input=BASH, agent_id='fg1')
    log.hook('Notification', notification_type='permission_prompt')
    log.hook('PreToolUse', tool_name='Bash', tool_input=BASH, agent_id='bg1')
    log.hook('PostToolUse', tool_name='Bash', tool_input=BASH, agent_id='bg1')
    log.hook('PostToolBatch', tool_calls=[], agent_id='bg1')
    waiting = log.events()
    log.hook('PostToolBatch', tool_calls=[], agent_id='fg1')
    check('T13 while a subagent waits on you, another subagent\'s calls, results and batches leave '
          'the turn docked, the same command included', waiting == WAIT
          and log.events() == waiting + ['answered', 'start'], f'{waiting} {log.events()}')


def t14_a_main_agents_open_ask_outranks_a_later_one(tmp: Path) -> None:
    log = Log(tmp, 't14')
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.hook('PermissionRequest', tool_name='Bash', tool_input=BASH)
    log.hook('PreToolUse', tool_name='Bash', tool_input=OTHER, agent_id='bg1')
    log.hook('PostToolBatch', tool_calls=[], agent_id='bg1')
    log.hook('PermissionRequest', tool_name='Bash', tool_input=OTHER, agent_id='bg1')
    log.hook('Notification', notification_type='permission_prompt')
    log.hook('PostToolUse', tool_name='Bash', tool_input=OTHER, agent_id='bg1')
    waiting = log.events()
    log.hook('PostToolUse', tool_name='Bash', tool_input=BASH)
    check('T14 a main agent waiting on its own prompt stays docked though a background subagent\'s '
          'later prompt is answered', waiting == ['start', 'ask', 'ask', 'end:waiting on you', 'answered']
          and log.events() == waiting + ['answered', 'start'], f'{waiting} {log.events()}')


def t15_a_finished_turn_names_no_asker(tmp: Path) -> None:
    log = Log(tmp, 't15')
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.hook('PermissionRequest', tool_name='Bash', tool_input=BASH, agent_id='fg1')
    log.hook('Notification', notification_type='permission_prompt')
    log.hook('PostToolUse', tool_name='Bash', tool_input=BASH, agent_id='fg1')
    log.hook('PostToolBatch', tool_calls=[])
    log.hook('Stop')
    log.hook('PreToolUse', tool_name='Bash', tool_input={}, agent_id='fg1')
    log.hook('PostToolBatch', tool_calls=[], agent_id='bg1')
    after_stop = log.events()
    log.hook('PreToolUse', tool_name='Bash', tool_input={})
    check('T15 once the turn finishes no subagent\'s call sends it out, the last asker\'s '
          'included, and a Stop hook\'s continuation does', log.events() == after_stop + ['start']
          and after_stop == WAIT + ['answered', 'start', 'end:finished'],
          f'{after_stop} {log.events()}')


def t16_each_wait_ends_on_its_own_asks(tmp: Path) -> None:
    log = Log(tmp, 't16')
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.hook('PermissionRequest', tool_name='Bash', tool_input=BASH, agent_id='fg1')
    log.hook('Notification', notification_type='permission_prompt')
    log.hook('PostToolBatch', tool_calls=[], agent_id='fg1')
    log.hook('PermissionRequest', tool_name='Bash', tool_input=BASH)
    log.hook('Notification', notification_type='permission_prompt')
    log.hook('PostToolBatch', tool_calls=[], agent_id='fg1')
    docked = log.events()
    log.hook('PostToolBatch', tool_calls=[])
    log.hook('PermissionRequest', tool_name='Bash', tool_input=BASH, agent_id='fg2')
    log.hook('Notification', notification_type='permission_prompt')
    log.hook('PostToolBatch', tool_calls=[], agent_id='fg2')
    one = WAIT + ['answered']
    check('T16 each wait ends on its own asks: an earlier asker\'s later batch leaves a later wait '
          'docked', docked == one + WAIT
          and log.events() == docked + ['answered', 'start', 'ask', 'end:waiting on you', 'answered',
                                        'start'], f'{docked} {log.events()}')


def t17_a_main_batch_beside_a_subagents_prompt(tmp: Path) -> None:
    log = Log(tmp, 't17')
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.hook('PreToolUse', tool_name='Bash', tool_input=BASH)
    log.hook('PermissionRequest', tool_name='Bash', tool_input=BASH)
    log.hook('PostToolUse', tool_name='Bash', tool_input=BASH)
    answered = log.events()
    log.hook('PreToolUse', tool_name='Agent', tool_input={'prompt': 'touch d2'})
    log.hook('PreToolUse', tool_name='Bash', tool_input=OTHER, agent_id='fg1')
    log.hook('PermissionRequest', tool_name='Bash', tool_input=OTHER, agent_id='fg1')
    log.hook('Notification', notification_type='permission_prompt')
    waiting = log.events()
    log.hook('PostToolUse', tool_name='Bash', tool_input=OTHER, agent_id='fg1')
    started = log.events()
    log.hook('PostToolBatch', tool_calls=[], agent_id='fg1')
    log.hook('PostToolUse', tool_name='Agent', tool_input={'prompt': 'touch d2'})
    log.hook('PostToolBatch', tool_calls=[])
    check('T17 a main agent\'s prompt answered at once is answered at its own result, ahead of the '
          'Agent call beside it', answered == ['start', 'ask', 'answered']
          and waiting == answered + ['ask', 'end:waiting on you'], f'{answered} {waiting}')
    check('T18 the subagent asking beside it sends the turn out at its approved call\'s result, and '
          'the main agent\'s later batch logs nothing', started == waiting + ['answered', 'start']
          and log.events() == started, f'{started} {log.events()}')


def t19_two_prompts_queued_at_once(tmp: Path) -> None:
    log = Log(tmp, 't19')
    for sid, second in (('a', 'fg2'), ('b', 'bg1')):
        log.hook('UserPromptSubmit', sid=sid, prompt='/robovac')
        log.hook('PreToolUse', sid=sid, tool_name='Agent', tool_input={})
        log.hook('PermissionRequest', sid=sid, tool_name='Bash', tool_input=BASH, agent_id='fg1')
        log.hook('PermissionRequest', sid=sid, tool_name='Bash', tool_input=OTHER, agent_id=second)
        log.hook('Notification', sid=sid, notification_type='permission_prompt')
        log.hook('Notification', sid=sid, notification_type='permission_prompt')
        log.hook('PostToolUse', sid=sid, tool_name='Bash', tool_input=BASH, agent_id='fg1')
        log.hook('PostToolBatch', sid=sid, tool_calls=[], agent_id='fg1')
    first = {s: log.events(s) for s in 'ab'}
    for sid, second in (('a', 'fg2'), ('b', 'bg1')):
        log.hook('PostToolUse', sid=sid, tool_name='Bash', tool_input=OTHER, agent_id=second)
    got = {s: log.events(s) for s in 'ab'}
    docked = ['start', 'ask', 'ask', 'end:waiting on you', 'answered']
    check('T19 two prompts queued at once, from two foreground subagents or a foreground and a '
          'background one, dock until both are answered, then go out once; the second notice logs '
          'nothing', first == {'a': docked, 'b': docked}
          and got == {s: docked + ['answered', 'start'] for s in 'ab'}, f'{first} {got}')


def t20_a_prompt_denied_without_esc(tmp: Path) -> None:
    log = Log(tmp, 't20')
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.hook('PreToolUse', tool_name='Bash', tool_input=BASH)
    log.hook('PermissionRequest', tool_name='Bash', tool_input=BASH)
    log.hook('Notification', notification_type='permission_prompt')
    log.hook('PostToolBatch', tool_calls=[{'tool_name': 'Bash', 'tool_input': BASH}])
    check('T20 a prompt denied without Esc runs no result, and its agent\'s batch sends the turn out',
          log.events() == WAIT + ['answered', 'start'], str(log.events()))


def t21_esc_while_docked(tmp: Path) -> None:
    log = Log(tmp, 't21')
    t = transcript(log.dir / 't.jsonl', said('/robovac'))
    log.hook('UserPromptSubmit', prompt='/robovac', transcript_path=str(t))
    log.hook('PermissionRequest', tool_name='Bash', tool_input=BASH, transcript_path=str(t))
    log.hook('Notification', notification_type='permission_prompt', transcript_path=str(t))
    pressed = int(log.rows()[0]['t']) + 5
    stamp = time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime(pressed))
    transcript(t, dict(said('[Request interrupted by user for tool use]'), timestamp=stamp))
    log.hook('PostToolUse', tool_name='Read', tool_input={}, agent_id='bg1', transcript_path=str(t))
    seen = log.events()
    ended = [r['t'] for r in log.rows() if r.get('why') == 'interrupted']
    log.hook('PreToolUse', tool_name='Read', tool_input={}, transcript_path=str(t))
    log.hook('PostToolBatch', tool_calls=[], transcript_path=str(t))
    stayed = log.events()
    log.hook('UserPromptSubmit', prompt='next', transcript_path=str(t))
    check('T21 an Esc on a prompt that docked the turn ends it as interrupted at the next hook, at '
          'the Esc\'s time; no call, batch or answer sends it out, and the next prompt does',
          seen == WAIT + ['end:interrupted'] and ended == [float(pressed)]
          and stayed[:len(seen)] == seen and 'start' not in stayed[len(seen):]
          and log.events() == stayed + ['start'], f'{seen} {ended} {stayed} {log.events()}')


def t22_a_foreground_subagent_denied_with_esc(tmp: Path) -> None:
    log = Log(tmp, 't22')
    t = transcript(log.dir / 't.jsonl', said('/robovac'))
    transcript(sub(t, 'fg1'), said('touch e1.txt'))
    log.hook('UserPromptSubmit', prompt='/robovac', transcript_path=str(t))
    log.hook('PreToolUse', tool_name='Agent', tool_input={}, transcript_path=str(t))
    log.hook('PermissionRequest', tool_name='Bash', tool_input=BASH, agent_id='fg1',
             transcript_path=str(t))
    log.hook('Notification', notification_type='permission_prompt', transcript_path=str(t))
    transcript(sub(t, 'fg1'), said('[Request interrupted by user for tool use]'))
    transcript(t, {'type': 'user', 'message': {'role': 'user', 'content': [
        {'type': 'tool_result', 'content': [{'type': 'text', 'text': ESC}]}]}})
    log.hook('PostToolUseFailure', tool_name='Agent', tool_input={}, is_interrupt=True,
             error='[Request interrupted by user for tool use]', transcript_path=str(t))
    failed = after(log)
    log.hook('PostToolBatch', tool_calls=[], transcript_path=str(t))
    log.hook('Stop', transcript_path=str(t))
    check('T22 a foreground subagent\'s prompt denied with Esc is answered by the interrupt line in '
          'its own transcript, at the main agent\'s next hook, and the turn goes on',
          failed == ['answered', 'start'] and after(log) == failed + ['end:finished'],
          f'{failed} {log.events()}')


def t23_a_background_subagent_denied_with_esc(tmp: Path) -> None:
    log = Log(tmp, 't23')
    t = transcript(log.dir / 't.jsonl', said('/robovac'))
    log.hook('UserPromptSubmit', prompt='/robovac', transcript_path=str(t))
    log.hook('PreToolUse', tool_name='Bash', tool_input={'command': 'sleep 20'}, transcript_path=str(t))
    log.hook('PermissionRequest', tool_name='Bash', tool_input=BASH, agent_id='bg1',
             transcript_path=str(t))
    log.hook('Notification', notification_type='permission_prompt', transcript_path=str(t))
    log.hook('PreToolUse', tool_name='Read', tool_input={}, agent_id='bg2', transcript_path=str(t))
    docked = log.events()
    transcript(sub(t, 'bg1'), said('[Request interrupted by user for tool use]'))
    log.hook('PostToolUse', tool_name='Bash', tool_input={'command': 'sleep 20'}, transcript_path=str(t))
    check('T23 a background subagent\'s prompt denied with Esc is answered at the next hook of any '
          'kind, and the turn goes on', docked == WAIT
          and log.events() == docked + ['answered', 'start'], f'{docked} {log.events()}')


def t24_a_background_prompt_and_the_main_agents_call(tmp: Path) -> None:
    log = Log(tmp, 't24')
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.hook('PermissionRequest', tool_name='Bash', tool_input=BASH, agent_id='bg1')
    log.hook('Notification', notification_type='permission_prompt')
    log.hook('PostToolUse', tool_name='Bash', tool_input=BASH)
    log.hook('PreToolUse', tool_name='Bash', tool_input=BASH, agent_id='bg2')
    log.hook('PostToolBatch', tool_calls=[], agent_id='bg2')
    docked = log.events()
    log.hook('PreToolUse', tool_name='Bash', tool_input={'command': 'sleep 2'})
    out = log.events()
    log.hook('PostToolUse', tool_name='Bash', tool_input=BASH, agent_id='bg1')
    check('T24 while only a background subagent\'s prompt waits, the main agent\'s next call sends '
          'the turn out and answers nothing; its sibling\'s result, the same command, and another '
          'subagent\'s call leave it docked', docked == WAIT and out == WAIT + ['start']
          and log.events() == out, f'{docked} {out} {log.events()}')


def t25_the_turn_finishes_while_a_background_prompt_waits(tmp: Path) -> None:
    log = Log(tmp, 't25')
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.hook('PermissionRequest', tool_name='Bash', tool_input=BASH, agent_id='bg1')
    log.hook('Notification', notification_type='permission_prompt')
    log.hook('Stop')
    stopped = log.events()
    log.hook('PostToolUse', tool_name='Bash', tool_input=BASH, agent_id='bg1')
    log.hook('PreToolUse', tool_name='Read', tool_input={}, agent_id='bg1')
    log.hook('PostToolBatch', tool_calls=[], agent_id='bg1')
    answered = log.events()
    log.hook('PreToolUse', tool_name='Bash', tool_input={})
    check('T25 a turn that finishes while docked on a background prompt logs finished; that '
          'prompt\'s answer and calls start nothing, and a Stop hook\'s continuation does',
          stopped == WAIT + ['end:finished'] and 'start' not in answered[len(stopped):]
          and log.events() == answered + ['start'], f'{stopped} {answered} {log.events()}')


def t26_a_main_agents_form(tmp: Path) -> None:
    log = Log(tmp, 't26')
    for sid, action in (('a', 'accept'), ('b', 'decline'), ('c', 'cancel')):
        log.hook('UserPromptSubmit', sid=sid, prompt='/robovac')
        log.hook('PreToolUse', sid=sid, tool_name='mcp__s__ask', tool_input={})
        log.hook('Elicitation', sid=sid, mcp_server_name='s', mode='form')
        log.hook('Notification', sid=sid, notification_type='elicitation_dialog')
        log.hook('ElicitationResult', sid=sid, mcp_server_name='s', mode='form', action=action)
        log.hook('PostToolUse', sid=sid, tool_name='mcp__s__ask', tool_input={})
    got = {s: log.events(s) for s in 'abc'}
    check('T26 a main agent\'s MCP form docks the turn, and its result sends it out, accepted, '
          'declined or cancelled', got == {s: WAIT + ['answered', 'start'] for s in 'abc'}, str(got))


def t27_a_subagents_form(tmp: Path) -> None:
    log = Log(tmp, 't27')
    for sid in 'ab':
        log.hook('UserPromptSubmit', sid=sid, prompt='/robovac')
        log.hook('PreToolUse', sid=sid, tool_name='mcp__s__ask', tool_input={}, agent_id='fg1')
        log.hook('Elicitation', sid=sid, mcp_server_name='s', mode='form')
        log.hook('Notification', sid=sid, notification_type='elicitation_dialog')
        log.hook('PostToolUse', sid=sid, tool_name='Read', tool_input={}, agent_id='bg1')
        log.hook('PostToolUse', sid=sid, tool_name='mcp__t__ask', tool_input={}, agent_id='bg1')
        log.hook('ElicitationResult', sid=sid, mcp_server_name='t', mode='form', action='accept')
        log.hook('PostToolBatch', sid=sid, tool_calls=[])
        log.hook('PreToolUse', sid=sid, tool_name='Read', tool_input={})
    docked = {s: log.events(s) for s in 'ab'}
    log.hook('ElicitationResult', mcp_server_name='s', mode='form', action='accept')
    log.hook('PostToolUse', sid='b', tool_name='mcp__s__ask', tool_input={}, agent_id='fg1')
    got = {s: log.events(s) for s in 'ab'}
    check('T27 a subagent\'s form, which names no agent, stays docked through other agents\' results '
          'and another server\'s, and goes out at its own result or its server\'s tool result',
          docked == {'a': WAIT, 'b': WAIT}
          and got == {s: WAIT + ['answered', 'start'] for s in 'ab'}, f'{docked} {got}')


def t28_a_form_after_a_background_prompt(tmp: Path) -> None:
    log = Log(tmp, 't28')
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.hook('PermissionRequest', tool_name='Read', tool_input={'file_path': '/x'}, agent_id='bg1')
    log.hook('PostToolUse', tool_name='Read', tool_input={'file_path': '/x'}, agent_id='bg1')
    log.hook('Elicitation', mcp_server_name='s', mode='form')
    log.hook('Notification', notification_type='elicitation_dialog')
    log.hook('PreToolUse', tool_name='Read', tool_input={}, agent_id='bg1')
    log.hook('PostToolBatch', tool_calls=[], agent_id='bg1')
    docked = log.events()
    log.hook('ElicitationResult', mcp_server_name='s', mode='form', action='accept')
    check('T28 a background subagent answered at once holds nothing, so its later calls leave the '
          'main agent\'s form docked', docked == ['start', 'ask', 'answered', 'ask',
                                                   'end:waiting on you']
          and log.events() == docked + ['answered', 'start'], f'{docked} {log.events()}')


def t29_a_notice_with_no_ask(tmp: Path) -> None:
    log = Log(tmp, 't29')
    for sid in 'ab':
        log.hook('UserPromptSubmit', sid=sid, prompt='/robovac')
        log.hook('Notification', sid=sid, notification_type='permission_prompt')
        log.hook('PreToolUse', sid=sid, tool_name='Bash', tool_input={})
        log.hook('PreToolUse', sid=sid, tool_name='Bash', tool_input={}, agent_id='bg1')
        log.hook('PostToolBatch', sid=sid, tool_calls=[], agent_id='bg1')
    docked = {s: log.events(s) for s in 'ab'}
    log.hook('PostToolUse', tool_name='Bash', tool_input={}, agent_id='bg1')
    log.hook('PostToolUseFailure', sid='b', tool_name='Bash', tool_input={})
    got = {s: log.events(s) for s in 'ab'}
    check('T29 a notice with no ask logged docks; any agent\'s result sends it out, and neither a '
          'call, the main agent\'s included, nor a subagent\'s batch does',
          docked == {'a': WAIT, 'b': WAIT}
          and got == {s: WAIT + ['answered', 'start'] for s in 'ab'}, f'{docked} {got}')


def t30_a_siblings_result_answers_nothing(tmp: Path) -> None:
    log = Log(tmp, 't30')
    out, inside = {'file_path': '/outside/o.txt'}, {'file_path': '/w/inside.txt'}
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.hook('PreToolUse', tool_name='Read', tool_input=out)
    log.hook('PermissionRequest', tool_name='Read', tool_input=out)
    log.hook('PreToolUse', tool_name='Read', tool_input=inside)
    log.hook('PostToolUse', tool_name='Read', tool_input=inside)
    log.hook('Notification', notification_type='permission_prompt')
    log.hook('PostToolUse', tool_name='Read', tool_input=inside)
    log.hook('PostToolUse', tool_name='Glob', tool_input=out)
    docked = log.events()
    log.hook('PostToolUse', tool_name='Read', tool_input=out)
    check('T30 a sibling call\'s result, before or after the notice, and another tool with the same '
          'input, answer nothing; the asked call\'s own result does', docked == WAIT
          and log.events() == WAIT + ['answered', 'start'], f'{docked} {log.events()}')


def t31_an_answered_question_adds_its_answers(tmp: Path) -> None:
    log = Log(tmp, 't31')
    asked = {'questions': [{'question': 'Proceed?', 'options': [{'label': 'yes'}, {'label': 'no'}]}]}
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.hook('PermissionRequest', tool_name='AskUserQuestion', tool_input=asked)
    log.hook('Notification', notification_type='permission_prompt')
    log.hook('PostToolUse', tool_name='AskUserQuestion',
             tool_input=dict(asked, answers={'Proceed?': 'yes'}))
    check('T31 a question\'s result, whose input adds the answers, answers its ask',
          log.events() == WAIT + ['answered', 'start'], str(log.events()))


def t32_an_escd_turns_ask_holds_no_later_wait(tmp: Path) -> None:
    log = Log(tmp, 't32')
    t = transcript(log.dir / 't.jsonl', said('/robovac'))
    log.hook('UserPromptSubmit', prompt='/robovac', transcript_path=str(t))
    log.hook('PermissionRequest', tool_name='Bash', tool_input=BASH, transcript_path=str(t))
    log.hook('Notification', notification_type='permission_prompt', transcript_path=str(t))
    transcript(t, said('[Request interrupted by user for tool use]'))
    log.hook('UserPromptSubmit', prompt='try another way', transcript_path=str(t))
    log.hook('PermissionRequest', tool_name='Bash', tool_input=OTHER, transcript_path=str(t))
    log.hook('Notification', notification_type='permission_prompt', transcript_path=str(t))
    log.hook('PostToolUse', tool_name='Bash', tool_input=OTHER, transcript_path=str(t))
    check('T32 an ask left open by an Esc\'d turn holds no wait of the next turn',
          log.events() == WAIT + ['end:interrupted'] + WAIT + ['answered', 'start'],
          str(log.events()))


def t33_settings_that_predate_the_newer_hooks(tmp: Path) -> None:
    log = Log(tmp, 't33')
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.hook('PermissionRequest', tool_name='Bash', tool_input=BASH)
    log.hook('Notification', notification_type='permission_prompt')
    log.hook('PostToolBatch', tool_calls=[])
    log.hook('UserPromptSubmit', sid='b', prompt='/robovac')
    log.hook('PermissionRequest', sid='b', tool_name='Bash', tool_input=BASH, agent_id='fg1')
    log.hook('Notification', sid='b', notification_type='permission_prompt')
    log.hook('PostToolBatch', sid='b', tool_calls=[], agent_id='fg1')
    log.hook('UserPromptSubmit', sid='c', prompt='/robovac')
    log.hook('Notification', sid='c', notification_type='permission_prompt')
    log.hook('PostToolBatch', sid='c', tool_calls=[], agent_id='fg1')
    docked = log.events('c')
    log.hook('PostToolBatch', sid='c', tool_calls=[])
    got = {s: log.events(s) for s in 'abc'}
    check('T33 with no result hooks a wait ends at the asker\'s batch, and with no ask hooks at the '
          'main agent\'s batch', docked == WAIT
          and got == {s: WAIT + ['answered', 'start'] for s in 'abc'}, f'{docked} {got}')


def t34_an_error_or_a_close_while_docked(tmp: Path) -> None:
    log = Log(tmp, 't34')
    for sid in 'ab':
        log.hook('UserPromptSubmit', sid=sid, prompt='/robovac')
        log.hook('PermissionRequest', sid=sid, tool_name='Bash', tool_input=BASH)
        log.hook('Notification', sid=sid, notification_type='permission_prompt')
    log.hook('StopFailure', error='overloaded')
    log.hook('SessionEnd', sid='b')
    got = {s: log.events(s) for s in 'ab'}
    check('T34 an API error or a close while docked on a prompt ends the wait as such',
          got == {'a': WAIT + ['end:error: overloaded'], 'b': WAIT + ['end:session closed']}, str(got))


def t35_a_command_never_reaches_the_log(tmp: Path) -> None:
    log = Log(tmp, 't35')
    secret = 'sk-ant-api03-SECRETVALUE'
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.hook('PermissionRequest', tool_name='Bash',
             tool_input={'command': f'curl -H "x-api-key: {secret}" https://x', 'description': 'call'})
    ask = next((r for r in log.rows() if r['event'] == 'ask'), {})
    check('T35 an ask keeps a digest of each input value, never the command',
          secret not in log.path.read_text()
          and all(re.fullmatch(r'[0-9a-f]{12}', v) for v in ask.get('keys', {}).values())
          and sorted(ask.get('keys', {})) == ['command', 'description'], str(ask))


def t36_the_main_agents_own_prompt_holds_its_calls(tmp: Path) -> None:
    log = Log(tmp, 't36')
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.hook('PermissionRequest', tool_name='Bash', tool_input=OTHER, agent_id='bg1')
    log.hook('PermissionRequest', tool_name='Read', tool_input={'file_path': '/o'})
    log.hook('Notification', notification_type='permission_prompt')
    log.hook('PreToolUse', tool_name='Read', tool_input={'file_path': '/i'})
    docked = log.events()
    log.hook('PostToolBatch', tool_calls=[])
    check('T36 the main agent\'s own open prompt keeps a sibling\'s call from sending the turn '
          'out, and once its batch answers it, only a background prompt is left and the turn goes',
          docked == ['start', 'ask', 'ask', 'end:waiting on you']
          and log.events() == docked + ['answered', 'start'], f'{docked} {log.events()}')


def t37_a_background_prompt_holds_no_later_wait(tmp: Path) -> None:
    log = Log(tmp, 't37')
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.hook('PermissionRequest', tool_name='Bash', tool_input=OTHER, agent_id='bg1')
    log.hook('Notification', notification_type='permission_prompt')
    log.hook('PreToolUse', tool_name='Agent', tool_input={})
    log.hook('PermissionRequest', tool_name='Bash', tool_input=BASH, agent_id='fg1')
    log.hook('Notification', notification_type='permission_prompt')
    log.hook('PostToolUse', tool_name='Bash', tool_input=BASH, agent_id='fg1')
    check('T37 a background prompt the main agent worked past holds no later wait, so a foreground '
          'subagent\'s approved call sends the turn out', log.events() == WAIT + ['start', 'ask',
                                                                                  'end:waiting on you',
                                                                                  'answered', 'start'],
          str(log.events()))


def t38_an_answer_found_at_a_boundary(tmp: Path) -> None:
    log = Log(tmp, 't38')
    events = (('a', 'Stop', {}), ('b', 'UserPromptSubmit', {'prompt': 'next'}),
              ('c', 'Notification', {'notification_type': 'permission_prompt'}),
              ('d', 'PermissionRequest', {'tool_name': 'Bash', 'tool_input': OTHER}))
    for sid, event, fields in events:
        t = transcript(log.dir / f'{sid}.jsonl', said('/robovac'))
        log.hook('UserPromptSubmit', sid=sid, prompt='/robovac', transcript_path=str(t))
        log.run('say', 'binning leftovers', sid=sid)
        log.hook('PermissionRequest', sid=sid, tool_name='Bash', tool_input=BASH, agent_id='fg1',
                 transcript_path=str(t))
        log.hook('Notification', sid=sid, notification_type='permission_prompt',
                 transcript_path=str(t))
        transcript(sub(t, 'fg1'), said('[Request interrupted by user for tool use]'))
        log.hook(event, sid=sid, transcript_path=str(t), **fields)
    got = {sid: after(log, sid) for sid, _, _ in events}
    fresh = [r.get('say') for r in log.rows('b') if r['event'] == 'start'][-1:]
    check('T38 an answer found at a turn\'s end, a prompt or a notice starts no run of its own: the '
          'turn finishes, the prompt starts a fresh one, a notice stays docked, and a new prompt\'s '
          'ask is logged', got == {'a': ['answered', 'end:finished'], 'b': ['answered', 'start'],
                                   'c': ['answered', 'ask'], 'd': ['answered', 'start', 'ask']}
          and fresh == [None], f'{got} {fresh}')


def t39_an_esc_while_a_background_prompt_waits(tmp: Path) -> None:
    log = Log(tmp, 't39')
    t = transcript(log.dir / 't.jsonl', said('/robovac'))
    log.hook('UserPromptSubmit', prompt='/robovac', transcript_path=str(t))
    log.hook('PermissionRequest', tool_name='Bash', tool_input=BASH, agent_id='bg1',
             transcript_path=str(t))
    log.hook('Notification', notification_type='permission_prompt', transcript_path=str(t))
    transcript(t, said(ESC))
    log.hook('PostToolUse', tool_name='Bash', tool_input=BASH, agent_id='bg1',
             transcript_path=str(t))
    escd = after(log)
    log.hook('UserPromptSubmit', prompt='next', transcript_path=str(t))
    check('T39 an Esc while docked on a background prompt ends the wait, and that prompt\'s answer '
          'afterwards starts nothing; the next prompt does',
          escd == ['end:interrupted', 'answered'] and after(log) == escd + ['start'],
          f'{escd} {log.events()}')


def t40_one_result_answers_one_of_two_equal_prompts(tmp: Path) -> None:
    log = Log(tmp, 't40')
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.hook('PermissionRequest', tool_name='Bash', tool_input=BASH)
    log.hook('PermissionRequest', tool_name='Bash', tool_input=BASH)
    log.hook('Notification', notification_type='permission_prompt')
    log.hook('PostToolUse', tool_name='Bash', tool_input=BASH)
    one = log.events()
    log.hook('PostToolUse', tool_name='Bash', tool_input=BASH)
    check('T40 of two equal prompts from one agent, the first result answers one, and the second '
          'sends the turn out', one == ['start', 'ask', 'ask', 'end:waiting on you', 'answered']
          and log.events() == one + ['answered', 'start'], f'{one} {log.events()}')


def t41_one_form_result_answers_one_of_two_forms(tmp: Path) -> None:
    log = Log(tmp, 't41')
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.hook('Elicitation', mcp_server_name='s', mode='form')
    log.hook('Elicitation', mcp_server_name='s', mode='form')
    log.hook('Notification', notification_type='elicitation_dialog')
    log.hook('ElicitationResult', mcp_server_name='s', mode='form', action='accept')
    one = log.events()
    log.hook('ElicitationResult', mcp_server_name='s', mode='form', action='accept')
    check('T41 of two forms from one server, the first docks the turn as it opens, the first result '
          'answers one, and the second sends the turn out',
          one == ['start', 'ask', 'end:waiting on you', 'ask', 'answered']
          and log.events() == one + ['answered', 'start'], f'{one} {log.events()}')


def t42_a_form_result_answers_a_notice(tmp: Path) -> None:
    log = Log(tmp, 't42')
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.hook('Notification', notification_type='elicitation_dialog')
    log.hook('ElicitationResult', mcp_server_name='s', mode='form', action='accept')
    check('T42 a notice with no ask logged is answered by any form\'s result, which sends the '
          'turn out', log.events() == WAIT + ['answered', 'start'], str(log.events()))


def t43_a_resumed_subagents_old_esc(tmp: Path) -> None:
    log = Log(tmp, 't43')
    t = transcript(log.dir / 't.jsonl', said('/robovac'))
    transcript(sub(t, 'fg1'), said('touch e1.txt'),
               said('[Request interrupted by user for tool use]'))
    log.hook('UserPromptSubmit', prompt='/robovac', transcript_path=str(t))
    log.hook('PermissionRequest', tool_name='Bash', tool_input=BASH, agent_id='fg1',
             transcript_path=str(t))
    log.hook('Notification', notification_type='permission_prompt', transcript_path=str(t))
    log.hook('PostToolBatch', tool_calls=[], agent_id='bg2', transcript_path=str(t))
    docked = log.events()
    log.hook('PostToolUse', tool_name='Bash', tool_input=BASH, agent_id='fg1',
             transcript_path=str(t))
    check('T43 a resumed subagent whose own transcript holds an earlier interrupt line stays '
          'docked on its new prompt until that prompt is answered', docked == WAIT
          and log.events() == WAIT + ['answered', 'start'], f'{docked} {log.events()}')


# ── one writer at a time ────────────────────────────────────────────────────


def l7_two_answers_at_once_start_one_run(tmp: Path) -> None:
    log = Log(tmp, 'l7')
    bad = []
    for n in range(30):
        sid = f's{n}'
        log.hook('UserPromptSubmit', sid=sid, prompt='/robovac')
        log.hook('PermissionRequest', sid=sid, tool_name='Bash', tool_input=BASH, agent_id='fg1')
        log.hook('PermissionRequest', sid=sid, tool_name='Bash', tool_input=OTHER, agent_id='fg2')
        log.hook('Notification', sid=sid, notification_type='permission_prompt')
        payloads = [json.dumps(dict(hook_event_name='PostToolUse', session_id=sid, cwd=str(log.dir),
                                    tool_name='Bash', tool_input=args, agent_id=agent))
                    for args, agent in ((BASH, 'fg1'), (OTHER, 'fg2'))]
        procs = [subprocess.Popen([sys.executable, str(SCRIPT), 'hook'], stdin=subprocess.PIPE,
                                  env=log.env, text=True) for _ in payloads]
        for proc, payload in zip(procs, payloads):
            proc.stdin.write(payload)
            proc.stdin.close()
        for proc in procs:
            proc.wait()
        got = log.events(sid)
        if got[4:] != ['answered', 'answered', 'start']:
            bad.append(got)
    check('L7 two answers landing at once, thirty times, start exactly one run each time',
          not bad, f'{len(bad)} of 30: {bad[:2]}')


if __name__ == '__main__':
    sys.exit(main((t1_permission_prompt_docks_until_the_tool_runs, t2_elicitation_waits_too,
                   t3_other_notifications_change_nothing, t4_stop_hook_continuation_keeps_going,
                   t5_tools_after_esc_stay_docked, t6_tools_elsewhere_log_nothing,
                   t7_hooks_json_sends_every_event, t8_a_run_going_on_keeps_its_line,
                   t9_a_subagent_does_not_send_it_out, t10_the_last_end_decides,
                   t11_a_line_given_while_waiting_is_kept,
                   t12_the_subagent_that_asked_sends_it_out,
                   t13_another_subagent_leaves_a_subagents_wait_docked,
                   t14_a_main_agents_open_ask_outranks_a_later_one,
                   t15_a_finished_turn_names_no_asker, t16_each_wait_ends_on_its_own_asks,
                   t17_a_main_batch_beside_a_subagents_prompt, t19_two_prompts_queued_at_once,
                   t20_a_prompt_denied_without_esc, t21_esc_while_docked,
                   t22_a_foreground_subagent_denied_with_esc,
                   t23_a_background_subagent_denied_with_esc,
                   t24_a_background_prompt_and_the_main_agents_call,
                   t25_the_turn_finishes_while_a_background_prompt_waits, t26_a_main_agents_form,
                   t27_a_subagents_form, t28_a_form_after_a_background_prompt,
                   t29_a_notice_with_no_ask, t30_a_siblings_result_answers_nothing,
                   t31_an_answered_question_adds_its_answers,
                   t32_an_escd_turns_ask_holds_no_later_wait,
                   t33_settings_that_predate_the_newer_hooks, t34_an_error_or_a_close_while_docked,
                   t35_a_command_never_reaches_the_log,
                   t36_the_main_agents_own_prompt_holds_its_calls,
                   t37_a_background_prompt_holds_no_later_wait,
                   t38_an_answer_found_at_a_boundary,
                   t39_an_esc_while_a_background_prompt_waits,
                   t40_one_result_answers_one_of_two_equal_prompts,
                   t41_one_form_result_answers_one_of_two_forms, t42_a_form_result_answers_a_notice,
                   t43_a_resumed_subagents_old_esc, l7_two_answers_at_once_start_one_run)))
