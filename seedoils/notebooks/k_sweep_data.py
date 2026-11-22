"""Dataset 'topic_k_sweep' for the 'How we did this' note under Figure 1a: for each number of merged topics k, stability across UMAP seeds (AMI), coherence (NPMI),
the share of all comments in the largest merged topic, and the growth multiple of the merged topic that is about RFK Jr./politics and the one about vaccines, if the merge kept them apart.
Run from final_project/ after seso_topics_k_sweep.py:  ../.venv/bin/python seedoils/notebooks/k_sweep_data.py -> seedoils/data/processed/artifact/topic_k_sweep.json. Aggregates only."""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
S = pd.read_csv(PROC / "seso_k_sweep.csv")
rows = []
for r in S.itertuples():
    I = pd.read_csv(PROC / f"seso_k{r.k}_topics_info.csv")
    I["ratio"] = I.share_from2024 / I.share_pre2024.replace(0, float("nan"))

    def ratio(word, minn=300):
        m = I[I.top_words.str.split(", ").str[:6].apply(lambda ws: word in ws) & (I.n_docs >= minn)]
        return None if m.empty else round(float(m.sort_values("n_docs", ascending=False).iloc[0].ratio), 1)
    rows.append({"k": int(r.k), "stability_ami": float(r.stability_ami), "coherence_npmi": float(r.coherence_npmi), "largest_topic_pct": round(100 * I.n_docs.max() / I.n_docs.sum(), 0),
                 "politics_ratio": ratio("rfk"), "vaccines_ratio": ratio("vaccines")})
meta = [{"label": "k_sweep_data.py", "value": Path(__file__).read_text()}]
(PROC / "artifact" / "topic_k_sweep.json").write_text(json.dumps({"rows": rows, "meta": meta}))
for x in rows:
    print(x)
