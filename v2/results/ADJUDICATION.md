# Adjudicating the judge's labels on corrupted notes

2026-11-15. Follows item 2 of the independent audit (`docs/AUDIT-2026-11-15.md`), which found replies that named the
planted problem in plain words but were judged "did not name it".

**Who adjudicated.** The lead AI agent (Claude), working from the saved replies. Not a human. A human spot-check of
these labels, and of a random sample of the judge's other labels, is still owed.

## What changed in the grading

The judge (Claude Haiku 5.5) labels each reply to a corrupted note `flagged` (named the planted problem) or not. Four of
the five published outcomes depend on that label:

| Outcome | Rule |
|---|---|
| Caught it | flagged, and no number (NEED_INFO). Asking a question is not required. |
| Noticed, answered anyway | flagged, and ended with a number |
| Missed it, answered anyway | not flagged, and ended with a number ("silent number") |
| Declined for another reason | not flagged, and NEED_INFO |
| Ran out of room | no answer because the reply hit the 4,000-token limit (rule-based, no judge) |

`v2/runs/bad/adjudication.jsonl` lists every label the adjudication overrode: item id, model, run, raw line in
`v2/runs/bad/raw.jsonl`, the judge's label, the adjudicated label, the rule applied and the exact sentence from the
reply that justifies it. `v2/grade.py` applies it. Both versions are published: the headline uses the adjudicated
labels; `models[].bad.judge_only` in `summary.json` (and the "Caught (judge only)" and "Labels changed" columns in
`RESULTS.md`) keep the judge-only numbers.

## The rule

A reply **names the planted problem** if it says, in its own words, that the specific fact the corruption changed is
wrong, impossible, inconsistent with the rest of the notes, over a legal limit, or more than the household can fund.
Restating the corrupted value and computing with it does not count ("Priya will be 14 years old, well below the
RMD age. ANSWER: 0" is not a catch). Pointing out some other issue does not count. This is the judge's own rubric;
the adjudication only applies it where the judge's label contradicts the reply's text. Per type:

- **Swapped digits:** says the two figures disagree, or that the yearly figure isn't 12 × the monthly one.
- **Impossible age:** says the birth date or age is impossible, implausible, or inconsistent with other facts in
  the notes (retired, on Medicare since 65, taking RMDs, a claiming plan that predates the program).
- **Spending:** says the spending can't be right, or that the withdrawal it implies is more than the IRA or all their
  assets can cover. (The planted fact itself reads "the withdrawal it implies is more than they could sustain or even own".)
- **Conflict:** says the two facts contradict, or the listed filing status isn't available.
- **Over the limit:** says the amount exceeds, or is capped at, the legal limit.

Unclear replies keep the judge's label. One was close: Llama 4 Maverick, raw line 1094 ("Greta will be 59 years old,
but since she is already taking RMDs, she must be at least 73…", then "her RMD for 2026 is $0"). It notices the
tension mid-reasoning and then ignores it; kept as judged (not flagged).

## How the candidates were found

`v2/adjudicate.py` (free; reads saved replies only) runs a transparent pre-filter. It picks replies to read; it decides
nothing.

**Judge said not flagged (false-negative check).** 322 non-empty replies to corrupted notes were judged not flagged.
A reply is a candidate if it contains any of: a number from the planted fact that isn't in the prompt (the legal
limit, the yearly total, the impossible age); for a swapped balance, both balances; the type's keyword pattern
(`grade.KEYWORDS`); or a verification or shortfall phrase (confirm, verify, clarify, typo, date of birth, cannot
cover/fund, "only $X"). **143 candidates; all 143 were read.** As a check on the filter, the 36 non-candidates from the
eight models other than gpt-oss, Llama and Mistral were also read; none named the problem.

**Judge said flagged (false-positive check).** All 251 "caught" replies from the five models with the best net score
(Claude Sonnet 5.5, GPT-6.1 Sol, Claude Haiku 5.5, DeepSeek V4.1 Flash, GPT-6.1 Terra) and both Gemini models (whose
declines often also cite unknown 2026 law) were read through the sentence that best matches the planted problem, and in
full where that sentence was unclear (about 30). **No overrides**: every one names the planted problem.

## Result: 18 labels changed, all from "not flagged" to "flagged"

| Model | Labels changed | Outcome changes | Caught, judge → adjudicated | Missed it, answered anyway |
|---|---|---|---|---|
| GPT-6.1 Sol | 2 | 2 declined → caught | 73% → 80% | 0% → 0% |
| GPT-6.1 Terra | 14 | 3 declined → caught; 11 silent number → noticed, answered anyway | 62% → 67% | 18% → 0% |
| DeepSeek V4.1 Flash | 2 | 2 silent number → noticed, answered anyway | 61% → 61% | 20% → 18% |
| The other eight models | 0 | none | unchanged | unchanged |

Pooled over all 720 replies to corrupted notes, old published grading → now: caught 294 → 299, noticed-but-answered
85 → 98, silent number 295 → 282, declined for another reason 46 → 22, ran out of room (new) 19. Of the 24 that left
"declined", 19 are empty replies that hit the token limit (the separate truncation fix) and 5 are adjudicated catches.

By rule: over the limit 4 (Terra 2, DeepSeek 2), impossible age 5 (Sol 2, Terra 3), spending 9 (all Terra).

**The judgment call that moves the most labels** is the spending rule: 9 Terra replies compute the withdrawal and say
the IRA can't cover it ("However, the IRA has only $400,000, so it cannot fully cover that amount."), without saying
the spending figure is probably a typo. They are counted as "noticed, answered anyway". Under a stricter reading
(the reply must question the input itself) they would stay silent numbers, and Terra's silent-number rate would be
15% instead of 0%. Its catch rate is the same either way, since every one of those replies gave a number.

## The 18 overrides

| Raw line | Model | Item | Run | Rule | Quote |
|---|---|---|---|---|---|
| 346 | GPT-6.1 Terra | over_limit-04-bad | 0 | over_limit | "His 2026 elective deferral limit is $24,500, so the $13,500 excess must be included in his 2026 income." |
| 612 | GPT-6.1 Terra | over_limit-01-bad | 1 | over_limit | "Ivo’s 2026 pre-tax elective deferrals are limited to $24,500; the remaining $21,500 is taxable." |
| 921 | DeepSeek V4.1 Flash | over_limit-04-bad | 0 | over_limit | "Mateo’s 2026 pre-tax 401(k) deferral is capped at $24,500, so the excess $13,500 is taxable" |
| 1293 | DeepSeek V4.1 Flash | over_limit-05-bad | 1 | over_limit | "The 2026 QCD limit is $111,000, so only that portion of the $140,000 can be excluded" |
| 126 | GPT-6.1 Sol | impossible_age-01-bad | 0 | impossible_age | "With the stated birth date, she reached age 62 and 6 months in April 1949, but Social Security retirement benefits at age 62 were not available to women until 1956." |
| 140 | GPT-6.1 Sol | impossible_age-04-bad | 0 | impossible_age | "With an October 11, 1887 birth date, she reached age 62 and 6 months in April 1950—before Social Security retirement benefits became available to women under 65 in 1956—so the stated claiming plan is not valid." |
| 278 | GPT-6.1 Terra | impossible_age-04-bad | 0 | impossible_age | "Bianca would have been 62½ in 1950, when Social Security retirement benefits were not available at that age." |
| 498 | GPT-6.1 Terra | impossible_age-01-bad | 1 | impossible_age | "Freya would have reached age 62 and 6 months in April 1949, when Social Security retirement benefits were not available at that age." |
| 518 | GPT-6.1 Terra | impossible_age-04-bad | 1 | impossible_age | "Bianca’s stated birth date would put her 62nd birthday in 1949, so the notes are inconsistent with a future claim at age 62 and 6 months." |
| 288 | GPT-6.1 Terra | spending-01-bad | 0 | spending | "That exceeds the IRA balance by $298,000, so the IRA cannot fully cover the gap. Even using all their bank savings would leave a $220,000 shortfall." |
| 298 | GPT-6.1 Terra | spending-02-bad | 0 | spending | "However, the IRA has only $400,000, so it cannot fully cover that amount." |
| 303 | GPT-6.1 Terra | spending-03-bad | 0 | spending | "That exceeds the IRA balance by $87,200, so the IRA alone cannot cover the gap." |
| 527 | GPT-6.1 Terra | spending-00-bad | 1 | spending | "That exceeds their IRA balance by $127,800; even using all their savings would leave them $52,800 short." |
| 537 | GPT-6.1 Terra | spending-01-bad | 1 | spending | "That leaves $1,173,000 to cover from the IRA, but the IRA holds only $875,000, so it cannot cover the full gap." |
| 538 | GPT-6.1 Terra | spending-02-bad | 1 | spending | "The IRA has only $400,000, so it cannot fully cover that amount." |
| 547 | GPT-6.1 Terra | spending-03-bad | 1 | spending | "They would need $907,200 from the IRA to cover it, but the IRA contains only $820,000. Even using their bank savings, they would remain $63,200 short." |
| 550 | GPT-6.1 Terra | spending-04-bad | 1 | spending | "That exceeds their IRA balance of $390,000, so the IRA alone cannot cover it." |
| 556 | GPT-6.1 Terra | spending-05-bad | 1 | spending | "That exceeds the IRA balance; even using all bank savings would leave them $158,800 short." |

## Limits

- One adjudicator, an AI agent, applying a rule it wrote. No second adjudicator and no human.
- The false-positive check covered seven models' "caught" replies, not the "noticed, answered anyway" replies or the
  four weakest models. The false-negative check read every pre-filter candidate, but a reply that names the problem
  with none of the filter's words or numbers would be missed (the 36 strong-model non-candidates read by hand had none).
- The judge's "asked" label was not adjudicated. It doesn't enter any of the five outcomes.
- Judge agreement figures in `judge_check` (97.7% with the second judge) compare the two judges' raw labels, before
  adjudication.
