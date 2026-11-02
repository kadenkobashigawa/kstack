#!/usr/bin/env python3
"""
test_ledger — runs ledger.py on a small fake session transcript whose usage records are known, and
checks the per-agent rows and the totals.

Run it with `python3 test_ledger.py`. Each check prints its label, which says what it holds, and
the exit code is the number of failed checks. The totals must equal the sums of the usage records;
a ledger that sums the completion notices' subagent_tokens fails L2 and L3.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile


SCRIPT   = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts', 'ledger.py')
MEASURE  = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'references',
                        'measure.md')
SESSION  = '11111111-2222-3333-4444-555555555555'
PARENT   = '99999999-8888-7777-6666-555555555555'
FORK     = '22222222-3333-4444-5555-666666666666'
CUT      = '33333333-4444-5555-6666-777777777777'
COPY     = '44444444-5555-6666-7777-888888888888'
LOST     = '77777777-6666-5555-4444-333333333333'
GROW     = '55555555-6666-7777-8888-999999999999'
WORKDIR  = '/work/my.project'
failures = 0


def check(label: str, ok: bool, detail: str = '') -> None:
    global failures
    print(('ok    ' if ok else 'FAIL  ') + label)
    if not ok:
        failures += 1
        print('      ' + detail.replace('\n', '\n      '))


def ledger(*args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True,
                          env={**os.environ, **(env or {})})


def usage(i: int, cw: int, cr: int, o: int) -> dict:
    return {'input_tokens': i, 'cache_creation_input_tokens': cw, 'cache_read_input_tokens': cr,
            'output_tokens': o, 'service_tier': 'standard'}


def reply(mid: str, u: dict, at: str, blocks: list[dict], model: str = 'claude-test-1',
          **extra) -> list[dict]:
    """One request, written once per content block with the same message id, as Claude Code does."""
    return [{'type': 'assistant', 'timestamp': at, **extra,
             'message': {'id': mid, 'model': model, 'role': 'assistant', 'content': [b],
                         'usage': u}} for b in blocks]


def notice(aid: str, tokens: int) -> str:
    return (f'<task-notification>\n<task-id>{aid}</task-id>\n<status>completed</status>\n'
            f'<usage><subagent_tokens>{tokens}</subagent_tokens><tool_uses>1</tool_uses>'
            f'<duration_ms>1000</duration_ms></usage>\n</task-notification>')


def write(path: str, rows: list[dict], tail: str | bytes = '', sid: str = '') -> None:
    """Rows as JSON lines, each given `sid` as its sessionId unless it names one, then `tail`."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    body = ''.join(json.dumps({'sessionId': sid, **r} if sid else r) + '\n' for r in rows)
    with open(path, 'wb') as f:
        f.write(body.encode() + (tail if isinstance(tail, bytes) else tail.encode()))


def session(project: str) -> str:
    """
    A session with two root requests and two subagents, one under a workflow folder.

    Records:  root    r1 (1, 10, 100, 5)  r2 (2, 0, 200, 7)
              aaa     a1 (3, 1000, 0, 40)  a2 (1, 20, 300, 9), plus a synthetic reply
              bbb     b1 (5, 500, 1000, 60)
    Notices:  aaa 330 (its last request), bbb 50, and a fake aaa 777777 inside a tool result.
    """
    main = os.path.join(project, SESSION + '.jsonl')
    write(main, [
        {'type': 'user', 'timestamp': '2026-01-01T10:00:00Z', 'message': {'role': 'user',
                                                                         'content': 'go'}},
        *reply('r1', usage(1, 10, 100, 5), '2026-01-01T10:00:01Z',
               [{'type': 'thinking', 'thinking': ''}, {'type': 'tool_use', 'id': 'rt1'}]),
        *reply('r2', usage(2, 0, 200, 7), '2026-01-01T10:05:00Z', [{'type': 'text', 'text': ''}]),
        {'type': 'queue-operation', 'timestamp': '2026-01-01T10:04:00Z',
         'content': notice('aaa', 330)},
        {'type': 'user', 'timestamp': '2026-01-01T10:04:00Z',
         'message': {'role': 'user', 'content': notice('aaa', 330)}},
        {'type': 'user', 'timestamp': '2026-01-01T10:04:30Z',
         'message': {'role': 'user', 'content': [{'type': 'text', 'text': notice('bbb', 50)}]}},
        {'type': 'user', 'timestamp': '2026-01-01T10:04:40Z',
         'message': {'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': 'rt1',
                                                  'content': notice('aaa', 777777)}]}},
    ], sid=SESSION)
    subs = os.path.join(project, SESSION, 'subagents')
    write(os.path.join(subs, 'agent-aaa.jsonl'), [
        {'type': 'user', 'timestamp': '2026-01-01T10:01:00Z', 'isSidechain': True,
         'message': {'role': 'user', 'content': 'brief'}},
        *reply('a1', usage(3, 1000, 0, 40), '2026-01-01T10:01:10Z',
               [{'type': 'tool_use', 'id': 't1'}, {'type': 'text', 'text': ''}],
               isSidechain=True),
        *reply('a2', usage(1, 20, 300, 9), '2026-01-01T10:02:00Z',
               [{'type': 'tool_use', 'id': 't2'}], isSidechain=True),
        *reply('s1', usage(9, 9, 9, 9), '2026-01-01T10:02:40Z',
               [{'type': 'text', 'text': ''}], model='<synthetic>', isSidechain=True),
    ], tail='{"type": "assistant", "cut sho', sid=SESSION)
    with open(os.path.join(subs, 'agent-aaa.meta.json'), 'w') as f:
        json.dump({'agentType': 'general-purpose', 'description': 'writer one'}, f)
    wf = os.path.join(subs, 'workflows', 'wf_1')
    write(os.path.join(wf, 'agent-bbb.jsonl'), [
        *reply('b1', usage(5, 500, 1000, 60), '2026-01-01T10:03:00Z',
               [{'type': 'text', 'text': ''}], isSidechain=True),
    ], sid=SESSION)
    with open(os.path.join(wf, 'agent-bbb.meta.json'), 'w') as f:
        json.dump({'agentType': 'researcher', 'description': 'prior art'}, f)
    return main


def fork(project: str) -> str:
    """
    A session forked from PARENT, whose transcripts carry copies of the parent's records. PARENT's
    own transcript sits beside it, so its transcript counts that work.

    Records:  root    a file-history delta with no sessionId and the parent's time, as a fork
                      copies it, p1 (1000, 0, 0, 1) and p2 (2000, 0, 0, 2) copied from PARENT,
                      f1 (4, 0, 40, 4) its own at 11:00:00 and its own user record at 11:00:30
              ccc     c1 (7000, 0, 0, 7) copied from PARENT: an agent the parent ran
              ddd     d1 (3, 30, 0, 3) its own
    """
    write(os.path.join(project, PARENT + '.jsonl'), [
        *reply('p1', usage(1000, 0, 0, 1), '2026-01-01T09:00:00Z',
               [{'type': 'text', 'text': ''}]),
    ], sid=PARENT)
    main = os.path.join(project, FORK + '.jsonl')
    write(main, [
        {'type': 'file-history-delta', 'timestamp': '2026-01-01T08:00:00Z'},
        *reply('p1', usage(1000, 0, 0, 1), '2026-01-01T09:00:00Z',
               [{'type': 'text', 'text': ''}], sessionId=PARENT),
        *reply('p2', usage(2000, 0, 0, 2), '2026-01-01T09:01:00Z',
               [{'type': 'tool_use', 'id': 'pt1'}], sessionId=PARENT),
        *reply('f1', usage(4, 0, 40, 4), '2026-01-01T11:00:00Z',
               [{'type': 'text', 'text': ''}], sessionId=FORK),
        {'type': 'user', 'timestamp': '2026-01-01T11:00:30Z', 'sessionId': FORK,
         'message': {'role': 'user', 'content': 'next'}},
    ])
    subs = os.path.join(project, FORK, 'subagents')
    write(os.path.join(subs, 'agent-ccc.jsonl'), [
        *reply('c1', usage(7000, 0, 0, 7), '2026-01-01T09:00:30Z',
               [{'type': 'text', 'text': ''}], isSidechain=True, sessionId=PARENT),
    ])
    write(os.path.join(subs, 'agent-ddd.jsonl'), [
        *reply('d1', usage(3, 30, 0, 3), '2026-01-01T11:00:10Z',
               [{'type': 'text', 'text': ''}], isSidechain=True, sessionId=FORK),
    ])
    return main


def orphan(project: str) -> str:
    """
    A session copied from LOST, whose own transcript is not on the machine, so the copies are the
    only record of LOST's work. Every request record carries LOST's sessionId, as a copy does.

    Records:  root    l1 (100, 0, 0, 1) copied, a notice for eee of 60 copied, and the session's
                      own title record with no request
              eee     e1 (50, 5, 0, 5) copied: an agent LOST ran
    """
    main = os.path.join(project, COPY + '.jsonl')
    write(main, [
        *reply('l1', usage(100, 0, 0, 1), '2026-01-01T07:00:00Z',
               [{'type': 'text', 'text': ''}], sessionId=LOST),
        {'type': 'user', 'timestamp': '2026-01-01T07:02:00Z', 'sessionId': LOST,
         'message': {'role': 'user', 'content': notice('eee', 60)}},
        {'type': 'custom-title', 'sessionId': COPY},
    ])
    write(os.path.join(project, COPY, 'subagents', 'agent-eee.jsonl'), [
        *reply('e1', usage(50, 5, 0, 5), '2026-01-01T07:01:00Z',
               [{'type': 'text', 'text': ''}], isSidechain=True, sessionId=LOST),
    ])
    return main


def machine(top: str) -> None:
    """
    A projects folder with no transcript of session A, two forks of A in two folders, a fork of a
    fork, an empty transcript of session E with one copy of it, and a request written three times.

    Records:  A       a1 (100, 0, 0, 0), and ax1 (1000, 0, 0, 0) in agent x: copies only
              p1/B    a1 and x copied from A, b1 (10, 0, 0, 0) its own
              p1/C    a1 and x copied from A, b1 copied from B, c1 (1, 0, 0, 0) its own
              p2-kit/D  a1 and x copied from A, d1 (2, 0, 0, 0) and d2 its own, d2 written
                      (2, 0, 0, 3), then (2, 0, 0, 8), then later with zeros
              p3/E    empty;  p3/G  e1 (500, 0, 0, 0) copied from E, g1 (5, 0, 0, 0) its own
    Each request once: 8 requests, 1620 input, 8 output, 1628 tokens; a1, ax1 and b1 sit in more
    than one transcript.
    """
    def one(sid: str, mid: str, tok: int, at: str, out: int = 0, **extra) -> list[dict]:
        return reply(mid, usage(tok, 0, 0, out), at, [{'type': 'text', 'text': ''}],
                     sessionId=sid, **extra)

    a1, ax1 = one('A', 'a1', 100, '2026-01-01T00:00:00Z'), one('A', 'ax1', 1000,
                                                                '2026-01-01T00:01:00Z',
                                                                isSidechain=True)
    b1 = one('B', 'b1', 10, '2026-01-02T00:00:00Z')
    for folder, sid, rows in (
            ('p1', 'B', a1 + b1),
            ('p1', 'C', a1 + b1 + one('C', 'c1', 1, '2026-01-03T00:00:00Z')),
            ('p2-kit', 'D', a1 + one('D', 'd1', 2, '2026-01-04T00:00:00Z')
             + one('D', 'd2', 2, '2026-01-04T00:01:00Z', 3)
             + one('D', 'd2', 2, '2026-01-04T00:01:00Z', 8)
             + [{'type': 'user', 'sessionId': 'D', 'message': {'role': 'user', 'content': 'x'}}]
             + one('D', 'd2', 0, '2026-01-04T00:01:00Z'))):
        write(os.path.join(top, folder, sid + '.jsonl'), rows)
        write(os.path.join(top, folder, sid, 'subagents', 'agent-x.jsonl'), ax1)
    write(os.path.join(top, 'p3', 'E.jsonl'), [])
    write(os.path.join(top, 'p3', 'G.jsonl'), one('E', 'e1', 500, '2026-01-05T00:00:00Z')
          + one('G', 'g1', 5, '2026-01-06T00:00:00Z'))


def one(sid: str, mid: str, tok: int, at: str, **extra) -> list[dict]:
    """One request of `tok` uncached input tokens, made by session `sid`."""
    return reply(mid, usage(tok, 0, 0, 0), at, [{'type': 'text', 'text': ''}], sessionId=sid,
                 **extra)


def partition(top: str) -> None:
    """
    A machine with every way a request can sit in more than one transcript, or outside the agent
    transcripts, each token count a distinct power of two so a sum shows what it holds.

    A       gone: a1 (1) in its root and ax1 (2) in its agent x, as copies only
    p1/B    forked from A: a1 and x copied, b1 (4) its own, agent y with y1 (8), and agent y2,
            y's fork, carrying y1 under B's id with y2 (16)
    p1/C    forked from B: a1, b1, x, y and y2 copied, c1 (32) its own, and c2 (64) its own with
            isSidechain set in its session transcript
    p2/D    d1 (128);  p3/D: the same session again, d1 and d2 (256), agent z with z1 (512)
    """
    a1  = one('A', 'a1', 1, '2026-01-01T00:00:00Z')
    ax1 = one('A', 'ax1', 2, '2026-01-01T00:01:00Z', isSidechain=True)
    b1  = one('B', 'b1', 4, '2026-01-02T00:00:00Z')
    y1  = one('B', 'y1', 8, '2026-01-02T00:01:00Z', isSidechain=True)
    y2  = y1 + one('B', 'y2', 16, '2026-01-02T00:02:00Z', isSidechain=True)
    d1  = one('D', 'd1', 128, '2026-01-04T00:00:00Z')
    for sid, rows in (('B', a1 + b1), ('C', a1 + b1 + one('C', 'c1', 32, '2026-01-03T00:00:00Z')
                                       + one('C', 'c2', 64, '2026-01-03T00:01:00Z',
                                             isSidechain=True))):
        write(os.path.join(top, 'p1', sid + '.jsonl'), rows)
        for aid, recs in (('x', ax1), ('y', y1), ('y2', y2)):
            write(os.path.join(top, 'p1', sid, 'subagents', f'agent-{aid}.jsonl'), recs)
    write(os.path.join(top, 'p2', 'D.jsonl'), d1)
    write(os.path.join(top, 'p3', 'D.jsonl'), d1 + one('D', 'd2', 256, '2026-01-04T00:01:00Z'))
    write(os.path.join(top, 'p3', 'D', 'subagents', 'agent-z.jsonl'),
          one('D', 'z1', 512, '2026-01-04T00:02:00Z', isSidechain=True))


def forks(top: str) -> str:
    """
    A session B whose agent b1 forks into b2, so b2 carries b1's m3 under B's own id, with a
    notice for each: b1 100 (m3), b2 1000 (m4, its last). Each request once, they processed 1100.
    """
    main = os.path.join(top, 'p', 'B.jsonl')
    write(main, one('B', 'm2', 10, '2026-01-02T00:00:00Z') + [
        {'type': 'user', 'sessionId': 'B', 'timestamp': '2026-01-02T00:01:00Z',
         'message': {'role': 'user', 'content': notice('b1', 100)}},
        {'type': 'user', 'sessionId': 'B', 'timestamp': '2026-01-02T00:02:00Z',
         'message': {'role': 'user', 'content': notice('b2', 1000)}}])
    m3 = one('B', 'm3', 100, '2026-01-02T00:00:10Z', isSidechain=True)
    write(os.path.join(top, 'p', 'B', 'subagents', 'agent-b1.jsonl'), m3)
    write(os.path.join(top, 'p', 'B', 'subagents', 'agent-b2.jsonl'),
          m3 + one('B', 'm4', 1000, '2026-01-02T00:00:20Z', isSidechain=True))
    return main


def dedupe(top: str) -> dict[str, tuple]:
    """
    Each request id under `top` with the usage of its record whose four counts sum highest, read
    from every .jsonl at any depth: a count written independently of ledger.py's.
    """
    best = {}
    for d, _, names in os.walk(top):
        for n in names:
            if not n.endswith('.jsonl'):
                continue
            for line in open(os.path.join(d, n), encoding='utf-8'):
                o = json.loads(line)
                m = o.get('message') or {}
                if o.get('type') == 'assistant' and m.get('usage'):
                    u = tuple(m['usage'][k] for k in ('input_tokens', 'cache_creation_input_tokens',
                                                      'cache_read_input_tokens', 'output_tokens'))
                    if sum(u) >= sum(best.get(m['id'], (-1,))):
                        best[m['id']] = u
    return best


def parse(out: str) -> dict[str, list[str]]:
    """Each row's cells by its first cell. A total row has no type or model, so it is shorter."""
    rows = {}
    for line in out.splitlines():
        cells = line.split()
        if cells and cells[0] != 'agent' and len(cells) > 8:
            rows[cells[0]] = cells
    return rows


def snapshot(top: str) -> list[tuple]:
    return sorted((os.path.relpath(os.path.join(d, n), top),
                   os.stat(os.path.join(d, n)).st_size, os.stat(os.path.join(d, n)).st_mtime_ns)
                  for d, _, names in os.walk(top) for n in names)


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        home    = os.path.join(tmp, 'claude')
        project = os.path.join(home, 'projects', '-work-my-project')
        path    = session(project)
        before  = snapshot(tmp)
        p       = ledger(path)
        rows    = parse(p.stdout)
        after   = snapshot(tmp)

        a, b = rows.get('aaa', []), rows.get('bbb', [])
        check('L1 an agent row counts each message id once, skips a synthetic reply and a cut '
              'line, and shows its type, model, tools and span',
              p.returncode == 0
              and a[1:11] == ['general-purpose', 'claude-test-1', '2', '4', '1020', '300', '49',
                              '1373', '2', '100']
              and b[1:11] == ['researcher', 'claude-test-1', '1', '5', '500', '1000', '60',
                              '1565', '0', '0'], p.stdout + p.stderr)

        subs = rows.get('subagents', [])
        check('L2 the subagents total is the sum of the usage records (9, 1520, 1300, 109, total '
              '2938), not the sum of the notices (380)',
              subs[1:7] == ['3', '9', '1520', '1300', '109', '2938'] and '380' not in subs,
              p.stdout)

        root, whole = rows.get('root', []), rows.get('session', [])
        check('L3 the root row reads the session transcript\'s own requests, and the session row '
              'adds root and subagents',
              root[1:7] == ['2', '3', '10', '300', '12', '325']
              and whole[1:7] == ['5', '12', '1530', '1600', '121', '3263'], p.stdout)

        check('L4 the notice column holds each agent\'s subagent_tokens from the harness\'s own '
              'notice, never one quoted inside a tool result, and the last column matches it '
              'for aaa', a[11:13] == ['330', '330'] and b[11:13] == ['1565', '50']
              and '777777' not in p.stdout, p.stdout)

        check('L5 the summary line counts agents whose notice equals their last request, and sets '
              'their processed tokens (2938) beside their notices\' sum (380)',
              'notice equals the last request in 1 of the 2 with a notice; those 2 processed 2938 '
              'tokens and their notices sum to 380' in p.stdout, p.stdout)

        q = ledger('--session', SESSION, '--project', WORKDIR, env={'CLAUDE_CONFIG_DIR': home})
        r = ledger('--session', SESSION, '--project', '-work-my-project',
                   env={'CLAUDE_CONFIG_DIR': home})
        check('L6 --session with --project finds the transcript from the working directory or '
              'the project folder\'s name, and prints the same table',
              q.returncode == 0 and q.stdout == p.stdout and r.stdout == p.stdout,
              q.stdout + q.stderr + r.stderr)

        miss = ledger('--session', 'nope', '--project', WORKDIR, env={'CLAUDE_CONFIG_DIR': home})
        none = ledger()
        check('L7 a missing transcript or no input exits 2 with a message',
              miss.returncode == 2 and 'nope.jsonl' in miss.stderr
              and none.returncode == 2 and 'ledger:' in none.stderr, miss.stderr + none.stderr)

        check('L8 the script writes nothing next to the transcripts', before == after,
              f'{before}\n{after}')

        f    = ledger(fork(project))
        frow = parse(f.stdout)
        check('L9 a forked session counts only records with its own sessionId: the root row '
              'holds its one request, an agent transcript copied from the parent gets no row, '
              'and the copies are listed under the table by the session that made them, with how '
              'many of their ids that session\'s own transcript holds (p1 of p1, p2, c1)',
              f.returncode == 0
              and frow.get('root', [])[1:7] == ['1', '4', '0', '40', '4', '48']
              and 'ccc' not in frow and frow.get('ddd', [])[3:9] == ['1', '3', '30', '0', '3', '36']
              and frow.get('subagents', [])[1:7] == ['1', '3', '30', '0', '3', '36']
              and frow.get('session', [])[1:7] == ['2', '7', '30', '40', '7', '84']
              and f'{PARENT}: 2 root requests and 1 agent request in 1 agent transcript, 10010 '
                  'tokens; its own transcripts hold 1 of these 3 ids' in f.stdout,
              f.stdout + f.stderr)

        rel = subprocess.run([sys.executable, SCRIPT, FORK + '.jsonl'], capture_output=True,
                             text=True, cwd=project)
        check('L15 a transcript named relative to its own folder finds the earlier session\'s '
              'transcript as an absolute path does, and prints the same output',
              rel.returncode == 0 and rel.stdout == f.stdout, rel.stdout + rel.stderr)

        check('L11 a forked session\'s root secs spans only its own records, not a copied '
              'file-history record with no sessionId and the parent\'s time',
              frow.get('root', [])[8] == '30', f.stdout)

        o    = ledger(orphan(project))
        orow = parse(o.stdout)
        check('L14 a session copied from one whose own transcript is not on the machine still '
              'counts none of the copies, since the missing session spent them, not this one: no '
              'row for the copied agent, totals of zero, and a line saying the missing '
              'session\'s transcripts hold none of the copied ids',
              o.returncode == 0 and 'eee' not in orow and 'copy:' not in o.stdout
              and not re.search(r'^copied\s+\d', o.stdout, re.M)
              and orow.get('session', [])[1:7] == ['0', '0', '0', '0', '0', '0']
              and 'notice equals the last request in 0 of the 0 with a notice' in o.stdout
              and f'{LOST}: 1 root request and 1 agent request in 1 agent transcript, 161 tokens; '
                  'its own transcripts hold 0 of these 2 ids' in o.stdout, o.stdout + o.stderr)

        e = os.path.join(project, LOST + '.jsonl')
        write(e, [])
        o = ledger(os.path.join(project, COPY + '.jsonl'))
        os.remove(e)
        check('L16 an earlier session whose transcript is there but empty holds none of the '
              'copied ids, and the line says so rather than taking the file for the work',
              o.returncode == 0 and f'{LOST}: 1 root request and 1 agent request in 1 agent '
              'transcript, 161 tokens; its own transcripts hold 0 of these 2 ids' in o.stdout
              and parse(o.stdout).get('session', [])[1:7] == ['0', '0', '0', '0', '0', '0'],
              o.stdout + o.stderr)

        u    = os.path.join(project, GROW + '.jsonl')
        grow = reply('g1', usage(2, 0, 0, 3), '2026-01-01T12:00:00Z',
                     [{'type': 'thinking', 'thinking': ''}])
        grow += reply('g1', usage(2, 0, 0, 8), '2026-01-01T12:00:00Z',
                      [{'type': 'text', 'text': ''}])
        grow += reply('g2', usage(1, 0, 0, 1), '2026-01-01T12:01:00Z',
                      [{'type': 'text', 'text': ''}])
        grow += reply('g1', usage(0, 0, 0, 0), '2026-01-01T12:00:00Z',
                      [{'type': 'text', 'text': ''}])
        write(u, grow, sid=GROW)
        g = ledger(u)
        check('L19 a request whose records differ counts each count\'s largest value: the output '
              'that grew while the reply streamed (8, not 3 or 11), and not a later rewrite of the '
              'request with zeros', g.returncode == 0
              and parse(g.stdout).get('root', [])[1:7] == ['2', '3', '0', '0', '9', '12'],
              g.stdout + g.stderr)

        q1 = reply('q1', usage(10, 0, 0, 1), '2026-01-01T12:00:00Z',
                   [{'type': 'tool_use', 'id': 'qt'}], isSidechain=True)
        q2 = reply('q2', usage(20, 0, 0, 2), '2026-01-01T12:01:00Z',
                   [{'type': 'text', 'text': ''}], isSidechain=True)
        write(os.path.join(project, GROW, 'subagents', 'agent-par.jsonl'), q1, sid=GROW)
        write(os.path.join(project, GROW, 'subagents', 'agent-frk.jsonl'), q1 + q2, sid=GROW)
        g    = ledger(u)
        grow = parse(g.stdout)
        check('L21 a request an agent\'s fork carries as a copy of the agent\'s records counts '
              'once in the totals, while each agent row counts it, and a line says how many more '
              'the rows hold',
              grow.get('par', [])[3:9] == ['1', '10', '0', '0', '1', '11']
              and grow.get('frk', [])[3:9] == ['2', '30', '0', '0', '3', '33']
              and grow.get('subagents', [])[1:8] == ['2', '30', '0', '0', '3', '33', '1']
              and grow.get('session', [])[1:7] == ['4', '33', '0', '0', '12', '45']
              and 'the agent rows hold 1 more request than the subagents total' in g.stdout,
              g.stdout + g.stderr)
        os.remove(u)

        k1   = reply('k1', usage(1, 0, 0, 2), '2026-01-01T12:00:00Z', [{'type': 'text', 'text': ''}])
        cut  = os.path.join(project, CUT + '.jsonl')
        write(cut, k1, tail='null\n[1]\n"text"\n', sid=CUT)
        k = ledger(cut)
        check('L12 a line that is JSON but not an object (null, a list, a string) is skipped, not '
              'a crash', k.returncode == 0
              and parse(k.stdout).get('root', [])[1:7] == ['1', '1', '0', '0', '2', '3'],
              k.stdout + k.stderr)

        write(cut, k1, tail='{"type": "user", "x": "\u00e9'.encode()[:-1], sid=CUT)
        k = ledger(cut)
        check('L13 a last line cut inside a multibyte character, as a live transcript can end, is '
              'skipped, not a crash', k.returncode == 0
              and parse(k.stdout).get('root', [])[1:7] == ['1', '1', '0', '0', '2', '3'],
              k.stdout + k.stderr)

        top = os.path.join(tmp, 'machine', 'projects')
        machine(top)
        m   = ledger('--all', '--projects', top)
        mg  = ledger('--all', '--projects', top, '--group', 'kit')
        rows, grows = parse(m.stdout), parse(mg.stdout)
        b   = parse(ledger(os.path.join(top, 'p1', 'B.jsonl')).stdout)
        c   = ledger(os.path.join(top, 'p1', 'C.jsonl'))
        check('L17 a fork of a fork (A gone, B forked from A, C from B): B and C each count only '
              'their own request, C lists A\'s copies as held nowhere and B\'s as held by B, and '
              '--all counts A\'s work once',
              m.returncode == 0 and b.get('session', [])[1:7] == ['1', '10', '0', '0', '0', '10']
              and parse(c.stdout).get('session', [])[1:7] == ['1', '1', '0', '0', '0', '1']
              and 'A: 1 root request and 1 agent request in 1 agent transcript, 1100 tokens; its '
                  'own transcripts hold 0 of these 2 ids' in c.stdout
              and 'B: 1 root request and 0 agent requests in 0 agent transcripts, 10 tokens; its '
                  'own transcripts hold 1 of these 1 ids' in c.stdout
              and rows.get('all', [])[1:9] == ['6', '8', '1620', '0', '0', '8', '1628', '3'],
              m.stdout + m.stderr + c.stdout)

        check('L18 two siblings of a missing session in different folders (B and D, both forked '
              'from A) leave A\'s work counted once machine-wide, in the first folder that carries '
              'it, and --group splits the rest by folder name',
              grows.get('kit', [])[1:9] == ['1', '2', '4', '0', '0', '8', '12', '0']
              and grows.get('other', [])[1:9] == ['5', '6', '1616', '0', '0', '0', '1616', '3']
              and grows.get('all', []) == rows.get('all', ['?']), mg.stdout + mg.stderr)

        want = dedupe(top)
        check('L20 --all equals an independent per-id count over every .jsonl under the folder: '
              'requests, each column and the total, and its differ column counts d2, the one '
              'request whose records differ, and no request names two sessions',
              rows.get('all', [])[9:10] == ['1']
              and '0 of the 8 requests name more than one session' in m.stdout
              and rows.get('all', [])[2:8] == [
                  str(len(want)), *(str(sum(u[i] for u in want.values())) for i in range(4)),
                  str(sum(map(sum, want.values())))],
              f'{m.stdout}\n{want}')

        top = os.path.join(tmp, 'part', 'projects')
        partition(top)
        al  = parse(ledger('--all', '--projects', top).stdout).get('all', [])
        own = {}
        for sid, folder in (('B', 'p1'), ('C', 'p1'), ('D', 'p2'), ('D', 'p3')):
            s = ledger(os.path.join(top, folder, sid + '.jsonl'))
            own.setdefault(sid, set()).add(parse(s.stdout).get('session', ['?'] * 7)[6])
        named = {}
        for d, _, names in os.walk(top):
            for n in names:
                for line in open(os.path.join(d, n), encoding='utf-8'):
                    o = json.loads(line)
                    named[o['message']['id']] = (o['sessionId'], sum(o['message']['usage'][k]
                        for k in ('input_tokens', 'cache_creation_input_tokens',
                                  'cache_read_input_tokens', 'output_tokens')))
        gone = sum(t for s, t in named.values() if s == 'A')
        per  = {s: int(next(iter(t))) if len(t) == 1 and next(iter(t)).isdigit() else None
                for s, t in own.items()}
        check('L22 partition: on a machine with forks, a fork of a fork, an agent\'s fork '
              'copies, a missing origin, a session\'s own isSidechain records and one session id '
              'in two folders, every session\'s own total (28, 96, 896) plus the missing '
              'session\'s work (3) equals --all (1023), and both transcripts of one session print '
              'the same total',
              per == {'B': 28, 'C': 96, 'D': 896} and gone == 3 and al[7:8] == ['1023'],
              f'{own} gone {gone} all {al}')

        c = parse(ledger(os.path.join(top, 'p1', 'C.jsonl')).stdout).get('root', [])
        check('L23 a session\'s own isSidechain record in its session transcript is in its root '
              'row, as --all counts it, and root secs spans it (c1 and c2, 96 tokens, 60 s)',
              c[1:2] == ['2'] and c[6:7] == ['96'] and c[8:9] == ['60'], str(c))

        d = ledger(os.path.join(top, 'p2', 'D.jsonl'))
        check('L24 a session with transcripts in two folders is one session: its ledger reads '
              'both, counts d1 once, and names the folders',
              parse(d.stdout).get('session', [])[1:2] == ['3']
              and 'transcripts in 2 project folders' in d.stdout and 'p2, p3' in d.stdout,
              d.stdout + d.stderr)

        top = os.path.join(tmp, 'forks', 'projects')
        b   = ledger(forks(top))
        fa  = parse(ledger('--all', '--projects', top).stdout).get('all', [])
        check('L25 processed counts a request an agent\'s fork carries once: --all\'s processed '
              'and the line under one session\'s table say 1100, not 1200',
              fa[11:15] == ['2', '2', '1100', '1100']
              and 'those 2 processed 1100 tokens' in b.stdout, f'{fa}\n{b.stdout}')

        bad = [ledger('--all', '--projects', top, '--group', g) for g in ('all', 'other', '')]
        check('L26 --group refuses all, other and an empty text, which would collide with a fixed '
              'row name or match every folder',
              all(x.returncode == 2 and 'ledger:' in x.stderr and x.stdout == '' for x in bad),
              '\n'.join(x.stdout + x.stderr for x in bad))

        top = os.path.join(tmp, 'g[1]*?', 'projects')
        machine(top)
        gm = parse(ledger('--all', '--projects', top).stdout).get('all', [])
        gc = ledger(os.path.join(top, 'p1', 'C.jsonl'))
        check('L27 a projects path with glob metacharacters reads every transcript: --all counts '
              'the same 8 requests, and one session finds its agents and the copies\' origin',
              gm[1:9] == ['6', '8', '1620', '0', '0', '8', '1628', '3']
              and 'B: 1 root request and 0 agent requests in 0 agent transcripts, 10 tokens; its '
                  'own transcripts hold 1 of these 1 ids' in gc.stdout
              and 'in 1 agent transcript' in gc.stdout, f'{gm}\n{gc.stdout}{gc.stderr}')

        weird = os.path.join(project, CUT + '.jsonl')
        write(weird, [
            {'type': 'assistant', 'message': {'id': 'w1', 'model': 'm', 'usage': [1, 2]}},
            {'type': 'assistant', 'message': {'id': 'w2', 'model': 'm', 'usage': 'x'}},
            {'type': 'assistant', 'message': {'id': 'w3', 'model': 'm', 'usage': 7}},
            {'type': 'assistant', 'message': {'id': 'w4', 'model': 'm',
                                              'usage': {'input_tokens': 'x', 'output_tokens': 2}}},
            *reply('w5', usage(3, 0, 0, 0), '2026-01-01T12:00:00Z',
                   [{'type': 'text', 'text': ''}])], sid=CUT)
        w = ledger(weird)
        check('L28 a usage that is not an object is skipped and a count that is not a number '
              'reads 0, not a crash', w.returncode == 0
              and parse(w.stdout).get('root', [])[1:7] == ['2', '3', '0', '0', '2', '5'],
              w.stdout + w.stderr)

        loose = os.path.join(tmp, 'loose', 'here', COPY + '.jsonl')
        os.makedirs(os.path.dirname(loose))
        with open(os.path.join(project, COPY + '.jsonl'), 'rb') as src, open(loose, 'wb') as dst:
            dst.write(src.read())
        lo = ledger(loose)
        check('L29 a transcript outside a projects folder says it can\'t look for the origin\'s '
              'transcripts, rather than that they hold none of the ids, until --projects names '
              'the folder',
              lo.returncode == 0 and 'hold 0 of' not in lo.stdout
              and "can't look for its own transcripts" in lo.stdout
              and 'hold 0 of these 2 ids' in ledger(loose, '--projects',
                                                    os.path.join(home, 'projects')).stdout,
              lo.stdout + lo.stderr)

    doc = open(MEASURE, encoding='utf-8').read()
    check('L10 measure.md states the notice comparison as measured over every session, with the '
          'shipped command that regenerates it, never as the last request in general or from one '
          'picked session, and bills no copies to the session that carries them',
          'last request alone' not in doc and 'most of the time, not always' in doc
          and 'Across every session on one machine' in doc
          and 'ledger.py" --all --group kstack' in doc and 'is not spend' in doc
          and 'ledger.py" "$t" | sed -n' not in doc and 'copy:<id>' not in doc
          and 'a large session in another project' not in doc and '3 of the 21' not in doc
          and 'nor a floor' not in doc, MEASURE)

    check('L30 measure.md says file-history deltas carry a timestamp and snapshots do not, gives '
          'the command that counts them, and says the request total grows with live sessions',
          'with no timestamp, and none' not in doc and 'file-history-delta' in doc
          and 'select(.sessionId == null)' in doc and 'every request total grows' in doc,
          MEASURE)

if __name__ == '__main__':
    main()
    sys.exit(failures)
