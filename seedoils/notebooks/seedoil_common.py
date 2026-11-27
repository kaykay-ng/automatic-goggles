"""Shared rules for every seed-oil script, so all of them filter accounts and split words the same way.

BOTS: an account is a bot when it is AutoModerator or its name ends in 'bot' (case-insensitive), e.g. RemindMeBot, sneakpeekbot.
  Applied to ALL input (comments, posts, reply parents, citing users, vote reference sets). '[deleted]' is a separate,
  per-script choice and is NOT part of this rule. Check what the rule catches:  python seedoils/notebooks/seedoil_common.py
TOKEN_PATTERN: words of 2+ characters, plus hyphenated compounds kept whole ('omega-6', 'n-6', 'omega-3s', 'low-fat',
  'seed-oil-free'). scikit-learn's default pattern \\b\\w\\w+\\b splits at the hyphen and drops 1-character pieces, so
  'omega-6' became 'omega' and 'n-6' vanished.
HyphenBERTopic: BERTopic, for English, deletes every character outside [A-Za-z0-9 ] before counting topic words
  (BERTopic._preprocess_text), which turned 'omega-6' into 'omega6' and glued words at other punctuation ('oils/omega-6' ->
  'oilsomega6'). This subclass uses bertopic_clean instead: hyphens and accented letters kept, apostrophes deleted
  ("don't" -> "dont"), names merged, negations marked, punctuation dropped. It changes topic WORDS only: topics are assigned
  from the embeddings.
NEGATION (version 3, 25 Nov): only absence claims are marked: 'no' / 'without' + the noun phrase ("no seed oils" -> no_seed-oil),
  so word counts no longer read "no seed oils" as more "seed oil". Verb negation is not marked. Check by reading:  python seedoils/notebooks/seedoil_common.py negation
LEMMATIZATION (decision 22 Nov): plural nouns become singular where words are counted ("oils" -> "oil"); see LEMMATIZE.
NAMES (entity_aliases.csv, edited by hand): spellings of one person/organisation/study are merged into one token (RFK, RFK Jr.,
  Robert F. Kennedy -> rfk-jr) wherever words are counted (bertopic_clean). Embeddings and emotion models read the original text.
  Check what each alias matches:  python seedoils/notebooks/seedoil_common.py aliases
"""
import csv
import json
import re
import sys
from pathlib import Path

AUTO_MOD = "AutoModerator"
TOKEN_PATTERN = r"(?u)\b\w+(?:-\w+)+\b|\b\w\w+\b"
ALIAS_FILE = Path(__file__).with_name("entity_aliases.csv")

# ---- text clean-up for WORD COUNTING (see bertopic_clean) ----
_POSS = re.compile(r"'s\b")                                         # possessive: "knobbe's" -> "knobbe"
_ABBR = re.compile(r"\b(\w|dr|mr|mrs|ms|jr|sr|st|vs|prof|etc|approx)\.")  # periods of initials and titles are not sentence ends: "u.s.", "dr.", "f."
_TOK = re.compile(r"[^\W_]+(?:-[^\W_]+)*|[.,;:!?()\[\]]")            # words (any alphabet, accents kept; hyphen compounds whole) + boundary punctuation;
#                                                                     everything else (emoji, quotes, slashes, underscores, symbols) acts as a space
# ANALYSIS SPLIT (decision 26 Nov 2026, back to 1 Jan 2024 to match the paper draft; the 1 Aug 2024 split of 25 Nov is kept as a marker and
# robustness column). Politics stayed ~0.5% of r/StopEatingSeedOils documents until July 2024 and jumped in August (RFK Jr. endorsed Trump on
# 23 Aug 2024), but activity was already growing from 2023. Column names pre2024 / from2024 mean before / from SPLIT_DATE. Newcomer = first comment from SPLIT_DATE.
SPLIT_DATE = "2024-01-01"
SPLIT_TS = 1704067200  # 2024-01-01 00:00 UTC
SPLIT_TS_JAN2024 = SPLIT_TS  # old name, same value
SPLIT_TS_AUG2024 = 1722470400  # 2024-08-01 00:00 UTC: RFK Jr. / politics marker, robustness rows only
PERIOD_LABELS = ("before 2024", "from 2024")
# author histories (fetch_author_histories.py) are stored split at one date; this glob picks the files that match SPLIT_DATE
HISTORY_GLOB = "author_subreddit_counts_shard*.jsonl.gz"
HISTORY_GLOB_AUG2024 = "author_subreddit_counts_aug2024_shard*.jsonl.gz"
# THEMES (decision 26 Nov): the 14 hand-assigned themes of the paper draft (themes_full_v3.json, all 123 topics); the 9 earlier themes stay in themes_confirmed.json
THEMES_FILE = "themes_full_v3.json"


def history_complete(min_authors=2900):
    """True once the author histories matching SPLIT_DATE (HISTORY_GLOB) hold at least min_authors people."""
    import glob as _g, gzip as _gz
    raw = Path(__file__).resolve().parents[1] / "data" / "raw"; n = 0
    for f in _g.glob(str(raw / HISTORY_GLOB)):
        try:
            with _gz.open(f, "rt", encoding="utf-8") as fh:
                n += sum(1 for _ in fh)
        except (EOFError, OSError):
            pass
    return n >= min_authors
_PUNCT = set(".,;:!?()[]")
# NEGATION (decision 22 Nov; revised twice on 25 Nov after hand checks). Version 1 (VADER-style, next 3 content words after any negator):
# fully right in 35% of 150 stretches. Version 2 (first content word after any negator): 56% of 100 fresh stretches (80% inside the negated
# phrase); most errors were verb negations landing on the object ('cant find any better alternatives' -> no_better).
# Version 3 (this one, user decision 25 Nov): only ABSENCE CLAIMS are marked, i.e. 'no' / 'without' + the noun phrase that follows
# ("no seed oils" -> no_seed-oil, "no added sugar" -> no_added no_sugar, "without any evidence" -> no_evidence). These are what change the
# meaning of a word count in this corpus (product labels, 'no evidence'). Verb and adjective negation ('dont eat', 'not toxic') is NOT marked.
# All negators are still dropped from the counted words, as before. Scope: up to NEG_SCOPE content words, ending at the first stop word after a
# marked word (the noun phrase has ended), punctuation, a line break or a clause word. Not absence claims (NOT_A_NEGATION_NEXT): 'no one',
# 'no way', 'no need', 'no longer', 'no matter', 'no doubt', 'no offense', 'no problem', 'no wonder', 'no idea', 'to no avail'; 'no' followed
# by a pronoun or 'the' is an interjection ('no the study says ...').
NEGATORS = {"aint", "arent", "cannot", "cant", "couldnt", "darent", "didnt", "doesnt", "dont", "hadnt", "hasnt", "havent", "isnt", "mightnt",
            "mustnt", "neither", "neednt", "never", "none", "nope", "nor", "not", "nothing", "nowhere", "oughtnt", "shant", "shouldnt", "wasnt",
            "werent", "without", "wont", "wouldnt", "rarely", "seldom", "no", "nobody"}
ABSENCE_NEGATORS = {"no", "without"}  # the only negators that mark words
NOT_A_NEGATION_NEXT = {("no", "one"), ("no", "way"), ("no", "need"), ("no", "longer"), ("no", "matter"), ("no", "doubt"), ("no", "offense"),
                       ("no", "offence"), ("no", "problem"), ("no", "worries"), ("no", "wonder"), ("no", "idea"), ("no", "avail"), ("no", "clue"),
                       ("no", "thanks"), ("no", "sense"), ("without", "doubt"), ("without", "question")}
NO_INTERJECTION = {"the", "i", "you", "it", "they", "we", "he", "she", "this", "that", "thats", "its", "im", "youre", "theyre"}
SCOPE_END = {"but", "however", "although", "though", "because", "since", "if", "when", "which", "who", "whereas", "while", "unless", "and", "or"}
NEG_SCOPE = 2
NEG_MAX_GAP = 2  # at most 2 stop words between 'no'/'without' and the first marked word ('without any evidence', 'no other health issues')
NEG_PRONOUNS = {"i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them", "everything", "anything", "something"}  # end the scope
NEG_COORD = {"or", "and", "nor"}  # 'no additives or chemicals': the list continues the noun phrase
_INTENSIFIERS = {"really", "actually", "necessarily", "exactly", "particularly", "inherently", "entirely", "completely", "totally", "that",
                 "super", "remotely", "significantly", "terribly", "especially", "literally", "even"}
_STOP_CACHE = []
# LEMMATIZATION (decision 22 Nov, replaces 'no lemmatization'): plural nouns -> singular, nothing else (verbs and adjectives untouched), with NLTK's
# WordNet noun list as the dictionary. Only REGULAR plural patterns are accepted, checked against WordNet nouns (revised 22 Nov after reading the
# changes: WordNet's own lemmatizer turned verbs into wrong nouns, uses -> us, doses -> dos, proves -> prof, believes -> belief, serves -> serf):
#   -ies -> -y if a noun (studies -> study); -s -> stem if a noun (doses -> dose, uses -> use); -es -> stem after s/x/z/ch/sh/o if a noun
#   (boxes -> box, potatoes -> potato); a short list of irregular plurals (analyses, hypotheses, indices, leaves, lives, children, ...).
# Words WordNet does not know at all (jargon, acronyms) lose a final plural 's' (carbs -> carb, pufas -> pufa, rcts -> rct) or -ies -> -y, except
# after ss/us/is, words ending in -omics, and the protected words below (singular words ending in s, names, brands, acronyms like PCOS, NHANES,
# PFAS, found by listing every change by frequency). Stop words are never changed; hyphenated terms change only their last part (seed-oils ->
# seed-oil); a negated word keeps its marker (no_oils -> no_oil).
LEMMATIZE = True
LEMMA_KEEP = {"data", "media", "news", "series", "species", "diabetes", "prediabetes", "less", "lens", "gas", "bus", "physics", "genetics", "economics",
              "politics", "hfcs", "gras", "aids", "sars", "texas", "omega", "trans", "pcos", "nhanes", "pfas", "diaas", "mets", "mcdonalds",
              "atkins", "taubes", "starbucks", "wholefoods", "stopeatingseedoils", "scientificnutrition", "theirs", "congrats", "doritos", "kudos",
              "athens", "paris", "always", "perhaps", "whereas", "thanks", "lots", "yes"}
LEMMA_IRREGULAR = {"analyses": "analysis", "hypotheses": "hypothesis", "diagnoses": "diagnosis", "prognoses": "prognosis", "theses": "thesis",
                   "syntheses": "synthesis", "indices": "index", "matrices": "matrix", "leaves": "leaf", "lives": "life", "shelves": "shelf",
                   "halves": "half", "knives": "knife", "wives": "wife", "loaves": "loaf", "calves": "calf", "children": "child", "men": "man",
                   "women": "woman", "feet": "foot", "teeth": "tooth", "mice": "mouse", "geese": "goose", "criteria": "criterion"}
_LEMMA_CACHE = {}
_WNL = []

# DIET COMMUNITIES, fixed 22 Nov 2026 BEFORE any overlap numbers were computed on the re-downloaded data (user decision).
# Rule: a subreddit organised around following or discussing a particular way of eating, or nutrition in general; not health, fitness,
# cooking or medical conditions in general. r/Biohackers is NOT a diet community; vegan communities ARE. ScientificNutrition is left out
# (it is the comparison subreddit). All names checked to exist on Arctic Shift on 22 Nov. Matching is case-insensitive.
DIET_CORE = {
    "low-carb / animal-based": ["keto", "ketoscience", "xxketo", "ketogains", "lowcarb", "carnivore", "carnivorediet", "zerocarb",
                                "AnimalBased", "SaturatedFat", "raypeat", "Paleo", "rawprimal"],
    "plant-based": ["vegan", "vegetarian", "PlantBasedDiet", "WholeFoodsPlantBased", "exvegans"],
    "fasting": ["intermittentfasting", "fasting", "omad"],
    "general nutrition": ["nutrition"],
}
# Borderline groups: reported as sensitivity checks (core + each group, and core + all of them), never in the main number.
DIET_BORDERLINE = {
    "weight loss / calorie counting": ["loseit", "CICO", "1200isplenty"],
    "recipes": ["ketorecipes", "veganrecipes"],
    "medical diets": ["glutenfree", "Celiac", "fodmap"],
    "diet-identity spin-offs": ["AntiVegan", "vegancirclejerk"],
}


COMMUNITY_NAMES = Path(__file__).resolve().parents[1] / "data" / "processed" / "community_names.json"


def community_labels(n):
    """Names of the n commenter communities (index order of commenter_topic_network_130_nodes.csv), from community_names.json:
    a list of {"long": ..., "short": ...} written by hand after reading each community's over-represented topics. Missing -> 'Community k'."""
    names = json.loads(COMMUNITY_NAMES.read_text()) if COMMUNITY_NAMES.exists() else []
    long_ = [names[k]["long"] if k < len(names) else f"Community {k + 1}" for k in range(n)]
    short = [names[k]["short"] if k < len(names) else f"C{k + 1}" for k in range(n)]
    return long_, short


def is_bot(author):
    """True for AutoModerator and any account whose name ends in 'bot'. None / NaN are not bots."""
    if not isinstance(author, str):
        return False
    return author == AUTO_MOD or author.lower().endswith("bot")


def not_bot(authors):
    """pandas Series of author names -> boolean mask, True where the account is NOT a bot."""
    s = authors.fillna("").astype(str)
    return ~((s == AUTO_MOD) | s.str.lower().str.endswith("bot"))


def _tokens(doc):
    """Lowercased word and boundary-punctuation tokens. Line breaks end a sentence; possessive 's dropped; apostrophes deleted
    ("don't" -> "dont"); periods of initials/titles removed so they do not end a sentence ("U.S." -> "us", "Dr. Knobbe" -> "dr knobbe")."""
    t = str(doc).replace("’", "'").replace("‘", "'").lower()
    t = re.sub(r"[\r\n\t]+", " . ", t)
    t = _POSS.sub("", t).replace("'", "")
    t = _ABBR.sub(r"\1", t)
    return _TOK.findall(t)


def basic_clean(doc):
    """Words only, space-separated (no punctuation, no name merging, no negation marking). Used to normalise aliases the same way as text."""
    return " ".join(x for x in _tokens(doc) if x not in _PUNCT)


def _stopwords():
    """Words that a negation passes over without marking: scikit-learn's English stop words (minus the negators) + intensifiers.
    Loaded lazily so that scripts without scikit-learn (the download scripts) can still import this module."""
    if not _STOP_CACHE:
        try:
            from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
            base = set(ENGLISH_STOP_WORDS)
        except ImportError:
            base = {"the", "a", "an", "is", "are", "be", "it", "this", "that", "to", "of", "and", "in", "for", "on", "at", "as", "all", "any", "so", "very", "too"}
        _STOP_CACHE.append((base | _INTENSIFIERS) - NEGATORS)
    return _STOP_CACHE[0]


def mark_negation(tokens, scope_len=NEG_SCOPE):
    """tokens (words + boundary punctuation) -> words without the negators; after 'no' / 'without' the content words of the following noun
    phrase are prefixed 'no_' (rules above NEGATORS)."""
    stop, out, n = _stopwords(), [], len(tokens)
    scope, marked, gap, coord = 0, False, 0, False
    for k, x in enumerate(tokens):
        if marked and x in NEG_COORD and out and out[-1].startswith("no_"):  # 'no X or Y': Y is inside the same absence claim
            out.append(x); scope, marked, gap, coord = scope_len, False, 0, True
            continue
        if x in _PUNCT or x in SCOPE_END:
            scope, marked = 0, False
            if x not in _PUNCT:
                out.append(x)
            continue
        if x in NEGATORS:
            nxt = tokens[k + 1] if k + 1 < n else ""
            scope, marked, gap, coord = 0, False, 0, False
            if x in ABSENCE_NEGATORS and (x, nxt) not in NOT_A_NEGATION_NEXT and not (x == "no" and nxt in NO_INTERJECTION):
                scope = scope_len
            continue
        if scope > 0 and (x in NEG_PRONOUNS or (x in stop and (marked or gap >= NEG_MAX_GAP or coord))):
            scope = 0  # the noun phrase has ended ('no evidence THAT ...'), or never started ('without YOU ...')
            out.append(x)
            continue
        if scope > 0 and x in stop:
            gap += 1; out.append(x)
            continue
        if scope > 0:
            out.append("no_" + x); scope -= 1; marked = True; coord = False
            continue
        out.append(x)
    return out


def load_aliases(path=ALIAS_FILE):
    """entity_aliases.csv -> {cleaned alias: canonical token}. Fails loudly on a malformed canonical or an alias given two canonicals."""
    out = {}
    if not Path(path).exists():
        return out
    with open(path, encoding="utf-8") as fh:
        rows = csv.DictReader(l for l in fh if l.strip() and not l.lstrip().startswith("#"))
        for r in rows:
            canon, alias = (r.get("canonical") or "").strip().lower(), basic_clean(r.get("alias") or "")
            if not alias:
                continue
            if not re.fullmatch(TOKEN_PATTERN, canon):
                raise ValueError(f"{path}: canonical {canon!r} is not one token (use lowercase letters/digits joined by hyphens)")
            if out.get(alias, canon) != canon:
                raise ValueError(f"{path}: alias {alias!r} is mapped to both {out[alias]!r} and {canon!r}")
            out[alias] = canon
    return out


ALIASES = load_aliases()
_ALIAS_RE = (re.compile(r"(?<![\w-])(" + "|".join(re.escape(a) for a in sorted(ALIASES, key=len, reverse=True)) + r")(?![\w-])")
             if ALIASES else None)


def merge_entities(text):
    """Replace every alias in already basic_clean-ed text by its canonical token (longest alias first, whole words only)."""
    return _ALIAS_RE.sub(lambda m: ALIASES[m.group(1)], text) if _ALIAS_RE else text


def _lemma_word(w):
    """Singular of one plain word (no prefix, no hyphen). Regular plural patterns only, checked against WordNet nouns (see LEMMATIZE)."""
    if w in LEMMA_IRREGULAR:
        return LEMMA_IRREGULAR[w]
    if w in LEMMA_KEEP or not w.isalpha() or len(w) < 4 or not w.endswith("s") or w.endswith(("ss", "us", "is", "omics")):
        return w
    if not _WNL:
        try:
            from nltk.corpus import wordnet
            from nltk.stem import WordNetLemmatizer
            wordnet.ensure_loaded()
        except (ImportError, LookupError) as err:
            raise RuntimeError("Lemmatization needs NLTK with WordNet data: pip install nltk; python -m nltk.downloader wordnet") from err
        _WNL.append((WordNetLemmatizer(), wordnet))
    _, wn = _WNL[0]
    noun = lambda x: bool(wn.synsets(x, pos="n"))
    if w.endswith("ies") and noun(w[:-3] + "y"):
        return w[:-3] + "y"                      # studies -> study
    if noun(w[:-1]):
        return w[:-1]                            # oils -> oil, doses -> dose, uses -> use
    if w.endswith("es") and w[:-2].endswith(("s", "x", "z", "ch", "sh", "o")) and noun(w[:-2]):
        return w[:-2]                            # boxes -> box, potatoes -> potato
    if wn.synsets(w):
        return w                                 # a known word that is not a regular plural (proves, believes, news): unchanged
    if w.endswith("ies"):
        return w[:-3] + "y"                      # unknown: comorbidities -> comorbidity
    return w[:-1]                                # unknown: carbs -> carb, pufas -> pufa, rcts -> rct


def lemmatize_token(t):
    """Plural -> singular for one counting token: keeps a 'no_' marker, changes only the last part of a hyphenated term, leaves stop words alone."""
    if t in _LEMMA_CACHE:
        return _LEMMA_CACHE[t]
    pre, w = ("no_", t[3:]) if t.startswith("no_") else ("", t)
    if w in _stopwords():
        out = t
    elif "-" in w:
        head, _, last = w.rpartition("-")
        last = last[:-1] if re.fullmatch(r"\d+s", last) else _lemma_word(last)  # omega-3s -> omega-3
        out = pre + head + "-" + last
        canon = set(ALIASES.values())
        if w in canon and (head + "-" + last) not in canon:  # a merged name stays whole (ancel-keys); merged plurals join their singular (seed-oils -> seed-oil)
            out = t
    else:
        out = pre + _lemma_word(w)
    _LEMMA_CACHE[t] = out
    return out


def _merge_tokens(tokens):
    """Apply the hand-merged names inside each stretch of words between punctuation (names never span punctuation)."""
    out, seg = [], []
    for x in tokens + ["."]:
        if x in _PUNCT:
            if seg:
                out += merge_entities(" ".join(seg)).split()
            out.append(x)
            seg = []
        else:
            seg.append(x)
    return out[:-1]


def bertopic_clean(doc):
    """The text clean-up used wherever WORDS ARE COUNTED (HyphenBERTopic topic words, seso_topics relabel, newcomer terms, k-sweep coherence),
    in this order: lowercase + tokens (_tokens) -> hand-merged names and terms -> negation marking -> punctuation dropped -> plural nouns to singular.
    Embeddings and emotion models never see this: they read the original text."""
    words = mark_negation(_merge_tokens(_tokens(doc)))
    if LEMMATIZE:
        words = [lemmatize_token(w) for w in words]
    doc = " ".join(words)
    return doc if doc else "emptydoc"


def hyphen_bertopic():
    """Return the BERTopic subclass (imported lazily so scripts without BERTopic can still import this module)."""
    from bertopic import BERTopic
    if not hasattr(BERTopic, "_preprocess_text"):
        raise RuntimeError("This BERTopic version has no _preprocess_text; check how it cleans text before relying on HyphenBERTopic.")

    class HyphenBERTopic(BERTopic):
        def _preprocess_text(self, documents):
            return [bertopic_clean(str(d)) for d in documents]

    return HyphenBERTopic


def _check_aliases(n_examples=3):
    """How many documents each alias matches, with a few short matches in context, so each alias can be checked by reading."""
    import random
    import pandas as pd
    rng = random.Random(0)
    for pfx in ("seso", "scinut"):
        f = Path(__file__).resolve().parents[1] / "data" / "processed" / f"{pfx}_docs.csv.gz"
        if not f.exists():
            print(f"missing {f} (run on the machine that has the data)"); continue
        texts = [basic_clean(t) for t in pd.read_csv(f, usecols=["text"], keep_default_na=False).text.astype(str)]
        print(f"\n=== {pfx}: {len(texts):,} documents")
        for canon in sorted(set(ALIASES.values())):
            total = 0
            for alias in sorted((a for a, c in ALIASES.items() if c == canon), key=len, reverse=True):
                rx = re.compile(r"(?<![\w-])" + re.escape(alias) + r"(?![\w-])")
                hits = [t for t in texts if rx.search(t)]; total += len(hits)
                print(f"  {canon:<32} {alias!r:<34} {len(hits):>7,} docs")
                for t in rng.sample(hits, min(n_examples, len(hits))):
                    m = rx.search(t); print(f"      ...{t[max(0, m.start() - 50):m.end() + 50]}...")
            print(f"  {canon:<32} {'(all aliases)':<34} {total:>7,} doc matches\n")
    print("Contains Reddit text: read it here, do not commit or paste the output.")


def _check_negation(n=150, seed=7, name="negation_check.csv"):
    """Writes a sample of negated stretches for checking by reading: data/processed/negation_check.csv (Reddit text: gitignored).
    One row per document (random documents of r/StopEatingSeedOils that contain a negator): the original stretch around the first negator
    and the words it marked. Fill in 'correct' (y / n) and report the share correct as the precision of the marking."""
    import random
    import pandas as pd
    f = Path(__file__).resolve().parents[1] / "data" / "processed" / "seso_docs.csv.gz"
    if not f.exists():
        print(f"missing {f} (run on the machine that has the data)"); return
    texts = pd.read_csv(f, usecols=["text"], keep_default_na=False).text.astype(str).tolist()
    rng = random.Random(seed); rng.shuffle(texts); rows = []
    for t in texts:
        toks = _merge_tokens(_tokens(t))
        k = next((i for i, x in enumerate(toks) if x in NEGATORS), None)
        if k is None:
            continue
        lo = max(0, k - 6); hi = min(len(toks), k + 12)
        stretch = toks[lo:hi]; marked = [x for x in mark_negation(toks[lo:hi]) if x.startswith("no_")]
        rows.append({"item": len(rows) + 1, "stretch": " ".join(stretch), "negator": toks[k], "marked": " ".join(marked), "correct": "", "note": ""})
        if len(rows) == n:
            break
    out = f.with_name(name); pd.DataFrame(rows).to_csv(out, index=False)
    print(f"wrote {len(rows)} items to {out}; first 15:")
    for r in rows[:15]:
        print(f"  [{r['negator']}] {r['stretch']}\n      -> {r['marked'] or '(nothing marked)'}")
    print("Contains Reddit text: do not commit or paste.")


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "aliases":
    _check_aliases()
elif __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "negation":
    # python seedoil_common.py negation [n seed file]: e.g.  negation 100 8 negation_check_v2.csv  (fresh test sample for the revised rules)
    a = sys.argv[2:]; _check_negation(*( [int(a[0]), int(a[1]), a[2]] if len(a) == 3 else []))
elif __name__ == "__main__":
    # List the accounts the bot rule removes, with their number of comments, so false positives (a human called '...bot') can be spotted.
    import glob
    import gzip
    import json
    from collections import Counter
    n = Counter()
    for f in sorted(glob.glob("seedoils/data/raw/*_comments.jsonl.gz")) + sorted(glob.glob("seedoils/data/raw/*_posts.jsonl.gz")):
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            for line in fh:
                try:
                    a = json.loads(line).get("author")
                except ValueError:
                    continue
                if is_bot(a):
                    n[a] += 1
    if not n:
        print("no raw files found under seedoils/data/raw/ (run from the repo root on the machine that has the data)")
    for a, c in n.most_common():
        print(f"{c:>8,}  {a}")
