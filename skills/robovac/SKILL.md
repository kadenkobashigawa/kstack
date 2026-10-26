---
name: robovac
description: One cleanup pass over the current project, or over one file or folder of it. clorox bins leftovers, stack-check suggests edits to the Claude Code setup, and build fixes the worst proven code-rule problem and merges that fix into local main after a clean review. It never pushes or deploys. Use only when the user types /robovac or a /loop runs it, such as /loop 12h /robovac.
argument-hint: "[file or folder]"
---

# robovac

`<target>` and `<run>` are the paths step 2 prints.

## Steps

| # | Step | Who | Source |
|---|---|---|---|
| 1 | `${CLAUDE_SKILL_DIR}/scripts/runs.py say "<what this pass will do, in one plain line>"` | model | "the widget shows only the run's own one line, which the agent sets at the start (`runs.py say`)" (kstack, `apps/robovac-widget/PRODUCT.md`, ll. 70–71) |
| 2 | `<target>` is the file or folder `$ARGUMENTS` names, as an absolute path in this repository or any worktree of it, else the main worktree's root, the parent of `--git-common-dir`. Then `D="$(git rev-parse --path-format=absolute --git-common-dir)/robovac" && mkdir -p "$D" && R="$(mktemp -d "$D/$(date +%Y-%m-%d-%H%M)-XXXXXX")" && echo "$R"`, so two runs started in one minute, from any worktree, get a folder each | model, then script | for `$ARGUMENTS`, "All arguments passed when invoking the skill" (Anthropic, 2026a); *(kstack: a pass can be pointed at one file or folder instead of the whole project)*; "`--git-common-dir` Show `$GIT_COMMON_DIR` if defined, else `$GIT_DIR`." (Git, 2026); "This file name is unique and suitable for use by the application." (Apple, 2026) |
| 3 | The clorox skill, with `<target>` and `<run>` | skill | "Delegate to other skills by path. Don't restate." (pstack, `skills/poteto-mode/playbooks/authoring-a-skill.md`, l. 10); `Skill` "Executes a skill within the main conversation" (Anthropic, 2026b) |
| 4 | The stack-check skill, with `<target>` and `<run>` | skill | as step 3 |
| 5 | The build skill, unattended, with no task handed over: `<target>` is its slice, and `<run>/build.tsv` is its trail. One task per run: the worst item in the project's findings queue that still holds, or, with none, the worst proven broken rule the two reviewers find in the slice, goes to its playbook (build `SKILL.md`, Playbooks), which ends at the gate and the merge, then the run ends. It runs in its own fresh worktree off current main, and removes that worktree when it ends. Its branch goes once merged, and a branch at merge-ready stays. The other findings go in the reply as the queue, left for a later pass. When the task's fix fails, build's `references/when-a-fix-fails.md` decides. Where it stops the work, the run ends and the problem goes in the reply only | skill | build `SKILL.md` sends long or unattended work to `references/long-run.md` (kstack, `skills/build/SKILL.md`, l. 47), whose "When no task is handed over" holds the one-task run (kstack, `skills/build/references/long-run.md`, l. 72); "Address broken skills, related bugs, ... yourself via poteto-mode." (pstack, `skills/poteto-mode/playbooks/autonomous-run.md`, l. 9); "Mid-run discoveries fix only what blocks the frontier. Everything else parks in follow-ups." (pstack, `skills/poteto-mode/playbooks/orchestrate.md`, l. 109); *(kstack: the pass does not cut the workflow into slices, so one run takes the single worst proven fix whole through to its merge)*; *(kstack: a run fixes one task, so the next pass does not re-review everything again)* |
| 6 | Stop the subagents and background shells this run started that still run. Then delete `<run>` with `rm -r`, after reading from it what the reply needs. Then reply with the replies of steps 3 to 5 in order (what clorox moved, stack-check's suggested edits, the gate's verdict and what merged, and the queue), then what this session still has running that this run did not start (agents, background shells, wake-ups other than this loop's) and the work named in it that is neither done, written down nor parked. The reply is the pass's only record | model | as step 3; "Start nothing new, and cancel any nested subagents." (pstack, `skills/poteto-mode/playbooks/pause-safely.md`, l. 5); "Never kill by process name; kill what you started." (pstack, `skills/create-verification-skill/SKILL.md`, l. 31); *(kstack: a pass that names work still open in the session either claims it or parks it, so nothing it lists is dropped)*; *(kstack: a pass starts and ends cleanly and leaves no markdown ledger to grow across runs)* |

## Rules

| Rule | Source |
|---|---|
| Each step works on `<target>` and reads outside it only to check what `<target>` touches | *(kstack: a pass reads outside its target only to check what the target touches, so the review stays on the named spot)* |
| Steps 3 to 5 run cheapest first: a script, then part script and part agents, then agents | *(kstack: steps run cheapest first, deterministic before agents, for token efficiency)* |
| Every run takes steps 1 to 6 whole. Nothing is skipped as clean | *(kstack: a pass is one deterministic sweep that never skips a step on a guess that the project is clean)* |
| On a schedule, it runs as `/loop <interval> /robovac [target]`, such as `/loop 12h /robovac`, and re-arms nothing itself | "the root arms `/loop 1h` with a prompt that runs this tick … Never leave the cadence to memory" (pstack, `skills/poteto-mode/playbooks/autopilot-stack.md`, l. 6); "When you supply an interval, Claude converts it to a cron expression, schedules the job" (Anthropic, 2026c); *(kstack: a pass can run for more than an hour, so the interval is the user's to set and the pass never re-arms itself)* |
| A clean gate verdict merges the pass's fix into the project's local main without asking. Pushing stays separate: the pass never pushes or deploys | "The operator's full-autonomy grant plus the root's clean verdict is the merge authorization that babysitting alone never has." (pstack, `skills/poteto-mode/playbooks/autopilot-full.md`, l. 9); *(kstack: the clean gate verdict is the merge authorization, so the pass merges without asking, and pushing stays a separate act)* |
| A pass leaves nothing on disk but clorox's bin: what you need goes in its final reply, and it deletes its run folder at the end | *(kstack: a pass starts and ends cleanly, so no markdown ledger grows across runs)* |
| This skill stays model-invocable | for `disable-model-invocation`, "Also prevents the skill … from running when a scheduled task fires with the skill as its prompt" (Anthropic, 2026a) |

## References

- Anthropic (2026a). Extend Claude with skills. https://code.claude.com/docs/en/skills
- Anthropic (2026b). Tools reference. https://code.claude.com/docs/en/tools-reference
- Anthropic (2026c). Run prompts on a schedule. https://code.claude.com/docs/en/scheduled-tasks
- Apple (2026). mktemp(1), macOS manual page (`man mktemp`).
- Git (2026). git-rev-parse Documentation. https://git-scm.com/docs/git-rev-parse
