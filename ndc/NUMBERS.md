# Numbers sheet: every number we plan to cite, and where it comes from

Rule: a number goes into the paper or slides only if it is in this sheet. If a script is rerun, check this sheet again.
Status: **CSV** = re-read from the saved file on 14 Nov night; **LOG** = copied from the script's printed output (recorded in ndc/PLAN.md), rerun the script to check.
All scripts run from `final_project/` with `./.venv-nlp/bin/python <script>`.

## Data and sample
| Number | Value | Source | Status |
|---|---|---|---|
| Countries in language network (EU as one) | 154 (13 dropped for missing data) | ndc/notebooks/ndc_common.py (printed) | LOG |
| EU joint-text group collapsed to one node | 29 entries (EU27 + EUU + GBR) | ndc_common.py | LOG |
| Text reliability (split-half, passages) | r = 0.66 (range .63–.69) | ndc/notebooks/ndc_validate.py | LOG |
| Length artefact before control | Spearman(words, mean similarity) = +0.75 | ndc_validate.py | LOG |
| Countries in emission-trend tests | 135 (19 under 1 Mt dropped) | ndc_round3.py / ndc_round4.py | LOG |

## Result 1: who writes alike (language network)
| Number | Value | Source | Status |
|---|---|---|---|
| Network | 154 nodes, 518 edges, mean degree 6.7, k = 5 | ndc/notebooks/ndc_network.py | LOG |
| Louvain communities, modularity | 7 communities, Q = 0.635 | ndc_network.py; ndc/data/processed/ndc_language_communities.csv | LOG (sizes 27,26,25,24,23,18,11 match CSV via Fig 1 legend) |
| Communities vs World Bank region | ARI = +0.40, p = 0.0002 | ndc_network.py | LOG |
| Communities vs income group / emission clusters | ARI = +0.10 / +0.04 | ndc_network.py | LOG |
| Stability (k = 3–15; 20 seeds) | ARI vs k=5: 0.54–0.84; seeds mean ARI 0.78 | ndc_network.py | LOG |
| Edge-layer comparison (ARI) | language–geography +0.44; language–emissions +0.04; language–income +0.05 | ndc_network.py | LOG |
| H1 emission similarity (DSP-MRQAP) | beta = +0.039, p = 0.0006, R² = 0.24 | ndc/notebooks/ndc_tests.py | LOG |
| H2 happiness similarity | beta = +0.002, p = 0.91 (111 countries) | ndc_tests.py | LOG |
| H9 convergence, mean similarity | 0.62 (first) → 0.72 (third); +0.093 [0.067, 0.119], p = 0.0005, 78 countries | ndc/notebooks/ndc_convergence.py | LOG |
| H9 regional clustering change | −0.004 [−0.032, +0.018] | ndc_convergence.py | LOG |
| Idea diffusion (% of 77 countries, first → third NDC) | carbon markets 6→86; methane 26→51; 1.5 °C 9→35; net zero 1→29 | ndc/notebooks/ndc_diffusion.py → ndc/data/processed/ndc_idea_diffusion.csv | CSV |
| H10 neighbours share trends | language r = +0.19 (within-region p = 0.047); geography +0.25 (p = 0.013) | ndc/notebooks/ndc_round3.py | LOG |

## Result 2: say vs do
| Number | Value | Source | Status |
|---|---|---|---|
| Checkable first-NDC pledges | 24; main set 19 (base-year emissions ≥ 1 Mt) | ndc/notebooks/ndc_pledge_check.py → ndc_pledge_progress.csv | CSV |
| Main set: target already met / on track | 5 met by 2023; 7 on track | ndc_pledge_progress.csv | CSV |
| Already met when pledged | 6 (AZE BWA KAZ MDA SRB UKR) | ndc_pledge_check.py | LOG |
| Needed real cuts after 2015 | 13 (H4 sample) | ndc_pledge_check.py | LOG |
| Share of first NDCs not checkable this way | ~85% of 193 | ndc_pledge_check.py | LOG |
| H4 ambition vs progress | rho = −0.09, p = 0.77, n = 13 | ndc_pledge_check.py | LOG |
| 2020 pledges checked | 16 (14 absolute in CSV + China and India intensity) | ndc/notebooks/ndc_pledge2020.py → ndc_pledge2020_outcomes.csv | CSV (14 absolute: 8 met in 2020, 6 in 2019) |
| 2020 pledges met | 10 of 16; ~3–4 policy-driven (EUU, JPN, CHN) | ndc_pledge2020.py; judgement in PLAN.md | LOG + judgement |
| Missed 2020 and on track now | 0 of 6 | ndc_pledge2020.py | LOG |
| DROPPED: H8b hedged wording vs trend 2015–19 | partial rho = −0.16, p = 0.034 (−0.17, p = 0.027 for 2015–23) | ndc/notebooks/ndc_round4.py → round4_firmness_v2.csv | LOG |
| DROPPED: Hand-check precision | hedged 10/10, firm v2 ~6/10 | round3_h8_handcheck.csv, round4_firm_v2_handcheck.csv | CSV (read by hand) |
| DROPPED: H12 within income × region | rho = −0.17, p = 0.064 (not significant) | ndc_round4.py | LOG |
| DROPPED: H11 firmness first → third NDC | median −0.61 → −0.32; firmer in 53/95; p = 0.019 | ndc_round4.py → round4_firmness_rounds.csv | LOG |

## Result 3: strategies vs parliaments
| Number | Value | Source | Status |
|---|---|---|---|
| Countries (goal-window view / all speeches) | 18 / 20 (incl. translated ES, BE) | ndc/notebooks/lts_vs_parliament.py --with-translated | LOG |
| P-A median rho per theme | +0.26, p = 0.007 (all speeches +0.44, p = 0.0002) | same | LOG |
| P-B own vs other parliaments | +0.51 vs +0.34; own better in 16/18; p = 0.008 | same | LOG |
| P-C gaps (Fig 3) | removals 4.7×, land 4.1× … energy 1/1.7 | lts_vs_parliament_profiles_with_translated.csv (recomputed in paper_figures.py) | CSV |
| H13 parliament attention vs trend | raw −0.29; partial on income −0.06, p = 0.40 (26 parliaments) | ndc/notebooks/parliament_attention.py → parliament_attention_vs_trend.csv | LOG |
| Parliament climate attention | median 2.2% of speeches (2015–17) → 5.2% (2020–22); rose in 24/26 | parliament_attention.py | LOG |

## Figures (ndc/figures/paper/, PDF + PNG, made by ndc/notebooks/paper_figures.py from saved CSVs only)
- fig1_language_network: double column; network coloured by community and by region.
- fig2_say_vs_do: double column; A first NDC 2023 vs pledge (MNE clipped, flagged), B 2020 pledges with 2019 shown.
- fig3_strategy_vs_parliament: single column; theme gaps.
- fig4_hedging_and_diffusion: panel A (hedged wording vs trend) DROPPED by decision on 15 Nov, do not use; panel B (ideas spreading) uses my own keyword list, same caveat, keep only if the list is justified.

## Dropped analyses
- Hedged vs firm wording (H8, H8b, H11, H12): dropped on 15 Nov. Effect small (rho about -0.16), keyword lists chosen by me and not validated against published practice. Rows above kept only as a record; do not cite.

## Known corrections
- 14 Nov night: earlier notes and the first paper plan said "13 checkable first-NDC pledges". Correct: 19 checkable (main set), of which 13 needed real cuts after 2015. PAPER_PLAN.md fixed.
