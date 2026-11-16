# PlannerBench v2: progress

**Live:** https://plannerbench.org/v2.html (report: `/report.html`). Deployed to production and pushed to
`origin v2` on 2026-11-14 at the owner's say-so, with the site restyled to match peytonthalman.com.
**Read `REPORT.md` first; its last five lines are the summary.**

Branch `v2`. Everything for v2 lives in `v2/`; nothing under `data/`, `runs/`, `leaderboard/` or the v1 site data is changed.
A new session can pick up from "Next step" at the bottom.

## Phases

- [x] 1. Audit → `AUDIT.md`
- [x] 2. Hard tier → `v2/data/hard.jsonl` (42 items, 7 families; `v2/build_hard.py`, examples in `v2/data/HARD.md`)
- [x] 3. Bad-inputs track → `v2/data/bad_inputs.jsonl` (30 corrupted + 30 clean twins + 10 odd-but-valid; `v2/build_bad.py`)
- [x] 4. Tool-use track: `v2/run.py --set hard --tools` (seven engine tools as function calls)
- [x] 5. Runs → `v2/runs/` (11 models, 2,772 graded replies; raw replies saved; `v2/run_all.sh` is the exact order)
- [x] 6. Analysis → `v2/results/` (`summary.json`, `RESULTS.md`, charts; `v2/grade.py`)
- [x] 7. `REPORT.md`, `site/v2.html` + `site/report.html` (`v2/build_site.py`), Vercel preview deployed and checked

## Spend

| What | Billed |
|---|---|
| Smoke tests (12 models × 11 bad-input notes; Mistral retest) | $0.26 |
| Hard tier, models alone | $1.98 |
| Hard tier with the engine (incl. the extra GPT-6.1 Sol and Terra run) | $0.70 |
| Bad inputs (incl. about $0.15 re-asking 14 fixed items) | $1.48 |
| Judge (Claude Haiku 5.5) + second judge (GPT-6 Luna) | $0.09 |
| **Total, runner's ledger** | **$4.51** |
| Total on OpenRouter's own meter for the key | $4.50 |

Done spending. $0.49 of the cap is unused.

**Cap: $5.00 total on OpenRouter**, judge included (owner's answer, 2026-11-14). The runner keeps a ledger in
`v2/runs/ledger.json` and refuses to start a request that could cross the cap passed to it (4.45 for the main runs, 4.75 for the last one).

## Decisions (owner's answers, 2026-11-14)

- Budget $5 "for the start". No Claude Opus. The judge runs through OpenRouter inside the cap.

## Decisions (mine, made while the owner was away)

1. **"v2" naming.** The repo already calls some v1 tasks "(v2)" and "(v3)". This project is "PlannerBench v2" and its
   files sit in `v2/` so the two can't be confused.
2. **$5 shapes everything.** Every model runs at reasoning effort `low` with a 4,000-token reply limit (v1 used
   `high` and 16–32k). Cheap models get 3 runs per item, mid-tier 2, frontier 1. The report says so.
3. **Tool track is sized by price.** Cheap models and Haiku get the engine on every hard item. One frontier model
   gets it on a small subset, because tool schemas are re-sent every turn and cost about 3 cents a question at $2/M.
4. **Tools offered:** the six single-year calculators and `run_scenario`. `plan_check` and `solve_roth_conversion`
   are left out (4.5k tokens of schema that no hard item needs).
5. **Bad-inputs prompt offers a way out.** Every prompt, clean or corrupted, ends with "ANSWER: <number>, or
   ANSWER: NEED_INFO if you can't responsibly give one". That makes two of the three scores rule-based, and clean
   twins measure the false-alarm rate. A model that says NEED_INFO to everything loses on the clean items.
6. **Hard-tier keys need two engines to agree.** Each key comes from the Planning Engine and must match the
   clean-room engine (`checks/cleanroom`, written from the rules alone) to the dollar, or the item is dropped.
7. **Outside-activity rule.** Nothing goes public from this work. The Vercel preview stays behind Vercel login.
   The employer's name appears nowhere.

8. **Lineup: 11 models** (`v2/lineup.json`): 3 frontier (Claude Sonnet 5.5, GPT-6.1 Sol, Gemini 3.1 Pro), 3 mid
   (GPT-6.1 Terra, Gemini 3.8 Flash, Claude Haiku 5.5), 5 cheap/open (DeepSeek V4.1 Flash, GLM 5.3 Flash,
   gpt-oss-120b, Llama 4 Maverick, Mistral Small). Each pinned to one host; OpenAI and Google models use the makers'
   half-price "flex" queue. Mistral Large 4 was dropped: it spent the whole reply limit thinking on 8 of 11 smoke
   questions and can't turn reasoning off. Mistral Small runs with reasoning off for the same reason.
9. **Runs per item, set by the budget:** bad inputs: frontier 1, mid 2, cheap 3. Hard tier: frontier 1, Terra and
   Haiku 2, Gemini Flash 1, cheap 2. Tools: cheap + Haiku 1 run on all 42; GPT-6.1 Sol on 7 (one per family).
10. **4,000-token reply limit kept for the hard tier** even though DeepSeek and Gemini Flash ran out of room on some
    smoke questions. Truncated is its own bucket, counted as not right, as in v1.
11. **14 bad-input items fixed after reading the first replies** (2026-11-14): the six `conflict` pairs never said the
    pension was fully taxable (GPT-6.1 Sol rightly asked), and `valid_odd-02` was not valid (a $185k earner's 401(k)
    catch-up must be Roth from 2026; Sol caught it). Replies to the old wording are kept in `v2/runs/bad/stale.jsonl`
    and not graded. Cost of the redo: about $0.15.
12. **Decline reasons are judged on clean notes too.** Gemini 3.1 Pro says NEED_INFO on clean tax notes because it
    doesn't know 2026 law, which is not the same as crying wolf about the client's data. The grader reports false
    alarms by reason and repeats the headline on the notes that need no 2026 tax law.

13. **Extra tools run with the leftover budget.** After the planned runs finished at about $3.90, GPT-6.1 Sol and
    Terra got the engine on all 42 hard questions (the plan had Sol on 7), so the "strong model gains nothing"
    result rests on full data. Sonnet and the Gemini models were not run with tools (too dear for what was left).
14. **Judge.** Claude Haiku 5.5 judges "named the problem" and "asked"; GPT-6 Luna re-judged every 4th reply
    (97.7% agreement, kappa 0.95). No human labels; the report says so.
15. **Site.** One new nav entry, "v2", on every page; the report page is linked from it. v1 pages are otherwise
    unchanged and `checks/site_check.py` passes against a local copy.
16. **Pushed and deployed (owner, 2026-11-14).** Branch `v2` is on `origin`; production serves it. Not merged into
    `master`.

## Assumptions

- The OpenRouter key in `.env` is the one to use (works; $50 limit on the key).
- IRMAA "two years out" uses the 2026 CMS table for 2028 premiums, stated in each prompt, as v1 does. 2028's real
  table isn't published.

## Blocked / skipped

- Mistral Large 4: dropped (burns the reply limit thinking, can't turn reasoning off).
- Sonnet 5.5, Gemini 3.1 Pro, Gemini 3.8 Flash with tools: skipped for cost.
- About 7 paid replies lost when the extra tools run crashed on a malformed reply (`KeyError: 'choices'`); the runner
  now records those as errors and the run was resumed to completion.
- Known judge miss: two GPT-6.1 Sol replies that asked to confirm an 1887 birth year were scored "declined for
  another reason". Left as scored; noted in the report's limits.

## Next step

All seven phases are done. For the owner:

1. Read `REPORT.md` (summary at the bottom), then the preview link at the top of this file.
2. Decide: push branch `v2` to the private repo; promote the preview; clear the outside-activity question before
   anything is public.
3. If there's more budget, the report's "What I'd do next" lists the runs in order (subtle errors first).
