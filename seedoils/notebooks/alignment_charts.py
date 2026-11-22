"""Charts for the online-vs-science alignment result (static PNGs for the paper).

Run from final_project/ after alignment.py's inputs exist:
  ../.venv/bin/python seedoils/notebooks/alignment_charts.py
  -> seedoils/figures/science_by_evidence.png, online_positions.png, matching_evidence.png

Encoding (one visual language across the three charts): harm / 'harmful' = red, benefit / 'not harmful' = blue (diverging pair),
mixed and no effect / no position = neutral greys between them. Evidence types use the first four slots of the reference categorical
palette (validated: all checks pass on light; two slots are below 3:1 contrast, so every segment carries a direct label and a legend).
100% stacked horizontal bars, 2 px surface gaps between segments, n shown per row, labels inside segments when the share is >= 6%.
Labels are blind LLM annotations (see seedoils/PLAN.md); the science bars describe the papers Reddit cites, not the whole literature.
"""
import csv
import sys
import textwrap
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from alignment import evidence_type  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROC, FIG = ROOT / "data" / "processed", ROOT / "figures"
SURFACE, INK, INK2 = "#fcfcfb", "#0b0b0b", "#52514e"
RED, BLUE = "#e34948", "#2a78d6"
GREY_MID, GREY_LIGHT = "#bdbcb6", "#e3e2dd"
# evidence types avoid red/blue (those mean harm/benefit in the other charts); order validated: worst adjacent CVD dE 9.1, normal 19.6
EVID = {"human trials / meta of trials": "#6250d6", "human observational": "#1baf7a", "animal / cell": "#eda100",
        "review / statement": "#e87ba4", "other": "#c9c8c2"}
EVID_LABEL = {"human trials / meta of trials": "human trials", "human observational": "human observational",
              "animal / cell": "animal / cell", "review / statement": "review", "other": "other"}
plt.rcParams.update({"font.family": "sans-serif", "font.size": 11, "text.color": INK, "axes.labelcolor": INK2,
                     "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE})


def load():
    papers = {}
    for f in ("paper_labels_omega6.csv", "paper_labels_satfat_rodent.csv", "paper_labels_ldl.csv"):
        for r in csv.DictReader(open(PROC / f, encoding="utf-8")):
            papers[r["openalex_id"]] = r
    key = {r["item_id"]: r for r in csv.DictReader(open(PROC / "comments_key.csv"))}
    lab = {}
    for i in (1, 2, 3):
        for r in csv.DictReader(open(PROC / f"comment_labels_part{i}.csv", encoding="utf-8")):
            lab[r["item_id"]] = r
    return papers, key, lab


def text_on(hex_color):
    r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    lum = 0.2126 * r ** 2.2 + 0.7152 * g ** 2.2 + 0.0722 * b ** 2.2
    return INK if lum > 0.32 else "#ffffff"


def stacked(ax, rows, cats, colors, title, note, labels=None):
    """rows: list of (label, Counter); cats: ordered category keys; colors: dict cat -> hex; labels: legend names (default = cats)."""
    labels = labels or {k: k for k in cats}
    for y, (label, c) in enumerate(rows):
        n = sum(c[k] for k in cats)
        left = 0.0
        for k in cats:
            w = c[k] / n if n else 0
            if w:
                ax.barh(y, w, left=left, height=0.62, color=colors[k], edgecolor=SURFACE, linewidth=2)
                if w >= 0.06:
                    ax.text(left + w / 2, y, f"{w:.0%}", ha="center", va="center", fontsize=10, color=text_on(colors[k]))
            left += w
        ax.text(1.01, y, f"n = {n}", va="center", fontsize=9.5, color=INK2)
    ax.set_yticks(range(len(rows)), [r[0] for r in rows], fontsize=10.5)
    ax.invert_yaxis()
    ax.set_xlim(0, 1)
    ax.set_xticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(axis="y", length=0, pad=8)
    fig = ax.figure
    fig.text(0.02, 0.965, title, fontsize=13, color=INK, ha="left", va="top")
    handles = [plt.Rectangle((0, 0), 1, 1, color=colors[k]) for k in cats]
    ax.legend(handles, [labels[k] for k in cats], ncol=len(cats), loc="lower left", bbox_to_anchor=(0, 1.02), frameon=False,
              fontsize=9.5, handlelength=1.1, handletextpad=0.4, columnspacing=1.2)
    fig.text(0.02, 0.015, "\n".join(textwrap.fill(p, 150) for p in note.split("\n")), fontsize=8.5, color=INK2, ha="left", va="bottom")


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    papers, key, lab = load()
    rel = [p for p in papers.values() if p["relevance"] in ("yes", "partly")]

    # 1. science
    dcats = ["harm", "mixed", "no effect", "benefit"]
    dmap = {"harm": "harm", "mixed": "mixed", "no_effect": "no effect", "benefit": "benefit"}
    dcol = {"harm": RED, "mixed": GREY_MID, "no effect": GREY_LIGHT, "benefit": BLUE}  # same greys as the online chart
    groups = [("Human trials & meta-analyses", lambda p: evidence_type(p) == "human trials / meta of trials"),
              ("Human studies of deaths & disease", lambda p: p["population"] == "humans" and p["outcome"] == "hard"),
              ("Human observational studies", lambda p: evidence_type(p) == "human observational"),
              ("Reviews & statements", lambda p: evidence_type(p) == "review / statement"),
              ("Animal & cell studies", lambda p: evidence_type(p) == "animal / cell")]
    rows = [(name, Counter(dmap[p["direction"]] for p in rel if f(p))) for name, f in groups]
    fig, ax = plt.subplots(figsize=(11, 4.2))
    stacked(ax, rows, dcats, dcol, "What the papers Reddit cites conclude about seed oils, by kind of evidence",
            f"{len(rel)} papers on seed oils / linoleic acid / polyunsaturated fat, from the four seed-oil communities of the co-citation network. "
            "Rows overlap (deaths & disease is a subset).\nConclusions labelled from abstracts by a blind LLM annotator. Cited papers, not a systematic sample of the literature.")
    fig.subplots_adjust(left=0.27, right=0.92, top=0.77, bottom=0.17)
    fig.savefig(FIG / "science_by_evidence.png", dpi=200)
    plt.close(fig)

    # 2. online
    pcats = ["harmful", "mixed", "no position", "not harmful"]
    pmap = {"H": "harmful", "M": "mixed", "O": "no position", "NH": "not harmful"}
    pcol = {"harmful": RED, "mixed": GREY_MID, "no position": GREY_LIGHT, "not harmful": BLUE}
    rows = []
    for s, short in (("StopEatingSeedOils", "r/StopEatingSeedOils"), ("ScientificNutrition", "r/ScientificNutrition")):
        for per, lab_per in (("pre2024", "before 2024"), ("from2024", "from 2024")):
            c = Counter(pmap[lab[i]["position"]] for i, k in key.items()
                        if "opinion" in k["samples"] and k["side"] == s and k["period"] == per and i in lab)
            rows.append((f"{short}, {lab_per}", c))
    fig, ax = plt.subplots(figsize=(11, 3.7))
    stacked(ax, rows, pcats, pcol, "What each community says: are seed oils harmful?",
            "Random comments mentioning seed oils, vegetable oils, canola, soybean oil, linoleic acid, omega-6 or PUFA (at least 15 words), 100 per row.\n"
            "Positions labelled by a blind LLM annotator that did not see the subreddit.")
    fig.subplots_adjust(left=0.27, right=0.92, top=0.75, bottom=0.19)
    fig.savefig(FIG / "online_positions.png", dpi=200)
    plt.close(fig)

    # 3. matching
    ecats = list(EVID)
    rows = []
    for pos, name in (("H", 'Comments saying "harmful"'), ("NH", 'Comments saying "not harmful"')):
        c, n_comments = Counter(), 0
        for i, k in key.items():
            if "citing" in k["samples"] and i in lab and lab[i]["position"] == pos:
                n_comments += 1
                for w in filter(None, k["cited_works"].split("|")):
                    if w in papers:
                        c[evidence_type(papers[w])] += 1
        rows.append((f"{name}\n({n_comments} comments)", c))
    fig, ax = plt.subplots(figsize=(11, 3.2))
    stacked(ax, rows, ecats, EVID, "What kind of evidence each side cites",
            "Comments from both subreddits that link at least one paper of the four seed-oil communities; n = papers cited (a paper counts once per comment).\n"
            "Evidence type from the paper labels (population and design). Human trials include meta-analyses of trials.", labels=EVID_LABEL)
    fig.subplots_adjust(left=0.27, right=0.92, top=0.68, bottom=0.22)
    fig.savefig(FIG / "matching_evidence.png", dpi=200)
    plt.close(fig)
    print("wrote", ", ".join(p.name for p in sorted(FIG.glob("*.png"))))


if __name__ == "__main__":
    main()
