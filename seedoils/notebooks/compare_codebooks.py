"""Compare the codebook-v2 relabelling (position_codebook_v2.md; two steps: relevance, then H/NH/M/NP) with the original labels (comment_labels_part1-3.csv; H/NH/M/O).
Inputs: relabel outputs out_chunk1-4.csv (+ out_repeat.csv: 120 items labelled a second time with the same codebook), original labels, comments_key.csv. No Reddit text is used or written.
Mapping new -> old for comparison: relevant=0 or NP -> O; H, NH, M unchanged.
Outputs printed: confusion matrix, raw agreement, Cohen's kappa, agreement among items where both take a position, test-retest agreement of the new codebook, and the position shares for the Figure 4b rows (old vs new).
Run from final_project/:  python3 seedoils/notebooks/compare_codebooks.py <relabel_dir>
"""
import csv
import glob
import sys
from collections import Counter, defaultdict
from pathlib import Path

PROC = Path(__file__).resolve().parents[1] / "data" / "processed"
D = Path(sys.argv[1])


def read(path):
    return {r["item_id"]: r for r in csv.DictReader(open(path, encoding="utf-8"))}


def new_code(r):
    return "O" if r["relevant"].strip() == "0" or r["position"].strip() in ("NP", "NA", "") else r["position"].strip()


def kappa(pairs, labels):
    n = len(pairs)
    po = sum(a == b for a, b in pairs) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum(ca[l] * cb[l] for l in labels) / n / n
    return po, (po - pe) / (1 - pe) if pe < 1 else 1.0


new = {}
for f in sorted(glob.glob(str(D / "out_chunk*.csv"))):
    new.update(read(f))
old = {}
for f in sorted(glob.glob(str(PROC / "comment_labels_part*.csv"))):
    old.update(read(f))
key = {r["item_id"]: r for r in csv.DictReader(open(PROC / "comments_key.csv", encoding="utf-8"))}
ids = sorted(set(new) & set(old), key=int)
print(f"items: new {len(new)}, old {len(old)}, both {len(ids)}")
L = ["H", "NH", "M", "O"]
pairs = [(old[i]["position"], new_code(new[i])) for i in ids]
conf = Counter(pairs)
print("\nconfusion (rows = old label, columns = new label mapped to H/NH/M/O)")
print("        " + "".join(f"{l:>6}" for l in L) + "   total")
for a in L:
    print(f"  {a:<5} " + "".join(f"{conf[(a, b)]:>6}" for b in L) + f"   {sum(conf[(a, b)] for b in L):>5}")
po, k = kappa(pairs, L)
print(f"raw agreement {po:.3f}, Cohen's kappa {k:.3f}")
both = [(a, b) for a, b in pairs if a != "O" and b != "O"]
print(f"where both take a position (n={len(both)}): agreement {sum(a == b for a, b in both) / len(both):.3f}; H<->NH flips: {sum({a, b} == {'H', 'NH'} for a, b in both)}")
print("new relevance: relevant=1", sum(new[i]["relevant"].strip() == "1" for i in ids), " relevant=0", sum(new[i]["relevant"].strip() == "0" for i in ids),
      "| new NP", sum(new[i]["position"].strip() == "NP" for i in ids))
rep = read(D / "out_repeat.csv") if (D / "out_repeat.csv").exists() else {}
rid = [i for i in rep if i in new]
if rid:
    pr = [(new_code(new[i]), new_code(rep[i])) for i in rid]
    p2, k2 = kappa(pr, L)
    print(f"\nTEST-RETEST of the new codebook (same items, second independent agent, n={len(rid)}): agreement {p2:.3f}, kappa {k2:.3f}")
    rel = sum(new[i]["relevant"].strip() == rep[i]["relevant"].strip() for i in rid) / len(rid)
    print(f"  relevance agreement {rel:.3f}")
    po_old = [(old[i]["position"], new_code(rep[i])) for i in rid if i in old]
    print(f"  second pass vs OLD labels on the same items: agreement {kappa(po_old, L)[0]:.3f}, kappa {kappa(po_old, L)[1]:.3f}")
print("\nlow-confidence items: old", sum(old[i]["confidence"] == "low" for i in ids), "new", sum(new[i]["confidence"].strip() == "low" for i in ids))
print("\nFigure 4b rows (opinion sample): share among position-takers, old -> new")
cells = defaultdict(lambda: {"old": Counter(), "new": Counter()})
for i in ids:
    k_ = key[i]
    if "opinion" not in k_["samples"]:
        continue
    c = (k_["side"], k_["period"])
    cells[c]["old"][old[i]["position"]] += 1
    cells[c]["new"][new_code(new[i])] += 1
for c in sorted(cells):
    def sh(cnt):
        t = cnt["H"] + cnt["NH"] + cnt["M"]
        return f"n_position={t:>3}  H {cnt['H'] / t * 100:3.0f}%  NH {cnt['NH'] / t * 100:3.0f}%  M {cnt['M'] / t * 100:3.0f}%  (O/NP/off {sum(cnt.values()) - t})" if t else "n/a"
    print(f"  {c[0]:<20} {c[1]:<9} old: {sh(cells[c]['old'])}\n  {'':<31} new: {sh(cells[c]['new'])}")
