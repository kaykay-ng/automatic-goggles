"""Where do links inside comments and self-posts lead? Counts of documents containing a URL, grouped by domain type (our grouping), r/StopEatingSeedOils vs r/ScientificNutrition. Aggregates only.
Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/link_domains.py"""
from seedoil_common import is_bot, not_bot, SPLIT_TS# shared bot rule: AutoModerator + names ending in 'bot'
import gzip, glob, json, re, collections
import pandas as pd
URL = re.compile(r"https?://([A-Za-z0-9.-]+)[^\s)\]>]*"); CUT = SPLIT_TS
ACAD = ("pubmed.ncbi.nlm.nih.gov", "ncbi.nlm.nih.gov", "doi.org", "sciencedirect.com", "nature.com", "jamanetwork.com", "thelancet.com", "bmj.com", "springer.com", "springeropen.com", "wiley.com", "frontiersin.org", "plos.org", "academic.oup.com", "researchgate.net", "mdpi.com", "cell.com", "ahajournals.org", "nejm.org", "cochranelibrary.com", "scholar.google.com", "europepmc.org", "biomedcentral.com", "tandfonline.com", "sagepub.com", "pnas.org", "science.org", "jci.org", "ajcn.nutrition.org", "nih.gov", "semanticscholar.org", "sci-hub.se", "elifesciences.org")
VIDEO = ("youtube.com", "youtu.be", "tiktok.com", "rumble.com", "vimeo.com", "odysee.com"); SOCIAL = ("x.com", "twitter.com", "facebook.com", "instagram.com", "t.co", "substack.com", "linkedin.com")
REDDIT = ("reddit.com", "redd.it", "i.redd.it", "v.redd.it", "preview.redd.it"); SHOP = ("amazon.com", "amzn.to", "costco.com", "walmart.com", "target.com", "thrivemarket.com", "iherb.com", "instacart.com")
def kind(d):
    d = d.lower().lstrip("www.") if d.lower().startswith("www.") else d.lower()
    for name, L in (("academic papers", ACAD), ("video", VIDEO), ("social media and newsletters", SOCIAL), ("reddit (other threads, images)", REDDIT), ("shopping", SHOP)):
        if any(d == x or d.endswith("." + x) for x in L): return name
    return "other sites (news, blogs, wikis, products)"
for sub in ("StopEatingSeedOils", "ScientificNutrition"):
    n = 0; withurl = 0; cnt = collections.Counter(); dom = collections.Counter(); per = {"before 2024": [0, 0], "from 2024": [0, 0]}
    for kindf in ("comments", "posts"):
        with gzip.open(glob.glob(f"seedoils/data/raw/*{sub}_{kindf}.jsonl.gz")[0], "rt", encoding="utf-8") as f:
            for l in f:
                x = json.loads(l)
                if is_bot(x.get("author")): continue
                txt = (x.get("body") if kindf == "comments" else (x.get("selftext") or "") + " " + (x.get("url") or "")) or ""
                u = URL.findall(txt); n += 1; p = per["from 2024" if int(x["created_utc"]) >= CUT else "before 2024"]; p[0] += 1
                if kindf == "posts" and x.get("url") and "reddit.com" in x["url"] and not (x.get("selftext") or "").strip(): u = []  # self posts only link to themselves
                if u: withurl += 1; p[1] += 1; ks = {kind(d) for d in u}; [cnt.update([k]) for k in ks]; dom.update({d.lower() for d in u})
    print(f"\n{sub}: documents {n:,}; with at least one link {withurl:,} ({withurl/n*100:.1f}%); before 2024 {per['before 2024'][1]/per['before 2024'][0]*100:.1f}% , from 2024 {per['from 2024'][1]/per['from 2024'][0]*100:.1f}%")
    print("  documents with a link, by where it leads (a document can have several kinds):", {k: f"{v/withurl*100:.0f}%" for k, v in cnt.most_common()})
    print("  top domains:", [(d, c) for d, c in dom.most_common(12)])
