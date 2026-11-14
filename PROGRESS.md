# PlannerBench v2: progress

**Preview link:** not deployed yet (phase 7)

Branch `v2`. Everything for v2 lives in `v2/`; nothing under `data/`, `runs/`, `leaderboard/` or the v1 site data is changed.
A new session can pick up from "Next step" at the bottom.

## Phases

- [ ] 1. Audit → `AUDIT.md`
- [ ] 2. Hard tier → `v2/data/hard.jsonl`
- [ ] 3. Bad-inputs track → `v2/data/bad_inputs.jsonl`
- [ ] 4. Tool-use track (same hard items, engine offered as tools)
- [ ] 5. Runs → `v2/runs/`
- [ ] 6. Analysis → `v2/results/`
- [ ] 7. `REPORT.md`, site pages, Vercel preview

## Spend

| What | Billed |
|---|---|
| (nothing yet) | $0.00 |

**Cap: $5.00 total on OpenRouter**, judge included (owner's answer, 2026-11-14). The runner keeps a ledger in
`v2/runs/ledger.json` and refuses to start a request that could cross $4.80.

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

## Assumptions

- The OpenRouter key in `.env` is the one to use (works; $50 limit on the key).
- IRMAA "two years out" uses the 2026 CMS table for 2028 premiums, stated in each prompt, as v1 does. 2028's real
  table isn't published.

## Blocked / skipped

(nothing yet)

## Next step

Write `AUDIT.md` from the v1 graded runs.
