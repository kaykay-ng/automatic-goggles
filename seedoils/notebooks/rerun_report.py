"""Builds seedoils/artifact/rerun_results.html: the results of the 22 Nov re-download and rerun, regenerated from whatever outputs exist.
Rerun after each step (it only reads files; nothing is recomputed):  ./.venv-nlp/bin/python seedoils/notebooks/rerun_report.py
Aggregates only: counts, shares, topic words and paper titles. No usernames, no comment text."""
import csv
import datetime as dt
import glob
import gzip
import html
import json
import subprocess
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from seedoil_common import is_bot, SPLIT_TS, SPLIT_TS_AUG2024, HISTORY_GLOB, THEMES_FILE

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC, OUT = ROOT / "data" / "raw", ROOT / "data" / "processed", ROOT / "artifact" / "rerun_results.html"
A_DIR = PROC / "artifact"
SPLIT = SPLIT_TS
OLD = {"StopEatingSeedOils_comments": 243097, "ScientificNutrition_comments": 177788, "StopEatingSeedOils_posts": 11642,
       "ScientificNutrition_posts": 14273, "carnivore_posts": 33266}
OLD_DOCS = {"seso": 149732, "scinut": 121672}
OLD_TOPICS = {"seso": 129, "scinut": 117}
N_AUTHORS = 2921
e = lambda x: html.escape(str(x))
mtime = lambda p: p.stat().st_mtime if p.exists() else 0
running = lambda pat: bool(subprocess.run(["pgrep", "-f", pat], capture_output=True, text=True).stdout.strip())


# ---------------------------------------------------------------- data
def raw_summary():
    rows, months = [], {"StopEatingSeedOils": Counter(), "ScientificNutrition": Counter()}
    for name, prev in OLD.items():
        f = RAW / f"{name}.jsonl.gz"
        if not f.exists():
            rows.append((name, None, prev, None, None)); continue
        n, lo, hi, sub = 0, 10 ** 11, 0, name.split("_")[0]
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            for line in fh:
                try:
                    x = json.loads(line)
                except ValueError:
                    continue
                t = int(x["created_utc"]); n += 1; lo, hi = min(lo, t), max(hi, t)
                if sub in months and not is_bot(x.get("author")):
                    months[sub][dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m")] += 1
        rows.append((name, n, prev, lo, hi))
    return rows, months


def author_progress():
    n = 0
    for f in glob.glob(str(RAW / HISTORY_GLOB)):
        try:
            with gzip.open(f, "rt") as fh:
                for _ in fh:
                    n += 1
        except (EOFError, OSError):
            pass
    return n


def status():
    """(step, state, detail); state in done / running / waiting / todo."""
    S = []
    dl_run = running("fetch_arctic_shift.py")
    S.append(("Reddit posts and comments", "running" if dl_run else ("done" if (RAW / "StopEatingSeedOils_comments.jsonl.gz").exists() else "todo"), "Arctic Shift, re-downloaded 22 Nov; r/carnivore comments dropped"))
    S.append(("Paper metadata", "done" if (RAW / "openalex_works.jsonl.gz").exists() else "todo", "cited-paper ids looked up in OpenAlex"))
    a = author_progress()
    S.append(("Author histories", "running" if running("fetch_author_histories.py fetch") else ("done" if a >= N_AUTHORS - 10 else "todo"), f"{a:,} of {N_AUTHORS:,} heavy commenters fetched (2 rejected by the API)"))
    S.append(("Documents and embeddings", "done" if (PROC / "scinut_vectors.npy").exists() else "todo", "comments of 15+ words, all-MiniLM-L6-v2"))
    S.append(("Topic models", "done" if mtime(PROC / "scinut_topics_info.csv") > mtime(PROC / "scinut_vectors.npy") else "todo", "BERTopic, both subreddits"))
    S.append(("Vote percentiles", "done" if mtime(PROC / "scinut_topic_votes.csv") > mtime(PROC / "scinut_doc_topics.csv.gz") else "todo", "rank of score within thread and level"))
    S.append(("Emotions (GoEmotions)", "done" if mtime(PROC / "goemo_scinut_short.npz") > mtime(PROC / "scinut_docs.csv.gz") else "todo", "all documents, both subreddits"))
    S.append(("Emoji (torchMoji, 256 tokens)", "done" if (PROC / "deepmoji_tm256_scinut_short.npz").exists() else "todo", "all documents, both subreddits"))
    S.append(("Corpus statistics", "done" if (PROC / "corpus_stats.json").exists() else "todo", "lengths, Zipf, Heaps, TF-IDF, PMI, concordance"))
    S.append(("Topic stability (5 seeds)", "running" if running("seso_topics_seeds.py") else ("done" if (PROC / "seso_seed_stability.json").exists() else "todo"), "UMAP seeds 42, 1-4; AMI and NMI"))
    S.append(("BERTopic vs LDA", "running" if running("lda_compare.py") else ("done" if (PROC / "lda_comparison.json").exists() else "todo"), "LDA K=123 (3 seeds) and K=30"))
    S.append(("Hand-picked themes", "waiting" if not (PROC / THEMES_FILE).exists() else "done", "your picks of topic ids per theme"))
    S.append(("Name list check", "done" if list(PROC.glob("alias_decisions_*.csv")) else "todo", "aliases checked by reading (check_aliases.html); omega 6 / omega 3 spellings merged"))
    facts = PROC / "artifact" / "facts.json"
    S.append(("Dashboard datasets", "done" if mtime(facts) > mtime(PROC / "diet_overlap.csv") else "todo", "artifact_data.py and chart-data scripts on the re-downloaded data"))
    S.append(("Negation check", "done" if (PROC / "negation_labels_v2_HY.csv").exists() else "todo", "absence claims only (no / without + noun phrase), 25 Nov"))
    S.append(("Hostility hand labels (150 comments)", "done" if (PROC / "hostility_eval.json").exists() else "todo", "3 labellers (HY, NP, KK); Fleiss kappa 0.70 on H vs not H"))
    S.insert(4, ("Commenter network and communities", "done" if (PROC / "commenter_topic_network_130_stats.json").exists() else "todo", "backbone, Louvain, outcomes"))
    S.insert(5, ("Network measures and community methods", "running" if running("network_stats.py") else ("done" if (PROC / "network_stats.json").exists() else "todo"), "degree, CCDF, clustering, k-clique, link communities"))
    S.insert(6, ("Reply network (all accounts)", "done" if (PROC / "reply_network_stats.json").exists() else "todo", "A -> B when A replies to B's post or comment"))
    S.insert(6, ("Co-citation networks", "done" if (PROC / "cocite_null_summary.txt").exists() else "todo", "scholarly and Reddit, with nulls"))
    S.insert(7, ("Community names", "done" if (PROC / "community_names.json").exists() else "waiting", "your names for the Louvain communities"))
    S.insert(4, ("Diet-community overlap", "done" if (PROC / "diet_overlap.csv").exists() else "todo", "22 pre-declared diet subreddits + borderline checks"))
    return S


# ---------------------------------------------------------------- charts
def line_chart(series, title, ylabel, fmt, height=240, shade_from="2024-01"):
    """series: {name: (color_token, {month: value})}. Inline SVG, months on x, linear y from 0."""
    months = sorted({m for _, d in series.values() for m in d})
    if not months:
        return ""
    W, H, L, R, T, B = 760, height, 52, 12, 14, 30
    ymax = max(v for _, d in series.values() for v in d.values()) * 1.08 or 1
    x = lambda i: L + i * (W - L - R) / max(1, len(months) - 1)
    y = lambda v: H - B - v / ymax * (H - T - B)
    parts = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{e(title)}">']
    if shade_from in months:
        i0 = months.index(shade_from)
        parts.append(f'<rect x="{x(i0):.1f}" y="{T}" width="{x(len(months) - 1) - x(i0):.1f}" height="{H - T - B}" fill="var(--shade)"/>')
    for k in range(5):
        v = ymax / 1.08 * k / 4; yy = y(v)
        parts.append(f'<line x1="{L}" x2="{W - R}" y1="{yy:.1f}" y2="{yy:.1f}" stroke="var(--grid)"/>'
                     f'<text x="{L - 6}" y="{yy + 4:.1f}" text-anchor="end" class="ax">{e(fmt(v))}</text>')
    for i, m in enumerate(months):
        if m.endswith("-01"):
            parts.append(f'<text x="{x(i):.1f}" y="{H - 10}" text-anchor="middle" class="ax">{m[:4]}</text>')
    for name, (col, d) in series.items():
        pts = " ".join(f"{x(i):.1f},{y(d[m]):.1f}" for i, m in enumerate(months) if m in d)
        parts.append(f'<polyline points="{pts}" fill="none" stroke="var({col})" stroke-width="2" stroke-linejoin="round"/>')
    parts.append(f'<text x="{L}" y="{T - 2}" class="ax">{e(ylabel)}</text></svg>')
    legend = "".join(f'<span><i style="background:var({c})"></i>{e(n)}</span>' for n, (c, _) in series.items())
    return f'<figure><figcaption>{e(title)}</figcaption><div class="legend">{legend}</div><div class="chart">{"".join(parts)}</div></figure>'


def loglog_chart(series, title, xlabel, ylabel, height=260):
    """series: {name: (color_token, [[x, y], ...])}, both axes log10, ticks at powers of ten."""
    import math
    pts = [p for _, s in series.values() for p in s if p[0] > 0 and p[1] > 0]
    if not pts:
        return ""
    W, H, L, R, T, B = 760, height, 58, 14, 34, 36
    x0, x1 = math.floor(math.log10(min(p[0] for p in pts))), math.ceil(math.log10(max(p[0] for p in pts)))
    y0, y1 = math.floor(math.log10(min(p[1] for p in pts))), math.ceil(math.log10(max(p[1] for p in pts)))
    X = lambda v: L + (math.log10(v) - x0) / max(1, x1 - x0) * (W - L - R)
    Y = lambda v: H - B - (math.log10(v) - y0) / max(1, y1 - y0) * (H - T - B)
    # 10^k drawn as "10" plus a raised, smaller exponent (tspan with dy), so it does not depend on the font having superscript characters
    sup = lambda k: f'10<tspan dy="-6" font-size="9">{"−" if k < 0 else ""}{abs(k)}</tspan>'
    parts = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{e(title)}">']
    for k in range(y0, y1 + 1):
        parts.append(f'<line x1="{L}" x2="{W - R}" y1="{Y(10 ** k):.1f}" y2="{Y(10 ** k):.1f}" stroke="var(--grid)"/><text x="{L - 10}" y="{Y(10 ** k) + 4:.1f}" text-anchor="end" class="ax">{sup(k)}</text>')
    for k in range(x0, x1 + 1):
        parts.append(f'<text x="{X(10 ** k):.1f}" y="{H - 18}" text-anchor="middle" class="ax">{sup(k)}</text>')
    for name, (col, s) in series.items():
        pl = " ".join(f"{X(a):.1f},{Y(b):.1f}" for a, b in s if a > 0 and b > 0)
        parts.append(f'<polyline points="{pl}" fill="none" stroke="var({col})" stroke-width="2" stroke-linejoin="round"/>')
    parts.append(f'<text x="{(L + W - R) / 2:.0f}" y="{H - 3}" text-anchor="middle" class="ax">{e(xlabel)}</text><text x="4" y="12" class="ax">{e(ylabel)}</text></svg>')
    legend = "".join(f'<span><i style="background:var({c})"></i>{e(n)}</span>' for n, (c, _) in series.items())
    return f'<figure><figcaption>{e(title)}</figcaption><div class="legend">{legend}</div><div class="chart">{"".join(parts)}</div></figure>'


def corpus_section():
    f = PROC / "corpus_stats.json"
    if not f.exists():
        return ""
    C = json.loads(f.read_text()); subs = list(C); col = lambda s: "--c1" if s.startswith("Stop") else "--c2"
    sec = ('<section id="corpus"><h2>Corpus statistics</h2><p>Lengths in words (split on spaces). Raw = as downloaded (removed, deleted and bot items dropped; link posts left out). '
           'Cleaned = after removing quoted parent text and links. Topic corpus = cleaned documents of 15+ words. Content tokens = what topic words are counted from: '
           'names merged, negations marked, stop words removed.</p>')
    rows = []
    for s in subs:
        for k, lab in (("comment", "Comments"), ("post", "Self-posts")):
            for stage, sl in (("raw", "Raw"), ("cleaned_all", "Cleaned"), ("topic_corpus", "Topic corpus (15+ words)"), ("content_tokens", "Content tokens")):
                d = C[s]["lengths"][k].get(stage)
                if d:
                    rows.append((f"r/{e(s)}", lab, sl, f"{d['n']:,}", f"{d['mean']:.1f}", f"{d['median']}", f"{d['p90']}"))
    sec += table(["Subreddit", "Type", "Stage", "Items", "Mean", "Median", "90th pct"], rows, num=(3, 4, 5, 6))
    sec += "<h3>Vocabulary (topic corpus, all tokens)</h3>" + table(
        ["Subreddit", "Tokens", "Types", "Type-token ratio", "Hapax (once)", "Share of types", "Dis legomena (twice)", "Zipf exponent s", "Heaps β"],
        [(f"r/{e(s)}", f"{C[s]['tokens']:,}", f"{C[s]['types']:,}", f"{C[s]['ttr']:.4f}", f"{C[s]['hapax']:,}", f"{C[s]['hapax'] / C[s]['types']:.0%}",
          f"{C[s]['dis_legomena']:,}", f"{C[s]['zipf']['s']:.2f}", f"{C[s]['heaps']['beta']:.2f}") for s in subs], num=(1, 2, 3, 4, 5, 6, 7, 8))
    sec += ('<p>Zipf: a word\'s frequency is proportional to its rank raised to the power −s, written <span class="math">f(r) ∝ r<sup>−s</sup></span>; s is the slope of a '
            "straight line fitted on the log–log plot over ranks 10 to 10,000 (s ≈ 1 is the classic value; above 1 means frequency falls off faster down the list). "
            'Heaps: vocabulary size V grows with the number of tokens N as <span class="math">V = K · N<sup>β</sup></span> (β below 1: new words keep appearing, '
            "but more and more slowly); documents added in time order.</p>")
    sec += loglog_chart({f"r/{s}": (col(s), C[s]["zipf"]["points"]) for s in subs}, "Zipf: word frequency by rank", "rank", "frequency")
    sec += loglog_chart({f"r/{s}": (col(s), C[s]["heaps"]["points"]) for s in subs}, "Heaps: vocabulary growth", "tokens read", "distinct words")
    for s in subs:
        r = C[s]; n = 15
        tw = [(str(i + 1), e(r["top_freq_all"][i][0]) if i < len(r["top_freq_all"]) else "", e(r["top_freq_content"][i][0]), e(r["top_tfidf"][i][0])) for i in range(n)]
        sec += f"<h3>r/{e(s)}: top words by raw frequency, after stop words, and by TF-IDF</h3>" + table(["Rank", "All tokens", "Content tokens", "Mean TF-IDF"], tw, num=(0,))
        pm = [(e(f"{a} {b}"), f"{p:.1f}", f"{c:,}") for a, b, p, c in r["pmi"][:12]]
        fb = [(e(f"{a} {b}"), f"{c:,}") for a, b, c in r["top_bigrams"][:12]]
        sec += (f'<div class="two"><div><h3>Collocations by PMI (pairs seen {r["pmi_min_count"]}+ times)</h3>' + table(["Pair", "PMI (bits)", "Count"], pm, num=(1, 2)) +
                '</div><div><h3>Most frequent pairs</h3>' + table(["Pair", "Count"], fb, num=(1,)) + "</div></div>")
        kw = [(e(t), f"{c['hits']:,}", e(", ".join(w for w, _ in c["left"][:6])), e(", ".join(w for w, _ in c["right"][:6]))) for t, c in r["concordance"].items()]
        sec += "<h3>Concordance: words just before and after key terms</h3>" + table(["Term", "Occurrences", "Most common word before", "Most common word after"], kw, num=(1,))
    sec += (f'<p class="note">The keyword-in-context lines themselves (25 per term) are Reddit text, so they stay in a local file and are not shown here: '
            f'<code>seedoils/data/processed/concordance_seso.txt</code> and <code>concordance_scinut.txt</code>.</p></section>')
    return sec


def stability_section():
    f = PROC / "seso_seed_stability.json"
    if not f.exists():
        return ""
    S = json.loads(f.read_text())
    sec = (f'<section id="stability"><h2>Topic model stability across seeds</h2><p>r/StopEatingSeedOils refitted with {S["n_runs"]} UMAP seeds ({", ".join(map(str, S["seeds"]))}), '
           'everything else unchanged. Agreement between two runs over the same documents: AMI (0 = chance, 1 = identical) and NMI for comparison; '
           '"confident" uses only documents HDBSCAN placed itself in both runs.</p>')
    sec += table(["Seed", "Topics", "Outliers before reassignment"], [(str(r["seed"]), str(r["topics"]), f"{r['outliers']:.0%}") for r in S["per_run"]], num=(0, 1, 2))
    sec += table(["Measure", f"Mean over {S['pairs']} pairs", "Lowest", "Highest"],
                 [(lab, f"{S[k]['mean']:.3f}", f"{S[k]['min']:.3f}", f"{S[k]['max']:.3f}") for k, lab in (("ami", "AMI, all documents"), ("nmi", "NMI, all documents"), ("ami_confident", "AMI, confident documents"))], num=(1, 2, 3))
    if "themes" in S:
        rows = [(e(th), " · ".join(f"{x['ratio']:.1f}" for x in v if x["ratio"]), f"{min(x['ratio'] for x in v if x['ratio']):.1f}–{max(x['ratio'] for x in v if x['ratio']):.1f}") for th, v in S["themes"].items()]
        sec += "<h3>Theme growth (share from 2024 ÷ before) in each run</h3>" + table(["Theme", "Per run", "Range"], rows, num=(2,))
    return sec + "</section>"


def network_section():
    st, cj, nj = PROC / "commenter_topic_network_130_stats.json", A_DIR / "commenter_network.json", A_DIR / "niche_network.json"
    if not st.exists():
        return ""
    from seedoil_common import community_labels
    S = json.loads(st.read_text()); C = json.loads(cj.read_text())["comms"] if cj.exists() else []
    long_, short = community_labels(len(C))
    sec = (f'<section id="network"><h2>Commenter network</h2><p>{S["n_users"]:,} r/StopEatingSeedOils commenters with 10+ topic comments, linked by how similar their topic '
           f'mixes are (cosine of topic profiles). The disparity filter (alpha 0.05) keeps {S["links_kept"]:,} of {S["links_full"]:,} links. Louvain over 20 seeds: modularity '
           f'{S["modularity_mean"]:.3f} ({S["modularity_min"]:.3f}–{S["modularity_max"]:.3f}), {S["communities"]} communities in the reference run, agreement between runs AMI '
           f'{S["ami_mean"]:.2f} (lowest {S["ami_min"]:.2f}). Names are written by hand from each community&#8217;s over-represented topics '
           f'(<code>community_names.json</code>; "Community k" until named).</p>')
    O = {r["c"]: r for r in json.loads(nj.read_text())["comms"]} if nj.exists() else {}
    ch = lambda r, a, b, lo, hi: (f'{r[a]} → {r[b]} <small>[{r[lo][0]:+}, {r[lo][1]:+}]</small>' if r.get(a) is not None and r.get(lo) and r[lo][0] is not None else "–")
    rows = [(f"C{c['id'] + 1}", e(long_[c["id"]]), f"{c['size']:,}", f"{c['long']}%", e("; ".join(t["w"] for t in c["topics"][:3])),
             ch(O.get(c["id"], {}), "h0", "h1", "hci", None) if O else "–", ch(O.get(c["id"], {}), "v0", "v1", "vci", None) if O else "–") for c in C]
    sec += table(["#", "Name", "People", "Long-time", "Talks more about", "Disapproving tone % before → from 2024 [95% CI of change]", "Downvoted % before → from 2024 [CI]"], rows, num=(2, 3))
    return sec + "</section>"


def netstats_section():
    f = PROC / "network_stats.json"
    if not f.exists():
        return ""
    N = json.loads(f.read_text()); b, d, c, p, a = N["basic"], N["degree"], N["clustering"], N["paths"], N["assortativity"]; pl = d["powerlaw"]
    sec = ('<section id="netstats"><h2>Network measures</h2><p>The same commenter backbone, unweighted unless stated. Null models: an Erdős–Rényi graph with the same '
           'density, and degree-preserving rewiring (double edge swaps, 10 networks) that keeps everyone&#8217;s number of links.</p>')
    sec += table(["Measure", "Value", "Reference"], [
        ("Nodes / links", f"{b['nodes']:,} / {b['edges']:,}", f"density {b['density']}"),
        ("Degree: mean / median / max", f"{b['mean_degree']} / {b['median_degree']} / {b['max_degree']}", f"SD {d['std']}; mean degree of a neighbour {d['friendship_paradox_mean_neighbour_degree']} (friendship paradox)"),
        ("Power-law fit of the degree tail", f"α = {pl['alpha']}, from k ≥ {pl['xmin']} ({pl['n_tail']:,} people)",
         f"vs lognormal R = {pl['vs_lognormal_R']} (p {pl['vs_lognormal_p']}); vs exponential R = {pl['vs_exponential_R']} (p {pl['vs_exponential_p']}); R &lt; 0 favours the alternative"),
        ("Average clustering", f"{c['average_local']}", f"Erdős–Rényi {c['er_expected']}; rewired {c['config_null_average'][0]} ± {c['config_null_average'][1]}"),
        ("Transitivity", f"{c['transitivity']}", f"rewired {c['config_null_transitivity'][0]} ± {c['config_null_transitivity'][1]}"),
        ("Average weighted clustering", f"{c['average_weighted']}", "link weights = topic similarity"),
        ("Average shortest path", f"{p['average']}", f"Erdős–Rényi ln n / ln ⟨k⟩ = {p['er_expected']}; longest seen {p['longest_seen']} (from {p['sources']} sources)"),
        ("Degree assortativity", f"{a['degree']}", f"rewired {a['degree_config_null'][0]} ± {a['degree_config_null'][1]}"),
        ("Assortativity by cohort (old guard / newcomer)", f"{a['cohort_old_new']}", f"shuffled labels {a['cohort_shuffle'][0]} ± {a['cohort_shuffle'][1]}"),
        ("Assortativity by Louvain community", f"{a['community']}", f"shuffled labels {a['community_shuffle'][0]} ± {a['community_shuffle'][1]}")], num=())
    sec += loglog_chart({"Observed": ("--c1", d["ccdf"]), "Poisson, same mean (Erdős–Rényi)": ("--c2", [x for x in d["ccdf_poisson_same_mean"] if x[1] > 0])},
                        "Degree CCDF: share of people with at least k links", "degree k", "P(K ≥ k)")
    sec += loglog_chart({"Observed": ("--c1", d["hist_logbinned"])}, "Degree distribution (log-binned)", "degree k", "p(k)")
    rho = N["centrality"]["spearman"]; keys = list(rho)
    sec += "<h3>Centralities: rank correlation (Spearman)</h3>" + table(["", *keys], [(k, *[f"{rho[k][j]:.2f}" for j in keys]) for k in keys], num=tuple(range(1, len(keys) + 1)))
    t = N["centrality"]["top30"]
    sec += (f'<p>Newcomers are {N["centrality"]["newcomer_share_all"]:.0%} of the network. Among the 30 most central people they are: '
            + "; ".join(f"{k} {v['newcomer_share']:.0%}" for k, v in t.items()) + ".</p>")
    rows = [(e(m["method"]), str(m["communities"]), str(m["largest"]), f"{m['coverage']:.0%}", f"{m['mean_memberships_covered']}" if m["mean_memberships_covered"] else "–",
             f"{m['share_in_exactly_one']:.0%}", f"{m['ami_vs_louvain_single']}" if m["ami_vs_louvain_single"] is not None else "–",
             f"{m.get('ami_vs_louvain_main', '–')}") for m in N["communities"]]
    sec += ('<h3>Community methods compared</h3><p>Louvain gives every person one community. k-clique percolation joins k-cliques sharing k−1 people; people in no '
            'k-clique stay outside, and people can sit in several. Link communities cluster links, not people (cut at the highest partition density), so a person '
            'belongs to every community their links fall in; "main" = the one holding most of their links. Agreement with Louvain is AMI over people with exactly one '
            'community, and for link communities also over everyone&#8217;s main community.</p>')
    sec += table(["Method", "Communities", "Largest", "People covered", "Communities per covered person", "In exactly one", "AMI vs Louvain (one)", "AMI vs Louvain (main)"], rows, num=(1, 2, 3, 4, 5, 6, 7))
    return sec + "</section>"


def cocite_section():
    f = PROC / "cocite_null_summary.txt"
    if not f.exists():
        return ""
    keep = [l for l in f.read_text().splitlines() if l.strip()]
    return ('<section id="cocite"><h2>Co-citation networks</h2><p>Papers cited by 2+ users. Scholarly network: papers linked when one cites the other (OpenAlex). '
            'Reddit network: papers linked when the same user cites both. Null 1 rewires links keeping each paper&#8217;s degree; null 2 shuffles which side cites a paper.</p>'
            f'<pre>{e(chr(10).join(keep))}</pre></section>')


def emoji_section():
    f, chk = A_DIR / "deepmoji.json", PROC / "torchmoji_check.txt"
    if not f.exists():
        return ""
    R = pd.DataFrame(json.loads(f.read_text())["rows"]); R["post"] = R.quarter >= "2024Q1"
    W = lambda g: (g.pct * g.n).sum() / g.n.sum()
    rows = []
    for (sub, grp), g in R.groupby(["subreddit", "group"]):
        a, b = W(g[~g.post]), W(g[g.post]); rows.append((e(sub), e(grp), e(g.emojis.iloc[0]), f"{a:.2f}%", f"{b:.2f}%", f"{b - a:+.2f}"))
    qm = lambda q: f"{q[:4]}-{(int(q[-1]) - 1) * 3 + 1:02d}"  # quarter -> its first month, for the time axis
    charts = ""
    for grp in ("Anger", "Skepticism"):
        ser = {s_: ("--c1" if "Stop" in s_ else "--c2", {qm(r.quarter): r.pct for r in g.itertuples()}) for s_, g in R[R.group == grp].groupby("subreddit")}
        charts += line_chart(ser, f"{grp} emojis per quarter (share of predicted emoji probability)", "% of emoji probability", lambda v: f"{v:.0f}%")
    sec = ('<section id="emoji"><h2>Emoji model (torchMoji)</h2><p>torchMoji (the DeepMoji model, trained on 1.2 billion tweets) predicts which of 64 emojis fits a text. '
           'Emojis are grouped into six families by hand (deepmoji_chart_data.py); value = the family&#8217;s share of the predicted emoji probability, averaged over documents '
           '(not a share of comments). Documents of 15+ words, read up to 256 tokens; quarters with fewer than 300 documents left out.</p>')
    sec += table(["Subreddit", "Emoji family", "Emojis", "Before 2024", "From 2024", "Change (points)"], rows, num=(3, 4, 5)) + charts
    if chk.exists():
        sec += ('<h3>30 or 256 tokens</h3><p>The model was trained on tweets with a 30-token limit. On 600 random comments the longer limit changes many predictions '
                'but does not make them blander, so all documents were scored at 256 tokens.</p>' + f"<pre>{e(chk.read_text().strip())}</pre>")
    return sec + "</section>"


def hostility_eval_section():
    f = PROC / "hostility_eval.json"
    if not f.exists():
        return ""
    H = json.loads(f.read_text())
    sec = ('<section id="handlabels"><h2>Disapproving-tone flag against hand labels</h2><p>150 r/StopEatingSeedOils comments, 30 per GoEmotions score band, labelled blind '
           '(H hostile toward a person or group, C critical but civil, N neither, U can&#8217;t tell; U left out). Precision and recall are given for the sample and '
           're-weighted by how many documents fall in each score band.</p>')
    for who, v in H["per_labeller"].items():
        sec += f"<h3>Labeller {e(who)}: " + ", ".join(f"{k} {n}" for k, n in v["counts"].items() if k and n) + "</h3>" + table(["Model score band", "Comments", "Hand label H", "H or C"],
            [(b["band"], str(b["n"]), f"{b['H_pct']}%" if b["H_pct"] is not None else "–", f"{b['H_or_C_pct']}%" if b["H_or_C_pct"] is not None else "–") for b in v["by_band"]], num=(1, 2, 3))
    fk = H.get("fleiss_kappa")
    if fk:
        sec += (f"<h3>Agreement between the {len(H['labellers'])} labellers</h3><p>Fleiss&#8217; kappa over the {fk['items_all_labelled']} comments everyone labelled: "
                f"<b>{fk['H_vs_rest']}</b> on hostile vs not, {fk['H_or_C_vs_N']} on hostile-or-critical vs neither, {fk['H_C_N']} on all three labels. "
                "Pairwise Cohen&#8217;s kappa below.</p>")
    for a in H.get("agreement", []):
        sec += (f"<p>Agreement {e(a['pair'])}: {a['percent']}% of {a['n']} comments; Cohen&#8217;s kappa {a['kappa_HCN']} on H/C/N, {a['kappa_H_vs_rest']} on H vs not H, "
                f"{a.get('kappa_HorC_vs_N', '–')} on H or C vs N. Most disagreements are C against N: the line between criticism and neutral is the fuzzy one, hostility is not.</p>")
        ct = a.get("crosstab")
        if ct:
            x, y = a["pair"].split("-"); cols = [c for c in ("H", "C", "N", "U") if c in ct]; rws = sorted({r for c in ct.values() for r in c}, key="HCNU".index)
            sec += table([f"{e(x)} \\ {e(y)}", *cols], [(r, *[str(ct[c].get(r, 0)) for c in cols]) for r in rws], num=tuple(range(1, len(cols) + 1)))
    rows = [(e(r["definition"]), e(r["hostile_means"]), str(r["flagged_in_sample"]), *[str(r["sample"][k]) for k in ("precision", "recall", "f1")],
             *[str(r["population_weighted"][k]) for k in ("precision", "recall", "f1")]) for r in H["model_vs_hand"]]
    ref = H["reference"]; rtxt = ref["items"] if "items" in ref else ", ".join(f"{k}: {v}" for k, v in ref.items() if k != "rule")
    sec += (f"<h3>Model flag against the reference ({e(rtxt)} comments; {e(ref['rule'])})</h3>" +
            table(["Model definition", "Hostile means", "Flagged", "Precision", "Recall", "F1", "Precision (weighted)", "Recall (weighted)", "F1 (weighted)"], rows, num=tuple(range(2, 9))))
    pe = H.get("population_estimate")
    if pe:
        sec += (f"<h3>Whole-subreddit estimate</h3><p>Weighting each band by its share of documents: hand-labelled hostile (H) "
                f"<b>{pe['H']['pct']}%</b> (95% CI {pe['H']['ci95'][0]}&#8211;{pe['H']['ci95'][1]}), hostile or critical (H or C) "
                f"<b>{pe['H_or_C']['pct']}%</b> ({pe['H_or_C']['ci95'][0]}&#8211;{pe['H_or_C']['ci95'][1]}), against "
                f"{pe['flagged_by_page_definition_pct']}% flagged by the page&#8217;s definition. Bootstrap within bands, 2,000 draws.</p>")
    pg = {r["hostile_means"]: r for r in H["model_vs_hand"] if r["definition"].startswith("page")}
    ps, pl = pg["strict: H"], pg["lenient: H or C"]
    sec += (f"<p><b>Reading.</b> The flag tracks criticism more than hostility: {pl['sample']['precision'] * 100:.0f}% of flagged comments are H or C by the reference, "
            f"but only {ps['sample']['precision'] * 100:.0f}% are hostile toward people ({ps['population_weighted']['precision'] * 100:.0f}% re-weighted). Most hostile comments sit in low "
            f"score bands, so the flag misses most of them (weighted recall {ps['population_weighted']['recall']:.2f}). The measure is better described as "
            "<i>disapproving or critical tone</i> than as hostility.</p>")
    return sec + "</section>"


def reply_section():
    f = PROC / "reply_network_stats.json"
    if not f.exists():
        return ""
    R = json.loads(f.read_text()); pr = R["periods"]; L = R["louvain"]
    sec = ('<section id="replynet"><h2>Reply network (r/StopEatingSeedOils)</h2><p>Nodes: every account that wrote a post or comment (bots and [deleted] left out). '
           'Directed edge A &#8594; B: A replied to B&#8217;s post or B&#8217;s comment; weight = number of replies; self-replies dropped. Whole history, comments of any length. '
           '<code>reply_network.py</code>.</p>')
    rows = [("Accounts linked", f"{R['nodes']:,}", f"{pr[0]['nodes']:,}", f"{pr[1]['nodes']:,}"),
            ("Directed links", f"{R['edges']:,}", f"{pr[0]['edges']:,}", f"{pr[1]['edges']:,}"),
            ("Replies", f"{R['replies']:,}", f"{pr[0]['replies']:,}", f"{pr[1]['replies']:,}"),
            ("Share of replies to posts (top-level)", *[f"{d['share_replies_to_posts'] * 100:.0f}%" for d in (R, *pr)]),
            ("Largest weakly connected component", *[f"{d['largest_weak_component_share'] * 100:.1f}%" for d in (R, *pr)]),
            ("Largest strongly connected component", *[f"{d['largest_strong_component_share'] * 100:.1f}%" for d in (R, *pr)]),
            ("Reciprocity (pairs replying both ways)", *[f"{d['reciprocity']:.3f}" for d in (R, *pr)]),
            ("Clustering (transitivity, undirected)", *[f"{d['transitivity_undirected']:.4f}" for d in (R, *pr)]),
            ("Degree assortativity", *[f"{d['degree_assortativity_undirected']:+.3f}" for d in (R, *pr)]),
            ("Accounts never replied to", *[f"{d['share_nodes_never_replied_to'] * 100:.0f}%" for d in (R, *pr)])]
    sec += table(["Measure", "All", "Before 2024", "From 2024"], rows, num=(1, 2, 3))
    fi, fo = R["in_degree_fit"], R["out_degree_fit"]
    sec += (f"<p><b>Against nulls (whole network).</b> Reciprocity {R['reciprocity']:.3f} vs {R['reciprocity_null_mean']:.3f} when targets are shuffled keeping every in- and out-degree "
            f"(range {R['reciprocity_null_range'][0]}&#8211;{R['reciprocity_null_range'][1]}): about {R['reciprocity'] / R['reciprocity_null_mean']:.0f}&#215; chance, people answer back. "
            f"Clustering {R['transitivity_undirected']:.4f} vs {R['transitivity_null_mean']:.4f} after degree-preserving rewiring: only slightly above chance, the reply network is close to tree-like "
            f"(threads branch, triangles are rare), unlike the co-commenting network (0.29 vs 0.038). The top 1% of accounts receive {R['top1pct_share_of_replies_received'] * 100:.0f}% of all replies. "
            f"Degree tails: in-degree {e(fi['better'])} fits better than a power law (R = {fi['loglik_ratio_pl_vs_lognormal']}, p = {fi['p']}; power-law &#945; {fi['alpha']} above {fi['xmin']}); "
            f"out-degree {e(fo['better'])} (R = {fo['loglik_ratio_pl_vs_lognormal']}).</p>")
    sec += loglog_chart({"Replies received (in-degree)": ("--c1", R["in_degree_ccdf"]), "Replies given (out-degree)": ("--c2", R["out_degree_ccdf"])},
                        "Degree distributions (CCDF, distinct partners)", "degree k", "P(K ≥ k)")
    vt = L.get("vs_topic_communities", {})
    from sklearn.metrics import adjusted_mutual_info_score
    N = pd.read_csv(PROC / "reply_network_nodes.csv").dropna(subset=["louvain"])
    N["q"] = N.first_month.str[:4] + "Q" + ((N.first_month.str[5:7].astype(int) - 1) // 3 + 1).astype(str)
    B = N[N.louvain.isin(N.louvain.value_counts().index[:9])]; tami = adjusted_mutual_info_score(B.louvain, B.q)
    gs = B.groupby("louvain").agg(n=("idx", "size"), new=("newcomer", "mean"), yr=("first_month", lambda x: int(x.str[:4].astype(int).median()))).sort_values("n", ascending=False)
    oldc = gs[gs.new < .5]
    cohort_txt = (f"{len(oldc)} of them is mostly old guard ({', '.join(f'{int(r.n):,} accounts, {r.new * 100:.0f}% newcomers' for r in oldc.itertuples())}); "
                  f"the others are {gs[gs.new >= .5].new.min() * 100:.0f}&#8211;{gs.new.max() * 100:.0f}% newcomers, by median first year "
                  + ", ".join(f"{int(r.n):,} ({r.yr})" for r in gs[gs.new >= .5].itertuples()) + ".") if len(gs) else ""
    sec += (f"<p><b>Communities.</b> Louvain on the undirected weighted graph ({L['nodes_in_largest_component']:,} accounts): {L['communities']} communities, {L['communities_with_100plus']} with 100+ accounts "
            f"(largest {', '.join(f'{x:,}' for x in L['largest_sizes'][:7])}), modularity {L['modularity']}, agreement across 5 seeds AMI {L['ami_across_5_seeds_mean']}. "
            f"Agreement with the co-commenting topic communities for the {vt.get('people_in_both', 0):,} people in both: AMI {vt.get('ami', '–')}, almost none. "
            f"They follow <i>when</i> people were active instead: AMI {tami:.2f} with the quarter of a person&#8217;s first post or comment (9 largest communities). "
            f"{cohort_txt}</p>")
    def mix(rows_):
        return table(["From", "To", "Observed share", "Expected from activity", "Lift"], [(r["from"], r["to"], f"{r['observed'] * 100:.1f}%", f"{r['expected'] * 100:.1f}%", f"{r['lift']:.2f}") for r in rows_], num=(2, 3, 4))
    sec += ("<h3>Newcomers and the old guard: replies from 2024</h3><p>Newcomer = first post or comment from 2024. Expected = share of replies sent by the group &#215; share received by the target group. "
            "Only replies from 2024 are used, because before 2024 everyone is old guard (over the whole history old guard &#8594; old guard has lift "
            f"{R['cohort_mixing'][0]['lift']}, which is mostly this time effect).</p>" + mix(R["cohort_mixing_from2024"]) +
            "<p>From 2024 the two groups reply to each other almost exactly as often as activity alone predicts: no sign that newcomers and the old guard keep to themselves.</p>")
    return sec + "</section>"


def reply_findings_section():
    f = PROC / "reply_findings.json"
    if not f.exists():
        return ""
    F = json.loads(f.read_text()); fc = F["q1_first_contribution"]; q2 = F["q2_interest_similarity"]; q3 = F["q3_tone_by_similarity"]; wb = F["q1_tone_within_replier"]
    sec = ('<section id="replyq"><h2>Who replies to whom, and how</h2><p>Replies from 2024 (both cohorts present), same reply rules as the network above; tone = disapproving tone '
           '(GoEmotions, hand-checked). <code>reply_findings.py</code>.</p><h3>Old guard and newcomers</h3>')
    sec += table(["From", "To", "Replies", "Lift vs activity", "Disapproving tone"], [(r["from"], r["to"], f"{r['replies']:,}", f"{r['lift']:.2f}", f"{r['disapproving_pct']:.1f}%") for r in F["q1_mixing_and_tone"]], num=(2, 3, 4))
    o, n = wb["old guard repliers"], wb["newcomer repliers"]
    sec += (f"<p>Within the same replier, replies to newcomers are {o['within_replier_diff_pts_to_newcomer_vs_old']:+.2f} points more often disapproving for old-guard repliers "
            f"(95% CI {o['ci95_pts'][0]:+.2f} to {o['ci95_pts'][1]:+.2f}) and {n['within_replier_diff_pts_to_newcomer_vs_old']:+.2f} for newcomer repliers ({n['ci95_pts'][0]:+.2f} to {n['ci95_pts'][1]:+.2f}): at most half a point. "
            f"Newcomers&#8217; first contributions ({fc['newcomers']:,} people): {fc['first_gets_reply_pct']}% get a reply ({fc['first_post_gets_reply_pct']}% of first posts, {fc['first_comment_gets_reply_pct']}% of first comments; "
            f"any contribution from 2024: {fc['any_contribution_from_2024_gets_reply_pct']}%), median {fc['hours_to_first_reply_median']:.1f} hours to the first reply; the old guard writes {fc['first_reply_by_old_guard_pct']}% of those first replies, "
            f"as expected from their share of replies that month ({fc['expected_old_guard_pct_from_reply_share_that_month']}%).</p>")
    sec += (f"<h3>Shared interests</h3><p>{q2['replies']:,} replies between the 2,621 commenters with topic profiles (topic shares, leaving out the thread in question). "
            f"Interest similarity to the person replied to: {q2['mean_similarity_to_replied']:.3f}; to the other such commenters in the same thread: {q2['mean_similarity_to_others_in_thread']:.3f} "
            f"(difference {q2['mean_gap']:+.4f}, 95% CI {q2['gap_ci95'][0]:+.4f} to {q2['gap_ci95'][1]:+.4f}); {q2['share_replies_above_thread_mean_pct']}% of replies go to someone more similar than the thread average. "
            "Within a thread, people do not pick partners by shared interests.</p>")
    sec += table(["Interest similarity quintile", "Similarity", "Replies", "Disapproving tone"], [(str(r["quintile"]), f"{r['similarity_range'][0]:.2f}&#8211;{r['similarity_range'][1]:.2f}", f"{r['replies']:,}", f"{r['disapproving_pct']:.2f}%") for r in q3["quintiles"]], num=(2, 3))
    sec += (f"<p>Tone does not depend on shared interests: per standard deviation of similarity, {q3['within_replier_pts_per_sd_similarity']:+.2f} points within replier "
            f"({q3['within_replier_ci95'][0]:+.2f} to {q3['within_replier_ci95'][1]:+.2f}), {q3['within_thread_pts_per_sd_similarity']:+.2f} within thread ({q3['within_thread_ci95'][0]:+.2f} to {q3['within_thread_ci95'][1]:+.2f}). "
            "Caveat: similar <i>interests</i> (what people write about) is not the same as similar <i>views</i>; two people can share the omega-6 topic and disagree.</p>")
    return sec + "</section>"


def same_people_section():
    """27 Nov: the reply network on exactly the topic network's people, and the self-posts check of the topic network."""
    sec = ""
    f = PROC / "reply_network_stats.json"
    if f.exists() and "same_people_as_topic_network" in (R := json.loads(f.read_text())) and "error" not in R["same_people_as_topic_network"]:
        S = R["same_people_as_topic_network"]; cm = S["community_mixing"]; lv = S["louvain"]
        sec += ('<h3>Reply network on the same 2,621 people as the commenter network</h3><p>Only replies between the commenters of the topic-similarity network, '
                f"so both networks have the same nodes (<code>reply_network.py</code>). {S['replies_between_them']:,} replies ({S['share_of_all_replies_pct']}% of all), "
                f"{S['linked_pairs']:,} linked pairs, every one of the {S['people']:,} people has a reply link. Reciprocity {S['reciprocity']:.2f} against "
                f"{min(S['reciprocity_null']):.2f}&#8211;{max(S['reciprocity_null']):.2f} in the target-shuffle null.</p>")
        sec += table(["From", "To", "Replies from 2024", "Lift vs activity"], [(r["from"], r["to"], f"{r['replies']:,}", f"{r['lift']:.2f}") for r in S["cohort_mixing_from_split"]], num=(2, 3))
        names = json.loads((PROC / "community_names.json").read_text()); labs = [x["short"] for x in names] if isinstance(names, list) else [names[str(i)]["short"] for i in range(len(names))]
        sec += ('<figure><figcaption>Replies between the 12 commenter communities (rows reply to columns): lift against activity alone; red = more than expected, blue = fewer, '
                'grey = as expected (colour capped at &#215;3 and &#215;1/3; the diagonal shows the value). Hover a cell for its lift.</figcaption><div class="chart">'
                + heatmap_svg(cm["lift_matrix"], labs[:len(cm["lift_matrix"])], "Reply lift between commenter communities") + "</div></figure>")
        sec += (f"<p>Replies inside the replier&#8217;s own topic community: {cm['within_community_share_pct']}% against {cm['expected_from_activity_pct']}% expected from activity "
                f"(&#215;{cm['ratio']}); with shuffled community labels {cm['shuffled_labels_pct_mean']}% (maximum {cm['shuffled_labels_pct_max']}%). Part of this is people meeting in the "
                f"same threads. Louvain on this reply network: {lv['communities']} communities, modularity {lv['modularity']:.2f}; agreement with the topic communities AMI "
                f"{lv['ami_vs_topic_communities']:.3f} (shuffled {lv['ami_vs_shuffled_topic_labels']:.3f}), with the cohort (old guard / newcomer) AMI {lv['ami_vs_cohort']:.3f}: "
                "who replies to whom follows when people were active more than what they write about.</p>")
    f = PROC / "commenter_network_posts_check.json"
    if f.exists():
        C = json.loads(f.read_text()); rows = []
        for k, lab in (("A_comments_only_reproduction", "A. Comments only (as used)"), ("B_same_people_plus_self_posts", "B. Same people, plus their self-posts"),
                       ("C_node_rule_counts_self_posts", "C. Self-posts also count toward the 10-document rule")):
            r = C[k]
            rows.append((lab, f"{r['people']:,}", f"{r['self_posts_used']:,}", str(r["communities"]), f"{r['modularity_mean']:.3f}", f"{r['ami_vs_saved_communities']:.2f}",
                         f"{r['Politics_group']['long_time_pct']:.0f}% ({r['Politics_group']['share_of_saved_members_in_it_pct']:.0f}%)",
                         f"{r['Omega-6_group']['long_time_pct']:.0f}% ({r['Omega-6_group']['share_of_saved_members_in_it_pct']:.0f}%)"))
        sec += ('<h3>Does leaving out self-posts matter?</h3><p>The commenter network builds profiles from comments only. Rebuilt with the same rules '
                '(<code>commenter_network_posts_check.py</code>); long-time share of the Politics and Omega-6 groups, in brackets the share of the original members still together.</p>')
        sec += table(["Version", "People", "Self-posts", "Communities", "Modularity", "AMI vs used", "Politics: long-time", "Omega-6: long-time"], rows, num=(1, 2, 3, 4, 5))
        sec += "<p>Same 12 communities and the same contrast (Politics about three quarters newcomers, Omega-6 about 60% long-time); AMI 0.70 is a little below the 0.79 between Louvain seeds.</p>"
    return f'<section id="samepeople"><h2>Checks of the commenter network (27 Nov)</h2>{sec}</section>' if sec else ""


def network_svg(layout, nodes, edges, title, coloured, names, label_ids=(), highlight=None, size=1.0, W=760, H=560):
    """Inline SVG drawing of the topic network: precomputed layout (0..1), node area ~ documents, colour = topic community (three coloured,
    rest grey), native hover tooltip per node. highlight(a, b) -> True draws that edge in the first series colour."""
    tok = {c: f"--k{i + 1}" for i, c in enumerate(coloured)}; pad = 28
    X = lambda v: pad + layout[str(v)][0] * (W - 2 * pad); Y = lambda v: pad + (1 - layout[str(v)][1]) * (H - 2 * pad)  # noqa: E731
    p = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{e(title)}">']
    for ed in edges:
        a, b = str(ed["a"]), str(ed["b"])
        if a in layout and b in layout:
            hi = highlight is not None and highlight(ed["a"], ed["b"])
            p.append(f'<line x1="{X(a):.1f}" y1="{Y(a):.1f}" x2="{X(b):.1f}" y2="{Y(b):.1f}" stroke="var({"--k1" if hi else "--edge"})" stroke-width="{2.5 if hi else 0.8}" stroke-opacity="{1 if hi else 0.7}"/>')
    for t, n in sorted(nodes.items(), key=lambda kv: -kv[1]["docs"]):
        if str(t) not in layout:
            continue
        r = max(2.5, (n["docs"] ** 0.5) * 0.16 * size); col = tok.get(n["community"], "--kg")
        p.append(f'<circle cx="{X(t):.1f}" cy="{Y(t):.1f}" r="{r:.1f}" fill="var({col})" stroke="var(--surface)" stroke-width="1.5">'
                 f'<title>[{t}] {e(n["words"])}\nTheme: {e(n["theme"])}\nCommunity: {e(names.get(str(n["community"]), "other"))}\n{n["docs"]:,} documents, {n["degree_all"]} linked topics</title></circle>')
    for t, dx, dy in label_ids:  # (topic, offset x, offset y) in px; a short leader line joins label and circle
        if str(t) in layout:
            txt = ", ".join(nodes[t]["words"].split(", ")[:2]); x2, y2 = X(t) + dx, Y(t) + dy
            p.append(f'<line x1="{X(t):.1f}" y1="{Y(t):.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="var(--muted)" stroke-width="0.8"/>'
                     f'<text x="{x2 + (-3 if dx < 0 else 3):.1f}" y="{y2 + 4:.1f}" text-anchor="{"end" if dx < 0 else "start"}" class="nl">{e(txt)}</text>')
    p.append("</svg>")
    return "".join(p)


def hbar_svg(rows, title, fmt, W=760, row_h=24, left=300, hi=None):
    """Horizontal bars, one series; rows = [(label, value)]. hi = set of labels drawn in the first series colour, others in the second."""
    vmax = max(v for _, v in rows) or 1; H = 18 + row_h * len(rows)
    p = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{e(title)}">']
    for i, (lab, v) in enumerate(rows):
        y = 8 + i * row_h; w = (W - left - 60) * v / vmax; col = "--k1" if hi and lab in hi else "--c2"
        p.append(f'<text x="{left - 8}" y="{y + 14}" text-anchor="end" class="ax">{e(lab)}</text>'
                 f'<rect x="{left}" y="{y + 3}" width="{max(w, 1):.1f}" height="{row_h - 8}" rx="3" fill="var({col})"><title>{e(lab)}: {e(fmt(v))}</title></rect>'
                 f'<text x="{left + w + 6:.1f}" y="{y + 14}" class="ax">{e(fmt(v))}</text>')
    return "".join(p) + "</svg>"


def heatmap_svg(M, labels, title, W=760, cell=None):
    """Lift matrix (dict of dicts, 1 = expected): diverging blue (below 1) - grey - red (above 1), log scale capped at x3 / x1/3; hover shows the value."""
    n = len(labels); left, top = 150, 150; cell = cell or min(42, (W - left - 10) / n); H = top + cell * n + 10
    p = [f'<svg viewBox="0 0 {left + cell * n + 10:.0f} {H:.0f}" role="img" aria-label="{e(title)}">']
    for j, lab in enumerate(labels):
        p.append(f'<text transform="translate({left + j * cell + cell / 2 + 4:.1f},{top - 6}) rotate(-55)" class="ax">{e(lab)}</text>')
    for i, li in enumerate(labels):
        p.append(f'<text x="{left - 6}" y="{top + i * cell + cell / 2 + 4:.1f}" text-anchor="end" class="ax">{e(li)}</text>')
        for j, lj in enumerate(labels):
            v = M.get(str(i), M.get(i, {})).get(str(j), M.get(str(i), M.get(i, {})).get(j))
            if v is None:
                continue
            s = max(-1, min(1, np.log(v) / np.log(3))); pct = abs(s) * 100; pole = "--dpos" if s > 0 else "--dneg"
            p.append(f'<rect x="{left + j * cell + 1:.1f}" y="{top + i * cell + 1:.1f}" width="{cell - 2:.1f}" height="{cell - 2:.1f}" rx="2" '
                     f'style="fill:color-mix(in oklab, var({pole}) {pct:.0f}%, var(--dmid))"><title>{e(li)} &#8594; {e(lj)}: lift {v:.2f}</title></rect>')
            if i == j:
                p.append(f'<text x="{left + j * cell + cell / 2:.1f}" y="{top + i * cell + cell / 2 + 4:.1f}" text-anchor="middle" class="cv">{v:.1f}</text>')
    return "".join(p) + "</svg>"


def topic_cooc_section():
    f = PROC / "topic_cooccurrence_network.json"
    if not f.exists():
        return ""
    T = json.loads(f.read_text()); A = T["all_years"]; per = T["periods"]
    sec = ('<section id="topicnet"><h2>Topic network: which topics the same people write about</h2>'
           f"<p>Nodes = the {T['topics']} BERTopic topics; {A['people']:,} people who wrote in 2+ topics (comments and self-posts). Edge = more people wrote in both topics than in all "
           f"{T['n_samples']} curveball randomisations of the person &#215; topic matrix (each person&#8217;s number of topics and each topic&#8217;s number of people kept exactly) "
           f"and Benjamini&#8211;Hochberg q {T['q']}; weight = lift. <code>topic_cooccurrence_network.py</code>.</p>"
           f"<p>{A['edges']} edges ({A['density']*100:.1f}% of pairs), {A['isolated_topics']} topics without an edge; Louvain modularity {A['modularity_best']:.2f} (stable across seeds, AMI "
           f"{A['stability_ami_across_seeds']:.2f}); agreement with the 14 themes AMI {A['ami_vs_14_themes']:.2f} (shuffled {A['ami_vs_shuffled_themes']:.2f}); "
           f"{A['edges_inside_a_theme_pct']}% of edges inside a theme against {A['pairs_inside_a_theme_pct']}% of all pairs.</p>")
    f2 = PROC / "topic_network_centrality.json"; Cn = json.loads(f2.read_text()) if f2.exists() else None
    nodes = {n["topic"]: n for n in T["nodes"]}
    if Cn and "layout" in Cn:
        lay, col, nm = Cn["layout"], Cn["coloured_communities"], Cn["community_names"]
        pol = lambda a, b: nodes[a]["theme"] == "Politics" and nodes[b]["theme"] == "Politics"  # noqa: E731
        legend = "".join(f'<span><i class="dot" style="background:var(--k{i + 1})"></i>{e(nm[str(c)])}</span>' for i, c in enumerate(col)) + '<span><i class="dot" style="background:var(--kg)"></i>other topic communities</span>'
        sec += (f'<figure><figcaption>The topic network, all years: {len(lay)} topics in the main connected network (circle area = documents; hover a circle for the topic). '
                f'{Cn["unlinked_topics"]} topics have no significant link and {sum(len(c) for c in Cn["small_components"])} sit in two small separate groups (mayo and dressing; skin and additives); they are not drawn.</figcaption>'
                f'<div class="legend">{legend}</div><div class="chart">{network_svg(lay, nodes, T["edges_all"], "Topic network, all years", col, nm, label_ids=[(4, -40, -44), (1, -70, 40), (14, -60, -30), (0, 60, -30), (24, 40, -16), (9, 40, -14), (47, 10, 30), (17, 50, 14)])}</div></figure>')
        sec += ('<div class="pair">' + "".join(f'<figure><figcaption>{lab} ({len(T[k])} links; same positions; politics&#8211;politics links in blue)</figcaption><div class="chart">'
                f'{network_svg(lay, nodes, T[k], lab, col, nm, highlight=pol, size=0.75, W=500, H=380)}</div></figure>' for k, lab in (("edges_before", "Before 2024"), ("edges_from", "From 2024 (one equal-size sample)"))) + "</div>")
    rows = [(str(c["community"]), str(c["topics"]), e(", ".join(f"{k} {v}" for k, v in c["themes"].items())), e(" | ".join(c["example_topics"][:3]))) for c in A["community_contents"] if c["topics"] >= 2]
    sec += "<h3>Topic communities (2+ topics)</h3>" + table(["#", "Topics", "Themes", "Biggest topics"], rows, num=(1,))
    if Cn:
        rows = [(f"[{r['topic']}] {e(r['words'])}", e(r["theme"]), str(r["degree"]), f"{r['betweenness']:.3f}", f"{r['eigenvector']:.2f}", f"{r['participation']:.2f}", str(r["communities_reached"]), f"{r['docs']:,}")
                for r in Cn["top_by_degree"][:8]]
        sec += ("<h3>Hubs</h3><p>Degree = significant partner topics; betweenness with distance 1 / lift; participation = how evenly a topic&#8217;s links spread over communities "
                f"(0 = only its own). Centrality correlates with topic size (Spearman {min(Cn['spearman_with_topic_size'].values()):.2f}&#8211;{max(Cn['spearman_with_topic_size'].values()):.2f}). "
                "<code>topic_network_centrality.py</code>.</p>")
        sec += ('<figure><figcaption>Most connected topics: number of significant partner topics (degree)</figcaption><div class="chart">'
                + hbar_svg([(f"[{r['topic']}] " + ", ".join(r["words"].split(", ")[:2]), r["degree"]) for r in Cn["top_by_degree"]], "Degree of the top topics", lambda v: f"{v:.0f}") + "</div></figure>")
        sec += ('<figure><figcaption>Bridging between communities: betweenness (shortest paths, distance 1 / lift)</figcaption><div class="chart">'
                + hbar_svg([(f"[{r['topic']}] " + ", ".join(r["words"].split(", ")[:2]), r["betweenness"]) for r in Cn["top_by_betweenness"]], "Betweenness of the top topics", lambda v: f"{v:.3f}") + "</div></figure>")
        sec += table(["Topic", "Theme", "Degree", "Betweenness", "Eigenvector", "Participation", "Communities reached", "Documents"], rows, num=(2, 3, 4, 5, 6, 7))
        rows = [(e(r["theme"]), str(r["topics"]), f"{r['mean_degree']:.1f}", f"{r['mean_participation']:.2f}") for r in Cn["by_theme"]]
        sec += ('<h3>By theme</h3><figure><figcaption>Mean participation by theme (0 = a theme&#8217;s topics link only inside their own community; Politics in blue)</figcaption><div class="chart">'
                + hbar_svg([(r["theme"].split(" (")[0], r["mean_participation"]) for r in sorted(Cn["by_theme"], key=lambda r: -r["mean_participation"])], "Participation by theme", lambda v: f"{v:.2f}", left=260, hi={"Politics"}) + "</div></figure>")
        sec += table(["Theme", "Topics", "Mean degree", "Mean participation"], rows, num=(1, 2, 3))
        sec += ("<p>The saturated-fat topic is the hub on every measure and links five of six communities; Politics has no links outside its own community "
                "(participation 0.00).</p>")
    f3 = PROC / "topic_link_communities.json"
    if f3.exists():
        L = json.loads(f3.read_text())["unweighted"]; Lw = json.loads(f3.read_text())["weighted"]
        sec += ("<h3>Link communities (second community method)</h3><p>Communities of <i>links</i> (Ahn, Bagrow and Lehmann 2010), so a topic can belong to several: "
                "links that share a topic are similar when the other two topics have similar neighbours (Jaccard), merged by single linkage and cut at the maximum "
                f"partition density ({L['partition_density']:.2f}). <code>topic_link_communities.py</code>. {L['link_communities']} link communities, but only "
                f"{L['link_communities_3plus']} with 3+ links, holding {L['links_in_3plus_pct']}% of the links: the method splits the sparse edge of the network into "
                f"single links. {L['topics_in_2plus_communities_3plus']} topics belong to two or more of the 3+-link communities. Each topic&#8217;s main link community "
                f"agrees with Louvain at AMI {L['ami_main_link_community_vs_louvain']:.2f} and with the 14 themes at {L['ami_main_link_community_vs_themes']:.2f} "
                f"(weighted version: {Lw['ami_main_link_community_vs_louvain']:.2f} and {Lw['ami_main_link_community_vs_themes']:.2f}).</p>")
        sec += ('<figure><figcaption>Overlap: number of link communities (3+ links) each topic belongs to</figcaption><div class="chart">'
                + hbar_svg([(f"[{r['topic']}] " + ", ".join(r["words"].split(", ")[:2]), r["link_communities_3plus"]) for r in L["most_overlapping_topics"][:10]],
                           "Link-community overlap per topic", lambda v: f"{v:.0f}") + "</div></figure>")
        pol = {47, 89, 93, 97, 98}
        rows = [(str(c["links"]), str(c["topics"]), e(", ".join(f"{k} {v}" for k, v in c["themes"].items())), e(" | ".join(c["topic_words"][:5])),
                 str(len(pol & set(c["topic_ids"])))) for c in L["largest"][:8]]
        sec += table(["Links", "Topics", "Themes", "Biggest topics", "Politics topics"], rows, num=(0, 1, 4))
        sec += ("<p>The saturated-fat topic sits in the most link communities (10), then calories and weight (8) and omega-6 (7): the same hubs as Louvain and centrality, "
                "now seen as topics shared by several conversations. Four of the five politics topics sit in one link community, the largest (with distrust, "
                "the subreddit itself, studies and cholesterol), and none reaches the diet or fat communities.</p>")
    R = per.get("resampled_from") or per.get("resampled_before")
    sec += (f"<h3>Before and from 2024</h3><p>Same number of people in each period ({per['people_each']:,}; the larger period resampled {R['reps'] if R else 1} times). "
            f"Edges: {per['before']['edges']} before, {R['edges_range'][0]}&#8211;{R['edges_range'][1] if R else per['from']['edges']} from 2024 (low power: most topics have no edge in either period).</p>")
    if R:
        rows = [(e(k), str(v["possible"]), str(v.get("before", "")), f"{v['from_range'][0]}&#8211;{v['from_range'][1]}") for k, v in R["key_theme_pairs"].items()]
        sec += table(["Theme pair", "Topic pairs possible", "Linked before", "Linked from 2024 (range over samples)"], rows, num=(1, 2, 3))
        sec += ("<p>Link counts per period are low-power (2,425 people before 2024), so a missing link is not evidence of no co-writing. "
                "The lift comparison below replaces them: it uses everyone in each period and no threshold.</p>")
    f4 = PROC / "topic_network_lift_periods.json"
    if f4.exists():
        LP = json.loads(f4.read_text()); a_, b_ = LP["periods"]["before 2024"], LP["periods"]["from 2024"]
        rows = [(e(k), f"{a_['sets'][k]['lift']:.2f} [{a_['sets'][k]['ci95'][0]:.2f}&#8211;{a_['sets'][k]['ci95'][1]:.2f}]", f"{b_['sets'][k]['lift']:.2f} [{b_['sets'][k]['ci95'][0]:.2f}&#8211;{b_['sets'][k]['ci95'][1]:.2f}]")
                for k in a_["sets"]]
        sec += (f"<h3>Lift before and from 2024 (everyone in each period)</h3><p>Lift = people who wrote in both topics, summed over the pairs, divided by the number expected from that "
                f"period&#8217;s own curveball null ({LP['n_null']} samples); 95% intervals from {LP['n_boot']} bootstrap resamples of people; {a_['people']:,} people before 2024, "
                f"{b_['people']:,} from 2024. <code>topic_network_lift_periods.py</code>.</p>")
        sec += table(["Topic pairs", "Before 2024", "From 2024"], rows, num=(1, 2))
        sec += ("<p>Politics topics go from chance (0.93) to 1.57 times chance, and politics writers become less likely than chance to write about food, diet and shopping "
                "(0.83). Omega-6 with keto (1.17 &#8594; 1.20), the saturated-fat hub and within-theme co-writing do not change: the earlier link-count reading "
                "(omega-6 losing keto, more links inside themes) came from the small sample before 2024.</p>")
    return sec + "</section>"


def paper_check_section():
    fm, fc = PROC / "paper_mesh_check.json", PROC / "conclusion_eval.json"
    if not (fm.exists() or fc.exists()):
        return ""
    sec = ('<section id="paperchecks"><h2>Checks of the AI paper labels</h2><p>The 499 cited papers behind Figure 3a/3c were labelled by Claude subagents from their abstracts '
           '(relevance, conclusion about more seed oil / linoleic acid / PUFA, design, population). Two checks, chosen so no nutrition expertise is needed.</p>')
    if fm.exists():
        M = json.loads(fm.read_text()); ct = pd.DataFrame(M["confusion_ai_rows_mesh_cols"]).fillna(0).astype(int)
        nonrev = [c for c in ct.columns if not c.startswith("review")]; diag = sum(ct.loc[c, c] for c in nonrev if c in ct.index); tot = int(ct[nonrev].values.sum())
        sec += (f"<h3>Evidence type vs PubMed MeSH (expert-assigned)</h3><p>{M['relevant_papers']} relevant papers, {M['mesh_type_known']} with a MeSH study-design tag: agreement "
                f"{M['agreement_pct']}% (kappa {M['kappa']}). Most disagreements are meta-analyses, which OpenAlex types as reviews while the AI codebook counts a meta-analysis of trials as trial evidence. "
                f"Where MeSH names a design (not review), the AI matches in <b>{diag} of {tot}</b> ({100 * diag / tot:.0f}%). The AI saw a coarse MeSH humans/animals tag, so that split is not fully independent; trial vs observational is. "
                "<code>paper_mesh_check.py</code>.</p>")
        sec += table(["AI evidence type", *[e(c) for c in ct.columns]], [(e(r), *[str(ct.loc[r, c]) for c in ct.columns]) for r in ct.index], num=tuple(range(1, len(ct.columns) + 1)))
    if fc.exists():
        C = json.loads(fc.read_text())
        for who, v in C["labellers"].items():
            sec += (f"<h3>Conclusions, non-expert check ({e(who)}, blind, {C['papers']} papers)</h3><p>The page showed each abstract&#8217;s conclusion sentences "
                    f"(section heading {C['conclusion_rule_counts'].get('section', 0)}, cue phrase {C['conclusion_rule_counts'].get('cue', 0)}, last two sentences {C['conclusion_rule_counts'].get('last two sentences', 0)}). "
                    f"Unclear: {v['unclear']}. On the {v['compared']} judged: agreement with the AI <b>{v['agreement_pct']}%</b> (kappa {v['kappa_HBEM']}); harm vs not harm "
                    f"<b>{v['agreement_harm_vs_not_pct']}%</b> (kappa {v['kappa_harm_vs_not']}). Disagreements are mostly borderline mixed findings and papers framed around lowering linoleic acid "
                    "or raising omega-3 (the codebook asks about eating <i>more</i> seed oil); some extracted &#8216;conclusions&#8217; were a methods sentence. <code>conclusion_eval.py</code>.</p>")
            cf = pd.DataFrame(v["confusion_ai_rows_hand_cols"]).fillna(0).astype(int)
            sec += table(["AI \\ hand", *cf.columns], [(r, *[str(cf.loc[r, c]) for c in cf.columns]) for r in cf.index], num=tuple(range(1, len(cf.columns) + 1)))
    sec += "<p>Comment positions (Figure 3b) are not checked: their sample files are not on this machine.</p>"
    return sec + "</section>"


def themes_section():
    out = []
    for pfx, name, f in (("seso", "r/StopEatingSeedOils", THEMES_FILE), ("scinut", "r/ScientificNutrition", "scinut_themes_confirmed.json")):
        tf, df = PROC / f, PROC / f"{pfx}_doc_topics.csv.gz"
        if not (tf.exists() and df.exists()):
            continue
        th = json.loads(tf.read_text()); D = pd.read_csv(df, usecols=["created_utc", "topic"]); post = D.created_utc >= SPLIT
        rows = []
        for t, ids in th.items():
            m = D.topic.isin(ids); a, b = m[~post].mean() * 100, m[post].mean() * 100
            pj = D.created_utc >= SPLIT_TS_AUG2024; aj, bj = m[~pj].mean() * 100, m[pj].mean() * 100
            rows.append((e(t), e(", ".join(map(str, ids))), f"{int(m.sum()):,}", f"{a:.2f}%", f"{b:.2f}%", f"×{b / a:.2f}" if a else "–", f"×{bj / aj:.2f}" if aj else "–"))
        out.append(f"<h3>{e(name)}</h3>" + table(["Theme", "Topics", "Documents", "Before 2024", "From 2024", "Change", "Change, split at 1 Aug 2024"], rows, num=(2, 3, 4, 5, 6)))
    if not out:
        return ""
    return ('<section id="themes"><h2>Themes</h2><p>r/StopEatingSeedOils: the 14 hand-assigned themes of the paper draft, covering all 123 topics (<code>themes_full_v3.json</code>, decision 26 Nov); r/ScientificNutrition: the hand-picked themes of 22 Nov ('
            '<code>scinut_themes_confirmed.json</code>). Share = documents in the theme&#8217;s topics among all documents of the period. '
            'The original r/ScientificNutrition themes were chosen because they grew, so their growth is descriptive; seed oils / PUFA tests whether the '
            'seed-oil surge spilled over.</p>' + "".join(out) + "</section>")


def diet_section():
    f, g = PROC / "diet_overlap.csv", PROC / "diet_overlap_by_subreddit.csv"
    if not f.exists():
        return ""
    R = pd.read_csv(f); S = pd.read_csv(g)
    lab = {"SESO all": "r/StopEatingSeedOils, all heavy commenters", "SESO old": "… old guard (first comment before 2024)",
           "SESO new": "… newcomers (first comment from 2024)", "SciNut": "r/ScientificNutrition heavy commenters"}
    ci = lambda r: f"{r.share_pct:.1f}% <small>[{r.ci_lo:.1f}–{r.ci_hi:.1f}]</small>"
    rows = []
    for grp in ("SESO all", "SESO old", "SESO new", "SciNut"):
        a = R[(R.group == grp) & (R.variant == "core")].set_index("period")
        rows.append((e(lab[grp]), f"{int(a.loc['pre2024', 'n_people']):,}", ci(a.loc["pre2024"]), ci(a.loc["from2024"]), f"{a.loc['from2024', 'share_pct'] - a.loc['pre2024', 'share_pct']:+.1f}"))
    sec = ('<section id="diet"><h2>Where the heavy commenters also post: diet communities</h2><p>Share of heavy commenters with 3+ posts or comments in at least one of '
           '22 diet subreddits (fixed before these numbers existed), among those active on Reddit in that period; 95% bootstrap intervals over people. '
           'Heavy commenters only (the 1,500 most active in each subreddit), not one-off visitors.</p>')
    sec += table(["Group", "People (before 2024)", "Before 2024", "From 2024", "Change (points)"], rows, num=(1, 2, 3, 4))
    v = R[R.group == "SESO all"].pivot_table(index="variant", columns="period", values="share_pct")
    sec += "<h3>Same measure with the borderline groups added</h3>" + table(["List", "Before 2024", "From 2024"], [(e(i), f"{r.pre2024:.1f}%", f"{r.from2024:.1f}%") for i, r in v.iterrows()], num=(1, 2))
    s = S[S.group == "SESO all"].pivot_table(index=["category", "subreddit"], columns="period", values="share_pct").assign(ch=lambda d: d.from2024 - d.pre2024).sort_values("ch")
    sec += "<h3>Each core diet subreddit (all heavy seed-oil commenters)</h3>" + table(["Kind", "Subreddit", "Before 2024", "From 2024", "Change"],
        [(e(k), f"r/{e(n)}", f"{r.pre2024:.1f}%", f"{r.from2024:.1f}%", f"{r.ch:+.1f}") for (k, n), r in s.iterrows()], num=(2, 3, 4))
    return sec + "</section>"


def lda_section():
    f = PROC / "lda_comparison.json"
    if not f.exists():
        return ""
    L = json.loads(f.read_text()); b = L["bertopic"]
    rows = [("BERTopic (seed 42)", str(b["topics"]), "–", "–", f"{b['coherence_npmi']:.3f}", f"{b['diversity']:.2f}", "one topic per document")]
    rows += [(f"LDA K={r['K']} (seed {r['seed']})", f"{r['used_topics']}", f"{r['ami_vs_bertopic']:.3f}", f"{r['nmi_vs_bertopic']:.3f}", f"{r['coherence_npmi']:.3f}", f"{r['diversity']:.2f}",
              f"top topic holds {r['mean_top_prob']:.0%} of a document on average") for r in L["lda"]]
    sec = ('<section id="lda"><h2>BERTopic compared with LDA</h2><p>LDA (scikit-learn, online variational Bayes) on the same r/StopEatingSeedOils documents and the same counting rules, single words. '
           'LDA gives each document a mixture of topics; here a document\'s LDA topic is its most probable one. Coherence = mean NPMI of each topic\'s top 10 words '
           '(higher means the words co-occur in documents); diversity = share of distinct words across all topics\' top 10s.</p>')
    sec += table(["Model", "Topics used", "AMI vs BERTopic", "NMI vs BERTopic", "Coherence (NPMI)", "Diversity", "Note"], rows, num=(1, 2, 3, 4, 5))
    if L.get("lda_stability"):
        sec += "<h3>LDA stability across its own seeds</h3>" + table(["K", "Seeds", "AMI"], [(str(s["K"]), f"{s['a']} vs {s['b']}", f"{s['ami']:.3f}") for s in L["lda_stability"]], num=(0, 2))
    if L.get("themes"):
        keys = [k for k in next(iter(L["themes"].values())) if k != "bertopic"]
        rows = [(e(th), f"{v['bertopic'][0]:.2f}% → {v['bertopic'][1]:.2f}%", *[f"{v[k][0]:.2f}% → {v[k][1]:.2f}%" for k in keys]) for th, v in L["themes"].items()]
        sec += ("<h3>Theme shares before → from 2024</h3><p>An LDA topic counts toward the theme that holds the largest share of its documents, "
                "if that share is at least 20% (LDA topics are mixtures). “0.00%” means no LDA topic reached that.</p>") + table(["Theme", "BERTopic", *[k.replace("lda_", "LDA ").replace("_s", " seed ") for k in keys]], rows)
    return sec + "</section>"


# ---------------------------------------------------------------- page
def table(head, rows, num=()):
    th = "".join(f'<th class="{"n" if i in num else ""}">{e(h)}</th>' for i, h in enumerate(head))
    tr = "".join("<tr>" + "".join(f'<td class="{"n" if i in num else ""}">{c}</td>' for i, c in enumerate(r)) + "</tr>" for r in rows)
    return f'<div class="tw"><table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'


def main():
    now = dt.datetime.now().strftime("%d %b %Y, %H:%M")
    sections = []
    # status
    S = status(); counts = Counter(s for _, s, _ in S)
    chips = "".join(f'<li class="st {s}"><span class="pill">{ {"done": "Done", "running": "Running", "waiting": "Needs you", "todo": "Not started"}[s]}</span>'
                    f'<b>{e(step)}</b><small>{e(note)}</small></li>' for step, s, note in S)
    sections.append(f'<section id="status"><h2>Pipeline</h2><p class="lede">{counts["done"]} of {len(S)} steps done, {counts["running"]} running, '
                    f'{counts["waiting"]} waiting for a decision.</p><ul class="steps">{chips}</ul></section>')
    # data
    rows, months = raw_summary()
    fmt_d = lambda t: dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%d %b %Y") if t else "–"
    R = [(e(n.replace("_", " ")), f"{c:,}" if c is not None else "–", f"{p:,}", (f"{c - p:+,}" if c is not None else "–"), f"{fmt_d(lo)} to {fmt_d(hi)}")
         for n, c, p, lo, hi in rows]
    last = max((m for d in months.values() for m in d), default=None)
    act = {f"r/{s}": (("--c1" if s.startswith("Stop") else "--c2"), {m: v for m, v in d.items() if m >= "2018-10" and m != last}) for s, d in months.items()}
    sections.append('<section id="data"><h2>Data collected</h2><p>Re-downloaded from Arctic Shift on 22 Nov 2026, compared with the first download of 18 Nov. '
                    'Arctic Shift lags a few days behind Reddit, so the last days are incomplete; r/carnivore comments were not downloaded (decision 22 Nov).</p>'
                    + table(["File", "Items now", "18 Nov", "Change", "Range"], R, num=(1, 2, 3))
                    + line_chart(act, "Posts and comments per month (bots excluded; last, incomplete month left out)", "items per month", lambda v: f"{v / 1000:.0f}k" if v >= 1000 else f"{v:.0f}")
                    + "</section>")
    sections.append(corpus_section())
    # documents + topics
    trows = []
    for p, name in (("seso", "r/StopEatingSeedOils"), ("scinut", "r/ScientificNutrition")):
        f = PROC / f"{p}_topics_info.csv"
        if f.exists():
            T = pd.read_csv(f); n_docs = int(T.n_docs.sum())
            trows.append((name, f"{n_docs:,}", f"{OLD_DOCS[p]:,}", f"{len(T)}", f"{OLD_TOPICS[p]}"))
    sec = '<section id="topics"><h2>Topic models</h2><p>BERTopic on comments and self-posts of 15+ words. HDBSCAN finds the number of topics itself (minimum topic size 150 comments); outliers are then reassigned to the nearest topic. Topic words use the new counting rules: hyphenated terms kept, names merged, negated words marked <code>no_</code>.</p>'
    sec += table(["Subreddit", "Documents", "19 Nov", "Topics", "19 Nov"], trows, num=(1, 2, 3, 4))
    f = PROC / "seso_topics_info.csv"
    if f.exists():
        T = pd.read_csv(f).assign(ch=lambda d: d.share_from2024 / d.share_pre2024.where(d.share_pre2024 > 0))
        big = T[T.n_docs >= 300]
        up = big.sort_values("ch", ascending=False).head(8); down = big.sort_values("ch").head(6)
        fr = lambda D: [(f"{r.topic}", e(", ".join(w.strip() for w in r.top_words.split(",")[:6])), f"{r.share_pre2024 * 100:.2f}%", f"{r.share_from2024 * 100:.2f}%", f"×{r.ch:.1f}") for r in D.itertuples()]
        sec += "<h3>r/StopEatingSeedOils: fastest-growing topics (300+ comments)</h3>" + table(["Topic", "Top words", "Before 2024", "From 2024", "Change"], fr(up), num=(0, 2, 3, 4))
        sec += "<h3>Shrinking the most</h3>" + table(["Topic", "Top words", "Before 2024", "From 2024", "Change"], fr(down), num=(0, 2, 3, 4))
        allr = [(f"{r.topic}", f"{r.n_docs:,}", e(", ".join(w.strip() for w in r.top_words.split(",")[:8])), f"{r.share_pre2024 * 100:.2f}%", f"{r.share_from2024 * 100:.2f}%")
                for r in T.sort_values("n_docs", ascending=False).itertuples()]
        sec += f'<details><summary>All {len(T)} topics of r/StopEatingSeedOils</summary>' + table(["Topic", "Comments", "Top words", "Before 2024", "From 2024"], allr, num=(0, 1, 3, 4)) + "</details>"
    sections.append(sec + "</section>")
    sections.append(themes_section())
    sections.append(network_section())
    sections.append(netstats_section())
    sections.append(reply_section())
    sections.append(reply_findings_section())
    sections.append(same_people_section())
    sections.append(topic_cooc_section())
    sections.append(cocite_section())
    sections.append(stability_section())
    sections.append(lda_section())
    sections.append(diet_section())
    # emotions
    f = PROC / "goemo_monthly.csv"
    if f.exists():
        M = pd.read_csv(f); M["post"] = M.month >= "2024-01"
        er = []
        for s, g in M.groupby("subreddit"):
            v = {p: (h.hostile_share * h.n).sum() / h.n.sum() * 100 for p, h in g.groupby("post")}; n = {p: int(h.n.sum()) for p, h in g.groupby("post")}
            er.append((e(s), f"{v[False]:.2f}%", f"{n[False]:,}", f"{v[True]:.2f}%", f"{n[True]:,}", f"{v[True] - v[False]:+.2f}"))
        ser = {}
        for s, g in M.groupby("subreddit"):
            g = g[(g.n >= 300) & (g.month >= "2019-01") & (g.month != M.month.max())]
            ser[s] = ("--c1" if "Stop" in s else "--c2", dict(zip(g.month, g.hostile_share * 100)))
        sections.append('<section id="emotion"><h2>Disapproving tone</h2><p>GoEmotions (<code>SamLowe/roberta-base-go_emotions</code>, trained on Reddit) on every comment and self-post, short ones included. '
                        'A document has a disapproving tone when anger, annoyance, disapproval or disgust scores 0.5 or more (called &#8216;hostile&#8217; until 25 Nov; renamed after the hand labels below showed it tracks criticism more than hostility toward people).</p>'
                        + table(["Subreddit", "Before 2024", "Documents", "From 2024", "Documents", "Change (points)"], er, num=(1, 2, 3, 4, 5))
                        + line_chart(ser, "Disapproving-tone share per month (months with 300+ documents)", "% of documents", lambda v: f"{v:.0f}%")
                        + "</section>")
    # emoji
    sections.append(hostility_eval_section())
    sections.append(paper_check_section())
    sections.append(emoji_section())
    # votes
    vs = []
    for p, name in (("seso", "r/StopEatingSeedOils"), ("scinut", "r/ScientificNutrition")):
        f = PROC / f"{p}_topic_votes.csv"
        if f.exists():
            V = pd.read_csv(f); V = V[(V.n_pre2024 >= 100) & (V.n_from2024 >= 100)].sort_values("mean_pct_from2024", ascending=False)
            fr = lambda D: [(f"{r.topic}", e(", ".join(w.strip() for w in r.top_words.split(",")[:6])), f"{r.mean_pct_from2024:.3f}", f"{int(r.n_from2024):,}") for r in D.itertuples()]
            vs.append(f"<h3>{e(name)}: best and worst received topics from 2024</h3>" + table(["Topic", "Top words", "Mean percentile", "Comments"], fr(V.head(5)) + [("…", "", "", "")] + fr(V.tail(5)), num=(0, 2, 3)))
    if vs:
        sections.append('<section id="votes"><h2>How comments are received</h2><p>Each comment\'s score ranked within its own thread and level (0.5 = typical for its thread). Bots excluded; comments of every age kept (decision 22 Nov). Topics with 100+ scored comments in both periods.</p>' + "".join(vs) + "</section>")
    # citations
    f = PROC / "cited_papers_summary.txt"
    if f.exists():
        keep = [l for l in f.read_text().splitlines() if l.startswith("==") or "design (MeSH)" in l or "works cited in both" in l]
        sections.append(f'<section id="papers"><h2>Cited papers</h2><p>Paper links (PubMed, PMC, DOI, nature.com) resolved in OpenAlex.</p><pre>{e(chr(10).join(keep))}</pre></section>')
    # decisions
    dec = ["Bots (AutoModerator and accounts ending in 'bot') removed from every input.", "Comments of every age kept in vote measures.",
           "Hyphenated terms kept whole (omega-6, n-6); accented letters kept; no lemmatization.", "Hand-merged names (entity_aliases.csv) and negation marking where words are counted: only absence claims, no / without + the noun phrase (no seed oils -> no_seed-oil), 0.7% of content words. Verb negation is not marked: on 100 hand-checked snippets, marking the first word after any negator was exactly right only 56% of the time (35% for the earlier 3-word rule).",
           "torchMoji with a 256-token limit.", "r/carnivore comments dropped; overlap with diet communities measured over 22 pre-declared subreddits (borderline groups as checks).",
           "Heavy commenters picked from r/StopEatingSeedOils and r/ScientificNutrition only."]
    sections.append('<section id="decisions"><h2>Decisions behind this rerun</h2><ul class="dec">' + "".join(f"<li>{e(d)}</li>" for d in dec) + "</ul></section>")
    page = PAGE.replace("__UPDATED__", e(now)).replace("__BODY__", "\n".join(sections))
    # Every non-ASCII character (−, ∝, β, é ...) is written as a numeric HTML reference, so the page reads correctly even when a browser opens the
    # local file with the wrong encoding (otherwise "−" shows as "âˆ’").
    OUT.write_text(page.encode("ascii", "xmlcharrefreplace").decode("ascii"), encoding="ascii")
    print(f"wrote {OUT} ({OUT.stat().st_size / 1e3:.0f} kB)")


PAGE = """<meta charset="utf-8">
<title>Seed Oil Rerun</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;600&family=JetBrains+Mono:wght@400&display=swap">
<style>
/* Layout: one reading column; a status board first, then each result section with its table and chart. */
:root { --bg:#f7f8f6; --surface:#ffffff; --fg:#1d2220; --muted:#5f6a65; --line:#dde2df; --grid:#e8ece9; --shade:#eef2ec;
  --c1:#c2571a; --c2:#3f6f8f; --k1:#2a78d6; --k2:#eb6834; --k3:#1baf7a; --kg:#b9b8b0; --edge:#c9c8c0; --dpos:#e34948; --dneg:#2a78d6; --dmid:#f0efec; --done:#2f7d4f; --run:#2b6cb0; --wait:#b7791f; --todo:#8a948f;
  --display:"Space Grotesk", "Helvetica Neue", Arial, sans-serif; --body:Inter, system-ui, -apple-system, "Segoe UI", sans-serif; --mono:"JetBrains Mono", ui-monospace, Menlo, monospace; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg:#141816; --surface:#1b201e; --fg:#e7ece9; --muted:#9aa59f; --line:#2c3330; --grid:#252b28; --shade:#1f2622;
  --c1:#e07a3f; --c2:#79a8c9; --k1:#3987e5; --k2:#d95926; --k3:#199e70; --kg:#5d5c57; --edge:#5a5954; --dpos:#e66767; --dneg:#3987e5; --dmid:#383835; --done:#5cbf85; --run:#6ea8e6; --wait:#e0a84a; --todo:#7d8883; color-scheme: dark; } }
:root[data-theme="dark"] { --bg:#141816; --surface:#1b201e; --fg:#e7ece9; --muted:#9aa59f; --line:#2c3330; --grid:#252b28; --shade:#1f2622;
  --c1:#e07a3f; --c2:#79a8c9; --k1:#3987e5; --k2:#d95926; --k3:#199e70; --kg:#5d5c57; --edge:#5a5954; --dpos:#e66767; --dneg:#3987e5; --dmid:#383835; --done:#5cbf85; --run:#6ea8e6; --wait:#e0a84a; --todo:#7d8883; color-scheme: dark; }
body { background:var(--bg); color:var(--fg); font:15px/1.55 var(--body); }
main { max-width:900px; margin:0 auto; padding-block:28px 64px; padding-left:max(16px, env(safe-area-inset-left, 0px)); padding-right:max(16px, env(safe-area-inset-right, 0px)); display:grid; gap:40px; }
main > * { min-width:0; }
header h1 { font:600 clamp(28px, 5vw, 40px)/1.1 var(--display); margin:4px 0 8px; text-wrap:balance; }
.eyebrow { font-size:12px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); margin:0; }
header p { margin:0; color:var(--muted); max-width:65ch; }
h2 { font:600 22px/1.2 var(--display); margin:0 0 8px; } h3 { font:600 15px/1.3 var(--body); margin:20px 0 8px; }
section > p { max-width:68ch; margin:0 0 12px; } .lede { color:var(--muted); }
code, pre { font-family:var(--mono); font-size:12.5px; }
pre { background:var(--surface); border:1px solid var(--line); border-radius:6px; padding:12px; overflow-x:auto; white-space:pre-wrap; margin:0; }
.steps { list-style:none; padding:0; margin:0; display:grid; grid-template-columns:repeat(auto-fill, minmax(260px, 1fr)); gap:8px; }
.st { display:grid; grid-template-columns:auto 1fr; column-gap:10px; align-items:baseline; padding:10px 12px; background:var(--surface); border:1px solid var(--line); border-radius:6px; min-width:0; }
.st b { font-weight:500; } .st small { grid-column:2; color:var(--muted); font-size:12.5px; }
.pill { font-size:11px; font-weight:600; letter-spacing:.03em; padding:2px 8px; border-radius:99px; color:var(--bg); white-space:nowrap; }
.done .pill { background:var(--done); } .running .pill { background:var(--run); } .waiting .pill { background:var(--wait); } .todo .pill { background:var(--todo); }
.waiting { border-color:var(--wait); }
.tw { overflow-x:auto; border:1px solid var(--line); border-radius:6px; background:var(--surface); }
table { border-collapse:collapse; width:100%; font-size:13.5px; } th, td { padding:7px 10px; text-align:left; border-bottom:1px solid var(--line); vertical-align:top; }
th { font-weight:600; color:var(--muted); font-size:12px; } tr:last-child td { border-bottom:0; } .n { text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }
figure { margin:16px 0 0; } figcaption { font-weight:600; font-size:14px; }
.legend { display:flex; flex-wrap:wrap; gap:4px 16px; font-size:12.5px; color:var(--muted); margin:4px 0; } .legend i { display:inline-block; width:12px; height:3px; margin-right:6px; vertical-align:middle; }
.chart { overflow-x:auto; } .chart svg { width:100%; min-width:520px; height:auto; display:block; } .ax { font:11px var(--body); fill:var(--muted); } .nl { font:11.5px var(--body); fill:var(--fg); paint-order:stroke; stroke:var(--surface); stroke-width:3px; } .cv { font:10px var(--body); fill:var(--fg); } .legend i.dot { width:10px; height:10px; border-radius:50%; } .pair { display:grid; grid-template-columns:repeat(auto-fit, minmax(300px, 1fr)); gap:12px; } .pair .chart svg { min-width:0; }
details { margin-top:16px; } summary { cursor:pointer; font-weight:500; } summary:focus-visible { outline:2px solid var(--run); outline-offset:2px; }
.dec { margin:0; padding-left:20px; display:grid; gap:4px; max-width:70ch; }
.two { display:grid; grid-template-columns:repeat(auto-fit, minmax(300px, 1fr)); gap:16px; } .two > div { min-width:0; }
.note { color:var(--muted); font-size:13px; margin-top:12px; }
sup { font-size:.72em; line-height:0; position:relative; top:-.5em; vertical-align:baseline; }
.math { font-family:"Cambria Math", "STIX Two Math", "Times New Roman", serif; font-style:italic; white-space:nowrap; }
</style>
<main>
<header><p class="eyebrow">Seed oils on Reddit · rerun of 22 Nov 2026</p><h1>Seed Oil Rerun</h1>
<p>Results of the full re-download and rerun, rebuilt from the output files after each step. Updated __UPDATED__. Aggregates only: no usernames, no comment text.</p></header>
__BODY__
</main>"""

if __name__ == "__main__":
    main()
