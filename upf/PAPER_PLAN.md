# Paper plan: UPF story (PNAS template, 6 pages incl. references) — drafted 16 Nov 2026

Replaces ndc/PAPER_PLAN.md (NDC story set aside). Deadline Fri 27 Nov 23:59 (paper, 3 slides, half-page reflection). Presentation Wed 2 Dec.
In-room sessions 18 and 25 Nov. All numbers come from upf/PLAN.md; re-check each against its script output before it goes in the paper.
OPEN: classifier choice awaits the TA's reply (see upf/PLAN.md 'OPEN QUESTION FOR THE TAs'). OPEN: reconcile with the partner's trade/policy-diffusion work.

## One story (the sentence both of us must be able to say)
"On Amazon, ultra-processed food is sold with slightly warmer, livelier words of pleasure, while less processed food is sold with calm words of purity.
The people who review ultra-processed food cluster together in the shopper network, also review more games and toys and fewer sports and health products,
and write warmer reviews everywhere. The differences in wording are small; the differences in who shops together are large."

Working title: "Sold on pleasure: how ultra-processed food is marketed, and who reviews it, on Amazon"

## Research questions (each maps to one Results subsection)
RQ1 SELL: Is ultra-processed (NOVA 4) food marketed with different emotional language than less processed food in the same category?
RQ2 SHOP: Do the people who review ultra-processed food form their own part of the shopper network, and what else do they review?
RQ3 FEEL: Do those shoppers write differently, and how far can lexicons and classifiers be trusted to measure emotion in reviews?

## Section budget (≈ 3,200 words + 4 figures + 1 table)
| Section | Words | Content |
|---|---|---|
| Abstract | 150 | Question, data (75,933 matched listings, 2.5M reviews, 7 departments), three findings, one limit |
| Significance | 100 | Plain language, ≤120 words (PNAS rule) |
| Introduction | 400 | UPF and health; NOVA; marketing language; why a shopper network; RQs; hypotheses pre-declared before computing |
| Results 1: sell | 550 | Fig 2. A1 valence +0.0135, arousal +0.0099 within category (p≤.0005); dominance −0.018 (descriptive); log-odds words: pleasure (delicious, snack, flavor) vs purity (organic, certified, non-GMO); H1 joy +8% but not robust; H2 null; H8 null (other products' copy not warmer) |
| Results 2: shop | 750 | Fig 3 + Fig 4. H4 NOVA assortativity +0.279 vs nulls .091 (category) / .200 (brand); cross-brand .208 vs .073. H5: Games +4.3, Toys +4.7, Sports −4.5, Health & Household −4.2 points; Baby null. Mixed network 16,729 products, 104 communities (modularity .46); H6 weak. Hubs are household staples, not food. H10 rich-get-richer α .93 (one paragraph or SI) |
| Results 3: feel | 450 | H9 warmer reviews elsewhere +0.011 (6/7 departments); A1-H3 promise gap +0.0087; H3 (EmoLex) null. Measurement: Table 1 (instrument validation) |
| Discussion | 450 | What it means; limits (below); what a stronger design needs |
| Methods | 600 | Data linking, NOVA, within-category permutation + Holm, disparity backbone, assortativity nulls, Louvain + c-TF-IDF, PageRank, preferential attachment, lexicons, classifiers, hand labels |
| References | ~15 | PNAS style |

## Figures (redraw at PNAS column width, ≥8 pt fonts, colour-blind-safe)
1. Data pipeline: Open Food Facts + Amazon barcode match → NOVA groups (10/2/20/69%) → three analyses. New, simple.
2. Sell: upf/figures/marketing_wordplot.png (log-odds) + a small panel of within-category VAD differences with CIs (from listing_vad.png).
3. Shop network: shopper backbone coloured by NOVA + assortativity observed vs the two nulls (from the story page; needs a static version).
4. Beyond groceries: H5 dot chart (percentage-point differences by department) + optional mixed-network community panel.
Table 1: instrument validation: VAD, EmoLex, Yelp, Cardiff, GoEmotions vs stars (AUC) and vs hand labels (macro-F1). Final rows depend on the TA reply.
Supplement/slide only: rich_get_richer.png, listing_vad.png, ingredient network, hubs list.

## What to cut or reframe
- Ingredient network (Open Food Facts): exploratory; supplement or one sentence.
- Complete Journey (H7), FAO guidelines, London/Tesco: dropped; at most one Methods sentence ("tried, dropped because…") or none.
- Emotion classifiers: a validation story (Table 1 + one paragraph), not a headline result, unless the TA advises otherwise.
- NDC / ParlaMint work: not in this paper.

## Honest limits that must appear (Discussion), one line each
- NOVA is assigned by rules from volunteer-scanned ingredient lists; 17 of 20 sampled matches were the same product; H1 vanishes on high-confidence matches.
- Reviews are not purchases; reviewers are a self-selected minority; pseudonymous IDs; no demographics (and none inferred).
- Effects in wording are small (about 5% of the mean); overlap is near-total.
- Lexicons ignore negation and context ('treat'); classifiers trained on tweets/Reddit; both failed the pre-declared hand-label bar; one labeller, 2 × 100 reviews; labels shift with the label list offered.
- US Amazon only; categories from Open Food Facts; association, not cause.

## Open decisions (need both of you)
1. Partner's agri-environmental policy / trade work: one paper with two strands, or this UPF story alone? Must be settled first.
2. Classifier: waits for the TA reply (Table 1 and Results 3 wording depend on it).
3. Network figure: shopper backbone (H4) or mixed network (H5/H6) as the main network picture?
4. Who owns what; every person must answer on any part (swap-explain rule by 22 Nov).

## Timeline (today is Mon 16 Nov)
- 16–17 Nov: freeze results; numbers sheet (every number → script → output file); regenerate figures at paper size; LaTeX skeleton from the PNAS template.
- 18 Nov (in-room): story + figures feedback; classifier question; partner decision.
- 19–21 Nov: full draft. 22 Nov: swap-explain. 23–24 Nov: revise, trim to 6 pages, check every claim against the numbers sheet.
- 25 Nov (in-room): final checks. 26 Nov: 3 slides + half-page reflection. 27 Nov: submit before 23:59.
- 28 Nov–1 Dec: rehearse; prepare the hard questions below.

## Questions we must be able to answer cold
- How is NOVA assigned, and how good is the barcode match? Why does H1 fail on the high-confidence subset?
- Why compare within category, and what does the permutation null keep fixed?
- What is assortativity, why two nulls (category, brand), and why does the brand null stay at .200?
- What does the disparity filter keep, and why a backbone at all?
- Why are reviews a fair proxy for shopping, and where does that break?
- How were emotions validated? Why did both classifiers fail the hand-label bar, and why report it?

## Reflection (half page, ungraded)
What the AI got wrong and we caught: the H4 null bug (full shuffle instead of within-category), the 'treat' artefact, the word-list approach the course does not teach,
a wrong count in a figure title (75,933 vs 61,341), the 13 vs 19 checkable pledges (NDC phase). What we checked by hand: 20 barcode matches, 200 emotion labels.
