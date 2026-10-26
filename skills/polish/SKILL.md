---
name: polish
description: "Brings files into the project's house style without changing behavior: comments, dividers, spacing and alignment, docstrings matched to the code they describe, and the markdown docs that cite those files. Defaults to the branch's changed files, and takes a path, a folder or \"all\". Proves Python unchanged by comparing parse trees before and after, and sends anything behavioral to the project's findings backlog. Run it with /polish."
disable-model-invocation: true
---

# polish

You are doing a **behavior-preserving hygiene pass**: making each file match the house style and
making its docs tell the truth about the code — without changing what the code *does*.

The shape in one line: **load the live rules, resolve the scope, polish each file, prove nothing
changed, then report what you fixed and send the behavioral findings to the findings backlog.**
Polishing a file covers style, docstring format, and docstring and markdown freshness. The proof is
the parse tree before against after for Python, and the linter and a cheap build elsewhere.

## The one hard contract: NEVER change behavior

Polish touches comments, whitespace, alignment, docstrings, and markdown docs. It does **not** touch
logic, control flow, names that are imported elsewhere, or anything else observable at runtime.
Docstrings are the one runtime-visible thing it rewrites: a program can read its own through
`__doc__` and print it, so Phase 3 checks those files by running them.

- **Remove nothing that runs.** An unused import, even one ruff F401 flags, is **flagged, never
  removed**: deleting it changes the parse tree, so Phase 3's gate calls it a behavior change and
  reverts it. A dead *export* (module-level name something else might import) is **flagged, never
  removed** too — it reaches across modules, so it belongs in the findings backlog.
- **Cosmetic-only edits.** Re-wording a comment, fixing a divider, aligning columns, reformatting a
  docstring, correcting a `Methods` list — yes. Re-ordering statements, merging duplicated logic,
  narrowing an `except`, fixing a bug — **no**: flag it for the backlog.
- **Prove it.** The pass snapshots each Python file before editing and compares parse trees after
  (see Phase 3). A file in another language rests on Phase 3's cheaper checks, which are weaker
  evidence. A cosmetic edit leaves the tree identical, so a tree that moved names the edit that
  crossed the line, and that edit gets reverted.

This contract is what lets polish auto-apply per file without a review walk of its own, and what
keeps it clear of the skills that do change behavior. *(kstack: polish is kstack's own skill.
pstack's closest is no-comments, which deletes comments that restate code rather than bringing them
into a house style, and its fix-it-in-place pass runs through build, not here.)*

## Phase 0 — Load the live rules (do this first, every run)

Before editing, load the authoritative rules for **this** repo, in order, and let the more specific
source win on any conflict:

1. **The project's own convention docs** — the `Conventions` / `Style` section of the project's
   standing guide (`CLAUDE.md`, `AGENTS.md` or `CONTRIBUTING.md`), plus any style rationale in its
   design or decision docs.
2. **The repo's formatter/linter config** — `ruff` / `black` / `isort` (`pyproject.toml`,
   `.ruff.toml`), `.editorconfig`, `eslint` / `prettier` (`.eslintrc*`, `.prettierrc*`).
   Machine-enforced truth — never fight it.
3. **The user's global style memory**, if the harness exposes one — a personal comment or docstring
   preference that travels across projects.
4. **The tools themselves**, wherever the sources above are silent. Run the repo's formatter and
   linter and follow what they produce. With none configured, the language's standard applies. For
   Python that means `ruff format` on defaults, which collapses aligned assignment columns and
   rewrites `#comment` to `# comment` — a repo wanting either has to say so, which is what tier 1
   is for. Match the docstring convention the file already uses rather than imposing one: a file
   mixing two is the finding, and converting a consistent file is a rewrite, not a polish.

If a project convention or linter config disagrees with the default, the project wins — apply its
rule and note the divergence in the report so the user can reconcile.

**When tier 1 and tier 2 contradict each other, the linter is a hard floor.** Phase 3 requires a
clean lint, so a project rule its own linter rejects cannot be applied without failing the pass.
Apply the linter's answer, leave the project's rule alone, and report the pair for the user to
settle in config.

## Phase 1 — Resolve scope

Default to **what you touched**, not a retroactive codebase sweep (sweeping untouched files churns
diffs and risks style edits nobody asked for):

- `/polish` (no arg) → the branch's changed files: `git diff --name-only main...HEAD` plus the
  working-tree changes.
- `/polish <path>` → that file.
- `/polish <dir>/` → every file under it.
- `/polish all` → the whole package (explicit opt-in to a full sweep; warn it's large and offer to
  fan out — see "Scaling").

**The rule source sets which languages are in scope.** A project that states its comment rules
are language-agnostic has put its stylesheets and scripts in scope alongside its Python, and a
`*.py` filter would silently skip them. A project that speaks only about Python has scoped itself
to Python. Read what the rules claim to cover, and honour the exemptions they name (vendored
directories, generated files). Where the project says nothing, Python is the default.

Print the resolved file list, the languages it spans, and the rule source before editing, then
snapshot it with `scripts/proof.py snapshot` — Phase 3 has nothing to compare against otherwise. The
tree compare proves only the Python files: `snapshot` and `verify` name every other file `NO PARSER`
and leave it to Phase 3's cheap build, which is weaker evidence. For a large list, walk it in a
deterministic order (leaves before callers, or sorted by path) so the report is readable.

## Phase 2 — Polish each file

Read the **whole file** first (you can't judge "blank line above every comment" or "Methods covers
every public name" from a fragment). Then apply the rules Phase 0 loaded.

**Where the project stated a rule, that rule is the rule.** The choice is made per rule, so a
project that states its comment shape and nothing else gets its own comment rule and Phase 0's
tier 4 for everything under it. **A comment says why, not what** — one idea each, and a comment
restating its line gets cut.

Then the three that are polish's own work whatever the style says. The first two read code to
judge whether a claim about it is still true. That is detection work, which stays reliable for
roughly 400 lines at a sitting before you are reading without seeing. Break a long file at a
section boundary and take it in two.

### Docstring freshness — read the code, don't just reformat
This is "update the docstrings," not "reformat them." For each file:
- **Module `Methods` list** enumerates every public name actually defined in the file — add missing
  ones, drop names that no longer exist, fix renamed ones.
- **Each function's `Parameters`/`Returns`** match the real signature and return shape. Canonical
  drift: a changeset adds a field or parameter but the docstring still lists the old set. Verify
  against the code, then correct the docstring (never the code).
- A docstring that describes behavior the code no longer has: correct the docstring to the truth.

### Markdown-doc sync
For modules in scope, scan the project markdown that documents them for references that the code
has outgrown. Start with the standing guide (`CLAUDE.md`, `AGENTS.md` or README), then its design,
decision and `docs/` files. Look for a renamed function or field, a removed export, a stale
`file.py:NN` line cite, or a described mechanism that changed. Correct the doc to match the code.
**Verify each reference against the code before editing the doc** (grep the name, then open the
line). Don't rewrite architecture prose wholesale — fix the specific stale facts.

**Once a fact is confirmed stale, grep its distinctive phrase across the repo and fix every copy
in the same diff.** One claim usually has several homes — a docstring, a comment, a standing
guide — and fixing the one you happened to open leaves the others asserting it.

### Dead and unused imports — flagged, never removed
- An import **ruff F401 flags** goes to the findings backlog, not out of the file. Removing it
  changes the parse tree, so the Phase 3 gate reports `BEHAVIOUR CHANGED`, and Phase 3 sends a
  refused edit through the change gates instead. Trust F401 over your own grep when flagging — it
  understands re-exports and annotation-only use, and grep does not.
- **Three cases that aren't even a flag, though the name looks unused:** a module declaring
  `__all__` (a re-export surface — removing from it silently breaks the package's public API),
  imports inside `if TYPE_CHECKING:` (used only in annotations), and any import already carrying
  `# noqa: F401`.
- A module-level name that *might* be imported elsewhere (a dead export, an unused constant other
  modules could pull): **flag it for the backlog**, and don't remove it.

### Out of scope — hand it off
While polishing you'll notice behavioral issues. Do **not** fix them here. Collect them into a short
"beyond polish" list (bug, duplicated logic, dead export, unused import, broad except, rot,
build-session divergence where dedup would change behavior), surface it at the end, and write each
one into the project's findings backlog so it survives the session. Build-session pollution — the
same value or recipe expressed two ways because two sessions each added their own — is a flag, not
an auto-fix. Normalize it only when it's provably cosmetic, such as a duplicated *comment*.

## Phase 3 — Prove no behavior change

**`scripts/proof.py` is the gate, and it is the only step here that proves the contract.** Run
`snapshot` over the resolved file list in Phase 1, before the first edit. Run `verify` after the
last one. It parses each Python file before and after, drops the docstrings polish is allowed to
rewrite, and compares what is left. A file in any other language prints `NO PARSER`, stays out of
the `N/N` count and leaves the exit code alone. A file deleted since its snapshot prints `MISSING`
and fails. A comment or docstring edit leaves the tree identical. Anything that moves a statement
shows up as `BEHAVIOUR CHANGED`, and that edit gets reverted. Once `verify` passes, run
`proof.py clear`. The baselines live in the working tree's own git directory, so another repo or
worktree never touches them. `snapshot` never replaces a baseline that differs from the file. It
refuses and names the file, because an earlier pass left that file unverified, so verify it or
clear it first.

Two cheaper checks run alongside it, and each answers a smaller question:

1. `ruff check <touched files>` — the linter's own rules, which catch the cosmetic misses the pass
   left behind. Fix what it surfaces.
2. A parse or import — `py_compile` the touched files, or import the package. For a language with
   no parser at hand, its cheap no-op build stands in here (`tsc --noEmit`, `go build ./...`,
   `cargo check`) and carries the whole weight, so treat that pass as weaker evidence.

**Both of those pass on a deleted statement.** `tests/test_proof.py` pins it (M1): dropping an
`os.getenv(...)` call from a function that still uses `os` leaves ruff clean and the file
compiling, and only the tree compare catches it. That gap is why the gate is the tree compare and
these two are support.

**The gate is deliberately conservative, and it will refuse some safe edits.** Rewriting
`Optional[X]` to `X | None` changes the tree while changing nothing at runtime, so `verify` calls
it a behavior change and polish declines it. That is the trade the contract asks for: a refused
edit costs a line in the backlog, and a permissive gate costs a shipped bug. Route such an edit
through the change gates rather than around this one.

A markdown-only pass has no tree to compare, and needs none — a document has no behavior to
preserve. Its gate is Phase 2's rule, **verify each reference against the code before editing the
doc** (grep the name, then open the line), run before each edit rather than after all of them.

The behavioral suite stays out of it: polish edits comments and docstrings, so the tree compare
answers the question those tests would, and answers it in a second. The one exception is a file
that reads `__doc__`, such as a script that prints its module docstring as its usage. There a
docstring edit changes what the program prints, and the tree compare can't see it, because it strips
docstrings.
Run that file's usage before and after the pass, and show both outputs in the report.

## Phase 4 — Report

Per file, one tight line: what categories you fixed (for example,
`models.py — 7 table-interruption comments stripped, Methods list +2`). Then:
- **Proof:** `N/N proved unchanged · ruff clean`, then each `NO PARSER` file with the cheap build
  that stood in for it.
- **Beyond polish (to the findings backlog):** the behavioral findings you deliberately didn't
  touch, each one line with file:line.

Keep it short. The diff is the detail, and the report is the index.

## Scaling (large scope / `/polish all`)

For a big file list, you may fan out: one subagent per file (or per directory), each handed the
resolved rule source, returning a per-file change summary and its "beyond polish" findings. Then you
run the single Phase-3 proof gate over the union and assemble the Phase-4 report. Don't fan out for
a handful of files — just do them inline.

## Language + style rules

- Match the house style you're enforcing — this skill's own edits are themselves house-style.
- Reference code with markdown links: `[file.py](path/file.py)` / `[file.py:42](path/file.py#L42)` —
  never bare backticks for paths.
- Recommend, don't poll: if a fix is genuinely ambiguous (is this an accepted idiom or a
  violation?), lead with your read and apply it; surface borderline calls in the report rather than
  blocking on a question.
