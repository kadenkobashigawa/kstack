# Appendix: How numbering works

This appendix sits in its own file, and `example.md` includes it with an `!include` line. Its
headings number as if they were written in the main file.

## Chapters and appendices

Chapters number 1, 2, 3 in the order they appear. The references take the next number. Appendices
take letters from A, and the glossary takes the letter after the last appendix.

## Sections

A `##` heading numbers under its part, as 1.1 or A.1. A `###` heading numbers under the `##` above
it, as 1.1.1 or A.1.1.

### A deeper section

This section is A.2.1, which shows a third level inside an appendix.

# Appendix: How links resolve

A link to `#slug` points at the heading with that slug, and the renderer adds the heading's number
after the link text. A link back to [the prints](#the-prints) works from an included file too.
