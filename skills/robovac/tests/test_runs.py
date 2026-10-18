#!/usr/bin/env python3
"""
test_runs — feeds runs.py hook events for throwaway sessions and checks that a robovac session's
run is open exactly while its agent is working; test_waits holds the turns that wait on the person.

Run it with `python3 test_runs.py`. It runs runs.py with ROBOVAC_RUNS pointing at a log in one
temporary folder, which it removes after. The exit code is the number of failed checks.

S1 to S5 say which prompts make a robovac session, S3 through the Skill tool by its own name or a
plugin's. W1 to W6 hold the rule that a run is open while a turn is in progress, loop or not, and
ends when the turn does, and W8 ends one silent for twelve hours. W7 and W9 to W16 keep a session
known through a trim of the log, and forget it once a week passes unheard from. E1 to E8 check that
Esc is read from the transcript's own interrupt line, never from text that quotes it, E9 counts an
Esc as hearing from the session, E10 ends a run at its first Esc, and E11 reads every line in
esc_lines.json, which Runs.swift's own test reads too, at the time it names: Esc lines, and replies
that ended their turn with no Stop hook after them. L1 to L3 cover `say`
and `live`, L4 to L6 and L11 hooks and `say` writing the log at once, L8 the length of a line, and
L9 and L10 `path` and an unknown command. H1 holds that a hook given input it cannot read prints
nothing and exits 0.
"""

from __future__ import annotations

import fcntl
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from harness import ESC, HERE, SCRIPT, Log, check, main, said, tool_result, transcript



# ── which sessions are robovac sessions ─────────────────────────────────────


def s1_prompt_starting_with_robovac(tmp: Path) -> None:
    log = Log(tmp, 's1')
    log.hook('UserPromptSubmit', prompt='/robovac skills/clorox')
    log.hook('UserPromptSubmit', sid='b', prompt='  /loop 1h /robovac')
    check('S1 a prompt that starts with /robovac, or /loop then /robovac, starts a run',
          log.events() == ['start'] and log.events('b') == ['start'], f'{log.events()} {log.events("b")}')


def s2_mention_is_not_a_run(tmp: Path) -> None:
    log = Log(tmp, 's2')
    log.hook('UserPromptSubmit', prompt='This session continues one that ran /loop 1h /robovac.')
    log.hook('UserPromptSubmit', sid='b', prompt='what does robovac do?')
    check('S2 a prompt that only mentions /robovac starts nothing',
          log.events() == [] and log.events('b') == [], f'{log.events()} {log.events("b")}')


def s5_loop_mentions_are_not_runs(tmp: Path) -> None:
    log = Log(tmp, 's5')
    for sid, prompt in (('a', '/loop 5m check whether /robovac is done'),
                        ('b', '/loop 10m /vet watch, and do not run /robovac'),
                        ('c', '/robovac-widget please'), ('d', '/loop /robovac'),
                        ('e', '/loop 12h /robovac apps/robovac-widget')):
        log.hook('UserPromptSubmit', sid=sid, prompt=prompt)
    got = {s: log.events(s) for s in 'abcde'}
    check('S5 only /loop [interval] /robovac starts a loop run; a mention or a longer name does not',
          got == {'a': [], 'b': [], 'c': [], 'd': ['start'], 'e': ['start']}, str(got))


def s3_skill_tool_starts_a_run(tmp: Path) -> None:
    log = Log(tmp, 's3')
    log.hook('UserPromptSubmit', prompt='run the robovac skill')
    log.hook('PreToolUse', tool_name='Skill', tool_input={'skill': 'robovac'})
    log.hook('PreToolUse', sid='b', tool_name='Skill', tool_input={'skill': 'build'})
    log.hook('UserPromptSubmit', sid='c', prompt='run it from the plugin')
    log.hook('PreToolUse', sid='c', tool_name='Skill', tool_input={'skill': 'kstack:robovac'})
    check('S3 the Skill tool running robovac, by its own name or a plugin\'s, starts a run, and '
          'another skill does not', log.events() == ['start'] and log.events('b') == []
          and log.events('c') == ['start'], f'{log.events()} {log.events("b")} {log.events("c")}')


def s4_old_start_rows_do_not_count(tmp: Path) -> None:
    log = Log(tmp, 's4')
    log.path.write_text(json.dumps({'t': 1, 'session': 'a', 'project': 'p', 'event': 'start',
                                    'loop': True}) + '\n'
                        + json.dumps({'t': 2, 'session': 'a', 'project': 'p', 'event': 'end',
                                      'why': 'finished'}) + '\n')
    log.hook('UserPromptSubmit', prompt='carry on')
    check('S4 a start logged before sessions were marked does not make a robovac session',
          log.events() == ['start', 'end:finished'], str(log.events()))


# ── open while the agent works ──────────────────────────────────────────────


def w1_turn_end_docks(tmp: Path) -> None:
    log = Log(tmp, 'w1')
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.hook('Stop')
    log.hook('UserPromptSubmit', sid='b', prompt='/loop 1h /robovac')
    log.hook('Stop', sid='b')
    check('W1 a turn ending ends the run, loop or not',
          log.events() == ['start', 'end:finished'] and log.events('b') == ['start', 'end:finished'],
          f'{log.events()} {log.events("b")}')


def w2_next_turn_goes_again(tmp: Path) -> None:
    log = Log(tmp, 'w2')
    log.hook('UserPromptSubmit', prompt='/loop 1h /robovac')
    log.hook('Stop')
    log.hook('UserPromptSubmit', prompt='run the robovac skill')
    log.hook('PreToolUse', tool_name='Skill', tool_input={'skill': 'robovac'})
    log.hook('Stop')
    log.hook('UserPromptSubmit', prompt='anything left from the last run?')
    check('W2 any later turn in a robovac session opens its run again, once',
          log.events() == ['start', 'end:finished', 'start', 'end:finished', 'start'], str(log.events()))


def w3_other_sessions_stay_out(tmp: Path) -> None:
    log = Log(tmp, 'w3')
    log.hook('UserPromptSubmit', sid='b', prompt='fix the bug')
    log.hook('Stop', sid='b')
    check('W3 a session that never ran robovac logs nothing', log.events('b') == [], str(log.events('b')))


def w4_error_ends_the_run(tmp: Path) -> None:
    log = Log(tmp, 'w4')
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.hook('StopFailure', error='overloaded')
    check('W4 a turn ending on an API error ends the run, naming the error',
          log.events() == ['start', 'end:error: overloaded'], str(log.events()))


def w5_closed_session_stays_closed(tmp: Path) -> None:
    log = Log(tmp, 'w5')
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.hook('Stop')
    log.hook('SessionEnd')
    log.hook('UserPromptSubmit', prompt='carry on')
    log.hook('UserPromptSubmit', sid='b', prompt='/robovac')
    log.hook('SessionEnd', sid='b')
    check('W5 a closed session is no longer a robovac session, docked or working when it closed',
          log.events() == ['start', 'end:finished', 'end:session closed']
          and log.events('b') == ['start', 'end:session closed'], f'{log.events()} {log.events("b")}')


def w6_mid_turn_prompt_keeps_going(tmp: Path) -> None:
    log = Log(tmp, 'w6')
    t = transcript(log.dir / 't.jsonl', said('/robovac'))
    log.hook('UserPromptSubmit', prompt='/robovac', transcript_path=str(t))
    transcript(t, said('also look at the README'))
    log.hook('UserPromptSubmit', prompt='also look at the README', transcript_path=str(t))
    check('W6 a message typed mid-turn leaves the run going', log.events() == ['start'], str(log.events()))


# ── Esc ─────────────────────────────────────────────────────────────────────


def e1_start_marks_the_transcript(tmp: Path) -> None:
    log = Log(tmp, 'e1')
    t = transcript(log.dir / 't.jsonl', said('earlier'), said(ESC))
    log.hook('UserPromptSubmit', prompt='/robovac', transcript_path=str(t))
    start = log.rows()[0]
    check('E1 a start records its transcript and how long it was',
          start.get('transcript') == str(t) and start.get('mark') == t.stat().st_size, str(start))


def e2_esc_after_start_is_an_interrupt(tmp: Path) -> None:
    log = Log(tmp, 'e2')
    t = transcript(log.dir / 't.jsonl', said(ESC))
    log.hook('UserPromptSubmit', prompt='/robovac', transcript_path=str(t))
    transcript(t, said(ESC))
    log.hook('UserPromptSubmit', prompt='start over', transcript_path=str(t))
    check('E2 Esc after the start ends the run as interrupted, and the new prompt opens it again',
          log.events() == ['start', 'end:interrupted', 'start'], str(log.events()))


def e3_quoted_mark_is_not_esc(tmp: Path) -> None:
    log = Log(tmp, 'e3')
    t = transcript(log.dir / 't.jsonl', said('/robovac'))
    log.hook('UserPromptSubmit', prompt='/robovac', transcript_path=str(t))
    transcript(t, tool_result(f'ESC = {ESC!r}'), said(f'why does it say {ESC}?'),
               {'type': 'assistant', 'message': {'role': 'assistant', 'content': [
                   {'type': 'text', 'text': ESC}]}})
    log.hook('UserPromptSubmit', prompt='more', transcript_path=str(t))
    check('E3 the mark quoted in a tool result, mid-message or by the agent is not an Esc',
          log.events() == ['start'], str(log.events()))


def e4_esc_before_the_start_stays_behind(tmp: Path) -> None:
    log = Log(tmp, 'e4')
    t = transcript(log.dir / 't.jsonl', said(ESC))
    log.hook('UserPromptSubmit', prompt='/robovac', transcript_path=str(t))
    transcript(t, said('also the README'))
    log.hook('UserPromptSubmit', prompt='also the README', transcript_path=str(t))
    check('E4 an Esc from before the run began does not end it', log.events() == ['start'],
          str(log.events()))


def e5_esc_as_plain_text_content(tmp: Path) -> None:
    log = Log(tmp, 'e5')
    t = transcript(log.dir / 't.jsonl', said('/robovac'))
    log.hook('UserPromptSubmit', prompt='/robovac', transcript_path=str(t))
    transcript(t, {'type': 'user', 'message': {'role': 'user', 'content': ESC}})
    log.hook('UserPromptSubmit', prompt='again', transcript_path=str(t))
    check('E5 an Esc line whose content is a plain string counts too',
          log.events() == ['start', 'end:interrupted', 'start'], str(log.events()))


def w7_trimmed_log_keeps_the_session(tmp: Path) -> None:
    log = Log(tmp, 'w7')
    now = time.time()
    log.path.write_text(json.dumps({'t': now - 60, 'session': 'a', 'project': 'p', 'event': 'start',
                                    'via': 'again'}) + '\n'
                        + json.dumps({'t': now - 30, 'session': 'a', 'project': 'p', 'event': 'end',
                                      'why': 'finished'}) + '\n')
    log.hook('UserPromptSubmit', prompt='keep going')
    check('W7 a session whose first start was trimmed from the log is still a robovac session',
          log.events() == ['start', 'end:finished', 'start'], str(log.events()))


def w9_trim_keeps_an_idle_session(tmp: Path) -> None:
    log = Log(tmp, 'w9')
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.hook('Stop')
    with log.path.open('a') as f:
        for n in range(4001):
            f.write(json.dumps({'t': time.time(), 'session': f'x{n}', 'project': 'p', 'event': 'say'}) + '\n')
    log.hook('UserPromptSubmit', sid='c', prompt='/robovac')
    log.hook('Stop', sid='c')
    trimmed = len(log.path.read_text().splitlines())
    going = json.loads(log.run('live', '--json'))
    log.hook('UserPromptSubmit', prompt='keep going')
    check('W9 a trim keeps an idle robovac session known and closed, and its next turn starts',
          trimmed < 2200 and going == [] and log.events()[-1:] == ['start'], f'{trimmed} lines, {going}, {log.events()}')


def w11_a_week_unheard_is_forgotten(tmp: Path) -> None:
    log = Log(tmp, 'w11')
    week = time.time() - 8 * 86400
    with log.path.open('w') as f:
        f.write(json.dumps({'t': week, 'session': 'a', 'project': 'p', 'event': 'start', 'via': 'prompt'}) + '\n')
        f.write(json.dumps({'t': week, 'session': 'a', 'project': 'p', 'event': 'end', 'why': 'finished'}) + '\n')
    log.hook('UserPromptSubmit', prompt='carry on')
    check('W11 a session a week unheard from is no longer a robovac session, trim or no trim',
          log.events() == ['start', 'end:finished'], str(log.events()))


def w12_six_days_idle_is_still_known(tmp: Path) -> None:
    log = Log(tmp, 'w12')
    days = time.time() - 6 * 86400
    with log.path.open('w') as f:
        f.write(json.dumps({'t': days, 'session': 'a', 'project': 'p', 'event': 'start', 'via': 'prompt'}) + '\n')
        f.write(json.dumps({'t': days, 'session': 'a', 'project': 'p', 'event': 'end', 'why': 'finished'}) + '\n')
    log.hook('UserPromptSubmit', prompt='carry on')
    log.hook('SessionEnd')
    check('W12 a session six days idle is still a robovac session, and its close is logged',
          log.events() == ['start', 'end:finished', 'start', 'end:session closed'], str(log.events()))


def w13_went_quiet_is_not_hearing(tmp: Path) -> None:
    log = Log(tmp, 'w13')
    log.path.write_text(json.dumps({'t': time.time() - 7.2 * 86400, 'session': 'a', 'project': 'p',
                                    'event': 'start', 'via': 'prompt'}) + '\n')
    log.hook('UserPromptSubmit', prompt='carry on')
    log.hook('UserPromptSubmit', prompt='carry on')
    check('W13 a run gone quiet over a week ago ends, and its went-quiet end does not make the session known',
          log.events() == ['start', 'end:went quiet'], str(log.events()))


def w14_closing_a_forgotten_session_logs_nothing(tmp: Path) -> None:
    log = Log(tmp, 'w14')
    week = time.time() - 8 * 86400
    with log.path.open('w') as f:
        f.write(json.dumps({'t': week, 'session': 'a', 'project': 'p', 'event': 'start', 'via': 'prompt'}) + '\n')
        f.write(json.dumps({'t': week, 'session': 'a', 'project': 'p', 'event': 'end', 'why': 'finished'}) + '\n')
    log.hook('SessionEnd')
    check('W14 closing a session docked and unheard from for a week logs nothing',
          log.events() == ['start', 'end:finished'], str(log.events()))


def w15_trim_counts_no_went_quiet_as_heard(tmp: Path) -> None:
    log = Log(tmp, 'w15')
    began = time.time() - 7.2 * 86400
    with log.path.open('w') as f:
        f.write(json.dumps({'t': began, 'session': 'a', 'project': 'p', 'event': 'start', 'via': 'prompt'}) + '\n')
        f.write(json.dumps({'t': began + 12 * 3600, 'session': 'a', 'project': 'p', 'event': 'end',
                            'why': 'went quiet'}) + '\n')
        for n in range(4001):
            f.write(json.dumps({'t': time.time(), 'session': f'x{n}', 'project': 'p', 'event': 'say'}) + '\n')
    log.hook('UserPromptSubmit', sid='c', prompt='/robovac')
    check('W15 a trim drops a session whose only sign of life inside the week is its went-quiet end',
          log.events() == [], str(log.events()))


def w16_a_say_is_hearing(tmp: Path) -> None:
    log = Log(tmp, 'w16')
    began = time.time() - 8 * 86400
    with log.path.open('w') as f:
        f.write(json.dumps({'t': began, 'session': 'a', 'project': 'p', 'event': 'start', 'via': 'prompt'}) + '\n')
        f.write(json.dumps({'t': time.time() - 86400, 'session': 'a', 'project': 'p', 'event': 'say',
                            'text': 'still sweeping'}) + '\n')
    log.hook('UserPromptSubmit', prompt='carry on')
    check('W16 a run\'s own line counts as hearing from its session, so a week of saying keeps it known',
          log.events() == ['start', 'say', 'end:went quiet', 'start'], str(log.events()))


def w10_trim_forgets_a_dead_session(tmp: Path) -> None:
    log = Log(tmp, 'w10')
    week = time.time() - 8 * 86400
    with log.path.open('w') as f:
        f.write(json.dumps({'t': week, 'session': 'a', 'project': 'p', 'event': 'start', 'via': 'prompt'}) + '\n')
        f.write(json.dumps({'t': week, 'session': 'a', 'project': 'p', 'event': 'end', 'why': 'finished'}) + '\n')
        for n in range(4001):
            f.write(json.dumps({'t': time.time(), 'session': f'x{n}', 'project': 'p', 'event': 'say'}) + '\n')
    log.hook('UserPromptSubmit', sid='c', prompt='/robovac')
    log.hook('UserPromptSubmit', prompt='keep going')
    check('W10 a trim drops a session not heard from in a week, so its log stays bounded',
          log.events() == [], str(log.events()))


def w8_stale_run_does_not_block(tmp: Path) -> None:
    log = Log(tmp, 'w8')
    old = time.time() - 13 * 3600
    log.path.write_text(json.dumps({'t': old, 'session': 'a', 'project': 'p', 'event': 'start',
                                    'via': 'prompt'}) + '\n')
    log.hook('UserPromptSubmit', prompt='/robovac')
    going = json.loads(log.run('live', '--json'))
    ended = [r['t'] for r in log.rows() if r['event'] == 'end']
    check('W8 a run silent past twelve hours ends when it went quiet, and the next one starts',
          log.events() == ['start', 'end:went quiet', 'start'] and [r['session'] for r in going] == ['a']
          and ended == [old + 12 * 3600], f'{log.events()} {going} {ended}')


def e6_esc_then_a_wake_through_the_skill(tmp: Path) -> None:
    log = Log(tmp, 'e6')
    t = transcript(log.dir / 't.jsonl', said('/robovac'))
    log.hook('UserPromptSubmit', prompt='/loop 12h /robovac', transcript_path=str(t))
    transcript(t, said(ESC))
    log.hook('PreToolUse', tool_name='Skill', tool_input={'skill': 'robovac'}, transcript_path=str(t))
    check('E6 an Esc seen at the next hook of any kind ends the run, and the wake opens a new one',
          log.events() == ['start', 'end:interrupted', 'start'], str(log.events()))


# ── say and live ────────────────────────────────────────────────────────────


def l1_say_needs_a_working_run(tmp: Path) -> None:
    log = Log(tmp, 'l1')
    before = log.run('say', 'too early', sid='a')
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.run('say', 'sweeping the bin', sid='a')
    log.hook('Stop')
    after = log.run('say', 'too late', sid='a')
    texts = [r.get('text') for r in log.rows() if r['event'] == 'say']
    check('L1 say is taken only while the agent is working',
          texts == ['sweeping the bin'] and 'no robovac run' in before + after, f'{texts} {before!r}')


def l2_live_lists_working_runs(tmp: Path) -> None:
    log = Log(tmp, 'l2')
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.hook('UserPromptSubmit', sid='b', prompt='/robovac')
    log.hook('Stop', sid='b')
    going = json.loads(log.run('live', '--json'))
    check('L2 live lists the runs whose agents are working', [r['session'] for r in going] == ['a'],
          str(going))


def e7_esc_ends_when_it_was_pressed(tmp: Path) -> None:
    log = Log(tmp, 'e7')
    t = transcript(log.dir / 't.jsonl', said('/robovac'))
    log.hook('UserPromptSubmit', prompt='/robovac', transcript_path=str(t))
    pressed = int(log.rows()[0]['t']) + 1
    transcript(t, dict(said(ESC), timestamp=time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime(pressed))))
    log.hook('SessionEnd', transcript_path=str(t))
    ends = [(r['why'], r['t']) for r in log.rows() if r['event'] == 'end']
    check('E7 an Esc found at a later hook is logged at the time it was pressed',
          ends[:1] == [('interrupted', float(pressed))] and ends[1:] == [('session closed', ends[1][1])],
          str(ends))


def e8_esc_before_silence(tmp: Path) -> None:
    log = Log(tmp, 'e8')
    t = transcript(log.dir / 't.jsonl', said('/robovac'))
    began = time.time() - 12 * 3600 - 120
    log.path.write_text(json.dumps({'t': began, 'session': 'a', 'project': 'p', 'event': 'start',
                                    'via': 'prompt', 'transcript': str(t),
                                    'mark': t.stat().st_size}) + '\n')
    pressed = int(began + 120)
    stamp = time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime(pressed))
    transcript(t, dict(said(ESC), timestamp=stamp))
    log.hook('SessionEnd', transcript_path=str(t))
    ends = [(r['why'], r['t']) for r in log.rows() if r['event'] == 'end']
    check('E8 an Esc in a run that has since gone quiet ends it as interrupted, when it was pressed',
          ends[:1] == [('interrupted', float(pressed))], str(ends))


def e10_two_escs_end_at_the_first(tmp: Path) -> None:
    log = Log(tmp, 'e10')
    t = transcript(log.dir / 't.jsonl', said('/robovac'))
    log.hook('UserPromptSubmit', prompt='/robovac', transcript_path=str(t))
    began = log.rows()[0]['t']
    first, second = (time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime(began + d)) for d in (30, 90))
    transcript(t, dict(said(ESC), timestamp=first), dict(said(ESC), timestamp=second))
    log.hook('UserPromptSubmit', prompt='go on', transcript_path=str(t))
    ended = [r['t'] for r in log.rows() if r['event'] == 'end']
    check('E10 two Escs in one run end it at the first, as the app shows it',
          len(ended) == 1 and 29 <= ended[0] - began <= 30, f'{ended} began {began}')


def e11_the_shared_esc_lines(tmp: Path) -> None:
    spec = importlib.util.spec_from_file_location('runs', SCRIPT)
    runs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runs)
    wrong = []
    for n, case in enumerate(json.loads((HERE / 'esc_lines.json').read_text())['cases']):
        log = Log(tmp, f'e11-{n}')
        t = log.dir / 't.jsonl'
        lines = [line + '\n' for line in case['lines']]
        t.write_text(''.join(lines[:case['mark']]))
        log.hook('UserPromptSubmit', prompt='/robovac', transcript_path=str(t))
        with t.open('a') as f:
            f.write(''.join(lines[case['mark']:]) + ('x' * case['pad'] + '\n' if case['pad'] else ''))
        if case['at'] == 'mtime':
            os.utime(t, (1700000000, 1700000000))

        #a case read at a time it names goes to the reader itself; the rest through a hook...
        if 'now' in case:
            at = runs.ended(str(t), log.rows()[0]['mark'], case['now'])
            got = [] if at is None else [at]
        else:
            log.hook('PreToolUse', tool_name='Read', tool_input={}, transcript_path=str(t))
            got = [r['t'] for r in log.rows() if r.get('why') == 'interrupted']
        want = [] if case['at'] is None else [1700000000.0 if case['at'] == 'mtime' else case['at']]
        if got != want:
            wrong.append(f"{case['name']}: {got}, not {want}")
    check('E11 each line in esc_lines.json, which test_runs.sh feeds Runs.swift too, ends a run at '
          'the time the file names: an Esc line at once, a reply that ended its turn six seconds on',
          not wrong, '; '.join(wrong))


def e9_esc_within_the_week_is_heard(tmp: Path) -> None:
    log = Log(tmp, 'e9')
    t = transcript(log.dir / 't.jsonl', said('/robovac'))
    began = time.time() - 7.1 * 86400
    log.path.write_text(json.dumps({'t': began, 'session': 'a', 'project': 'p', 'event': 'start',
                                    'via': 'prompt', 'transcript': str(t),
                                    'mark': t.stat().st_size}) + '\n')
    stamp = time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime(int(began + 3 * 3600)))
    transcript(t, dict(said(ESC), timestamp=stamp))
    log.hook('UserPromptSubmit', prompt='carry on', transcript_path=str(t))
    log.hook('Stop')
    log.hook('UserPromptSubmit', prompt='carry on', transcript_path=str(t))
    check('E9 an Esc inside the week is hearing from the session, at the first prompt as at the next',
          log.events() == ['start', 'end:interrupted', 'start', 'end:finished', 'start'], str(log.events()))


def l3_live_leaves_out_an_esc(tmp: Path) -> None:
    log = Log(tmp, 'l3')
    t = transcript(log.dir / 't.jsonl', said('/robovac'))
    log.hook('UserPromptSubmit', prompt='/robovac', transcript_path=str(t))
    transcript(t, said(ESC))
    going = json.loads(log.run('live', '--json'))
    check('L3 live leaves out a run whose turn was ended by Esc', going == [], str(going))


def l4_hooks_at_once_lose_no_line(tmp: Path) -> None:
    log = Log(tmp, 'l4')
    with log.path.open('w') as f:
        for n in range(3990):
            f.write(json.dumps({'t': time.time(), 'session': f'x{n}', 'project': 'p', 'event': 'say'}) + '\n')
    payloads = [json.dumps(dict(hook_event_name='UserPromptSubmit', session_id=f'h{n}', cwd=str(log.dir),
                                prompt='/robovac')) for n in range(60)]
    procs = [subprocess.Popen([sys.executable, str(SCRIPT), 'hook'], stdin=subprocess.PIPE, env=log.env,
                              text=True) for _ in payloads]
    for proc, payload in zip(procs, payloads):
        proc.stdin.write(payload)
        proc.stdin.close()
    for proc in procs:
        proc.wait()
    rows = [json.loads(line) for line in log.path.read_text().splitlines()]
    lost = sorted({f'h{n}' for n in range(60)} - {r['session'] for r in rows})
    check('L4 sixty hooks writing at once, through a trim, lose no line', not lost, f'lost {lost}')


def l5_a_hook_waits_for_the_lock(tmp: Path) -> None:
    log = Log(tmp, 'l5')
    log.path.write_text('')
    with open(log.dir / 'runs.jsonl.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        proc = subprocess.Popen([sys.executable, str(SCRIPT), 'hook'], stdin=subprocess.PIPE,
                                env=log.env, text=True)
        proc.stdin.write(json.dumps(dict(hook_event_name='UserPromptSubmit', session_id='a',
                                         cwd=str(log.dir), prompt='/robovac')))
        proc.stdin.close()
        time.sleep(1)
        held = log.events()
    proc.wait()
    check('L5 a hook waits while another writer holds the log\'s lock, then writes',
          held == [] and log.events() == ['start'], f'{held} {log.events()}')


def l11_say_waits_for_the_lock(tmp: Path) -> None:
    log = Log(tmp, 'l11')
    log.hook('UserPromptSubmit', prompt='/robovac')
    with open(log.dir / 'runs.jsonl.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        env = dict(log.env, CLAUDE_CODE_SESSION_ID='a')
        proc = subprocess.Popen([sys.executable, str(SCRIPT), 'say', 'sweeping'], env=env,
                                stdout=subprocess.DEVNULL)
        time.sleep(1)
        held = log.events()
    proc.wait()
    check('L11 say waits while another writer holds the log\'s lock, then writes',
          held == ['start'] and log.events() == ['start', 'say'], f'{held} {log.events()}')


def l6_a_trim_replaces_the_log_whole(tmp: Path) -> None:
    log = Log(tmp, 'l6')
    with log.path.open('w') as f:
        for n in range(4000):
            f.write(json.dumps({'t': time.time(), 'session': f'x{n}', 'project': 'p', 'event': 'say'}) + '\n')
    before = log.path.stat().st_ino
    log.hook('UserPromptSubmit', prompt='/robovac')
    lines = log.path.read_text().splitlines()
    check('L6 a trim writes the cut log aside and swaps it in, so a reader never sees a part',
          log.path.stat().st_ino != before and len(lines) == 2000
          and sorted(p.name for p in log.dir.iterdir()) == ['runs.jsonl', 'runs.jsonl.lock'],
          f'{len(lines)} lines, {sorted(p.name for p in log.dir.iterdir())}')


def l8_a_line_is_kept_to_140_characters(tmp: Path) -> None:
    log = Log(tmp, 'l8')
    log.hook('UserPromptSubmit', prompt='/robovac')
    log.run('say', 'x' * 200, sid='a')
    shown = [r.get('say') for r in json.loads(log.run('live', '--json'))]
    check('L8 a line longer than 140 characters is cut to 140', shown == ['x' * 140], str(shown))


def l9_path_prints_the_log(tmp: Path) -> None:
    log = Log(tmp, 'l9')
    check('L9 path prints where the log is', log.run('path').strip() == str(log.path),
          log.run('path'))


def l10_an_unknown_command_exits_2(tmp: Path) -> None:
    log = Log(tmp, 'l10')
    got = [subprocess.run([sys.executable, str(SCRIPT), *argv], env=log.env, capture_output=True,
                          text=True) for argv in (['sweep'], [], ['say'])]
    check('L10 an unknown command, no command, or a say with no line exits 2 with the usage',
          all(r.returncode == 2 and 'Commands' in r.stdout for r in got),
          str([(r.returncode, r.stdout[:40]) for r in got]))


def h1_a_hook_that_cannot_read_its_input(tmp: Path) -> None:
    log = Log(tmp, 'h1')
    got = [subprocess.run([sys.executable, str(SCRIPT), 'hook'], input=stdin, env=log.env,
                          capture_output=True, text=True) for stdin in ('not json', '[]', '')]
    check('H1 a hook given input it cannot read prints nothing and exits 0',
          all(r.returncode == 0 and not r.stdout and not r.stderr for r in got)
          and not log.path.exists(), str([(r.returncode, r.stdout, r.stderr[-80:]) for r in got]))


if __name__ == '__main__':
    sys.exit(main((s1_prompt_starting_with_robovac, s2_mention_is_not_a_run,
                   s3_skill_tool_starts_a_run, s4_old_start_rows_do_not_count,
                   s5_loop_mentions_are_not_runs, w1_turn_end_docks,
                   w2_next_turn_goes_again, w3_other_sessions_stay_out, w4_error_ends_the_run,
                   w5_closed_session_stays_closed, w6_mid_turn_prompt_keeps_going,
                   w7_trimmed_log_keeps_the_session, w8_stale_run_does_not_block,
                   w9_trim_keeps_an_idle_session, w10_trim_forgets_a_dead_session,
                   w11_a_week_unheard_is_forgotten, w12_six_days_idle_is_still_known,
                   w13_went_quiet_is_not_hearing, w14_closing_a_forgotten_session_logs_nothing,
                   w15_trim_counts_no_went_quiet_as_heard, w16_a_say_is_hearing,
                   e1_start_marks_the_transcript, e2_esc_after_start_is_an_interrupt,
                   e3_quoted_mark_is_not_esc, e4_esc_before_the_start_stays_behind,
                   e5_esc_as_plain_text_content, e6_esc_then_a_wake_through_the_skill,
                   e7_esc_ends_when_it_was_pressed, e8_esc_before_silence,
                   e9_esc_within_the_week_is_heard, e10_two_escs_end_at_the_first,
                   e11_the_shared_esc_lines,
                   l1_say_needs_a_working_run, l2_live_lists_working_runs,
                   l3_live_leaves_out_an_esc, l4_hooks_at_once_lose_no_line,
                   l5_a_hook_waits_for_the_lock, l11_say_waits_for_the_lock,
                   l6_a_trim_replaces_the_log_whole,
                   l8_a_line_is_kept_to_140_characters, l9_path_prints_the_log,
                   l10_an_unknown_command_exits_2, h1_a_hook_that_cannot_read_its_input)))
