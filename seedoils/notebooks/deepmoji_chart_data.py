"""Dataset 'deepmoji' for the artifact: DeepMoji emoji-prediction scores grouped into six emotion families, per quarter and subreddit.
The grouping of the 64 emojis is OURS and approximate (emojis left out as ambiguous: mask, flushed, relieved, relaxed, sleeping, sleepy, see_no_evil, raised_hand, notes, headphones, sparkles, gun).
Value = mean over documents of the summed predicted probability of the family's emojis, in percent of the model's predicted emoji mass (not the share of comments).
Run from final_project/ after deepmoji_time.py:  ./.venv-moji/bin/python seedoils/notebooks/deepmoji_chart_data.py -> seedoils/data/processed/artifact/deepmoji.json. Quarters with fewer than 300 documents are dropped."""
import json
from pathlib import Path

import pandas as pd

PROC = Path(__file__).resolve().parents[1] / "data" / "processed"
_VENDOR = Path(__file__).resolve().parents[2] / "vendor" / "torchMoji" / "data" / "emoji_codes.json"  # emoji id -> name, from the torchMoji repo
CODES = json.load(open(_VENDOR if _VENDOR.exists() else next(Path.home().glob(".cache/**/emoji_codes.json"))))
NAMES = [CODES[str(i)] for i in range(64)]
CH = {":joy:": "😂", ":sweat_smile:": "😅", ":grin:": "😁", ":smile:": "😄", ":wink:": "😉", ":stuck_out_tongue_winking_eye:": "😜", ":skull:": "💀", ":heart_eyes:": "😍", ":heart:": "❤️", ":two_hearts:": "💕",
      ":kissing_heart:": "😘", ":hearts:": "♥️", ":blue_heart:": "💙", ":purple_heart:": "💜", ":sparkling_heart:": "💖", ":blush:": "😊", ":ok_hand:": "👌", ":thumbsup:": "👍", ":clap:": "👏", ":raised_hands:": "🙌",
      ":100:": "💯", ":muscle:": "💪", ":v:": "✌️", ":pray:": "🙏", ":sunglasses:": "😎", ":rage:": "😡", ":angry:": "😠", ":punch:": "👊", ":imp:": "👿", ":triumph:": "😤", ":sob:": "😭", ":cry:": "😢",
      ":broken_heart:": "💔", ":disappointed:": "😞", ":pensive:": "😔", ":weary:": "😩", ":tired_face:": "😫", ":persevere:": "😣", ":confounded:": "😖", ":sweat:": "😓", ":unamused:": "😒", ":smirk:": "😏",
      ":expressionless:": "😑", ":neutral_face:": "😐", ":eyes:": "👀", ":information_desk_person:": "💁", ":speak_no_evil:": "🙊", ":no_good:": "🙅", ":grimacing:": "😬", ":confused:": "😕"}
GROUPS = {"Laughter": [":joy:", ":sweat_smile:", ":grin:", ":smile:", ":wink:", ":stuck_out_tongue_winking_eye:", ":skull:"],
          "Love": [":heart_eyes:", ":heart:", ":two_hearts:", ":kissing_heart:", ":hearts:", ":blue_heart:", ":purple_heart:", ":sparkling_heart:", ":blush:"],
          "Approval": [":ok_hand:", ":thumbsup:", ":clap:", ":raised_hands:", ":100:", ":muscle:", ":v:", ":pray:", ":sunglasses:"],
          "Anger": [":rage:", ":angry:", ":punch:", ":imp:", ":triumph:"],
          "Sadness": [":sob:", ":cry:", ":broken_heart:", ":disappointed:", ":pensive:", ":weary:", ":tired_face:", ":persevere:", ":confounded:", ":sweat:"],
          "Skepticism": [":unamused:", ":smirk:", ":expressionless:", ":neutral_face:", ":eyes:", ":information_desk_person:", ":speak_no_evil:", ":no_good:", ":grimacing:", ":confused:"]}
M = pd.read_csv(PROC / "deepmoji_monthly.csv")
M["q"] = pd.PeriodIndex(M.month, freq="M").asfreq("Q").astype(str)
rows = []
for (sub, q), g in M.groupby(["subreddit", "q"]):
    n = int(g.n.sum())
    if n < 300 or q < "2020Q1":
        continue
    for name, ems in GROUPS.items():
        idx = [i for i, e in enumerate(NAMES) if e in ems]
        rows.append({"subreddit": sub, "quarter": q, "group": name, "pct": round(sum((g[str(i)] * g.n).sum() for i in idx) / n * 100, 2), "n": n, "emojis": "".join(dict.fromkeys(CH[e] for e in ems))})
meta = [{"label": "deepmoji_chart_data.py", "value": Path(__file__).read_text()}]
(PROC / "artifact" / "deepmoji.json").write_text(json.dumps({"rows": rows, "meta": meta}))
print(len(rows), "rows;", sorted({r["quarter"] for r in rows})[0], "to", sorted({r["quarter"] for r in rows})[-1])
