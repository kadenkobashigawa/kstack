---
title: Example Report
author: The write-report skill
release: 1.0
date: October 2026
---

# Introduction

This report shows every construct the write-report format has, once each. It renders with
`scripts/report.py`, and its test renders it on every run, so the format and this file cannot drift
apart.

A paragraph before the first `##` heading is the chapter's introduction. It carries no number of its
own.

## What this example covers

The chapters below hold a table, a figure, notes, lists, code, links between sections, references,
two appendices and a glossary. The appendices live in a second file, which this one includes.

### Scope

The example covers the input format only. It does not cover how to choose a report's chapters,
which `SKILL.md` covers.

#### An unnumbered heading

A `####` heading stays unnumbered, at the body size. Use it for a titled item inside a section,
such as one decision in a list of decisions.

## Tables and boxes

A table takes its caption from a `Table:` line directly above it. The renderer numbers tables
through the whole report.

Table: The parts a report can have, in the order they must appear

| Part | Heading | Numbered |
|---|---|---|
| Chapter | `# Title` | 1, 2, 3 |
| References | `# References` | after the last chapter |
| Appendix | `# Appendix: Title` | A, B, C |
| Glossary | `# Glossary` | the letter after the last appendix |

> [!NOTE]
> A note helps the reader but is not needed to follow the text. It never holds a requirement.

> [!EXAMPLE]
> `[Scope](#scope)` renders as a link that ends with the section's number.

> [!WARNING]
> A relative link to another file stops the build, because it would be dead in the PDF.

# How a report is built

The renderer prints the report until its contents hold still. Each print finds the page each
heading lands on, and the next writes those pages into the contents. A short report settles on its
second print, and one more print without the page markers makes the PDF.

## The prints

![The report printed until the contents carry real page numbers](figure.svg)

The steps are:

1. Read the front matter and every included file.
2. Number the chapters, the references, the appendices and the glossary in one pass.
3. Print a marked PDF and read each heading's page from its text, until the pages hold still.
4. Print the final PDF without markers, check it matches, and write the HTML beside it.

## Lists and code

A bulleted list may carry one nested list:

- The front matter names the title, author, release and date.
- The body starts at the first `#` heading.
  - Text before it stops the build.
  - A `##` or `###` heading numbers under the chapter above it.
- A `---` line starts a new page.

Code keeps its line breaks and is never justified:

```bash
python3 scripts/report.py docs/reports/example.md
```

See [Scope](#scope) for what this example leaves out, and [the numbering appendix](#appendix-how-numbering-works)
for how the numbers are assigned. Full addresses stay links, such as https://www.w3.org/TR/WCAG22/.

---

## A section that opens a page

The `---` line above this section starts a new page, for a record that should begin at the top of
one.

# Known problems

- The skill bundles no fonts. On a machine without Times, Chrome falls back to the next font in the
  stylesheet, and the page count can differ from a Mac's.
- An arc in a wordmark has to be converted to curves before `wordmark.py` reads it.

# References

1. Read the Docs. *sphinx_rtd_theme*. https://github.com/readthedocs/sphinx_rtd_theme
2. Sphinx. *LaTeX builder style files*. https://github.com/sphinx-doc/sphinx/tree/master/sphinx/texinputs

!include example-appendix.md

# Glossary

- **Front matter** — the `key: value` lines between two `---` lines at the top of the report.
- **Slug** — a heading lowercased, punctuation dropped and spaces turned into hyphens, used as a
  link target.
