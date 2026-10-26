---
name: write-report
description: "Writes a report or manual in Markdown and renders it to a numbered US Letter PDF and a matching web page, with a title page, a contents page with real page numbers, appendices and a glossary. Use when asked to \"write a report\", \"make a manual\" or \"turn these notes into a PDF\", or for another report or manual delivered as a PDF. Not for an invoice, a letter or a CV, and not for a README, docstrings or docs kept as Markdown in a repository."
---

# write-report

A report is one Markdown file, or several joined by `!include`. One command reads it, numbers it,
and prints it with headless Chrome until the contents page numbers match the body. The look is
fixed: US Letter, 0.75in margins, 10pt Times justified, numbered sections, title-case headings, a
right-aligned title page, and on screen a dark navigation panel. The look and the reasons for
each value are in `references/design.md`, and the research behind them in
`references/layout-research.md`.

Set `R=$(cd "${CLAUDE_SKILL_DIR}" && pwd -P)` first. The renderer is
`python3 "$R/scripts/report.py"`.

## Steps

1. **Preflight.** Run `python3 "$R/scripts/report.py" --check`. It needs Google Chrome or Chromium
   (or `$CHROME` set to one) and `pdftotext` from poppler. A missing tool stops the run with its
   install command. The skill bundles no fonts, so on a machine without Times, Chrome falls back to
   TeX Gyre Termes, Liberation Serif or any serif, and the page count can differ from a Mac's
   *(kstack: no font ships with the skill, so its licence and size stay out of a public repo)*.
2. **Read the subject.** Read the code, records and notes the report is about. Name the reader in
   one sentence, and what they will do with the report.
3. **Outline.** Write the `#` chapters in the order the reader needs them, never in the order the
   work happened. Put known problems in one chapter of their own, sources in `# References`,
   supporting research in `# Appendix: <title>` parts, and terms in `# Glossary`.
4. **Write** the report, by default at `docs/reports/<name>.md`, in the format of
   `references/format.md`. The title, author, release and date go in its front matter, written for
   this report, and nothing is configured per project. A long report can be split into files
   joined with `!include`, and the numbering is the same either way. Write headings in sentence
   case.
   - **Converting existing docs:** never paste. For each claim in the old text, find the code, the
     test or the named commit that proves it now. Correct a claim that fails, drop one nothing
     proves, and name the commit you checked against in the report's introduction *(kstack: an old
     document's claims are as stale as the code has moved since)*.
5. **Prose pass.** Read `$R/../technical-writing/SKILL.md` and `$R/../unslop/SKILL.md` by path and
   apply both to every file of the report. *(kstack: both are typed-only skills, so this step
   reads them rather than invoking them.)* Headings stay in sentence case in the source, as
   technical-writing says (technical-writing, `SKILL.md`, l. 61); the renderer title-cases them
   *(kstack: the fixed look sets title case, and casing at render time keeps the source under
   technical-writing's rule and the output under the look's)*.
6. **Wordmark, if the project has a logo.** This is the only per-project input, and the default is
   none. Run `python3 "$R/scripts/wordmark.py" <logo.svg> <beside-the-report>/wordmark.svg`, then
   add `wordmark: wordmark.svg` to the front matter. It merges the logo's shapes into one path so
   abutting pieces print without hairline seams, and keeps the holes in letters such as O and A.
   It refuses text, basic shapes, strokes, arcs and CSS classes by name, and reads a stroke or fill
   set on a group as set on each path inside it. Convert those to filled paths in the logo's
   editor first, and export with presentation attributes rather than CSS.
7. **Render.** Run `python3 "$R/scripts/report.py" <report.md>`. It writes `<report>.pdf` and
   `<report>.html` beside the file (`--out <path-without-extension>` puts them elsewhere) and
   prints the page count. Each error names the file and line; fix it and rerun.
8. **Look.** Open the PDF's title page, contents and one chapter page, and with a wordmark look at
   the title page at full zoom for seams and filled counters. Open the HTML and check the
   navigation panel. Report the two paths, the page count, and what you did not check.

## What the renderer refuses

Every one of these stops the build with the file and line, so a broken report never prints:

- Front matter that misses a required key or carries an unknown one.
- Text before the first `#`, a `###` with no `##` above it, or a reserved part out of order.
- A link to a slug no heading has, a slug two headings share, or a relative link to a file, which
  would be dead in the PDF.
- A missing figure or include, an include cycle, or a code fence left open.
- A `Table:` caption with no table after it, or a table with no header row.

The HTML inlines its stylesheet, figures and wordmark, and holds no `file://` address, so it works
wherever it is moved or published.

## Tests

`python3 skills/write-report/tests/test_report.py` from the repository root. It renders
`assets/example.md` for real when Chrome is installed. Set `$KSTACK_PRIVATE_TERMS` to a
comma-separated list of words that must never appear in the skill, and the leak check reads it.
