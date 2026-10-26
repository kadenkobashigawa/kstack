# The look

Every report has the same look. It follows the software-manual layout of Sphinx's LaTeX output,
DocBook XSL-FO as the PostgreSQL manual uses it, and, on screen, the Read the Docs theme. The
values below are what `scripts/theme.css` sets. The CSS does not read this file, so change both
together. `layout-research.md` gives the reason for each value, with sources.

The look is plain on purpose: black text on a white page, one full-width column, no decoration.

## Key characteristics

- US Letter, 0.75in margins, one column.
- Serif throughout: 10pt body, justified and hyphenated, and bold headings in title case. Part
  titles are 20pt, the size of Contents, then 14.4 and 12pt.
- Each part starts on a new page, and so does each `---` break.
- Sections numbered 1, 1.1 and 1.1.1, appendices A and A.1, tables captioned above and figures
  below.
- Notes, examples and warnings in boxes with a 1pt border.
- On screen: the Read the Docs layout.

## Tokens

Table: Colors

| Token | Value | Use |
|---|---|---|
| paper | #FFFFFF | page |
| ink, rule | #000000 | text, header rule, table rules, boxes |
| leader | #777777 | dotted contents leaders |
| code-fill, code-border | #F2F2F2, #BBBBBB | code blocks |
| nav-fill, nav-ink | #2C2C2C, #DDDDDD | screen navigation panel |
| link-print | #377063 | links in the PDF |
| link-screen, hover, visited | #2980B9, #3091D1, #9B59B6 | links on screen |

Table: Type

| Role | Value |
|---|---|
| body | Times 10pt, line height 1.2 |
| headings | bold, 20 / 14.4 / 12pt; unnumbered headings 10pt |
| captions, running header and footer | 9pt |
| code | Menlo 8.5pt |
| screen body | 16px on a 24px line; headings 200 / 144 / 120% |

Table: Spacing

| Token | Value |
|---|---|
| page margin | 0.75in |
| screen content | up to 800px |
| screen navigation panel | 300px |
| wordmark, print | a 2.4in-wide slot, at most 0.9in tall |
| wordmark, screen | 200px wide |

## Colors

Black and white, with greys only for structure: dotted contents leaders, the code background and
the dark navigation panel on screen. The one color is for links in the text: colored text, no
underline or box.

- **Print:** #377063 is Sphinx LaTeX's default `OuterLinkColor`, `{rgb}{0.216,0.439,0.388}`
  (Sphinx, `sphinx.sty`).
- **Screen:** #2980B9, #3091D1 and #9B59B6 are the `a`, `a:hover` and `a:visited` colors of the
  Read the Docs theme (Read the Docs, `sphinx_rtd_theme`). #2980B9 on white is 4.3:1, under the
  4.5:1 WCAG AA asks of body text. The look keeps it because it is the source value.

## Typography

Times stands in for TeX Gyre Termes, the Times clone Sphinx's LaTeX output uses (Sphinx,
`sphinx.sty`), and Menlo for code. Where neither Times nor Times New Roman is installed, the
stylesheet falls back to TeX Gyre Termes, then Liberation Serif, then any serif, and to DejaVu
Sans Mono for code. Page breaks can then fall differently.

The renderer sets headings in title case. The source is written in sentence case. Bold marks
only headings, labels and glossary terms, and running text stays regular weight. An unnumbered
heading is set at the body size, 10pt bold, which is the next step down from 12pt and about 20%
smaller, as the other steps are.

## The wordmark

The wordmark is optional and absent by default. A logo's separate shapes print hairline seams
where they meet, because a renderer anti-aliases each shape alone, so `scripts/wordmark.py` merges
them into one path filled by the nonzero rule, with holes wound the other way so counters stay
open.

- **Print:** on the title page only, right-aligned above the title, as Sphinx places
  `latex_logo`, and never in the running header. Its aspect sets its height. It fills a 2.4in
  slot, capped at 0.9in, so a square logo is 0.9in tall and a 5.7:1 wordmark is 0.42in.
- **Screen:** at the top of the navigation panel, alone and in white, as the Read the Docs theme
  places `html_logo` with `logo_only`. The title stays in the content.

## Layout

- **Print:** Letter, 0.75in margins. A title page, then the contents, then the body. Each part
  starts a new page. Lists of five items or fewer do not split across pages. Text keeps a 14pt gap
  below the header rule, which carries the title on the left and the release on the right. The
  page number sits at the bottom center. The contents list chapters to the third level and
  appendices to the second.
- **Screen:** the contents in a fixed 300px panel on the left, content up to 800px. Below 900px
  wide, the panel stacks above the content and lists part titles only.

## Components

- **Note / Example / Warning:** a box with a 1pt black border and a bold label.
- **Table:** caption above ("Table 1 – Title"), bold header row, horizontal rules only.
- **Figure:** caption below, centered ("Figure 1 – Title").
- **Code:** light grey fill, thin border, Menlo.
- **Lists:** an item may carry one nested list.
- **References:** a numbered list. **Glossary:** a definition list, term in bold.

## Sources

- Sphinx. LaTeX style files (`sphinx.sty`, `sphinxmanual.cls`).
  https://github.com/sphinx-doc/sphinx/tree/master/sphinx/texinputs
- Read the Docs. `sphinx_rtd_theme`. https://github.com/readthedocs/sphinx_rtd_theme
- PostgreSQL. `doc/src/sgml/stylesheet-fo.xsl`.
  https://github.com/postgres/postgres/blob/master/doc/src/sgml/stylesheet-fo.xsl
- W3C. WCAG 2.2, Contrast (Minimum). https://www.w3.org/TR/WCAG22/#contrast-minimum
