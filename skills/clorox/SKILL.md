---
name: clorox
description: "Moves a git project's proven leftovers into a bin under ~/.clorox: cache folders tagged with a CACHEDIR.TAG signature, __pycache__ folders holding only .pyc files, iCloud \" 2\" copies identical to their original, and clean, merged, idle worktrees. Leaves everything else in place, lists branches holding unmerged commits, and deletes bin batches older than 30 days. Use only as robovac's cleaning step, which supplies the target and the run folder."
---

# clorox

`C=${CLAUDE_SKILL_DIR}/scripts/clorox.py`

## Steps

| # | Step | Who | Source |
|---|---|---|---|
| 1 | `$C sweep --in <target> --out <run>/clorox.md`, with robovac's `<target>` and `<run>` | script | "A deterministic lever beats fan-out. If the tool can process every unit in one pass, run it yourself." (pstack, `skills/principle-build-the-lever/SKILL.md`, l. 16) |
| 2 | `$C empty` | script | "Claude Code deletes the files in the paths below once they're older than `cleanupPeriodDays` … The default is 30 days" (Anthropic, 2026a) |
| 3 | Reply with the lines step 1 printed | model | "`df -h /` before and after with space reclaimed, the worktrees pruned, and a one-line reason for each held back" (pstack, `skills/poteto-mode/playbooks/worktree-cleanup.md`, l. 14) |

## Into the bin

| Item | Proof | Source |
|---|---|---|
| A tagged cache folder | `CACHEDIR.TAG` opens with `Signature: 8a477f597d28d172789f06886806bc55` | "the first 43 octets of this file must consist of the following ASCII header string" (Ford, 2004) |
| A `__pycache__` folder | holds only `.pyc` files | "write and search for byte code cache files in a single directory … called `__pycache__`"; "the py file is recompiled and a new pyc file is written" (Python, 2009) |
| An iCloud twin, `<name> 2` | its original exists and matches byte for byte | a duplicate "has the same name with a number added to the end" (Apple, 2026); *(kstack: a twin moves only when its original exists, since a twin can be the only copy)* |
| A linked worktree | clean, merged into main, unlocked, not in use, and holding no commit that no branch, tag or remote has | "Per Autonomy, clean and merged and not-in-use proceeds." (pstack, `skills/poteto-mode/playbooks/worktree-cleanup.md`, l. 8); "refs inside `refs/bisect`, `refs/worktree` and `refs/rewritten` are not shared" (Git, 2026) |

## Stays where it is

| Item | Source |
|---|---|
| Anything git tracks | *(kstack: a tracked file changes only through `/build`, never in a cleaning pass)* |
| A name the settings deny reading (`.env`, `*.pem`, …), at any depth, and a twin of one | `permissions.deny` in `~/.claude/settings.json`, and in the main worktree's `.claude/settings.json` and `.claude/settings.local.json` where they exist |
| A worktree a process works in, or one that is locked | "every step guards against deleting something in use" (pstack, `skills/poteto-mode/playbooks/worktree-cleanup.md`, l. 3); "This also prevents it from being moved or deleted." (Git, 2026) |
| A worktree a session worked in within 5 days: its path, followed by `/` or `"`, is in a transcript under `~/.claude/projects`, subagents' included, written in that time. Every worktree stays when such a transcript cannot be read | "the newest chat that touched it" (pstack, `skills/poteto-mode/playbooks/worktree-cleanup.md`, l. 5); "Match path followed by "/" or a quote so glint-482 does not match glint-482-r37." (pstack, `skills/poteto-mode/scripts/worktree-audit.sh`, ll. 63–64), and a chat within `-le 4` days is `verify-recent-chat` (pstack, `skills/poteto-mode/scripts/worktree-audit.sh`, ll. 72, 76); that test divides the age by 86400 into whole days, so it holds anything under 5 days, which is the window here *(kstack: every project folder is read, not only this repository's, since kstack's work runs from other workspaces' sessions, as stack-check's digest found)* |
| A worktree with changed or untracked files, or whose HEAD is not on main | when "the worktree has work in it", where work is "changed or untracked files", "Claude prompts you to keep or remove the worktree" (Anthropic, 2026b); `git merge-base --is-ancestor "$head" origin/main` (pstack, `skills/poteto-mode/scripts/worktree-audit.sh`, l. 42) *(kstack: the local `main` is the trunk here, since `origin/main` lags until a push; build `gate.md`, Merge preparation, works "with local merges in place of PRs")* |
| A worktree under `.claude/worktrees/` | "The same age cutoff applies to automatic removal of orphaned worktrees" (Anthropic, 2026a) |
| Anything that cannot be read, and anything not proven above | when Claude Code "can't count the worktree's changes … it prompts you rather than removing the worktree automatically" (Anthropic, 2026b) |
| Anything outside `<target>`, and every worktree and branch when `<target>` is not the main worktree's root | *(kstack: a sweep scoped to one folder stays inside it, so a scoped pass never touches the rest of the project)* |
| A branch ahead of its upstream, or with none and not merged into main. It is listed | *(kstack: clorox moves nothing a branch holds, so it lists the commits that live only here)*; the motive is "Make the work durable." (pstack, `skills/poteto-mode/playbooks/pause-safely.md`, l. 7), whose step goes on to commit, which a cleaning pass does not |
| Processes | "Never kill by process name; kill what you started." (pstack, `skills/create-verification-skill/SKILL.md`, l. 31) |

## The bin

| Rule | Source |
|---|---|
| It lives at `~/.clorox/<repo>/<time>/`, outside Desktop and Documents | "When you store your Desktop and Documents folders in iCloud Drive, you can access files from your Mac on all your devices" (Apple, 2026) |
| A worktree in the bin stays locked | "to prevent its administrative files from being pruned automatically" (Git, 2026) |
| `$C bin` lists it. `$C restore <id>` moves an item back and unlocks a worktree | (under `skills/.trash/`) "The files stay here so you can recover them" (Anthropic, 2026a); "to prevent its administrative files from being pruned automatically" (Git, 2026) (restore puts the worktree back at its own path, so git's links to it still hold and `repair` has nothing to mend) |
| Step 2 deletes batches older than 30 days | "The default is 30 days" (Anthropic, 2026a) |

## Not carried from worktree-cleanup

| Part | Why |
|---|---|
| Step 2's pinned set: "Get that set from the user or sidebar and cross-check every candidate." | Dropped: an unattended pass has no person to give it, and `$C restore` brings a binned worktree back |
| `worktree-audit.sh`'s `hold-open-pr` bucket | Dropped: an open PR's branch is not on main, so the merge rule above already keeps its worktree |

## References

- Anthropic (2026a). Explore the .claude directory. https://code.claude.com/docs/en/claude-directory
- Anthropic (2026b). Run parallel sessions with worktrees. https://code.claude.com/docs/en/worktrees
- Apple (2026). iCloud User Guide. https://support.apple.com/guide/icloud/welcome/icloud
- Ford, B. (2004). Cache Directory Tagging Specification. https://bford.info/cachedir/
- Git (2026). git-worktree Documentation. https://git-scm.com/docs/git-worktree
- Python (2009). PEP 3147: PYC Repository Directories. https://peps.python.org/pep-3147/
