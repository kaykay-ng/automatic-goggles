# What still has to be re-run on the teammate's rerun data (written 25 Nov 2026)

Decision (KK, 25 Nov): the teammate's rerun is the reference. My analyses from 21-25 Nov were computed on the 18-21 Nov download and the pre-rerun rules, so their numbers are superseded (see the banner in PLAN.md).
The rerun's big files are not in git (gitignored: raw Reddit data, documents with text, embeddings, score arrays). Either she shares her `seedoils/data/raw/` and the processed files below privately (they hold Reddit text and usernames: not GitHub, not a shared folder others can open),
or the raw data is re-downloaded with notebooks/fetch_arctic_shift.py (public archive; then the pipeline takes hours: embeddings, topic model, emotion and emoji scoring).

## Already done by her on the rerun (use these, do not re-run mine)
BERTopic topics, themes, stability across seeds, LDA K=123, commenter network and communities (+ community names), network measures and community methods, reply network and reply questions, diet-community overlap, co-citation networks, tone hand labels (three labellers; categories H/C/N), negation and alias checks, paper-label checks, dashboard datasets. Summaries: seedoils/artifact/rerun_results.html and PLAN.md 22-25 Nov.
She also re-ran my earlier scripts community_null.py, commenter_thread_network.py, commenter_reply_network.py and hostility_robustness.py (PLAN.md 25 Nov, community names entry); ask her for their printed results (not saved in the repo).

## Superseded by hers (my script stays for reference only)
| My script | Replaced by |
|---|---|
| lda_compare_k20_k40.py | lda_compare.py (K=123, 3 seeds) |
| hostility_agreement.py, make_hostility_label_tool_sampleA.py | hostility_eval.py and her labelling page (3 labellers) |
| commenter_reply_network.py, reply_exposure.py | reply_network.py, reply_findings.py |
| newcomer_terms.py, newcomer_terms_check.py, lol_and_trolling.py | dropped (vocabularies almost identical) |

## Only mine: to re-run before any number is used
| Finding (old-pipeline direction) | Script | Inputs needed from her |
|---|---|---|
| DONE 26 Nov on raw_haoyu (output seedoils/data/processed/thread_trees_rerun.txt; result: little change, marginal flattening, mostly gone within post type; see REPORT_PLAN.md). Was: Reply-tree shape per post: flatter threads after 2024, SciNut deeper and unchanged | thread_trees.py | raw comments and posts of both subreddits (decide: keep bots as tree nodes, exclude them from author measures) |
| Where newcomers entered: popular posts, food-product and question threads, few political threads | newcomer_entry_threads.py | raw comments and posts |
| Where newcomers came from: general Reddit, not diet communities | newcomer_origins.py | author_subreddit_counts*.jsonl.gz and seed_authors.csv (her 2,919 heavy commenters), raw comments |
| Growth began in 2023; Google Trends interest rose from 2022 and peaked 6 months after the subreddit | google_trends_compare.py, reddit_monthly_activity.csv | raw comments (bots removed by her rule); the Trends CSV stays valid; her activity.json already has monthly items per subreddit |
| Topic mix in 2023 and January-August 2024: politics near 0.5% until July, 6.7% in August; first shifts vaccines, pharma, labels | inline code (to be saved as a script); needs themes_confirmed.json instead of my hard-coded topic ids | seso_doc_topics.csv.gz, seso_topics_info.csv, themes_confirmed.json |
| Document-network communities by year: same ~15 regions, 2024 a reweighting | doc_network_by_year.py | seso_docs.csv.gz, seso_vectors.npy, seso_doc_topics.csv.gz |
| People vs topic vs newcomers: tone change mostly old guard, downvotes mostly newcomers | people_vs_topic.py | raw comments, seso_doc_topics.csv.gz, goemo_seso.npz (15+ words only now), commenter_topic_network_130_nodes.csv |
| Dialectograms r/StopEatingSeedOils vs r/ScientificNutrition (exploratory) | dialectograms_seso_scinut.py (switch its tokenizer to seedoil_common.bertopic_clean) | seso_docs.csv.gz, scinut_docs.csv.gz |

## Notes
- Terms (KK decision 26 Nov): use GoEmotions' own names (the groups and the 28 emotions). The old "disapproving tone" flag and the word "hostile" are retired. Script and file names that contain the old word are kept so they can be found.
- Her decision: emotion scores on 15+ word documents only, everywhere; my reply_exposure.py used all comments (short ones too), so it is not comparable.
- r/carnivore comments are not used; the seed sample for author histories is r/StopEatingSeedOils and r/ScientificNutrition only. My filter that keeps only r/StopEatingSeedOils authors in the cross-subreddit figure is in artifact_data.py but her datasets in the repo were built without it.
