---
name: maintain-verification-skill
description: Checks a project's verification skill and feature map against the current app. One read-only agent per feature reads the source, one live session drives every feature, and at most one commit fixes the doc drift it proved, while a fix to the harness scripts goes through /build. App bugs are reported, never patched over in the docs. Run it with /maintain-verification-skill.
disable-model-invocation: true
---

# Maintain a verification skill

Ported from pstack's maintain-verification-skill (Lauren Tan, MIT,
`upstream/pstack/skills/maintain-verification-skill/`). kstack changed four things: the path is
Claude Code's `.claude/skills/`, a run ships one commit where pstack opens one PR, a fix to the
harness scripts goes through `/build`, and the source wave names its agent type and caps how many
run at once.

A feature map rots the moment the app changes. This skill is the upkeep loop for a skill generated
by `/create-verification-skill` (or any project-local verification skill with a feature map). The
unit of rigor is the feature, not every sentence: cover every feature file from source and exercise
every feature live, without terminalising every bullet.

## Outcomes

Pick one, and say which:

- **clean** — every feature got source and live coverage, and nothing is worth shipping. No commit.
- **changed** — one commit ships proven doc and map corrections, in the repo that holds the
  verification skill. A fix to the harness scripts is code, so it goes through `/build`, and build's
  gate does the review a PR would get. pstack ships "one PR of proven corrections" (pstack,
  `skills/maintain-verification-skill/SKILL.md`, l. 37) *(kstack, the translation: these projects
  merge locally, so a bare commit gets no review. Doc-only corrections stay one commit, and harness
  code takes build's gate)*.
- **blocked** — coverage could not finish or a proven fix could not ship safely. Say exactly what
  blocked it.

## Edit scope

Only edit the verification skill's own directory (its SKILL.md, features/, and any harness scripts
it owns). Never edit product code during a run: a behavior the map describes that the app no longer
does is either doc drift (fix the map) or a product regression (report it, don't paper over it in
docs).

## Pass

0. **Locate the target.** Find the verification skill to maintain: the project-local skill whose
   body has launch and drive sections and a feature map (usually `.claude/skills/verify-*/` in the
   project). If there are several candidates, ask which one. If there are none, stop and point at
   `/create-verification-skill` instead of inventing a target.

1. **Index hygiene.** Read the feature map README and glob its sibling files. Fix missing, extra,
   duplicate, or dead entries. Keep it light, with no generated inventory.

2. **Source wave.** One read-only subagent per feature file, launched concurrently, at most three at
   a time *(kstack: they share the session's usage limit)*. Each is a `general-purpose` subagent
   told it may not edit, the way pstack's how spawns its readers (pstack, `skills/how/SKILL.md`,
   ll. 26–28). Never use an `Explore` agent, whose Claude Code description says it "locates code; it
   doesn't review or audit it" *(kstack: pstack names no agent type here, and flagging drift is a
   review)*. Each explains "how does this user-facing feature work?" from source, flags likely doc
   drift with citations, and returns one concise live-verification recipe. Children
   never drive the app and never edit files. Return shape: feature summary, source entry points,
   likely drift or none, one recipe.

3. **Reconcile.** Every feature file has a returned summary. Merge overlapping recipes into as few
   app states as practical. Spot-check cited drift, and don't re-prove clean claims. Sweep recent
   churn for user-facing surfaces missing from the map — require a concrete source path before
   calling one missing.

4. **Live pass.** Required even when source looks clean. The coordinator owns all driving. Follow
   the verification skill's own launch model: one long-lived instance driven serially for servers
   and UIs, or a fresh isolated session per drive for short-lived CLIs. The skill's Launch section
   decides, not this one. Exercise every feature at least once, and hold three invariants the whole
   pass, whatever the failure. (1) Never drive an instance you haven't health-checked since it last
   did something surprising. Run doctor before the first drive, on each fresh session where sessions
   are the unit, and again after any failed drive. Where doctor can't see the failure (a wedged UI
   state on a healthy process), reset to a known state or relaunch rather than hoping. (2) Evidence
   captured so far survives every cleanup, checked at its named location, not assumed. (3) Nothing
   a drive started outlives that drive's usefulness. Clean failed-iteration residue whether the
   session is stuck, exited, or shared, and for a shared instance, clean the residue, not the
   instance. A doctor failure caused by skill drift is drift: fix it under edit scope and retry
   once — restart whatever the fix invalidated, nothing more — before calling the pass `blocked`. A
   feature that can't be reached is `verified-unreachable` only with the concrete prerequisite
   (auth, entitlement, OS, external state) and the route attempted. If the map omits that
   prerequisite, that's drift. Any harness fix from triage gets re-driven live before it ships.
   Final teardown happens after the last drive of the run — including those re-proofs — so nothing
   outlives the run. Evidence stays, as the skill says.

5. **Triage.** A wrong or missing user-POV description is doc drift: fix it. Working behavior the
   harness can't drive is a harness gap: fix it. A harness fix follows the same helpers rule as
   generation (scripts executable, invocation documented in the skill body). App behavior that's
   actually broken is a product gap: record it for the user, and keep it out of this commit.

6. **Ship or stop.** For changed, ship one commit of proven doc and map corrections, and re-read
   every changed file first. Send each harness-script fix through `/build`, as Outcomes says. For
   clean or blocked, make no commit, and report the outcome and the coverage honestly.

Keep concise run notes (features covered, unreachable prerequisites, confirmed drift, outcome) in a
scratch location, and don't commit them.
