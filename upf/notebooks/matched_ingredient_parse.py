"""Parse the ingredient list TEXT of the matched products into individual ingredients (one row per product x ingredient).
Run from final_project/:  ./.venv-nlp/bin/python upf/notebooks/matched_ingredient_parse.py
Input: soj/matched_ingredients_raw.csv.gz (matched_ingredients_extract.py). Output: soj/matched_ingredients_long.csv.gz (code13, nova, ingredient).
Rules:
 - brackets [] {} are read as (); the list is split at top-level commas / semicolons / full stops / colons;
 - COMPOUND ingredients 'X (a, b, c)' (2+ items inside) are replaced by their sub-ingredients (most specific level, recursively);
   a single item in brackets is a clarification: kept as the inner item if X is a function word ('preservative (sodium benzoate)'), else X is kept ('tocopherols (vitamin e)');
 - parsing STOPS at an allergen / facility statement ('contains: milk', 'may contain', 'manufactured in'); 'contains 2% or less of:' headers are dropped, not stops;
 - cleaned: percentages, numbers, footnote marks, 'organic', 'non-gmo', 'for freshness'-type purpose phrases, leading 'and'/'or'; British spellings -> US;
 - items longer than 6 words or 50 characters are dropped (sentences, not ingredients);
 - plural merge: 'x' and 'xs'/'xes' that both occur are merged into the more common form.
"""
import re
from pathlib import Path
import pandas as pd

SOJ = Path("upf/data/processed/soj")
D = pd.read_csv(SOJ / "matched_ingredients_raw.csv.gz", dtype=str)

FUNCTION = {"preservative", "preservatives", "emulsifier", "emulsifiers", "color", "colors", "colour", "colours", "coloring", "acidity regulator", "acidity regulators",
            "antioxidant", "antioxidants", "thickener", "thickeners", "stabilizer", "stabilizers", "stabiliser", "acidulant", "acidulants", "sweetener", "sweeteners",
            "raising agent", "raising agents", "leavening", "leavening agent", "leavening agents", "firming agent", "anticaking agent", "anti-caking agent", "humectant",
            "gelling agent", "flavor enhancer", "flavour enhancer", "glazing agent", "acid", "acidifier", "artificial color", "artificial colors", "dough conditioner",
            "dough conditioners", "vitamins", "minerals", "vitamins and minerals", "spices", "spice", "seasoning", "seasonings", "flavoring", "flavorings", "natural flavor",
            "natural flavors", "artificial flavor", "artificial flavors", "a preservative", "an emulsifier", "colour added", "color added", "added color"}
# words dropped when they stand ALONE (a function class with no substance named); spices / flavors / vitamins are kept as ingredients
CLASS_ONLY = {"preservative", "preservatives", "emulsifier", "emulsifiers", "color", "colors", "coloring", "acidity regulator", "acidity regulators", "antioxidant", "antioxidants",
              "thickener", "thickeners", "stabilizer", "stabilizers", "acidulant", "acidulants", "sweetener", "sweeteners", "raising agent", "raising agents", "leavening agent",
              "leavening agents", "firming agent", "anticaking agent", "anti-caking agent", "humectant", "gelling agent", "flavor enhancer", "glazing agent", "acid", "acidifier",
              "a preservative", "an emulsifier", "dried", "added", "blend", "vitamins and minerals", "minerals", "vitamins/minerals", "preserved with",
              "for thickening", "phenylketonurics", "color added", "added color", "artificial color", "artificial colors", "colors added"}
OILSEED = {"canola", "sunflower", "safflower", "soybean", "cottonseed", "palm", "coconut", "olive", "peanut", "rapeseed", "palm kernel", "high oleic sunflower",
           "high oleic safflower", "high oleic canola", "expeller pressed canola", "expeller pressed sunflower"}
SYN = {"thiamin mononitrate": "thiamine mononitrate", "thiamin": "thiamine", "natural flavor": "natural flavors", "natural flavoring": "natural flavors",
       "natural flavorings": "natural flavors", "natural and artificial flavor": "natural and artificial flavors", "artificial flavor": "artificial flavors",
       "mono- and diglycerides": "mono and diglycerides", "monoglycerides and diglycerides": "mono and diglycerides", "baking soda": "sodium bicarbonate",
       "bicarbonate of soda": "sodium bicarbonate", "vitamin c": "ascorbic acid", "msg": "monosodium glutamate", "evaporated cane juice": "evaporated cane juice",
       "spice": "spices", "folate": "folic acid", "cornstarch": "corn starch", "modified cornstarch": "modified corn starch",
       "food starch-modified": "modified food starch", "food starch modified": "modified food starch", "mono - and diglycerides": "mono and diglycerides",
       "mono-and diglycerides": "mono and diglycerides", "confectioner s glaze": "confectioners glaze", "milkfat": "milk fat", "gum acacia": "gum arabic",
       "carob bean gum": "locust bean gum", "red lake": "red 40 lake", "yellow lake": "yellow 5 lake", "blue lake": "blue 1 lake", "flavoring": "flavor"}
STOP = re.compile(r"^(contains?\b(?!\s+(less|\d|one|two|three|no more|not more)))|^may contain|^manufactured|^made in a|^produced in|^processed in|^packed in a|^allergen|^this product|"
                  r"^keep |^store |^leep |^distributed|^product of|^best before|^refrigerate")
HEADER = re.compile(r"^(contains?|and|with)?\s*(less than|\d+\s*%?\s*or less|no more than|not more than|one or more|two percent|2 percent)\b.*")
PURPOSE = re.compile(r"\b(for|to)\s+(freshness|preserve|retain|maintain|protect|promote|prevent|keep|help|ensure|add|enhance|color|flavor|tartness|leavening|thicken)\b.*$|"
                     r"\s+-\s+(an?|the)\s.*$|\s+-\s+(emulsifier|preservative|color|antioxidant).*$")
DROPWORDS = re.compile(r"\b(pure|organic|organically grown|non-gmo|non gmo|gmo-free|gmo free|certified|kosher|all natural|100%|fair trade certified|fair trade|ingredients?)\b")
UKUS = [("flavour", "flavor"), ("colour", "color"), ("fibre", "fiber"), ("yoghurt", "yogurt"), ("sulphate", "sulfate"), ("sulphite", "sulfite"), ("stabiliser", "stabilizer")]


def split_top(s):
    """split at top-level separators; returns list of (head, inner_text or None)."""
    out, depth, cur = [], 0, []
    for ch in s:
        if ch == "(": depth += 1
        elif ch == ")": depth = max(0, depth - 1)
        if depth == 0 and ch in ",;:" or (depth == 0 and ch == "." and True):
            out.append("".join(cur)); cur = []
        else:
            cur.append(ch)
    out.append("".join(cur))
    return [x for x in out if x.strip()]


SEEDS = OILSEED | {"corn", "cottonseed", "rice bran", "avocado", "sesame", "soy", "palm fruit", "partially hydrogenated soybean", "hydrogenated palm kernel"}
DIGITS = lambda d: "".join(chr(65 + int(c)) for c in d)                  # digits -> UPPERCASE letters (text is lowercase), restored after number stripping


def clean(x):
    x = re.sub(r"\(.*?\)", " ", x)                                      # leftover brackets
    x = re.sub(r"[*†‡^~_\"'`]+", " ", x)
    x = re.sub(r"\bfd\s*&\s*c\b", " ", x)                                # FD&C Red No. 40 -> red 40
    # numbers that are part of a name are spelled out before other numbers are stripped: 'red no. 40' -> 'red 40', 'vitamin b12' -> 'vitamin b12'
    x = re.sub(r"\b(red|yellow|blue|green)\s*(?:no\.?|#)?\s*(\d+)", lambda m: f"{m.group(1)} {DIGITS(m.group(2))}", x)
    x = re.sub(r"\bvitamin\s*(b|d|k)\s*(\d+)", lambda m: f"vitamin {m.group(1)}{DIGITS(m.group(2))}", x)
    x = re.sub(r"\d+(\.\d+)?\s*%?", " ", x); x = x.replace("%", " ")
    x = re.sub(r"[A-J]+", lambda m: "".join(str(ord(c) - 65) for c in m.group(0)), x)
    for a, b in UKUS: x = x.replace(a, b)
    x = PURPOSE.sub("", x); x = DROPWORDS.sub(" ", x)
    x = re.sub(r"[^a-z0-9 \-/&]", " ", x); x = re.sub(r"\s+", " ", x).strip(" -/&")
    x = re.sub(r"^((and|or|&|with|of|contains?|includes?|preserved with)\s+)+", "", x); x = re.sub(r"\s+(and|or|added)\s*$", "", x)
    x = x.replace(" & ", " and ")
    if not x or len(x) > 60 or len(x.split()) > 8 or len(x) < 2: return None
    return SYN.get(x, x)


def leaves(s, out, depth=0, oil=False):
    """append the most specific ingredients of list text s to out; return False if a STOP statement was hit."""
    for item in split_top(s):
        item = item.strip()
        if STOP.match(item): return False
        if HEADER.match(item) and "(" not in item: continue
        m = re.match(r"^([^()]*)\((.*)\)\s*([^()]*)$", item)
        if m and depth < 4:
            head, inner, tail = m.group(1).strip(), m.group(2), m.group(3).strip()
            inner_items = split_top(inner)
            if len(inner_items) >= 2:
                leaves(inner, out, depth + 1, oil=bool(re.search(r"\boils?\b|shortening", head)))   # 'vegetable oil (canola, sunflower)
            else:
                h = clean(head)
                if h is None or h in FUNCTION or HEADER.match(head.strip()): leaves(inner, out, depth + 1)
                else: out.append(h)
            if re.match(r"^(and|&)\s+\w", tail): leaves(re.sub(r"^(and|&)\s+", "", tail), out, depth)   # 'ascorbic acid (vitamin c) and malic acid'
            continue
        c = clean(item)
        if oil and " or " in item and "(" not in item:                    # 'cottonseed or palm' inside an oil bracket
            leaves(re.sub(r"\s+or\s+", ",", item), out, depth, oil); continue
        if c and oil and c in SEEDS: c = c + " oil"
        if c and c not in CLASS_ONLY and not HEADER.match(c): out.append(c)
    return True


def parse(text):
    t = text.lower().replace("[", "(").replace("]", ")").replace("{", "(").replace("}", ")")
    t = re.sub(r"(\d)\.(\d)", r"\1\2", t); t = re.sub(r"\bno\.\s*(?=\d)", "no ", t)                                # 2.5% -> no stray full stop
    # 'canola, sunflower and/or safflower oil' -> canola oil, sunflower oil, safflower oil (only inside such a list, so 'organic coconut' stays coconut)
    def _oils(m):
        parts = [p.strip() for p in re.split(r",|\band/or\b|\bor\b|\band\b", m.group(0)) if p.strip()]
        return ", ".join(p if re.search(r"\boils?$", p) or len(p.split()) > 3 else p + " oil" for p in parts)
    seed = r"(?:(?:high oleic|expeller pressed|refined|fully hydrogenated|partially hydrogenated|hydrogenated)\s+)?(?:%s)" % "|".join(sorted(OILSEED | {"corn", "cottonseed", "rice bran", "avocado", "sesame"}, key=len, reverse=True))
    t = re.sub(rf"\b{seed}(?:\s*(?:,|\band/or\b|\bor\b|\band\b)\s*{seed})*\s*,?\s*(?:\band/or\b|\bor\b)\s+{seed}\s+oils?\b", _oils, t)
    t = t.replace("and/or", ",")
    # an inline 'contains 2% or less of:' header between two ingredients becomes a separator
    t = re.sub(r"\b(?:and\s+)?contains?\s+(?:less than\s+\d*\s*%?|\d+\s*%?\s*or less|one or more)(?:\s+of)?(?:\s+each)?(?:\s+of)?(?:\s+the following)?\s*[:\-]?", ", ", t)
    t = re.sub(r"\bless than\s+\d+\s*%?\s*(?:of)?\s*[:\-]", ", ", t)
    if t.count("(") != t.count(")"): t = t.replace("(", ",").replace(")", ",")   # unbalanced: flatten
    out = []; leaves(t, out)
    return list(dict.fromkeys(out))


if __name__ == "__main__":
    D["ings"] = D.ingredients_text.map(parse)
    L = D[["code13", "nova", "ings"]].explode("ings").dropna(subset=["ings"]).rename(columns={"ings": "ingredient"})
    vc = L.ingredient.value_counts()
    merge = {}
    for w, n in vc.items():
        for suf in ("s", "es"):
            if w.endswith(suf) and w[: -len(suf)] in vc.index and not w.endswith("ss"):
                s = w[: -len(suf)]; tgt = w if n > vc[s] else s; src = s if tgt == w else w; merge[src] = tgt; break
    L["ingredient"] = L.ingredient.replace(merge)
    # 'x and y' is split when x and y are each a common ingredient on their own (>= 50 products), so 'potassium sorbate and citric acid' splits
    # but 'natural and artificial flavors' / 'mono and diglycerides' / 'fruit and vegetable juice concentrate' do not
    vc = L.ingredient.value_counts(); common = set(vc[vc >= 50].index)
    # factored lists share a word across the 'and': 'disodium inosinate and guanylate' -> disodium inosinate, disodium guanylate;
    # 'palm and coconut oil' -> palm oil, coconut oil; 'hydrolyzed soy and corn protein' -> hydrolyzed soy protein, hydrolyzed corn protein
    KEEP = {"natural and artificial flavors", "artificial and natural flavors", "mono and diglycerides", "mono - and diglycerides of fatty acids", "live and active cultures",
            "fruit and vegetable juice", "fruit and vegetable juice concentrate", "natural and artificial flavor", "salt and vinegar seasoning", "macaroni and cheese"}
    def _split(w):
        if " and " not in w or w.count(" and ") > 1 or w in KEEP: return [w]
        p, q = [x.strip() for x in w.split(" and ")]
        pw, qw = p.split(), q.split()
        # shared-word readings first, so 'palm and coconut oil' gives 'palm oil' rather than a bare 'palm'
        cands = [(p + " " + qw[-1], q), (p, pw[0] + " " + q), (p + " " + qw[-1], pw[0] + " " + q), (p, q)] if pw and qw else []
        for a, b in cands:
            if a in common and b in common: return [a, b]
        return [w]
    L["ingredient"] = L.ingredient.map(_split); L = L.explode("ingredient")
    L = L.drop_duplicates(["code13", "ingredient"])
    L.to_csv(SOJ / "matched_ingredients_long.csv.gz", index=False)
    per = L.groupby("code13").size().reindex(D.code13, fill_value=0)
    vc = L.ingredient.value_counts()
    print(f"products {len(D):,}; with >= 1 parsed ingredient {(per > 0).sum():,}; median ingredients per product {int(per.median())}; plural merges {len(merge)}")
    print(f"distinct ingredient strings {len(vc):,}; in >= 50 products {(vc >= 50).sum():,}; >= 20 {(vc >= 20).sum():,}")
    print("top 40:", ", ".join(f"{w} {n}" for w, n in vc.head(40).items()))
