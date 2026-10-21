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

Keys not tied to a workspace also need `ANTHROPIC_WORKSPACE_ID`. Keys can live in `.env` (git-ignored; see `.env.example`) instead of the shell.

**Other labs' models go through OpenRouter**, pinned to one host so a score names the deployment that produced it (the same open model is served by dozens of hosts, many at 4-bit precision):

```bash
.venv/bin/python src/run_models.py --models @lineups/cheap.txt --per-task 1 --run smoke          # every host answers? ~1 cent
.venv/bin/python src/run_models.py --models @lineups/cheap.txt --per-task 50 --max-usd 10        # stops at $10; rerun to resume
```

`or:<vendor>/<model>@<host>` allows only that host with no fallback. Hosts that keep prompts for training are always excluded, and `--split private` also requires zero data retention. Each reply records the host that served it and OpenRouter's billed cost. `--max-usd` stops a run at a spend limit (it may go over by the questions already in flight); questions are asked case by case across models, so a stopped run leaves every model with the same questions. Any other OpenAI-compatible provider (OpenAI, OpenCode Zen, OpenRouter, DeepSeek) runs with an `oai:` prefix:

```bash
export OPENAI_BASE_URL=https://opencode.ai/zen/v1 OPENAI_API_KEY=...
.venv/bin/python src/run_models.py --models oai:<model-id> --per-task 10
```

**With planning tools.** `--tools` asks the same questions with the MoneyGuide engine available as MCP tools (build them once: `cd ~/moneyguide && npm run mcp:build`). How it's kept fair: [METHODOLOGY.md](METHODOLOGY.md#with-planning-tools---tools).

```bash
.venv/bin/python -I checks/tools_check.py                                       # the tools answer every numeric question (free)
.venv/bin/python src/run_models.py --fake --tools --per-task 10                 # whole pipeline through the MCP server, offline
.venv/bin/python src/run_models.py --models claude-haiku-5-5 --tools --per-task 1 --max-usd 1 --run tools-smoke
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

- 2026-10-21: **Tools that show their work: 50/50 on the hardest questions** (`tools-v2-high-10x1`: Claude Haiku 5.5, effort high, the 5 multi-step and stacked tasks at 10 each, $0.10; MCP server 1.1.0, MoneyGuide `b3c29bd`). One change from `tools-high-10x1`: the `federal_income_tax` reply now splits the deduction into standard and senior parts and works the senior phase-out per person, with the rule and its form lines (Schedule 1-A Part V, lines 35-36b) in the reply. The engine's answers didn't change; the public set regenerates byte-for-byte. On the same 50 questions: **62% → 100%** against the first tools (19 fixed, 0 broken, p < 0.0001) and **40% → 100%** against no tools (30 fixed, 0 broken). senior_phaseout went 0/10 → 10/10 and widow_all_in 6/10 → 10/10. Dollars off fell to $0. 18 of the 50 replies use the per-spouse rule in their own words. Caveats: one run of 50 public questions, one model. The explanation targets a misreading this benchmark had already found, so it says nothing about misreadings nobody has named yet. The single-step and compliance tasks weren't rerun. Lesson: a tool that gives a model the right number loses to the model's confident wrong rule, and a tool that shows the rule and its source wins. Next: confirm on the private held-out set (separate ask), then Sonnet.
- 2026-10-21: **Claude + planning tools, 140 questions** (`tools-high-10x1`: Claude Haiku 5.5, effort high, 10 per task, $0.22 against $0.14 without tools; report in `runs/tools-high-10x1/TOOL_EFFECT_vs_live-high-10x1.md`, from `src/tool_effect.py`). On the same 140 questions: **77% → 84%** (13 fixed, 3 broken, p = 0.02). Stacked questions **17% → 47%** (9 fixed, 0 broken, p = 0.004): conversion_all_in 3/10 → 8/10, widow_all_in 2/10 → 6/10. Single-step was already 97% and stayed there (95%, p = 1). **senior_phaseout stayed 0/10: on all ten, Haiku called the tax tool, got the key, and replaced it.** 18 of the 22 misses with tools are that: the tools, as Haiku called them, give the key, and the final answer is the per-couple senior-deduction misreading. All 18 say so in the reply ("the tool returned $16,074, but I believe it overstates the senior deduction phase-out", "so I recalculated by hand"). The other 4 misses: two answered without calling a tool, one misread the bracket table (top of 12% taken as top of 22%, $110,600 off), one used the tools wrongly. Dollars off went up, $171 → $1,255 a question, because of that one bracket miss; the median miss is $719 against $568. Lesson for tool design: a right answer isn't enough when the model holds a confident wrong rule. The tool's reply said nothing about how the deduction was figured or where the rule comes from. Next test: the same tools with the reply showing the per-spouse phase-out and citing Schedule 1-A Part V.

- 2026-10-21: **First tools run, smoke test** (`tools-smoke`: Claude Haiku 5.5, effort high, 1 question per task, $0.02, 40 seconds). Everything worked: 14/14 answered, 0 tool errors, at most 7 calls on a question. On the same 14 questions Haiku went from 10/14 without tools to 12/14 with them; both widow questions flipped to right. That's far too few questions to count as a result. The two misses are the finding: **Haiku had the right number from the tool and overruled it.** On `senior_phaseout` the tool returned the key ($16,152) and Haiku replaced it with $15,928, saying the tool wrongly applied the phase-out "separately to each spouse's $6,000." That is the same per-couple misreading this benchmark found earlier, and Schedule 1-A Part V confirms the tool's per-spouse method. On `conversion_all_in` it called the tax tool before and after ($13,680 apart), then redid the tax by hand without the phase-out ($14,501) and used that, missing by $820. A verified calculator only helps if the model trusts it over its own wrong rule. The $5 run (10 per task) will show how often that happens.

- 2026-10-21: **Planning tools over MCP, no API calls yet.** The MoneyGuide engine is now an MCP server (`~/moneyguide/mcp/server.ts`, six general calculators), and `--tools` lets Claude call it on the same questions. Before any model sees it, `checks/tools_check.py` answers every numeric question from tool calls alone: 2,200/2,200 public and 550/550 private match the key, so a miss in a tools run is the model's. The tool loop was tested against a pretend API client (two calls in one turn, a bad argument returned as a readable error, thinking passed back, tokens summed over turns), and `--fake --tools` runs the whole pipeline through the real server. The site went behind Vercel login until the outside-activity clearance.

- 2026-10-20: Dollars off, not just right or wrong. Every numeric reply is now scored by how many dollars a year it is off from the key (monthly answers times 12; right = $0), with a "material" line at $1,000 a year (`src/dollars.py`, checked by `checks/dollars_check.py`, which recomputes it from the raw replies and must match). No new API calls. The ranking changes: Sonnet 5.5 is 84% accurate and DeepSeek V4.1 Flash 75%, but both are off by the same $161 a year per question, because DeepSeek's misses are smaller (median $300 vs $677). gpt-oss-120b is off by $1,929 per question, and 40% of its answers miss by $1,000 or more. Sizes vary a lot by mistake: the pre-2022 RMD table is rare but typically $5,675 too high, which would push a client to withdraw and pay tax on money they didn't need to. The senior-deduction misreading is common and typically $669. "Right tier, wrong cents" on IRMAA is $1.20. Qwen3.8 Flash gave a number on only 48 questions (it often ran out of tokens), so its dollar score covers less.
- 2026-10-20: First models from other labs, through OpenRouter with each model pinned to one host (run `or-5models-15x1`, 15 questions per task, 32k-token limit, $3.66 billed). Harness check passed: Claude Haiku 5.5 scored 77% on the same 140 questions both directly and through OpenRouter (p = 1.0). Overall: DeepSeek V4.1 Flash 75%, Haiku 5.5 73%, GLM 5.3 Flash 62%, Qwen3.8 Flash 45%, gpt-oss-120b 39%. DeepSeek tied Haiku overall (p = 0.61) and beat it on stacked questions (36% vs 20%, p = 0.04, suggestive at n = 45), matching Sonnet there (p = 0.73). Haiku was cheapest per right answer ($1.34 per 1,000); Qwen was the most expensive ($20.23) despite a low token price, because 49% of its replies ran out of tokens while thinking. The senior-deduction misreading isn't Claude-only: DeepSeek made it 21 times and GLM 7. gpt-oss used the Uniform Lifetime Table replaced in 2022 on all 8 RMDs it missed (now a named mistake). Several models put Medicare premiums $0.10 above the key; SSA POMS HI 01101.020 matches the key to the cent. The 12 slowest questions were left unasked when the run was stopped; 24 Qwen requests were rate-limited (not scored). Both can be filled by rerunning the same command.

- 2026-10-20: Credibility pass. PolicyEngine-US now recomputes every tax answer as a third, outside implementation: 1,600/1,600 public and 400/400 private agree within $2, the senior phase-out included. (Its first run showed 82%. Both gaps were harness mistakes on my side: PolicyEngine keeps NIIT outside "tax before credits," and its taxable-SS variable is per person.) Added a 700-case private held-out set from a secret seed, 95% intervals and paired McNemar tests on every number, cost per right answer, a run `meta.json` recording settings, `./reproduce.sh`, and METHODOLOGY.md. Fixed a fairness bug: 54 federal_tax questions called a single filer "1 spouse age 65 or older"; 561 prompts reworded, no inputs or answers changed. With intervals, Haiku's widow_all_in gain from the rule (20% → 60%) is not significant (p = 0.29). The other three rule effects are (p < 0.01). Haiku costs $1.29 per 1,000 right answers to Sonnet's $13.27.

- 2026-10-20: Compliance track + the rule experiment. Both models scored 100% on all three compliance tasks, where each issue is defined in the question: when the rule is stated, they apply it. So the same senior_phaseout and widow_all_in questions were asked again with the two-line Schedule 1-A Part V instructions in front (`--context contexts/schedule_1a_part_v.md`, run with-rule-10x1). Sonnet went 10% → 100% and 20% → 100%; Haiku 0% → 90% and 20% → 60%. The models don't lack the math. They lack the current rule. Next: make the compliance questions name issues without defining them, so they test knowledge, not reading.
- 2026-10-20: v3 stacked tasks + Haiku 5.5. On 110 questions: Sonnet 79% (single-step 97%, multi-step 90%, stacked 37%); Haiku 71% (97 / 75 / 17). 19 of Sonnet's 23 misses and 20 of Haiku's 32 are one misreading: the senior-deduction phase-out taken once off $12,000 instead of off each $6,000. Both models agree on the wrong number, so model agreement is not evidence the key is wrong; the IRS form decides. The grader now labels this mistake automatically.
- 2026-10-20: Sonnet 5.5 on the first 20 v2 cases: tax_torpedo 10/10, widow_penalty 8/10. Both widow misses were the same mistake: taking the OBBBA senior-deduction phase-out once off the couple's combined $12,000 instead of off each spouse's $6,000. Schedule 1-A Part V (lines 35, 36a, 36b) confirms the key, which applies it per spouse. The new-law phase-out is a real weak spot; it never came up in v1 because the federal_tax pilot cases didn't hit it.
- 2026-10-20: First live pilot (Sonnet 5.5, 60 v1 cases): 97%. Both misses were the model's (wrong full retirement age for 1956; counted 13 months instead of 15). The key held. Single-step math is nearly solved, so v2 multi-step tasks were added for headroom.
- 2026-10-20: The independent checker caught a real engine bug. MAGI exactly at the top IRMAA threshold ($500k single / $750k joint) was placed one tier low. CMS defines that tier as "greater than or equal to." Fixed in the engine, and threshold-exact cases are now 20% of the IRMAA set.

## Next

(Superseded in part by the log above; see the latest report for the current list.)

1. **Model runner.** Ask Claude, GPT and Gemini each case and grade their `ANSWER:` lines. Needs API keys and a few dollars of tokens.
2. **Leaderboard page.** Scores by model and task, plus the most common wrong answers. The wrong answers are the story.
3. **Planning tools as MCP.** Expose the engine as Claude tools and rerun. The chart to publish is "Claude alone: X% · Claude + planning tools: Y%."
4. **Write-up.** "I tested frontier AI on 1,200 retirement-planning questions." Post it, then send it to product teams at Jump, Altruist and the labs.
