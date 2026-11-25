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

import pandas as pd

from seedoil_common import is_bot

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC, OUT = ROOT / "data" / "raw", ROOT / "data" / "processed", ROOT / "artifact" / "rerun_results.html"
A_DIR = PROC / "artifact"
SPLIT = 1704067200
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
    for f in glob.glob(str(RAW / "author_subreddit_counts*.jsonl.gz")):
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
    S.append(("Hand-picked themes", "waiting" if not (PROC / "themes_confirmed.json").exists() else "done", "your picks of topic ids per theme"))
    for step, note in (("Name list check", "seedoil_common.py aliases"),                        ("Dashboard datasets", "artifact_data.py, last")):
        S.append((step, "todo", note))
    S.append(("Negation check", "done" if (PROC / "negation_labels_v2_HY.csv").exists() else "todo", "absence claims only (no / without + noun phrase), 25 Nov"))
    S.append(("Hostility hand labels (150 comments)", "done" if (PROC / "hostility_eval.json").exists() else "todo", "2 labellers (HY, NP); kappa 0.72 on H vs not H"))
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
    sec += ('<p><b>Reading.</b> The flag tracks criticism more than hostility: about nine in ten flagged comments are H or C, but only about one in five '
            'is hostile toward people, and the top band (0.7+) is mostly civil criticism. Most hostile comments sit in the lowest band, so the flag misses '
            'most of them (weighted recall about 0.17). The measure is better described as <i>disapproving or critical tone</i> than as hostility.</p>')
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


def themes_section():
    out = []
    for pfx, name, f in (("seso", "r/StopEatingSeedOils", "themes_confirmed.json"), ("scinut", "r/ScientificNutrition", "scinut_themes_confirmed.json")):
        tf, df = PROC / f, PROC / f"{pfx}_doc_topics.csv.gz"
        if not (tf.exists() and df.exists()):
            continue
        th = json.loads(tf.read_text()); D = pd.read_csv(df, usecols=["created_utc", "topic"]); post = D.created_utc >= SPLIT
        rows = []
        for t, ids in th.items():
            m = D.topic.isin(ids); a, b = m[~post].mean() * 100, m[post].mean() * 100
            rows.append((e(t), e(", ".join(map(str, ids))), f"{int(m.sum()):,}", f"{a:.2f}%", f"{b:.2f}%", f"×{b / a:.2f}" if a else "–"))
        out.append(f"<h3>{e(name)}</h3>" + table(["Theme", "Topics", "Documents", "Before 2024", "From 2024", "Change"], rows, num=(2, 3, 4, 5)))
    if not out:
        return ""
    return ('<section id="themes"><h2>Themes</h2><p>Hand-picked groups of topics (decisions of 22 Nov, saved in <code>themes_confirmed.json</code> and '
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
  --c1:#c2571a; --c2:#3f6f8f; --done:#2f7d4f; --run:#2b6cb0; --wait:#b7791f; --todo:#8a948f;
  --display:"Space Grotesk", "Helvetica Neue", Arial, sans-serif; --body:Inter, system-ui, -apple-system, "Segoe UI", sans-serif; --mono:"JetBrains Mono", ui-monospace, Menlo, monospace; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg:#141816; --surface:#1b201e; --fg:#e7ece9; --muted:#9aa59f; --line:#2c3330; --grid:#252b28; --shade:#1f2622;
  --c1:#e07a3f; --c2:#79a8c9; --done:#5cbf85; --run:#6ea8e6; --wait:#e0a84a; --todo:#7d8883; color-scheme: dark; } }
:root[data-theme="dark"] { --bg:#141816; --surface:#1b201e; --fg:#e7ece9; --muted:#9aa59f; --line:#2c3330; --grid:#252b28; --shade:#1f2622;
  --c1:#e07a3f; --c2:#79a8c9; --done:#5cbf85; --run:#6ea8e6; --wait:#e0a84a; --todo:#7d8883; color-scheme: dark; }
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
.chart { overflow-x:auto; } .chart svg { width:100%; min-width:520px; height:auto; display:block; } .ax { font:11px var(--body); fill:var(--muted); }
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
