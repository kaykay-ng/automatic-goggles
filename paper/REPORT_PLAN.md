# Final report plan (written 25 Nov 2026)

Requirements read from the course site (front page and week 8), summarised by a subagent: check them against the site before handing in.
- Hand in on DTU Learn as three PDFs, Friday 27 Nov 2026, 23:59: (1) paper in the PNAS template, LaTeX only (Overleaf), at most 6 pages including figures and references;
  (2) slides: 3 pages, one slide per page, no animations; (3) half-page reflection (ungraded) on the "From an AI-drafted report" boxes.
- Presentation: Wednesday 2 Dec, 3 slides, 3 minutes, then questions. No laptops plugged in, so slides are the only demo; the artifact is optional extra.
- Paper sections: Abstract (about 150 words), Significance Statement (2-3 sentences), Introduction, Results, Discussion, Methods, References, author contributions (specific; "all contributed equally" is not accepted).
- Graded (0-3 each): research question; data and scope (networks AND text); showcasing the course tools; analysis and checks; figures (three good beat eight, captions that stand alone); references; overall; presentation.
- Checks expected: a null, a second method, or a hand-labelled sample with agreement; every analysis gets "what it measures" and "what it misses". LLM-made labels must be validated on a sample the authors read themselves.
- Methods must say what the data is, where from, when collected, how many items. Everyone must be able to explain everything.
- No LaTeX on this machine: write the .tex and figure PDFs here, compile in Overleaf.

## Research question and claim (one sentence each)
Question: did the 2024 surge change what the seed-oil conversation on Reddit is about, who takes part, and how they talk, and which of these findings survive a second method, a null model and a hand check?
Claim: from 2023 to 2024 r/StopEatingSeedOils grew about 3.2x in comments (35,997 to 113,401, bots excluded) and 3.4x in commenters (4,334 to 14,605), against 1.4x in commenters for r/ScientificNutrition (1,877 to 2,721); the conversation shifted from fatty-acid science towards politics, vaccines, distrust of industry and shopping; the new crowd forms one coherent politics/vaccines/pharma community; hostility (a disapproval signal) rose among old and new commenters alike while downvotes rose mostly for newcomers. We document the shift and its timing around the 2024 political events; we do NOT show what caused the surge. r/ScientificNutrition stayed flat.

## Numbers to use (the rerun of 22 Nov is the base; extras from our own runs are marked OURS)
Data: r/StopEatingSeedOils 243,223 comments + 11,648 posts; r/ScientificNutrition 177,989 + 14,282; downloaded from Arctic Shift on 22 Nov 2026 (last days incomplete); topic corpus = comments and posts of 15+ words (149,815 and 121,833 documents). r/carnivore comments were NOT used.
Topics (BERTopic, 123 topics): politics theme x6.07 (0.42% -> 2.54%), vaccines x3.06, industry/medicine/media distrust x1.94, ingredient labels x2.04, shopping x1.62, omega-6/PUFA x0.55, keto/carbs/fasting x0.48.
Stability: 5 UMAP seeds, AMI 0.811 (0.775-0.846), confident documents 0.962; theme growth ranges politics 4.8-6.1, vaccines 3.0-3.1.
Second method: LDA K=123: coherence 0.06-0.07 vs BERTopic 0.252; AMI vs BERTopic 0.22; LDA seed stability 0.27-0.28; LDA finds no ingredient-labels theme and little politics (OURS: LDA K=20/40 same direction). Our hand merge vs BERTopic's reduce_topics: reduce_topics unstable (AMI 0.49 at 50 topics vs 0.70).
Network (commenter topic-similarity backbone): 2,621 commenters (10+ topic comments), 54,246 of 3,193,803 links (disparity filter, alpha 0.05), Louvain modularity 0.553 (0.549-0.555), 12 communities, agreement across 20 runs AMI 0.79; clustering 0.29 vs 0.0158 (Erdos-Renyi) and 0.038 (degree-preserving rewiring); transitivity 0.272; average path 2.69; assortativity by community 0.568; degree tail not a clean power law (alpha 2.75; lognormal and exponential fit better); centralities correlate (degree/strength/PageRank 0.98-0.99, betweenness 0.82); newcomers 60% of the network and 73% of the 30 most central by betweenness; k-clique percolation (AMI 0.80 at k=12 but only 42% covered) and link communities (poor) vs Louvain.
OURS (network checks): same-density null for communities, modularity 0.505 vs 0.151 shuffled; every community has more internal links than random labels of its size (x1.9 to x23); thread-based commenter network (no topic labels) recovers the politics group only (56% of the politics community in two thread groups) and mostly tracks arrival year; reply network: 20.4% of replies stay in the community vs 18.8% expected from shared threads (ratio 1.09), so communities are topic groups, not interaction groups.
Co-citation (rerun): scholarly network 1,647 papers, modularity 0.635 vs 0.327 rewired; Reddit network 1,971 papers, 0.389 vs 0.216; side assortativity 0.307 and 0.143 vs about 0 under shuffles.
Hostility (GoEmotions, anger/annoyance/disapproval/disgust >= 0.5): r/StopEatingSeedOils 4.76% -> 6.15% (+1.40), r/ScientificNutrition 4.91% -> 4.47% (-0.44). OURS: flagged comments are 65% disapproval, 24% annoyance; direction holds under six definitions, levels do not (0.7% to 13.3% flagged); politics community change is definition-dependent. HAND LABELS STILL MISSING.
OURS (who changed): hostility +1.47 pts among the 2,618 network members: old guard in the same topics +1.06 [0.43, 1.63], topic mix +0.38, newcomers +0.04 [-0.37, 0.51]; downvoted +4.26: newcomers +2.76 [1.87, 3.69]; same 418 long-time people hostile 5.03 -> 6.22. Reply test: no sign that a hostile parent comment makes a hostile reply (-0.38 [-1.86, 1.10]).
Diet communities (rerun): heavy commenters also active in 22 diet subreddits 49.7% -> 63.3%; old guard 73.8 -> 69.0; newcomers 25.4 -> 59.6; r/carnivore itself 12.3 -> 8.7.
Emotions: torchMoji (256 tokens) shifts are small (anger +0.84, laughter -0.85 points in r/StopEatingSeedOils).

## Proposed three figures
1. Activity and topic shift: panel A posts+comments per month in both subreddits with 2024 marked; panel B the fastest-growing and fastest-shrinking topics (log share before/after) or the nine hand themes; caption lists the seed stability range.
2. Commenter network: panel A backbone drawn with the community-preserving layout, coloured by Louvain community; panel B per-community newcomer share and growth in people (x3.6 politics...); null results in the caption.
3. Checks and outcomes: panel A stability (BERTopic 5 seeds vs LDA), panel B hostility under alternative definitions and the hand-label agreement, panel C decomposition of the hostility and downvote change (old guard, topic mix, newcomers).
Tables: one compact table of checks (null, second method, hand check) per claim.

## Cut or demote (no time to validate)
- Stance and paper-quality results (Claude subagent labels, never hand-checked): leave out of the results, or one clearly labelled sentence in the Discussion.
- Co-citation networks: one sentence unless there is room.
- Scattertext/newcomer words: dropped (similar vocabularies, cosine 0.985).

## To settle before writing (needs the authors)
1. Hostility hand labels: 150 comments (30 per score band) in seedoils/data/processed/hostility_sample_to_label.csv; label them yourself, then I compute precision and agreement (required check; no labels, no hostility claim beyond "disapproval signal").
2. Author contributions: who collected data, built which analysis, labelled, wrote which section (needed in the paper; I will not invent it).
3. Our page's carnivore fact (15.3% -> 6.7%) versus the rerun's diet-community measure: use the rerun's.
4. Emoji token limit: our page says 30 tokens, the rerun used 256; use the rerun's.
5. Which community names (the rerun waits for them).

## Schedule
Wed 25 Nov: freeze numbers, hand-label hostility sample, build the three figures as PDFs, outline and draft Methods and Results.
Thu 26 Nov: finish Introduction, Discussion, abstract, significance, references, contributions; compile in Overleaf, trim to six pages.
Fri 27 Nov: slides (3), reflection (half page), final read, hand in before 23:59. Wed 2 Dec: presentation.
