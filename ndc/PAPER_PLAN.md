# Paper plan (PNAS template, 6 pages including references) — drafted 14 Nov 2026

Deadline Fri 27 Nov 23:59 (paper, 3 slides, half-page reflection). Presentation Wed 2 Dec. In-room sessions 18 and 25 Nov.
All numbers below come from ndc/PLAN.md; re-check each against the CSV/script output before it goes in the paper.

## One story (the sentence both of us must be able to say)
"Countries' climate pledges are written in the language of their region, not of their emissions, and the pledges
can rarely be checked; where they can, delivery owes more to history and COVID than to policy. National long-term
strategies and national parliaments do stress the same sectors, but strategies lean on land and removals while
parliaments talk energy."

Title (working): "Who sounds alike in climate pledges? Geography, not emissions, and few promises we can check"

## Research questions (each maps to one Results subsection)
RQ1 Say: what organises how countries write about climate (emissions structure, income, happiness, region)?
RQ2 Say vs do: for pledges that can be checked, were they kept?
RQ3 Plan vs talk: do parliaments discuss the sectors that their own long-term strategy stresses?

## Section budget (6 pages, two columns ≈ 1,000 words/page incl. figures; target ≈ 3,200 words + 4 figures + 1 table)
| Section | Words | Content |
|---|---|---|
| Abstract | 150 | Question, data, three findings, one limit |
| Significance statement | 100 | Plain-language, ≤120 words (PNAS rule) |
| Introduction | 400 | Pledges vs delivery; why language + network; three RQs; hypotheses pre-declared |
| Results 1: language network | 600 | Fig 1. H1 beta +0.039 (tiny); H2 happiness +0.002 p=.91; communities vs region ARI +0.40 (p=.0002) vs emissions +0.04; rewired null; layer comparison (language-geography +0.44, others ≤0.05) |
| Results 2: say vs do | 600 | Fig 2 (2015 NDC progress) + Fig 3 (2020 pledges). 19 checkable 2015 pledges (13 needed real cuts after 2015), 7 on track; H4 rho −0.09 (n=13); 2020: 10 of 16 met but only ~3–4 look policy-driven; 0/6 that missed 2020 are on track. EU member decomposition: 3 sentences (descriptive) |
| Results 3: strategies vs parliament | 500 | Fig 4. P-A median rho +0.26 (n=18, p=.007); P-B own parliament +0.51 vs others +0.34 (16/18); P-C gaps: removals +2.23, land +2.02 ... energy −0.73, transport −0.35 |
| Discussion | 450 | What it means; limits (below); what a stronger design needs |
| Methods | 600 | Data sources, embeddings, kNN network, Louvain, nulls, DSP-MRQAP, pledge rules, translation, term lists |
| References | ~15 | PNAS style |

## Figures (existing, need redrawing at PNAS column width, ≥8 pt fonts, colour-blind-safe)
1. ndc/figures/language_network.png — language communities vs region (two panels). Keep.
2. ndc/figures/pledge_vs_emissions.png + pledge2020_vs_outcome.png — merge into one two-panel say-vs-do figure.
3. ndc/figures/lts_vs_parliament_with_translated.png — theme gap plot.
4. Word plot (wordplot_agri_vs_energy.png) only if space allows; otherwise supplement/slide.
Table 1: layer comparison (ARI matrix) — small.
Drop EU decomposition figure to supplement; mention in text.

## What to cut or reframe
- Food/FAOSTAT/ParlaMint-trade work: not the paper's story. ParlaMint appears only as the parliament corpus in RQ3 (one Methods paragraph). Optional one sentence: an earlier trade-network question was closed as trivial. Decide together.
- Network-science requirement: carried by the language kNN network, Louvain, degree-preserving null, edge-layer comparison. If a grader wants a trade network, the FAOSTAT networks are the fallback (not planned).
- Happiness: report as a pre-declared null (H2), one paragraph, no separate story.

## Honest limits that must appear (Discussion), one line each
- NDC summaries/early rounds; language reliability 0.66 (attenuation); length artefact controlled.
- Checkable pledges are few (19 + 16) and skewed to rich and post-Soviet countries; 2023 is not 2030.
- Emissions data are modelled; LULUCF treatment varies; Montenegro data mismatch.
- LTS comparison: n=18–20, shared circumstances confound, document types differ, machine translation, national vs EU/other-country talk not separated.
- Machine-translated parliaments (ParlaMint English MT); regex lists are broad (instruments/energy include generic words).

## Open decisions before drafting (need both of you)
1. Do the national-vs-EU talk separation (≈half a day) or state it as a limit? Recommendation: state as limit unless time remains after the first full draft.
2. Include the word plot in the paper or only on slide?
3. Who owns what (everyone must answer on any part):
   - Person A: Results 1 + Methods (network, nulls, regression). Person B: Results 2 and 3 (pledges, LTS). Both: Intro, Discussion, slides.
   - Swap-explain rule: each writes a 5-line explainer of the other's part by 22 Nov.

## Timeline (today is Sat 14 Nov)
- 15–16 Nov: result freeze; regenerate figures at paper size; build a one-page numbers sheet (every number → script → CSV).
- 17 Nov: LaTeX skeleton from PNAS template, Methods + Results text from PLAN.md.
- 18 Nov (in-room): get feedback on story and figures; ask the one open question from the decisions above.
- 19–21 Nov: full draft; 22 Nov: swap-explain; 23–24 Nov: revise, trim to 6 pages, check every claim against the sheet.
- 25 Nov (in-room): final checks. 26 Nov: slides (3) + reflection (half page). 27 Nov: submit before 23:59; do not wait for the last hour.
- 28 Nov–1 Dec: rehearse the 3-minute talk; prepare answers for the hard questions (below).

## Questions we must be able to answer cold
- Why is a cosine similarity between embeddings meaningful here? (split-half 0.66, validation)
- Why Louvain, and how do we know the communities are not noise? (rewired null, 20 seeds, k sweep)
- What does DSP-MRQAP do and why not plain regression? (dyads not independent)
- Why can only 19 of ~190 first pledges be checked? What is excluded and why? Which rule was added after seeing results (tiny emitters)?
- Why is "met 2020" mostly not policy? (post-Soviet base, COVID)
- What does "own parliament +0.51 vs others +0.34" show and what does it not? (shared circumstances)
- How were the term lists made and checked? What is their precision?

## Reflection (half page, ungraded)
Draft from the AI-drafted-report boxes: what the AI got wrong (BAU claim, wrong EU benchmark, regex false positives, reversed colour scale), what we checked by hand.
