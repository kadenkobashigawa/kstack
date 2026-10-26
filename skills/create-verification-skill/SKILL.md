---
name: create-verification-skill
description: Generates a project-local verification skill in .claude/skills that launches the project's app, drives it the way a user does and captures evidence, for any language or platform. Seeds a feature map and runs the new skill once end to end before handing it over. Run it with /create-verification-skill when a project has no scripted way to prove UI, CLI or service behavior.
disable-model-invocation: true
---

# Create a verification skill

Ported from pstack's create-verification-skill (Lauren Tan, MIT,
`upstream/pstack/skills/create-verification-skill/`). kstack changed three things: the paths are
Claude Code's `.claude/skills/`, section 2 gives Claude Code's reason for the frontmatter, and
section 2 adds the Data item. The example feature map in `references/feature-map-example/` is
pstack's, unchanged. `references/evidence.md` holds the external sources.

Every serious project needs a scripted way to drive the real app and prove behavior: launch it,
exercise a feature the way a user would, and capture evidence. This skill generates that as a
project-local skill (`.claude/skills/verify-<app>/`) tailored to the repo. You write the generator's
output for the next agent, not for a human: it will be read cold, mid-task, by an agent that has
never seen the app.

## 1. Interview the repo, not the user

Answer these from the codebase and only ask the user what you cannot observe:

- **Surface:** what does a user actually touch? A web UI, a CLI or TUI, a desktop app, an API, a
  mobile app, a library? A repo can have several. Pick the primary one and note the rest.
- **Run:** how does the app start locally? Prefer the repo's own documented dev command (package
  scripts, Makefile, README quickstart). Note ports, env vars, seed data, auth.
- **Drive:** how can an agent interact with it programmatically? Existing harnesses first —
  Playwright or Cypress specs, expect scripts, PTY helpers, curl-able endpoints, a debug port. Only
  then pick a generic recipe: a browser driven over CDP for web and Electron, a tmux or PTY harness
  for a CLI or TUI, plain HTTP for services.
- **Observe:** what evidence can be captured? Screenshots, terminal transcripts, response bodies,
  logs, exit codes, DB state.
- **Isolate:** can two instances run side by side (ports, data dirs, profiles)? If not, say so in
  the generated skill: refusing to double-drive a shared instance beats corrupting the user's
  session.

If the checkout doesn't build or start as-is, fix that first (or report it precisely) before
generating. A skill written against a broken base teaches wrong steps. When an irrelevant missing
asset blocks startup (a static dir the API never serves, a sample config), the generated skill may
create it, clearly marked as verification scaffolding, and remove it in cleanup.

## 2. Generate the skill

Write `.claude/skills/verify-<app>/SKILL.md`. Its YAML frontmatter holds `name: verify-<app>` and a
`description` that names the app, the surface, and when to reach for it. Claude "uses this to
decide when to apply the skill", and without a description it "uses the first non-empty line of the
markdown content" (Anthropic, 2026) *(kstack, the translation: pstack's reason, that without
frontmatter the skill never registers, was written for Cursor, and Claude Code says "All fields are
optional" (Anthropic, 2026))*. Below the frontmatter come these sections, each grounded in what the
interview actually found (no placeholders left):

- **Launch:** the exact command that starts the app for verification, and how to tell it's ready (a
  log line, a port answering, a prompt). Include teardown. For a short-lived CLI or TUI there is no
  server to keep alive: launch means build the binary (or install deps) once, then start each drive
  in its own isolated PTY or tmux session.
- **Doctor:** one read-only check that answers "is this instance worth driving?" — process up, the
  right version and build, port held by this run, auth valid. An agent runs this first whenever
  anything looks off.
- **Drive:** the harness recipe with real selectors and commands from this repo, not examples.
  Prefer stable handles (ARIA labels, data attributes, prompt strings, route paths) over coordinates
  and tab order.
- **Evidence:** what to capture for a proof and where it goes. State the proof standards. Exercise
  the real user path, not internal setters or test-only endpoints. Capture the action and the
  resulting state, not just the final screen. Verify side effects (files written, rows inserted,
  messages sent) alongside what's visible. Use mocks only where a production boundary already
  isolates the external system. When the safe path is a dry-run or test mode, verify what it
  actually skips by observing (files, network, git refs) rather than trusting its name: some
  dry-runs still touch the network or open a browser.
- **Cleanup:** how to tear down instances the run created. Never kill by process name; kill what you
  started. Cleanup removes instances and scratch state, never the evidence: proof artifacts survive
  the teardown, in a location the skill names.
- **Helpers:** any script the skill ships is executable and its invocation is shown in the skill
  body. A helper the reader has to reverse-engineer is not a helper.
- **Data:** which data a run starts from, named per claim and held fixed across a baseline and its
  treatment. "Use the same environment inputs for baseline and patched builds." (pstack,
  `automations/benny/skills/reproduce-and-fix-issues/references/control-adapter.md`, l. 133)
  Default to a snapshot of the developer's own dev data. Use made-up fixtures where no dev data
  holds the precondition. Never use production or a copy of it *(kstack: production rows belong to
  the people in them)*. Evidence from real data stays on disk only with the user's agreement
  (cursor-team-kit, `skills/verify-this/SKILL.md`, l. 51) *(kstack: pstack's generator names no
  data, and a baseline compared with a treatment on different data proves nothing)*.

## 3. Seed the feature map

Create `.claude/skills/verify-<app>/features/README.md` plus one file per user-facing feature you
can identify (aim for the top 3-5 to start, from routes, commands, menus, or docs). Follow the shape
in [`references/feature-map-example/`](references/feature-map-example/), with a README index and one
file per feature. Each file answers, from the user's point of view: what the feature is, how to
reach it, how to drive it with the harness, and what observable end state proves it works. The four
H2s are `Sub-features`, `How to get to it (user POV)`, `Driving it with <harness>`, and `Gotchas`.
The map is the repo's maintained verification source. A proof that drives one convenient entry point
is incomplete when the map lists others.

## 4. Prove the generated skill before handing it over

Run its own instructions end to end once: launch, doctor, drive **one** mapped feature (one is
enough, since the map exists so later runs can cover the rest), capture evidence, clean up. After
cleanup, confirm the evidence still exists at the named location — a cleanup that eats the proof
fails this step. Fix what fails, and run the generated cleanup after every failed iteration too, so
broken attempts don't strand processes and ports. A generated skill that was never executed is a
draft, not a deliverable.

## 5. Offer the maintenance loop

Point the user at `/maintain-verification-skill` for keeping the map honest as the app changes.
Suggest a cadence only if they ask.
