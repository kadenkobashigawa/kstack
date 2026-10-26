# The report format

A report is one Markdown file, which can be split across included files. `scripts/report.py` reads
it and stops at the first fault with one line naming the file, the line and the fix. Every
```` ```markdown ```` example on this page parses, and `tests/test_report.py` checks that (R5).

## Front matter

The file opens with `key: value` lines between two `---` lines. Four keys are required and one is
optional. Any other key stops the build. This is a hand parser, not YAML: one key per line, no
quotes needed, no lists.

```markdown
---
title: Q3 Platform Review
author: Platform team
release: 1.2
date: October 2026
wordmark: brand/wordmark.svg
---

# Introduction

The report starts here.
```

- `title`: the title page and the running header's left side.
- `author` and `date`: the title page.
- `release`: the title page and the running header's right side, as "Release 1.2".
- `wordmark` (optional): an SVG, by path relative to this file. It goes on the title page and at
  the top of the screen's navigation panel, inlined, so the HTML works wherever it is moved. Run
  `scripts/wordmark.py` on a logo first. The result fills with the text color, so the dark panel
  shows it white. Without a wordmark the title page has no logo and keeps its layout.

## Parts and headings

Every `#` heading starts a part on a new page. Text before the first `#` stops the build.

- `# Title` is a chapter, numbered 1, 2, 3 in file order.
- `## Title` is a section, numbered under its part: 2.1.
- `### Title` is a subsection: 2.1.3. A `###` with no `##` above it stops the build.
- `####` and deeper are unnumbered headings at the body size, for a titled item inside a section.

Three `#` titles are reserved, and they come after the chapters in this order:

1. `# References`: one numbered list, numbered as the next chapter.
2. `# Appendix: <title>`: lettered A, B, C. Its sections number A.1, A.1.1.
3. `# Glossary`: one list of `**term** — definition` items, lettered after the last appendix.

A reserved part out of order, or a second References or Glossary, stops the build.

```markdown
# Introduction

Paragraphs before the first `##` are the chapter's introduction.

## What this review covers

### Scope

#### A decision title stays unnumbered

# Known problems

# References

1. Bass, L. et al. *Software Architecture in Practice*, 4th ed. 2021.

# Appendix: Convention survey

## Method

# Glossary

- **PPR** — personalized PageRank.
```

Write headings in sentence case. The renderer title-cases them in the PDF, the HTML and the
contents, so the source follows technical-writing's rule and the output follows the layout's.
A word in backticks, or one holding a digit, an underscore or a capital, stays as written.

## Page breaks

A `---` line on its own in the body starts a new page, for a record that should open at the top of
one. On screen it becomes a gap.

```markdown
## The last section of a record

---

## The next record opens a page
```

## Blocks

Blocks are separated by blank lines.

- **Paragraph**: consecutive lines. A backslash at the end of a line breaks it.
- **Lists**: `- ` or `1. ` at the start of the line. An item may carry one nested list, indented
  two spaces or more. A list of five items or fewer never splits across pages.
- **Code**: a ```` ``` ```` fence with an optional language. The closing fence is a line starting
  with ```` ``` ````. A fence left open stops the build.
- **Table**: pipe rows under a one-line `Table: caption`, directly or after a blank line. Tables
  number 1, 2, 3 through the whole report, captioned above. A caption with no table as the next
  block, or a table with no header row above its `|---|` line, stops the build.
- **Box**: GitHub's `> [!NOTE]`, `> [!EXAMPLE]` or `> [!WARNING]` on the first line. Any other
  kind stops the build. A quote with no kind is a Note.
- **Figure**: `![caption](file)` alone on a line. An SVG is inlined, and a PNG, JPEG, GIF or WebP
  becomes a `data:` URI. The path is relative to the file the line is in. Figures number 1, 2, 3,
  captioned below. A caption may hold brackets and links. A remote address or a missing file stops
  the build.

````markdown
Table: Services in scope

| Service | Owner |
|---|---|
| ingest | data team |

> [!WARNING]
> Boxed text.

- First item.
  - A nested item.
- Second item.

```python
print('code keeps its line breaks')
```
````

Inline: `**bold**`, `*italics*`, `` `code` ``, `[text](address)` and bare `https://` addresses,
which become links.

## Links

A link to a heading uses its slug: the heading as written, lowercased, punctuation dropped and
spaces turned into hyphens. An appendix's slug includes its prefix: `# Appendix: Convention
survey` is `#appendix-convention-survey`. The renderer adds the target's number after the link
text, so the link still tells a reader of the printed page where to turn.

```markdown
# Introduction

## Scope

See [Scope](#scope) for the limits, and [the method](#method).

# Appendix: Convention survey

## Method
```

That renders as "Scope (1.1)" and "the method (A.1)". A chapter link reads "(Chapter 2)" and an
appendix link "(Appendix A)".

- An unknown slug stops the build.
- A slug two headings share is fine until a link names it. Then the build stops and lists both, so
  reword one heading.
- A relative link to a file stops the build, because it would be dead in the PDF. Link a heading,
  or give a full `https://` address. `http`, `https` and `mailto` links pass through.
- A link inside a code span is text and is left alone.
- A link in a table or figure caption follows the same rules.

## Includes

An `!include path.md` line, alone on a line, is replaced by that file's lines before anything is
numbered, so a report split across files numbers exactly as one file would. *(kstack: an include
line rather than a front matter list, so the order of parts stays the order of lines, and the one
numbering pass never knows a file boundary.)*

```text
# Introduction

Text of the introduction.

!include chapters/design.md
!include chapters/known-problems.md

# References

1. A reference.

!include research/convention-survey.md
```

- The path is relative to the file the `!include` line is in, so an included file can include its
  neighbours.
- An included file has no front matter. Only the main file carries it.
- An included file may hold any number of parts, or only sections that continue the part above.
- Figures in an included file resolve against that file's folder, and its errors name that file
  and line.
- A missing file, a cycle (a file that includes itself, directly or through others) or an included
  file with front matter stops the build at the `!include` line.
- An `!include` inside a code fence is text.

## Not supported

These stop the build or render as plain text, by design:

- HTML in the source is escaped and shown as text.
- Setext headings (a line underlined with `===` or `---`). A `---` line is a page break.
- More than one nested list level, footnotes, and images inside a paragraph.
