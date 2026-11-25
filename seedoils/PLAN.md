# Seed oils on Reddit: a myth's rise and the evidence (started 18 Nov 2026)

Origin: The Pudding, "Is Sleep Training Harmful?" (2024). It compared online opinion (one Reddit thread, hand-coded; Google News; Instagram)
with the research consensus (75 clinical trials), then traced the few sources the anti side cites. This strand applies that design
to the claim that seed oils (soybean, canola, sunflower, corn...) are toxic or inflammatory, using full subreddit histories instead of one thread.
Chosen 18 Nov over breast vs formula (more nuanced evidence, weaker news hook) and DraCor/novel-character personality ideas.
Related to the UPF strand (both about food and processing). User decision 18 Nov: kept as a SEPARATE strand, not merged into the UPF story.

## Data
- Reddit via Arctic Shift (https://arctic-shift.photon-reddit.com, by u/RaiderBDev): per-subreddit history to the present.
  The Academic Torrents dumps (ba051999...; 2005-06 to 2024-12, 3.12 TB) only come as whole-of-Reddit monthly files (~30 GB each);
  the old per-subreddit torrent linked from Watchful1/PushshiftDumps now 404s. No licence is stated for the dumps: cite as research data,
  keep text local (gitignored), publish only aggregates and short paraphrases.
- seedoils/notebooks/fetch_arctic_shift.py: resumable, standard library only; output seedoils/data/raw/<sub>_<posts|comments>.jsonl.gz.
  Tested 18 Nov: StopEatingSeedOils posts 11,642, no duplicate ids, rerun adds 0.
- Core subreddits (sizes from Arctic Shift metadata, 18 Nov): r/StopEatingSeedOils 11.5k posts / 241k comments (since 2018);
  r/ScientificNutrition 14.1k / 175k (since 2018); r/carnivore 33k / 304k (since 2011). Later: r/nutrition (1.9M comments), r/keto, r/ketoscience (192k).
- The aggregate endpoint (yearly counts) and body full-text search time out under load; paging by created_utc works.

## First look (18 Nov, samples)
- Growth, all 11,642 r/StopEatingSeedOils posts by year: 2018 29, 2019 32, 2020 125, 2021 456, 2022 955, 2023 2,038, 2024 4,099, 2025 2,766, 2026 1,142 (to 18 Nov).
  Busiest months Sep-Nov 2024 (430-466 posts/month). 5 of the 8 top-scoring posts are about RFK Jr. (Oct-Dec 2024); another is a restaurant switching to beef tallow (May 2024).
  r/ScientificNutrition is flat by comparison (1,300-2,400 posts/year since 2019).
- Post links in r/StopEatingSeedOils: mostly reddit.com crossposts (6,748) and images (1,590); papers too: pubmed 227, sciencedirect 182, mdpi 107, nature 54, frontiersin 52; youtube ~500.
- 1,000 most recent comments per subreddit (Nov 2026; carnivore's 1,000 span Jun-Nov):
  share with links: StopEatingSeedOils 3.9%, ScientificNutrition 10%, nutrition 5.7%, carnivore 1%.
  Mentions of study/trial/RCT/meta-analysis per 1,000: 18 vs 187 (ScientificNutrition). The anti side talks mechanisms (omega-6/linoleic 46, oxidation/rancid 19,
  tallow/butter 59, RFK/MAHA 17); the research side talks outcomes (heart/CVD 109, cancer 39). Minnesota Coronary Experiment / Sydney Diet Heart: 0 in the samples.
  Shared commenters in the samples: SESO-SciNutrition 9, SESO-carnivore 6, SESO-nutrition 6, SciNutrition-nutrition 20.
  CAUTION: keyword counts, not stance labels; one recent slice of each subreddit.

## Research side (from memory, VERIFY each before use)
- Cochrane, Hooper et al. 2020: reducing saturated fat ~17% fewer CV events; benefit tied to replacement with polyunsaturated fat.
- Marklund et al. 2019, Circulation (pooled cohorts): higher circulating linoleic acid, lower CVD.
- Johnson & Fritsche 2012 (systematic review of RCTs): more linoleic acid does not raise inflammatory markers.
- AHA presidential advisory on dietary fats (Sacks et al. 2017).
- The anti side's strongest sources: Ramsden et al. re-analyses of the Sydney Diet Heart Study (2013) and Minnesota Coronary Experiment (2016),
  plus non-trial figures (e.g. Knobbe, Shanahan, Ray Peat). These are the "Sears and Narvaez" to trace.

## Planned strands (not yet pre-declared)
1. Timeline: posts/comments per month vs news events (RFK Jr. campaign and nomination, MAHA, restaurant tallow switches).
2. Claims: lexicon/keyword families (mechanism vs outcome language) per subreddit and over time; later stance labelling on a hand-labelled sample.
3. Networks from the same data: (a) subreddit co-commenter network (who also posts where; Louvain), needs author histories for top commenters;
   (b) subreddit x cited-domain bipartite network (PageRank of sources); (c) DOIs/PMIDs cited -> OpenAlex -> co-citation network: do the papers each side cites sit in different clusters, and are the anti side's papers on topic (the Pudding/Mindell check, automated).
4. Reply networks inside threads (who argues with whom across communities).

## Main network: subreddit co-commenter network (chosen 18 Nov)
Question: where does seed-oil scepticism live on Reddit -- with diet communities (carnivore, keto, animal-based) or with
political/contrarian ones -- and did that change with the 2024 RFK Jr./MAHA surge?
- seedoils/notebooks/fetch_author_histories.py select: seed authors = most active commenters (>= 5 comments, top 1,500 per seed subreddit)
  in StopEatingSeedOils, ScientificNutrition, carnivore, from the full comment downloads. Excludes [deleted], AutoModerator, *bot.
- ... fetch: WHOLE-history posts + comments per subreddit for each author via /api/users/interactions/subreddits, one request per
  period (before / from 2024-01-01), so 2 requests per author. Resumable. (First version paged each author's latest 1,000 comments;
  replaced 18 Nov: on the same 45 test authors it saw a median of 300 interactions vs 4,625, 37 vs 163 distinct subreddits, and 0 vs 31
  authors with any pre-2024 activity -- the cap would have emptied the before-2024 network.)
- Rate limits (Arctic Shift API docs, read 18 Nov): "a couple requests per second" is fine; limits are dynamic (server load, query cost);
  a 429 carries X-RateLimit-Reset, which both scripts now wait out. No published hard quota. The docs ask heavy users to prefer the dumps.
  Fallback if we get blocked: the "2005-06 - 2023-12 top 40k subreddits" per-subreddit torrent (academictorrents 56aa49f9...,
  listed in ArthurHeitmann/arctic_shift download_links.md) covers the core subreddits up to 2023; 2024+ would still need the API or the
  monthly dumps (~30 GB per month for all of Reddit).
- seedoils/notebooks/build_cocommenter_network.py: author--subreddit bipartite (>= 3 comments) -> subreddits with >= 25 seed authors ->
  projection weighted by lift = S_ij N / (k_i k_j) (1 = independence; damps AskReddit-type subreddits), edges with lift > 1 and >= 5 shared authors ->
  Louvain (seed 42), modularity, weighted PageRank, betweenness on 1/lift; per-subreddit lean (+1 only seed-oil commenters, -1 only
  ScientificNutrition commenters, normalised by camp size). --period all|pre2024|from2024, --drop-seeds.
- Pipeline test 18 Nov on 45 sample authors (300 comments each; outputs deleted, too small to interpret): 68 subreddits, 334 edges, 5 communities, Q = .37.
  It already separates an animal-based/raypeat/SaturatedFat/exvegans/rawprimal community (positive lean) from one holding
  ScientificNutrition/nutrition/ketoscience (negative lean). Treat as a smoke test only.
- To add later: null model for modularity (degree-preserving rewiring of the bipartite graph), backbone filtering (disparity filter)
  if the projection is too dense, and stability of communities across Louvain seeds.
- Cost estimate: ~4,000 authors x 2 requests = ~8k requests. Test speed 18 Nov (while the comment download shared the API): 45 authors in
  5 min 10 s (~7 s per author) -> ~8 h for 4,000; likely faster once the download finishes. Run after the comment downloads, never alongside.

## BERTopic on r/StopEatingSeedOils (18 Nov, seedoils/notebooks/seso_topics.py; EXPLORATORY, not pre-declared)
- Docs: comments and self-posts with >= 15 words after cleaning (quotes '>' and URLs removed; bots/AutoMod/[deleted] dropped):
  149,732 docs (142,814 comments, 6,918 self-posts), median 35 words, 19,341 authors. Pre-2024 34,637 docs, from 2024 115,095.
  The 15-word cut drops 39% of comments (93,773); only ~3% of those are pure reactions (lol/thanks/this/agreed); many are short on-topic
  replies ('tallow', 'source'). Share kept falls from 65% (2021-23) to 59% (2024): the surge brought shorter comments (state in methods).
- all-MiniLM-L6-v2 on MPS; UMAP(15, 5 dims, cosine, seed 42) + HDBSCAN(min_cluster_size 150, min_samples 15) + c-TF-IDF (English + Reddit
  filler stopwords, min_df 20, 1-2 grams; proper nouns KEPT). 129 topics; 41% outliers before embedding-based reassignment.
  Several near-duplicate generic 'seed oils' topics (16, 27, 84, 109, 127) -> candidates for merging (reduce_topics) later.
- Shift with the 2024 surge (share of docs, pre-2024 -> from 2024; 'confident only' = docs HDBSCAN assigned before reassignment, same direction):
  RFK (46, 117) .03% -> .87% (confident 1.14%); Trump/left-right politics 0.55 -> 2.15%; vaccines/covid 0.36 -> 1.08%;
  pharma/FDA/corporations 2.5 -> 4.6%; conspiracy/media 0.39 -> 0.73%; ingredient labels/processed/natural flavors 1.1 -> 2.3%;
  shopping (Costco, avocado oil, chips) 2.7 -> 4.5%. Shrinking: PUFA/linoleic mechanism 11.6 -> 6.7% (still the largest topic),
  keto/carbs/fasting 4.5 -> 2.3%, Tucker Goodrich/podcasts 0.74 -> 0.48%. Science/evidence talk flat (3.4 -> 3.7%).
  Reading: the surge moved the community from biochemistry and low-carb diets towards politics, institutional distrust and shopping.

## Relative upvotes (18 Nov, seso_topics.py votes; seedoils/data/processed/seso_topic_votes.csv)
- Raw scores are not comparable: mean comment score ~2 (2018-19) vs ~4.2 (2024-25); median 2; 38% at score 1; 8% <= 0.
- Measure: percentile rank of score within the same thread AND level (top-level vs reply), ties averaged; threads with >= 5 comments at that
  level; comments < 3 days old excluded (scores settle after ~36 h). 228,139 comments scored, 134,525 of them in the topic model.
  Mean percentile of topic-model comments .542 (> .5 because the reference also contains the short, low-voted comments).
- By theme, from 2024 (mean percentile; share in their thread's top 10%): labels/processed .562; pharma/FDA/corporations .557;
  PUFA mechanism .555; politics .544; shopping .543; RFK .525 (top-10% share .155, high for its mean -> possibly polarised, check);
  conspiracy .523; keto .521; studies/science/evidence .507; meta reddit/sub/evidence .496; vaccines/covid .470 (lowest).
  Reading (TENTATIVE): talk about evidence and studies is the least rewarded; distrust-of-institutions talk the most. Topic is not stance:
  low votes on evidence topics may be outside sceptics being downvoted. Needs stance labels or author camp (from the network) to separate.
- Next: polarisation per topic (share in bottom 10% as well as top 10%); split by author camp once the co-commenter data exists.
- Thread diversity check (19 Nov): threads with >= 5 topic-model comments (6,369) hold a median of 8 topics; the most common topic takes a median
  33% of a thread; only 3.8% of threads are >= 80% one topic. Same-topic neighbours of a typical comment: evidence/science topics ~5%,
  RFK 2-11%, vaccines 16%, politics 19%, PUFA 24% -> their vote contrasts come from mixed threads (well identified). Clustered niche topics
  (pets 46%, baby formula 44%, sunscreen 43%, cast iron 41%) are shrunk towards .5; treat with caution. The within-thread measure cannot
  see between-thread differences (whether whole RFK threads draw more votes); a post-level measure (post score vs same-month posts) would.

## BERTopic on r/ScientificNutrition (19 Nov; same script and settings, outputs scinut_*)
- 121,672 docs (117,181 comments, 4,491 self-posts), median 52 words, 10,826 authors. 117 topics; 37% outliers before reassignment.
- Largest: meta/'evidence, paper, comment' (0) 8.7% -> 11.7%; keto/insulin 9.4 -> 6.9%; protein; weight/calories; LDL/apoB/CVD; vegan; supplements.
- Grew from 2024: creatine x3.8, gut microbiota x3.4, coronary plaque/CAC/LMHR (lean-mass hyper-responders) x2.9, ultra-processed/NOVA x2.6
  (overlap with the UPF strand), industry funding/bias x1.8, '95% CI' statistics talk x1.8, cognition/dementia x1.7.
  NO political topic surfaced (no RFK/Trump/vaccine topic among the 117).
- Seed-oil-related topics are small and flat or shrinking: PUFA/SFA 1.0 -> 0.7%; seed oils/canola 0.8 -> 0.9%; linoleic acid 0.6 -> 0.3%;
  omega-6:3 ratio 0.4 -> 0.3%. The 2024 seed-oil surge did not spill into the research community.
- Votes (149,742 comments scored; topic-model comments mean .555). Best received from 2024: cognition/dementia .632, '95% CI'/risk statistics .619,
  meal timing .598, choline/TMAO .595, cancer risk .593. Worst: moderation/submission rules .390, causation vs correlation .470,
  epidemiology-is-weak arguments .474, Hong Kong/Okinawa pork .477, farming/land .480, atherosclerosis mechanism .490, Inuit/Maasai/ancestral
  populations .495, nutrition-science meta .502, FFQ validity .502.
  Reading (TENTATIVE): r/ScientificNutrition downvotes the classic moves AGAINST nutritional epidemiology ('correlation is not causation',
  FFQs are invalid, 'the Inuit/Maasai ate meat') -- the mirror of r/StopEatingSeedOils downvoting evidence talk from 2024. Votes look like a
  measure of agreement with each community's position, not of comment quality. Author camp split needed to confirm.

## Cited papers, both sides (19 Nov; seedoils/notebooks/cited_papers.py; cited_papers_summary.txt, cited_works.csv)
- Ids from URLs in posts and comments (PubMed, PMC, DOI, nature.com). First run stopped on a malformed DOI ('...634394-,a': the comma is
  OpenAlex filter syntax); fixed DOI cleaning (Reddit '\_' escapes, commas, figure/media suffixes) and batch bisection on HTTP 400; 0 ids rejected after.
  OpenAlex: ~420 requests total, no key, no contact email sent.
- Coverage: SESO 3,996 citations -> 2,552 resolved (64%), 1,715 distinct works; SciNut 29,851 -> 20,045 (67%), 11,700 works.
  Not covered at all: links without an id in the URL (SESO 2,134; SciNut 12,047: ScienceDirect, MDPI, OUP, JAMA, most BMJ).
- Study design from MeSH (citation-weighted): humans only SESO 51% vs SciNut 63%; animal-only SESO 17% vs SciNut 8% (2x);
  humans+animal/cell 15% vs 14%; no MeSH 13% both. Reviews 25% vs 27%. Newer on the seed-oil side (2020s 41% vs 33%).
  Median OpenAlex citation count of cited works 47 vs 70. Retracted works: 1 of 1,715 vs 15 of 11,700 (similar rate, ~0.1%).
  OpenAlex 'field' puts much nutrition under 'Nursing' (37% / 20%): a classification quirk, do not report as such.
- Most widely cited by distinct users. SESO: Astrup et al. 2020 'Saturated fats and health: a reassessment' (16 users); Ramsden et al. 2016
  Minnesota Coronary Experiment re-analysis (12); Deol et al. 2015 soybean oil obesogenic (mouse study; 11); Simopoulos 2002 omega-6/3 ratio
  review (10); Ramsden et al. 2013 Sydney Diet Heart re-analysis (10); then several animal studies (hairless-mouse photocarcinogenesis 1996,
  tumour initiation 1992, linoleic acid in induced disease 1989, endocannabinoids 2012).
  SciNut: AHA presidential advisory on dietary fats 2017 (22); total cholesterol and mortality 2019 (20); 'LDL causes ASCVD' consensus 2017 (20);
  Cochrane reduction in saturated fat 2020 (20); Mozaffarian 2010 PUFA meta-analysis (17; also 7 SESO users); 'LDL-C does not cause CVD' 2018 (17,
  a contrarian review, likely cited to argue against); Hamley 2017 replacing SFA with n-6 PUFA (17); Marklund 2019 omega-6 biomarkers (15).
- 466 works are cited in both subreddits: the shared battleground for a co-citation network.
- This VERIFIES as real and central: Hooper 2020 Cochrane, Marklund 2019, AHA 2017 advisory, Ramsden 2013/2016. Johnson & Fritsche 2012 not seen yet.
- Johnson & Fritsche 2012 (linoleic acid and inflammation markers, RCT review) found in the network: 5 SESO / 7 SciNut users. All five papers
  on the from-memory research list are now verified as real and cited.

## Co-citation networks (19 Nov; seedoils/notebooks/cocitation_network.py; cocite_nodes.csv, cocite_*_edges.csv, cocite_summary.txt)
- Nodes: works cited by >= 2 distinct users: 1,985 (SciNut-only 1,479; both 418; SESO-only 88). Citing users SESO 513, SciNut 1,293; 49 cite in both.
  CORRECTED 19 Nov: the '418 of 506 (83%)' first reported is inflated by the pooled threshold (a paper with 1 SESO + 1 SciNut user counts).
  Proper overlap, papers the seed-oil side cites that r/ScientificNutrition also cites: all 1,712 papers 27% (465); weighted by mentions 42%
  (1,055 of 2,542 citations); papers cited by >= 2 seed-oil users 60% (134 of 222); >= 3 users 80% (74 of 92); >= 5 users 92% (33 of 36).
  Reading: the seed-oil side's CORE papers are almost all also discussed on the research side; its long tail of one-off links is mostly its own.
  'Cited by both' says nothing about direction: a paper may be cited in support by one side and to rebut by the other, or in support by both.
  Direction needs stance labels on the citing comments (not done).
- Reddit co-citation (same user cites both; Newman 1/(k-1) weights): 1,969 nodes, 167,668 edges, 23 communities, Q = .389, side assortativity .141.
  The seed-oil canon forms its own community (c1, 248 works, 20% animal: Ramsden 2013 Sydney, Ramsden 2016 Minnesota, Deol 2015 soybean-oil
  mouse study, hairless-mouse skin cancer 1996), separate from the mainstream fat/LDL canon (c2, 226 works, 3% animal: LDL-causes-ASCVD 2017,
  AHA 2017 advisory, Mozaffarian 2010, Cochrane 2020, Hamley 2017). A third, mixed community (c3, lean +.20) holds the contrarian reassessments
  (Astrup 2020, 'LDL-C does not cause CVD' 2018, cooking oil and deaths 2021). The rest are SciNut-only clusters (protein, plant-based, keto,
  hunter-gatherers, meat and cancer...).
- Scholarly citation (one references the other, OpenAlex): 1,643 nodes, 6,244 edges, 45 communities, Q = .643, side assortativity .306
  (HIGHER than on Reddit). The omega-6/linoleic literature is its own cluster (c2, lean +.06: Marklund 2019, Simopoulos 2002, Deol 2015,
  Farvid 2014 LA meta-analysis, Johnson & Fritsche 2012). An animal-carcinogenesis cluster (c9, 50 works, 58% animal vs 0-6% in most others;
  rodent studies 1985-2004 on dietary fat and UV/mammary tumours) carries the seed-oil skin-cancer argument.
- Agreement of the two partitions: AMI .071 -> users pair papers ACROSS scholarly clusters (an argument pairs a seed-oil paper with the
  mainstream paper it disputes), so Reddit communities are argument structures, not literature fields.
- Bridges (Reddit network, sampled betweenness): works cited by both sides .0012 vs SciNut-only .0004 vs SESO-only .0001. Top bridges: the
  plant-based vs ketogenic trial 2021, Chowdhury 2014 fatty acids meta-analysis, LDL-causes-ASCVD 2017, Hamley 2017, AHA 2017, and the
  contrarian 'LDL-C does not cause CVD' 2018: the contested core.
- Story reading: the debate is not two literatures but two readings of one; the seed-oil side's distinctive evidence is a small cluster of
  re-analyses plus rodent mechanism studies, while the outcome trials and meta-analyses sit in the mainstream cluster both sides cite.
- Caveats: >= 2 users threshold; only 64-67% of scholarly links resolved; side label 'both' includes works one side cites to rebut.
- NULL MODELS (19 Nov; seedoils/notebooks/cocitation_null.py; cocite_null_summary.txt, cocite_null_runs.csv). Null 1 = degree-preserving
  double-edge swaps (2 per edge; Reddit weights shuffled onto rewired edges), 50 reps, Louvain on each; null 2 = side-label permutation, 200 reps.
  Scholarly: modularity .635 vs null .327 +/- .002 (excess +.31); side assortativity .306 vs null .000 +/- .010 (label shuffle -.001 +/- .011).
  Reddit:    modularity .388 vs null .217 +/- .001 (excess +.17); side assortativity .141 vs null -.004 +/- .002 (label shuffle -.001 +/- .002).
  All far beyond chance (z 28-241). z is NOT an effect size here: the null SDs are tiny and smaller for the denser Reddit graph, so report the
  excess over the null instead. As expected, a large part of the raw modularity gap was density: random sparse scholarly graphs already reach .33,
  random dense Reddit graphs .22. Beyond chance the scholarly network is still more clustered (+.31 vs +.17) and more side-segregated (.31 vs .14).
  (Community counts differ by 1-3 from the first run, 44 vs 45 and 20 vs 23, because Louvain depends on node order when loaded from the edge
  CSVs; modularity is unchanged to two decimals.)
- STABILITY + LABELS (19 Nov; seedoils/notebooks/cocite_communities.py; cocite_communities_<network>.csv, cocite_node_communities.csv,
  cocite_communities_summary.txt). 20 Louvain seeds per network (edges loaded in a fixed order); reference partition = run with the highest mean
  AMI to the others; community stability = share of runs keeping its paper pairs together; labels = top OpenAlex topics + c-TF-IDF title words.
  SCHOLARLY is stable: modularity .631-.644, 42-48 communities (13-16 with >= 20 papers), mean pairwise AMI .79. Stable labelled communities:
    omega-6 / linoleic acid (200 papers, stability .65, lean +.12, the ONLY seed-oil-leaning community; 44 SESO-only, 96 both);
    rodent dietary-fat carcinogenesis (40, stability .92, 68% animal, median year 1992; 31 of 40 cited by both sides);
    saturated fat and CVD (135, .86, lean -.38; 62 cited by both: Astrup 2020, AHA 2017, Mozaffarian 2010, Hamley 2017);
    oxidised oils / AGEs / frying (33, .90); olive oil / Mediterranean (30, .67); LDL / lipoproteins (124, .94: LDL-causes-ASCVD 2017 and the
    contrarian 'LDL-C does not cause CVD' 2018 together); then research-side-only fields: meat and mortality cohorts (246), keto / low-carb (236),
    vegetarian / vegan (166), sugar / metabolic (74), protein / muscle (73), hunter-gatherers / foods (62), vitamin D / omega-3 supplements (48), fasting (37).
  REDDIT is NOT stable: modularity .382-.392 but 17-24 communities, mean pairwise AMI .52; most communities have stability .28-.41. Only three hold
  (.65-.82): the seed-oil canon (242, .82: Ramsden 2013/2016, Deol 2015, hairless-mouse 1996), a polyunsaturated-fat/mortality mix (187, .65,
  lean +.13) and plant-based / protein meta-analyses (240, .67). Do not interpret the other Reddit community labels.
  So: the scholarly partition is the one to label and report; the Reddit network is better summarised by side assortativity and bridges than by
  its communities.

## Dive: the four seed-oil communities (19 Nov; seedoils/notebooks/dive_communities.py; dive_summary.txt)
Baseline share of each side's paper citations made from 2024: SESO 61%, SciNut 34%. Vote pct = within-thread percentile of citing comments.
- Omega-6 / linoleic (c2): SESO 423 citing docs / 155 users, SciNut 650 / 155 users (same number of people on each side). From 2024: SESO 58%
  (slightly BELOW its baseline), SciNut 28%. Vote pct SESO .514, SciNut .585.
- Rodent fat carcinogenesis (c10): few people, many citations: SESO 83 docs / 16 users, SciNut 309 / 29 users (202 of them inside the linoleic-acid
  topic). An OLD debate: from 2024 only SESO 36%, SciNut 4%. Highly upvoted on both sides (.727, .781): long, detailed exchanges.
- Saturated fat and CVD (c4): SESO 247 / 95 users, SciNut 835 / 160. From 2024: SESO 75% (ABOVE baseline), SciNut 33%. Votes .560 / .617.
- LDL / lipoproteins (c5): SESO 63 / 36 users, SciNut 629 / 136. From 2024: SESO 73% (ABOVE baseline), SciNut 26%. Votes .540 / .571.
Reading: with the 2024 surge the seed-oil side's citing moved from omega-6 mechanisms and rodent studies towards saturated fat and LDL
(the 'saturated fat is fine / LDL does not matter' frame), matching the topic-model shift away from biochemistry.
In every community the research side's citing comments are better received in their own community than the seed-oil side's are in theirs.
- Stance sheet: 177 items (8 most both-sided papers per community, up to 3 random citing comments per side per paper, seed 7), blind and shuffled:
  stance_sheet.csv to label (S supports / D disputes / N neutral / ? unclear, plus focus), stance_key.csv holds side and community. Both gitignored.
  First build cut comment text at 1,500 characters (86 of 177 cut); rebuilt with full text (median 1,447, max 38,969 characters); same items, same order.
- STANCE PLAN (user decision 19 Nov): hand-label first, then test models against the hand labels; scale up only if agreement holds (kappa >= .6).
  Labelling page: seedoils/label_stance.html (built by make_stance_label_tool.py; offline, progress in localStorage, keys S/D/N/U or 1-4;
  exports stance_labels.csv -> seedoils/data/processed/). Gitignored (holds Reddit text).
  After labelling: stance_eval.py summary (stance by side x community) and stance_eval.py zeroshot (MoritzLaurer/deberta-v3-large-zeroshot-v2.0,
  ~1.7 GB download, local; accuracy, Cohen's kappa, confusion table). An LLM labeller is the other candidate; it would send public Reddit
  comments to an external API, so it needs the user's go-ahead.
  CITATION WINDOWS (user decision 19 Nov, ~300 words): 133 of the 177 comments contain >= 2 links and 47 exceed the model's ~380-word limit, so
  each item now has a window of 150 words either side of the first link to THAT paper (found via the same identifier extraction as the citation
  table); the cited link is marked [[CITED STUDY LINK]], other links [other link]. Link found in 168 of 177; the other 9 are link posts (paper =
  post URL), shown from the start of the post. Window median 155 words, max ~330. Same 177 items and order (key file unchanged).
  The labelling page shows the window with the link highlighted and the full comment collapsible; stance_eval.py zeroshot classifies the window.
  Hand labels are the REFERENCE: the zero-shot model does not train on them, so all labelled items are its test set; a few-shot LLM would use
  ~20 labelled items as examples and the rest as test. Only after agreement is measured is the model applied to all citing comments.
  LABELLING AID (19 Nov, after the user found it hard to code support/dispute without knowing each paper's conclusion):
  (1) codes reworded to how the commenter TREATS the paper: S = uses it as evidence for their point; D = attacks or discredits it (rats, methods,
  observational, funding, misread); N = neutral / bare link; U = cannot tell. Same letters, so any labels already saved in the browser carry over.
  (2) each item shows the paper's conclusion and its full abstract: abstracts for the 32 papers in the sheet from OpenAlex (abstract_inverted_index;
  27) plus PubMed efetch (5) -> seedoils/data/raw/sheet_abstracts.json; conclusion = text after a CONCLUSION/INTERPRETATION label, else the last
  two sentences (rough for unstructured abstracts: use the full abstract then). The zero-shot hypotheses were reworded to the same codes.
  Side check: subreddit names appear only inside 2 comment texts (commenters naming a subreddit), not in the page data otherwise.
  LLM REFERENCE LABELS (19 Nov; user found hand-labelling too hard and asked Claude to label): one Claude subagent labelled all 177 items BLIND
  (citation window + paper title, conclusion, abstract; no side) -> stance_labels_claude.csv (item_id, stance, claim, confidence, reason ≤ 20 words;
  gitignored with the other stance files). Codebook as on the page plus claim accuracy when S (matches / overstates / misrepresents / unclear) and
  the Minnesota example as the worked case. Confidence: high 77, medium 79, low 21. NOT human-validated: report as LLM annotation; an optional
  human spot-check of ~20 items (incl. the user's 3 page labels) would give a human-LLM agreement figure.
  RESULT (stance_eval.py summary --labels stance_labels_claude.csv): overall S 142 (80%), N 29, D 6, U 0.
    omega-6: SESO S 75% D 12% N 12% | SciNut S 62% D 0% N 38%.  rodent carcinogenesis: SESO S 89% | SciNut S 77%, no D on either side.
    saturated fat: SESO S 71% N 29% | SciNut S 96%.  LDL: SESO S 83% | SciNut S 91%.
    Claim accuracy when used as evidence: SESO matches 73%, overstates 16%, misrepresents 1%, unclear 9% (n=67);
    SciNut matches 77%, overstates 11%, misrepresents 4%, unclear 8% (n=75). Small n; no clear difference between sides.
  READING: the hypothesis 'one side uses a shared paper as evidence, the other attacks it' is NOT supported: attacks are rare (6 of 177) and BOTH
  sides mostly use the same papers as evidence, i.e. for opposite conclusions, by leaning on different findings of the same paper (e.g. Minnesota:
  'no mortality benefit' vs 'lowers cholesterol'). The contest is over which finding counts, not over the paper's credibility. Overstating happens on
  both sides at similar rates in this sample.
  ZERO-SHOT MODEL vs LLM labels: accuracy .23, Cohen's kappa .07 (high-confidence items: accuracy .21). It labels most evidence-uses as neutral (96)
  or attack (36). Unusable for scaling; do not use. (Caveat: tested against LLM, not human, labels; but the gap is too large to be a reference artefact.)
  Ready-made options checked and rejected: scite.ai (citations inside papers only, commercial), SciCite-type citation-intent models (intent, not
  agreement), tweet stance models (fixed targets such as abortion).

## ALIGNMENT: online vs scientific community (19 Nov; seedoils/notebooks/{paper_abstracts,build_comment_sample,alignment}.py;
## alignment_summary.txt) -- the Pudding-style core result
Design (user, 19 Nov): instead of labelling how a comment treats a paper, label (1) what each PAPER concludes about seed oils / LA / PUFA, from its
abstract, and (2) what POSITION each COMMENT takes on seed oils; then compare and match. All labels are blind LLM annotations (Claude subagents) with
reasons and confidence, not human-validated; codebooks in the scratchpad copies were: papers relevance/direction/outcome/population/design/claim;
comments H harmful / NH not harmful / M mixed / O no position (stated avoidance for health = H; SFA defence without a PUFA claim = O).
- Papers: the 499 papers of the four seed-oil communities; abstracts for 487 (OpenAlex 370 + PubMed 117) -> papers_to_label.jsonl; three agents
  (omega-6; saturated fat + rodent; LDL), shared codebook -> paper_labels_{omega6,satfat_rodent,ldl}.csv (no Reddit text). Confidence high 393 / medium 95 /
  low 11. Agent rule to watch: omega-6 agent coded 'LA lowers omega-3 status, no clinical outcome' as harm -> sensitivity row below.
- Comments: 698 blind items (comments_to_label.jsonl + comments_key.csv, gitignored): OPINION sample = 100 random comments mentioning seed-oil terms
  (>= 15 words) per subreddit x period (eligible pools 2,151-32,253), CITING sample = 150 per side of documents citing one of the 499 papers.
  Three agents by item range. QUALITY FIXES: agents first labelled from a text prefix (600-1,400 characters); all re-read long items in full
  (changes: part1 13 positions + 7 confidence of 89 rechecked, part2 3, part3 5 positions + 6 confidence; mostly O -> H/NH), and four items coded
  inconsistently across agents (SFA fine / replacement not clearly supported; 243, 275, 386 'M', 631 'H') were harmonised to O like the identical items
  of the other agents. Final: H 276, O 277, NH 123, M 22; confidence high 282 / medium 253 / low 163.
RESULTS
- Science (242 of 499 papers relevant): harm 43%, benefit 36%, no effect 12%, mixed 10% overall -- but by evidence type:
    human trials / meta-analyses of trials (n=80): benefit 46%, harm 21%, no effect 20%;  human observational (55): benefit 42%, harm 38%;
    animal / cell (58): HARM 79%;  reviews / statements (45): split 44% benefit / 42% harm.
    Human studies with hard outcomes (82): benefit 55%, harm 23%, no effect 15%. Mechanistic outcomes: harm 81%.
    Sensitivity without harm verdicts resting on intermediate markers: harm 38%, benefit 39%.
  CAVEAT: these are the papers REDDIT CITES (in four communities), not a systematic sample of the literature; the harm share is inflated by what
  users bring up. Within it, the human-trial and hard-outcome evidence leans to benefit; the harm verdicts come mostly from animal/cell work.
- Online (opinion sample, share of all / of those taking a position):
    r/StopEatingSeedOils pre-2024 H 71% / 92%; from 2024 H 65% / 80% (NH rose 3% -> 13%).
    r/ScientificNutrition pre-2024 H 35% / 53%, NH 27% / 41%; from 2024 H 21% / 36%, NH 29% / 49%, M 9%.
    The research subreddit was itself split before 2024 and moved towards 'not harmful' from 2024; the seed-oil subreddit stays overwhelmingly 'harmful'.
- Matching (citing sample): comments saying 'harmful' (n=86) cite papers that conclude harm 68%, benefit 6%; their evidence is 32% animal/cell, 25%
  human trials. Comments saying 'not harmful' (n=51) cite papers concluding benefit 62%, harm 5%; evidence 54% human trials, 2% animal/cell.
  Same pattern within each subreddit. Both sides cite evidence that agrees with them; the difference is the KIND of evidence: the harm case rests on
  animal/cell studies three times as often, while the human trials and hard outcomes in the same cited literature mostly do not show harm.
- FIGURES (19 Nov; seedoils/notebooks/alignment_charts.py -> seedoils/figures/): science_by_evidence.png, online_positions.png, matching_evidence.png.
  100% stacked bars; harm/'harmful' red, benefit/'not harmful' blue (diverging pair), mid grey = mixed, light grey = no effect / no position in both;
  evidence types on violet / aqua / yellow / magenta (no red or blue, so colours keep one meaning across the set; validated: worst adjacent CVD dE 9.1,
  normal-vision 19.6; three slots < 3:1 contrast so every segment >= 6% is direct-labelled plus a legend). Captions state LLM labelling and the
  cited-papers selection.
- Reading: misalignment is concentrated in r/StopEatingSeedOils (80-92% 'harmful' among comments with a position vs 23% harm among human hard-outcome
  papers); r/ScientificNutrition is closer to the human evidence, and moved further towards it from 2024.

## Who changed in 2024? (19 Nov; seedoils/notebooks/who_changed.py; who_changed.txt; downloaded comments only)
- Turnover: only 14% of r/ScientificNutrition's from-2024 commenters (7,596) commented there before 2024; r/StopEatingSeedOils 9% of 22,356
  (it grew from 5,677). Both subreddits are mostly NEW people from 2024.
- SESO's link to the diet communities weakened: share of SESO commenters who ever comment in r/carnivore 15.3% (pre-2024) -> 6.7% (from 2024);
  in r/ScientificNutrition 8.5% -> 3.7%. The surge crowd came from outside both (preview of the co-commenter network question).
- In r/ScientificNutrition, SESO commenters wrote a GROWING share of comments: 22% -> 36%.
- Finding 1 (SciNut moved towards 'not harmful'): its 'harmful' comments come largely from seed-oil-community members visiting: authors also
  commenting in SESO 43% (pre-2024) and 62% (from 2024) for 'harmful' vs 7% and 31% for 'not harmful'; 'harmful' authors from 2024 also
  carnivore 57%. From 2024, 41% of 'not harmful' authors are new to SciNut. Reading: the seed-oil view inside SciNut is largely carried by visitors from
  SESO/carnivore, and the from-2024 shift coincides with near-total turnover of SciNut's commenters.
- Finding 6 ('not harmful' rose inside SESO): 85% of those authors are NEW to SESO in 2024 (vs 54% of 'harmful' authors) and only 8% also comment
  in SciNut: the dissent inside SESO comes from newcomers, not from research-community members arriving to argue.
- Small n (13-71 per cell): tentative. Positions are LLM labels.

## ARTIFACT: 'Seed Oil Debate' (19 Nov; https://claude.ai/artifact/MYSMGLgGVhmAe4fJ2VdXjj, private until shared) -- six figures for the 6-page report and 3-page talk
Built on the claude.ai 'Data' artifact type: every figure draws from an uploaded JSON dataset (rows + meta incl. the script text), page source = seedoils/artifact/index.html,
data builder = seedoils/notebooks/artifact_data.py -> seedoils/data/processed/artifact/*.json (aggregates and paper titles only; no usernames, no comment text).
Figures (page order): 1 community map of the 1,591 cited papers (bubbles = scholarly-citation communities, dots = papers, colour by community or by who cites; hover = title and links);
2 bridge papers (betweenness on the Reddit co-citation network, PageRank on the citation network) + null model (observed vs 50 random networks, modularity and side assortativity);
3a/3b/3c science vs online vs evidence cited (the alignment charts); 4 topic themes before/from 2024 (share on log scale, or reception), r/StopEatingSeedOils and r/ScientificNutrition;
5 emotion by theme and period (sentiment strand); 6 where seed-oil commenters also post (network + before/after share), PRELIMINARY.
Community-map layout: the contested core links almost every community, so a link-based layout collapses; bubbles are placed by normalised cross-links and pushed apart, papers inside by spring layout.
Run: ../.venv/bin/python seedoils/notebooks/artifact_data.py; then re-upload changed JSON (Artifact asset upload) and update datasets/<id> in the artifact store.
Emotion strand (seedoils/notebooks/emotions.py; emotion_scores.csv.gz has ids and scores only, no text): SamLowe/roberta-base-go_emotions, threshold 0.5, max 256 tokens, PROVISIONAL
(emotion-classifier choice still open with the TAs; not validated by hand here). Sample: up to 1,200 docs per SESO theme and period + 3,000 random per subreddit and period.
 Hostile share (anger, annoyance, disapproval, disgust): SESO all 4.9% -> 6.5%; SciNut all 4.8% -> 4.8%; SESO 'studies & evidence' 5.6 -> 9.5, vaccines 7.2 -> 9.5 (n=125 before),
 ingredient labels 4.5 -> 8.3, shopping 3.2 -> 5.8, politics 11.5 (n=200 before) -> 9.4. Positive share is higher in SESO (~20%) than SciNut (~14%); curious/confused falls in both.
 Reading: most comments are neutral or friendly; hostility rose in the seed-oil subreddit, concentrated in evidence, vaccines and label talk; the research subreddit stayed flat.
Figure 6 status: built from the author histories fetched so far (1,946 of 4,292 at 19 Nov 12:30; all 1,500 SESO regulars + 525 SciNut + 103 carnivore); 50 subreddits (top 30 by commenters + 14 risers + 14 fallers);
 layout Kamada-Kawai on all pairs with lift > 1, draws each subreddit's 4 strongest links; Louvain groups (news/politics/science, advice/everyday life, diet/biohacking) have modularity ~0.07: rough corners only.
 Largest shifts in share of active seed-oil commenters also posting there (before -> from 2024): r/Biohackers 14 -> 36, r/AmIOverreacting 0 -> 23, r/AITAH 9 -> 24, r/AnimalBased 8 -> 23, r/carnivorediet 10 -> 23;
 r/science 26 -> 12, r/worldnews 27 -> 14, r/funny 27 -> 10, r/keto 27 -> 19. To refresh when the fetch is done: rerun artifact_data.py, re-upload facts + the three cocomment files, update their dataset records.
SCROLLYTELLER DRAFT (19 Nov, from the artifact's Design page; draft id ypd1x67mfj7v, written to drafts/ypd1x67mfj7v/files/index.html; the live dashboard page is untouched until an editor presses Save):
 built by seedoils/notebooks/build_scrolly_draft.py from seedoils/artifact/index.html -> seedoils/artifact/draft_scrolly.html. 13 chapters beside one sticky chart that changes with the chapter in view
 (IntersectionObserver, root: document); it reads the dashboard's own datasets; a print layout gives each chapter its own chart. Left out versus the dashboard: the controls (colour switch becomes two chapters;
 PageRank list, r/ScientificNutrition topics and the other emotion groups are not shown; the risers/fallers chart is cut to 16 rows) and the long notes (condensed into the last chapter).
 Tested locally: all 13 chapters render in the print path with no errors; scroll switching worked on two runs with a visible pane (the pane was hidden later, so the last build's scroll wiring was not re-run).
 The real dashboard's check for the draft had not been read at hand-over (the page draws the draft only when the person's view shows it).
Real-dashboard check passed after one fix (a drawn element stored with text). Browser downloads are blocked inside artifacts, so static PNGs for the report still come from matplotlib (alignment_charts.py exists; the other figures do not yet).

## What each side rewards (19 Nov, seedoils/notebooks/vote_features.py; vote_features.txt)
Same within-thread percentile; text markers are keyword regexes (not stance labels); contrasts compare comments of 16-100 words with vs
without the marker, so length does not drive them. SESO 224,414 scored comments; SciNut 131,816.
- Length is rewarded on both sides (SESO 1-5 words .489 -> 100+ .557; SciNut .468 -> .563) -> any rating must control for length.
- Questions are penalised on both sides (SESO -.045, SciNut -.026).
- Paper links: SciNut +.058 (pre +.045, from 2024 +.080; 6.7% of comments); SESO -.003 (pre +.018, from 2024 -.013; 0.7% of comments).
- Study/trial/evidence words: SciNut +.017; SESO -.036, and it is a 2024 change: pre-2024 +.002, from 2024 -.045.
- Hedging (may/might/suggests/associated): SciNut +.026; SESO +.005.
- Distrust words (industry/FDA/propaganda/lobby...): SESO +.028 (pre +.050); SciNut +.010.
- 'Seed oils are bad' words (toxic/inflammatory/rancid/oxidised/engine oil...): SESO +.021; SciNut +.010.
Reading (TENTATIVE): r/ScientificNutrition rewards citing and hedging; r/StopEatingSeedOils rewards distrust and harm language, and after
the 2024 surge began to penalise evidence talk. Same stance confound as above (evidence talk in SESO may come from outside sceptics).
Rating strategy implications: (1) control for length and questions; (2) model the within-thread percentile with all features + topic in one
regression per subreddit x period, so effects are adjusted for each other; (3) split SESO comments by author camp (also posts in SciNut or not)
to separate 'the community dislikes evidence' from 'outsiders citing evidence get downvoted'.

## Log
- 18 Nov: subreddit sizes checked; samples above; downloader written and tested; full downloads of posts + comments for the three core subreddits started (background).
- 18 Nov: user chose to keep seed oils as a separate strand from UPF.
- 18 Nov: user chose the subreddit co-commenter network as the main network; author-history fetch and network build scripts written and smoke-tested (see above).
- 18 Nov 15:54: download PAUSED by the user. Complete: posts for all three subreddits (SESO 11,642; SciNutrition 14,273; carnivore 33,266).
  Partial: StopEatingSeedOils comments 161,068 (no duplicates, file intact), up to 2024-12-03. Not started: ScientificNutrition and carnivore comments.
  Resume (picks up from the newest saved comment; repairs a cut-off file first):
  `../.venv/bin/python seedoils/notebooks/fetch_arctic_shift.py StopEatingSeedOils comments`, then the same for ScientificNutrition and carnivore.
- 18 Nov 17:06: download resumed; StopEatingSeedOils comments complete 17:4x: 243,097 comments (4,469 = 2% by [deleted] accounts), 26,128 named commenters.
- 19 Nov: comment downloads COMPLETE: SESO 243,097 (2018-10 -> 2026-11-18), SciNut 177,788 (2018-10 -> 2026-11-18), carnivore 303,979
  (2011-10 -> 2026-11-17); no duplicate ids. Full selection (defaults: >= 5 comments, top 1,500 per subreddit): SESO 7,111 eligible, SciNut 3,012,
  carnivore 8,223 -> 4,500 rows, 4,292 distinct authors; 192 in two or more lists (SESO+carnivore 68, SESO+SciNut 63, SciNut+carnivore 45, all three 16).
  The SESO list is identical to the early SESO-only selection. Author-history fetch (2 requests per author) started in the background.
- 18 Nov: seed-author selection, seed-oil side only (`select --subreddits StopEatingSeedOils`, defaults >= 5 comments, top 1,500;
  copy kept as data/processed/seed_authors_StopEatingSeedOils.csv because a later full `select` overwrites seed_authors.csv).
  7,111 commenters have >= 5 comments; the top 1,500 have >= 29 (median 54, max 3,134) and wrote 60% of all comments (top 100: 21%; top 10: 7%).
  First comment year of the 1,500: 2018-2022 273, 2023 353, 2024 674, 2025-26 200 -> about half of the core joined in the 2024 surge.
  524 were active both before and from 2024: a panel for the before/after comparison.

## Introduction section (19 Nov, from user request): 'Where the comments come from' (before 'One body of research')
- notebooks/intro_data.py -> datasets subreddits, activity (posts+comments per month, Oct 2018 on, last unfinished month dropped), events (3 public news dates, hand-added). Cards for the three subreddits + monthly line chart with shaded 23 Aug-14 Nov 2024.
- Honest framing: the data show WHEN (SESO items/month 3,197 Dec 2023 -> 6,203 Jan 2024, peak 15,949 Sep 2024; SciNut flat), not WHY. The jump starts in Jan 2024, before the RFK Jr. events, so politics is not the whole story; no dated news coverage was collected, so the cause is untested.
- Also this day: Figure 2 on the dashboard is now 'case files' (top 4 papers by betweenness/PageRank joined by red string; solid = directly linked, dashed = steps apart). The scroll draft (drafts/ypd1x67mfj7v) was NOT liked; the regular dashboard stays the main page.

## Who are the people? Two cohorts of heavy commenters (19 Nov; notebooks/who_hangs_out.py -> data/processed/who_hangs_out.csv)
- Cohorts = the 1,500 heaviest r/StopEatingSeedOils commenters (all-time comment count; author histories fetched, 4,287 of 4,292 done): OLD = first comment before 2024 (626), NEW = first from 2024 (874).
  Share of cohort with >= 3 posts+comments in a subreddit, before / from 2024.
- Where NEW came from (their pre-2024 activity): general-audience subs (AskReddit 34%, pics 18%, funny 16%, mildlyinfuriating 16%, facepalm 15%), NOT diet subs (keto 6%, Biohackers 4%, carnivore 3%, SaturatedFat 1%).
  OLD pre-2024: SaturatedFat 40%, keto 36%, ketoscience 21%, carnivore 21%, Biohackers 20% (and AskReddit 61%: older accounts are active everywhere).
- From 2024 NEW vs OLD: mildlyinfuriating 37 vs 22, AmIOverreacting 25 vs 14, AITAH 24 vs 18, SipsTea 23 vs 13, TikTokCringe 18 vs 11, FluentInFinance 17 vs 10; OLD higher in SaturatedFat 29 vs 14. OLD cohort's own diet-sub activity also fell (SaturatedFat 40 -> 29, keto 36 -> 17).
- Caveats: heavy commenters only (median ~52 comments each; the 874 new are 4% of the 22,356 newcomers, the rest are mostly one-off visitors); old accounts are older so more active everywhere; ">= 3 interactions" threshold; no causal claim (arrival route unknown).

## Reply network of the 1,500 heaviest commenters (19 Nov; notebooks/network_heavy.py; nodes csv per period, aggregates only)
- Edge A->B = A's comment is a direct reply to B's comment/post, both in the heavy set (81,803 replies all time; 63,027 from 2024). OLD (626) / NEW (874) as in who_hangs_out.
- From 2024 (fair comparison): 1,394 commenters tied, 30,192 ties, density .031, average shortest path ~2.2 (same-cohort 2.16, cross 2.23). Ties old-old 14%, old-new 43%, new-new 43% = close to random mixing for 37/63 shares.
  Cohort assortativity .068 vs shuffled labels -.002 (sd .005): weakly above chance. Louvain 9 communities, modularity .25; largest has 42% new.
  Top 30 by PageRank and by betweenness: 53% new (cohort share 63%) -> the old guard is over-represented among hubs (47% vs 37%). Median replies received: old 15, new 28; 83% of OLD still tie vs 100% NEW.
- All time: assortativity .307 (null -.002), modularity .289, one old-guard community of 371 members that is 2% new; top-30 PageRank 27% new. Mechanical: old accounts have had more years to be replied to.
- Caveats: induced subgraph of heavy commenters only (not the many one-off visitors); dense (everyone ~2 replies apart), so path lengths barely discriminate; replies are not agreement (replies include arguments); betweenness approximated from 500 sampled sources.

## Flairs (19 Nov; notebooks/user_flair.py, topic_vs_post_flair.py)
- POST flair coverage jumped from 30% of posts before 2024 to 84% from 2024 (flairing became near-universal; 'miscellaneous', 'Product Recommendation' ... barely exist before). Use only within 2024+.
- Validity of the 130 BERTopic topics against thread flair (docs from 2024 with a thread flair: 91,027 of 115,095): NMI 0.055 vs 0.022 +- 0.001 when flairs are shuffled across threads: above chance, weak because 7 coarse flairs vs 129 topics.
  Sensible alignments (lift = flair share / overall share): Product Recommendation -> Costco/store 3.0, bread 3.0, chips 3.2, eggs 2.1; Peer Reviewed Science -> omega-6/PUFA 3.7 (22.6% of its comments), studies 3.2;
  Seed-Oil-Free Diet Anecdote -> butter 2.2, mayo 2.2; Blog Post -> vaccines 3.1, pharma 1.8; 'Keeping track of seed oil apologists' -> generic seed oils 2.6 / reddit meta 2.0; Video Lecture -> Trump/politics 7.5, RFK 5.4 (a surprise: probably videos of politicians).
- USER flair (self-declared, 26,803 comments, 12% of comments from 2024 vs 6.5% before) is used by few, heavy accounts: ~470 authors from 2024 (83 old, 389 new). Options were added over time (Avoider/Omnivore/Ray Peat Jul-Aug 2021; Vegan Jul 2023; Skeptical of SESO, Low Fat, Keto Oct 2023),
  so before/after 2024 shares are partly mechanical. Among flaired authors from 2024: Avoider 41% old vs 39% new, Omnivore 12% vs 24%, Skeptical 2 vs 4% (n=2 and 16). Quarterly composition is noisy (a few heavy accounts): Avoider share rises from 28% (2023Q4) to ~49% (2026Q2). No strong claim possible.

## COMMENT POSITION CODEBOOK v2 (19 Nov; seedoils/notebooks/position_codebook_v2.md, compare_codebooks.py)
User asked how comments were labelled and how to handle comments that are not about the harm claim. v2 = two steps: (1) relevance (is the comment about whether seed oils / LA / PUFA harm health?), (2) position H / NH / M / NP
(on the claim, no verdict) for relevant ones. Tighter rules: health harm only; a quoted study counts only if adopted; insults alone do not decide; passing mentions are off the claim; saturated-fat or sugar talk alone is off the claim.
Relabelled all 698 comments blind by four Claude agents (full text, no side/date/old labels) -> data/processed/comment_labels_v2.csv; 120 items labelled again by a fifth agent -> comment_labels_v2_repeat.csv.
RESULTS (new mapped to old: off-claim and NP -> O): agreement with v1 84.2%, kappa 0.755; where both take a position 95.5% (337 items), H<->NH flips 3. Biggest change: 50 of v1's 276 H and 28 of 123 NH become off-claim / no position (implied or passing).
New relevance: 420 on the claim, 278 off the claim (40%) although every item mentions a seed-oil term; NP 72. Test-retest of v2 (n=120): agreement 90.8%, kappa 0.85, relevance 91.7%.
Figure 4b shares among position-takers barely move (SESO pre 92 -> 94% H, from 2024 80 -> 81% H, NH 4 -> 4% and 16 -> 18%; SciNut 53 -> 54% and 36 -> 37% H): the conclusion is robust to the rewrite.
CAVEAT: all labellers are Claude; agreement between runs is not accuracy and errors may be shared. Human spot-check still needed.

## COMMENTER TOPIC NETWORK + BACKBONE (19 Nov; commenter_topic_network.py [--export], commenter_network_datasets.py) -> main artifact Figure 7 / 7b
Question (user): connect commenters who talk about the same sub-topics; avoid the hairball; find the backbone communities.
Nodes: 2,618 r/StopEatingSeedOils commenters with >= 10 topic-model comments (>= 15 words), 106,783 comments (75% of topic comments). Profile: counts over the 50 data-driven topics (k=50 merge), IDF-weighted, L2-normalised; similarity = cosine -> complete network, 3,417,947 links.
BACKBONE: disparity filter (Serrano, Boguna, Vespignani 2009), alpha 0.05, edge kept if significant for at least one end. Why: dense similarity network; a global threshold would keep mostly heavy commenters' edges; the filter judges each link against the node's own link strengths.
REMOVED: 3,417,947 -> 8,652 links (99.75% removed); 788 of 2,618 nodes (30%) left with no link (not drawn); one giant component of 1,830 nodes.
Communities: Louvain, 20 seeds on the giant component: modularity 0.744, 13-16 communities, membership agreement AMI 0.95 across seeds; 10 communities of >= 100 people. Alpha sensitivity: agreement with alpha 0.05 is 0.85 (0.01), 0.79 (0.02), 0.62 (0.1). Null (topic labels permuted among comments, 5 reps): 0-44 backbone links vs 8,652.
Isolated people are NOT generalists: they put 56% of their comments in the general seed-oil topic (topic 40, 42% of all comments) vs 35% for linked people; 73% of people with >= 60% of comments there are isolated. Isolation rises with volume (24% for 10-19 comments, 56% for 100+).
Findings: communities are topic niches by construction (food and oil niches, politics, vaccines/fluoride, LDL, labels, sugar/carbs...). Long-time share differs by community beyond chance (permutation p = 0.013): politics 22% long-time, labels 27%, olive oil 29%, eggs/raw milk 53%; overall 40%.
Growth (engaged commenters, comments per month 2022-23 -> from 2024: 1,010 -> 2,308): general core x1.8 (34% of growth), politics x11.9, olive oil x5.2, vaccines/fluoride x5.0, labels x4.5. CAUTION: newcomer share and growth are linked by construction (a newcomer's comments are all from 2024), not independent evidence.
Artifact: datasets cn_nodes, cn_edges, cn_comms + facts cn_*; page version 29. Test page (private): Commenter Communities. Not yet checked in the live dashboard (nobody had it open); rendered correctly in the local harness.

## NICHE BRIDGES AND NICHE EMERGENCE (20 Nov; niche_bridges.py, niche_emergence.py)
Stretched commenters (degree >= 6 and >= 25% of links outside own community; 196 of 1,830) have higher betweenness in the backbone: median rank 224 vs 1,014 of 1,830, mean 6.0 vs 0.96 (x1000); 17% are in the top 5% by betweenness (5% by chance); betweenness correlates 0.68 with share of links outside own community, 0.61 with degree. The top-betweenness nodes are hubs (80-200 links) with 13-48% cross-community links. 55% of nodes have all links inside their own community. Betweenness here is about network position, not content flow (no interaction data in this network).
User niche growth, active people per month (communities from the all-period backbone), 2022-23 -> from 2024: politics 5.0 -> 33.2 (x6.7), labels x4.1, olive oil x3.6, vaccines x3.0, general core x1.9; sum 196 -> 450. Same ranking as comment volume. Circularity caveat as before (newcomers' activity is all from 2024).
Same method run separately by period: before 2024 only 641 commenters with >= 10 topic comments (68% with no link, giant component 161, no community of >= 50 people); from 2024 2,093 commenters, 12 communities of >= 50. Matching by topic profile (cosine): politics 0.11, vaccines + seed oils 0.01, LDL 0.04 (no pre-2024 counterpart); labels 0.85, bread/condiments 0.83-0.91, eggs 0.92, infant formula 0.83 (established niches). CAUTION: the before-2024 communities are tiny (7-32 people), so 'no match' may mean too few people to form a niche then.
Replies: 19% of replies between niche members stay inside the niche vs 8% by chance (x2.4), identical before and after 2024 (4,061 and 20,367 replies). Topical threads make this partly mechanical.

## NICHE OUTCOMES: HOSTILITY AND DOWNVOTES ON THE BACKBONE (20 Nov; niche_overlay_data.py -> artifact/niche_network.json; test page Niche Network v4)
Per-niche hostile / downvoted shares before and from 2024 with 95% intervals for the change (resampling people, 400 reps). Hostility CLEARLY rose (interval above zero) only in: condiments/snacks (3.6 -> 5.8), olive oil (3.9 -> 6.5), sugar/carbs (4.1 -> 7.0) and the general core (5.0 -> 6.7). Politics (8.7 -> 6.9, CI -4.7..+0.7) and vaccines (9.0 -> 8.1, CI -3.9..+1.5) were already the most hostile niches before 2024; the change cannot be told from zero (only 355 and 575 comments before 2024).
Politics theme (5 BERTopic topics, all commenters): 200 comments before 2024 (149 people), hostile 11.5% -> 9.3%, change -2.2 pts, CI -6.5..+2.3; positive unchanged (19.5 -> 19.4).
DECOMPOSITION of the overall hostile rise (4.76% -> 6.15%, +1.39 pts, all documents with topics): within-theme change +1.13 (of which +0.79 'all other topics', 71% of documents), shift in topic mix +0.26 (politics +0.23: more discussion moved into a topic that is more hostile than average, although its own rate did not rise). Politics holds only 4.6% of all hostile documents from 2024 (3.0% of documents x 9.3%); 66.7% of hostile documents are in topics outside the eight themes.
Downvotes clearly rose in condiments/snacks, olive oil, eggs/raw milk, vaccines (5.6 -> 13.0), skin/sun and the general core.

## MAIN PAGE: FIGURES 8 AND 9 (20 Nov; niche_network_datasets.py -> datasets nn_nodes, nn_comms, nn_months; edges reuse cn_edges; page version 30)
Figure 8: the Figure 7 backbone with a month slider and play button (people appear the month they first commented; people from before 2022 are there from the start; legend counts per niche; note: 40 of 184 politics people had appeared by end of 2023 vs 93 of 175 in eggs and raw milk). Figure 9: the same map coloured by each person's shrunk share of hostile or downvoted comments, all time / before 2024 / from 2024. The change-by-niche colour views and the niche table were removed at the user's request (test page Niche Network v5 has the same two figures). Notes under Figure 9 are drawn from nn_comms (95% intervals for the change; politics and vaccines unclear). Rendered in the local harness; not yet checked in the live dashboard.

## MAIN PAGE: FIGURES 7 AND 8 MERGED (20 Nov; page version 31)
At the user's request the table (old Figure 7b) was removed and the static backbone map (old Figure 7) and the timeline (old Figure 8) were merged into one Figure 7: one map with the colour toggle (community / newcomer or long-time), the month slider and play button (default: all months, i.e. the full network), legend counts per niche or cohort as the slider moves. The outcome map is now Figure 8. The permutation p-value (0.013) for differences in long-time share moved into the 'How we did this' box. Rendered in the local harness; not yet checked in the live dashboard.

## MAIN PAGE: STORY REWRITTEN (21 Nov; page version 32)
Title now 'Same papers, new crowd, harsher tone'. Lead paragraphs rewritten around the later findings: shared core literature with differences at the edges (harm case leans on animal studies; human trials mostly benefit/no effect), commenters per year 4,334 -> 14,605 in 2024 with the conversation moving from omega-6 chemistry towards politics, vaccines and distrust of industry; the surge faded within two years but comments stayed harsher (hostile, mostly in food and diet niches that had been mild before; more downvoted); data show when and who, not why. All numbers are fact marks from facts.json.

## MAIN PAGE: ACTIVITY CAPTION SHORTENED (21 Nov; page version 33)
At the user's request the activity caption under 'Activity per month' is now one sentence with no numbers (seed-oil subreddit activity jumped at the start of 2024 and peaked that autumn, the research subreddit stayed flat); the data-drawn caption (actlede) was removed. The two disclosures it carried (last month left out as incomplete; shaded dates are public news added by hand) moved to the 'How this was made' list.
