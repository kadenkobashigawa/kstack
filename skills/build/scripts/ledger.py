#!/usr/bin/env python3
"""
ledger.py prints what Claude Code sessions spent, read from the per-request usage records in
their transcripts. references/measure.md ("A process number") says why these records are the
source of spend and the completion notice's `subagent_tokens` is not.

  ledger.py SESSION.jsonl [--projects DIR]
  ledger.py --session ID --project DIR
                what one session spent; DIR is a folder under ~/.claude/projects, given by its
                path or its name, or the working directory the session ran in; --projects names
                the projects folder of a transcript that sits outside one
  ledger.py --all [--projects DIR] [--group TEXT]
                what every session under the projects folder spent, each request counted once;
                --group splits the figures into the project folders whose name contains TEXT and
                the rest, and refuses `all`, `other` and an empty TEXT, the fixed row names and
                a text every folder contains

A session's transcript is `<project>/<session>.jsonl`, and each subagent's is
`<project>/<session>/subagents/agent-<id>.jsonl` (workflow agents sit one or two folders lower),
with `agent-<id>.meta.json` beside it naming its type and description. Each assistant record
carries `message.usage` for the request that produced it. A request that returned several content
blocks is written once per block with the same `message.id`, so the script counts each id once.
The records of one request can differ: the counts grow while the reply streams, and a request
rewritten later in a transcript can carry zeros, so the script takes each count's largest value
among the request's records, which is the final count.

Every record names the session that made the request in `sessionId`, and copies keep it: a
session forked or resumed from an earlier one starts with copies of the earlier session's records,
in its own transcript and as copied `agent-<id>.jsonl` files, under the earlier `sessionId` and
the same `message.id`. A copied request was spent by the session it names, never by the one that
carries it. So one session's ledger counts only the records whose `sessionId` is its own (the
transcript's file name), `isSidechain` records in its session transcript included, gives no row to
an agent transcript with no request of its own, and lists the copies under the table by the
session they came from, outside every total, saying how many of their ids that session's own
transcripts hold, or that it can't look when the transcript is not in a projects folder (one named
`projects`, or the one --projects names). A record with no `sessionId` counts for no session:
copied file-history records carry none, and the deltas among them carry the earlier session's
times.

A session id can have a transcript in more than one project folder. It is one session, so its
ledger reads the session transcript and agent transcripts in every folder as one, counts each
request once, and prints the same table whichever transcript is named. So one table per session
id, plus the work of sessions whose transcripts are gone, adds up to what --all counts.

One session's table has one row per subagent of this session, in start order, then the total rows
`subagents` (this session's agents), `root` (the requests its transcripts record for it) and
`session` (both). Columns:

  agent    the agent id, or the total's name
  type     the agent type from meta.json
  model    the model id the records name
  req      requests, one per distinct message id
  input    input_tokens, the uncached input
  c_write  cache_creation_input_tokens, input written to the cache
  c_read   cache_read_input_tokens, input read from the cache
  output   output_tokens
  total    input + c_write + c_read + output, summed over every request: the tokens processed
  tools    tool_use blocks
  secs     seconds from the agent's first record to its last, idle time between resumes included
  last     input + c_write + c_read + output of the agent's last request alone
  notice   the completion notice's subagent_tokens, for comparison only; '-' when none arrived
  desc     the description from meta.json, cut to 40 characters

The total rows count each request and tool call once, however many rows hold it: an agent that
forks hands each fork copies of its records under this session's `sessionId`, so a request can sit
in several agent rows. They sum `secs` as agent-seconds, and leave `last` and `notice` blank, since
neither is spend and a sum of either means nothing. The line under the table counts the agents
whose notice equals their last request, and sets the tokens those agents processed, each request
once, beside their notices' sum.

--all reads every session and agent transcript under the projects folder and counts each
`message.id` once, whichever transcripts carry it, so a request copied into forks is counted once
and the work of a session whose own transcript is gone is counted from its copies. A request
belongs to the project folder that holds the transcript of the session it names, or, when that
session has no transcript left, to the first folder in name order that carries it. Its table has
one row per group and an `all` row, and the line under it says how many requests name more than
one session in `sessionId`. Columns:

  group     the project folders whose name contains --group, `other`, or `all`
  sessions  sessions named by the group's requests
  req, input, c_write, c_read, output, total   as above, each request once
  copies    requests carried by more than one transcript, counted once in the columns before
  differ    requests whose records do not all carry the same counts
  agents    agents whose requests are in the group, each agent id once
  noticed   those with a completion notice; the notice read is the latest one carried
  equal     those whose notice equals their last request
  processed the tokens the noticed agents processed, each request once
  notices   the sum of their notices

Cost is the four token columns weighted by the pricing page for the row's model; a cache read
costs a small fraction of uncached input, so `total` alone overstates cost.

The script only reads. Exit codes: 0 on success, 2 when the transcript or projects folder can't be
found or read.
"""

from __future__ import annotations

import argparse
import collections
import datetime
import glob
import json
import os
import re
import sys


FIELDS   = ('input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens',
            'output_tokens')
NOTICE   = re.compile(r'<task-notification>(.*?)</task-notification>', re.S)
TASK_ID  = re.compile(r'<task-id>([^<]+)</task-id>')
TOKENS   = re.compile(r'<subagent_tokens>(\d+)</subagent_tokens>')
HEADER   = ('agent', 'type', 'model', 'req', 'input', 'c_write', 'c_read', 'output', 'total',
            'tools', 'secs', 'last', 'notice', 'desc')
ALL      = ('group', 'sessions', 'req', 'input', 'c_write', 'c_read', 'output', 'total', 'copies',
            'differ', 'agents', 'noticed', 'equal', 'processed', 'notices')


def refuse(message: str) -> int:
    sys.stderr.write(f'ledger: {message}\n')
    return 2


def records(path: str):
    """
    Each JSON object in a transcript. A live transcript can end in a write cut short, even inside
    a multibyte character, so a line that isn't valid UTF-8 JSON, or is JSON but not an object, is
    skipped.
    """
    with open(path, 'rb') as f:
        for line in f:
            try:
                o = json.loads(line)  #bytes: a cut character raises UnicodeDecodeError, a ValueError
            except ValueError:
                continue
            if isinstance(o, dict):
                yield o


def request(o: dict):
    """
    A record's (key, usage counts, message) when it records a real request, else None. A usage
    that is not an object records no request, and a count that is not a number reads 0.
    """
    m = o.get('message')
    if o.get('type') != 'assistant' or not isinstance(m, dict):
        return None
    u = m.get('usage')
    if m.get('model') == '<synthetic>' or not isinstance(u, dict) or not u:
        return None
    key = m.get('id') or o.get('requestId') or o.get('uuid')
    return key, tuple(count(u.get(k)) for k in FIELDS), m


def count(v) -> int:
    return v if isinstance(v, int) and not isinstance(v, bool) else 0


def merge(seen: dict, key: str, counts: tuple) -> None:
    """
    Records one request's counts, keeping each count's largest value: the counts grow while the
    reply streams, and a request rewritten later in a transcript can carry zeros, so the largest
    is the final count. In the transcripts read at 12:42 MST on 2026-11-02 the last record held
    it for 362 of the 364 requests whose records differ, and a later rewrite with zeros followed
    it in the other 2.
    """
    old = seen.get(key)
    seen[key] = counts if old is None else tuple(max(a, b) for a, b in zip(old, counts))


def usage_of(paths: list[str], me: str) -> dict:
    """
    The requests in these transcripts that session `me` made, counted once per message id, with
    tools, span and models, and the copied requests they carry, by the session that made them.
    """
    seen, tools, models, stamps = {}, set(), collections.Counter(), []
    copied = collections.defaultdict(dict)
    for o in (o for path in paths for o in records(path)):
        r = request(o)
        if o.get('sessionId') != me:
            if r and o.get('sessionId'):
                merge(copied[o['sessionId']], r[0], r[1])
            continue
        if o.get('timestamp'):
            stamps.append(o['timestamp'])
        if not r:
            continue
        merge(seen, r[0], r[1])
        models[r[2].get('model')] += 1
        for block in r[2].get('content') or []:
            if isinstance(block, dict) and block.get('type') == 'tool_use':
                tools.add(block.get('id'))
    sums = {k: sum(u[i] for u in seen.values()) for i, k in enumerate(FIELDS)}
    last = sum(list(seen.values())[-1]) if seen else 0
    return {'req': len(seen), **sums, 'tools': len(tools), 'last': last,
            'model': ','.join(m for m, _ in models.most_common()) or '-',
            'secs': span(stamps), 'start': min(stamps) if stamps else '', 'from': dict(copied),
            'ids': seen, 'tool_ids': tools}


def span(stamps: list[str]) -> int:
    if not stamps:
        return 0
    t = sorted(datetime.datetime.fromisoformat(s.replace('Z', '+00:00')) for s in stamps)
    return round((t[-1] - t[0]).total_seconds())


def notices_in(main: str):
    """(agent id, subagent_tokens, timestamp, sessionId) of each completion notice in `main`."""
    for o in records(main):
        if o.get('type') == 'queue-operation':
            texts = [o.get('content')]
        elif o.get('type') == 'user' and isinstance(o.get('message'), dict):
            c = o['message'].get('content')

            #a tool result that quotes a notice is not one, so read only text the harness sent...
            texts = [c] if isinstance(c, str) else [
                b.get('text') for b in c or [] if isinstance(b, dict) and b.get('type') == 'text']
        else:
            continue
        for t in texts:
            if not isinstance(t, str):
                continue
            for block in NOTICE.findall(t):
                aid, tok = TASK_ID.search(block), TOKENS.search(block)
                if aid and tok:
                    yield aid.group(1).strip(), int(tok.group(1)), o.get('timestamp') or '', \
                        o.get('sessionId')


def agent_files(main: str) -> list[str]:
    return glob.glob(os.path.join(glob.escape(main[:-len('.jsonl')]), 'subagents', '**',
                                  'agent-*.jsonl'), recursive=True)


def agent_id(path: str) -> str:
    return os.path.basename(path)[len('agent-'):-len('.jsonl')]


def agents(mains: list[str], me: str) -> list[dict]:
    """One row per agent id under these session transcripts, its transcripts read as one."""
    by_id = collections.defaultdict(list)
    for main in mains:
        for path in sorted(agent_files(main)):
            by_id[agent_id(path)].append(path)
    rows = []
    for aid, paths in by_id.items():
        meta = {}
        for path in paths:
            try:
                with open(path[:-len('.jsonl')] + '.meta.json', encoding='utf-8') as f:
                    meta = json.load(f)
                break
            except (OSError, ValueError):
                pass
        rows.append({'agent': aid, 'type': meta.get('agentType') or '-',
                     'desc': (meta.get('description') or '')[:40], **usage_of(paths, me)})
    rows.sort(key=lambda r: (r['start'], r['agent']))
    return rows


def projects_of(main: str, given: str | None) -> str | None:
    """
    The projects folder that holds `main`: `given`, else the folder two levels up when it is a
    projects folder, which Claude Code names `projects`, else None. The path is made absolute
    first, so a transcript named relative to its own folder still finds the projects folder.
    """
    if given:
        return given
    top = os.path.dirname(os.path.dirname(os.path.abspath(main)))
    if os.path.basename(top) == 'projects' or os.path.realpath(top) == os.path.realpath(
            projects()):
        return top
    return None


def transcripts(top: str | None, sid: str) -> list[str]:
    """Session `sid`'s session transcripts in every folder of the projects folder, by folder."""
    if top is None:
        return []
    return sorted(glob.glob(os.path.join(glob.escape(top), '*', glob.escape(sid) + '.jsonl')))


def held(top: str | None, origin: str) -> set[str] | None:
    """
    The request ids that session `origin`'s own transcripts hold, its session transcripts and its
    agents', in any folder of the projects folder `top`; None when there is no folder to look in.
    """
    if top is None:
        return None
    ids = set()
    for path in transcripts(top, origin):
        for p in [path, *agent_files(path)]:
            ids.update(r[0] for r in map(request, records(p)) if r)
    return ids


def total(name: str, rows: list[dict]) -> dict:
    """
    A total row, each request and tool call once however many of the rows hold it: an agent that
    forks hands each fork copies of its records under the session's sessionId, so two agent rows
    of one session can hold the same request.
    """
    ids, tools = {}, set()
    for r in rows:
        for k, u in r['ids'].items():
            merge(ids, k, u)
        tools |= r['tool_ids']
    return {'agent': name, 'type': '', 'model': '', 'desc': '', 'last': '', 'notice': '',
            'req': len(ids), **{k: sum(u[i] for u in ids.values()) for i, k in enumerate(FIELDS)},
            'tools': len(tools), 'secs': sum(r['secs'] for r in rows), 'ids': ids,
            'tool_ids': tools}


def cells(r: dict) -> list[str]:
    tot = sum(r[k] for k in FIELDS)
    return [r['agent'], r['type'], r['model'], str(r['req']), *(str(r[k]) for k in FIELDS),
            str(tot), str(r['tools']), str(r['secs']), str(r['last']), str(r['notice']), r['desc']]


def table(rows: list[list[str]], left: tuple[int, ...]) -> str:
    width = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    out   = []
    for r in rows:
        line = [c.ljust(w) if i in left else c.rjust(w) for i, (c, w) in enumerate(zip(r, width))]
        out.append('  '.join(line).rstrip())
    return '\n'.join(out)


def plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def one(main: str, given: str | None) -> int:
    me  = os.path.basename(main)[:-len('.jsonl')]
    top = projects_of(main, given)

    #one session id can have a transcript in more than one project folder; it is one session, so
    #every transcript of it is read and each request counted once, whichever one is named...
    here  = os.path.realpath(main)
    mains = transcripts(top, me)
    if here not in map(os.path.realpath, mains):
        mains = [main, *mains]
    try:
        every  = agents(mains, me)
        notice = {aid: tok for m in mains for aid, tok, _, sid in notices_in(m) if sid == me}
        mine   = usage_of(mains, me)

        #copies, by the session that made them; they are listed, never added to a total...
        copies = collections.defaultdict(lambda: {'root': {}, 'agents': 0, 'agent': {}})
        for s, ids in mine['from'].items():
            copies[s]['root'].update(ids)
        for r in every:
            for s, ids in r['from'].items():
                copies[s]['agents'] += 1
                copies[s]['agent'].update(ids)
        holds  = {s: held(top, s) for s in copies}
    except OSError as e:
        return refuse(str(e))
    rows = [r for r in every if r['req']]
    for r in rows:
        r['notice'] = notice.get(r['agent'], '-')
    subs  = total('subagents', rows)
    root  = total('root', [mine])
    whole = total('session', [subs, root])
    print(table([list(HEADER), *(cells(r) for r in rows), cells(subs), cells(root), cells(whole)],
                (0, 1, 2, 13)))
    told = [r for r in rows if r['notice'] != '-']
    same = sum(1 for r in told if r['notice'] == r['last'])
    used = total('', told)
    print(f'\n{len(rows)} subagents. notice equals the last request in {same} of the '
          f'{len(told)} with a notice; those {len(told)} processed '
          f'{sum(used[k] for k in FIELDS)} '
          f"tokens and their notices sum to {sum(r['notice'] for r in told)}; spend is the total "
          f'column, never the notice.')
    if sum(r['req'] for r in rows) > subs['req']:
        more = sum(r['req'] for r in rows) - subs['req']
        print(f"the agent rows hold {plural(more, 'more request')} than "
              f'the subagents total: an agent that forks hands each fork copies of its records, so '
              f'a request can sit in several agent transcripts of this session; each row counts '
              f'it, the totals once.')
    if len(mains) > 1:
        print(f'\nthis session has transcripts in {len(mains)} project folders, read as one '
              f'session, each request once: '
              f"{', '.join(os.path.basename(os.path.dirname(m)) for m in mains)}.")
    if copies:
        print(f'\ncopied from {plural(len(copies), "earlier session")}, outside every total above: '
              f'those sessions spent them, and `ledger.py --all` counts each request once.')
    for s in sorted(copies):
        c   = copies[s]
        ids = {**c['root'], **c['agent']}
        tok = sum(sum(u) for u in ids.values())
        has = (f"can't look for its own transcripts: {main} is not in a projects folder, so give "
               f'--projects' if holds[s] is None else
               f'its own transcripts hold {len(set(ids) & holds[s])} of these {len(ids)} ids')
        print(f"  {s}: {plural(len(c['root']), 'root request')} and "
              f"{plural(len(c['agent']), 'agent request')} in "
              f"{plural(c['agents'], 'agent transcript')}, {tok} tokens; {has}")
    return 0


def everything(top: str, group: str | None) -> int:
    """Every request under the projects folder `top`, each message id once, by group."""
    if not os.path.isdir(top):
        return refuse(f'{top} is not a folder')
    if group is not None and group in ('', 'all', 'other'):
        return refuse(f"--group {group!r} would collide with a row name or match every folder; "
                      f'give text a project folder name contains')
    folders = sorted(d for d in os.listdir(top) if os.path.isdir(os.path.join(top, d)))
    root    = glob.escape(top)
    seen, stamp, owner, carriers, differ = {}, {}, {}, collections.Counter(), set()
    mixed = set()
    home, by_agent, notice = {}, collections.defaultdict(set), {}
    try:
        for d in folders:
            for main in sorted(glob.glob(os.path.join(root, glob.escape(d), '*.jsonl'))):
                sid = os.path.basename(main)[:-len('.jsonl')]
                home.setdefault(sid, d)
                for aid, tok, at, _ in notices_in(main):
                    if aid not in notice or at >= notice[aid][1]:
                        notice[aid] = (tok, at)
                for path in [main, *sorted(agent_files(main))]:
                    aid, here = agent_id(path) if path != main else None, set()
                    for o in records(path):
                        r = request(o)
                        if not r:
                            continue
                        if r[0] in seen and seen[r[0]] != r[1]:
                            differ.add(r[0])
                        merge(seen, r[0], r[1])
                        here.add(r[0])
                        if r[0] not in owner:
                            owner[r[0]] = (o.get('sessionId'), d)
                        elif o.get('sessionId') != owner[r[0]][0]:
                            mixed.add(r[0])
                        at = o.get('timestamp')
                        if at and (r[0] not in stamp or at < stamp[r[0]]):
                            stamp[r[0]] = at
                        if aid:
                            by_agent[aid].add(r[0])
                    carriers.update(here)
    except OSError as e:
        return refuse(str(e))

    #a request belongs to the folder of the session that made it, else the first that carries it...
    def where(key: str) -> str:
        sid, first = owner[key]
        d = home.get(sid, first)
        return 'all' if group is None else group if group in d else 'other'

    names = ['all'] if group is None else [group, 'other', 'all']
    rows  = []
    for g in names:
        keys = [k for k in seen if g == 'all' or where(k) == g]
        mine = [a for a, ks in by_agent.items()
                if g == 'all' or where(min(ks, key=lambda k: (stamp.get(k, ''), k))) == g]
        told = [a for a in mine if a in notice]
        last = {a: sum(seen[max(by_agent[a], key=lambda k: (stamp.get(k, ''), k))]) for a in told}
        rows.append([g, str(len({owner[k][0] for k in keys})), str(len(keys)),
                     *(str(sum(seen[k][i] for k in keys)) for i in range(len(FIELDS))),
                     str(sum(sum(seen[k]) for k in keys)),
                     str(sum(1 for k in keys if carriers[k] > 1)),
                     str(sum(1 for k in keys if k in differ)), str(len(mine)), str(len(told)),
                     str(sum(1 for a in told if notice[a][0] == last[a])),
                     str(sum(sum(seen[k]) for k in set().union(*(by_agent[a] for a in told)))),
                     str(sum(notice[a][0] for a in told))])
    print(table([list(ALL), *rows], (0,)))
    print(f'\neach request counted once, whichever transcripts carry it; spend is the total '
          f'column, never the notices. {len(mixed)} of the {len(seen)} requests name more than '
          f'one session.')
    return 0


def resolve(project: str, session: str) -> str:
    for folder in (project, os.path.join(projects(), project),
                   os.path.join(projects(), re.sub(r'[^A-Za-z0-9]', '-',
                                                   os.path.abspath(project)))):
        path = os.path.join(folder, session + '.jsonl')
        if os.path.isfile(path):
            return path
    return ''


def projects() -> str:
    home = os.environ.get('CLAUDE_CONFIG_DIR') or os.path.expanduser('~/.claude')
    return os.path.join(home, 'projects')


def plain(argv: list[str]) -> list[str]:
    """argv with no path or folder name mistaken for an option."""

    #a project folder's name starts with '-', which argparse reads as an option, so a value is
    #joined to its option and a bare path gets a leading './'...
    out, i = [], 0
    while i < len(argv):
        x = argv[i]
        if x in ('--project', '--session', '--projects', '--group') and i + 1 < len(argv):
            out.append(f'{x}={argv[i + 1]}')
            i += 2
            continue
        out.append(os.path.join('.', x) if x.startswith('-') and not x.startswith('--')
                   and x != '-h' else x)
        i += 1
    return out


def run(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog='ledger.py', description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('transcript', nargs='?', help='the session transcript, <session>.jsonl')
    p.add_argument('--session', help='the session id, with --project')
    p.add_argument('--project', help='the project folder, its name or its working directory')
    p.add_argument('--all', action='store_true', help='every session, each request counted once')
    p.add_argument('--projects', help='the projects folder, by default ~/.claude/projects with '
                   '--all, and the folder two levels above a transcript named `projects`')
    p.add_argument('--group', help='with --all, split by project folders whose name contains this')

    a = p.parse_args(plain(argv))
    if a.all:
        return everything(a.projects or projects(), a.group)
    if a.group is not None:
        return refuse('--group goes with --all')
    if a.transcript:
        main = a.transcript
    elif a.session and a.project:
        main = resolve(a.project, a.session)
        if not main:
            return refuse(f'no transcript {a.session}.jsonl for project {a.project}')
    else:
        return refuse('give a transcript path, --session with --project, or --all')
    if not main.endswith('.jsonl') or not os.path.isfile(main):
        return refuse(f'{main} is not a session transcript (<session>.jsonl)')
    return one(main, a.projects)


if __name__ == '__main__':
    sys.exit(run(sys.argv[1:]))
