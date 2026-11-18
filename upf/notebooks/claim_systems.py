"""CLAIM SYSTEMS in marketing copy (exploratory, upf/PLAN.md 18 Nov). Same category-balanced listings as the word plot.
Free-from claims are found by NEGATION, not by a word list: a content word within the scope of a VADER negator (Hutto & Gilbert 2014; next 3 words, stops at punctuation),
or an 'X-free' compound, or 'free of/from X'. Other systems = the word network's Louvain communities (word_network.py): a listing uses a system if it uses >= 2 of its words
outside a negation scope. Output: share of NOVA 1 / 3 / 4 listings using each system; combinations of systems (UpSet-style); most common free-from targets.
Writes upf/figures/claim_systems.png, soj/claim_systems.csv, data/processed/claim_systems.txt.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python upf/notebooks/claim_systems.py
"""
import re
from collections import Counter
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

PROC = Path("upf/data/processed"); C = PROC / "soj"; log = []
def say(s=""): print(s, flush=True); log.append(s)
NEG = {"aint", "arent", "cannot", "cant", "couldnt", "darent", "didnt", "doesnt", "dont", "hadnt", "hasnt", "havent", "isnt", "mightnt", "mustnt", "neither", "neednt", "never", "none",
       "nope", "nor", "not", "nothing", "nowhere", "oughtnt", "shant", "shouldnt", "wasnt", "werent", "without", "wont", "wouldnt", "rarely", "seldom", "despite", "no", "nobody"}  # VADER NEGATE
P = pd.read_csv(C / "products.csv.gz", usecols=["parent_asin", "nova", "category"])
M = pd.read_csv(PROC / "amazon_meta_compact.csv.gz", usecols=["parent_asin", "features", "description"]).drop_duplicates("parent_asin")
D = P.merge(M, on="parent_asin"); D["text"] = (D.features.fillna("") + " " + D.description.fillna("")).str.strip()
D = D[D.text.str.split().str.len() >= 10]; D["u"] = D.nova == 4
c = D.groupby("category").u.agg(["sum", "size"]); cats = c[(c["sum"] >= 100) & (c["size"] - c["sum"] >= 100)].index
rng = np.random.default_rng(31); parts = []
for k in cats:
    s = D[D.category == k]; n = min(int(s.u.sum()), int((~s.u).sum()))
    parts += [s[s.u].sample(n, random_state=int(rng.integers(1e9))), s[~s.u].sample(n, random_state=int(rng.integers(1e9)))]
B = pd.concat(parts).reset_index(drop=True)
N = pd.read_csv(C / "word_nodes.csv")
SYS = {2: "Certification & sourcing", 6: "Heritage & freshness", 3: "Brand values", 1: "Pleasure, convenience\n& nutrition panel"}
words = {c: set(N.word[N.community == c]) for c in SYS}
STOP = set(ENGLISH_STOP_WORDS) | {"artificial", "added", "any", "s"}                         # 'artificial'/'added' are modifiers: target is the next word
TOK = re.compile(r"[a-z]+(?:-free)?|[.,;:!?()•]")
use = {nm: np.zeros(len(B), bool) for nm in ["Free-from claims"] + list(SYS.values())}; targets = Counter(); tgt_side = Counter()
for r, t in enumerate(B.text.str.lower()):
    toks = TOK.findall(t); scope = 0; plain = []; ff = False
    for k, x in enumerate(toks):
        if x in ".,;:!?()•": scope = 0; continue
        if x.endswith("-free"): ff = True; targets[x[:-5]] += 1; tgt_side[(x[:-5], B.u[r])] += 1; continue
        if x == "free" and k + 2 < len(toks) and toks[k + 1] in ("of", "from") and toks[k + 2] not in STOP: ff = True; targets[toks[k + 2]] += 1; tgt_side[(toks[k + 2], B.u[r])] += 1
        if x in NEG: scope = 3; continue
        if scope > 0:
            if x not in STOP and len(x) > 2: ff = True; targets[x] += 1; tgt_side[(x, B.u[r])] += 1; scope = 0
            else: scope -= 1
            continue
        plain.append(x)
    use["Free-from claims"][r] = ff; ps = set(plain)
    for cc, nm in SYS.items(): use[nm][r] = len(ps & words[cc]) >= 2
U = pd.DataFrame(use); U["nova"] = B.nova.values; U["u"] = B.u.values
say(f"listings {len(B):,}: NOVA 1 {np.mean(B.nova == 1):.0%}, NOVA 2 {np.mean(B.nova == 2):.1%}, NOVA 3 {np.mean(B.nova == 3):.0%}, NOVA 4 {np.mean(B.nova == 4):.0%}")
names = list(use)
T = pd.DataFrame({g: U[U.nova == g][names].mean() for g in (1, 3, 4)}); T.columns = ["NOVA 1", "NOVA 3", "NOVA 4"]
say("share of listings using each system:\n" + (100 * T).round(1).to_string())
say("\nmost common free-from targets (listings): " + ", ".join(f"{w} {n}" for w, n in targets.most_common(25)))
U.to_csv(C / "claim_systems.csv", index=False)
combo = U[names].apply(lambda r: tuple(r.values), axis=1); cnt = combo.value_counts(); up = combo.map(dict(zip(cnt.index, U.groupby(combo).u.mean().reindex(cnt.index).values)))
top = [c_ for c_ in cnt.index if sum(c_) > 0][:12]
say("\ntop combinations (share of listings, share ultra-processed):")
for c_ in top: say(f"  {' + '.join(n.replace(chr(10), ' ') for n, b in zip(names, c_) if b):75s} {cnt[c_] / len(U):.1%}  UPF {U.u[combo == c_].mean():.0%}")
say(f"  (none of these) {cnt.get(tuple([False] * len(names)), 0) / len(U):.1%}  UPF {U.u[combo == tuple([False] * len(names))].mean():.0%}")

# ---- figure
fig = plt.figure(figsize=(13.5, 7.6)); a1 = fig.add_axes([0.2, 0.36, 0.28, 0.52]); a2 = fig.add_axes([0.6, 0.48, 0.38, 0.4]); a3 = fig.add_axes([0.6, 0.12, 0.38, 0.32], sharex=a2)
COL = {"NOVA 1": "#1d5fae", "NOVA 3": "#7fa9dc", "NOVA 4": "#eb6834"}; y = np.arange(len(names))[::-1]
for yi, nm in zip(y, names):
    r = T.loc[nm]; a1.plot([100 * r.min(), 100 * r.max()], [yi, yi], color="#d3d1c7", lw=2, zorder=1)
    for g, col in COL.items(): a1.scatter(100 * r[g], yi, s=70, color=col, edgecolor="white", zorder=3, label=g if yi == y[0] else None)
a1.set_yticks(y, names, fontsize=9); a1.tick_params(axis="y", length=0); a1.set_xlabel("share of listings using it", fontsize=8.5)
a1.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0f}%")); a1.tick_params(axis="x", labelsize=8)
for s_ in ("top", "right", "left"): a1.spines[s_].set_visible(False)
a1.grid(axis="x", color="#e6e8e1", lw=0.6); a1.set_axisbelow(True); a1.legend(frameon=False, fontsize=8, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, handletextpad=0.2)
a1.set_title("Who uses each claim system", loc="left", fontsize=11, pad=24)
x = np.arange(len(top)); h = [cnt[c_] / len(U) * 100 for c_ in top]; ups = [U.u[combo == c_].mean() for c_ in top]
from matplotlib.colors import LinearSegmentedColormap; cm = LinearSegmentedColormap.from_list("d", ["#2a78d6", "#d3d1c7", "#eb6834"])
a2.bar(x, h, color=[cm(u_) for u_ in ups], width=0.65)
for xi, hi, u_ in zip(x, h, ups): a2.text(xi, hi + 0.3, f"{u_:.0%}\nUPF", ha="center", va="bottom", fontsize=6.8, color="#444441", linespacing=0.95)
a2.set_ylim(0, max(h) * 1.22); a2.set_ylabel("% of listings", fontsize=8.5); a2.tick_params(labelsize=8, labelbottom=False); [a2.spines[s_].set_visible(False) for s_ in ("top", "right")]
a2.set_title("Which claims are stacked together (most common combinations)", loc="left", fontsize=11)
for k, nm in enumerate(names):
    yy = len(names) - 1 - k; a3.scatter(x, [yy] * len(x), s=34, color="#e1e0d9", zorder=1)
    on = [xi for xi, c_ in zip(x, top) if c_[k]]; a3.scatter(on, [yy] * len(on), s=46, color="#2c2c2a", zorder=2)
for xi, c_ in zip(x, top):
    ys = [len(names) - 1 - k for k, b in enumerate(c_) if b]
    if len(ys) > 1: a3.plot([xi, xi], [min(ys), max(ys)], color="#2c2c2a", lw=1.5, zorder=1)
a3.set_yticks(range(len(names)), [n.replace("\n", " ") for n in names[::-1]], fontsize=7.8); a3.set_xticks([]); a3.set_ylim(-0.6, len(names) - 0.4)
for s_ in a3.spines.values(): s_.set_visible(False)
a3.tick_params(axis="y", length=0)
tg = [w for w, _ in targets.most_common(30) if w not in ("high", "use", "matter", "ingredients", "compromising")][:16]
fig.text(0.2, 0.25, "Most common free-from targets:\n" + ", ".join(tg[:8]) + ",\n" + ", ".join(tg[8:]) + "\n('high' = high-fructose corn syrup; 'guilt' = guilt-free)", fontsize=8.5, color="#2c2c2a", va="top")
fig.text(0.01, 0.965, "Free-from claims are everywhere; certification is what sets less processed food apart", fontsize=13)
fig.text(0.01, 0.015, "20,698 Amazon grocery listings, equal numbers of ultra-processed (NOVA 4) and less processed (NOVA 1-3) in each of 25 food categories (NOVA 2 is under 1% and not shown).\n"
         "Free-from claims are found by negation, not a word list: a word after no / not / never / without (VADER negator list, 3-word scope), an 'X-free' compound, or 'free of/from X'.\n"
         "The other systems are word communities from the marketing word network; a listing uses one if it has at least 2 of its words outside a negation.\n"
         "Bars: % of all listings with exactly that combination; colour and label = share of them that are ultra-processed. Descriptive.", fontsize=7.4, color="#5f5e5a")
fig.savefig("upf/figures/claim_systems.png", dpi=170); (PROC / "claim_systems.txt").write_text("\n".join(log) + "\n"); print("saved")
