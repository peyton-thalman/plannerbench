# Cold read, round 4 (2026-11-15)

Scores so far — hiring manager (GPT-6.1 Sol): 7 → 7 → 8 → 8. Everyday reader (Claude Haiku): 4 → 5 → 6 → 6.

## Hiring manager (8/10): to make it a 10

- Shorten Home to: the problem, three memorable results, one verification paragraph, the reading path.
- Every experiment gets the same compact identifier, sample size, settings and grading standard wherever its scores appear.
- Report's November calculator table: use the actual paired baselines (one run alone vs one run with the calculator, e.g. Haiku 48% / 20 of 42), not the two-run averages.
- How I built it, Oct 21 timeline: "the overruling stopped" contradicts the two held-back misses that were overrules → "almost stopped".
- "Prove" (Home "Why you can trust the numbers", How I checked "prove my own answers") → "check" / "verify"; agreement among implementations is strong but not proof.
- Report summary "a free or cheap one will usually be wrong" → scope to the models and quick-answer settings tested.
- Calculator, whole-household: "every decision and every number right" → use the defined standard (decision right and every number within 2%).
- How I built it: "$26,002" reads like a real client loss → say it's a simulated difference in projected wealth.
- Home finding 3: "50 hardest questions from the first test" — say how they were picked (the five multi-step and stacked tasks, 10 each).
- Agent label looks like a reading-mode toggle but leads to a directory → label/explain.
- Wrong facts: "Across all 720 replies" — explain the denominator (30 files × repeated runs per model) in visible text.
- How I checked: 2,750 calculator-checked answers vs 2,800 questions — explain the 50 (compliance questions have no number).
- Replays: question selector shows first-RMD, muni, QCD, MAGI, IRMAA at once — plain labels.
- Repetition: four findings, verification and audit recur on Home, finding pages, Built and Report. Keep full verification on How I checked and corrections in the Report; elsewhere one line + link.
- Portfolio (peytonthalman.com, separate repo; owner's call): "The newest frontier models now saturate it" → name the first test; "The answer key is computed three separate ways" → coverage limits.

## Everyday reader (6/10): to make it a 10

- A plain-English bottom line at the very top of Home: three short bullets. Move "How to read the numbers" below the fold.
- Define the planning engine, answer key, held-back questions and "caught" in one sentence each, on first use.
- One consistent label per model group (top / middle / cheap-free, with the price tier) used on every page; "three cheap models" vs "cheap and free models" vs DeepSeek 61% confused them.
- Replace "Rule 2210(d)(1)" and "via OpenRouter / relay service" in visible text with a plain note, or move to How I checked.
- Rewrite Home's "Why you can trust the numbers" for a non-expert: one sentence on what was checked and by whom; technical details on How I checked.
- One "what to do this week" action on the first screen.
- Didn't understand: "held-back", "reasoning effort", "quicker-answer settings", "separately written checker", "two-way check", "written blind", "4,000 / 4,000", "clean twin", "QCD" (gloss easy to miss).
