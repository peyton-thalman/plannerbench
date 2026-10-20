# PlannerBench

Can AI do a financial planner's math? PlannerBench asks frontier models the questions advisors answer every week, using 2026 tax law, and grades them against an exact answer key.

The answer key comes from the MoneyGuide engine, whose tests check it against IRS and SSA publications. A separately written Python checker recomputes every answer from the published rules. Then [PolicyEngine-US](https://github.com/PolicyEngine/policyengine-us), an open-source tax model this project didn't write, recomputes every tax answer a third time. If any of them disagree on even one case, the benchmark doesn't ship. How every number is made, and how to check it yourself: [METHODOLOGY.md](METHODOLOGY.md).

```bash
./reproduce.sh      # re-verify the key, regrade every saved reply, rebuild the leaderboard; fails on any difference
```

## Tasks (200 each, 2,800 total)

| Task | What it tests | Source of truth |
|---|---|---|
| `federal_tax` | Full 2026 federal tax: brackets, LTCG stacking, age-65 and OBBBA senior deductions, taxable Social Security, NIIT | Rev. Proc. 2025-32, P.L. 119-21 |
| `taxable_ss` | Pub 915 worksheet | IRS Pub 915 |
| `rmd` | SECURE 2.0 start ages + Uniform Lifetime Table | Pub 590-B |
| `ss_claim` | Early reduction and delayed credits, month by month | SSA POMS |
| `bracket_room` | Roth conversion room to the top of a bracket | Rev. Proc. 2025-32 |
| `irmaa` | Medicare Part B with IRMAA, with cases weighted toward the cliffs | CMS 2026 fact sheet |
| `tax_torpedo` (v2) | Tax cost of a Roth conversion when it also makes Social Security taxable, pushes gains out of 0% and erodes the senior deduction | Composed from the rows above |
| `widow_penalty` (v2) | Extra tax when a survivor switches to single brackets and loses the smaller SS check | Composed from the rows above |
| `senior_phaseout` (v3) | Full tax for retirees inside the OBBBA senior-deduction phase-out band | Schedule 1-A Part V |
| `conversion_all_in` (v3) | Roth conversion's true cost: tax torpedo plus the IRMAA cliff it triggers two years later | Rows above + CMS tiers |
| `widow_all_in` (v3) | Widow's penalty including Medicare: single IRMAA tiers are half the joint ones | Rows above + CMS tiers |
| `rollover_flags` (compliance) | Which planted issues a 401(k)-to-IRA rollover recommendation missed: age-55 penalty exception, NUA, cost | Reg BI Care Obligation, FINRA RN 13-45 |
| `breakpoint` (compliance) | Sales charge after rights of accumulation (spouse and minor children count; adult child and other fund families don't) | Prospectus schedule given in the question |
| `comms_review` (compliance) | Which sentences of a client email break Rule 2210(d)(1); compliant look-alikes share keywords | FINRA Rule 2210(d)(1) |

## Run

```bash
~/moneyguide/node_modules/.bin/vite-node src/generate.ts 200
PB_EXCLUDE=data/cases.jsonl PB_SEED=$(cat private/seed) ~/moneyguide/node_modules/.bin/vite-node src/generate.ts 50 "$PWD/private/cases.jsonl"   # held-out set
.venv/bin/python -I checks/trust.py      # all seven trust layers → TRUST.md, checks/AUDIT.md, checks/POLICYENGINE.md
```

The full plan is in [SPEC.md](SPEC.md).

## Test models

```bash
export ANTHROPIC_API_KEY=...                       # from console.anthropic.com → API keys
.venv/bin/python src/run_models.py --models claude-sonnet-5-5 --per-task 10    # 60-question pilot, about $1–3
.venv/bin/python src/grade.py live-high-10x1                                    # writes runs/live-high-10x1/REPORT.md
.venv/bin/python src/leaderboard.py live-high-10x1                              # leaderboard/*.json for the leaderboard page
```

Keys not tied to a workspace also need `ANTHROPIC_WORKSPACE_ID`. Any OpenAI-compatible provider (OpenAI, OpenCode Zen, OpenRouter, DeepSeek) runs with an `oai:` prefix:

```bash
export OPENAI_BASE_URL=https://opencode.ai/zen/v1 OPENAI_API_KEY=...
.venv/bin/python src/run_models.py --models oai:<model-id> --per-task 10
```

Add `--split private` to ask the held-out set; its run folder ends in `-private`. For providers whose API doesn't report cost, put `"oai:<model-id>": [input $/M, output $/M]` in `prices.json` so cost per right answer is filled in.

Each run saves replies as they arrive, so if it stops you can run the same command again and it picks up where it left off. `--fake` runs the whole pipeline offline with a stand-in model. Refusals are scored as refusals, never quietly re-answered by a fallback model.

## Site

The public page lives in `site/` (plain HTML, CSS and JS, no build step) and reads `site/data/`, which comes from the graded runs:

```bash
.venv/bin/python src/leaderboard.py live-high-10x1 with-rule-10x1
.venv/bin/python src/build_site.py live-high-10x1 with-rule-10x1
cd site && vercel deploy --prod      # Vercel project "plannerbench" → plannerbench.vercel.app
```

## Log

- 2026-10-20: Credibility pass. PolicyEngine-US now recomputes every tax answer as a third, outside implementation: 1,600/1,600 public and 400/400 private agree within $2, the senior phase-out included. (Its first run showed 82%. Both gaps were harness mistakes on my side: PolicyEngine keeps NIIT outside "tax before credits," and its taxable-SS variable is per person.) Added a 700-case private held-out set from a secret seed, 95% intervals and paired McNemar tests on every number, cost per right answer, a run `meta.json` recording settings, `./reproduce.sh`, and METHODOLOGY.md. Fixed a fairness bug: 54 federal_tax questions called a single filer "1 spouse age 65 or older"; 561 prompts reworded, no inputs or answers changed. With intervals, Haiku's widow_all_in gain from the rule (20% → 60%) is not significant (p = 0.29). The other three rule effects are (p < 0.01). Haiku costs $1.29 per 1,000 right answers to Sonnet's $13.27.

- 2026-10-20: Compliance track + the rule experiment. Both models scored 100% on all three compliance tasks, where each issue is defined in the question: when the rule is stated, they apply it. So the same senior_phaseout and widow_all_in questions were asked again with the two-line Schedule 1-A Part V instructions in front (`--context contexts/schedule_1a_part_v.md`, run with-rule-10x1). Sonnet went 10% → 100% and 20% → 100%; Haiku 0% → 90% and 20% → 60%. The models don't lack the math. They lack the current rule. Next: make the compliance questions name issues without defining them, so they test knowledge, not reading.
- 2026-10-20: v3 stacked tasks + Haiku 5.5. On 110 questions: Sonnet 79% (single-step 97%, multi-step 90%, stacked 37%); Haiku 71% (97 / 75 / 17). 19 of Sonnet's 23 misses and 20 of Haiku's 32 are one misreading: the senior-deduction phase-out taken once off $12,000 instead of off each $6,000. Both models agree on the wrong number, so model agreement is not evidence the key is wrong; the IRS form decides. The grader now labels this mistake automatically.
- 2026-10-20: Sonnet 5.5 on the first 20 v2 cases: tax_torpedo 10/10, widow_penalty 8/10. Both widow misses were the same mistake: taking the OBBBA senior-deduction phase-out once off the couple's combined $12,000 instead of off each spouse's $6,000. Schedule 1-A Part V (lines 35, 36a, 36b) confirms the key, which applies it per spouse. The new-law phase-out is a real weak spot; it never came up in v1 because the federal_tax pilot cases didn't hit it.
- 2026-10-20: First live pilot (Sonnet 5.5, 60 v1 cases): 97%. Both misses were the model's (wrong full retirement age for 1956; counted 13 months instead of 15). The key held. Single-step math is nearly solved, so v2 multi-step tasks were added for headroom.
- 2026-10-20: The independent checker caught a real engine bug. MAGI exactly at the top IRMAA threshold ($500k single / $750k joint) was placed one tier low. CMS defines that tier as "greater than or equal to." Fixed in the engine, and threshold-exact cases are now 20% of the IRMAA set.

## Next

1. **Model runner.** Ask Claude, GPT and Gemini each case and grade their `ANSWER:` lines. Needs API keys and a few dollars of tokens.
2. **Leaderboard page.** Scores by model and task, plus the most common wrong answers. The wrong answers are the story.
3. **Planning tools as MCP.** Expose the engine as Claude tools and rerun. The chart to publish is "Claude alone: X% · Claude + planning tools: Y%."
4. **Write-up.** "I tested frontier AI on 1,200 retirement-planning questions." Post it, then send it to product teams at Jump, Altruist and the labs.
