---
name: robovac
description: One cleaning pass, every run, over the project the session is in, or over one file or folder of it. clorox bins its leftovers, stack-check reviews the Claude Code setup and the recent sessions, and build fixes its code against the code rules. Use only when the user types /robovac or a /loop runs it.
argument-hint: "[file or folder]"
---

# robovac

`<target>` and `<run>` are the paths step 2 prints.

## Steps

| # | Step | Who | Source |
|---|---|---|---|
| 1 | `${CLAUDE_SKILL_DIR}/scripts/runs.py say "<what this pass will do, in one plain line>"` | model | kstack `apps/robovac-widget/PRODUCT.md`, Positioning: "the widget shows only the run's own one line, which the agent sets at the start (`runs.py say`)" |
| 2 | `<target>` is the file or folder `$ARGUMENTS` names, as an absolute path in this repository or any worktree of it, else the main worktree's root, the parent of `--git-common-dir`. Then `D="$(git rev-parse --path-format=absolute --git-common-dir)/robovac" && mkdir -p "$D" && R="$(mktemp -d "$D/$(date +%Y-%m-%d-%H%M)-XXXXXX")" && echo "$R"`, so two runs started in one minute, from any worktree, get a folder each | model, then script | code.claude.com/docs/en/skills, `$ARGUMENTS`: "All arguments passed when invoking the skill"; your words, e1c6753d L1321: "we should be able to point the skill at a at a folder or a file or just a whole thing"; git-rev-parse: "`--git-common-dir` Show `$GIT_COMMON_DIR` if defined, else `$GIT_DIR`."; mktemp(1): "This file name is unique and suitable for use by the application." |
| 3 | The clorox skill, with `<target>` and `<run>` | skill | pstack `authoring-a-skill.md`: "Delegate to other skills by path. Don't restate."; code.claude.com/docs/en/tools-reference: `Skill` "Executes a skill within the main conversation" |
| 4 | The stack-check skill, with `<target>` and `<run>` | skill | as step 3 |
| 5 | The build skill, unattended, with no task handed over: `<target>` is its slice, and `<run>/build.tsv` is its trail. One task per run: the two reviewers grade the slice, the root sorts, and the worst proven broken rule is built through build's checks, the gate and the merge, then the run ends. It runs in its own fresh worktree off current main, and removes that worktree when it ends; its branch goes once merged, and a branch at merge-ready stays. The other findings are not recorded. A task that fails twice stops the run, and the problem goes in the reply only | skill | build `SKILL.md`: "runs unattended, under `/loop` or while the user is away → `references/long-run.md`", whose "When no task is handed over" holds the one-task run; your words, f057a2d7 L2769: "we have to design it in a way that doesnt forcefully cut the workflow into slices"; your words, 2026-10-17: "the next rollback call, it's gonna go and review everything. Again" |
| 6 | Stop the subagents and background shells this run started that still run. Then delete `<run>` with `rm -r`, after reading from it what the reply needs. Then reply with the replies of steps 3 to 5 in order (what clorox moved, stack-check's suggested edits, what merged), then what this session still has running that this run did not start (agents, background shells, wake-ups other than this loop's) and the work named in it that is neither done, written down nor parked. The reply is the pass's only record | model | as step 3; pstack `pause-safely.md` step 1: "Start nothing new, and cancel any nested subagents."; pstack `create-verification-skill`: "Never kill by process name; kill what you started."; your words, in memory `feedback_own_the_work_you_list`: "when you list things to do, have some intention of doing them"; your words, 2026-10-17: "I want it to start and then end cleanly ... I don't want any markdown ledgers to just grow until infinity" |

## Rules

| Rule | Source |
|---|---|
| Each step works on `<target>` and reads outside it only to check what `<target>` touches | your words, e1c6753d L1321: "you can look outside to see if, you know, there are any discrepancies between files … but the the focus should be around that spot" |
| Steps 3 to 5 run cheapest first: a script, then half script, then agents | your words, a73b674f L16327: "make sure to effectively split deterministic from non for token efficiency" |
| Every run takes steps 1 to 6 whole; nothing is skipped as clean | your words, a73b674f L16271: "a robovac doesnt micromanage where if vaccumed or not it just does one deterministic pass" |
| On a schedule, it runs as `/loop <interval> /robovac [target]`, such as `/loop 12h /robovac`, and re-arms nothing itself | pstack `autopilot-stack.md` step 2: "the root arms `/loop 1h` with a prompt that runs this tick … Never leave the cadence to memory"; code.claude.com/docs/en/scheduled-tasks: "When you supply an interval, Claude converts it to a cron expression, schedules the job"; your words after the first kstack run's pass took 83 minutes, relayed into e1c6753d by the session that analysed it: "its ok we can just extend the interval to twice a day or once a day if needed", and your go-ahead in e1c6753d: "ok go ahead with all of it" |
| A clean gate verdict merges the pass's fix into the project's local main without asking. Pushing stays separate: the pass never pushes or deploys | pstack `autopilot-full` step 5: "The operator's full-autonomy grant plus the root's clean verdict is the merge authorization that babysitting alone never has."; your words, 2026-10-17: "the pipeline doesn't really need my say to merge, right? It's designed so that it merges through the verification" |
| A pass leaves nothing on disk but clorox's bin: what you need goes in its final reply, and it deletes its run folder at the end | your words, 2026-10-17: "I want it to start and then end cleanly ... I don't want any markdown ledgers to just grow until infinity" |
| This skill stays model-invocable | code.claude.com/docs/en/skills, `disable-model-invocation`: "Also prevents the skill … from running when a scheduled task fires with the skill as its prompt" |
