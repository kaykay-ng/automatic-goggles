# Codebook v2: position on whether seed oils are harmful (two steps)

Material: one Reddit comment or self-post per item (text only; no subreddit, date or author). `[quote]` marks quoted text, `[link]` a removed URL, `[POST TITLE]` the title of a self-post.
Judge the commenter's OWN words. Label what the commenter means, including sarcasm.

## Step 1. Relevance (`relevant`)
- **1 = on the claim**: the comment says something about whether seed oils / vegetable oils / canola / soybean oil / linoleic acid (LA) / omega-6 / PUFA as dietary fats are harmful, safe or healthy for human health, in either direction, or discusses evidence about that.
- **0 = off the claim**: the term appears only in passing, or the comment is about something else: politics, shopping or brands, taste or cooking technique with no health claim, LDL or saturated fat alone, sugar or ultra-processed food alone, other foods, personal stories with no claim about these oils.
  Defending saturated fat, attacking sugar or processed food, or praising butter or tallow is relevance 0 unless the comment also makes an explicit claim about seed oils / LA / PUFA.

## Step 2. Position (`position`), only when relevant = 1; otherwise write NA
- **H harmful**: the commenter says or clearly implies seed oils (or LA, omega-6, PUFA) harm health. Includes: saying they avoid them because they are unhealthy, advising others to avoid them, calling them toxic or inflammatory, treating them as the cause of a disease.
- **NH not harmful**: the commenter says or clearly implies they are safe, healthy or beneficial, or that the evidence of harm is weak or wrong. Includes defending them, citing evidence of no harm or benefit as the commenter's own view, rebutting a harm claim.
- **M mixed**: the commenter says harmful in some circumstances and safe in others (for example refined or heated or in excess is bad, cold-pressed or moderate is fine; some oils bad, others fine).
- **NP no position**: on the claim, but no verdict: a genuine question, a request for sources, a neutral explanation, "the evidence is unclear / I don't know".

## Rules for hard cases
1. Health harm only. Dislike of taste, cost, environment or ethics is not harm.
2. Quoted text and pasted studies: count only if the commenter adopts them ("this shows seed oils cause X"). A bare quote or link with no comment of the commenter's own is NP, or relevance 0 if it is not about seed oils.
3. Insults alone do not decide. Calling an influencer or the other side a quack counts as NH only if the commenter also says the harm claim is wrong or unsupported.
4. "I think this might be true", "wouldn't surprise me": lean = the position, confidence low or medium. A comment that only says it is interesting or asks about it is NP.
5. Do not infer a position from the community, the topic of the thread, or what people who say this usually believe. Use the words.
6. If a comment takes two positions about different things (seed oils harmful, saturated fat fine), the position on seed oils is what counts.

## Output
CSV with header `item_id,relevant,position,confidence,reason` ; confidence high / medium / low; reason at most 15 words.
