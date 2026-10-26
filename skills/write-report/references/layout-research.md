# Layout research

This file explains why the look in `design.md` is what it is. Three surveys, of standards bodies,
of software-documentation toolchains and of readability studies, each read primary sources in
October 2026. This file keeps what they found and which value each finding set. A value with no
source here is a choice, and `design.md` says so.

## What standards bodies agree on

- One column, and decimal section numbers at most five levels deep, with no lone subsection
  (ISO/IEC, 2021, 22.3; IEEE, 2014, 11.1; RFC 7322, §4).
- Table captions above the table and figure captions below, each numbered in its own sequence,
  in the form "Table 1 – Title" (ISO/IEC, 2021, 28.3, 29.3; IEEE, 2014, 13.1, 14.2; AFRL, 2010).
- Appendices lettered: "Appendix A", items A.1 (RFC 7322, §4; ISO/IEC, 2021, 29.3).
- Notes and examples labelled and informative only, never carrying a requirement (ISO/IEC, 2021,
  24.3–24.5, 25.3). W3C sets them in boxes (W3C, `base.css`).
- A fixed front-matter order: title, then contents, then body (RFC 7322, §4; NASA, 2005).
- A 10–12pt print body. NASA never goes below 10pt (NASA, 2005, §4.3.1.7; AFRL, 2010).

They split on paper: ISO/IEC and IETF use A4, while IEEE, NASA and AFRL use Letter (RFC 7995,
§3.1.2; AFRL, 2010). Letter is the choice here, for US readers.

## What documentation toolchains do

- **Print:** one column, a 10–10.5pt serif body, bold headings, numbered sections, chapters on a
  new page. Sphinx's LaTeX output is Letter, 10pt, with sections at 14.4, 12 and 10pt (Sphinx,
  `sphinx.sty`). DocBook XSL-FO justifies and hyphenates a 10pt serif body (DocBook,
  `xsl/params`). The PostgreSQL manual turns off DocBook's body indent and boxes its notes with a
  1pt border (PostgreSQL, `stylesheet-fo.xsl`).
- **Screen:** a 16px base and a line height of 1.5–1.65. The Read the Docs theme has a 300px
  left navigation panel, content up to 800px, and paragraphs at 16px on 24px (Read the Docs,
  `sphinx_rtd_theme`).

The look takes Sphinx's sizes, DocBook's justified body and PostgreSQL's boxes for print, and the
Read the Docs layout for the screen.

## What readability studies show

- **Line length.** The print convention is 45–75 characters, 66 ideal (Nanavati & Bias, 2005,
  p. 134). On screen, 100-character lines read faster than 25-character ones with equal
  comprehension (Dyson & Kipping, 1998), but in the one careful comprehension test 55 beat 100
  (Dyson & Haselgrove, 2001). WCAG 1.4.8 (AAA) caps lines at 80 characters. A full-width Letter
  line at 10pt runs past these. The look accepts the longer line to fit tables and code, as Sphinx
  does.
- **Size.** 9–12pt print reads equally fast (Dyson, 2004), and fluent reading needs about 9pt
  Times at reading distance (Legge & Bigelow, 2011). 10pt sits inside both.
- **Line spacing.** 8–10pt type takes 1–2pt of extra leading, a ratio of about 1.1–1.25 (Dyson,
  2004). The body is 10pt on 1.2.
- **Headings.** Size is the strongest cue to level, and steps of about 20% between levels were
  easiest to tell apart (Williams & Spyridakis, 1992). The steps 14.4, 12 and 10pt are 20% each.
  Part titles take 20pt to match the contents title.
- **Justification.** Readers prefer justified text, though left-aligned text was searched faster
  (Ling & van Schaik, 2007). Print justifies, as the toolchains do, and the screen is
  left-aligned.
- **Margins.** The evidence is thin: Dyson says their contribution "has not yet been determined"
  (Dyson, 2004). 0.75in is a choice that leaves room for tables.

## Sources

- AFRL (2010). Format Guidelines for ANSI/NISO Z39.18.
  https://files.simpler.grants.gov/opportunities/2948ce44-1a9f-4998-9a3d-4a8517cd34d8/attachments/430ca43b-6f1f-4b49-9b8b-9eab7ed59300/ANSI_Format_Guidelines_Jun_10.pdf
- DocBook. XSL stylesheet parameters.
  https://github.com/docbook/xslt10-stylesheets/tree/master/xsl/params
- Dyson, M. C. (2004). How physical text layout affects reading from screen. *Behaviour &
  Information Technology* 23(6). https://doi.org/10.1080/01449290410001715714
- Dyson, M. C. & Haselgrove, M. (2001). *International Journal of Human-Computer Studies* 54(4).
  https://doi.org/10.1006/ijhc.2001.0458
- Dyson, M. C. & Kipping, G. J. (1998). *Visible Language* 32(2).
  https://journals.uc.edu/index.php/vl/article/view/5671
- IEEE (2014). IEEE-SA Standards Style Manual.
  https://sagroups.ieee.org/sagroups-hyperspectral/wp-content/uploads/sites/76/2019/12/IEEE_Standards_StyleManual_2014.pdf
- ISO/IEC (2021). ISO/IEC Directives, Part 2, edition 9.0.
  https://www.cta.tech/media/1ebl2xah/iso-iec-directives-part-2.pdf
- Legge, G. E. & Bigelow, C. A. (2011). Does print size matter for reading? *Journal of Vision*
  11(5). https://pmc.ncbi.nlm.nih.gov/articles/PMC3428264/
- Ling, J. & van Schaik, P. (2007). *Displays* 28(2). https://doi.org/10.1016/j.displa.2007.04.003
- Nanavati, A. A. & Bias, R. G. (2005). Optimal line length in reading. *Visible Language* 39(2).
  https://journals.uc.edu/index.php/vl/article/view/5765
- NASA (2005). Publications Guide for Authors, NASA/SP-2005-7602/REV1.
  https://ntrs.nasa.gov/citations/20050189209
- PostgreSQL. `doc/src/sgml/stylesheet-fo.xsl`.
  https://github.com/postgres/postgres/blob/master/doc/src/sgml/stylesheet-fo.xsl
- Read the Docs. `sphinx_rtd_theme`. https://github.com/readthedocs/sphinx_rtd_theme
- RFC 7322 (2014). RFC Style Guide. https://www.rfc-editor.org/rfc/rfc7322.html
- RFC 7995 (2016). PDF Format for RFCs. https://www.rfc-editor.org/rfc/rfc7995.html
- Sphinx. LaTeX style files. https://github.com/sphinx-doc/sphinx/tree/master/sphinx/texinputs
- W3C. TR design `base.css`. https://github.com/w3c/tr-design/blob/gh-pages/src/base.css
- W3C. WCAG 2.2, 1.4.8 Visual Presentation. https://www.w3.org/TR/WCAG22/#visual-presentation
- Williams, T. R. & Spyridakis, J. H. (1992). *IEEE Transactions on Professional Communication*
  35(2). https://doi.org/10.1109/47.144865
