"""Paste network_draft.tex into a COPY of body.tex (used by compile_draft.sh; body.tex itself is not changed).
Part (1) RESULTS replaces '\\subsection*{TODO}' and its line up to '\\section*{Discussion}'; part (2) METHODS replaces '\\textbf{Networks.} TODO. \\\\'."""
import sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src + "/body.tex").read(); d = open(src + "/network_draft.tex").read()
res = d.split("% (1) RESULTS")[1].split("% (2) METHODS")[0].split("\n", 2)[2]
met = d.split("% (2) METHODS")[1].split("% (3) DISCUSSION")[0].split("\n", 2)[2].split("% ====")[0].strip()
i, j = s.index("\\subsection*{TODO}"), s.index("\\section*{Discussion}")
s = s[:i] + res + "\n" + s[j:]
s = s.replace("\\textbf{Networks.} TODO. \\\\", met + " \\\\")
open(dst + "/body.tex", "w").write(s)
