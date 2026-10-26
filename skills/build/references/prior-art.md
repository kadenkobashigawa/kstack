# Prior art

Load this when you check a design against how others solved the same problem.
`references/design.md` and `references/refactor.md` call for it, and the `researcher` agent runs it
with a fresh context, given this file's path in its brief.

Treat the current design as a hypothesis, and look for evidence against it before
evidence for it. The step is pstack's prototype playbook's "Search for prior art" (pstack,
`skills/poteto-mode/playbooks/prototype.md`, l. 8). *(kstack: the playbook gathers references "when
the design space is open" and skips the step "when the direction is set", while this step also runs
on a design already chosen. The method below came from crawl, a kstack skill that crawled the
standing codebase. pstack has no crawler, so the source ranking, the query hygiene, the verdicts and
the confidence line have no pstack source. The source ranking is the project owner's, and it
applies to every claim this step makes.)*

## What counts as a source

In order of weight:

1. **The official documentation and specifications of what the code is built on**: the database,
   the framework, the language, the browser platform, the standard or regulation the code answers
   to.
2. **The code of mature, widely used projects solving the same problem.** Find candidates with
   `gh search code '<generic query>' --limit 20` (add `--language` and `--extension` to narrow),
   then read the matching file in its repository: `gh api repos/<owner>/<repo>/contents/<path>`, or
   the raw file. Judge a repository by its use (adoption, maintainers, release history), not by its
   README. A toy or a tutorial repository is not prior art.
3. **Peer-reviewed papers**, for algorithms and for claims about design.

These can lead you to a source but never stand in for one: blogs, tutorials, Q&A answers, vendor
marketing and AI-written summaries. An unreviewed preprint is a lead, not a number.

## Query hygiene

A query leaves this machine. Describe the problem in general terms: "optimistic concurrency with a
content hash and HTTP 412", "append-only audit table with HMAC rows in PostgreSQL". Never paste this
project's code, identifiers only it uses, file contents, data, or the names of people or customers.

## Per design

Cover the current design and every candidate design, such as the two that `references/design.md`
sketches to design it twice, or a refactor's target shape:

- **What established projects do.** Two or more independent ones when they exist, each with a link
  to the exact file or section.
- **The verdict**, one of:
  - `HOLDS`: the design matches the established pattern, or differs for a reason this project
    actually has.
  - `BETTER EXISTS`: a pattern with a concrete advantage that applies here. Name it, cite its
    sources, and say what it would remove.
  - `OURS IS BETTER`: the common pattern doesn't fit. Name the constraint, such as an
    audit-trail rule the common pattern would break.
- **Confidence:** how many independent sources, and whether they agree.

When nothing comparable exists, say so and list the queries you tried. The verdict is then
`HOLDS`, with "no prior art found" as its reason.

Return the verdicts, then one line listing every query and every source read.
