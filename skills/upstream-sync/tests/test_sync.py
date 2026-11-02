#!/usr/bin/env python3
"""
test_sync — builds two throwaway upstream repositories and a throwaway kstack whose
upstream/sources.json names them by file:// URL, and checks what `sync.py` check, scan and settle
report. No check touches the network or the real repository.

Run it with `python3 test_sync.py`. It needs git. It makes one temporary folder and runs git and
sync.py with HOME inside it and no global or system git config, then removes it. The exit code is
the number of failed checks.

P1 to P9 parse each citation form kstack writes: `l. N`, `ll. N–M`, `ll. N, M`, `;`-separated pairs
with the label carried, trailing prose, a quote wrapped across lines, a kstack tag as a
citation's kept hint, a tracked Python file never read, and one id per pair. P10 to P12 hold the parser's
edges: a pair opened by prose, a pair after a prose part naming its path, and the kept hint, the
nearest tag after a citation and before the next one, after another sentence too; P13 holds that
no punctuation between them, an abbreviation or a line label included, hides it. C1 holds the
clean repository:
check exits 0 with no finding. B1 to B3 hold the baseline failures: a wrong line, a quote not at its
line and a missing file. C2 holds a pin the prose leaves out, C3 a changed declared copy. S0 holds
that scan writes the ledger, and S1 a changed imported file: the pin does not prove and its row's
citations are blocked. S2 holds the longest-folder rule for a nested row, and S3 a file .gitignore
leaves out of a whole row. H1 to H6 hold each citation at the head: in sync, shifted lines, moved to
another file, reworded past the threshold and in the brief, deleted, and a renamed file followed. H7
attaches each commit, with its whole message, to the file it touched. D1 to D5 hold the citations
the script decides: a moved citation, at new lines in its file or in another file of the row,
lands in remap.patch with no verdict, no brief holds it, settle counts it as updated, a verdict on
it overrides the ledger, and a quote whose shifted lines no longer hold it whole goes to an agent
instead. D6 to D8 hold that remap.patch edits only the path and numbers of the pair it means: a
citation wrapped across lines keeps its line break, `l. 3` next to `l. 37` leaves `l. 37` alone, and
eleven pairs on one line each take their own new lines. K1 to K3 hold the packing: scan puts small
kstack files in one brief whose header names them, under a cap a file over it gets a brief of its
own, and each citation left to judge sits in exactly one brief; K4 finds no stale brief after a
second scan into the same run folder, K5 that the cap counts each byte of a brief, the paths it
names included, and K6 that a second scan fetches the newest head. T1 to T3 hold the rule a brief quotes: the table cell that holds the citation, the
whole paragraph for a citation on its second line, and the list item itself rather than the one
before it. T4 holds that each upstream file in a brief names its pin copy and its head copy, both
on disk, and T5 that the brief's instructions say the agent may read and search them and edit
nothing. A1 lists a new SKILL.md and,
for a partial row, only SKILL.md files; A2 lists an upstream deletion in reimport.md. M1 is the
mutation: settle refuses a suggested citation that does not hold at the head. M2 checks remap.patch
with `git apply --check`, M3 keeps a row with a blocked citation at its pin in sources.next.json, M4
one with an edited citation that has no verdict, and says why, and M5 refuses a suggested path
outside the clone's import path. X4 holds that the kept hint reaches the brief and kept is counted
from the verdict. V1 to V9 hold pstack's step 6 as written: a row moves unless its pin did not prove, its head
was not fetched, or one of its citations is blocked, so diverged citations move their row and a
blocked one holds its own (V1); reimport.md gives each moving row's NOTICE and upstream/README.md
edit (V2) and leaves a held nested row out of its parent's copy (V3); a failed recheck and a
changed citation with no verdict each hold their row (V4); for a partial row a suggestion fails
the recheck unless reimport.md copies its file (V5), and so does one under another label (V6); a
wrapped line list rewritten in a new shape keeps its line break (V7); and the module docstring
names only Ledger fields, the baseline and the remaps among them (V8); remap.patch edits only
citations in rows that move (V9). W1 to W4 hold round 5: a script move into a partial row's file
that reimport.md does not copy holds its row with no remap.patch edit (W1); when rows sharing one
short commit split, reimport.md's NOTICE and upstream/README.md instructions, followed, leave the
pin check clean (W2); a wrapped line list that opens a line still parses once rewritten (W3); and
an updated verdict with no suggested citation fails the recheck (W4). Y1 and Y2 hold round 6: a
citation whose edit is left out because a held row owns its new path holds the row that owns it as
written (Y1), and a partial row's file that upstream renamed is copied at its new path (Y2),
while scan's SKILL.md count takes in a renamed SKILL.md (Y3). R1 refuses a run folder inside the repository, R2 finds the
repository clean after scan and settle, R3 refuses to scan a tree whose tracked files differ from
HEAD, R4 has settle refuse a run with no ledger and a verdict line with missing keys, in one line
and creating nothing, R5 to R7 a verdict whose id is a list, whose citation is a number, or any
other field of a wrong type or outside its values, kept included, each refused the same way, and U1 the usage.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


HERE    = Path(__file__).resolve().parent
SCRIPT  = HERE.parent / 'scripts' / 'sync.py'
RESULTS = []


def check(name: str, ok: bool, detail: str = '') -> None:
    RESULTS.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f'  ({detail})' if not ok and detail else ''))


def git(cwd: Path, *a: str) -> str:
    return subprocess.run(['git', *a], cwd=cwd, check=True, capture_output=True,
                          text=True).stdout.strip()


def write(root: Path, files: dict[str, str | None]) -> None:
    """each file written under root, or removed when its text is None."""
    for name, text in files.items():
        path = root / name
        if text is None:
            path.unlink()
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


def commit(repo: Path, files: dict[str, str | None], message: str) -> str:
    """the files written and committed with this message; the new commit."""
    write(repo, files)
    git(repo, 'add', '-A')
    git(repo, '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '-m', message)
    return git(repo, 'rev-parse', 'HEAD')


def sync(*argv: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *argv], capture_output=True, text=True)


def doc(*paras: str) -> str:
    return '\n\n'.join(paras) + '\n'


PIN_A = {
    'toolkit/LICENSE': 'MIT\n',
    'toolkit/assets/logo.png': 'an image kstack leaves out\n',
    'toolkit/skills/same/SKILL.md': doc('# same', 'Pin the version before you build.',
                                        'Read the whole file first, then edit the part that '
                                        'matters.', 'Keep each change small.'),
    'toolkit/skills/shift/SKILL.md': doc('# shift', 'Run the tests before every commit.'),
    'toolkit/skills/move-src/SKILL.md': doc('# move-src', 'Name each lock after the state it '
                                            'guards.', 'Other text stays here.', 'And more here.'),
    'toolkit/skills/reword/SKILL.md': doc('# reword', 'Write the failing test first, then make '
                                          'it pass with the smallest change.'),
    'toolkit/skills/del/SKILL.md': doc('# del', 'Never force-push a shared branch.',
                                       'Ask before you delete.'),
    'toolkit/skills/ren/SKILL.md': doc('# ren', 'Squash before merge.', 'Write the reason.'),
    'toolkit/skills/copied/SKILL.md': doc('# copied', 'A verbatim rule.'),
    'toolkit/nested/SKILL.md': doc('# nested', 'Nested rule one.'),
    'toolkit/skills/wrap/SKILL.md': doc('# wrap', 'Keep the build green and the tests fast.'),
}
HEAD_A = [
    ({'toolkit/skills/shift/SKILL.md': doc('# shift', 'A new intro line.',
                                           'Run the tests before every commit.')},
     'shift: add an intro\n\nThe intro says why the tests run first.'),
    ({'toolkit/skills/move-src/SKILL.md': doc('# move-src', 'Other text stays here.',
                                              'And more here.'),
      'toolkit/skills/move-dst/SKILL.md': doc('# move-dst', 'Locks.', 'Name each lock after the '
                                              'state it guards.')},
     'move the lock rule to move-dst'),
    ({'toolkit/skills/reword/SKILL.md': doc('# reword', 'Write the failing test first, then make '
                                            'it pass with the smallest possible change.')},
     'reword: say possible\n\nOn purpose: the change should be the smallest one possible.'),
    ({'toolkit/skills/del/SKILL.md': doc('# del', 'Ask before you delete.')},
     'del: drop the force-push rule'),
    ({'toolkit/skills/ren/SKILL.md': None,
      'toolkit/skills/renamed/SKILL.md': PIN_A['toolkit/skills/ren/SKILL.md']},
     'rename ren to renamed'),
    ({'toolkit/skills/brand-new/SKILL.md': doc('# brand-new', 'A new skill.'),
      'toolkit/skills/brand-new/notes.md': 'notes\n'}, 'add brand-new'),
    ({'toolkit/skills/wrap/SKILL.md': doc('# wrap', 'Why it matters.', 'Keep the build green\n'
                                          'and the tests fast.')}, 'wrap: reflow the rule'),
]
PIN_B = {
    'LICENSE': 'MIT\n',
    'skills/x/SKILL.md': doc('# x', 'Solo rule.'),
    'skills/old/SKILL.md': doc('# old', 'An old skill.'),
    'skills/y/SKILL.md': doc('# y', 'Never imported.'),
}
HEAD_B = [({'skills/old/SKILL.md': None, 'skills/z/SKILL.md': doc('# z', 'New.'),
            'docs/extra.md': 'extra\n'}, 'drop old, add z')]

CITES = doc(
    '# Citations',
    'P1 "Pin the version before you build." (toolkit, `skills/same/SKILL.md`, l. 3).',
    'P2 the passage (toolkit, `skills/same/SKILL.md`, ll. 3–5).',
    'P3 the pair (toolkit, `skills/same/SKILL.md`, ll. 3, 7).',
    'P4 many (toolkit, `skills/same/SKILL.md`, l. 5; `nested/SKILL.md`, l. 3; solo, '
    '`skills/x/SKILL.md`, l. 3; Mayer, 2009).',
    'P5 trailing (toolkit, `skills/same/SKILL.md`, l. 7, for what a test cannot see; the rest is '
    'kstack practice).',
    'P6 wrapped "Read the whole file first, then edit\n   the part that matters." (toolkit,\n   '
    '`skills/same/SKILL.md`, l. 5).',
    'P7 kept "Keep each change small." (toolkit, `skills/same/SKILL.md`, l. 7) and more '
    '*(kstack: kstack keeps it)*.',
    'P9 two (toolkit, `skills/same/SKILL.md`, l. 7) and (toolkit, `skills/same/SKILL.md`, l. 3).',
    'H2 "Run the tests before every commit." (toolkit, `skills/shift/SKILL.md`, l. 3).',
    'H3 "Name each lock after the state it guards." (toolkit, `skills/move-src/SKILL.md`, l. 3).',
    'H4 "Write the failing test first, then make it pass with the smallest change." (toolkit, '
    '`skills/reword/SKILL.md`, l. 3).',
    'H5 "Never force-push a shared branch." (toolkit, `skills/del/SKILL.md`, l. 3).',
    'H6 "Squash before merge." (toolkit, `skills/ren/SKILL.md`, l. 3).',
)


def kstack(root: Path, pin_a: dict[str, str], nested: str, a_url: str, b_url: str,
           pins: dict[str, str]) -> Path:
    """a throwaway kstack whose upstream/ holds the pin copies and whose docs cite them."""
    repo = root / 'kstack'
    git(root, 'init', '-q', '-b', 'main', str(repo))
    files = {f'upstream/{k}': v for k, v in pin_a.items() if '/assets/' not in k}
    files['.gitignore'] = 'upstream/*/assets/\n'
    files['upstream/toolkit/nested/SKILL.md'] = nested
    files.update({f'upstream/solo/{k}': PIN_B[k] for k in ('LICENSE', 'skills/x/SKILL.md',
                                                           'skills/old/SKILL.md')})
    files['upstream/sources.json'] = json.dumps({'imports': [
        {'folder': 'toolkit', 'url': a_url, 'path': 'toolkit', 'commit': pins['a'], 'date': 'd'},
        {'folder': 'toolkit/nested', 'url': a_url, 'path': 'toolkit/nested',
         'commit': pins['nested'], 'date': 'd'},
        {'folder': 'solo', 'url': b_url, 'path': '', 'commit': pins['b'], 'date': 'd',
         'partial': True}], 'copies': {'skills/copied': 'toolkit/skills/copied'}}, indent=1)
    shorts = ' '.join(p[:7] for p in pins.values())
    files['upstream/README.md'] = f'# upstream\n\nPins: {shorts}.\n'
    files['NOTICE'] = f'Imported at {shorts}.\n'
    files['skills/copied/SKILL.md'] = pin_a['toolkit/skills/copied/SKILL.md']
    files['docs/cites.md'] = CITES
    files['tests/fixture.py'] = ('BAD = \'"Not upstream at all." (toolkit, '
                                 '`skills/same/SKILL.md`, l. 1)\'\n')
    commit(repo, files, 'kstack')
    return repo


def variant(repo: Path, root: Path, name: str, files: dict[str, str | None]) -> Path:
    """a copy of the throwaway kstack with these files changed and committed."""
    other = root / name
    shutil.copytree(repo, other, symlinks=True)
    commit(other, files, name)
    return other


def main() -> int:
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t).resolve()
        os.environ.update({'HOME': str(tmp), 'GIT_CONFIG_NOSYSTEM': '1',
                           'GIT_CONFIG_GLOBAL': str(tmp / 'gc')})
        for k in [k for k in os.environ if k.startswith('GIT_') and k not in
                  ('GIT_CONFIG_NOSYSTEM', 'GIT_CONFIG_GLOBAL')]:
            del os.environ[k]
        up_a, up_b = tmp / 'up-a', tmp / 'up-b'
        for up in (up_a, up_b):
            git(tmp, 'init', '-q', '-b', 'main', str(up))
        pin_a = commit(up_a, PIN_A, 'pin')
        nested_v2 = doc('# nested', 'Nested rule one.', 'Nested rule two.')
        pin_nested = commit(up_a, {'toolkit/nested/SKILL.md': nested_v2}, 'nested: rule two')
        for files, message in HEAD_A:
            commit(up_a, files, message)
        pin_b = commit(up_b, PIN_B, 'pin')
        for files, message in HEAD_B:
            head_b = commit(up_b, files, message)
        pins = {'a': pin_a, 'nested': pin_nested, 'b': pin_b}
        repo = kstack(tmp, PIN_A, nested_v2, up_a.as_uri(), up_b.as_uri(), pins)

        spec = importlib.util.spec_from_file_location('sync', SCRIPT)
        sync_mod = importlib.util.module_from_spec(spec)
        sys.modules['sync'] = sync_mod
        spec.loader.exec_module(sync_mod)
        sync_mod.use_repo(repo)
        sources = sync_mod.read_sources(sync_mod.SOURCES)
        cites, unparsed = sync_mod.all_citations(sources)
        at = lambda tag: [c for c in cites if (repo / c.kfile).read_text().splitlines()[
            c.kline - 1].lstrip().startswith(tag)]
        spans = lambda c: [(s.first, s.last) for s in c.spans]
        p1, p2, p3, p4 = at('P1'), at('P2'), at('P3'), at('P4')
        check('P1 `l. N` with its quote', len(p1) == 1 and spans(p1[0]) == [(3, 3)]
              and p1[0].quote == 'Pin the version before you build.', str(p1))
        check('P2 `ll. N–M`', len(p2) == 1 and spans(p2[0]) == [(3, 5)], str(p2))
        check('P3 `ll. N, M`', len(p3) == 1 and spans(p3[0]) == [(3, 3), (7, 7)], str(p3))
        check('P4 `;`-separated pairs: a bare path takes the label before it, and prose is out',
              [(c.label, c.path) for c in p4] == [('toolkit', 'skills/same/SKILL.md'),
                                                  ('toolkit', 'nested/SKILL.md'),
                                                  ('solo', 'skills/x/SKILL.md')], str(p4))
        p5 = at('P5')
        check('P5 trailing prose after the line is kept apart from the lines',
              len(p5) == 1 and spans(p5[0]) == [(7, 7)]
              and p5[0].trailing == 'for what a test cannot see', str(p5))
        p6 = [c for c in cites if c.quote and c.quote.startswith('Read the whole')]
        check('P6 a quote wrapped across lines is read whole',
              len(p6) == 1 and p6[0].quote == 'Read the whole file first, then edit the part that '
              'matters.' and spans(p6[0]) == [(5, 5)], str(p6))
        p7 = at('P7')
        check('P7 a kstack tag after the citation marks it kept, and only that one',
              len(p7) == 1 and p7[0].kept_hint == '*(kstack: kstack keeps it)*'
              and not any(c.kept_hint for c in cites if c is not p7[0]), str(p7))
        check('P8 no unparsed parenthesis, and the tracked Python fixture is never read',
              not unparsed and all(c.kfile.endswith('.md') for c in cites), str(unparsed))
        check('P9 each pair has its own id, two parentheses on one line included',
              len({c.id for c in cites}) == len(cites) == 16, str([c.id for c in cites]))
        parse = lambda text: sync_mod.parse_text('x.md', text, {'toolkit'})
        got, bad = parse('X (toolkit, `a.md`, l. 1; see `b.md`, l. 2).\n')
        check('P10 a pair opened by prose, `see `b.md`, l. 2`, is a pair with the label carried',
              not bad and [(c.label, c.path, spans(c), c.raw) for c in got] == [
                  ('toolkit', 'a.md', [(1, 1)], 'toolkit, `a.md`, l. 1'),
                  ('toolkit', 'b.md', [(2, 2)], 'see `b.md`, l. 2')], str(got) + str(bad))
        text = 'X (toolkit, `a.md`, l. 1; compare `b.md` there; `b.md`, l. 4).\n'
        got, bad = parse(text)
        check('P11 a pair takes its own part as written, not an earlier prose part naming its path',
              not bad and [(c.path, spans(c), c.raw) for c in got] == [
                  ('a.md', [(1, 1)], 'toolkit, `a.md`, l. 1'), ('b.md', [(4, 4)], '`b.md`, l. 4')]
              and all(sync_mod._place(c, text, 0) for c in got), str(got) + str(bad))
        got, _ = parse('A (toolkit, `a.md`, l. 1). B has its own reason *(kstack: mine)*.\n\n'
                       'C (toolkit, `c.md`, l. 1) and D (toolkit, `d.md`, l. 1) *(kstack: d)*.\n')
        check('P12 the kept hint is the nearest kstack tag after a citation in its paragraph, '
              'after another sentence too, and a tag after the next citation is not its hint',
              [c.kept_hint for c in got] == ['*(kstack: mine)*', None, '*(kstack: d)*'],
              str([(c.id, c.kept_hint) for c in got]))
        got, _ = parse(''.join(f'A (toolkit, `a.md`, l. 1), {w} more *(kstack: kept)*.\n\n'
                               for w in ('e.g. on a retry', 'i.e. once', 'etc. and', 'vs. the '
                                         'rest', 'cf. the other', 'see l. 4 and', 'at ll. 2–3 and',
                                         'E.g. here')))
        check('P13 no punctuation between a citation and the next tag, an abbreviation or a line '
              'label included, hides the kept hint',
              len(got) == 8 and all(c.kept_hint == '*(kstack: kept)*' for c in got),
              str([(c.id, c.kept_hint) for c in got]))

        out = sync('check', '--repo', str(repo))
        check('C1 the clean repository: check exits 0 with no finding',
              out.returncode == 0 and 'no finding' in out.stdout, out.stdout + out.stderr)

        bad = variant(repo, tmp, 'bad', {'docs/bad.md': doc(
            '"Pin the version before you build." (toolkit, `skills/same/SKILL.md`, l. 5).',
            '"A sentence upstream never wrote." (toolkit, `skills/same/SKILL.md`, l. 3).',
            '"Pin the version." (toolkit, `skills/nowhere/SKILL.md`, l. 1).')})
        out = sync('check', '--repo', str(bad)).stdout
        check('B1 a wrong line is a finding that says where the quote sits',
              'docs/bad.md:1:' in out and 'quote-elsewhere, the quote sits at 3–3' in out, out)
        check('B2 a quote not at its line, nor anywhere, is a finding',
              'docs/bad.md:3:' in out and 'quote-missing' in out, out)
        check('B3 a missing file is a finding', 'docs/bad.md:5:' in out and 'file-missing' in out,
              out)

        prose = variant(repo, tmp, 'prose', {'NOTICE': f'Imported at {pin_a[:7]}.\n'})
        out = sync('check', '--repo', str(prose))
        check('C2 a pin NOTICE leaves out is a finding', out.returncode == 1
              and f'NOTICE does not name the pin of upstream/solo, {pin_b[:7]}' in out.stdout,
              out.stdout)
        copy = variant(repo, tmp, 'copy', {'skills/copied/SKILL.md': '# copied\n\nChanged.\n'})
        out = sync('check', '--repo', str(copy))
        check('C3 a changed declared copy is a finding', out.returncode == 1 and
              'skills/copied/SKILL.md: differs from upstream/toolkit/skills/copied/SKILL.md'
              in out.stdout, out.stdout)

        run = tmp / 'run'
        out = sync('scan', str(run), '--repo', str(repo))
        ok = out.returncode == 0 and (run / 'ledger.json').is_file()
        check('S0 scan writes the ledger', ok, out.stdout + out.stderr)
        if not ok:
            return RESULTS.count(False)
        ledger = sync_mod.load(run, 'ledger.json')
        state = lambda tag: [ledger.remaps[c.id] for c in at(tag)]
        check('S2 the longest folder owns a file: the nested row proves at its own pin, and the '
              'outer row proves without it',
              sources.owner('toolkit', 'nested/SKILL.md').folder == 'toolkit/nested'
              and ledger.proof == {'toolkit': [], 'toolkit/nested': [], 'solo': []}
              and state('P4')[1].state == 'in sync', str(ledger.proof))
        check('S3 a file at the pin that kstack\'s .gitignore leaves out does not fail the proof',
              not (repo / 'upstream' / 'toolkit' / 'assets').exists()
              and not ledger.proof['toolkit'],
              str(ledger.proof))
        h1 = state('P1')[0]
        check('H1 a passage unchanged at the same lines is in sync', h1.state == 'in sync'
              and h1.found == 'lines', str(h1))
        h2 = state('H2')[0]
        check('H2 shifted lines are moved, with the new lines', h2.state == 'moved'
              and [(s.first, s.last) for s in h2.spans] == [(5, 5)], str(h2))
        h3 = state('H3')[0]
        check('H3 a passage moved to another file of the row is found there', h3.state == 'moved'
              and h3.found == 'quote-elsewhere' and h3.path == 'skills/move-dst/SKILL.md'
              and [(s.first, s.last) for s in h3.spans] == [(5, 5)], str(h3))
        h4 = state('H4')[0]
        brief = run / 'briefs' / '1.md'
        text = brief.read_text() if brief.is_file() else ''
        check('H4 a passage reworded past the threshold is edited, and in the brief with its '
              'commit message whole', h4.state == 'edited' and h4.found == 'fuzzy'
              and at('H4')[0].id in text and 'reword: say possible\n\nOn purpose: the change '
              'should be the smallest one possible.' in text, str(h4))
        h5 = state('H5')[0]
        check('H5 a deleted passage is gone', h5.state == 'gone' and h5.found == 'none', str(h5))
        h6, ren = state('H6')[0], ledger.files['toolkit:skills/ren/SKILL.md']
        check('H6 a renamed file is followed', ren.state == 'renamed'
              and ren.head_path == 'skills/renamed/SKILL.md' and h6.state == 'moved'
              and h6.path == 'skills/renamed/SKILL.md', f'{ren} {h6}')
        shift = ledger.files['toolkit:skills/shift/SKILL.md']
        check('H7 each commit is attached to the file it touched, with its whole message',
              [c.message for c in shift.commits] == ['shift: add an intro\n\nThe intro says why '
                                                     'the tests run first.']
              and [c.message for c in ledger.files['toolkit:skills/same/SKILL.md'].commits] == [],
              str(shift.commits))
        added = [(a.folder, a.path, a.skill) for a in ledger.added]
        check('A1 a new SKILL.md is listed first, and a partial row lists only SKILL.md files',
              added == [('toolkit', 'skills/brand-new/SKILL.md', True),
                        ('toolkit', 'skills/move-dst/SKILL.md', True),
                        ('toolkit', 'skills/brand-new/notes.md', False),
                        ('solo', 'skills/z/SKILL.md', True)], str(added))

        h2_id, h3_id, h4_id, h5_id, h6_id = (at(x)[0].id for x in ('H2', 'H3', 'H4', 'H5', 'H6'))
        verdict = lambda i, outcome, cite, sort='pointer drift', kept=False: json.dumps({
            'id': i, 'sort': sort, 'outcome': outcome, 'commit': None, 'old': '', 'new': '',
            'citation': cite, 'edit': None, 'kept': kept})

        def settle(where: Path, lines: list[str], kstack: Path = repo):
            """settle run on these verdict lines; its output and remap.patch."""
            (where / 'verdicts.jsonl').write_text(''.join(f'{x}\n' for x in lines))
            out = sync('settle', str(where), '--repo', str(kstack))
            patch = where / 'remap.patch'
            return out, patch.read_text() if patch.is_file() else ''

        def full(where: Path, kstack: Path = repo) -> tuple[str, Path]:
            """
            remap.patch with no row held, from the verdicts settle last read in `where`, and the
            file it is written to, so the patch's mechanics are read on rows that hold too.
            """
            sync_mod.use_repo(kstack)
            text = sync_mod.remap_patch(sync_mod.load(where, 'ledger.json'),
                                        sync_mod.read_verdicts(where))
            sync_mod.use_repo(repo)
            path = where.parent / f'{where.name}.full.patch'
            path.write_text(text)
            return text, path

        judged = [verdict(h4_id, 'diverged', None, 'changed on purpose'),
                  verdict(h5_id, 'blocked', None, 'no stated reason')]
        out, _ = settle(run, judged)
        patch, whole = full(run)
        applies = subprocess.run(['git', 'apply', '--check', str(whole)], cwd=repo,
                                 capture_output=True, text=True)
        check('D1 a moved citation, at new lines in its file or in another file of the row, lands '
              'in remap.patch from the ledger with no verdict',
              out.returncode == 0 and applies.returncode == 0
              and '+H2 "Run the tests before every commit." (toolkit, `skills/shift/SKILL.md`, '
              'l. 5).' in patch and '+H3 "Name each lock after the state it guards." (toolkit, '
              '`skills/move-dst/SKILL.md`, l. 5).' in patch
              and '+H6 "Squash before merge." (toolkit, `skills/renamed/SKILL.md`, l. 3).' in patch,
              out.stdout + applies.stderr + patch)
        briefs = '\n'.join(p.read_text() for p in sorted((run / 'briefs').rglob('*.md')))
        moved_ids = sorted(i for i, r in ledger.remaps.items() if r.state == 'moved')
        check('D2 no brief holds a moved citation', moved_ids == sorted([h2_id, h3_id, h6_id])
              and briefs and not any(f'`{i}`' in briefs for i in moved_ids), str(moved_ids))
        printed = out.stdout.splitlines()
        check('D3 settle counts a moved citation with no verdict as updated, decided by the script',
              'updated: 3' in printed and 'updated by the script: 3' in printed
              and not any(x.startswith('no verdict') for x in printed), out.stdout)
        out, _ = settle(run, judged + [
            verdict(h3_id, 'diverged', None, 'changed on purpose'),
            verdict(h6_id, 'updated', '(toolkit, `skills/renamed/SKILL.md`, ll. 3–5)')])
        patch, _ = full(run)
        check('D4 a verdict on a moved citation overrides the ledger',
              out.returncode == 0 and 'move-dst' not in patch
              and '`skills/renamed/SKILL.md`, ll. 3–5).' in patch
              and '`skills/shift/SKILL.md`, l. 5).' in patch, out.stdout + patch)
        more = variant(repo, tmp, 'more', {'docs/wrap.md': doc(
            '# Wrap', 'W1 "Keep the build green and the tests fast." (toolkit, '
            '`skills/wrap/SKILL.md`, l. 3).')})
        run3 = tmp / 'run3'
        sync('scan', str(run3), '--repo', str(more))
        led3 = sync_mod.load(run3, 'ledger.json')
        w1 = led3.remaps['docs/wrap.md:3:1']
        out, _ = settle(run3, [], more)
        patch, _ = full(run3, more)
        briefs3 = '\n'.join(p.read_text() for p in sorted((run3 / 'briefs').rglob('*.md')))
        check('D5 a quote found at the head whose shifted lines no longer hold it whole goes to an '
              'agent, not into remap.patch', w1.state == 'edited' and w1.found == 'quote'
              and '`docs/wrap.md:3:1`' in briefs3 and 'skills/wrap/' not in patch
              and 'skills/shift/SKILL.md`, l. 5).' in patch, f'{w1} {patch}')

        wrapped = doc('# Wrapped', 'W1 "Run the tests before every commit." (toolkit,\n   '
                      '`skills/shift/SKILL.md`, l. 3).', 'W2 "Run the tests before every '
                      'commit." (toolkit, `skills/shift/SKILL.md`,\n  l. 3) and more.')
        near = doc('# Near', 'N1 (toolkit, `skills/shift/SKILL.md`, l. 37) and "Run the tests '
                   'before every commit." (toolkit, `skills/shift/SKILL.md`, l. 3).')
        patching = variant(repo, tmp, 'patching', {'docs/wrapped.md': wrapped,
                                                   'docs/near.md': near})
        run5 = tmp / 'run5'
        sync('scan', str(run5), '--repo', str(patching))
        out, _ = settle(run5, [], patching)
        _, whole = full(run5, patching)
        applied = tmp / 'applied'
        shutil.copytree(patching, applied, symlinks=True)
        done = subprocess.run(['git', 'apply', str(whole)], cwd=applied,
                              capture_output=True, text=True)
        got = (applied / 'docs' / 'wrapped.md').read_text()
        check('D6 a citation wrapped across lines keeps its line break in the patched file',
              out.returncode == 0 and done.returncode == 0
              and got == wrapped.replace('l. 3)', 'l. 5)'), done.stderr + got)
        got = (applied / 'docs' / 'near.md').read_text()
        check('D7 `l. 3` and `l. 37` on one line, only `l. 3` remapped, leaves `l. 37` untouched',
              done.returncode == 0 and got == near.replace('l. 3).', 'l. 5).'),
              done.stderr + got)
        pairs = lambda shift: '; '.join(f'`skills/same/SKILL.md`, l. {n + shift}'
                                        for n in range(1, 12))
        many = variant(repo, tmp, 'many', {'docs/many.md': doc('# Many',
                                                               f'M (toolkit, {pairs(0)}).')})
        run6 = tmp / 'run6'
        sync('scan', str(run6), '--repo', str(many))
        led6 = sync_mod.load(run6, 'ledger.json')
        ids = sorted((i for i in led6.citations if i.startswith('docs/many.md:')),
                     key=lambda i: int(i.rsplit(':', 1)[1]))
        votes = {i: sync_mod.Verdict(i, 'pointer drift', 'updated', None, '', '',
                                     f'(toolkit, `skills/same/SKILL.md`, l. {n + 1})', None)
                 for n, i in enumerate(ids, 1)}
        sync_mod.use_repo(many)
        patch6 = sync_mod.remap_patch(led6, votes)
        sync_mod.use_repo(repo)
        check('D8 a line with ten or more pairs remaps each pair to its own new lines',
              len(ids) == 11 and f'+M (toolkit, {pairs(1)}).\n' in patch6, patch6)

        filler = 'This rule runs long on purpose so that its brief passes the cap. ' * 90
        packed = variant(repo, tmp, 'packed', {
            'docs/a.md': doc('# A', 'A "Never force-push a shared branch." (toolkit, '
                             '`skills/del/SKILL.md`, l. 3).'),
            'docs/b.md': doc('# B', 'B "Write the failing test first, then make it pass with the '
                             'smallest change." (toolkit, `skills/reword/SKILL.md`, l. 3).'),
            'docs/big.md': doc('# Big', filler + '"Never force-push a shared branch." (toolkit, '
                               '`skills/del/SKILL.md`, l. 3).')})
        run4 = tmp / 'run4'
        out = sync('scan', str(run4), '--repo', str(packed))
        led4 = sync_mod.load(run4, 'ledger.json')
        names = sorted(p.name for p in (run4 / 'briefs').iterdir())
        first = (run4 / 'briefs' / '1.md').read_text() if names else ''
        kfiles = ['docs/a.md', 'docs/b.md', 'docs/big.md', 'docs/cites.md']
        check('K1 scan packs small kstack files into one brief, whose header names each of them',
              out.returncode == 0 and names == ['1.md']
              and all(f'- `{k}`' in first.split('Judge each')[0] for k in kfiles)
              and 'briefs: 1,' in out.stdout, out.stdout + str(names))
        sync_mod.use_repo(packed)
        small = sync_mod.pack(led4, run4, cap=5000)
        sync_mod.use_repo(repo)
        sizes = [len(t.encode()) for _, t in small]
        check('K2 under a cap, two small kstack files share a brief and a file over the cap gets '
              'a brief of its own', [g for g, _ in small] == [kfiles[:2], kfiles[2:3], kfiles[3:]]
              and sizes[0] <= 5000 < sizes[1], str([(g, len(t)) for g, t in small]))
        judged = [i for i, r in led4.remaps.items() if r.state not in sync_mod.DECIDED]
        seen = [sum(t.count(f'Citation `{i}`') for _, t in small) for i in judged]
        check('K3 every citation left to judge sits in exactly one brief', len(judged) == 5
              and seen == [1] * len(judged) and first.count('#### Citation `') == len(judged),
              str(list(zip(judged, seen))))
        sync_mod.use_repo(packed)
        two = len(sync_mod.brief_text(1, kfiles[:2], {k: sync_mod.section_for(k, led4, run4)
                                                      for k in kfiles[:2]}).encode())
        edge = [[g for g, _ in sync_mod.pack(led4, run4, cap=c)][0] for c in (two, two - 1)]
        sync_mod.use_repo(repo)
        check('K5 pack counts every byte of a brief, the paths it names included: a cap of '
              'exactly two files\' brief keeps them together, and one byte less splits them',
              edge == [kfiles[:2], kfiles[:1]], f'{two} {edge}')
        huge = variant(repo, tmp, 'huge', {'docs/huge.md': doc(
            '# Huge', 'This rule runs long on purpose. ' * 3500 + '"Never force-push a shared '
            'branch." (toolkit, `skills/del/SKILL.md`, l. 3).')})
        run7 = tmp / 'run7'
        sync('scan', str(run7), '--repo', str(huge))
        before = sorted(p.name for p in (run7 / 'briefs').iterdir())
        out = sync('scan', str(run7), '--repo', str(repo))
        after = sorted(p.name for p in (run7 / 'briefs').iterdir())
        one = (run7 / 'briefs' / '1.md').read_text() if after else ''
        check('K4 a second scan into the same run folder leaves no stale brief',
              out.returncode == 0 and before == ['1.md', '2.md'] and after == ['1.md']
              and 'docs/huge.md' not in one and 'briefs: 1,' in out.stdout,
              f'{before} {after} {out.stdout}')

        table = doc('# Table', '| # | Who | Rule |\n|---|---|---|\n| 1 | agent | T1 "Never '
                    'force-push a shared branch." (toolkit, `skills/del/SKILL.md`, l. 3) |',
                    'T2 the rule wraps\nonto a second line "Write the failing test first, then '
                    'make it pass with the smallest change." (toolkit, `skills/reword/SKILL.md`, '
                    'l. 3).', '- an item with no citation\n- T3 "Never force-push a shared '
                    'branch." (toolkit, `skills/del/SKILL.md`, l. 3).')
        tabled = variant(repo, tmp, 'tabled', {'docs/table.md': table})
        run8 = tmp / 'run8'
        sync('scan', str(run8), '--repo', str(tabled))
        briefs8 = '\n'.join(p.read_text() for p in sorted((run8 / 'briefs').glob('*.md')))
        line_of = lambda s: next(n for n, x in enumerate(table.splitlines(), 1) if s in x)

        def rule_of(cid: str) -> str | None:
            """the line a brief quotes under "The rule in kstack" for one citation, or None."""
            part = briefs8.split(f'#### Citation `{cid}`', 1)
            m = re.search(r'The rule in kstack:\n\n> (.*)\n', part[1]) if len(part) == 2 else None
            return m.group(1) if m else None

        t1 = rule_of(f'docs/table.md:{line_of("T1 ")}:1')
        check('T1 a citation in the third cell of a table row gets that cell as its rule',
              t1 == 'T1 "Never force-push a shared branch." (toolkit, `skills/del/SKILL.md`, l. 3)',
              repr(t1))
        t2 = rule_of(f'docs/table.md:{line_of("onto a second line")}:1')
        check('T2 a citation on the second line of a paragraph gets the whole paragraph',
              t2 == 'T2 the rule wraps onto a second line "Write the failing test first, then '
              'make it pass with the smallest change." (toolkit, `skills/reword/SKILL.md`, l. 3).',
              repr(t2))
        t3 = rule_of(f'docs/table.md:{line_of("- T3")}:1')
        check('T3 a citation in a list item right under another item gets its own item',
              t3 == '- T3 "Never force-push a shared branch." (toolkit, `skills/del/SKILL.md`, '
              'l. 3).', repr(t3))
        sections = briefs.split('\n### `')[1:]
        named = [(re.search(r'^- Pin copy: `([^`]+)`$', s, re.M),
                  re.search(r'^- Head copy: `([^`]+)`$', s, re.M)) for s in sections]
        pins_ok = [bool(p) and Path(p.group(1)).is_file()
                   and repo / 'upstream' in Path(p.group(1)).parents for p, _ in named]
        heads_ok = [bool(h) and Path(h.group(1)).is_file()
                    and run / 'clones' in Path(h.group(1)).parents for _, h in named]
        dele = [(Path(p.group(1)).read_text(), Path(h.group(1)).read_text())
                for s, (p, h), a, b in zip(sections, named, pins_ok, heads_ok)
                if s.startswith('toolkit:skills/del/SKILL.md`') and a and b]
        check('T4 each upstream file in a brief names its pin copy in the repository and its head '
              'copy in the run\'s clone, and the head copy is the head',
              len(sections) == 2 and all(pins_ok) and all(heads_ok) and len(dele) == 1
              and 'Never force-push' in dele[0][0] and 'Never force-push' not in dele[0][1],
              str(list(zip(pins_ok, heads_ok))) + briefs[:600])
        header = briefs.split('\n## `')[0]
        check('T5 a brief\'s instructions say the pin and head copies may be read and searched, '
              'and that nothing is edited', all(w in header for w in (
                  'pin copy', 'head copy', 'read', 'search', 'Edit nothing.')), header)

        lines = [verdict(h2_id, 'updated', '(toolkit, `skills/shift/SKILL.md`, l. 4)'),
                 verdict(h3_id, 'updated', '(toolkit, `skills/move-dst/SKILL.md`, l. 5)'),
                 verdict(h4_id, 'diverged', None, 'changed on purpose'),
                 verdict(h5_id, 'blocked', None, 'no stated reason'),
                 verdict(h6_id, 'updated', '(toolkit, `skills/renamed/SKILL.md`, l. 3)')]
        (run / 'verdicts.jsonl').write_text('\n'.join(lines) + '\n')
        out = sync('settle', str(run), '--repo', str(repo))
        check('M1 settle refuses a suggested citation that does not hold at the head',
              out.returncode == 1 and f'{h2_id}: the suggested' in out.stdout
              and 'quote-elsewhere' in out.stdout, out.stdout + out.stderr)
        lines[0] = verdict(h2_id, 'updated', '(toolkit, `skills/shift/SKILL.md`, l. 5)')
        (run / 'verdicts.jsonl').write_text('\n'.join(lines) + '\n')
        out = sync('settle', str(run), '--repo', str(repo))
        patch, whole = full(run)
        applies = subprocess.run(['git', 'apply', '--check', str(whole)], cwd=repo,
                                 capture_output=True, text=True)
        check('M2 remap.patch edits the moved parentheses and passes git apply --check',
              out.returncode == 0 and applies.returncode == 0
              and '+H2 "Run the tests before every commit." (toolkit, `skills/shift/SKILL.md`, '
              'l. 5).' in patch and '`skills/move-dst/SKILL.md`, l. 5)' in patch
              and '`skills/renamed/SKILL.md`, l. 3)' in patch,
              out.stdout + applies.stderr + patch)
        nxt = json.loads((run / 'sources.next.json').read_text())
        moved = {r['folder']: r['commit'] for r in nxt['imports']}
        check('M3 sources.next.json keeps a row with a blocked citation at its pin and moves the '
              'others', moved == {'toolkit': pin_a, 'solo': head_b,
                                  'toolkit/nested': git(up_a, 'rev-parse', 'HEAD')}, str(moved))
        plan = (run / 'reimport.md').read_text()
        check('A2 an upstream deletion is listed in reimport.md',
              '`upstream/solo/skills/old/SKILL.md`' in plan, plan)
        out, _ = settle(run, [verdict(h5_id, 'diverged', None, 'changed on purpose')])
        nxt = json.loads((run / 'sources.next.json').read_text())
        plan = (run / 'reimport.md').read_text()
        check('M4 an edited citation with no verdict keeps its row at its pin, and reimport.md and '
              'settle say which citation holds it', {r['folder']: r['commit'] for r in
                                                     nxt['imports']}['toolkit'] == pin_a
              and h4_id in plan and 'no verdict' in plan and h4_id in out.stdout,
              out.stdout + plan)
        p2_id = at('P2')[0].id
        escape = '(toolkit, `../../../../kstack/NOTICE`, l. 1)'
        out, patch = settle(run, [verdict(p2_id, 'updated', escape)])
        direct = sync_mod.remap_patch(ledger, {p2_id: sync_mod.Verdict(
            p2_id, 'pointer drift', 'updated', None, '', '', escape, None)})
        check('M5 a suggested path outside the clone\'s import path fails the recheck and never '
              'reaches remap.patch', out.returncode == 1 and f'{p2_id}: the suggested' in out.stdout
              and 'NOTICE' not in patch and 'NOTICE' not in direct, out.stdout + patch + direct)
        head_a = git(up_a, 'rev-parse', 'HEAD')
        nested_id = next(c.id for c in at('P4') if c.path == 'nested/SKILL.md')
        solo_id = next(c.id for c in at('P4') if c.label == 'solo')
        commits_of = lambda where: {r['folder']: r['commit'] for r in json.loads(
            (where / 'sources.next.json').read_text())['imports']}
        part_of = lambda plan, folder: plan.split(f'## upstream/{folder}:', 1)[-1].split('\n## ')[0]
        out, v1_patch = settle(run, [verdict(h4_id, 'diverged', None, 'changed on purpose'),
                                     verdict(h5_id, 'diverged', None, 'changed on purpose'),
                                     verdict(nested_id, 'blocked', None, 'no stated reason')])
        moved, plan = commits_of(run), (run / 'reimport.md').read_text()
        check('V1 a row moves unless one of its citations is blocked: two diverged citations, whose '
              'quotes the head has lost at their lines, move their row, and a blocked one holds '
              'its own row, which settle and reimport.md say',
              out.returncode == 0
              and moved == {'toolkit': head_a, 'toolkit/nested': pin_nested, 'solo': head_b}
              and any(x.startswith('held at the pin: upstream/toolkit/nested,') and nested_id in x
                      and 'blocked' in x for x in out.stdout.splitlines())
              and nested_id in part_of(plan, 'toolkit/nested'), f'{moved} {out.stdout} {plan}')
        tool, solo = part_of(plan, 'toolkit'), part_of(plan, 'solo')
        edits = lambda old, new: [f'- In `{f}`, change `{old[:7]}` to `{new[:7]}`.'
                                  for f in ('NOTICE', 'upstream/README.md')]
        check('V2 reimport.md gives each moving row\'s edit to NOTICE and upstream/README.md, its '
              'old short commit to its new one, and none for a held row',
              all(e in tool for e in edits(pin_a, head_a))
              and all(e in solo for e in edits(pin_b, head_b))
              and 'NOTICE' not in part_of(plan, 'toolkit/nested'), plan)
        copy_line = next((x for x in tool.splitlines() if x.startswith('Copy `toolkit`')), '')
        check('V3 a moving row\'s copy leaves out a nested row that holds',
              'leaving out `upstream/toolkit/nested/`, which stays at its pin' in copy_line, plan)
        out, patch4 = settle(run, [verdict(h4_id, 'updated',
                                           '(toolkit, `skills/reword/SKILL.md`, l. 1)'),
                                   verdict(h5_id, 'diverged', None, 'changed on purpose')])
        moved = commits_of(run)
        held_by = [x for x in out.stdout.splitlines()
                   if x.startswith('held at the pin: upstream/toolkit,')]
        out2, _ = settle(run, [verdict(h4_id, 'diverged', None, 'changed on purpose')])
        moved2 = commits_of(run)
        held2 = [x for x in out2.stdout.splitlines()
                 if x.startswith('held at the pin: upstream/toolkit,')]
        check('V4 a suggestion that fails the recheck, and a changed citation with no verdict, '
              'each hold their row, settle says why, and the other rows move',
              moved == moved2 == {'toolkit': pin_a, 'toolkit/nested': head_a, 'solo': head_b}
              and len(held_by) == 1 and f'{h4_id} (its suggestion failed the recheck' in held_by[0]
              and len(held2) == 1 and f'{h5_id} (no verdict' in held2[0],
              f'{moved} {out.stdout} {moved2} {out2.stdout}')
        check('V9 remap.patch edits only citations in rows that move: a held row\'s moved '
              'citations are left out, and settle names them', patch4 == ''
              and any(x.startswith('left out of remap.patch: upstream/toolkit,') and h2_id in x
                      and h3_id in x and h6_id in x for x in out.stdout.splitlines())
              and '`skills/shift/SKILL.md`, l. 5)' in v1_patch, out.stdout + patch4 + v1_patch)
        rc = lambda i, cite: sync_mod.recheck(sync_mod.Verdict(
            i, 'pointer drift', 'updated', None, '', '', cite, None), ledger, run).status
        got = [rc(solo_id, f'(solo, `{p}`, l. {n})') for p, n in (
            ('skills/y/SKILL.md', 3), ('docs/extra.md', 1), ('skills/z/SKILL.md', 3),
            ('skills/x/SKILL.md', 3))]
        check('V5 for a partial row, a suggestion fails the recheck unless its path is a file '
              'imported now or a new SKILL.md, the files reimport.md copies',
              got[:2] == ['file-missing', 'file-missing'] and all(g in sync_mod.PASS for g in got[2:]),
              str(got))
        got = rc(p2_id, '(solo, `skills/x/SKILL.md`, l. 3)')
        check('V6 a suggestion under another label fails the recheck, since remap.patch edits only '
              'the path and line numbers', got not in sync_mod.PASS, got)
        listed = doc('# Listed', 'L (toolkit, `skills/same/SKILL.md`, ll. 3,\n   5–6).')
        lists = variant(repo, tmp, 'lists', {'docs/listed.md': listed})
        run14 = tmp / 'run14'
        sync('scan', str(run14), '--repo', str(lists))
        led14 = sync_mod.load(run14, 'ledger.json')
        lid = next(i for i in led14.citations if i.startswith('docs/listed.md:'))
        sync_mod.use_repo(lists)
        patch14 = sync_mod.remap_patch(led14, {lid: sync_mod.Verdict(
            lid, 'pointer drift', 'updated', None, '', '', '(toolkit, `skills/same/SKILL.md`, l. 7)',
            None)})
        sync_mod.use_repo(repo)
        applied14 = tmp / 'applied14'
        shutil.copytree(lists, applied14, symlinks=True)
        done = subprocess.run(['git', 'apply', '-'], cwd=applied14, input=patch14, text=True,
                              capture_output=True)
        got = (applied14 / 'docs' / 'listed.md').read_text()
        new = sync_mod.parse_text('docs/listed.md', got, {'toolkit', 'solo'})[0]
        check('V7 a line list wrapped across lines and rewritten in a new shape keeps its line '
              'break in remap.patch', done.returncode == 0
              and len(got.splitlines()) == len(listed.splitlines())
              and [spans(c) for c in new] == [[(7, 7)]], done.stderr + patch14 + got)
        docs = sync_mod.__doc__
        named = set(re.findall(r'`Ledger\.(\w+)`', docs))
        check('V8 each `Ledger.<field>` the module docstring names is a field of the Ledger, the '
              'baseline and the remaps among them',
              {'baseline', 'remaps'} <= named
              <= {f.name for f in sync_mod.dataclasses.fields(sync_mod.Ledger)}, docs)
        up_w, kw, runw = tmp / 'up-w', tmp / 'kw', tmp / 'runw'
        git(tmp, 'init', '-q', '-b', 'main', str(up_w))
        pin_w = commit(up_w, {'LICENSE': 'MIT\n', 'skills/x/SKILL.md': doc('# x', 'Solo rule.'),
                              'skills/y/SKILL.md': doc('# y', 'Never imported.')}, 'pin')
        commit(up_w, {'skills/x/SKILL.md': doc('# x', 'Other.'),
                      'skills/y/SKILL.md': doc('# y', 'Never imported.', 'Solo rule.')},
               'move the solo rule to y')
        git(tmp, 'init', '-q', '-b', 'main', str(kw))
        commit(kw, {'upstream/solo/LICENSE': 'MIT\n',
                    'upstream/solo/skills/x/SKILL.md': doc('# x', 'Solo rule.'),
                    'upstream/sources.json': json.dumps({'imports': [
                        {'folder': 'solo', 'url': up_w.as_uri(), 'path': '', 'commit': pin_w,
                         'date': 'd', 'partial': True}], 'copies': {}}),
                    'upstream/README.md': f'Pin {pin_w[:7]}.\n', 'NOTICE': f'Pin {pin_w[:7]}.\n',
                    'docs/d.md': doc('# d', '"Solo rule." (solo, `skills/x/SKILL.md`, l. 3).')},
               'kstack')
        sync('scan', str(runw), '--repo', str(kw))
        movedw = sync_mod.load(runw, 'ledger.json').remaps.get('docs/d.md:3:1')
        out, patchw = settle(runw, [], kw)
        check('W1 a script move into a partial row\'s file that reimport.md does not copy holds '
              'the row as changed with no verdict, and gets no remap.patch edit',
              movedw is not None and movedw.state == 'moved'
              and movedw.path == 'skills/y/SKILL.md' and patchw == ''
              and commits_of(runw) == {'solo': pin_w}
              and 'updated by the script' not in out.stdout
              and any(x.startswith('held at the pin: upstream/solo,') and 'docs/d.md:3:1' in x
                      and 'no verdict' in x for x in out.stdout.splitlines()),
              f'{movedw} {out.stdout} {patchw}')
        row = sync_mod.Import
        rows_w = [row('toolkit', 'u', 'toolkit', 'a' * 40, 'd'),
                  row('toolkit/nested', 'u', 'toolkit/nested', 'a' * 40, 'd'),
                  row('other', 'u', 'other', 'a' * 40, 'd'),
                  row('solo', 'v', '', 'b' * 40, 'd', True)]
        src_w = sync_mod.Sources(rows_w, {})
        led_w = sync_mod.Ledger('HEAD', src_w, {'u': 'c' * 40, 'v': 'e' * 40},
                                {r.folder: [] for r in rows_w}, {}, {}, {}, {}, [], [], [], [])
        held_w = {'toolkit/nested': 'a citation is blocked: x (blocked)'}
        moved_w = sync_mod.next_sources(led_w, held_w)
        plan_w = sync_mod.reimport_plan(led_w, moved_w, held_w)
        texts = {'NOTICE': 'toolkit, toolkit/nested and other were imported at aaaaaaa, and solo '
                           'at bbbbbbb.\n',
                 'upstream/README.md': 'Pins: aaaaaaa and bbbbbbb.\n\nThe aaaaaaa copy predates '
                                       'it.\n'}
        keeps = []
        for x in plan_w.splitlines():
            m = re.fullmatch(r'- In `([^`]+)`, change `(\w+)` to `(\w+)`\.', x)
            if m:
                texts[m[1]] = texts[m[1]].replace(m[2], m[3])
            m = re.fullmatch(r'- In `([^`]+)`, in each sentence that names `(\w+)`, keep it for '
                             r'(.+), which holds?, and add `(\w+)` for (.+), which moves? to it\.',
                             x)
            if m:
                keeps.append(m.groups())
                texts[m[1]] = texts[m[1]].replace(m[2], f'{m[2]} ({m[3]}) and {m[4]} ({m[5]})')
        got = sync_mod.check_prose(moved_w, texts['upstream/README.md'], texts['NOTICE'])
        check('W2 when rows sharing one short commit split, reimport.md says to keep the held '
              'row\'s pin and add the moving rows\' pin, naming the folders each covers, and '
              'followed it leaves the pin check clean', got == [] and len(keeps) == 2
              and all('`upstream/toolkit/nested`' in k[2] and '`upstream/toolkit`' in k[4]
                      and '`upstream/other`' in k[4] for k in keeps), f'{got} {texts} {plan_w}')
        wrapped = doc('# Wrapped', 'L (toolkit, `skills/same/SKILL.md`,\nll. 3,\n5–6).',
                      'M (toolkit, `skills/same/SKILL.md`,\n   ll. 3,\n   5–6).')
        wraps = variant(repo, tmp, 'wraps', {'docs/wrapped.md': wrapped})
        runw3 = tmp / 'runw3'
        sync('scan', str(runw3), '--repo', str(wraps))
        led_w3 = sync_mod.load(runw3, 'ledger.json')
        wids = [i for i in led_w3.citations if i.startswith('docs/wrapped.md:')]
        sync_mod.use_repo(wraps)
        patch_w3 = sync_mod.remap_patch(led_w3, {i: sync_mod.Verdict(
            i, 'pointer drift', 'updated', None, '', '', '(toolkit, `skills/same/SKILL.md`, l. 7)',
            None) for i in wids})
        sync_mod.use_repo(repo)
        applied_w3 = tmp / 'applied-w3'
        shutil.copytree(wraps, applied_w3, symlinks=True)
        done = subprocess.run(['git', 'apply', '-'], cwd=applied_w3, input=patch_w3, text=True,
                              capture_output=True)
        got = (applied_w3 / 'docs' / 'wrapped.md').read_text()
        new = sync_mod.parse_text('docs/wrapped.md', got, {'toolkit', 'solo'})
        check('W3 a wrapped line list that opens a line, rewritten in a new shape, parses to the '
              'same citation with the new lines and gains no blank line', done.returncode == 0
              and len(wids) == 2 and got.count('\n\n') == wrapped.count('\n\n')
              and not new[1] and [(c.path, spans(c)) for c in new[0]] == [
                  ('skills/same/SKILL.md', [(7, 7)])] * 2, done.stderr + patch_w3 + repr(got))
        bare = sync_mod.recheck(sync_mod.Verdict(h4_id, 'pointer drift', 'updated', None, '', '',
                                                 None, None), ledger, run)
        out, _ = settle(run, [verdict(h4_id, 'updated', None)])
        check('W4 an updated verdict that suggests no citation fails the recheck, so its citation '
              'is blocked, its row holds, and settle says what was wrong',
              bare is not None and bare.status not in sync_mod.PASS and out.returncode == 1
              and any(x.startswith(f'finding: {h4_id}: ') and 'no citation' in x
                      for x in out.stdout.splitlines())
              and commits_of(run)['toolkit'] == pin_a
              and any(x.startswith('held at the pin: upstream/toolkit,')
                      and f'{h4_id} (its suggestion failed the recheck' in x
                      for x in out.stdout.splitlines()), f'{bare} {out.stdout}')
        up_y, ky, runy = tmp / 'up-y', tmp / 'ky', tmp / 'runy'
        git(tmp, 'init', '-q', '-b', 'main', str(up_y))
        y_pin = {'p/skills/a/SKILL.md': doc('# a', 'Moving rule stays put.'),
                 'p/skills/n/SKILL.md': doc('# n', 'Nested rule one.')}
        pin_y = commit(up_y, y_pin, 'pin')
        commit(up_y, {'p/skills/a/SKILL.md': doc('# a', 'Something else.'),
                      'p/skills/n/SKILL.md': doc('# n', 'Nested rule one reworded slightly.',
                                                 'Moving rule stays put.')}, 'move into n')
        git(tmp, 'init', '-q', '-b', 'main', str(ky))
        commit(ky, {**{f'upstream/{k}': v for k, v in y_pin.items()},
                    'upstream/sources.json': json.dumps({'imports': [
                        {'folder': 'p', 'url': up_y.as_uri(), 'path': 'p', 'commit': pin_y,
                         'date': 'd'},
                        {'folder': 'p/skills/n', 'url': up_y.as_uri(), 'path': 'p/skills/n',
                         'commit': pin_y, 'date': 'd'}], 'copies': {}}),
                    'upstream/README.md': f'Pin {pin_y[:7]}.\n', 'NOTICE': f'Pin {pin_y[:7]}.\n',
                    'docs/d.md': doc('# d', '"Moving rule stays put." (p, `skills/a/SKILL.md`, '
                                     'l. 3).', '"Nested rule one." (p, `skills/n/SKILL.md`, l. 3).')},
               'kstack')
        sync('scan', str(runy), '--repo', str(ky))
        out, patchy = settle(runy, [], ky)
        held_p = [x for x in out.stdout.splitlines() if x.startswith('held at the pin: upstream/p,')]
        check('Y1 a citation whose remap.patch edit is left out, since a held row owns its new path, '
              'is blocked for the row that owns it as written, which holds, and settle says why',
              patchy == '' and commits_of(runy) == {'p': pin_y, 'p/skills/n': pin_y}
              and len(held_p) == 1 and 'docs/d.md:3:1 (' in held_p[0]
              and 'upstream/p/skills/n' in held_p[0], f'{out.stdout} {patchy}')
        up_z, kz, runz = tmp / 'up-z', tmp / 'kz', tmp / 'runz'
        git(tmp, 'init', '-q', '-b', 'main', str(up_z))
        z_pin = {'LICENSE': 'MIT\n', 'skills/x/SKILL.md': doc('# x', 'Solo rule.',
                                                             'More text here, long enough.'),
                 'skills/x/notes.md': doc('# notes', 'Some notes that are long enough to match.'),
                 'skills/w/SKILL.md': doc('# w', 'Other rule.')}
        pin_z = commit(up_z, z_pin, 'pin')
        commit(up_z, {'skills/x/SKILL.md': None, 'skills/x/notes.md': None,
                      'skills/z/SKILL.md': z_pin['skills/x/SKILL.md'],
                      'skills/z/notes.md': z_pin['skills/x/notes.md']}, 'rename x to z')
        head_z = git(up_z, 'rev-parse', 'HEAD')
        git(tmp, 'init', '-q', '-b', 'main', str(kz))
        commit(kz, {**{f'upstream/solo/{k}': v for k, v in z_pin.items()},
                    'upstream/sources.json': json.dumps({'imports': [
                        {'folder': 'solo', 'url': up_z.as_uri(), 'path': '', 'commit': pin_z,
                         'date': 'd', 'partial': True}], 'copies': {}}),
                    'upstream/README.md': f'Pin {pin_z[:7]}.\n', 'NOTICE': f'Pin {pin_z[:7]}.\n',
                    'docs/d.md': doc('# d', '"Solo rule." (solo, `skills/x/SKILL.md`, l. 3).')},
               'kstack')
        scan_z = sync('scan', str(runz), '--repo', str(kz))
        led_z = sync_mod.load(runz, 'ledger.json')
        out, patchz = settle(runz, [], kz)
        plan_z = (runz / 'reimport.md').read_text()
        names = lambda p: f'`upstream/solo/skills/{p}`' in plan_z
        check('Y2 for a partial row, a file imported now that upstream renamed stays imported at '
              'its new path: copied accepts it, reimport.md copies the new path and removes the '
              'old one, and a citation into it is remapped there',
              sync_mod.copied(led_z, led_z.sources.imports[0], 'skills/z/notes.md')
              and all(names(f'{d}/{f}') for d in 'xz' for f in ('SKILL.md', 'notes.md'))
              and commits_of(runz) == {'solo': head_z}
              and '`skills/z/SKILL.md`, l. 3)' in patchz, f'{out.stdout} {patchz} {plan_z}')
        added_z = [x for x in scan_z.stdout.splitlines() if x.startswith('added: ')]
        check('Y3 scan\'s SKILL.md count takes in a SKILL.md upstream renamed, as reimport.md '
              'lists it among the additions', added_z == ['added: 2 (1 SKILL.md), removed: 2'],
              scan_z.stdout)
        nowhere = tmp / 'nowhere'
        out = sync('settle', str(nowhere), '--repo', str(repo))
        run9 = tmp / 'run9'
        run9.mkdir()
        shutil.copy(run / 'ledger.json', run9 / 'ledger.json')
        (run9 / 'verdicts.jsonl').write_text(json.dumps({'id': h4_id, 'sort': 'no effect',
                                                         'outcome': 'in sync'}) + '\n')
        short = sync('settle', str(run9), '--repo', str(repo))
        check('R4 settle refuses, in one line and creating nothing, a run folder with no ledger and '
              'a verdict line with missing keys',
              out.returncode == 1 and not nowhere.exists() and 'Traceback' not in out.stderr
              and len((out.stdout + out.stderr).strip().splitlines()) == 1
              and short.returncode == 1 and 'Traceback' not in short.stderr
              and 'verdicts.jsonl:1' in short.stdout
              and len((short.stdout + short.stderr).strip().splitlines()) == 1
              and not (run9 / 'remap.patch').exists(),
              out.stdout + out.stderr + short.stdout + short.stderr)
        base = {'id': h4_id, 'sort': 'no stated reason', 'outcome': 'diverged', 'commit': None,
                'old': '', 'new': '', 'citation': None, 'edit': None, 'kept': False}

        def refused(**over) -> tuple[bool, str]:
            """settle on the ledger and one verdict line with these values: refused in one line?"""
            where = Path(tempfile.mkdtemp(dir=tmp))
            shutil.copy(run / 'ledger.json', where / 'ledger.json')
            (where / 'verdicts.jsonl').write_text(json.dumps({**base, **over}) + '\n')
            out = sync('settle', str(where), '--repo', str(repo))
            said = (out.stdout + out.stderr).strip().splitlines()
            return (out.returncode == 1 and 'Traceback' not in out.stderr and len(said) == 1
                    and said[0].startswith('finding: verdicts.jsonl:1: ')
                    and sorted(p.name for p in where.iterdir()) == ['ledger.json',
                                                                   'verdicts.jsonl'],
                    f'{over}: {out.returncode} {out.stdout.strip()} '
                    f'{(out.stderr.strip().splitlines() or [""])[-1]}')

        ok, why = refused(id=[h4_id])
        check('R5 settle refuses a verdict whose id is a list, in one line and creating nothing',
              ok, why)
        ok, why = refused(citation=5)
        check('R6 settle refuses a verdict whose citation is a number, in one line and creating '
              'nothing', ok, why)
        bad = [refused(**{k: v}) for k, v in (('id', {}), ('sort', 'bogus'), ('sort', 3),
                                              ('outcome', 1), ('commit', 3), ('old', None),
                                              ('new', []), ('citation', ['x']), ('edit', {}),
                                              ('kept', 'yes'), ('kept', None))]
        check('R7 settle refuses each other field of a wrong type or outside its values, in one '
              'line and creating nothing', all(ok for ok, _ in bad),
              '; '.join(why for ok, why in bad if not ok))
        q = {'Q1': '"Run the tests before every commit." (toolkit, `skills/shift/SKILL.md`, l. 3).',
             'Q3': 'the solo rule (solo, `skills/x/SKILL.md`, l. 3).',
             'Q4': '"Keep the build green and the tests fast." (toolkit, `skills/wrap/SKILL.md`, '
                   'l. 3). A later sentence *(kstack: ours)*.',
             'Q7': '"Pin the version before you build." (toolkit, `skills/same/SKILL.md`, l. 3).'}
        qdoc = lambda *tags: doc('# Q', *(f'{t} {q[t]}' for t in tags))
        qid = lambda tags, t: f'docs/q.md:{3 + 2 * tags.index(t)}:1'
        row_tags = ('Q1', 'Q3', 'Q4', 'Q7')
        rows = variant(repo, tmp, 'rows', {'docs/cites.md': None, 'docs/q.md': qdoc(*row_tags)})
        run12 = tmp / 'run12'
        sync('scan', str(run12), '--repo', str(rows))

        def pins(where: Path, lines: list[str], kstack: Path) -> tuple[str, dict[str, str]]:
            """settle on these verdict lines: its printout and each row's commit after it."""
            out, _ = settle(where, lines, kstack)
            nxt = where / 'sources.next.json'
            return out.stdout, {r['folder']: r['commit'] for r in json.loads(
                nxt.read_text())['imports']} if nxt.is_file() else {}

        brief12 = '\n'.join(p.read_text() for p in sorted((run12 / 'briefs').glob('*.md')))
        q4 = qid(row_tags, 'Q4')
        part = brief12.split(f'#### Citation `{q4}`', 1)[-1].split('#### ', 1)[0]
        said = [pins(run12, [verdict(q4, 'updated', '(toolkit, `skills/wrap/SKILL.md`, ll. 5–6)',
                                     kept=k)], rows)[0].splitlines() for k in (True, False)]
        check('X4 the nearest kstack tag after a citation reaches its brief as a kept hint, even '
              'after another sentence, and settle counts kept from the agent\'s verdict alone',
              '- Kept hint: *(kstack: ours)*' in part and 'kept' in brief12.split('#### ', 1)[0]
              and 'kept: 1' in said[0] and not any(x.startswith('kept:') for x in said[1]),
              part + str(said))

        check('R2 the repository is clean after scan and settle',
              git(repo, 'status', '--porcelain') == '', git(repo, 'status', '--porcelain'))
        inside = repo / 'run'
        out = sync('scan', str(inside), '--repo', str(repo))
        check('R1 a run folder inside the repository is refused', out.returncode != 0
              and 'inside the repository' in out.stderr and not inside.exists(), out.stderr)
        dirty = tmp / 'dirty'
        shutil.copytree(repo, dirty, symlinks=True)
        write(dirty, {'docs/cites.md': 'New line.\n\n' + CITES})
        run10 = tmp / 'run10'
        out = sync('scan', str(run10), '--repo', str(dirty))
        check('R3 scan refuses a tree whose tracked files differ from HEAD, so the text scanned is '
              'the text remap.patch applies to', out.returncode == 1
              and 'docs/cites.md' in out.stdout and not (run10 / 'ledger.json').exists(),
              out.stdout + out.stderr)

        changed = variant(repo, tmp, 'unproved', {'upstream/toolkit/skills/same/SKILL.md':
                                                  PIN_A['toolkit/skills/same/SKILL.md'] + 'x\n'})
        run2 = tmp / 'run2'
        sync('scan', str(run2), '--repo', str(changed))
        led2 = sync_mod.load(run2, 'ledger.json')
        toolkit = [r for i, r in led2.remaps.items()
                   if led2.citations[i].label == 'toolkit'
                   and 'nested' not in led2.citations[i].path]
        check('S1 a changed imported file: the pin does not prove and its row\'s citations are '
              'blocked', any('skills/same/SKILL.md: differs' in f for f in led2.proof['toolkit'])
              and toolkit and all(r.state == 'blocked' for r in toolkit)
              and led2.proof['solo'] == [], str(led2.proof))

        newer = commit(up_b, {'docs/later.md': 'later\n'}, 'later')
        out = sync('scan', str(run7), '--repo', str(repo))
        led7 = sync_mod.load(run7, 'ledger.json')
        check('K6 a second scan into the same run folder fetches, so it reports the newest head',
              out.returncode == 0 and led7.heads[up_b.as_uri()] == newer
              and f'solo: {pin_b[:7]} to {newer[:7]}' in out.stdout, out.stdout + str(led7.heads))

        got = [sync(*argv) for argv in (['bogus'], [], ['scan'], ['settle'])]
        check('U1 an unknown command, none, or scan and settle with no run folder exit 2',
              all(r.returncode == 2 for r in got) and 'Commands' in got[0].stdout,
              str([(r.returncode, r.stdout[:30]) for r in got]))
    failed = RESULTS.count(False)
    print(f'{len(RESULTS) - failed}/{len(RESULTS)} passed')
    return failed


if __name__ == '__main__':
    sys.exit(main())
