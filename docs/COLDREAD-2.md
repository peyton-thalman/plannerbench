# Cold read, round 2 (2026-11-15, after the rewrite)

Two readers who had never seen the site read a local copy over HTTP. Round 1 scores: hiring manager 7/10,
everyday reader 4/10. Round 2: hiring manager 7/10 (different, finer issues), everyday reader 5/10.
Note: both read raw HTML, so text inside closed `<details>` toggles counted as visible to them. Real visitors
see toggles closed. Still: anything a reader must cross to get the story should be plain.

Already done by the lead after this read: nav order is now AI on its own → With a calculator → Wrong facts →
How I checked → How I built it (finding order); footer link "Chat demo".

## Hiring manager (GPT-6.1 Sol), 7/10: where it got lost

- Home "2,800 questions" vs AI on its own "10–15 questions per task per model": reader thought each model answered
  2,800. Put generated set size and evaluated sample size together immediately.
- Home "The biggest risk is what you type in": no comparison shows it causes more harm than wrong rules or tool
  misuse. "Biggest risk" is broader than the evidence. Say what was measured.
- AI on its own "4 models from 3 labs gave the same wrong answer": the example shows five matching rows incl. Haiku
  by two routes. Explain the count.
- AI on its own "The math isn't the problem": Wrong facts quotes a model saying $70,200 exceeds $798,000. Arithmetic
  and comparison also fail. Drop the categorical wording.
- Nav order vs finding order and "Next" links: one reading order everywhere (fixed in nav; check every page's
  "Next" link follows: home → AI on its own → With a calculator → Wrong facts → How I checked → How I built it).
- Calculator: six numbered sections; lost track of which experiment supports which claim. Give each experiment a
  compact ID line (questions actually evaluated, models, settings, grading rule, held-out or not).
- Calculator: Haiku 52% vs "20/42" explained only after the mismatch; table's "2 runs per item" sits beside tool
  results that used one run. Label each condition directly.
- Calculator: DeepSeek 29% → 79% — the tool condition also allowed more total output. Frame it as the improvement
  from the tool-enabled setup, with part of the mechanism unresolved.
- Wrong facts headline: cheap models catch "almost none", but DeepSeek catches 61% and GLM 40%. Headline and
  "Cheap models trust whatever you tell them" must say "three cheap models".
- Wrong facts: "caught" = noticed AND withheld a number. Differs from ordinary "noticed". Sol named the problem in
  every corrupted note yet scores 80%. Define before the headline comparison.
- Method: "Nobody's opinion is involved" and "No question is used unless all of these pass" — wrong-facts labels
  need judgment and the human audit hasn't happened. Bound these statements.
- Method vs Home: "to the dollar" vs checks that allow $1 (second engine) and $2 (PolicyEngine). Say "within $1".
- Built: "Never let the builder grade itself" — the lead agent adjudicated 18 labels. State the principle as
  practiced. "Hold out what you tune on" reads backwards; rename (e.g. "Keep a test set nobody tunes on").
- Chat: "Try it" then "Not yet". Label as a private demo. "It never adds a number of its own" reads as a guarantee;
  evidence is instructions + a checker that detects extra numbers — scope it. Costs/savings breakdown doesn't
  reconcile with the stated $113,779 lifetime tax saving / $132,193 wealth gain; explain or fix.
- Replays: "The question" shows options A–C without the household background; lead with a readable household
  summary before raw calls.
- Repetition: the four findings, verification counts, AI authorship, audit and pending checks recur on many pages.
  Make each page add something new; say each once where it belongs, link elsewhere.

What would make it a 10 (Sol): one reading order; an ID line per experiment; three or four headline findings each
with one example and one result, secondary experiments linked as detail; replace broad claims about "AI", "cheap
models", "the math", "biggest risk" with the behavior measured; fix the counting/baseline/tolerance/grading-language
mismatches; each page adds something new; connector labeled as a private demo; first replay readable without JSON.

## Everyday reader (Claude Haiku), 5/10

Took away the story correctly. Didn't understand:
- Home: "a trusted calculator" (is it on the site? can I use it?); the straight-answer box never names which AIs are
  best vs cheap/free; Finding 2 "98% vs 62%" — why these two, and that 37% and 62% are different tests; Finding 3
  "40% → 100%" looks universal; "the first test" / "the newer, harder set" never explained; "answer key", "planning
  engine", "PolicyEngine-US", "CPA", "the audit" undefined; "directed AI coding agents" and "the audit found 12
  errors" — does that make it more or less trustworthy?; the Human | Agent switch is unexplained.
- AI on its own: Compliance, Never finished, Cost per 1,000 right, Overall, "OpenRouter → DeepInfra (fp8)",
  Schedule 1-A Part V, modified adjusted gross income, RMD, pre-2022 RMD table, stacked, one-rule.
- Wrong facts: clean twin, false alarms, declined for another reason, ran out of room, noticed/answered anyway,
  top price / middle price / cheap tiers; 95% interval bands.
- How I checked: McNemar's test, held-back set, reproduce.sh, verify/COMPARE.md, "Same model, two routes".
Would have stopped at How I checked's technical section and at the wrong-facts tables; "a CPA hasn't signed off"
made them wonder whether to trust the numbers at all (explain why the numbers are still solid).

What would make it a 10 (Haiku): a one-sentence plain answer and bottom line naming which AI; define each term on
first use (IRA, RMD, answer key, the calculator, the first test, the newer test) and a short "How to read the
numbers" box near the top; make "best" consistent (Gemini 3.8 Flash catches 92% but false-alarms on 50%; say why
it isn't "best"); remove confusing duplicate numbers and put the caveat beside "40% → 100%"; technical detail
behind a clearly labeled toggle with a short summary per finding page; explain or remove the Human | Agent switch;
end with three things to do before trusting an AI with a retirement number.
