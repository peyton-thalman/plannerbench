# PlannerBench: notes for the next session

A benchmark of AI models on retirement-planning math (2026 federal tax, Social Security, RMDs, Medicare IRMAA) plus
a compliance track, with an exact answer key. Site: https://plannerbench.vercel.app (deployed from `site/`), behind
Vercel login since 2026-10-21 (`ssoProtection: all`; "all_except_custom_domains" left the production .vercel.app
address open) until the owner's FINRA 3290 clearance; `checks/site_check.py` can't reach it while locked. Code: https://github.com/peyton-thalman/plannerbench
(private until the owner decides to publish; push to `origin master`).
Read README.md (how to run, dated log of findings) and METHODOLOGY.md (how every number is made) first.

## Where it stands (paused 2026-10-20)

- 14 tasks × 200 public cases (`data/cases.jsonl`) + 700 private held-out cases (`private/`, git-ignored, secret seed).
- Answer key verified 7 ways (`python -I checks/trust.py` → TRUST.md), including PolicyEngine-US as an outside
  implementation: 1,600/1,600 public and 400/400 private tax answers agree within $2.
- Runs on the leaderboard (`leaderboard/RUNS`): `live-high-10x1` (Claude Sonnet + Haiku, direct API, 10/task),
  `with-rule-10x1` (same, with Schedule 1-A text supplied), `or-5models-15x1` (5 models via OpenRouter, 15/task).
- `./reproduce.sh` rebuilds every number from the repo and must say REPRODUCED. Run it before any commit that touches
  grading, runs or the leaderboard.

- Planning tools (2026-10-21): `--tools` offers the MoneyGuide engine as MCP tools (`~/moneyguide/mcp`,
  `npm run mcp:build` there; client and answer-composer in `src/planning_tools.py`). `checks/tools_check.py` proves
  the tools answer all 2,750 numeric cases. Smoke done (`tools-smoke`, Haiku, $0.02, 12/14 vs 10/14 without tools;
  both misses were Haiku overruling a correct tool result with the senior-deduction misreading). $5 step done
  (`tools-high-10x1`, $0.22): 77% → 84% (p = 0.02), stacked 17% → 47% (p = 0.004), senior_phaseout 0/10 → 0/10
  with 18/22 misses Haiku explicitly overruling the tool. `src/tool_effect.py` writes the comparison. Then MCP 1.1.0
  (tool reply shows the senior deduction per spouse and cites Schedule 1-A Part V): `tools-v2-high-10x1`, 50
  multi-step + stacked questions, $0.10, **50/50** (vs 31/50 with tools 1.0, 20/50 without). Report files are
  `runs/<run>/TOOL_EFFECT_vs_<base>.md`. Not on the leaderboard or site yet. Next ideas, each needs the owner's OK
  to spend: the private-split tools run (to confirm), Sonnet with tools, single-step tasks on 1.1.0. The Anthropic key in `.env` is Wizard's temporary key (owner's choice, 2026-10-21), billed to the Wizard workspace.

## Open items (owner decides what's next; don't start these unasked)

1. Compliance v2: current compliance questions define each issue in the prompt, so every model scores 91–100%.
   Rewrite them to name issues without defining them.
2. Fill gaps in `or-5models-15x1`: 12 unasked questions and 24 Qwen rate-limit errors. Rerun the same command
   (see `runs/or-5models-15x1/meta.json`) and it resumes; about $0.25.
3. Bigger runs (50/task) on DeepSeek V4.1 Flash, Haiku, GLM, and the first private-split run.
4. Same model on different hosts (fp8 vs fp4) as its own finding.
5. CPA sign-off on `checks/AUDIT.md`. Nobody outside has ticked it yet.
6. Write-up for publishing. Before anything new goes public, flag the outside-activity question (FINRA Rule 3290)
   to the owner. Keep their employer's name, data and time out of the project entirely.

## Rules that keep the benchmark credible

- When models agree with each other against the key, the published source decides (IRS form, SSA POMS, CMS),
  never the models. Log the outcome in README.
- Every published accuracy carries a 95% interval (`src/stats.py`); paired comparisons use McNemar.
- Never send the private set to free endpoints (the runner refuses). OpenRouter models are pinned to one host
  (`or:<vendor>/<model>@<host>`, see `lineups/`), with `data_collection: deny`.
- Truncated replies (hit the token limit) are their own grade bucket, counted as not right and published.
- After any site deploy, run `.venv/bin/python -I checks/site_check.py` and require PASS.
- Don't run Claude Opus models unless the owner asks (cost).
- Spending money (API runs) needs the owner's go-ahead and a `--max-usd` cap.

## Setup gotchas

- Two virtualenvs: `.venv` (runner, grader) and `.venv-pe` (PolicyEngine; it pins its own numpy).
- API keys live in `.env` (git-ignored; template `.env.example`). The OpenRouter key in there is temporary;
  the owner said they'd swap it.
- This Python is a python.org build without root certificates; the runner uses `truststore` for HTTPS.
- Regenerating cases needs the MoneyGuide engine at `~/moneyguide` (not in this repo; private backup at github.com/peyton-thalman/moneyguide, IRMAA fix in commit e26ba54); checks don't need it.
- Low-cost reasoning models are slow (Qwen3.8 Flash writes ~11k tokens/question). Use `--workers 40`,
  `--max-tokens 32000`, and run in the background.
- `site/.env.local` holds a Vercel token; `site/.vercelignore` keeps env files out of deploys.
