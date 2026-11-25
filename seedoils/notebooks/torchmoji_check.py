"""DeepMoji through the torchMoji port (vendor/torchMoji + weights from huggingface.co/Uberduck/torchmoji); `score()` is used by deepmoji_torch_time.py.
Patched upstream code (two one-line fixes for Python 3.11+ / PyTorch 2): torchmoji/tokenizer.py RE_TITLES = r'|'.join([r'(?i:' + t + r')' for t in TITLES]); torchmoji/lstm.py `input, batch_sizes = input.data, input.batch_sizes`.
Env: python3.12 -m venv .venv-torchmoji; pip install torch numpy scipy scikit-learn 'emoji<2' text-unidecode pandas.

Token limit (decision 22 Nov): MAXLEN = 256 DeepMoji tokens (words, punctuation and emoji each count as one). The authors' examples use 30, the length of
the tweets the model was trained on; longer input runs fine (bi-LSTM + attention, padding is skipped) but is longer than anything seen in training.
This script therefore also reports how far 256 agrees with 30 on the same comments, next to the 30-token check against the ONNX port.

Run from final_project/:  ./.venv-torchmoji/bin/python seedoils/notebooks/torchmoji_check.py"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd, torch
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "vendor" / "torchMoji"))
from torchmoji.sentence_tokenizer import SentenceTokenizer
from torchmoji.model_def import torchmoji_emojis
W = ROOT / "vendor" / "torchmoji_weights"
MAXLEN = 256
_vocab = json.load(open(W / "vocabulary.json"))
_tok = {}
model = torchmoji_emojis(str(W / "pytorch_model.bin")).eval()


def score(texts, bs=256, maxlen=MAXLEN):
    """Probabilities over the 64 DeepMoji emojis, one row per text; texts longer than `maxlen` DeepMoji tokens are cut there."""
    if maxlen not in _tok:
        _tok[maxlen] = SentenceTokenizer(_vocab, maxlen)
    out = []
    for i in range(0, len(texts), bs):
        tok, _, _ = _tok[maxlen].tokenize_sentences(texts[i:i + bs])
        with torch.no_grad():
            out.append(np.asarray(model(tok)))
    return np.concatenate(out)


def n_tokens(texts):
    """Number of DeepMoji tokens per text (before any cut), using a tokenizer with a very long limit."""
    if 10_000 not in _tok:
        _tok[10_000] = SentenceTokenizer(_vocab, 10_000)
    tok, _, _ = _tok[10_000].tokenize_sentences(texts)
    return (np.asarray(tok) > 0).sum(1)


def compare(A, B):
    return (f"same top-1 {float((A.argmax(1) == B.argmax(1)).mean()):.2f}, top-5 overlap {np.mean([len(set(np.argsort(-a)[:5]) & set(np.argsort(-b)[:5])) / 5 for a, b in zip(A, B)]):.2f}, "
            f"mean corr {float(np.mean([np.corrcoef(a, b)[0, 1] for a, b in zip(A, B)])):.3f}, mean abs diff {float(np.abs(A - B).mean()):.4f}")


if __name__ == "__main__":
    for t in ["I love mom's cooking", "This is shit", "This is the shit", "lol", "source?"]:
        p = score([t])[0]; print(t, "->", np.argsort(p)[::-1][:5].tolist(), np.round(np.sort(p)[::-1][:3], 3))
    PROC = ROOT / "seedoils" / "data" / "processed"
    D = pd.read_csv(PROC / "seso_docs.csv.gz", usecols=["id", "text"], keep_default_na=False)
    S = D.sample(600, random_state=1); texts = S.text.astype(str).tolist()
    L = n_tokens(texts)
    print(f"\nDeepMoji tokens per comment (600 random documents of >= 15 words): median {int(np.median(L))}, 90th pct {int(np.percentile(L, 90))}; "
          f"longer than 30: {(L > 30).mean():.0%}; longer than {MAXLEN}: {(L > MAXLEN).mean():.0%}")
    A30, A256 = score(texts, maxlen=30), score(texts, maxlen=MAXLEN)
    print(f"maxlen 30 vs {MAXLEN}, all 600: {compare(A30, A256)}")
    long_ = L > 30
    if long_.any():
        print(f"maxlen 30 vs {MAXLEN}, only the {int(long_.sum())} comments longer than 30 tokens: {compare(A30[long_], A256[long_])}")
        print(f"  mean entropy of the emoji distribution (higher = blander), long comments: 30 -> {float((-A30[long_] * np.log(A30[long_] + 1e-12)).sum(1).mean()):.2f}, "
              f"{MAXLEN} -> {float((-A256[long_] * np.log(A256[long_] + 1e-12)).sum(1).mean()):.2f}")
    onnx = PROC / "deepmoji_seso.npz"
    if onnx.exists():  # the old check: torchMoji vs the ONNX port, both at 30 tokens
        z = np.load(onnx, allow_pickle=True); ids = pd.Series(range(len(z["id"])), index=z["id"].astype(str)); ok = S.id.astype(str).isin(ids.index).values
        print(f"torchMoji vs ONNX port, both 30 tokens (n={int(ok.sum())}): {compare(A30[ok], z['p'][ids[S.id.astype(str)[ok]].values].astype(np.float32))}")
