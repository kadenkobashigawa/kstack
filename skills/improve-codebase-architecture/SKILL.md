---
name: improve-codebase-architecture
description: Finds shallow modules worth deepening, weighting recently changed code, draws each as a before-and-after card in an HTML report, then interviews the user about the one they pick, one AskUserQuestion round at a time. Never changes code. It writes only the glossary and decision-record entries the interview settles. Run it with /improve-codebase-architecture, optionally naming a module or pain point.
disable-model-invocation: true
argument-hint: "[a module, subsystem, pain point or spec to aim at]"
---

# Improve Codebase Architecture

Surface architectural friction and propose **deepening opportunities**: refactors that turn shallow modules into deep ones. The aim is testability and AI-navigability.

Ported from Matt Pocock's improve-codebase-architecture skill (MIT), kept unmodified under `upstream/mattpocock-skills/` with the three skills it calls and their docs pages. Upstream's text is kept as written, except for links that now point to the files under `references/`, and each departure is marked *(kstack)*. The run never changes code: its output is a conversation, one HTML file in the OS temp directory, and the glossary and decision-record edits the grilling settles.

This command is _informed_ by the project's domain model and built on a shared design vocabulary:

- Read [references/codebase-design.md](references/codebase-design.md) for the architecture vocabulary (**module**, **interface**, **depth**, **seam**, **adapter**, **leverage**, **locality**) and its principles (the deletion test, "the interface is the test surface", "one adapter = hypothetical seam, two = real"). Use these terms exactly in every suggestion, and don't drift into "component," "service," "API," or "boundary."
- The domain language in `GLOSSARY.md` gives names to good seams; ADRs in `docs/adr/` record decisions this command should not re-litigate.

*(kstack)* Upstream calls codebase-design, grilling and domain-modeling as skills through the Skill tool. Its own docs record that "A skill that names another skill does not reliably cause that skill to load" (mattpocock-skills, `docs/productivity/grilling.md`, l. 73). So here the three are reference files this skill reads. And where the project's instruction files (CLAUDE.md, AGENTS.md) name another home for its decision records, that home stands in for `docs/adr/` throughout ([references/adr-format.md](references/adr-format.md)).

## Process

### 1. Explore

**Scope before you scan: YAGNI.** Deepening a module pays off by making future changes to it easier, so put extra weight on the parts of the codebase that have recently changed. Decide *where* to look before you look:

- If the user named a direction (a module, a subsystem, a pain point), take it, and skip the inference below.
- Otherwise, walk back a good stretch of the commit history (`git log --oneline`) to find the codebase's hot spots, the files and areas that keep coming up, and let those paths pull your attention first. If the changes are scattered with no clear hot spot, widen the net.

Read the project's domain glossary (`GLOSSARY.md`) and any ADRs in the area you're touching first.

Then spawn a `general-purpose` sub-agent to walk the codebase *(kstack: Claude Code's Explore agent locates code and does not review it)*. Don't follow rigid heuristics; explore organically and note where you experience friction:

- Where does understanding one concept require bouncing between many small modules?
- Where are modules **shallow**, with an interface nearly as complex as the implementation?
- Where have pure functions been extracted just for testability, but the real bugs hide in how they're called (no **locality**)?
- Where do tightly-coupled modules leak across their seams?
- Which parts of the codebase are untested, or hard to test through their current interface?

Apply the **deletion test** to anything you suspect is shallow: would deleting it concentrate complexity, or just move it? A "yes, concentrates" is the signal you want.

### 2. Present candidates as an HTML report

Write a self-contained HTML file to the OS temp directory so nothing lands in the repo. Resolve the temp dir from `$TMPDIR`, falling back to `/tmp` (or `%TEMP%` on Windows), and write to `<tmpdir>/architecture-review-<timestamp>.html` so each run gets a fresh file. Open it for the user (`xdg-open <path>` on Linux, `open <path>` on macOS, `start <path>` on Windows) and tell them the absolute path.

The report uses **Tailwind via CDN** for layout and styling, and **Mermaid via CDN** for diagrams where a graph/flow/sequence reliably communicates the structure. Mix Mermaid with hand-crafted CSS/SVG visuals: use Mermaid when relationships are graph-shaped (call graphs, dependencies, sequences), and hand-built divs/SVG when you want something more editorial (mass diagrams, cross-sections, collapse animations). Each candidate gets a **before/after visualisation**. Be visual.

For each candidate, render a card with:

- **Files**: which files/modules are involved
- **Problem**: why the current architecture is causing friction
- **Solution**: plain English description of what would change
- **Benefits**: explained in terms of locality and leverage, and how tests would improve
- **Before / After diagram**: side-by-side, custom-drawn, illustrating the shallowness and the deepening
- **Recommendation strength**: one of `Strong`, `Worth exploring`, `Speculative`, rendered as a badge

End the report with a **Top recommendation** section: which candidate you'd tackle first and why.

**Use GLOSSARY.md vocabulary for the domain, and the [references/codebase-design.md](references/codebase-design.md) vocabulary for the architecture.** If `GLOSSARY.md` defines "Order," talk about "the Order intake module," not "the FooBarHandler," and not "the Order service."

**ADR conflicts**: if a candidate contradicts an existing ADR, only surface it when the friction is real enough to warrant revisiting the ADR. Mark it clearly in the card (e.g. a warning callout: _"contradicts ADR-0007, but worth reopening because…"_). Don't list every theoretical refactor an ADR forbids.

See [references/html-report.md](references/html-report.md) for the full HTML scaffold, diagram patterns, and styling guidance.

Do NOT propose interfaces yet. After the file is written, ask the user: "Which of these would you like to explore?"

*(kstack)* Ask it through AskUserQuestion, as one question with the header `Explore`. Offer the strongest candidates as options, at most four, with the top recommendation first and "(Recommended)" after its label. Each option's description is that card's problem in one sentence. The user names any other card, or none, through "Other". The tool needs at least two options. So a report with one card offers that card and "Stop at the report", and a report with no cards ends the run without asking. If the user asked for the report only, stop here instead of asking. Upstream's docs page gives "don't grill me, just show the report" as the way to ask for that. It also calls being grilled instead of shown options the skill's most common complaint (mattpocock-skills, `docs/engineering/improve-codebase-architecture.md`, l. 62).

### 3. Grilling loop

Once the user picks a candidate, run the interview in [references/grilling.md](references/grilling.md) to walk the decision tree with them: constraints, dependencies, the shape of the deepened module, what sits behind the seam, what tests survive.

*(kstack)* Every round goes through AskUserQuestion, as that file maps it. Upstream asks in chat text and turns the question tool down for two reasons. The first is harness neutrality (mattpocock-skills, `.out-of-scope/native-question-tool.md`, l. 7), which doesn't apply to kstack, since kstack runs only in Claude Code. The second is that pickers push toward pre-baked answers (l. 9), and grilling.md answers it by keeping open questions open. Upstream's own way back to the tool is a `CLAUDE.md` line asking for it (l. 11), and kstack makes that line the default.

Side effects happen inline as decisions crystallize; follow [references/domain-modeling.md](references/domain-modeling.md) to keep the domain model current as you go:

- **Naming a deepened module after a concept not in `GLOSSARY.md`?** Add the term to `GLOSSARY.md`. Create the file lazily if it doesn't exist.
- **Sharpening a fuzzy term during the conversation?** Update `GLOSSARY.md` right there.
- **User rejects the candidate with a load-bearing reason?** Offer an ADR, framed as: _"Want me to record this as an ADR so future architecture reviews don't re-suggest it?"_ Only offer when the reason would actually be needed by a future explorer to avoid re-suggesting the same thing; skip ephemeral reasons ("not worth it right now") and self-evident ones. *(kstack: the offer is an AskUserQuestion question too.)*
- **Want to explore alternative interfaces for the deepened module?** Use the design-it-twice parallel sub-agent pattern in [references/design-it-twice.md](references/design-it-twice.md).

*(kstack)* The grilling ends in a decision, not a diff. The change that carries it out is a `/build` task, which takes the decision rather than the report. Build routes it to its refactor playbook (`references/refactor.md`) when the deepening keeps what the code does, and to its feature playbook (`references/feature.md`) when it changes it. Upstream hands the decision to its to-spec, to-tickets and implement skills (mattpocock-skills, `docs/engineering/improve-codebase-architecture.md`, l. 56), which kstack does not carry.
