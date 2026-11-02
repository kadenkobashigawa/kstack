'''
settle — what settle makes of the ledger and the agents' verdicts: each suggested citation
rechecked against the head, the rows that stay at their pins, remap.patch, the moved pins and the
re-import plan, and the count per outcome.

Methods
-------
    read_verdicts :
        the agents' verdicts, refused on a line that is not one.
    copied, script_outcome :
        whether the re-import copies a file of a row, and the outcome the scan alone gives a
        citation with no verdict.
    recheck :
        each suggested citation run by `resolve` against its row's head copy.
    pin_holds :
        each row that stays at its pin, because its pin did not prove, its head was not fetched,
        or a citation into it is blocked, and why.
    patch_edits, patch_text, remap_patch :
        the edits remap.patch makes, with those in a held row left out, the patch they make, and
        the patch made from verdicts.
    next_sources, reimport_plan, counts :
        what settle writes and prints.
'''

from __future__ import annotations

import dataclasses
import difflib
import json
import re
import typing
from pathlib import Path

import home
from cite import NUM, escapes, fmt_lines, parse_text, resolve
from home import clone_dir, git, load
from model import PASS, UPDATED, Check, Citation, Import, Ledger, Outcome, Sources, Span, Verdict
from model import decode


# ── the verdicts ──────────────────────────────────────────────────────────────

def read_verdicts(run: Path) -> dict[str, Verdict]:
    '''
    <run>/verdicts.jsonl by citation id, failing on a line that is not a JSON object with every
    key, a value that `decode` refuses as not of its field's type or among its field's values, or
    an id the ledger does not hold; every check is here, so nothing after it meets a bad row.
    '''
    ledger: Ledger = load(run, 'ledger.json')
    hints = typing.get_type_hints(Verdict)
    out = {}
    path = run / 'verdicts.jsonl'
    for n, line in enumerate(path.read_text().splitlines() if path.is_file() else [], 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError as e:
            raise ValueError(f'verdicts.jsonl:{n}: not JSON: {e}') from None
        if not isinstance(row, dict):
            raise ValueError(f'verdicts.jsonl:{n}: not a JSON object')
        missing = [f.name for f in dataclasses.fields(Verdict) if f.name not in row]
        if missing:
            raise ValueError(f'verdicts.jsonl:{n}: no {", ".join(missing)}')
        fields, wrong = {}, []
        for k in hints:
            try:
                fields[k] = decode(hints[k], row[k])
            except ValueError:
                wrong.append(f'{k} {json.dumps(row[k])}')
        if wrong:
            raise ValueError(f'verdicts.jsonl:{n}: not of its field\'s type or values: '
                             + ', '.join(wrong))
        if row['id'] not in ledger.citations:
            raise ValueError(f'verdicts.jsonl:{n}: {row["id"]} is not a citation the ledger holds')
        out[row['id']] = Verdict(**fields)
    return out


def _suggestion(verdict: Verdict, ledger: Ledger) -> Citation | None:
    '''
    a verdict's suggested citation parsed as recheck and remap_patch both read it, a bare
    parenthesis or one opened by its path taking the original's label, or None when it suggests
    none or it does not parse.
    '''
    text = (verdict.citation or '').strip()
    if not text:
        return None
    original = ledger.citations[verdict.id]
    text = text if text.startswith('(') else f'({text})'
    text = f'({original.label}, {text[1:]}' if text.startswith('(`') else text
    found, _ = parse_text('<verdict>', text, {r.label() for r in ledger.sources.imports})
    return dataclasses.replace(found[0], id=verdict.id,
                               quote=found[0].quote or original.quote) if found else None


def copied(ledger: Ledger, row: Import, path: str) -> bool:
    '''
    whether the re-import reimport.md gives copies `upstream/<label>/<path>` of `row`: any file of
    a whole row, and for a partial row a file imported now, a file imported now at the new path
    upstream renamed it to, or a new SKILL.md.
    '''
    return not row.partial or (home.UPSTREAM / row.label() / path).is_file() or any(
        a.folder == row.folder and a.path == path and (a.skill or a.renamed)
        for a in ledger.added)


def _moved(ledger: Ledger, i: str) -> bool:
    '''whether the scan moved citation `i` to a place the re-import copies, as `copied` says.'''
    r, c = ledger.remaps[i], ledger.citations[i]
    row = ledger.sources.owner(c.label, r.path) if r.path else None
    return r.state == 'moved' and row is not None and copied(ledger, row, r.path)


def script_outcome(ledger: Ledger, i: str) -> Outcome | None:
    '''
    the outcome the scan alone gives citation `i`, which has no verdict: `in sync`, `updated`
    for a move into a place the re-import copies, `blocked`, or None for every other state, a
    move the re-import does not copy included, which only an agent can settle.
    '''
    state = ledger.remaps[i].state
    if state == 'moved':
        return 'updated' if _moved(ledger, i) else None
    return state if state in ('in sync', 'blocked') else None


def recheck(verdict: Verdict, ledger: Ledger, run: Path) -> Check | None:
    '''
    the suggested citation parsed and run by `resolve` against the head copy of the row that owns
    its path, in `run`'s clone, the clone's import path its root, or None when there is none. It is
    `unparsed` when an updated outcome suggests no citation, since updated means the suggested
    citation points at the passage at the head, and `file-missing` when no row owns the path, when
    it names another label than the citation, since remap.patch edits only the path and line
    numbers, and when `copied` finds that the re-import does not copy its file.
    '''
    if not (verdict.citation or '').strip():
        if verdict.outcome in UPDATED:
            return Check(verdict.id, 'unparsed', (), 'head')
        return None
    c = _suggestion(verdict, ledger)
    if c is None:
        return Check(verdict.id, 'unparsed', (), 'head')
    row = ledger.sources.owner(c.label, c.path)
    if row is None or escapes(c.path) or c.label != ledger.citations[verdict.id].label:
        return Check(c.id, 'file-missing', (), 'head')
    if not copied(ledger, row, c.path):
        return Check(c.id, 'file-missing', (), 'head')
    clone = clone_dir(run, row.url)
    return resolve(c, clone / row.path if row.path else clone, clone / row.repo_path(c.path),
                   ledger.heads.get(row.url, 'head'))


# ── remap.patch ───────────────────────────────────────────────────────────────

PAIR = re.compile(rf'([^`]*)`([^`]+)`(\s*,\s*)(ll?\.\s*{NUM}(?:\s*,\s*{NUM})*)(.*)$', re.S)


def _flex(text: str) -> str:
    '''a pattern for flattened text, each run of whitespace matching any run, line breaks too.'''
    return ''.join(r'\s+' if part.isspace() else re.escape(part)
                   for part in re.split(r'(\s+)', text) if part)


def _place(citation: Citation, text: str, at: int) -> re.Match | None:
    '''
    the first exact match of a pair's flattened `raw` in a text from offset `at`, opened by `(` or
    `;` and closed by `;` or `)`; group 1 is the path and group 2 the `l. N` or `ll. N–M`.
    '''
    m = PAIR.match(citation.raw)
    if not m:
        return None
    head, path, mid, lines, tail = m.groups()
    return re.compile(rf'[(;]\s*{_flex(head)}`({re.escape(path)})`{_flex(mid)}({_flex(lines)})'
                      rf'{_flex(tail)}(?=\s*[;)])').search(text, at)


def _relined(written: str, old: tuple[Span, ...], new: tuple[Span, ...]) -> str:
    '''
    a pair's `l. N` or `ll. N–M` as written, renumbered to `new`: each number swapped in place when
    the spans keep their shape, so its spacing and line breaks stay, else written afresh after the
    gap that follows `l.` or `ll.`, the gap's line break kept, or, when the break sat inside the
    list, that break put before `l.` or `ll.`, where no number opens a line.
    '''
    numbers = lambda spans: [n for s in spans for n in dict.fromkeys((s.first, s.last))]
    shape = lambda spans: [s.first == s.last for s in spans]
    if shape(old) == shape(new) and len(re.findall(r'\d+', written)) == len(numbers(old)):
        fresh = iter(numbers(new))
        return re.sub(r'\d+', lambda _: str(next(fresh)), written)
    prefix, _, rest = fmt_lines(new).partition(' ')
    m = re.match(r'll?\.(\s*)', written)
    gap = m.group(1)
    breaks = None if '\n' in gap else re.search(r'\n\s*', written[m.end():])
    return (breaks.group() if breaks else '') + prefix + (gap or ' ') + rest


def _order(citation: Citation) -> tuple[int, int]:
    '''a citation's place in its file: its line, then its pair number on that line, as numbers.'''
    return citation.kline, int(citation.id.rsplit(':', 1)[1])


def _pointer(ledger: Ledger, i: str,
             verdict: Verdict | None) -> tuple[str, tuple[Span, ...]] | None:
    '''
    the path and spans remap.patch gives citation `i`, or None when it leaves the citation as
    written: with no verdict, a moved citation's place in the ledger, when the re-import copies
    it; with one, its suggestion, when the outcome is updated or the citation moved, and the path
    stays in its folder.
    '''
    r = ledger.remaps[i]
    if verdict is None:
        return (r.path, r.spans) if _moved(ledger, i) else None
    if verdict.outcome not in UPDATED and r.state != 'moved':
        return None
    new = _suggestion(verdict, ledger)
    return (new.path, new.spans) if new and not escapes(new.path) else None


Edits = dict[str, dict[str, tuple[str, tuple[Span, ...]]]]


def patch_edits(ledger: Ledger, verdicts: dict[str, Verdict],
                held=frozenset()) -> tuple[Edits, dict[str, list[str]]]:
    '''
    the path and spans remap.patch gives each citation it edits, by kstack file and id, and the
    ids of the edits it leaves out, by folder: an edit is left out when a row in `held` owns the
    citation as written or its new path, since only a row that moves is re-imported, so remap.patch
    edits only citations in rows that move.
    '''
    edits: Edits = {}
    left: dict[str, list[str]] = {}
    for i, old in ledger.citations.items():
        to = _pointer(ledger, i, verdicts.get(i))
        if not to or to == (old.path, old.spans):
            continue
        rows = [ledger.sources.owner(old.label, p) for p in (old.path, to[0])]
        stay = [r for r in rows if r is not None and r.folder in held]
        if stay:
            left.setdefault(stay[0].folder, []).append(i)
        else:
            edits.setdefault(old.kfile, {})[i] = to
    return edits, left


def patch_text(ledger: Ledger, edits: Edits) -> str:
    '''
    a unified diff against the commit scanned that makes `edits`, from `patch_edits`, changing
    only the path and line numbers inside citation parentheses. Each file's pairs are found in
    order, every pair from the end of the one before, and each edit keeps the whitespace and line
    breaks around and inside the parenthesis.
    '''
    by_kfile: dict[str, list[Citation]] = {}
    for c in ledger.citations.values():
        if c.kfile in edits:
            by_kfile.setdefault(c.kfile, []).append(c)
    patch = []
    for kfile, wanted in sorted(edits.items()):
        before = git('show', f'{ledger.scanned}:{kfile}', cwd=home.REPO, strip=False)
        starts = [0] + [m.end() for m in re.finditer('\n', before)]
        cuts, at = [], 0
        for old in sorted(by_kfile[kfile], key=_order):
            m = _place(old, before, max(at, starts[min(old.kline, len(starts)) - 1]))
            if not m:
                continue
            at = m.end(2)
            if old.id not in wanted:
                continue
            path, spans = wanted[old.id]
            if path != old.path:
                cuts.append((m.start(1), m.end(1), path))
            if spans != old.spans:
                relined = _relined(m.group(2), old.spans, spans)
                start = back = m.start(2)
                while relined.startswith('\n') and before[back - 1] in ' \t':
                    back -= 1
                if relined.startswith('\n') and before[back - 1] == '\n':
                    relined = relined.lstrip()   # the list opens a line already
                elif relined.startswith('\n'):
                    start = back
                cuts.append((start, m.end(2), relined))
        after = before
        for a, b, new in sorted(cuts, reverse=True):
            after = after[:a] + new + after[b:]
        if after == before:
            continue
        lines = difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                     f'a/{kfile}', f'b/{kfile}')
        patch.append(f'diff --git a/{kfile} b/{kfile}\n')
        for line in lines:
            patch.append(line if line.endswith('\n') else line + '\n\\ No newline at end of file\n')
    return ''.join(patch)


def remap_patch(ledger: Ledger, verdicts: dict[str, Verdict], held=frozenset()) -> str:
    '''
    remap.patch from the verdicts: a moved citation with no verdict takes its head path and lines
    from the ledger, and a citation with a verdict takes the suggestion that held at the head,
    when the outcome is updated or the citation moved, so a verdict on a moved citation overrides
    the ledger. An edit into a row in `held` is left out, as `patch_edits` says, and `patch_text`
    writes the rest.
    '''
    return patch_text(ledger, patch_edits(ledger, verdicts, held)[0])


# ── the pins ──────────────────────────────────────────────────────────────────

def pin_holds(ledger: Ledger, verdicts: dict[str, Verdict],
              failed: frozenset[str] = frozenset()) -> dict[str, str]:
    '''
    each row that stays at its pin, by folder, with why, as "Set the sync commit to the commit
    that you checked. Do not move the sync commit for a blocked check" asks: a row moves to its
    head unless its pin did not prove, its head was not fetched, or a citation into it, by the
    row that owns its path as written, is blocked. A citation is blocked when its verdict says
    blocked, when its suggestion is in `failed`, the ids whose suggestion failed `recheck`, or when
    no verdict judged it and `script_outcome` gives it neither `in sync` nor `updated`, `stale`
    included, since an unjudged check has not been checked, or when `patch_edits` leaves its edit
    out because a held row owns its new path, since it cannot then be made true.
    '''
    out = {}
    for row in ledger.sources.imports:
        if ledger.proof.get(row.folder):
            out[row.folder] = 'the pin did not prove: ' + '; '.join(ledger.proof[row.folder][:3])
        elif not ledger.heads.get(row.url):
            out[row.folder] = 'the head was not fetched'
    why: dict[str, list[str]] = {}
    for i, c in ledger.citations.items():
        row = ledger.sources.owner(c.label, c.path)
        if row is None or row.folder in out:
            continue
        v, r = verdicts.get(i), ledger.remaps[i]
        if i in failed:
            reason = 'its suggestion failed the recheck at the head'
        elif v is not None:
            reason = 'blocked' if v.outcome == 'blocked' else None
        elif (outcome := script_outcome(ledger, i)) is not None:
            reason = 'blocked' if outcome == 'blocked' else None
        elif r.state == 'moved':
            reason = f'no verdict, moved into {r.path}, which the re-import does not copy'
        else:
            reason = f'no verdict, {r.state} at the head'
        if reason:
            why.setdefault(row.folder, []).append(f'{i} ({reason})')
    while why:
        for folder, notes in why.items():
            out[folder] = 'a citation is blocked: ' + ', '.join(notes)
        why = {}
        for folder, ids in patch_edits(ledger, verdicts, frozenset(out))[1].items():
            for i in ids:
                c = ledger.citations[i]
                row = ledger.sources.owner(c.label, c.path)
                if row is not None and row.folder not in out:
                    why.setdefault(row.folder, []).append(
                        f'{i} (its edit is left out of remap.patch, since upstream/{folder} holds)')
    return {r.folder: out[r.folder] for r in ledger.sources.imports if r.folder in out}


def next_sources(ledger: Ledger, held: dict[str, str],
                 dates: dict[str, str] | None = None) -> Sources:
    '''
    the rows with each pin moved to its head, unless `held`, from `pin_holds`, holds it; `dates`
    gives each repository's head date.
    '''
    rows = [row if row.folder in held else dataclasses.replace(
        row, commit=ledger.heads[row.url], date=(dates or {}).get(row.url, row.date))
        for row in ledger.sources.imports]
    return Sources(rows, dict(ledger.sources.copies))


def reimport_plan(ledger: Ledger, moved: Sources, held: dict[str, str],
                  left: dict[str, list[str]] | None = None) -> str:
    '''
    the re-import at the moved pins, as Markdown. For each moving row it gives the copy, which
    leaves out each held row nested in it, every deletion and addition, and the edit to NOTICE and
    upstream/README.md, which `check` reads for every row's short commit. Where moving rows share a
    held row's short commit, that edit is given once, under the first of them: keep the old short
    commit for the held rows and add the new one for the moving rows. For each held row it gives
    why it stays at its pin, from `pin_holds`, and the citations `left`, from `patch_edits`, whose
    edit remap.patch leaves out.
    '''
    out = ['# Re-import at the moved pins', '']
    for old, new in zip(ledger.sources.imports, moved.imports):
        if old.folder in held:
            out += [f'## upstream/{old.folder}: stays at {old.commit[:7]}', '',
                    f'Held: {held[old.folder]}.', '']
            if (left or {}).get(old.folder):
                out += ['Edits left out of remap.patch, since this row holds: '
                        + ', '.join(f'`{i}`' for i in left[old.folder]) + '.', '']
            continue
        inside = [f'`upstream/{f}/`' for f in held if f.startswith(old.folder + '/')]
        out += [f'## upstream/{old.folder}: {old.commit[:7]} to {new.commit[:7]}', '',
                f'Copy `{new.path or "/"}` from {new.url} at {new.commit} into '
                f'`upstream/{new.folder}/`' + (', only the files imported now, at their new paths '
                                               'where upstream renamed them, and each new SKILL.md'
                                               if new.partial else '')
                + (f', leaving out {", ".join(inside)}, which stays at its pin' if inside else '')
                + '.', '']
        keep = [f'`upstream/{r.folder}`' for r in ledger.sources.imports
                if r.folder in held and r.commit[:7] == old.commit[:7]]
        same = [o for o, n in zip(ledger.sources.imports, moved.imports)
                if o.folder not in held and o.commit[:7] == old.commit[:7]
                and n.commit[:7] == new.commit[:7]]
        if new.commit[:7] != old.commit[:7] and not keep:
            out += [f'- In `{f}`, change `{old.commit[:7]}` to `{new.commit[:7]}`.'
                    for f in ('NOTICE', 'upstream/README.md')] + ['']
        elif new.commit[:7] != old.commit[:7] and same[0] is not old:
            out += [f'- `NOTICE` and `upstream/README.md`: the edit under '
                    f'`upstream/{same[0].folder}` names this row.', '']
        elif new.commit[:7] != old.commit[:7]:
            add = ', '.join(f'`upstream/{o.folder}`' for o in same)
            out += [f'- In `{f}`, in each sentence that names `{old.commit[:7]}`, keep it for '
                    f'{", ".join(keep)}, which hold{"s" if len(keep) == 1 else ""}, and add '
                    f'`{new.commit[:7]}` for {add}, which move{"s" if len(same) == 1 else ""} '
                    'to it.' for f in ('NOTICE', 'upstream/README.md')] + ['']
        gone = [p for p in ledger.removed if ledger.sources.owner(*p.split('/', 1)) == old]
        out += [f'Deletions: {len(gone)}.', ''] + [f'- `upstream/{p}`' for p in gone] + ['']
        new_files = [a for a in ledger.added if a.folder == old.folder]
        out += [f'Additions: {len(new_files)}.', ''] + [
            f'- `upstream/{old.label()}/{a.path}`'
            + (f' (renamed from `upstream/{old.label()}/{a.renamed}`)' if a.renamed
               else ' (a new skill)' if a.skill else '')
            for a in new_files] + ['']
        for copy in ledger.copies:
            if ledger.sources.owner(*copy.source.split('/', 1)) == old and copy.at_head:
                out += [f'Copy `{copy.kfolder}` from `upstream/{copy.source}`: '
                        f'{len(copy.at_head)} files differ at the head, in `{copy.diff}`.', '']
    return '\n'.join(out)


def counts(ledger: Ledger, verdicts: dict[str, Verdict]) -> dict[str, int]:
    '''
    the number of citations per outcome and per mark, `stale at the pin`, `kept`, which a verdict
    alone decides, and `updated by the script`, a citation with no verdict that `script_outcome`
    counts as updated, a move into a file the re-import copies; with no verdict and no outcome
    from `script_outcome`, a citation counts as `no verdict`.
    '''
    out: dict[str, int] = {}
    for i, c in ledger.citations.items():
        v = verdicts.get(i)
        outcome = v.outcome if v else script_outcome(ledger, i) or 'no verdict'
        out[outcome] = out.get(outcome, 0) + 1
        if not v and outcome == 'updated':
            out['updated by the script'] = out.get('updated by the script', 0) + 1
        if ledger.baseline[i].status not in PASS:
            out['stale at the pin'] = out.get('stale at the pin', 0) + 1
        if v and v.kept:
            out['kept'] = out.get('kept', 0) + 1
    return out
