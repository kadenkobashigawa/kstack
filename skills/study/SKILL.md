---
name: study
description: "Builds an interactive mind map of one scope (a codebase or part of one, a skill, or notes), opens it beside the chat, and then walks the person through a branch, writes hover cards for it, or quizzes them on it. Use on /study, \"study X\", \"map X\", \"walk me through X\", \"quiz me on X\" or a request for cards on a map."
argument-hint: "[folder, file, skill or notes]"
---

# study

`/study <scope>` maps one idea that has many parts. The map is a page of boxes that open branch by
branch, with a hover card on each tip and a row of small triangles from each mention of a shared
piece to its home. A link whose home is on another map ends at a round vortex portal on the map's
rim. You open it beside the chat, name its top branches in one line, and wait for the person to
name one. From there they ask for a walkthrough lecture, cards or a quiz. study replaces the
verbal study skill and the study-map skill *(kstack: the operator's rule)*.

`S=${CLAUDE_SKILL_DIR}/scripts` · `W=<top>/.study/<scope>`, where `<top>` is the top of the
repository or notes folder the scope lies in. `W` holds the map's files and saved cards, so both
apps share one set *(kstack: the operator's rule)*. `W` lives in `<top>` and never in the home
folder, because Cowork cannot reach `~/.claude` and can be granted only a folder that already
exists. No folder in the home directory works in both apps *(kstack: Cowork refused to create
`~/.study` on 2026-10-26)*. Maps and cards are never committed: in a git repository, add the line
`.study/` to `<top>/.git/info/exclude` once, if it is not there. That file is local to the clone,
so this changes nothing anyone else sees. Never edit `.gitignore`.

You run every command in this skill. The person never runs one *(kstack: the operator's rule)*.

## Scripts do the fixed work, and you do the judgment

Whatever gives the same result every time is a script. Whatever needs judgment is yours, and the
references say how *(kstack: the operator's rule)*. "A deterministic script turns "trust me"
into "run this"." (pstack, `skills/principle-build-the-lever/SKILL.md`, l. 10)

The scripts do this work:

- **`tree.py`** outlines Python and JavaScript code as folders, files, classes, functions and
  methods.
- **`page.py`** checks the Document, its links and the cards, and refuses a bad one with the
  reason. It splits a tree of over 500 nodes into nested maps behind portals, and it builds the
  page.

You do this work:

- **The outline** of a skill, notes or other Markdown: its sections, where they fall, and its
  cross-links.
- **The text:** the cards, the lecture, and the quiz questions.
- **The fixes** to whatever `page.py` refuses.

Never do a script's part by hand. Don't split a map, write the page's HTML, or reshape a
Document that `page.py` accepts.

## Build the map

1. **Check for uv** where you run the scripts. `tree.py` runs under uv, which installs its
   tree-sitter grammars on first run. `page.py` needs only `python3`. If `command -v uv` prints
   nothing, ask the person once for a yes to install uv, and name the command
   `curl -LsSf https://astral.sh/uv/install.sh | sh` *(kstack: write-report's preflight also stops
   on a missing tool and gives its install command)*. On a yes, run that command yourself and go
   on. If `uv` is still not on `PATH`, run it as `$HOME/.local/bin/uv`.
2. **Write the Document** at `$W/tree.json`, after `mkdir -p $W`.
   - For code, run `uv run $S/tree.py <scope> -o $W/tree.json`. The scope is a folder, a file, or
     `file:Symbol`, as a path from the current folder or an absolute one. Spell it as git does,
     case included. Where the disk ignores case, as on a Mac, a scope in another case is refused
     with a message that names git's spelling, so run again with that spelling. Exit 2 prints
     `tree:` and the reason. stderr counts the files that have no grammar by extension, on a line
     that starts `tree: skipped with no grammar:`. When that line names `.md`, the scope holds
     prose that the person likely came to study. Then write the outline Document at
     `$W/tree.json` in place of `tree.py`'s, as the next bullet says, with `tree.py`'s code
     branches in it. Never publish the code-only map *(kstack: the operator's rule)*.
   - For a skill, notes or other Markdown, read every file and write the Document yourself, as
     the next section says. Where such a scope holds code, run `tree.py` on each code folder
     with `-o $W/<folder>.json`, and put the `tree` node of each output into your outline as a
     branch, unchanged.
3. **Build the page:** `python3 $S/page.py $W/tree.json -o $W/map.html`. Add
   `--cards $W/cards.json` once cards exist. In Cowork, add `--artifact`. Exit 2 prints `page:`,
   the file and the reason. Fix that file, the Document or the cards, and build again. stderr
   names the maps, the tips with and without a card, the links, each warning, and each map left
   over the cap.
4. **Open it and wait,** as `references/walkthrough.md` says under "Open the map and wait".

Each app shows the map and quizzes in its own way *(kstack: the operator's rule)*:

- **In Cowork,** which the references call Claude's app, build and publish the map as the next
  section says. The default quiz is `references/quiz-card.md`.
- **In Claude Code,** open `$W/map.html` in the Browser pane. The default quiz is
  `references/ask-user-question.md`.

### Build the map in Cowork

In Cowork, the scripts run on the person's Mac, and you publish the page from the container:

1. **Find the folder.** The repository or notes folder must be a connected folder, and
   `ls $HOME/mnt/` in `device_bash` lists them. If it is not connected, ask the person to connect
   it, and stop.
2. **Copy the scripts to the Mac.** Copy the `scripts`, `assets` and `vendor` folders from
   `${CLAUDE_SKILL_DIR}` to `/mnt/user-data/outputs/study/`. List the files to write, without
   `__pycache__` or `*.pyc`, with this command:
   `find /mnt/user-data/outputs/study -type f -not -path '*/__pycache__/*' -not -name '*.pyc'`.
   `device_commit_files` takes single files, at most 50 a call, so write them in batches of 50 or
   fewer, each to the same place under `<top>/.study/.skill/`. Copy them on every build, so the
   Mac's copy stays current. Keep the three folders side by side, because `page.py` reads `assets`
   and `vendor` beside its own `scripts` folder.
3. **Run the scripts with `device_bash`.** Do steps 1 to 3 of "Build the map" there, with `S`
   set to `<top>/.study/.skill/scripts` and `W` to `<top>/.study/<scope>`, each as the path
   `device_bash` sees under `$HOME/mnt/`. Run git with `GIT_OPTIONAL_LOCKS=0`. The page lands at
   `map.html` in `W`. `device_bash` runs in a Linux VM on the Mac, with the folder mounted and the
   network behind an allowlist. If the allowlist refuses the uv install, or the grammar download
   that `tree.py` makes on its first run, tell the person which download was refused, and stop.
   Never retry it another way *(kstack: the operator's rule)*.
4. **Stage the page** into the container with `device_stage_files`. Give it the page's path on the
   Mac, `<top>/.study/<scope>/map.html`. The result gives the staged path.
5. **Publish the staged file** with the Artifact tool. After each rebuild, stage the page again
   and publish from the same staged path, so the artifact keeps its link.

## Write an outline Document

Write the outline the way a good exam map reads. For the build skill, that is Playbooks, then
Feature, then its steps, then the check each step runs, then that check's reference. Then write it
as this JSON, which `page.py` reads as it reads `tree.py`'s output:

```text
{"schema": 1, "tree": Node, "links": [["pointer id", "home id"]]}
Node = {"id": str, "name": str, "kind": "root" or "dir", "children": [Node]}
```

- **`kind`** is `root` on the top node and `dir` on every other node you write. `page.py` cuts a
  big map only at nodes of kind `root`, `dir` or `file`, and it adds `()` to the label of a
  `function` or a `method`.
- **Layers are section boundaries.** `page.py` cuts a map at its shallowest whole layer that fits,
  so put each section's parts one layer below the section.
- **`name`** is the label, in Title Case. Code nodes from `tree.py` keep their real names.
- **`id`** is unique and stays the same across rebuilds, because saved cards are keyed by id. The
  path of names from the root works, such as `build/Playbooks/Feature`.
- **A shared piece has one home.** Each other place that names it gets a pointer leaf, a node
  with no children, and a link from the pointer's id to the home's id. A pointer leaf is no tip
  and takes no card. A node whose children are all pointer leaves is a tip and takes a card.
- **Links draw from what is on screen.** `page.py` places each link on every map that shows its
  source, as `[from, end, home]`. The end is the home, the portal box that holds it, or the map's
  root. The page draws a link as a row of triangles beneath the boxes, and only while its source's
  own box is on screen. A link whose home is on another map ends at that home's vortex portal.
- **Cover the scope.** Check that every file and every heading in the scope has a place in the
  outline.

## Walk, write cards, or quiz

Load the reference for what the person asks. `references/evidence.md` holds the papers the quiz
references cite.

| The person | Load |
|---|---|
| names a branch, or asks what something does | `references/walkthrough.md` |
| asks for cards on a map or a branch | `references/cards.md` |
| asks for a quiz | the default quiz for the app, above |
| asks to answer out loud | `references/verbal.md` |

`page.py` reads one cards file for all the maps of a set, `$W/cards.json`, keyed by node id.
After you save cards, build the page again and reopen it.

Not built yet: the staleness scan and its red glow, source fingerprints, the token estimate before
cards, and `tree.py`'s list of Markdown files and headings. The references leave them out until
they land. Check an outline's coverage by reading.
