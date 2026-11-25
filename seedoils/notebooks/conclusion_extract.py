"""Finds the conclusion sentences of an abstract, for the conclusion check (make_conclusion_check_tool.py).
Rules, in order: (1) a structured 'CONCLUSION(S)' / 'INTERPRETATION' / 'IMPLICATIONS' section to the end; (2) from the first sentence starting with
'In conclusion', 'In summary', 'Overall', 'Taken together', 'These (results|findings|data) (suggest|indicate|show|demonstrate|support)', 'Our
(results|findings|data) (suggest|indicate|show)', 'We conclude'; (3) the last two sentences. Returns (conclusion text, rule used)."""
import re

SECTION = re.compile(r"\b(CONCLUSIONS?|Conclusions?|INTERPRETATION|Interpretation|IMPLICATIONS|CONCLUSIONS? AND RELEVANCE|Conclusions? and relevance)\s*[:.]\s*")
CUE = re.compile(r"(?:^|(?<=[.!?]\s))(In conclusion|In summary|Overall|Taken together|We conclude|(?:These|Our|The present|The)\s+(?:results|findings|data|study|studies|evidence)\s+"
                 r"(?:suggest|suggests|indicate|indicates|show|shows|demonstrate|demonstrates|support|supports|provide|provides))", re.I)
SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z(])")


def conclusion(abstract):
    a = re.sub(r"\s+", " ", abstract or "").strip()
    if not a:
        return "", "none"
    m = list(SECTION.finditer(a))
    if m:
        return a[m[-1].end():].strip(), "section"
    m = CUE.search(a)
    if m:
        return a[m.start():].strip(), "cue"
    s = SENT.split(a)
    return " ".join(s[-2:]).strip(), "last two sentences"
