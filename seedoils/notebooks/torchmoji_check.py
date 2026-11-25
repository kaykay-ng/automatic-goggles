"""Check the torchMoji port (vendor/torchMoji + weights from huggingface.co/Uberduck/torchmoji) against the ONNX scores already computed (deepmoji_seso.npz).
Patched upstream code (two one-line fixes for Python 3.11+ / PyTorch 2): torchmoji/tokenizer.py RE_TITLES = r'|'.join([r'(?i:' + t + r')' for t in TITLES]); torchmoji/lstm.py `input, batch_sizes = input.data, input.batch_sizes`.
Env: python3.12 -m venv .venv-torchmoji; pip install torch numpy scipy scikit-learn 'emoji<2' text-unidecode pandas.
Run from final_project/:  ./.venv-torchmoji/bin/python seedoils/notebooks/torchmoji_check.py"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd, torch
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "vendor" / "torchMoji"))
from torchmoji.sentence_tokenizer import SentenceTokenizer
from torchmoji.model_def import torchmoji_emojis
W = ROOT / "vendor" / "torchmoji_weights"
st = SentenceTokenizer(json.load(open(W / "vocabulary.json")), 30)
model = torchmoji_emojis(str(W / "pytorch_model.bin")).eval()
def score(texts, bs=256):
    out = []
    for i in range(0, len(texts), bs):
        tok, _, _ = st.tokenize_sentences(texts[i:i + bs])
        with torch.no_grad():
            out.append(np.asarray(model(tok)))
    return np.concatenate(out)
if __name__ == "__main__":
    for t in ["I love mom's cooking", "This is shit", "This is the shit", "lol", "source?"]:
        p = score([t])[0]; print(t, "->", np.argsort(p)[::-1][:5].tolist(), np.round(np.sort(p)[::-1][:3], 3))
    PROC = ROOT / "seedoils" / "data" / "processed"
    z = np.load(PROC / "deepmoji_seso.npz", allow_pickle=True)
    D = pd.read_csv(PROC / "seso_docs.csv.gz", usecols=["id", "text"], keep_default_na=False)
    ids = pd.Series(range(len(z["id"])), index=z["id"].astype(str))
    S = D.sample(600, random_state=1); S = S[S.id.astype(str).isin(ids.index)]
    A = score(S.text.astype(str).tolist()); B = z["p"][ids[S.id.astype(str)].values].astype(np.float32)
    print("n", len(S), "max abs diff", float(np.abs(A - B).max()), "mean abs diff", float(np.abs(A - B).mean()),
          "same top-1", float((A.argmax(1) == B.argmax(1)).mean()), "mean corr", float(np.mean([np.corrcoef(a, b)[0, 1] for a, b in zip(A, B)])))
