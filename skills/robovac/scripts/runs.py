#!/usr/bin/env python3
'''
runs — when the agent in a robovac session is working, written by Claude Code hooks to one log the
desktop widget reads, so each session's robot sweeps while its agent works and docks when it stops.

Commands
--------
    hook                    read a hook's JSON on stdin and log what it means; installed for
                            UserPromptSubmit, PreToolUse, PostToolUse, PostToolUseFailure,
                            PostToolBatch, PermissionRequest, Elicitation, ElicitationResult,
                            Notification (the three that wait on the person), Stop, StopFailure
                            and SessionEnd. prints nothing and always exits 0, so it never holds
                            up a session.
    say "<line>"            the run's agent says, in one plain line, what the run is doing; the
                            widget shows it when the robot is hovered. run from inside the session.
    live [--json]           the runs going now, oldest first.
    path                    where the log is.

a session becomes a robovac session when a prompt starts with /robovac or the plugin's
/kstack:robovac (or /loop, an optional interval and then either), or the Skill tool runs robovac, and stays one until it closes or goes a
week unheard from. its robot has two states, out sweeping or docked with its !, tied to whether its
agent works: a run is a stretch it sweeps. it goes out when a turn of the main agent starts, loop or
not, and stays out while the turn goes on, and after it while the session's background work runs: a
background shell, or a background agent. it docks when the turn has ended and no background work
runs, when the session closes, or when the agent waits on the person, so a loop waiting for its next
wake is docked. a run heard nothing from in twelve hours counts as over, so a crashed session's
robot still goes home; an Esc counts first.

the background work is read from the hooks: a background shell's call returns its task id, a
background agent's call returns at once naming its agent, each Stop lists the tasks still running,
and a task that ends starts a turn whose prompt is its <task-notification>. the session's turn and
work are logged as a work row whenever they move other than its start and end rows say, and each
start carries the work going on as it starts.

a turn ends when it finishes (Stop), hits an API error (StopFailure) or is interrupted, and the
session closes at SessionEnd. Claude Code runs no hook for Esc, or for a prompt the person denies
with it, but writes a user line reading "[Request interrupted by user]", or "... for tool use]",
into the transcript; and an Esc landing between the turn's last reply and its Stop hook can run no
Stop hook and write no such line. so each start records the transcript's length, and while its turn
is open the next hook of any kind, and the widget as it watches, end the turn at the first Esc line
past that length, or at the last reply past it, if that reply ended its turn and is six seconds
old (the next prompt need not wait): its Stop hook, which starts within a tenth of a second and is
killed at five, can no longer land. an Esc stops every background agent but no shell, so a shell
keeps the robot out past it.

the turn waits on the person, and the robot docks, from when a question (AskUserQuestion) or an MCP
form opens, or a permission prompt or an MCP link has gone about six seconds unanswered
(Notification), until no ask that holds the wait is open, one asked after the dock included, so a
prompt answered at once never docks the robot. an answer seen at a prompt, a notice or the turn's
end leaves the run to that event instead. a wait outranks background work but not the turn's own:
while the turn goes on, the ask of an agent known to run in the background holds nothing, and once
the turn has ended, only a running background agent's ask, a form or a notice holds the robot in.
an ask is one tool call's prompt (PermissionRequest: the agent that asked, the tool, and a digest of
each input value, never the value), one MCP form (Elicitation: its server; it names no agent), or,
when a notice comes with no ask open, the notice itself. a tool call's prompt is answered by that
call's own result (PostToolUse or PostToolUseFailure from the same agent, with the same tool and an
equal digest for every value it asked with), by its agent's batch ending (PostToolBatch), which is
all a prompt denied without Esc runs, or, for a subagent's prompt denied with Esc, by the interrupt
line in that subagent's own transcript; a form by its result (ElicitationResult) or its server's
tool result; a notice by any agent's result, the main agent's batch, or any form's result. asks
count from the run's last start, a running background agent's excepted, so one an Esc'd turn left
open, or a prompt the run went out past, holds no later wait. the main agent's calls in one batch
start together, or each after the one before it ends, so none starts after a prompt in its batch,
its own or a foreground subagent's, has waited long enough to dock the robot, and its batch ends
only once they are answered: its call or its batch's end while every open ask is a subagent's shows
those are background prompts, and sends the run out with them unanswered.

after a turn finishes, errs or goes quiet, a main-agent call starts the turn again, as a turn
another Stop hook keeps going; a subagent's call never does, since no hook ends a turn it starts.

Methods
-------
    events :
        every line of the log, oldest first.
    last_heard :
        when each session was last heard from.
    locked :
        hold the lock beside the log, so one writer at a time reads it and appends to it.
    append :
        add one line to the log, trimming it when it grows long.
    runs :
        each session's run as it stands after a list of log lines.
    doing :
        each session's turn and background work as they stand after a list of log lines.
    live :
        the runs going now, oldest first.
    known :
        whether a session has run robovac, is still open, and was heard from within a week.
    digest :
        each value of a tool's input as a short hash, never the value.
    launched :
        the background task a tool call's result starts.
    asks :
        the asks a session has open.
    holds :
        whether an open ask keeps the robot docked.
    answered_by :
        the open asks one hook event answers.
    resumes :
        whether a tool call starts a session's run again.
    going_on :
        the start of a run that goes on, carrying the line its agent last gave.
    tail :
        the transcript lines past a run's start, and the file's modification time.
    stamped :
        a transcript line's own time.
    interrupted :
        when a session's transcript shows Esc pressed since a run began.
    ended :
        when a session's transcript shows its turn ended with no hook to say so.
    hook :
        log what one hook event means for its session's run.
    say :
        log a run's own one-line account of what it is doing.
    main :
        dispatch on the command named first.
'''

from __future__ import annotations

import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import math
import os
import re
import sys
import time
from pathlib import Path



LOG           = Path(os.environ.get('ROBOVAC_RUNS',
                                    Path.home() / '.claude' / 'robovac' / 'runs.jsonl'))
STALE         = 12 * 3600
ESC           = '[Request interrupted by user'
KEEP          = 2000
WAITS         = ('permission_prompt', 'elicitation_dialog', 'elicitation_url_dialog')
FORGET        = 7 * 86400
ASKED         = re.compile(r'^\s*(/loop(\s+\d+[smhd])?\s+)?/(kstack:)?robovac(?=\s|$)')
BOUNDS        = ('UserPromptSubmit', 'Notification', 'Stop', 'StopFailure', 'SessionEnd')
REPLIED       = 6
NOTIFIED      = re.compile(r'<task-id>([^<\s]+)</task-id>')


# ── the log ───────────────────────────────────────────────────────────────────

def events() -> list[dict]:
    '''every line of the log, oldest first; a line that will not parse is skipped.'''
    if not LOG.exists():
        return []
    out = []
    for line in LOG.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def last_heard(rows: list[dict]) -> dict:
    '''when each session was last heard from: its latest stamp, a went-quiet end aside, as silence.'''
    out = {}
    for row in rows:
        if row.get('why') != 'went quiet':
            sid = row.get('session')
            out[sid] = max(out.get(sid, 0), row.get('t', 0))
    return out


@contextlib.contextmanager
def locked():
    '''
    hold the lock beside the log, so one writer at a time reads it and appends to it.

    Notes
    -----
    a hook decides from what it reads, so it holds the lock from its read to its last append: two
    hooks each answering one of two asks then see each other's answer, and one of them starts the
    run. the lock goes with the file that holds it, also when the process dies.
    '''
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG.with_name(LOG.name + '.lock'), 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def append(row: dict) -> None:
    '''
    add one line to the log, trimming it when it grows long; the caller holds `locked`.

    Parameters
    ----------
    row : dict
        the event to log, written as one JSON line.

    Notes
    -----
    once the log passes twice KEEP lines, it is cut back to its newest KEEP, ahead of which go the
    lines of every robovac session still open and heard from within FORGET seconds, from its last
    start on, so a session idle through the cut is still known, and still docked, while one that
    died without closing is dropped in time. the cut log replaces the old one whole, so a reader
    sees one or the other, never a file half written.
    '''
    with LOG.open('a') as f:
        f.write(json.dumps(row) + '\n')
    lines = LOG.read_text().splitlines()
    if len(lines) <= KEEP * 2:
        return
    cut, since, rows = len(lines) - KEEP, {}, []
    for n, line in enumerate(lines):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        rows.append(r)
        if r.get('event') == 'start' and r.get('via'):
            since[r.get('session')] = n
        elif r.get('event') == 'end' and r.get('why') == 'session closed':
            since.pop(r.get('session'), None)
    heard = last_heard(rows)
    first = {s: n for s, n in since.items() if n < cut and heard.get(s, 0) > time.time() - FORGET}
    carried = [line for n, line in enumerate(lines[:cut])
               if any(n >= first[s] for s in first if f'"session": "{s}"' in line)]
    cut_log = LOG.with_name(LOG.name + '.cut')
    cut_log.write_text('\n'.join(carried + lines[cut:]) + '\n')
    os.replace(cut_log, LOG)


def runs(rows: list[dict]) -> dict:
    '''
    each session's run as it stands after a list of log lines.

    Parameters
    ----------
    rows : list of dict
        log lines, oldest first, as `events` returns them.

    Returns
    -------
    dict
        session id mapped to its run's start row, with `heard` (when it was last heard from) and
        `say` (its last line) added, or to None once it ended; a work row counts as hearing from it.
    '''
    out = {}
    for row in rows:
        sid = row.get('session')
        if row.get('event') == 'start':
            out[sid] = dict(row, heard=row['t'])
        elif row.get('event') == 'say' and out.get(sid):
            out[sid]['say'] = row['text']
            out[sid]['heard'] = row['t']
        elif row.get('event') == 'work' and out.get(sid):
            out[sid]['heard'] = row['t']
        elif row.get('event') == 'end':
            out[sid] = None
    return out


def doing(rows: list[dict]) -> dict:
    '''
    each session's turn and background work as they stand after a list of log lines.

    Parameters
    ----------
    rows : list of dict
        log lines, oldest first, as `events` returns them.

    Returns
    -------
    dict
        session id mapped to (turn, tasks): whether its main agent's turn is open, and its
        background tasks still running, task id mapped to kind ('shell', 'subagent', ...). a start
        opens the turn with the tasks it carries, a work row says both, an end other than a wait
        closes the turn with nothing running, and a wait leaves both as they were.

    Notes
    -----
    Runs.swift folds the log the same way; tests/test_runs.sh and test_work hold the two to it.
    '''
    out = {}
    for row in rows:
        event, sid = row.get('event'), row.get('session')
        if event == 'start':
            out[sid] = (True, dict(row.get('tasks') or {}))
        elif event == 'work':
            out[sid] = (bool(row.get('turn')), dict(row.get('tasks') or {}))
        elif event == 'end' and row.get('why') != 'waiting on you':
            out[sid] = (False, {})
    return out


def live(now: float | None = None) -> list[dict]:
    '''
    the runs going now, oldest first.

    Parameters
    ----------
    now : float, optional
        the time to judge by, for tests.

    Returns
    -------
    list of dict
        every open run heard from within STALE seconds, as the widget shows them, less those whose
        open turn the transcript shows ended, by an Esc or a reply no Stop hook followed, with no
        background shell left running.
    '''
    now   = time.time() if now is None else now
    rows  = events()
    work  = doing(rows)
    going = []
    for r in runs(rows).values():
        if not r or now - r['heard'] >= STALE:
            continue
        turn, tasks = work.get(r['session'], (True, {}))
        if turn and 'shell' not in tasks.values() and ended(r.get('transcript'), r.get('mark', 0),
                                                             now) is not None:
            continue
        going.append(r)
    return sorted(going, key=lambda r: r['t'])


# ── the hook ──────────────────────────────────────────────────────────────────

def known(rows: list[dict], sid: str, now: float) -> bool:
    '''
    whether a session has run robovac, is still open, and was heard from within a week.

    Parameters
    ----------
    rows : list of dict
        log lines, oldest first, as `events` returns them.
    sid : str
        the session.
    now : float
        the time to judge by.

    Returns
    -------
    bool
        True once a start is logged for the session with a `via` (prompt or skill, which the person
        asked for, or again, which is logged only in a session already known, so a log trimmed past
        the first start still knows it), until an end logged because the session closed, or until
        the session has gone FORGET seconds, a week, unheard from; a went-quiet end marks silence,
        so it is not hearing from it, while an Esc's end is.
    '''
    on = False
    for row in rows:
        if row.get('session') != sid:
            continue
        if row.get('event') == 'start' and row.get('via') in ('prompt', 'skill', 'again'):
            on = True
        elif row.get('event') == 'end' and row.get('why') == 'session closed':
            on = False
    return on and now - last_heard(rows).get(sid, 0) < FORGET


def digest(args) -> dict:
    '''each top-level value of a tool's input as 12 hex digits of its sha1, never the value.'''
    if not isinstance(args, dict):
        return {}
    return {k: hashlib.sha1(json.dumps(v, sort_keys=True).encode()).hexdigest()[:12]
            for k, v in args.items()}


def launched(payload: dict) -> tuple[str, str] | None:
    '''
    the background task a tool call's result starts, as (task id, kind), or None.

    Notes
    -----
    a background shell's Bash result carries `backgroundTaskId`; a background agent's Agent result
    comes back at once, async, naming its `agentId`, which is the id its own hooks carry.
    '''
    out = payload.get('tool_response')
    if isinstance(out, str):
        try:
            out = json.loads(out)
        except ValueError:
            return None
    if not isinstance(out, dict):
        return None
    if out.get('backgroundTaskId'):
        return str(out['backgroundTaskId']), 'shell'
    if out.get('agentId') and (out.get('isAsync') or out.get('status') == 'async_launched'):
        return str(out['agentId']), 'subagent'
    return None


def asks(rows: list[dict], sid: str, tasks: dict) -> list[dict]:
    '''
    the asks a session has open.

    Parameters
    ----------
    rows : list of dict
        log lines, oldest first, as `events` returns them.
    sid : str
        the session.
    tasks : dict
        its background tasks still running, as `doing` gives them.

    Returns
    -------
    list of dict
        the ask rows logged since the session's last start, oldest first, with those of an agent
        still running in the background from before it, less those an `answered` row names; a start
        clears the rest, so an ask a turn left open holds no later wait.
    '''
    found = {}
    for row in rows:
        if row.get('session') != sid:
            continue
        if row.get('event') == 'start':
            found = {k: a for k, a in found.items() if a.get('agent') in tasks}
        elif row.get('event') == 'ask' and row.get('id'):
            found[row['id']] = row
        elif row.get('event') == 'answered':
            found.pop(row.get('ask'), None)
    return list(found.values())


def holds(ask: dict, turn: bool, tasks: dict) -> bool:
    '''
    whether an open ask keeps the robot docked, given the session's turn and background work.

    Notes
    -----
    a form and a notice name no agent, so they always hold. while the turn goes on, a tool ask
    holds unless its agent is known to run in the background, whose wait the turn's own work
    outranks; once the turn has ended, a tool ask holds only while its agent still runs.
    '''
    if ask.get('kind') != 'tool':
        return True
    background = bool(ask.get('agent')) and ask.get('agent') in tasks
    return not background if turn else background


def answered_by(opened: list[dict], payload: dict, waiting: bool) -> list[dict]:
    '''
    the open asks one hook event answers.

    Parameters
    ----------
    opened : list of dict
        the session's open asks, oldest first, as `asks` returns them.
    payload : dict
        the hook's JSON.
    waiting : bool
        whether the session is docked waiting on the person, the only time a subagent's
        transcript is read.

    Returns
    -------
    list of dict
        the asks it answers: every tool ask of an agent at that agent's batch; at a result, the
        oldest tool ask with the same agent and tool and an equal digest for every value it holds,
        more values allowed, as a question's answers; while waiting, a subagent's tool ask once
        that subagent's transcript shows the interrupt line past where it stood at the ask; the
        oldest form of a server at that server's form result or tool result; and a notice at any
        agent's result, the main agent's batch, or any form result.
    '''
    name   = payload.get('hook_event_name')
    who    = payload.get('agent_id') or ''
    tool   = payload.get('tool_name') or ''
    result = name in ('PostToolUse', 'PostToolUseFailure')
    given  = digest(payload.get('tool_input')) if result else {}
    out, took = [], set()
    for ask in opened:
        kind, agent = ask.get('kind'), ask.get('agent')
        if kind == 'tool':
            mine = agent == who and (name == 'PostToolBatch' or result and 'tool' not in took
                                     and tool == ask.get('tool')
                                     and all(given.get(k) == v
                                             for k, v in ask.get('keys', {}).items()))
            if mine and name != 'PostToolBatch':
                took.add('tool')
            if mine or waiting and agent and interrupted(ask.get('transcript'),
                                                         ask.get('mark', 0)) is not None:
                out.append(ask)
        elif kind == 'form':
            server = ask.get('server')
            if 'form' not in took and (name == 'ElicitationResult'
                                       and payload.get('mcp_server_name') == server
                                       or result and tool.startswith(f'mcp__{server}__')):
                took.add('form')
                out.append(ask)
        elif result or name == 'ElicitationResult' or name == 'PostToolBatch' and not who:
            out.append(ask)
    return out


def resumes(rows: list[dict], sid: str, who: str, now: float, opened: list[dict]) -> bool:
    '''
    whether a tool call starts a session's run again.

    Parameters
    ----------
    rows : list of dict
        log lines, oldest first, the hook's own new ends included.
    sid : str
        the session, which has no run going.
    who : str
        the agent making the call: '' for the main agent, else the subagent's id.
    now : float
        the time to judge by.
    opened : list of dict
        the session's asks still open after this hook's answers.

    Returns
    -------
    bool
        True for a known session's main agent, after a run that finished, erred or went quiet, as a
        turn another Stop hook keeps going; and while the run is docked waiting, when every open ask
        is a subagent's tool prompt, since the main agent starts no call and ends no batch after a
        prompt of its own or of a foreground subagent docked it. False for a subagent's call, and
        after an Esc, until the next prompt.
    '''
    ends = [r for r in rows if r.get('session') == sid and r.get('event') == 'end']
    why  = ends[-1].get('why') if ends else None
    if who or why == 'interrupted' or not known(rows, sid, now):
        return False
    background = all(a.get('kind') == 'tool' and a.get('agent') for a in opened)
    return why != 'waiting on you' or background


def going_on(rows: list[dict], sid: str, began: dict) -> dict:
    '''the start of a run that goes on, carrying the line its agent last gave.'''
    last = next((r for r in reversed(rows) if r.get('session') == sid
                 and r.get('event') in ('start', 'say')), {})
    line = last.get('text') if last.get('event') == 'say' else last.get('say')
    return dict(began, via='again', **({'say': line} if line else {}))


def tail(transcript: str | None, mark: int) -> tuple[list[str], float] | None:
    '''
    the transcript's lines past `mark`, its length in bytes when the run began, within its last
    256 KB, with the file's modification time; None when there is no transcript or it won't read.
    '''
    if not transcript:
        return None
    try:
        with open(transcript, 'rb') as f:
            f.seek(0, 2)
            f.seek(max(mark, f.tell() - 262144))
            text = f.read().decode('utf-8', 'replace')
            written = os.fstat(f.fileno()).st_mtime
    except OSError:
        return None
    return text.splitlines(), written


def stamped(row: dict, written: float) -> float:
    '''a transcript line's own time, else the file's modification time.'''
    try:
        return dt.datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00')).timestamp()
    except (KeyError, AttributeError, ValueError):
        return written


def interrupted(transcript: str | None, mark: int) -> float | None:
    '''
    when a session's transcript shows Esc pressed since a run began.

    Parameters
    ----------
    transcript : str or None
        the transcript's path, as the run's start recorded it.
    mark : int
        the transcript's length in bytes when the run began.

    Returns
    -------
    float or None
        the time stamped on the first user line past `mark`, within the transcript's last 256 KB,
        whose text starts with "[Request interrupted by user", or the transcript's modification time
        when it carries no stamp that parses, as Runs.swift reads it (tests/esc_lines.json holds
        both to the same lines); the same words quoted in a tool result or mid-message are not an
        Esc. None when there is no transcript, it cannot be read, or it shows no Esc.
    '''
    lines, written = tail(transcript, mark) or ([], 0.0)
    for line in lines:
        if ESC not in line:
            continue
        try:
            row = json.loads(line)
            content = row['message']['content']
        except (ValueError, KeyError, TypeError):
            continue
        parts = [content] if isinstance(content, str) else [
            c.get('text', '') for c in content if isinstance(c, dict)]
        if row.get('type') == 'user' and any(p.startswith(ESC) for p in parts):
            return stamped(row, written)
    return None


def ended(transcript: str | None, mark: int, now: float) -> float | None:
    '''
    when a session's transcript shows its turn ended since a run began with no hook to say so.

    Parameters
    ----------
    transcript : str or None
        the transcript's path, as the run's start recorded it.
    mark : int
        the transcript's length in bytes when the run began.
    now : float
        the time to judge by; infinity at a new prompt, which shows the turn before it is over.

    Returns
    -------
    float or None
        the first Esc past `mark`, as `interrupted` reads it; else the time of the main agent's
        last assistant line past `mark`, a subagent's line (`isSidechain`) skipped, if its message
        stopped as `end_turn` and that time is REPLIED seconds before `now`: the reply that ended
        its turn, whose Stop hook would have landed by then. None otherwise, so a turn thinking or
        running a tool, which writes nothing until it ends, is never ended by silence. Runs.swift's
        turnEnded reads the same lines.
    '''
    esc = interrupted(transcript, mark)
    if esc is not None:
        return esc
    lines, written = tail(transcript, mark) or ([], 0.0)
    for line in reversed(lines):
        if '"assistant"' not in line:
            continue
        try:
            row = json.loads(line)
            stop = row['message'].get('stop_reason')
        except (ValueError, KeyError, TypeError, AttributeError):
            continue
        if row.get('type') != 'assistant' or row.get('isSidechain'):
            continue
        at = stamped(row, written)
        return at if stop == 'end_turn' and now - at >= REPLIED else None
    return None


def hook(payload: dict, now: float | None = None) -> str | None:
    '''
    log what one hook event means for its session's run.

    Parameters
    ----------
    payload : dict
        the hook's JSON: hook_event_name, session_id, cwd, and the event's own fields.
    now : float, optional
        the time to stamp, for tests.

    Returns
    -------
    str or None
        'start' or 'end' for a run it starts or ends, or None when the run stands as it was, an
        ask or its answer included; a prompt that both ends an interrupted run and starts a new one
        returns 'start'.

    Notes
    -----
    it holds `locked` from its read of the log to its last append, so hooks fired at once, as
    PostToolUse is for parallel calls, each decide from what the one before wrote.
    '''
    now  = time.time() if now is None else now
    name = payload.get('hook_event_name')
    sid  = payload.get('session_id')
    who  = payload.get('agent_id') or ''
    cwd  = payload.get('cwd') or os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()
    with locked():
        rows = events()
        run  = runs(rows).get(sid)
        mine = [r for r in rows if r.get('session') == sid and r.get('event') in ('start', 'end')]
        row  = dict(t=now, session=sid, project=Path(cwd).name)
        turn, tasks = doing(rows).get(sid, (False, {}))

        def put(new: dict) -> None:
            rows.append(new)
            append(new)

        #an open turn, going or docked waiting, ends at an Esc or a reply no Stop hook followed; a
        #new prompt shows that reply ended its turn at once, and a turn's own Stop says it did...
        logged  = None
        waiting = not run and mine[-1:] != [] and mine[-1].get('why') == 'waiting on you'
        since   = run or (next((r for r in reversed(mine) if r['event'] == 'start'), None)
                          if waiting else None)
        upto    = {'UserPromptSubmit': math.inf, 'Stop': -math.inf,
                   'StopFailure': -math.inf}.get(name, now)
        at      = (ended(since.get('transcript'), since.get('mark', 0), upto) if since and turn
                   else None)

        #which stops every background agent but no shell, so a shell keeps the robot out...
        if at is not None:
            turn, tasks = False, {k: v for k, v in tasks.items() if v == 'shell'}
            if not tasks:
                put(dict(row, t=at, event='end', why='interrupted'))
                run, waiting, logged = None, False, 'end'

        #a run silent past STALE is over, as in `live` and the widget, from when it went quiet...
        if run and now - run['heard'] >= STALE:
            put(dict(row, t=run['heard'] + STALE, event='end', why='went quiet'))
            run, logged = None, 'end'
            turn, tasks = False, {}

        #the background work this event starts, ends, or lists as still running...
        task = launched(payload) if name == 'PostToolUse' and (run or waiting) else None
        if task:
            tasks[task[0]] = task[1]
        if name == 'UserPromptSubmit':
            for told in NOTIFIED.findall(payload.get('prompt') or ''):
                tasks.pop(told, None)
        listed = payload.get('background_tasks')
        if name == 'Stop' and (run or waiting) and isinstance(listed, list):
            tasks = {str(t['id']): str(t.get('type')) for t in listed
                     if isinstance(t, dict) and t.get('id') and t.get('status') == 'running'}

        #where the transcript stands as a run starts, so an end can be found past it later...
        path = payload.get('transcript_path')
        try:
            mark = os.path.getsize(path) if path else 0
        except OSError:
            mark = 0
        began = dict(row, event='start', cwd=cwd, transcript=path, mark=mark, tasks=dict(tasks))

        #a wait an Esc ended goes out to the shells still running...
        if at is not None and waiting:
            run = going_on(rows, sid, began)
            put(run)
            waiting, logged = False, 'start'

        #each ask this event answers is logged, and the last one holding a wait sends it out...
        opened = asks(rows, sid, tasks)
        done   = answered_by(opened, payload, waiting)
        for ask in done:
            put(dict(row, event='answered', ask=ask['id']))
        opened = [a for a in opened if a not in done]

        #but not at a turn's end, a prompt or a notice, which each decide the run themselves...
        if done and waiting and not any(holds(a, turn, tasks) for a in opened) and name not in BOUNDS:
            run = going_on(rows, sid, began)
            put(run)
            waiting, logged = False, 'start'

        #a prompt starts a turn, with the run's line if work kept the robot out past the last one...
        ask = dict(row, event='ask', id=os.urandom(6).hex())
        if name == 'UserPromptSubmit':
            asked = ASKED.search(payload.get('prompt') or '')
            if not (run and turn) and (asked or known(rows, sid, now)):
                via = 'prompt' if asked else 'again'
                put(dict(going_on(rows, sid, began) if run else began, via=via))
                run, turn, logged = rows[-1], True, 'start'
        elif name in ('PreToolUse', 'PostToolBatch'):
            tool, args = payload.get('tool_name'), payload.get('tool_input') or {}

            #a main-agent call past a Stop that left work running opens the turn again...
            if run:
                turn = turn or not who
            elif tool == 'Skill' and str(args.get('skill', '')).split(':')[-1] == 'robovac':
                put(dict(began, via='skill'))
                run, turn, logged = rows[-1], True, 'start'
            elif resumes(rows, sid, who, now, opened):
                put(going_on(rows, sid, began))
                run, turn, logged = rows[-1], True, 'start'

        #an ask is logged only in a run going or docked waiting, under an id its answer names; a
        #question or a form docks the robot as it opens, a prompt only at its notice...
        elif name == 'PermissionRequest' and (run or waiting):
            ask.update(kind='tool', agent=who, tool=payload.get('tool_name'),
                       keys=digest(payload.get('tool_input')))
            if who and path:
                own = Path(path).with_suffix('') / 'subagents' / f'agent-{who}.jsonl'
                try:
                    ask.update(transcript=str(own), mark=own.stat().st_size)
                except OSError:
                    ask.update(transcript=str(own), mark=0)
            put(ask)
            if run and ask['tool'] == 'AskUserQuestion' and holds(ask, turn, tasks):
                put(dict(row, event='end', why='waiting on you'))
                run, logged = None, 'end'
        elif name == 'Elicitation' and (run or waiting):
            put(dict(ask, kind='form', server=payload.get('mcp_server_name')))
            if run:
                put(dict(row, event='end', why='waiting on you'))
                run, logged = None, 'end'
        elif name == 'Notification' and payload.get('notification_type') in WAITS:
            if (run or waiting) and not opened:
                put(dict(ask, kind='notice'))
                opened = [rows[-1]]
            if run and any(holds(a, turn, tasks) for a in opened):
                put(dict(row, event='end', why='waiting on you'))
                run, logged = None, 'end'

        #a turn's end docks the robot unless work still runs; a running agent's ask outranks it...
        elif name in ('Stop', 'StopFailure') and (run or waiting):
            turn = False
            held = [a for a in opened if a.get('kind') == 'tool' and holds(a, turn, tasks)]
            if held and run:
                put(dict(row, event='end', why='waiting on you'))
                run, logged = None, 'end'
            elif not held and tasks and waiting:
                put(going_on(rows, sid, began))
                run, logged = rows[-1], 'start'
            elif not held and not tasks:
                why = 'finished' if name == 'Stop' else f"error: {payload.get('error', 'unknown')}"
                put(dict(row, event='end', why=why))
                run, logged = None, 'end'
        elif name == 'SessionEnd' and (run or known(rows, sid, now)):
            put(dict(row, event='end', why='session closed'))
            run, turn, tasks, logged = None, False, {}, 'end'

        #the turn and the work as this event leaves them, where the rows so far say otherwise...
        if doing(rows).get(sid, (False, {})) != (turn, tasks):
            put(dict(row, event='work', turn=turn, tasks=tasks))
        return logged


def say(line: str, sid: str | None, now: float | None = None) -> bool:
    '''
    log a run's own one-line account of what it is doing, if its session has a run going, or one
    waiting on the person, whose approved tool is what gives the line.

    Parameters
    ----------
    line : str
        what the run is doing, in one plain line; kept to 140 characters.
    sid : str or None
        the session, as CLAUDE_CODE_SESSION_ID gives it inside the session.
    now : float, optional
        the time to stamp, for tests.

    Returns
    -------
    bool
        whether a run was there to take the line; one taken while the run waits shows once the
        run goes on, whose start carries the line.
    '''
    text = ' '.join(line.split())[:140]
    with locked():
        rows = events()
        ends = [r.get('why') for r in rows if r.get('session') == sid and r.get('event') == 'end']

        #a line given by the tool a person approved lands while the wait still docks the run...
        if not text or not sid or not (runs(rows).get(sid) or ends[-1:] == ['waiting on you']):
            return False
        append(dict(t=time.time() if now is None else now, session=sid, event='say', text=text))
        return True


# ── main ──────────────────────────────────────────────────────────────────────

def main(argv: list[str]) -> int:
    '''
    dispatch on the command named first.

    Parameters
    ----------
    argv : list of str
        the whole command line, the script's own name first.

    Returns
    -------
    int
        0 for a known command, `hook` included whatever it hit; 2, with this docstring printed,
        for an unknown one or a `say` with no line.
    '''
    if argv[1:2] == ['hook']:
        try:
            hook(json.load(sys.stdin))
        except Exception:
            pass
        return 0
    if argv[1:2] == ['say'] and len(argv) > 2:
        said = say(' '.join(argv[2:]), os.environ.get('CLAUDE_CODE_SESSION_ID'))
        print('noted' if said else 'no robovac run in this session, nothing noted')
        return 0
    if argv[1:2] == ['live']:
        going = live()
        if '--json' in argv:
            print(json.dumps(going))
        for r in [] if '--json' in argv else going:
            print(f"{r['session']}  {r['project']}  "
                  f"since {time.strftime('%H:%M', time.localtime(r['t']))}")
        return 0
    if argv[1:2] == ['path']:
        print(LOG)
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
