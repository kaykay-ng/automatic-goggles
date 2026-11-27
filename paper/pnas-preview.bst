% pnas-preview.bst -- bibliography style for the LOCAL preview (preview.tex) only, written 27 Nov 2026 to imitate the current PNAS reference format
% (the official pnas-new.bst comes with the Overleaf PNAS template and is used by main.tex there). Numbered in order of citation.
%   article:        A. B. Author, C. Author, Title. Journal Volume, pages (year).
%   inproceedings:  A. B. Author, "Title" in Book title (Publisher, year), pp. pages.
%   six or more authors: first author et al.
%   book:           A. B. Author, Title (Publisher, year).
%   misc / online:  A. B. Author, Title. How published (year). URL. Note.
ENTRY
  { author booktitle edition editor howpublished journal note number pages publisher series title url volume year }
  {}
  { label }

INTEGERS { nameptr namesleft numnames }
STRINGS { s t }

FUNCTION {not} { { #0 } { #1 } if$ }
FUNCTION {and} { 'skip$ { pop$ #0 } if$ }
FUNCTION {or} { { pop$ #1 } 'skip$ if$ }
FUNCTION {field.or.null} { duplicate$ empty$ { pop$ "" } 'skip$ if$ }

FUNCTION {format.names}
{ 's :=
  "" 't :=
  #1 'nameptr :=
  s num.names$ 'numnames :=
  numnames #5 >
    { #1 'namesleft := }  % PNAS: six or more authors -> first author et al.
    { numnames 'namesleft := }
  if$
    { namesleft #0 > }
    { s nameptr "{f.~}{vv~}{ll}{, jj}" format.name$
      duplicate$ "others" =
        { pop$ "et al." }
        'skip$
      if$
      nameptr #1 >
        { t ", " * swap$ * 't := }
        { 't := }
      if$
      nameptr #1 + 'nameptr :=
      namesleft #1 - 'namesleft :=
    }
  while$
  numnames #5 > { t " et al." * } { t } if$
}

FUNCTION {authors} { author empty$ { "" } { author format.names ", " * } if$ }
FUNCTION {pages.dash} { pages field.or.null }
FUNCTION {year.paren} { year empty$ { "" } { "(" year * ")" * } if$ }
FUNCTION {url.part} { url empty$ { "" } { " \url{" url * "}." * } if$ }
FUNCTION {note.part} { note empty$ { "" } { " " note * "." * } if$ }

FUNCTION {bibitem} { newline$ "\bibitem{" cite$ * "}" * write$ newline$ }

FUNCTION {article}
{ bibitem
  authors title field.or.null * ". " *
  journal field.or.null *
  volume empty$ 'skip$ { " " * volume * } if$
  pages empty$ 'skip$ { ", " * pages.dash * } if$
  " " * year.paren * "." *
  url.part * note.part *
  write$ newline$
}

FUNCTION {inproceedings}
{ bibitem
  authors "``" * title field.or.null * "'' in " * booktitle field.or.null *  % PNAS: conference paper titles in quotation marks
  series empty$ 'skip$ { ", " * series * volume empty$ 'skip$ { " " * volume * } if$ } if$
  series empty$ volume empty$ not and { ", vol. " * volume * } 'skip$ if$
  " (" * publisher empty$ { "" } { publisher ", " * } if$ * year field.or.null * ")" *
  pages empty$ { "." * } { ", pp. " * pages.dash * "." * } if$
  url.part * note.part *
  write$ newline$
}

FUNCTION {book}
{ bibitem
  authors title field.or.null * " (" * publisher empty$ { "" } { publisher ", " * } if$ * year field.or.null * ")." *
  url.part * note.part *
  write$ newline$
}

FUNCTION {misc}
{ bibitem
  authors title field.or.null * ". " *
  howpublished empty$ 'skip$ { howpublished * " " * } if$
  year.paren * "." *
  url.part * note.part *
  write$ newline$
}

FUNCTION {online} { misc }
FUNCTION {techreport} { misc }
FUNCTION {incollection} { inproceedings }
FUNCTION {default.type} { misc }

READ

FUNCTION {begin.bib}
{ "\begin{thebibliography}{99}" write$ newline$ }

EXECUTE {begin.bib}
ITERATE {call.type$}

FUNCTION {end.bib}
{ newline$ "\end{thebibliography}" write$ newline$ }

EXECUTE {end.bib}
