"""Build one text per country and round from Climate Watch NDC text fields, embed it (week 7 recipe), count sector mentions.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python ndc/notebooks/ndc_embed.py
Text = all text fields (>=150 chars) of the round, HTML stripped, identical strings de-duplicated, concatenated per country.
Embedding: all-MiniLM-L6-v2 (max_seq_length 256), passages of <=180 words cut on sentence boundaries, mean of passage vectors, normalised.
Writes ndc/data/processed/ndc_vectors_<round>.npy, ndc_index_<round>.csv, ndc_sector_emphasis.csv."""
import html, re, sys
from pathlib import Path
import numpy as np, pandas as pd

PROC = Path("ndc/data/processed")
ROUNDS = ["indc", "first_ndc", "revised_first_ndc", "second_ndc", "third_ndc"]
# LIST FIX 15 Nov (ndc/PLAN.md KEYWORD-LIST REVIEW): industry no longer matches "cement" inside enhancement/enforcement/... or "pre-industrial"; buildings no longer matches "capacity building".
SECTORS = {"energy": r"energy|electricity|renewable|solar|wind|fossil|coal|\bpower\b|\bfuels?\b|efficiency",
           "agriculture": r"agricultur|\bfarm|livestock|\bcrops?\b|\brice\b|fertili|manure|\bsoils?\b",
           "land_forest": r"forest|afforest|reforest|land[- ]use|lulucf|deforest|mangrove|peat",
           "waste": r"\bwaste|landfill|recycl|sewage|wastewater",
           "industry": r"(?<!pre-)(?<!pre)industr(?!ial revolution)|\bcement\b|manufactur|\bhfcs?\b|refrigerant",
           "transport": r"transport|vehicle|aviation|shipping|\broads?\b|\brail",
           "buildings": r"(?<!capacity )(?<!capacity-)\bbuildings\b|\bbuilding (?:sector|codes?|stock|energy|envelope|regulations?|standards?|materials?|insulation|efficiency)\b|\bhousing\b|heating|cooling"}


def clean(t):
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    return re.sub(r"\s+", " ", t).strip()


def passages(text, max_words=180):
    out, cur, n = [], [], 0
    for sent in re.split(r"(?<=[.!?;])\s+", text):
        w = len(sent.split())
        if cur and n + w > max_words:
            out.append(" ".join(cur)); cur, n = [], 0
        cur.append(sent); n += w
    if cur:
        out.append(" ".join(cur))
    return out


if __name__ == "__main__":
    T = pd.read_csv(PROC / "ndc_text_long.csv")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2", device="mps")
    emph = []
    for rd in ROUNDS:
        S = T[T.document == rd]
        docs = {}
        for iso, g in S.groupby("iso"):
            seen, parts = set(), []
            for v in g.value:
                c = clean(v)
                if c and c not in seen:
                    seen.add(c); parts.append(c)
            docs[iso] = " ".join(parts)
        isos = sorted(docs)
        chunks, owner = [], []
        for k, iso in enumerate(isos):
            for p in passages(docs[iso]):
                chunks.append(p); owner.append(k)
        E = model.encode(chunks, batch_size=64, normalize_embeddings=True, show_progress_bar=False)
        owner = np.array(owner); V = np.zeros((len(isos), E.shape[1]), dtype=np.float32); np.add.at(V, owner, E)
        V /= np.linalg.norm(V, axis=1, keepdims=True)
        np.save(PROC / f"ndc_vectors_{rd}.npy", V)
        np.save(PROC / f"ndc_passvec_{rd}.npy", E.astype(np.float32)); np.save(PROC / f"ndc_passowner_{rd}.npy", owner)
        idx = pd.DataFrame({"iso": isos, "n_chars": [len(docs[i]) for i in isos], "n_words": [len(docs[i].split()) for i in isos],
                            "n_passages": np.bincount(owner, minlength=len(isos))})
        idx.to_csv(PROC / f"ndc_index_{rd}.csv", index=False)
        print(f"{rd:18s} countries {len(isos):3d} | median words {int(idx.n_words.median()):5d} | passages {len(chunks):5d}", flush=True)
        for iso in isos:
            low = docs[iso].lower(); nw = max(len(low.split()), 1)
            row = {"round": rd, "iso": iso, "n_words": nw}
            row.update({s: 1e4 * len(re.findall(rx, low)) / nw for s, rx in SECTORS.items()})
            emph.append(row)
    pd.DataFrame(emph).to_csv(PROC / "ndc_sector_emphasis.csv", index=False)
    print("done")
