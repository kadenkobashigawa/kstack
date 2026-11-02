'''
brief — the briefs a scan writes for the judging agents, a projection of the ledger: each kstack
file with a citation left to judge, whole, with the pin and head copies of each file it cites,
packed in path order up to `CAP` bytes a brief.

Methods
-------
    section_for :
        one kstack file's part of a brief.
    brief_text :
        one brief.
    pack :
        the kstack files packed into briefs.
'''

from __future__ import annotations

from pathlib import Path

import home
from cite import flatten, fmt_lines, parse_with_starts
from home import clone_dir
from model import DECIDED, PASS, Ledger


CAP = 100_000   # bytes of text a brief holds before the next kstack file starts another

JUDGE = ('Judge each citation below against the upstream text at the head, never against a '
         'commit message. Sort it as no effect, pointer drift, changed on purpose or no stated '
         'reason, and give it one outcome: in sync, updated, diverged, updated and diverged, or '
         'blocked. Each upstream file below names its pin copy under the repository\'s upstream/, '
         'its head copy in the run\'s clone, and the head tree it sits in: read and search them '
         'as you need, such as to tell a passage the head moved or reworded from one it removed. '
         'Return one JSON line per citation with the keys id, sort, outcome, commit, old, new, '
         'citation, edit and kept. Kept is true when a `*(kstack: …)*` tag marks the citation\'s '
         'rule as kstack\'s own; the kept hint is only the nearest such tag after the citation, '
         'which may mark another sentence, so read the rule and decide. A citation you mark kept '
         'gets no rule edit. Edit nothing.')


def _rule(flat: str, i: int) -> str:
    '''
    the paragraph, or table cell, of a flattened kstack text that holds offset `i`, where a
    citation's parenthesis opens.
    '''
    start, end = flat.rfind('\n', 0, i) + 1, flat.find('\n', i)
    para = flat[start:end if end >= 0 else len(flat)]
    if para.startswith('|'):
        at, cells = i - start, para.split('|')
        for cell in cells:
            if at <= len(cell):
                return cell.strip()
            at -= len(cell) + 1
    return para


def section_for(kfile: str, ledger: Ledger, run: Path) -> str | None:
    '''
    one kstack file's part of a brief: each upstream file it cites, with the paths of its pin
    copy, its head copy and the head tree in `run`'s clone, and each citation left to judge with
    its rule, its old and new upstream text, and every commit message whole. None when the script
    decided every citation.
    '''
    ids = [i for i in ledger.by_kfile().get(kfile, []) if ledger.remaps[i].state not in DECIDED]
    if not ids:
        return None
    text = (home.REPO / kfile).read_text(encoding='utf-8')
    flat, _ = flatten(text)
    found, _, starts = parse_with_starts(kfile, text, {r.label() for r in ledger.sources.imports})
    opened = {c.id: s for c, s in zip(found, starts)}
    out = [f'## `{kfile}`', '']
    by_file: dict[str, list[str]] = {}
    for i in ids:
        c = ledger.citations[i]
        by_file.setdefault(f'{c.label}:{c.path}', []).append(i)
    for key, cids in by_file.items():
        f = ledger.files[key]
        row = next((r for r in ledger.sources.imports if r.folder == f.folder), None)
        head = ledger.heads.get(row.url, '')[:7] if row else ''
        label, path = key.split(':', 1)
        moved = f', now `{f.head_path}`' if f.head_path and f.head_path != path else ''
        clone = clone_dir(run, row.url) if row else None
        out += [f'### `{key}`: {f.state}{moved}', '',
                f'- Pin copy: `{home.UPSTREAM / label / path}`',
                f'- Head copy: `{clone / row.repo_path(f.head_path)}`' if clone and f.head_path
                else '- Head copy: none, the head removes it',
                f'- Head tree: `{clone / row.path}`' if clone else '- Head tree: none', '',
                f'Commits from {row.commit[:7] if row else "?"} to {head} that touched it, oldest '
                f'first: {len(f.commits)}.', '']
        for commit in f.commits:
            out += [f'#### {commit.sha[:12]} {commit.date}', '', '~~~~text', commit.message,
                    '~~~~', '']
        for i in cids:
            c, r, b = ledger.citations[i], ledger.remaps[i], ledger.baseline[i]
            out += [f'#### Citation `{i}`', '',
                    f'- As written: ({c.raw})',
                    f'- Quote: "{c.quote}"' if c.quote else '- Quote: none, a paraphrase',
                    f'- Kept hint: {c.kept_hint}' if c.kept_hint else '- Kept hint: none',
                    f'- Baseline against upstream/: {b.status}'
                    + (' (stale at the pin)' if b.status not in PASS else ''),
                    f'- At the head: {r.state}, found by {r.found}'
                    + (f', `{r.path}`, {fmt_lines(r.spans)}' if r.spans else '')
                    + f', score {r.score:.2f}', '',
                    'The rule in kstack:', '', '> ' + _rule(flat, opened.get(i, 0)), '',
                    f'Upstream at the pin, {fmt_lines(c.spans)}:', '', '> ' + (r.old or '(none)'),
                    '', 'Upstream at the head'
                    + (f', {fmt_lines(r.spans)}:' if r.spans else ': not found'), '',
                    '> ' + (r.new or '(none)'), '']
    return '\n'.join(out)


def brief_text(n: int, kfiles: list[str], sections: dict[str, str]) -> str:
    '''brief `n`: a header naming the kstack files it covers, what to return, and their sections.'''
    head = [f'# Brief {n}', '', f'Kstack files: {len(kfiles)}.', ''] + [f'- `{k}`' for k in kfiles]
    return '\n'.join(head + ['', JUDGE, ''] + [sections[k] for k in kfiles])


def pack(ledger: Ledger, run: Path, cap: int = CAP) -> list[tuple[list[str], str]]:
    '''
    the briefs as kstack files and text: each kstack file with a citation left to judge goes whole
    into one, in path order, and a brief takes the next file while its whole text, the paths each
    section names in `run` included, stays within `cap` bytes, so a file over `cap` gets a brief
    of its own.
    '''
    sections = {k: s for k in ledger.by_kfile() if (s := section_for(k, ledger, run))}
    groups: list[list[str]] = []
    for k in sections:
        if groups and len(brief_text(len(groups), groups[-1] + [k], sections).encode()) <= cap:
            groups[-1].append(k)
        else:
            groups.append([k])
    return [(g, brief_text(n, g, sections)) for n, g in enumerate(groups, 1)]
