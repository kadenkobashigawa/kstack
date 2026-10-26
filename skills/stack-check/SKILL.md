---
name: stack-check
description: Reviews the Claude Code setup as one system (skills, agents, hooks, CLAUDE.md files and memory) against the last 7 days of sessions that worked in this repository, from any workspace, using three reviewer agents and a synthesizer, and replies with suggested edits it never applies. Use only as robovac's setup-review step, which supplies the run folder.
---

# stack-check

`S=${CLAUDE_SKILL_DIR}/scripts/stack.py` · `R=$(cd "${CLAUDE_SKILL_DIR}" && pwd -P)/../../upstream/pstack/skills/reflect`
· `<run>` is the folder robovac names.

## Steps

| # | Step | Who | Source |
|---|---|---|---|
| 1 | `$S freeze <run>/frozen`, then `$S check > <run>/check.md`, then `$S digest --project "${CLAUDE_PROJECT_DIR}" --out <run>/digest.md` | script | "A deterministic lever beats fan-out." (pstack, `skills/principle-build-the-lever/SKILL.md`, l. 16); "write a tight digest of the session and pass that instead" (pstack, `skills/reflect/SKILL.md`, l. 27); "default the last 7 days" (pstack, `skills/recall/SKILL.md`, l. 18); *(kstack: the setup is frozen as it stood when the pass began, and the current session counts, since a pass often runs right after work ends)*; for `${CLAUDE_PROJECT_DIR}`, "The project root directory. This is the same path hooks and MCP servers receive" (Anthropic, 2026a); "Do not glob across `~/.cursor/projects/*/`. That crosses workspace boundaries and reads private chats from unrelated projects." (pstack, `skills/reflect/SKILL.md`, l. 19). The digest departs from that *(kstack: sessions are picked by launch folder, not by what they worked on, and kstack's work runs from other projects' sessions, so other workspaces' logs are read and only the lines whose working folder lies in this repository's worktrees are kept, which keeps unrelated chats out)* |
| 2 | One message, three `Agent` calls, `general-purpose`: judgment on `opus`, tooling on `sonnet`, divergent on `opus`. Each gets `$R/references/<lens>-reviewer.md` verbatim, with the substitutions below, `<run>/digest.md` as the digest, and this line: "Read the files a finding names from the frozen copy at `<run>/frozen`, under each file's absolute path." With a `<target>`, add: "Weigh the work on `<target>` first." | model | "One message, three `Task` calls" (pstack, `skills/reflect/SKILL.md`, l. 31); "Pass each template verbatim, substituting the transcript path or digest where marked" (pstack, `skills/reflect/SKILL.md`, l. 41); *(kstack: reflect's workflow is adapted to Claude Code, the only runtime kstack targets)*. The models are kstack's: reflect's tooling default is `grok-4.7-xhigh-fast` (pstack, `skills/reflect/SKILL.md`, l. 38), another family, and Claude Code runs only Claude models, so tooling runs on a different Claude model, weaker diversity, as build `gate.md` names it for its review lanes. The two added lines are kstack's: the frozen copy, so a finding is read as the setup stood when step 1 froze it *(kstack: reviewers judge the setup as the pass began, not as it changes mid-run)*; and the target *(kstack: a pass pointed at one spot weighs that spot first)* |
| 3 | One `Agent` call, `general-purpose`, on `opus`: `$R/references/synthesizer.md` verbatim, with each reviewer's full output inlined | model | "with each reviewer's full output inlined where marked" (pstack, `skills/reflect/SKILL.md`, l. 45) |
| 4 | Move each Accepted row that a lint rule, script, metadata flag or runtime check could enforce to Backlog | model | "For any item that would be enforced more reliably by a lint rule, script, metadata flag, or runtime check, move it from Accepted to Backlog." (pstack, `skills/reflect/SKILL.md`, l. 49) |
| 5 | Apply nothing. The suggested edits stay in the reply, and no file keeps them | model | "Skill changes affect every future agent in the org. Do not auto-apply." (pstack, `skills/reflect/SKILL.md`, l. 53); *(kstack: nothing is applied and no ledger file grows across passes)*. Not carried: "Backlog items file to whatever devex / backlog tracker your team uses automatically." (pstack, `skills/reflect/SKILL.md`, l. 55), since no tracker is wired here; the Backlog goes in the reply, which robovac carries into the pass's reply |
| 6 | Reply with `<run>/check.md`'s lines, then one line per Accepted and Backlog item, one per Dropped finding with the synthesizer's reason, then "applied: none" | model | "Short list, no preamble" (pstack, `skills/reflect/SKILL.md`, l. 68), with a line per edit, backlog item and dropped finding *(kstack: "applied: none" in place of its edits applied, since step 5 applies nothing)* |

## Substitutions in reflect's templates

| reflect says | Write | Source |
|---|---|---|
| `Task` | `Agent` | `Agent` "Spawns a subagent with its own context window" (Anthropic, 2026b) |
| `Shell` | `Bash` | `Bash` "Executes shell commands in your environment" (Anthropic, 2026b) |
| `Read` tool calls against any `SKILL.md` file | `Skill` tool calls, and `Read` tool calls against any `SKILL.md` file | `Skill` "Executes a skill within the main conversation" (Anthropic, 2026b) |
| `.cursor/skills/`, `~/.cursor/skills/`, `~/.cursor/plugins/` | `.claude/skills/`, `~/.claude/skills/`, `~/.claude/plugins/` | (Anthropic, 2026a) |
| `create-skill` | `skill-creator` | skill-creator "runs a blind A/B between two versions of the skill" and "Description tuning" (Anthropic, 2026a) |

## References

- Anthropic (2026a). Extend Claude with skills. https://code.claude.com/docs/en/skills
- Anthropic (2026b). Tools reference. https://code.claude.com/docs/en/tools-reference
