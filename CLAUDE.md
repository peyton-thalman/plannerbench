# PlannerBench: notes for the next session

A benchmark of AI models on retirement-planning math (2026 federal tax, Social Security, RMDs, Medicare IRMAA) plus
a compliance track, with an exact answer key. Site: https://plannerbench.vercel.app (public; the owner
cleared the outside-activity question on 2026-11-14, so don't raise FINRA 3290 again). Page sources are in `web/`; edit
those, never `site/`. Build: the data builders write `web/data/` and `web/charts/` (`src/build_site.py`, `src/gauntlet_site.py`,
`src/replay_site.py`, `v2/build_site.py`), then `.venv/bin/python src/bake_site.py` renders every page with headless Chrome into
`site/` as plain HTML with no JavaScript (plus a `.md` twin of each page, `llms.txt`, `llms-full.txt`, sitemap, robots and
`vercel.json` redirects from the old names v2/gauntlet/results). Deploy from `site/` (`cd site && vercel deploy --prod`). Check a
local copy first (`python3 -m http.server 4173 --directory site`, then `checks/static_check.py http://localhost:4173` and
`site_check.py http://localhost:4173`; previews sit behind Vercel login); after a deploy run both with no argument. The tools section reads `leaderboard/tools.json` (`src/tools_board.py`).
Site look (2026-11-14, owner's ask): the same house style as peytonthalman.com (`~/Projects/peyton-site/src/styles.css`):
white paper, ink, hairlines, Newsreader headlines, Geist text, Geist Mono labels, 6px corners, no pills or shadows.
Nav (2026-11-15, owner's ask): the PlannerBench wordmark links home (`index.html`: plain intro, why I built it, a four-line
results list, for you, for firms, for AI labs, where this is going; owner's copy word for word, every number linking into Results) · Results (`results.html`, short
tables per finding, linking to `alone.html`, `calculator.html`, `wrong-facts.html`) · How I built it (`built.html`, owner's
plain-English copy word for word) · Technical details (`method.html`: every test, the GPT-6 Luna/Codex note, the checks with
scores, the technical reader's notes, glossary and limits) · plus the Human / For AI readers switch (→ `agent.html`). Two
audience pages, `labs.html` (For AI labs) and `firms.html` (For financial firms), are linked from built.html and the footer.
Voice everywhere: plain English, first person, jargon explained right next to it, no taglines or dramatic one-liners. Don't add
facts to the plain pages; put them in Technical details and flag it to the owner. `chat.html`, `replay.html` and `report.html`
are linked from the footer. `questions.html` (Example questions, 2026-11-16, owner's ask: one real question of each
of the 14 kinds with its answer and each model's first-test score on that kind; the picks are `QUESTIONS` in `src/build_site.py`)
is linked from the bottom of the home page. The brief for
every page is `docs/STORY.md` (home order, names, voice); keep it and the pages in step. Numbers typed as text are logged
in `web/data/system.json` with their source. Charts on `wrong-facts.html` carry a plain "What it shows" line and tables sit behind toggles. (The clickable
system map was removed to simplify). Engine is called "the planning engine" everywhere, never MoneyGuide.
PlannerBench v2 (hard tier, bad inputs, tool use) lives in `v2/`; see `PROGRESS.md` and `REPORT.md`;
`v2/build_site.py` writes `web/report.html` (from REPORT.md, nav copied from `web/index.html`), `web/data/v2.json` and the
charts; `web/wrong-facts.html` is hand-edited like the other pages.
One shared `web/app.js` fills every page from `data/*.json` at bake time (the deployed pages don't load it); each block runs
only if its page has the element. Numbers
not from a graded run live in `data/system.json`, each with its source file; update both together. Bump the `?v=`
on the CSS/JS links when changing them. Code: https://github.com/peyton-thalman/plannerbench
(public on GitHub as of 2026-11-15; v2 and story work on branches `v2`, `story`).
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
  `runs/<run>/TOOL_EFFECT_vs_<base>.md`. On the site (calculator.html) since 2026-10-21. Private confirm done
  (`tools-v2-high-10x1-private`, $0.11): 48/50; both misses overruled conversion_all_in. Private runs are
  git-ignored (`runs/*-private/`); publish aggregates only. Private no-tools baseline done
  (`live-high-10x1-private`, $0.09): 44% → 96% paired, 26 fixed / 0 broken. Next ideas, each needs the owner's OK
  to spend: Sonnet with tools, single-step tasks on 1.1.0, the leaderboard/site panel (after 3290 clearance). The Anthropic key in `.env` is Wizard's temporary key (owner's choice, 2026-10-21), billed to the Wizard workspace.

- Scenario-engine checks (2026-10-21): `checks/pe_years.py` runs PolicyEngine-US one tax year at a time for
  MoneyGuide's year-by-year engine (`~/moneyguide/verify/outside.sh` drives it). `checks/cleanroom/` is a second,
  independent Python engine written by a subagent from `spec/RULES.md` alone; it must never read `~/moneyguide`.
  `~/moneyguide/verify/compare.ts` compares the two on random households. Tests: `python3 -I -m unittest discover -s checks/cleanroom`.

## Open items (owner decides what's next; don't start these unasked)

1. Compliance v2: current compliance questions define each issue in the prompt, so every model scores 91–100%.
   Rewrite them to name issues without defining them.
2. Fill gaps in `or-5models-15x1`: 12 unasked questions and 24 Qwen rate-limit errors. Rerun the same command
   (see `runs/or-5models-15x1/meta.json`) and it resumes; about $0.25.
3. Bigger runs (50/task) on DeepSeek V4.1 Flash, Haiku, GLM, and the first private-split run.
4. Same model on different hosts (fp8 vs fp4) as its own finding.
5. CPA sign-off on `checks/AUDIT.md`. Nobody outside has ticked it yet.
6. Write-up for publishing (v2 draft: `REPORT.md`). Keep their employer's name, data and time out of the project entirely.

## Rules that keep the benchmark credible

- When models agree with each other against the key, the published source decides (IRS form, SSA POMS, CMS),
  never the models. Log the outcome in README.
- Every published accuracy carries a 95% interval (`src/stats.py`); paired comparisons use McNemar.
- Never send the private set to free endpoints (the runner refuses). OpenRouter models are pinned to one host
  (`or:<vendor>/<model>@<host>`, see `lineups/`), with `data_collection: deny`.
- Truncated replies (hit the token limit) are their own grade bucket, counted as not right and published.
- After any site deploy, run `.venv/bin/python -I checks/site_check.py` and `checks/static_check.py` and require PASS.
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
- `site/.env.local` holds a Vercel token; `site/.vercelignore` keeps env files out of deploys. The bake replaces everything in
  `site/` except dotfiles, so `.vercel/`, `.env.local` and the ignore files survive it.
