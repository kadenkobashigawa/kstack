---
name: upstream-sync
description: Compares kstack with the newest commits of the sources it imports under upstream/. Runs every citation into upstream/ as it stands, finds where each cited passage sits at the head, and replies with suggested edits, line remaps and new pins, applying none. Run it with /upstream-sync.
disable-model-invocation: true
---

# upstream-sync

`S=${CLAUDE_SKILL_DIR}/scripts/sync.py` · `<run>` is a new folder outside the repository, from
`mktemp -d`. The script refuses a run folder inside the repository.

Ported from pstack's maintain-formal-verification-skill (Lauren Tan, MIT), kept under
`upstream/pstack/skills/maintain-formal-verification-skill/` at `ae5650f`. Read across, upstream's
text is the code, a kstack citation is the verification, and a row's `commit` in
`upstream/sources.json` is the sync commit.

## Outcomes

"Give each check one outcome, and say which:" (pstack,
`skills/maintain-formal-verification-skill/SKILL.md`, l. 13). Here a check is one citation, one
path-and-lines pair.

- **in sync**: the cited passage reads the same at the head, at the same path and lines, and the
  citation held at the pin. "no change since the last sync alters what the check describes, and
  the check passes" (pstack, `skills/maintain-formal-verification-skill/SKILL.md`, l. 15). The
  script decides it alone *(kstack: a passage identical at the same lines leaves nothing to
  judge)*.
- **updated**: the passage moved or was reworded without changing the rule, and the suggested
  citation points at it at the head (pstack, `skills/maintain-formal-verification-skill/SKILL.md`,
  l. 16) *(kstack, the translation: "the verification now describes the new code" becomes "the
  suggested citation does", since nothing is applied)*.
- **diverged**: the citation points at the right passage at the head, and upstream's rule there
  now says something kstack's rule does not. pstack calls it a bug: "This is a finding about the
  code. It is not drift." (pstack, `skills/maintain-formal-verification-skill/SKILL.md`, l. 17)
  *(kstack, the translation: the property is "kstack's rule says what its source says", so the
  finding is about kstack's text, not its pointer)*.
- **blocked**: "Say exactly why." (pstack, `skills/maintain-formal-verification-skill/SKILL.md`,
  l. 18). Step 4 lists when a citation is blocked.

A citation can be both updated and diverged (pstack,
`skills/maintain-formal-verification-skill/SKILL.md`, l. 20).

Two marks go beside an outcome:

- **stale at the pin**: the citation already failed `check` against `upstream/`, before upstream
  moved *(kstack: `upstream/` is the copy at the pin, so a failure there is kstack's own error, not
  drift)*.
- **kept**: the judging agent finds that a `*(kstack: …)*` or `*(kstack, the translation: …)*`
  tag marks the citation's rule as kstack's own, and says so in its verdict's `kept`. The script
  only hints: each brief shows the nearest such tag after the citation, in its paragraph or table
  cell and before the next citation, as its kept hint, and the agent reads the rule to decide
  *(kstack: where a sentence ends is judgment, and two punctuation scans for it failed;
  `skills/build/references/when-a-fix-fails.md`, A scan that keeps growing)*. The reply reports
  upstream's change there and never suggests kstack's rule back to upstream's wording *(kstack:
  CONTRIBUTING.md, Citations, marks such a rule as kstack's own)*.

## Edit scope

Edit nothing. The script writes only in `<run>`, and the skill writes nothing in the repository
*(kstack: a re-import moves the line numbers of every citation into the refreshed folders, and
they must land in one commit with their remaps, so the re-import goes through build when the
operator takes it)*. pstack's own scope is
wider: "Edit only the verification: models, harnesses, property files, and the verify skill
itself." (pstack, `skills/maintain-formal-verification-skill/SKILL.md`, l. 24). Its limit holds
here: "do not weaken the property or the model to make it pass. Report the failure." (pstack,
`skills/maintain-formal-verification-skill/SKILL.md`, l. 24). Never widen a line range, drop a
quote or cite another file to make a diverged citation resolve.

## Steps

| # | Step | Who | Source |
|---|---|---|---|
| 1 | `$S check`. It reads `upstream/sources.json` and checks that NOTICE and `upstream/README.md` each name every row's short commit. It parses every citation in the markdown files git tracks outside `upstream/`, one per path-and-lines pair, and runs each against `upstream/`: the file exists, the lines exist, and the quote sits at the lines. It checks that each folder in `copies` is byte-identical to its `upstream/` source. If `sources.json` is missing or names no import, stop and say so | script | Find the checks: "For each check, collect the property, the code it covers, the bounds and assumptions, the command that runs it, and the commit where it was last confirmed to describe the code." (pstack, `skills/maintain-formal-verification-skill/SKILL.md`, l. 28) *(kstack, the translation: the commit is the row's `commit`, and a file under `upstream/` belongs to the row whose `folder` is its longest match)*. "If no verify skill exists, stop and point at `/create-formal-verification-skill`." (pstack, `skills/maintain-formal-verification-skill/SKILL.md`, l. 28) *(kstack, the translation: a source enters kstack by an import through build, so the stop names the missing file)*. Not carried: "If the skill does not record a sync commit, use the last commit that changed the verification files, and say that you did." (pstack, `skills/maintain-formal-verification-skill/SKILL.md`, l. 28) *(kstack: `sources.json` records every pin, and a run without it stops)*. Run it as it is: "Run each check once before you change anything, and record the result." (pstack, `skills/maintain-formal-verification-skill/SKILL.md`, l. 30). `check` reads no network *(kstack: so build's gates lane can run it on any kstack change)*. The pins in prose *(kstack: NOTICE and `upstream/README.md` state each pin by hand, so `check` fails when either leaves a row's short commit out)*. The copies *(kstack: NOTICE names two verbatim copies, and a declared copy is compared byte for byte rather than guessed)*. "A deterministic lever beats fan-out." (pstack, `skills/principle-build-the-lever/SKILL.md`, l. 16) |
| 2 | `$S scan <run>`. It refuses a tree whose tracked files differ from HEAD, since `remap.patch` applies to the commit scanned. It runs `check` and keeps each result as that citation's baseline. It makes a blobless clone of each repository in `<run>`, or fetches the one already there, with a sparse checkout of the import paths, so the head files arrive in one fetch. It proves each row's pin: the blob ids of the row's folder under `upstream/` equal `git ls-tree -r` at the pin, but for a file kstack's `.gitignore` leaves out, such as each folder's `assets/` image. It reads renames and deletions from one `git diff -M --name-status`, and each commit's full message from `git log --name-only`. It finds each cited passage at the head, lists new SKILL.md files and upstream deletions, and diffs each copy at the head. It writes `<run>/ledger.json`. It packs each kstack file with a citation left to judge into `<run>/briefs/<n>.md`, whole and in path order. A brief takes the next file while it stays within `CAP` bytes, 100,000 in `sync.py`, and a file over `CAP` gets a brief of its own. Each brief opens with the kstack files it covers. A citation is moved when the script finds its cited text the same at other lines or in another file of the row. The citation rewritten to that place must also hold at the head. No brief holds a moved citation, as none holds one in sync. A row whose pin does not prove blocks its citations | script | "Diff the covered files from the sync commit to the current commit, and read each commit message." (pstack, `skills/maintain-formal-verification-skill/SKILL.md`, l. 32). "Also look for code that moved: a covered function that is renamed, split, or moved to another file is still covered code." (pstack, `skills/maintain-formal-verification-skill/SKILL.md`, l. 32) *(kstack: quote-anchored, as the W3C Text Quote Selector and Hypothesis anchor. The line map goes first, then the quote in the head file, then in the row's other head files, then the hit nearest the mapped line, then a fuzzy match whose threshold splits reworded from gone; prior-art check, 2026-10-31)*. "Also look for new code that touches the state that a check guards, such as a new function that writes the same fields." (pstack, `skills/maintain-formal-verification-skill/SKILL.md`, l. 32) *(kstack, the translation: a new SKILL.md under an imported folder, or anywhere in mattpocock/skills, whose import is partial)*. The proof *(kstack: a diff from the pin means something only once each folder equals its repository at the pin, as Go checks vendor/modules.txt against go.mod; prior-art check, 2026-10-31)*. The fetch *(kstack: one batched fetch and never `git log -p`, which fetches once per commit on a blobless clone; prior-art check, 2026-10-31)* |
| 3 | One message, one `Agent` call per brief, `general-purpose`, on `opus`, told it may read and search the pin and head copies its brief names and may edit nothing. Each agent sorts every citation in its brief into one of the four classes below, judging against the passage at the head. It returns one JSON line per citation: the id, the class, the outcome, the commit for a change on purpose, the old and new upstream wording, the suggested citation, the suggested rule edit written from the new upstream text, and kept, true or false, judged from the rule and its kept hint. A citation marked kept gets no rule edit. The root writes the lines to `<run>/verdicts.jsonl` | model | "One read-only subagent per feature file, launched concurrently." (pstack, `skills/maintain-verification-skill/SKILL.md`, l. 29) *(kstack: each agent pays a fixed context of about 75k tokens before it reads its brief, measured in two AIKYAM build runs, 2026-11-01, so scan packs briefs up to a size cap rather than writing one per kstack file)*, with the agent type kstack's maintain-verification-skill names in its step 2 *(kstack: an `Explore` agent does not review)*. The four classes (pstack, `skills/maintain-formal-verification-skill/SKILL.md`, ll. 33–36). "Check this against the model or harness, not against the commit message." (pstack, `skills/maintain-formal-verification-skill/SKILL.md`, l. 33) *(kstack, the translation: against the passage at the head. The script has already checked a moved citation there and found its text unchanged, so no agent judges it)*. Each brief quotes every commit message whole, and a class is the agent's suggestion beside it, never the script's verdict *(kstack: Dependabot, Renovate and Skia's AutoRoller show the messages, and no tool classifies intent from them; prior-art check, 2026-10-31)*. "Write the update from the code before you rerun, and do not shape it by what makes the check pass." (pstack, `skills/maintain-formal-verification-skill/SKILL.md`, l. 38). "Change a property only for a promise that changed on purpose. Write down the old wording, the new wording, and the evidence." (pstack, `skills/maintain-formal-verification-skill/SKILL.md`, l. 38). Not carried: "Keep the bounds unless the change makes them wrong." (pstack, `skills/maintain-formal-verification-skill/SKILL.md`, l. 38), since a citation has no bounds. The model *(kstack: judging a rule against its source is judgment, as stack-check runs its judgment lens on `opus`)* |
| 4 | `$S settle <run>`. It refuses, in one line and creating nothing, a run folder with no ledger, and a verdict line that is not a JSON object, lacks a key, holds a value not of its field's type or outside its field's values, or names a citation the ledger does not hold. It rechecks each suggested citation against the head. A suggestion fails when an updated verdict gives none, when its path is outside the clone's import path, when it names another label than its citation, and, for a partial row, when its path is neither a file imported now, at its new path where upstream renamed it, nor a new SKILL.md. A suggestion that fails there is wrong: rewrite it from the head text, say what was wrong, and run `settle` again. It writes `<run>/sources.next.json`, where a row's pin moves to its head unless its pin did not prove, its head was not fetched, or one of its citations is blocked. A citation belongs to the row that owns its path as written. It is blocked when its verdict says blocked, when its suggestion failed the recheck, or when it got no verdict and the scan found it neither in sync nor moved, as for a citation stale at the pin, or when `remap.patch` leaves its edit out because a held row owns its new path, since it cannot then be made true. A citation the scan moved into a partial row's file that is neither imported now, at its new path where upstream renamed it, nor a new SKILL.md counts as not moved. It writes `<run>/remap.patch`, which edits only citation parentheses and applies to the commit scanned. The patch takes a moved citation's new path and lines from the ledger, and every other edit from a verdict whose suggestion held. A verdict on a moved citation overrides the ledger. The patch edits only citations in rows that move, and leaves out an edit when a held row owns the citation or its new path. It writes `<run>/reimport.md`, which gives for each moving row the copy, leaving out each nested row that holds, every upstream deletion and addition, a partial row's file imported now that upstream renamed listed as an addition at its new path, and the edit to NOTICE and to `upstream/README.md` from the row's old short commit to its new one. Where a held row shares that short commit, the edit is given once, under the first moving row that shares it: in each sentence naming it, keep it for the held rows and add the new one for the moving rows, naming each folder *(kstack: NOTICE and upstream/README.md name several imports in one sentence)*. `reimport.md` and the printout say which rows hold and why, and which citations' edits were left out. It prints the count per outcome, and `kept` counts the verdicts marked kept. A moved citation with no verdict counts as updated when it counts as moved, and the line `updated by the script` gives their number. `settle` runs no citation against the re-import: `check` does, once the operator applies it | script, then model | "If a step cannot happen in the code, the verification is wrong. Fix the verification, and say what was wrong." (pstack, `skills/maintain-formal-verification-skill/SKILL.md`, l. 42) *(kstack, the translation: a suggested citation that does not hold at the head is the wrong one, and so is one `remap.patch` cannot write, since it edits only the path and line numbers, or whose file the re-import does not copy)*. "Set the sync commit to the commit that you checked. Do not move the sync commit for a blocked check, and say so in the report." (pstack, `skills/maintain-formal-verification-skill/SKILL.md`, l. 44) *(kstack, the translation: per row of `sources.json`, a check is one citation, and a citation that got no verdict and that the scan found neither in sync nor moved has not been checked)*. "Then follow the verify skill once as the next agent would, so that you know its steps still run." (pstack, `skills/maintain-formal-verification-skill/SKILL.md`, l. 44) *(kstack, the translation: the verify skill is `$S check`, run on the applied re-import. The operator applies `remap.patch` and `reimport.md` through build, whose gates lane runs `$S check` on that change, so `settle` does not simulate it, and reads `sources.next.json` back with the loader `check` uses)*. Only moving rows' citations *(kstack: a held row is not re-imported, so its citations must still hold at its pin)*. The nested row left out *(kstack: a copy of the outer folder at its head would overwrite a nested row that holds)*. The NOTICE and README edits *(kstack: `check` fails when either leaves a row's short commit out)*. The patch *(kstack: a unified diff, which `git apply --check` refuses once the files have moved, while rule wording stays prose in the reply; prior-art check, 2026-10-31)*. Not carried: "Break the new code the way the property guards against" (pstack, `skills/maintain-formal-verification-skill/SKILL.md`, l. 41) *(kstack: the remaps are the script's own output, so breaking them on every run is the script checking itself, and the script's tests break them instead)* |
| 5 | Apply nothing. Read the Parked table in `upstream/README.md`, and mark each deletion in `<run>/reimport.md` that would remove a parked part. Reply as below | model | "Do not auto-apply." (pstack, `skills/reflect/SKILL.md`, l. 53), as stack-check step 5 carries it. The Parked table *(kstack: a re-import deletes what upstream deleted, and a parked part is kept so it can be ported later, so the root reads the table rather than a parser)* |

## The four classes

Step 3 sorts each change to a cited passage the way pstack sorts a change to covered code:

- **No effect**: the change leaves the cited passage's rule as it was, such as a reflowed line
  or an edit elsewhere in the file (pstack, `skills/maintain-formal-verification-skill/SKILL.md`,
  l. 33). The outcome is in sync or updated.
- **Pointer drift**: "The verification no longer describes the code." (pstack,
  `skills/maintain-formal-verification-skill/SKILL.md`, l. 34). The passage moved lines or files,
  so the citation must change and the rule stands. The outcome is updated.
- **Changed on purpose**: "The promise changed on purpose." (pstack,
  `skills/maintain-formal-verification-skill/SKILL.md`, l. 35). The agent names the commit whose
  message, or whose changed text, says so. The outcome is diverged, or kept under a kstack tag.
- **No stated reason**: "The promise may be broken." (pstack,
  `skills/maintain-formal-verification-skill/SKILL.md`, l. 36). The rule changed and no commit
  says why. The outcome is diverged, and the reply says no evidence was found.

## Reply

"Short list, no preamble:" (pstack, `skills/reflect/SKILL.md`, l. 68), in this order:

1. One line per row of `sources.json`: the old pin, the head, whether the pin proved, and how many
   commits were read.
2. The count per outcome. Then one line per citation that is neither in sync nor updated by the
   script, grouped by kstack file, with its outcome and marks, "the outcome, and the commits that
   you read" (pstack, `skills/maintain-formal-verification-skill/SKILL.md`, l. 50), and the
   suggested edit. The citations updated by the script get one line with their count.
3. Each diverged citation in plain words: the old and new wording, the commit, and the harm, as
   pstack asks a bug to "state the harm in one sentence" (pstack,
   `skills/maintain-formal-verification-skill/SKILL.md`, l. 42). "Say outright which failures were
   drift in the verification and which were bugs in the code." (pstack,
   `skills/maintain-formal-verification-skill/SKILL.md`, l. 56). Here that is pointer drift or a
   rule change, and each citation stale at the pin is named as kstack's own error.
4. What kstack does not cover: new upstream skills, and changed files that no citation names.
   "what the verification still does not cover, including new code that it should cover and does
   not." (pstack, `skills/maintain-formal-verification-skill/SKILL.md`, l. 54).
5. Each upstream deletion, and whether the Parked table names it.
6. The refresh as one suggested commit: `sources.next.json`, the re-import and `remap.patch`.
   Each diverged rule's edit goes in a commit of its own. "Put the verification updates in a change
   of their own, separate from any product fix." (pstack,
   `skills/maintain-formal-verification-skill/SKILL.md`, l. 58) *(kstack, the translation: the
   re-import and its remaps are the verification update, and a rule edit is the product fix)*.
7. "applied: none" *(kstack: as stack-check step 6 ends)*.
