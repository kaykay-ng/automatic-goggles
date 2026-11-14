"""Translate the Spanish (ES_1) and French (BE_1) strategies to English with OPUS-MT (same family ParlaMint used). Run from final_project/ with the NLP env:
./.venv-nlp/bin/python ndc/notebooks/lts_translate.py"""
import re, time
from pathlib import Path
import torch
from transformers import MarianMTModel, MarianTokenizer

SRC = Path("ndc/data/processed/lts_text"); OUT = Path("ndc/data/processed/lts_text_translated"); OUT.mkdir(parents=True, exist_ok=True)
JOBS = {"ES_1": "Helsinki-NLP/opus-mt-es-en", "BE_1": "Helsinki-NLP/opus-mt-fr-en"}
dev = "mps" if torch.backends.mps.is_available() else "cpu"


def sentences(text):
    t = re.sub(r"-\n(?=[a-zà-ÿ])", "", text)                  # hyphenated line breaks
    t = re.sub(r"\n{2,}", " <PARA> ", t); t = re.sub(r"\s*\n\s*", " ", t); t = re.sub(r"\s+", " ", t)
    out = []
    for para in t.split("<PARA>"):
        for s in re.split(r"(?<=[.!?;:])\s+(?=[A-ZÀ-Ý¿¡0-9•])", para.strip()):
            s = s.strip()
            if len(s) >= 25 and sum(c.isalpha() for c in s) > 15: out.append(s[:600])
    return out


for name, model in JOBS.items():
    t0 = time.time(); tok = MarianTokenizer.from_pretrained(model); mt = MarianMTModel.from_pretrained(model).to(dev).eval()
    S = sentences((SRC / f"{name}.txt").read_text()); res = [None] * len(S)
    order = sorted(range(len(S)), key=lambda i: len(S[i]))      # batch similar lengths together
    for b in range(0, len(order), 24):
        idx = order[b:b + 24]
        enc = tok([S[i] for i in idx], return_tensors="pt", padding=True, truncation=True, max_length=200).to(dev)
        with torch.no_grad():
            gen = mt.generate(**enc, num_beams=2, max_new_tokens=220)
        for i, g in zip(idx, tok.batch_decode(gen, skip_special_tokens=True)): res[i] = g
        if (b // 24) % 20 == 0: print(f"{name}: {b}/{len(S)} sentences, {time.time()-t0:.0f}s", flush=True)
    (OUT / f"{name}.txt").write_text("\n".join(res))
    (OUT / f"{name}_source_sentences.txt").write_text("\n".join(S))
    print(f"{name}: {len(S)} sentences translated in {time.time()-t0:.0f}s -> {sum(len(x.split()) for x in res)} English words", flush=True)
