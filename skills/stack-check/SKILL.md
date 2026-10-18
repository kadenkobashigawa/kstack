---
name: stack-check
description: Reviews the Claude Code setup as one system (skills, agents, hooks, instruction files and memory) by running pstack's reflect over the last 7 days of sessions that worked in this repository, from any workspace, the current one included, and replies with suggested edits it never applies. Run by robovac.
---

# stack-check

`S=${CLAUDE_SKILL_DIR}/scripts/stack.py` · `R=$(cd "${CLAUDE_SKILL_DIR}" && pwd -P)/../../upstream/pstack/skills/reflect`
· `<run>` is the folder robovac names.

## Steps

| # | Step | Who | Source |
|---|---|---|---|
| 1 | `$S freeze <run>/frozen`, then `$S check > <run>/check.md`, then `$S digest --project "${CLAUDE_PROJECT_DIR}" --out <run>/digest.md` | script | pstack `principle-build-the-lever`: "A deterministic lever beats fan-out."; reflect step 1: "write a tight digest of the session and pass that instead"; pstack `recall`: "default the last 7 days"; your words, f057a2d7 L2228: "it makes a snapshot ig a worktree of whatever you want it to audit"; your words, e1c6753d L1217, on the current session: "I just finished and call RoboVac just to clean up"; code.claude.com/docs/en/skills, `${CLAUDE_PROJECT_DIR}`: "The project root directory. This is the same path hooks and MCP servers receive"; reflect step 1: "Do not glob across ~/.cursor/projects/*/. That crosses workspace boundaries and reads private chats from unrelated projects." The digest departs from that (ours): kstack's work runs from other projects' sessions (the first kstack run's stack-check, backlog A: "Sessions are picked by launch folder, not by what they worked on"), so other workspaces' logs are read and only the lines whose working folder lies in this repository's worktrees are kept, which keeps unrelated chats out |
| 2 | One message, three `Agent` calls, `general-purpose`: judgment on `opus`, tooling on `sonnet`, divergent on `opus`. Each gets `$R/references/<lens>-reviewer.md` verbatim, with the substitutions below, `<run>/digest.md` as the digest, and this line: "Read the files a finding names from the frozen copy at `<run>/frozen`, under each file's absolute path." With a `<target>`, add: "Weigh the work on `<target>` first." | model | reflect step 2: "One message, three `Task` calls"; "Pass each template verbatim, substituting the transcript path or digest where marked"; your words, f057a2d7 L560: "adopt the best workflow tuned towards our only Claude workflow". The models are ours: reflect's tooling default is `grok-4.7-xhigh-fast`, another family, and Claude Code runs only Claude models, so tooling runs on a different Claude model, weaker diversity, as build `gate.md` names it for its review lanes. The two added lines are ours: the frozen copy, so a finding is read as the setup stood when step 1 froze it (your words, f057a2d7 L2228: "it makes a snapshot ig a worktree of whatever you want it to audit"); and the target, your words, e1c6753d L1321: "the focus should be around that spot" |
| 3 | One `Agent` call, `general-purpose`, on `opus`: `$R/references/synthesizer.md` verbatim, with each reviewer's full output inlined | model | reflect step 3: "with each reviewer's full output inlined where marked" |
| 4 | Move each Accepted row that a lint rule, script, metadata flag or runtime check could enforce to Backlog | model | reflect step 4: "For any item that would be enforced more reliably by a lint rule, script, metadata flag, or runtime check, move it from Accepted to Backlog." |
| 5 | Apply nothing. The suggested edits stay in the reply, and no file keeps them | model | reflect step 5: "Skill changes affect every future agent in the org. Do not auto-apply."; your words, f057a2d7 L2729: "never auto apply"; your words, 2026-10-17: "I want it to start and then end cleanly ... I don't want any markdown ledgers to just grow until infinity". Not carried: reflect step 5's "Backlog items file to whatever devex / backlog tracker your team uses automatically.", since no tracker is wired here; the Backlog goes in the reply, which robovac carries into the pass's reply |
| 6 | Reply with `<run>/check.md`'s lines, then one line per Accepted and Backlog item, one per Dropped finding with the synthesizer's reason, then "applied: none" | model | reflect step 6, "Summarize for the user": "Short list, no preamble", with a line per edit, backlog item and dropped finding (ours: "applied: none" in place of its edits applied, since step 5 applies nothing) |

## Substitutions in reflect's templates

| reflect says | Write | Source |
|---|---|---|
| `Task` | `Agent` | code.claude.com/docs/en/tools-reference: `Agent` "Spawns a subagent with its own context window" |
| `Shell` | `Bash` | code.claude.com/docs/en/tools-reference: `Bash` "Executes shell commands in your environment" |
| `Read` tool calls against any `SKILL.md` file | `Skill` tool calls, and `Read` tool calls against any `SKILL.md` file | code.claude.com/docs/en/tools-reference: `Skill` "Executes a skill within the main conversation" |
| `.cursor/skills/`, `~/.cursor/skills/`, `~/.cursor/plugins/` | `.claude/skills/`, `~/.claude/skills/`, `~/.claude/plugins/` | code.claude.com/docs/en/skills |
| `create-skill` | `skill-creator` | code.claude.com/docs/en/skills: skill-creator "runs a blind A/B between two versions of the skill" and "Description tuning" |
