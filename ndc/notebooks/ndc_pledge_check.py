"""Did countries keep their word? Base-year pledges (first NDC) vs actual emissions (Climate Watch).
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python ndc/notebooks/ndc_pledge_check.py [parse|compute]
parse   : extract (reduction %, base year, target year) from the 'GHG target' text of the first NDC for countries whose structured type is 'Base year target'; print for eyeballing
compute : progress against the pledge using emissions to 2023
"""
import re, sys
from pathlib import Path
import numpy as np, pandas as pd

PROC = Path("ndc/data/processed")
L = pd.read_csv(PROC / "ndc_indicators_long.csv")
E = pd.read_csv(PROC / "emissions_cw_long.csv")
ROUND = "first_ndc"
PCT = re.compile(r"(\d+(?:\.\d+)?)\s*(?:%|per\s?cent|percent)(?:\s*(?:to|-|–|and)\s*(\d+(?:\.\d+)?)\s*(?:%|per\s?cent|percent))?", re.I)
YEAR = re.compile(r"\b(19[6-9]\d|20[0-4]\d)\b")
BASEKW = re.compile(r"(?:compared\s+(?:to|with)|relative\s+to|below|from|against|over|than|vs\.?|versus|of|in)\s+(?:the\s+)?(?:(?:base|baseline|reference)\s+year\s+)?(?:of\s+)?(?:levels?\s+(?:of|in)\s+)?\(?(?:fy\s*|fiscal\s+year\s*)?((?:19[6-9]\d|20[01]\d))", re.I)
BAU = re.compile(r"\bbau\b|business[- ]as[- ]usual|baseline scenario|reference scenario|projected", re.I)
CAP = re.compile(r"not\s+exceed(?:ing)?\s+(\d+(?:\.\d+)?)\s*(?:-|–|to)?\s*(\d+(?:\.\d+)?)?\s*%\s+of\s+(?:the\s+)?(?:fy\s*)?(19[6-9]\d|20[01]\d)", re.I)
REDUCE = re.compile(r"reduc|cut|below|decreas|lower|limit|curb", re.I)


def get(ind, doc=ROUND):
    s = L[(L.indicator == ind) & (L.document == doc)]
    return s.groupby("iso").value.apply(lambda v: " | ".join(dict.fromkeys(str(x) for x in v)))


def parse():
    ttype, ghg, ty = get("GHG target type"), get("GHG target"), get("Target year (mitigation)")
    rows = []
    for iso in sorted(set(ttype.index)):
        t = ttype[iso]
        if "Base year target" not in t:
            continue
        txt = ghg.get(iso, "")
        pct = PCT.search(txt); ymatch = BASEKW.search(txt)
        tgt = None
        m = re.search(r"(?:by|in|until)\s+(?:the\s+year\s+)?(20[1-4]\d)", txt)
        if m: tgt = int(m.group(1))
        elif iso in ty.index:
            yy = YEAR.findall(ty[iso]); tgt = int(yy[0]) if yy else None
        r_lo = float(pct.group(1)) if pct else np.nan
        r_hi = float(pct.group(2)) if pct and pct.group(2) else r_lo
        cap = CAP.search(txt)
        by = int(ymatch.group(1)) if ymatch else np.nan
        if cap:                                    # 'not exceed X% of YEAR level' = (100-X)% reduction
            a, b = float(cap.group(1)), float(cap.group(2)) if cap.group(2) else float(cap.group(1))
            r_lo, r_hi = 100 - max(a, b), 100 - min(a, b); by = int(cap.group(3))
        m2 = re.search(r"\bto\s+(\d+(?:\.\d+)?)\s*(?:percent|per cent|%)\s+relative\s+to\s+the\s+(?:fy\s*)?(19[6-9]\d|20[01]\d)", txt, re.I)
        if not cap and m2:                         # 'reduction ... to 70 percent relative to the 1990 level' = emissions at 70% of base = 30% reduction (RUS)
            r_lo = r_hi = 100 - float(m2.group(1)); by = int(m2.group(2)); cap = m2
        if not cap and re.match(r"\s*(?:will\s+)?not\s+exceed", txt, re.I) and pct:     # e.g. 'Not exceeding 80-90% (...) of 1990 level'
            a = float(pct.group(1)); b = float(pct.group(2)) if pct.group(2) else a
            r_lo, r_hi = 100 - max(a, b), 100 - min(a, b)
        rows.append(dict(iso=iso, ttype=t[:40], text=txt[:200], reduction_lo=r_lo, reduction_hi=r_hi,
                         base_year=by, target_year=tgt,
                         has_reduce_word=bool(REDUCE.search(txt)) or bool(cap), bau=bool(BAU.search(txt)),
                         eu_joint=("European Union and its 28 Member States" in txt),
                         sector_only=bool(re.search(r"from\s+(?:the\s+)?(?:\w+\s+){0,2}(?:energy|electricity|power|transport|forestry|waste)\b|electricity generation|energy sector", txt, re.I))))
    P = pd.DataFrame(rows)
    P.to_csv(PROC / "ndc_pledges_parsed.csv", index=False)
    return P


def compute():
    from scipy import stats
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    P = parse()
    ctl = pd.read_csv(PROC / "controls.csv").set_index("iso")
    eu28 = set(P[P.eu_joint].iso) - {"EUU"}                  # 27 members + GBR carry the EU's joint first NDC
    P = P[(~P.eu_joint) | (P.iso == "EUU")]
    ok = P.reduction_lo.notna() & P.base_year.notna() & P.target_year.notna() & P.has_reduce_word & ~P.bau & ~P.sector_only
    ok &= P.base_year.between(1990, 2015) & P.target_year.between(2020, 2030)
    C = P[ok].copy()
    def series(sector):
        W = E[E.sector == sector].pivot_table(index="iso", columns="year", values="mtco2e")
        W.loc["EUU"] = W.loc[[c for c in eu28 if c in W.index]].sum(min_count=1)
        return W
    out = {}
    for lab, sec in [("excl", "Total excluding LULUCF"), ("incl", "Total including LULUCF")]:
        W = series(sec); rows = []
        for r in C.itertuples():
            if r.iso not in W.index or pd.isna(W.loc[r.iso, int(r.base_year)]): continue
            Eb, E15, E23 = W.loc[r.iso, int(r.base_year)], W.loc[r.iso, 2015], W.loc[r.iso, 2023]
            T = int(r.target_year); ye = min(2023, T); Eye = W.loc[r.iso, ye]
            for rr_name, rr in [("lo", r.reduction_lo), ("mid", (r.reduction_lo + r.reduction_hi) / 2)]:
                Et = Eb * (1 - rr / 100); path = E15 + (Et - E15) * (ye - 2015) / (T - 2015)
                rows.append(dict(iso=r.iso, basis=lab, r_kind=rr_name, reduction=rr, base_year=int(r.base_year), target_year=T, E_base=Eb, E_2015=E15, E_2023=E23,
                                 E_target=Et, target_met=bool(Eye <= Et), on_track=bool(Eye <= path), gap_remaining=(E23 - Et) / Eb,
                                 progress_share=(E15 - E23) / (E15 - Et) if E15 > Et else np.nan,
                                 actual_pace=100 * (E15 - E23) / 8 / Eb, required_pace=100 * (E23 - Et) / max(T - 2023, 1) / Eb if T > 2023 else np.nan))
        out[lab] = pd.DataFrame(rows)
    R = out["excl"][out["excl"].r_kind == "lo"].set_index("iso")
    R["income"] = ctl.income.reindex(R.index); R.loc["EUU", "income"] = "High income"
    R.to_csv(PROC / "ndc_pledge_progress.csv")
    print(f"\nCHECKABLE base-year pledges (economy-wide, not BAU): {len(R)} (EU counted once); target met by evaluation year: {int(R.target_met.sum())}; on track (ahead of linear path): {int(R.on_track.sum())}; behind: {int((~R.on_track).sum())}")
    tiny = R[R.E_base < 1.0]; print(f"   of these, {len(tiny)} have base-year emissions < 1 Mt (modelled data unreliable): {' '.join(tiny.index)}")
    R = R[R.E_base >= 1.0]
    print(f"MAIN SET (base-year emissions >= 1 Mt, rule added after seeing the tiny-state rows): {len(R)} countries; target met {int(R.target_met.sum())}; on track {int(R.on_track.sum())}; behind {int((~R.on_track).sum())}")
    pd.set_option("display.width", 240)
    show = R.assign(pledge=lambda d: d.reduction.round(0).astype(int).astype(str) + "% vs " + d.base_year.astype(str) + " by " + d.target_year.astype(str))
    show["E_base"] = show.E_base.round(0); show["E_2023"] = show.E_2023.round(0); show["E_target"] = show.E_target.round(0)
    print(show.sort_values("gap_remaining")[["pledge", "E_base", "E_2023", "E_target", "gap_remaining", "on_track", "target_met", "income"]].round(2).to_string())
    S = out["incl"][out["incl"].r_kind == "lo"].set_index("iso")
    both = R.index.intersection(S.index)
    print(f"\nSENSITIVITY: including LULUCF changes on_track for {int((R.loc[both,'on_track'] != S.loc[both,'on_track']).sum())} of {len(both)} countries:",
          list(both[(R.loc[both, 'on_track'] != S.loc[both, 'on_track']).values]))
    M = out["excl"][out["excl"].r_kind == "mid"].set_index("iso")
    print(f"SENSITIVITY: using the midpoint of ranges changes on_track for {int((R.loc[R.index.intersection(M.index),'on_track'] != M.loc[R.index.intersection(M.index),'on_track']).sum())} countries")
    # H4: ambitious pledges not kept better
    rho, p = stats.spearmanr(R.reduction, R.progress_share, nan_policy="omit"); print(f"\nH4: Spearman(pledged reduction, progress share since 2015) = {rho:+.2f} (p={p:.3f}, two-sided; n={R.progress_share.notna().sum()})")
    rho2, p2 = stats.spearmanr(R.reduction, R.gap_remaining); print(f"    Spearman(pledged reduction, gap remaining) = {rho2:+.2f} (p={p2:.3f})")
    # H5: income
    R["rich"] = R.income.isin(["High income"])
    print("H5: on track by income group:\n", pd.crosstab(R.income, R.on_track).to_string())
    a = R[R.rich].on_track.sum(), (R.rich).sum(), R[~R.rich].on_track.sum(), (~R.rich).sum()
    print(f"    high income on track {a[0]}/{a[1]} vs others {a[2]}/{a[3]}; Fisher exact p={stats.fisher_exact([[a[0], a[1]-a[0]], [a[2], a[3]-a[2]]])[1]:.3f}")
    # context: what everyone else did (non-checkable pledge types)
    W = series("Total excluding LULUCF"); chg = 100 * (W[2023] / W[2015] - 1)
    tt = get("GHG target type"); typ = tt.map(lambda t: "Baseline scenario (BAU)" if "Baseline" in t else "Base year" if "Base year" in t else "Fixed level" if "Fixed" in t else "Intensity" if "Intensity" in t else "Not applicable/other")
    ctx = pd.DataFrame({"type": typ, "chg": chg}).dropna(); ctx = ctx[~ctx.index.isin(eu28)]
    print("\nCONTEXT: emission change 2015->2023 (%, total excl LULUCF) by pledge type in the first NDC (EU members excluded):")
    print(ctx.groupby("type").chg.agg(n="count", median="median", share_growing=lambda s: (s > 0).mean()).round(2).to_string())
    # figure: trajectories of the 20 largest checkable emitters
    top = R.sort_values("E_2015", ascending=False).head(20)
    fig, axs = plt.subplots(4, 5, figsize=(19, 12)); Wx = series("Total excluding LULUCF")
    for ax, (iso, r) in zip(axs.ravel(), top.iterrows()):
        yrs = list(range(1990, 2024)); ax.plot(yrs, [Wx.loc[iso, y] for y in yrs], color="#2a6f97", lw=1.8)
        ax.plot([2015, int(r.target_year)], [r.E_2015, r.E_target], color="#d1495b", ls="--", lw=1.5)
        ax.scatter([int(r.target_year)], [r.E_target], color="#d1495b", zorder=3, s=26)
        ax.axvline(2015, color="#999", lw=0.6)
        ax.set_title(f"{iso}: {int(r.reduction)}% vs {int(r.base_year)} by {int(r.target_year)}  ({'on track' if r.on_track else 'behind'})", fontsize=9)
        ax.tick_params(labelsize=7); ax.set_ylim(bottom=0)
    fig.suptitle("Actual emissions (blue, Mt CO2e excl. LULUCF) vs the straight-line path from 2015 to the pledged target (red dashed); grey line = pledge year", fontsize=12)
    fig.tight_layout(); fig.savefig(Path("ndc/figures") / "pledge_vs_emissions.png", dpi=130)
    print("\nsaved ndc/figures/pledge_vs_emissions.png and data/processed/ndc_pledge_progress.csv")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "parse"
    if mode == "compute":
        compute(); sys.exit()
    P = parse()
    ok = P.reduction_lo.notna() & P.base_year.notna() & P.target_year.notna() & P.has_reduce_word
    print(f"countries with 'Base year target' in first NDC: {len(P)} | fully parsed (reduction %, base year, target year): {ok.sum()}")
    print("base years:", P.base_year.value_counts().sort_index().to_dict(), "| target years:", P.target_year.value_counts().sort_index().to_dict())
    pd.set_option("display.width", 240, "display.max_colwidth", 110)
    print("\nSAMPLE OF PARSED ROWS TO EYEBALL (text vs extracted):")
    for r in P[ok].sample(min(18, ok.sum()), random_state=3).itertuples():
        print(f"  {r.iso}: {r.reduction_lo}-{r.reduction_hi}% vs {int(r.base_year)} by {int(r.target_year)} | {r.text[:130]}")
    print("\nNOT parsed (sample):")
    for r in P[~ok].sample(min(10, (~ok).sum()), random_state=3).itertuples():
        print(f"  {r.iso}: pct={r.reduction_lo} base={r.base_year} target={r.target_year} | {r.text[:140]}")
