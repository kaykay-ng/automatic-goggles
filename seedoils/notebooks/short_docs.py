"""The SHORT comments that the topic corpus drops: documents of 1 to 14 words after cleaning (seso_topics.py keeps >= 15 words; it drops ~39% of comments).
Same filters and cleaning as seso_topics.prep (no bots/[deleted]/AutoModerator, quotes and links removed, removed/deleted text skipped), only the word minimum differs.
Output (local, contains Reddit text, gitignored): seedoils/data/processed/{seso,scinut}_short_docs.csv.gz (id, kind, author, created_utc, score, text). Used for emotion scoring only: BERTopic stays on >= 15 words.
Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/short_docs.py"""
import gzip
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import seso_topics as st  # noqa: E402

for sub, pfx in st.PREFIX.items():
    rows = []
    for kind in ("comments", "posts"):
        with gzip.open(st.RAW / f"{sub}_{kind}.jsonl.gz", "rt", encoding="utf-8") as f:
            for line in f:
                try:
                    x = json.loads(line)
                except ValueError:
                    continue
                a = x.get("author") or ""
                if a in st.SKIP_AUTHORS or a.lower().endswith("bot"):
                    continue
                raw = x.get("body") if kind == "comments" else f"{x.get('title', '')}. {x.get('selftext') or ''}"
                if not raw or raw.strip() in ("[removed]", "[deleted]") or (kind == "posts" and (x.get("selftext") or "").strip() in ("", "[removed]", "[deleted]")):
                    continue
                t = st.clean(raw); n = len(t.split())
                if 1 <= n < st.MIN_WORDS:
                    rows.append((x["id"], kind[:-1], a, int(x["created_utc"]), x.get("score"), t))
    D = pd.DataFrame(rows, columns=["id", "kind", "author", "created_utc", "score", "text"]).sort_values("created_utc", ignore_index=True)
    D.to_csv(st.PROC / f"{pfx}_short_docs.csv.gz", index=False)
    full = len(pd.read_csv(st.PROC / f"{pfx}_docs.csv.gz", usecols=["id"]))
    print(f"{sub}: {len(D):,} short documents (1-{st.MIN_WORDS - 1} words), median {int(D.text.str.split().str.len().median())} words; the topic corpus has {full:,}")
