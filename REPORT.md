# Can you trust AI with retirement math?

Peyton Thalman · updated 2026-11-15 · two rounds of tests (October and November 2026), then an independent audit

## Summary

I'm a financial advisor. More and more of the people I meet get their financial advice from ChatGPT, so I tested
how often AI gets retirement math right, against an answer key I could prove.

1. **Simple questions: almost always right.** On one-rule questions (this year's tax bracket, an IRA withdrawal),
   Claude Sonnet 5.5 and Claude Haiku 5.5 both scored 97% in the first test.
2. **Real-life questions: it depends which AI.** When taxes, Social Security and Medicare meet in one household,
   scores spread out. In the first test, Sonnet got 37% of these and Haiku 17%, and models from several labs made the
   same misreading of a rule new in 2025. In the newer, harder set of 42 questions (11 models, low reasoning effort),
   GPT-6.1 Sol got 98%, Claude Sonnet 5.5 62%, and all five cheap models under 30%.
3. **A calculator helps, if it shows its work, and only for some models.** Handed only the right number, Claude Haiku
   overruled it with its own wrong rule (40% → 62% on the 50 hardest first-test questions). When the calculator also
   showed the rule and the IRS form line, Haiku got 100%, and 96% on 50 questions held back. In the newer set,
   DeepSeek V4.1 Flash went from 29% to 79% with the calculator; three other cheap models called it and scored
   10% or less, and the best model gained nothing.
4. **Tell it something wrong: the best models catch most of it, three cheap models almost none. This is the biggest
   open gap.** In 30 client files with one
   planted mistake each, GPT-6.1 Sol caught 80% and Claude Sonnet 5.5 73%, with almost no false alarms. Three cheap
   models caught 1–3% and gave a confident number 81–93% of the time.

**And ChatGPT?** GPT-6 Luna on a ChatGPT subscription got 71% of one-rule questions but 17% of the hardest ones, and
caught half the planted mistakes. It was a different setup, so it is reported in its own section below.

**The plain answer.** For one well-known rule, the best AIs are reliable. For a whole household, it depends heavily on
which AI you ask: the cheap and free models I tested, at quick-answer settings, got most of the hard questions wrong. And the answer is only as good as what you type in:
in my tests, three cheap models almost never questioned an impossible fact, and even the best missed about one in
four. Check your inputs, and take big decisions to a professional.

**How this was built.** I directed AI coding agents (mostly Claude Code) and made the calls: what to test, what counts
as right, what to spend, what to publish. Because AI did most of the work, the checks are set up so no agent is the only grader of its
own work (the lead agent did re-check 18 judge labels; that is disclosed below, and a human spot-check is owed), and a model from another lab audited every published claim on 2026-11-15. It found 12 errors. They are fixed
in this version and listed under [Corrections](#corrections).

![Catch rate against false-alarm rate](v2/results/charts/catch_vs_false_alarm.svg)

## Why I made this

I meet most people by knocking on their door. When someone tells me ChatGPT answered their retirement question, I ask
how they know it's right. Usually they Googled it, and the top result was another AI's answer. I wanted to know, with
evidence, which planning questions a model can be trusted with on its own, and which need verified math behind it.

## What I built

- **An answer key I could prove.** The 2026 federal tax, Social Security, required-withdrawal and Medicare rules
  written as a program: the planning engine. A second engine, written by an agent that never saw the first, from the
  published rules alone, agrees with it on 4,000 of 4,000 random households within $1. PolicyEngine-US, an
  open-source tax model nobody on this project wrote, agrees on 1,600 of 1,600 first-test tax answers within $2.
- **The first test (October 2026).** 2,800 public questions with one exact answer each (plus 700 held back), from
  one-rule questions to ones where several rules meet. Seven model setups from five labs, reasoning effort high,
  16,000–32,000-token replies.
- **The calculator.** The engine as tools a model can call while it answers (an MCP server), and as a connector in
  Claude and ChatGPT.
- **The newer, harder set (November 2026).** My own audit of the first test ([AUDIT.md](AUDIT.md)) found two
  problems: the best models had nearly maxed out the simple questions, and every fact I gave them was true. So I added
  42 harder questions and 30 client files with a planted mistake, and ran 11 models at low reasoning effort with
  4,000-token replies, for $4.51 against a $5 cap.

The two rounds used different settings, so their scores are reported separately and never compared directly.

## Findings 1 and 2: AI on its own

### The first test (October)

| Model | One rule | Several rules at once | Overall |
|---|---|---|---|
| Claude Sonnet 5.5 | 97% | 37% | 84% |
| Claude Haiku 5.5 | 97% | 17% | 77% |

Five more setups (DeepSeek V4.1 Flash, GLM 5.3 Flash, gpt-oss-120b, Qwen3.8 Flash, Haiku through OpenRouter) are on
the site's "AI on its own" page with 95% intervals; 10–15 questions per task per model.

**One rule explains a large share of the misses.** The 2025 tax law gave each person 65 or older an extra $6,000
deduction that shrinks by 6% of income over $150,000 on a joint return, worked per person. Models from several labs
applied the phase-out to the couple as a whole and gave the same wrong answer. Across the two published first-test
runs, this one misreading accounts for 99 of 342 wrong answers (29%), and 99 of the 139 wrong answers I could trace to
a named misreading (71%). Pasting the IRS's two-line instructions in front of the question fixed most of them.

### The newer, harder set (November)

Each of the 42 questions makes two or more rules meet: the largest Roth conversion that leaves Medicare premiums alone
two years later; a conversion's cost in federal plus Arizona tax; taxable Social Security with muni interest and a
charitable gift from an IRA (a QCD); an inherited IRA's 2026 required withdrawal under the 10-year rule; tax when part
of a required withdrawal goes to charity; a widow's first year; Arizona tax for retirees. Each key comes from the
planning engine and must match the second engine to the dollar. Sources and examples: [v2/data/HARD.md](v2/data/HARD.md).

| Model | Maker | Alone | Ran out of room | $ per right answer |
|---|---|---|---|---|
| GPT-6.1 Sol | OpenAI | 98% [88–100] | 0% | $0.0032 |
| GPT-6.1 Terra | OpenAI | 80% [65–89] | 0% | $0.0019 |
| Claude Sonnet 5.5 | Anthropic | 62% [47–75] | 0% | $0.0173 |
| Claude Haiku 5.5 | Anthropic | 52% [38–67] | 2% | $0.0022 |
| Gemini 3.1 Pro | Google | 29% [17–44] | 0% | $0.0513 |
| Gemini 3.8 Flash | Google | 29% [17–44] | 36% | $0.0195 |
| DeepSeek V4.1 Flash | DeepSeek (open) | 29% [17–44] | 71% | $0.0036 |
| GLM 5.3 Flash | Z.ai (open) | 15% [8–29] | 20% | $0.0063 |
| gpt-oss-120b | OpenAI (open) | 7% [2–19] | 0% | $0.0016 |
| Mistral Small | Mistral (open) | 7% [2–19] | 0% | $0.0087 |
| Llama 4 Maverick | Meta (open) | 6% [2–17] | 0% | $0.0185 |

- **Only one model is near the ceiling.** GPT-6.1 Sol missed one of 42 at low effort. Everything else is between 6%
  and 80%. The Arizona family is the hardest: only Sol got any of it right alone.
- **Running out of room is a big part of the cheap models' scores.** DeepSeek hit the 4,000-token limit on 71% of
  questions and Gemini 3.8 Flash on 36%. Scores at a higher setting may be higher; I didn't run that comparison.
- Haiku's 52% averages its two runs; its first run alone was 20 of 42 (48%), the baseline used in the paired tool
  comparison below.

## Finding 3: with a calculator

### Hand it the number and it argues; show it the rule and it listens (October)

Claude Haiku 5.5, effort high, on the 50 hardest first-test questions:

| | Alone | Calculator 1.0 (number only) | Calculator 1.1 (number, rule, form line) |
|---|---|---|---|
| Public questions | 40% (20/50) | 62% (31/50) | 100% (50/50) |
| Held-back questions | 44% | | 96% (48/50) |

With calculator 1.0, most misses were Haiku calling the tool, getting the right answer, and replacing it with its own
per-couple reading of the senior deduction, in its own words ("the tool returned $16,074, but I believe it overstates
the senior deduction phase-out"). The engine's answers didn't change between 1.0 and 1.1; only the reply did. Both
held-back misses were Haiku overruling the tool again. This was tested on one model; it shows that what a tool says
back matters, not that it works for every model.

**Whole-household decisions.** Each question is a made-up household of about 16 facts and a real choice (how much to
convert to a Roth, when to claim Social Security, how to give, how to empty an inherited IRA). One question from each
of 10 families plus a trap, one try each:

| Model | Right decision and every number within 2%, alone | With the calculator |
|---|---|---|
| Claude Haiku 5.5 | 4/11 | 11/11 |
| Claude Sonnet 5.5 | 7/10 (3 ran out of room) | 11/11 |
| DeepSeek V4.1 Flash | 2/11 | 11/11 |

Every key agrees with the second engine on every field of every year, and every 2026 return agrees with PolicyEngine-US
(203/203). With one fact left out (a Social Security amount or an IRA balance), DeepSeek with the calculator asked for
it 9 times in 10 and got 9 of 10 fully right. Small samples: this shows the gap, not a ranking.

### The newer set: a cheap model catches up, others don't (November)

Paired: each model's first run alone against its one run with the calculator, on the same 42 questions.

| Model | Alone (first run) | With the calculator | Fixed / broken | Called a tool |
|---|---|---|---|---|
| GPT-6.1 Sol | 41/42 | 40/42 | 0 / 1 | 79% |
| GPT-6.1 Terra | 34/42 | 36/42 | 3 / 1 | 81% |
| DeepSeek V4.1 Flash | 12/42 | 33/42 | 21 / 0 | 90% |
| Claude Haiku 5.5 | 20/42 | 26/42 | 8 / 2 | 50% |
| GLM 5.3 Flash | 7/42 | 18/42 | 11 / 0 | 86% |
| gpt-oss-120b | 3/42 | 4/42 | 2 / 1 | 79% |
| Mistral Small | 3/42 | 3/42 | 3 / 3 | 79% |
| Llama 4 Maverick | 3/42 | 2/42 | 0 / 1 | 79% |

Sonnet and the Gemini models were not run with the calculator (cost). The "Alone" column in the earlier table averages
two runs for some models; this one uses the first run, the one the calculator run is paired with.

- **DeepSeek scored higher than Sonnet alone, at about a fifteenth of the cost per right answer.** DeepSeek with the
  engine got 33 of 42 right; Sonnet alone got 26. Both were right on 23, only DeepSeek on 10, only Sonnet on 3,
  neither on 6 (exact McNemar p = 0.09). The difference isn't statistically significant.
- **The calculator helped the models that were running out of room.** DeepSeek fixed 21 questions and broke none
  (paired, p < 0.001); GLM fixed 11 and broke none (p = 0.001). The 4,000-token limit applies to each turn of the tool
  loop, up to 8 turns: 10 of 336 tool-track replies used more than 4,000 output tokens in total (DeepSeek 9, GLM 1;
  the most was 7,135). Counting only DeepSeek's replies within 4,000 tokens in total, it still got 27 of 42 (64%).
- **Three cheap models called the tools and it didn't matter.** gpt-oss, Llama and Mistral Small called a tool on 79%
  of questions and scored 10% or less: wrong inputs, or one call where the question needed three.
- **Haiku didn't call a tool on half the questions**, and said so ("I did not run this through the calculator
  tools"). Its gain, 20 to 26 of 42, isn't significant (p = 0.11).
- **The best model gained nothing.** Sol went from 41 to 40 of 42. Both misses with tools were Arizona questions where
  it took the federal numbers from the tool and left out Arizona's $2,100 age-65 exemption.

## Finding 4: wrong facts

**Setup.** Each note is a short planner's intake file and one question. 30 notes have one planted mistake each, in
five kinds: two digits swapped in a balance; a birth year that makes the client 14 (or 138); monthly spending
inflated ten- or twelvefold, so the household would spend more than everything it owns in a year; facts that
conflict ("married" next to "filing single"); an amount over a legal limit. Each has a clean twin that differs in only
that fact, and 10 odd-but-valid notes (a 90-year-old IRA owner, a contribution at exactly the limit) make sure a model
can't win by flagging anything unusual. Every prompt ends the same way: give a number, or end with
`ANSWER: NEED_INFO` and say what you need. Examples: [v2/data/BAD_INPUTS.md](v2/data/BAD_INPUTS.md).

A reply to a corrupted note lands in one of five places:

- **Caught it**: named the planted problem and gave no number.
- **Noticed, answered anyway**: named the problem and still ended with a number.
- **Missed it, answered anyway**: a confident number with no mention of the problem.
- **Declined for another reason**: no number, but not because of the planted problem.
- **Ran out of room**: no answer because the reply hit the token limit. Counted as not caught.

Whether a reply ended in a number or NEED_INFO is read by a rule. Whether it named the planted problem was judged by
Claude Haiku 5.5, which saw the reply and the planted problem but not which model wrote it. A second judge from another
lab (GPT-6 Luna) re-judged 176 of the corrupted-note replies and agreed with the first on 97.7% of "named the problem"
labels (kappa 0.95). Then the lead AI agent (Claude), not a person, adjudicated every reply the judge marked as not naming the problem (details below).

| Model | Caught it | Noticed, answered anyway | Missed it, answered anyway | Declined, other reason | Ran out of room | False alarms (40 valid notes) | Clean twins right (30) |
|---|---|---|---|---|---|---|---|
| GPT-6.1 Sol | 80% [63–90] | 20% | 0% | 0% | 0% | 2% | 100% |
| Claude Sonnet 5.5 | 73% [56–86] | 20% | 7% | 0% | 0% | 0% | 93% |
| GPT-6.1 Terra | 67% [49–81] | 33% | 0% | 0% | 0% | 2% | 97% |
| Claude Haiku 5.5 | 65% [47–79] | 17% | 18% | 0% | 0% | 0% | 85% |
| DeepSeek V4.1 Flash | 61% [43–76] | 14% | 18% | 0% | 7% | 0% | 93% |
| Gemini 3.8 Flash | 92% [76–97] | 0% | 0% | 8% | 0% | 50% | 47% |
| Gemini 3.1 Pro | 70% [52–83] | 0% | 3% | 27% | 0% | 68% | 30% |
| GLM 5.3 Flash | 40% [25–58] | 31% | 14% | 0% | 14% | 0% | 33% |
| Llama 4 Maverick | 3% [1–17] | 16% | 81% | 0% | 0% | 2% | 30% |
| gpt-oss-120b | 3% [1–17] | 0% | 93% | 3% | 0% | 5% | 20% |
| Mistral Small | 1% [0–13] | 1% | 91% | 7% | 0% | 1% | 22% |

![What each model did with a corrupted note](v2/results/charts/outcomes.svg)

- **The gap is behavior, not arithmetic.** Three cheap models almost never stop. Across all 720 replies to corrupted
  notes: 42% caught it, 14% noticed and answered anyway, 39% missed it and answered anyway, 3% declined for another
  reason, 3% ran out of room.
- **"Best" means catching without crying wolf.** Gemini 3.8 Flash caught the most (92%) but also declined half of the
  valid notes. Read its false alarms by reason, though: 54 of the two Geminis' 67 declines on valid notes say they
  can't verify the 2026 tax law, not that the client's data is wrong. On notes that need no 2026 tax law, Gemini 3.8
  Flash caught 100% with no false alarms; Gemini 3.1 Pro caught 93% with 35% false alarms.
- **DeepSeek V4.1 Flash is the exception among cheap models.** It caught 61%, level with the mid-priced models, with
  no false alarms.
- **Naming the problem and stopping are different skills.** Sonnet named the problem in 93% of corrupted notes and
  Sol in 100%; they stopped in 73% and 80%. One reply in five saw the problem and gave a number anyway.
- **Amounts over a legal limit had the lowest pooled catch rate:** conflicting facts 60%, impossible age 47%, swapped
  digits 43%, spending that can't fit 41%, amount over a legal limit 17%. Not every model followed the pattern: Sol
  and Terra caught over-limit amounts more often than spending errors (Sol 67% vs 33%; Terra 33% vs 0%). Haiku and
  Gemini 3.1 Pro caught none of the over-limit notes. Many over-limit replies saw the problem and computed with the
  legal maximum instead (22% of all over-limit replies).
- **Catching isn't stable for the cheap models that do it.** On notes asked more than once, DeepSeek gave the same
  one of the five outcomes on every run for 60% of notes and GLM for 27%; Haiku 77% and Terra 93% over two runs.
  (Caught versus not caught alone: DeepSeek 67%, GLM 57%, Haiku 83%, Terra 93%.)

**Adjudication.** The audit found replies that plainly named the planted problem but were judged as not naming it. So
the lead AI agent checked every one of the 322 corrupted-note replies the judge marked "not named": a transparent pre-filter (the
planted numbers and terms appearing in the reply) picked 143 candidates, and each was read against the rule "the reply
says, in its own words, that the corrupted fact is wrong, impossible, inconsistent, over a limit, or more than the
household can fund". 18 labels changed, all from "missed" to "named": GPT-6.1 Terra 14, Sol 2, DeepSeek 2. A reverse
check of 251 "caught" replies found none to change. Every override is in `v2/runs/bad/adjudication.jsonl` with the
exact quote, and [v2/results/ADJUDICATION.md](v2/results/ADJUDICATION.md) has the method. The judgment call that
matters most: 9 Terra spending replies say the IRA can't cover the withdrawal without questioning the spending figure.
I counted them as "noticed". On a stricter reading, Terra's "missed it" rate would be 15% instead of 0%; its catch rate
is the same either way. The adjudicator was the lead AI agent, not a person; a human spot-check is still owed. The
judge-only numbers are kept in `v2/results/summary.json` (`judge_only`).

## How it fails: real replies

Excerpts from saved replies (`v2/runs/*/raw.jsonl`). Personas are made up.

### 1. Missed it, answered anyway: computing on a fact that can't be true

The note gives a date of birth in 2012 for a retired school administrator with a $785,000 IRA and asks for her
required withdrawal.

> **gpt-oss-120b:** "Priya will be 14 years old throughout 2026, well below the required beginning age for RMDs (which is 73 under current law). Therefore, no required minimum distribution is required for 2026. ANSWER: 0"

It saw the age and reasoned from it. The real answer, with the real birth year, is $34,279.

The note gives spending of $66,500 a month for a couple with $70,200 of income and $675,000 in total.

> **Mistral Small:** "Their annual spending is $66,500 * 12 = $798,000. Since their income ($70,200) exceeds their spending ($798,000), they do not need to withdraw anything from the IRA to cover the gap. ANSWER: 0"

The note lists an IRA balance of $624,900 and a custodian statement showing $642,900.

> **Llama 4 Maverick:** "...the distribution period for an 82-year-old is 17.1. Thus, the RMD for 2026 is $624,900 / 17.1 = $36,543.86. ANSWER: 36544"

It picked one balance without a word, and used the life-expectancy table that was replaced in 2022.

### 2. Noticed, answered anyway

> **GPT-6.1 Sol:** "They would need $620,400 from the IRA to cover the gap, but its $400,000 balance cannot fund that withdrawal. Confirm that the spending figure is monthly, not annual. ANSWER: 620400"

The reply is right about the problem and still hands back a number that a downstream system would store.

> **Claude Sonnet 5.5** (a $46,000 401(k) deferral at age 43): "the $46,000 deferral exceeds the 2026 limit of $24,500 for someone under 50, so only $24,500 can be pre-tax; the excess $21,500 is taxable... ANSWER: 20774"

This one is defensible: it corrected the input to the legal limit and said so. A planner would still want to be asked.

> **GLM 5.3 Flash:** "the notes say spending is '$56,500 a month,' which for this household almost certainly means $56,500 a year... On the annual reading... ANSWER: 0"

It guessed which fact the client meant, which is the behavior this test exists to catch.

### 3. Missing a wrong amount because the rule is half-remembered

A $140,000 qualified charitable distribution, over the 2026 limit of $111,000:

> **Claude Sonnet 5.5:** "This assumes the QCD is fully eligible, since it is under the $111,000 2026 limit..."

It knew the limit and didn't compare the number to it.

### 4. False alarm: declining a valid note

> **Gemini 3.8 Flash** (a clean note): "The cited 'One Big Beautiful Bill Act' and 'IRS Rev. Proc. 2025-32' are not actual federal tax authorities... ANSWER: NEED_INFO"

The law is real and was passed after the model's training data ends. For a firm this is still a failure: an
answerable question got no answer.

### 5. Calculator offered, not used

> **Claude Haiku 5.5** (inherited IRA, key $9,960): "$248,000 ÷ 23.0 = $10,782.61... I did not run this through the calculator tools. The 27.0 factor for age 58 is from my memory of the Pub 590-B table. ANSWER: 10783"

### 6. Calculator called, then wrong

The question: tax for a single retiree whose required withdrawal partly goes to charity, with a pension and Social
Security. gpt-oss made one call to the tax tool with the pension alone, left out the withdrawal entirely, and replied
with a single line:

> **gpt-oss-120b:** "ANSWER: 1115" (key: $9,614)

> **GPT-6.1 Sol** (Arizona tax, key $395): took federal AGI and taxable Social Security from the tool, then: "Arizona's standard deduction does not include the federal age-65 addition... $17,900 × 2.5% = $447.50. ANSWER: 448"

Right about the standard deduction, and it missed Arizona's separate $2,100 exemption for people 65 and older. The
tool gave it correct parts; the assembly was its own.

## ChatGPT’s model on a subscription (GPT-6 Luna, through Codex)

Most people ask ChatGPT. So on 2026-11-15 the same questions went to GPT-6 Luna, the model on my ChatGPT subscription,
run through OpenAI’s Codex app (not the ChatGPT chat window), graded with the same answer keys and graders. Luna answered each prompt as its own chat with no code,
calculator or web, at medium effort with no token limit, in batches of 5–11 prompts per session. That is a different
setup from the API runs (one message per question, fixed token limits), so these numbers sit beside the tables above,
not inside them. In real ChatGPT the model may choose to run code; here it didn't, the same as the other models.

| Test | GPT-6 Luna |
|---|---|
| First test: one-rule questions | 71% (42/59) |
| First test: a few steps / several rules at once | 5% (1/20) / 0% (0/30) |
| First test: compliance | 93% (28/30) |
| Newer, harder set | 17% (7/42) |
| Wrong facts: caught / noticed, answered anyway / missed, answered anyway | 50% / 10% / 40% (of 30) |
| Wrong facts: false alarms (40 valid notes) / clean twins right (30) | 10% / 43% |
| Whole-household decisions | declined all 10 questions that had an answer; correctly declined the trap |

- **It accepts impossible facts like the cheap models do.** "Priya is only 14 in 2026, so age-based required minimum
  distributions do not apply to her traditional IRA... Her RMD is therefore zero." It caught none of the over-limit
  amounts and a third of the impossible ages, but every conflicting fact and most swapped digits.
- **Without a calculator, it said it couldn’t do whole-household plans.** It declined all 10 that had an answer ("A reliable
  answer requires a full multi-year projection"). Honest, but no help to the person asking, which is the case for
  giving it a calculator.
- **How it was run, and what went wrong.** The first attempt (batches of 11–35) was thrown out: most replies were a
  bare "ANSWER: n" with no reasoning, which is not how the model answers a person. In the second attempt one session
  declined a whole batch of hard tax questions "from memory", and a few answers were skipped or malformed; those
  questions were re-asked one at a time. One first-test question was never answered, so that score is out of 139.
  Wrong-facts replies were judged by Claude Haiku 5.5 with the same rubric, and every "missed" label was read; none
  changed. Files: `runs/luna-codex-10x1/`, `runs/luna-gauntlet/`, `v2/runs/luna-codex/`, `v2/results/luna.json`,
  `v2/runs/luna-map/` (the prompt-id map and both attempts).

## Corrections

On 2026-11-15, GPT-6.1 Sol (a model from a different lab than the agents that built this) audited every published
claim against the saved data, read-only. What it found and what changed:

| # | Error | Fix |
|---|---|---|
| 1 | "Most wrong answers" came from the senior-deduction misreading | It's 99 of 342 wrong answers (29%), and 71% of those traced to a named misreading; the text says so |
| 2 | Some judge labels missed replies that named the planted mistake | Every "not named" label adjudicated; 18 changed (Sol 73% → 80%, Terra 62% → 67%); method above |
| 3 | "Every model was worst at over-limit amounts" | False for Sol and Terra; now "lowest pooled catch rate", with the exceptions named |
| 4 | `reproduce.sh` was described as rebuilding every number on the site | It rebuilds and checks the first test's leaderboard; the newer set regrades with `v2/grade.py`; the text says which is which |
| 5 | Replies that ran out of room were counted as declining for another reason | A separate "ran out of room" outcome (19 replies, 6 DeepSeek and 13 GLM), still counted as not caught |
| 6 | Run-to-run stability measured caught/not-caught but was described as "same outcome" | Both numbers reported and labeled |
| 7 | Chart label "Caught the mistake and asked" (catching doesn't require asking); text said the other columns were rule-based | Label is "Caught it"; the judge's role is described |
| 8 | Twin pairs counted each repeated run as a separate item | Runs averaged within each of the 30 pairs |
| 9 | The worked IRS form showed 2025 line numbers next to a 2026 question | Labeled as the 2025 form the 2026 rule comes from |
| 10 | "Single IRMAA thresholds are half the joint ones" | Not at the top tier ($500,000 single, $750,000 joint); corrected |
| 11 | Whole-household key check quoted as 290/290 | 203/203, matching `checks/GAUNTLET.md` |
| 12 | "Spending ten times what the family owns" | Monthly spending inflated ten- or twelvefold (about 1.2–1.7 times assets a year) |

It also flagged claims stronger than the evidence, all now scoped: the home page combined numbers from different models
and tests into one story; "at least as good" was claimed from overlapping intervals; "a product fix works for every
model" rested on one model; a harness check with p = 1 was described as proof of neutral routing; the 4,000-token
limit was per turn in the tool loop; PolicyEngine's check covers the first test's tax answers and 2026 returns, not
Arizona. The full list is in [docs/AUDIT-2026-11-15.md](docs/AUDIT-2026-11-15.md).

## Limits

- **Small samples.** 30 corrupted notes and 42 hard questions in the newer set; 10–15 questions per task per model in
  the first test. Most intervals are 25 to 35 points wide. Ranks inside a price tier are not reliable; the gap between
  "catches most" and "catches almost none" is.
- **Different settings in the two rounds.** First test: effort high, 16,000–32,000 tokens. Newer set: effort low,
  4,000 tokens per turn, set by the $5 cap. Scores at higher settings may be higher, most of all for models that ran
  out of room.
- **One run per item for the top models in the newer set.** Their run-to-run spread is unknown.
- **The prompt offers a way out.** Every wrong-facts prompt says NEED_INFO is allowed. Catch rates without that line
  would likely be lower. Not tested.
- **The planted mistakes are large.** A client aged 14, spending far beyond the household's means. A birth year off by
  one, or spending 20% too high, is untested and surely harder.
- **A model judged, an AI adjudicated.** Two judges from different labs agreed on 97.7%, and the lead AI agent
  adjudicated every "not named" label. No person has labeled a sample yet; agreement between models is not a measured
  error rate.
- **Clean accuracy mixes two things.** Half the notes need 2026 tax law. A model that answers a clean tax note wrong
  may be weak at tax, not at reading notes. The split is in `v2/results/summary.json` (`no_law`).
- **"Noticed, answered anyway" isn't always wrong.** For an amount over a limit, computing with the legal maximum and
  saying so is reasonable. It is counted separately for that reason.
- **Fourteen notes were fixed after I read the first replies.** The clean "conflict" notes didn't say the pension was
  fully taxable, and one odd-but-valid control was underspecified (whether a 401(k) catch-up must be Roth in 2026
  turns on 2025 wages over $150,000, and the note gave 2026 salary). Replies to the old wording are kept in
  `v2/runs/bad/stale.jsonl` and not graded.
- **Arizona is the least-verified key.** Both engines follow Laws 2026 ch. 140, but Arizona hasn't published 2026
  forms and no outside implementation checked these items. No CPA has signed off on any key.
- **Not run:** Sonnet and the Gemini models with the calculator, Claude Opus, any model at high effort in the newer
  set. Mistral Large 4 was dropped after it spent its whole reply limit thinking in the smoke test.
- **Templated notes.** Six notes per kind share a layout.

## What I'd do next

1. **A person checks the judge and the key.** Human labels on 100 replies, and a CPA sign-off on the answer key.
2. **Subtle mistakes.** The same note with spending 1.2×, 2×, 5× and 10× too high, birth years off by 1, 5 and 50.
   Where each model starts to notice is the useful number.
3. **Take away the way out.** Rerun with no mention of NEED_INFO, and with "always give a number", to measure how much
   the instruction is doing.
4. **Put validation in the calculator.** A calculator that explains its rule beats one that returns a number; the same
   may hold for inputs. Have the engine reject a 14-year-old retiree, and measure whether cheap models pass that on.
5. **Three runs for everyone, high effort for the top models.** About $40.

## Reproduce

```
./reproduce.sh                        # first test: re-verify the key, regrade saved replies, rebuild the leaderboard
.venv/bin/python v2/build_hard.py     # 42 hard items; fails if the two engines disagree
.venv/bin/python v2/build_bad.py      # 70 notes; fails if the engine and the checker disagree
./v2/run_all.sh                       # every run, resumable, stops at the cap in v2/runs/ledger.json (costs money)
.venv/bin/python v2/grade.py judge    # then: grade.py judge --second (costs money)
.venv/bin/python v2/grade.py          # summary.json and RESULTS.md, free, from saved replies and adjudication.jsonl
.venv/bin/python v2/build_site.py     # charts, web/data/v2.json, web/report.html
.venv/bin/python src/bake_site.py     # web/ → site/, readable without JavaScript
```
