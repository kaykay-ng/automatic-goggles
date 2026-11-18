"""Negation marking for marketing copy (upf/PLAN.md, 18 Nov). Shared by the word plot and robustness checks.
Rule (VADER-style, Hutto & Gilbert 2014; similar in spirit to NLTK's mark_negation):
 - negators = VADER's NEGATE list (no, not, never, without, none, nothing, nor, cannot, don't ...), plus 'free of' / 'free from';
 - a negator marks the next 4 CONTENT words (stopwords do not use up the scope, so 'without the use of pesticides' reaches 'pesticides');
 - commas, 'or', 'and', 'nor' do not end the scope (lists: 'no artificial flavors, colors or preservatives'); sentence punctuation and 'but' do;
 - 'not only / not just / not even / not merely / not simply' is not a negation;
 - an 'X-free' compound marks X (gluten-free -> no_gluten).
Marked words are returned as 'no_<word>'. Known limit: a list scope can run into a following clause after a comma ('no preservatives, delicious taste').
"""
import re
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

NEG = {"aint", "arent", "cannot", "cant", "couldnt", "darent", "didnt", "doesnt", "dont", "hadnt", "hasnt", "havent", "isnt", "mightnt", "mustnt", "neither", "neednt", "never",
       "none", "nope", "nor", "not", "nothing", "nowhere", "oughtnt", "shant", "shouldnt", "wasnt", "werent", "without", "wont", "wouldnt", "rarely", "seldom", "despite", "no", "nobody"}
NOT_NEG_AFTER_NOT = {"only", "just", "even", "merely", "simply"}
SENT_END = set(".;:!?()•") | {"but"}
LIST_GLUE = {",", "or", "and", "nor", "&"}
STOPW = set(ENGLISH_STOP_WORDS) | {"use", "used", "using", "added", "any", "artificial"} - {"no", "not", "nor", "without", "never", "none", "nothing"}
TOK = re.compile(r"[a-z]+(?:-free)?|[.,;:!?()•&]")
SCOPE = 4


def mark(text):
    """lower-cased tokens; negated content words prefixed 'no_'. 'artificial', 'added', 'any', 'use' do not use up scope (they modify the target), but are still marked."""
    toks = [t.replace("'", "") for t in TOK.findall(text.lower().replace("’", "'").replace("n't", "nt"))]
    out, scope = [], 0
    for k, x in enumerate(toks):
        if x in SENT_END: scope = 0; out.append(x); continue
        if x.endswith("-free"):
            out.append("no_" + x[:-5]); continue
        if x == "free" and k + 1 < len(toks) and toks[k + 1] in ("of", "from"): scope = SCOPE; continue
        if x in NEG:
            if x == "not" and k + 1 < len(toks) and toks[k + 1] in NOT_NEG_AFTER_NOT: out.append(x); continue
            scope = SCOPE; continue
        if scope > 0:
            if x in LIST_GLUE: continue
            if x in STOPW and x not in ("artificial", "added", "use", "used", "using", "any"): out.append(x); continue
            out.append("no_" + x)
            if x not in ("artificial", "added", "use", "used", "using", "any"): scope -= 1
            continue
        out.append(x)
    return out


if __name__ == "__main__":
    for s in ["No artificial flavors, colors or preservatives. Delicious!", "Grown without the use of pesticides", "Not only delicious but healthy",
              "Gluten-free and free from high fructose corn syrup", "Contains no added sugar", "We don't use chemicals, ever."]:
        print(s, "->", [t for t in mark(s) if t.startswith("no_")])
