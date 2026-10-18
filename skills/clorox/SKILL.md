---
name: clorox
description: One deterministic cleaning pass over a git project's leftovers, or those under one file or folder of it. Signed caches, __pycache__ folders, identical iCloud " 2" twins and finished worktrees move into a bin; everything else stays; bin batches older than 30 days are deleted. Run by robovac.
---

# clorox

`C=~/.claude/skills/clorox/scripts/clorox.py`

## Steps

| # | Step | Who | Source |
|---|---|---|---|
| 1 | `$C sweep --in <target> --out <run>/clorox.md`, with robovac's `<target>` and `<run>` | script | pstack `principle-build-the-lever`: "A deterministic lever beats fan-out. If the tool can process every unit in one pass, run it yourself." |
| 2 | `$C empty` | script | code.claude.com/docs/en/claude-directory: "Claude Code deletes the files in the paths below once they're older than `cleanupPeriodDays` … The default is 30 days" |
| 3 | Reply with the lines step 1 printed | model | pstack `worktree-cleanup.md`, Reply: "`df -h /` before and after with space reclaimed, the worktrees pruned, and a one-line reason for each held back" |

## Into the bin

| Item | Proof | Source |
|---|---|---|
| A tagged cache folder | `CACHEDIR.TAG` opens with `Signature: 8a477f597d28d172789f06886806bc55` | bford.info/cachedir: "the first 43 octets of this file must consist of the following ASCII header string" |
| A `__pycache__` folder | holds only `.pyc` files | PEP 3147: "write and search for byte code cache files in a single directory … called `__pycache__`"; "the py file is recompiled and a new pyc file is written" |
| An iCloud twin, `<name> 2` | its original exists and matches byte for byte | Apple iCloud User Guide: a duplicate "has the same name with a number added to the end"; memory `feedback_verify_before_bulk_delete`: "check the clean-name original EXISTS before deleting the `" 2"` copy" |
| A linked worktree | clean, merged into main, unlocked, not in use, and holding no commit that no branch, tag or remote has | pstack `worktree-cleanup.md` step 4: "Per Autonomy, clean and merged and not-in-use proceeds."; git-worktree, REFS: "refs inside `refs/bisect`, `refs/worktree` and `refs/rewritten` are not shared" |

## Stays where it is

| Item | Source |
|---|---|
| Anything git tracks | `CLAUDE.md`: "Every code change runs through `/build`" |
| A name the settings deny reading (`.env`, `*.pem`, …), at any depth, and a twin of one | `permissions.deny` in `~/.claude/settings.json`, and in the main worktree's `.claude/settings.json` and `.claude/settings.local.json` where they exist |
| A worktree a process works in, or one that is locked | pstack `worktree-cleanup.md`: "every step guards against deleting something in use"; git-worktree, lock: "This also prevents it from being moved or deleted." |
| A worktree a session worked in within 5 days: its path, followed by `/` or `"`, is in a transcript under `~/.claude/projects`, subagents' included, written in that time; every worktree, when such a transcript cannot be read | pstack `worktree-cleanup.md` step 1: "the newest chat that touched it"; `worktree-audit.sh`: "Match path followed by "/" or a quote so glint-482 does not match glint-482-r37.", and a chat within `-le 4` days is `verify-recent-chat`; that test divides the age by 86400 into whole days, so it holds anything under 5 days, which is the window here (ours: every project folder is read, not only this repository's, since kstack's work runs from other workspaces' sessions, as stack-check's digest found) |
| A worktree with changed or untracked files, or whose HEAD is not on main | code.claude.com/docs/en/worktrees: when "the worktree has work in it", where work is "changed or untracked files", "Claude prompts you to keep or remove the worktree"; pstack `worktree-audit.sh`: `git merge-base --is-ancestor "$head" origin/main` (ours: the local `main`, the trunk here, since `origin/main` lags until a push; build `gate.md`, Merge preparation, works "with local merges in place of PRs") |
| A worktree under `.claude/worktrees/` | code.claude.com/docs/en/claude-directory: "The same age cutoff applies to automatic removal of orphaned worktrees" |
| Anything that cannot be read, and anything not proven above | code.claude.com/docs/en/worktrees: when Claude Code "can't count the worktree's changes … it prompts you rather than removing the worktree automatically" |
| Anything outside `<target>`, and every worktree and branch when `<target>` is not the main worktree's root | your words, e1c6753d L1321: "have it run within that scope … the focus should be around that spot" |
| A branch ahead of its upstream, or with none and not merged into main; it is listed | ours: clorox moves nothing a branch holds, so it lists the commits that live only here; the motive is pstack `pause-safely.md` step 3, "Make the work durable.", whose step goes on to commit, which a cleaning pass does not |
| Processes | pstack `create-verification-skill`: "Never kill by process name; kill what you started." |

## The bin

| Rule | Source |
|---|---|
| It lives at `~/.clorox/<repo>/<time>/`, outside Desktop and Documents | Apple: "When you store your Desktop and Documents folders in iCloud Drive, you can access files from your Mac on all your devices" |
| A worktree in the bin stays locked | git-worktree, lock: "to prevent its administrative files from being pruned automatically" |
| `$C bin` lists it; `$C restore <id>` moves an item back, and a worktree is unlocked | code.claude.com/docs/en/claude-directory, `skills/.trash/`: "The files stay here so you can recover them"; git-worktree, lock: "to prevent its administrative files from being pruned automatically" (restore puts the worktree back at its own path, so git's links to it still hold and `repair` has nothing to mend) |
| Step 2 deletes batches older than 30 days | code.claude.com/docs/en/claude-directory: "The default is 30 days" |

## Not carried from worktree-cleanup

| Part | Why |
|---|---|
| Step 2's pinned set: "Get that set from the user or sidebar and cross-check every candidate." | Dropped: an unattended pass has no person to give it, and `$C restore` brings a binned worktree back |
| `worktree-audit.sh`'s `hold-open-pr` bucket | Dropped: an open PR's branch is not on main, so the merge rule above already keeps its worktree |
