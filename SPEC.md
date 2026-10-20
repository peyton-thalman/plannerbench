# PlannerBench: Spec

## What it does

PlannerBench measures how often frontier AI models get financial-planning math right, and how much a real planning engine improves them. The audience is two groups: wealthtech product teams deciding what to trust AI with, and AI labs building for financial services. A model's result is its accuracy by task, plus the specific mistakes it makes.

It also serves as Peyton's portfolio: proof that he can define "correct" for an AI product, measure it, and ship it, which is a PM's job at an AI company.

## The bar

| Goal | Measurable target |
|---|---|
| "Not blind faith" | No case ships unless five automated layers pass (see Trust). Peyton never hand-checks more than the 12-case audit pack. |
| "Dope" / credible | Wrong answers are reported by *category* (wrong bracket, missed senior deduction, wrong IRMAA cliff), not just as a score. A CFP reading the write-up nods. |
| Gets him recruited | A public leaderboard and write-up with at least one finding that isn't obvious, such as "the best model is 98% on brackets but 61% once Social Security is in the mix." |

## Evals in one paragraph

An eval is a set of questions with known correct answers, a way to ask a model each question, and a grader that compares the model's answer to the key. The hard part is not asking. It's being sure the **answer key** is right and the **questions** are fair. If the key is wrong, you're grading the model on your bug. Most of this project's engineering goes into that trust, which is also why it impresses AI companies.

## Trust: why this isn't blind faith

`python3 -I checks/trust.py` runs all five layers and writes [TRUST.md](TRUST.md). The rule is simple: if any layer fails, nothing ships.

1. **Golden set.** 16 cases whose answers come straight from IRS, SSA and CMS tables, such as "born 1960, claims at 62 → 70% of PIA." This anchors everything to the government's own numbers.
2. **Two-way check.** Two programs written separately compute every answer: the TypeScript engine and a Python re-implementation built from the rules. Two independent programs rarely make the *same* mistake, so agreement on all 1,200 cases is strong evidence. This check already caught a real IRMAA bug that the engine's own tests missed.
3. **Invariants.** Rules that must hold for any household, tested on 4,000 random ones: more income never lowers tax, waiting a month never lowers a Social Security benefit, taxable SS never exceeds 85%, and so on. These catch bugs without needing any answers.
4. **Dataset health.** No duplicate questions, and no task where one answer dominates (so a model can't score by guessing). This check already caught 50 duplicates.
5. **Human audit pack.** [checks/AUDIT.md](checks/AUDIT.md) holds 12 random cases with worked solutions. You, or a CPA friend, can check each in about 2 minutes with a calculator.

**Layer 6 (once models run): disagreement review.** If three frontier models all give the *same* answer and it differs from the key, that case goes to a review queue. Either the key has a bug or the question is ambiguous. The models become free auditors.

**Fairness review.** Before launch, a model is asked "is this question ambiguous or missing information?" for each template. One wording issue has already been fixed: "IRA distributions and taxable interest" left it unclear whether interest counted toward NIIT.

## Scope

**In (v1):** six numeric tasks on 2026 federal rules: full federal tax, Pub 915, RMDs, SS claiming, Roth bracket room, IRMAA. That's 1,200 public cases plus a private held-out set made by regenerating with a secret seed. A model that memorized the public set still faces new questions, which is the standard defense against *contamination*.

**In (v2): multi-step tasks, where models should fail interestingly.**
- The "tax torpedo": a Roth conversion that also makes more Social Security taxable.
- The widow's penalty: the switch to single brackets after the first spouse dies.
- The IRMAA two-year lookback.
- Social Security breakeven ages.
- Whether a Roth conversion beats leaving the money, using the full engine.

**Out:** state tax (the engine simplifies it), judgment and advice quality (needs rubric grading; a later project), and anything involving real client data.

## Milestones

| # | Milestone | Done when | Needs |
|---|---|---|---|
| M0 | Generator + answer key | 1,200 cases, two-way check passes | Done 2026-10-20 |
| M1 | Trust report | All 5 layers pass, AUDIT.md exists | Done 2026-10-20 |
| M2 | Model runner + grader | Runner, grader, parser tests and an offline fake run are built (2026-10-20). Next: Claude pilot on 60 cases, then all 1,200 run 3× each | ANTHROPIC_API_KEY; about $1–3 for the pilot |
| M3 | Error taxonomy | Every wrong answer tagged with a mistake type, and the top 5 types named | M2 |
| M4 | Tools vs. no tools | Engine exposed as an MCP server; the chart "Claude alone vs. Claude + planning tools" | M2 |
| M5 | v2 multi-step tasks | 5 new task types, each through all trust layers. 2/5 done 2026-10-20 (tax torpedo, widow's penalty; 1,600/1,600 two-way). Left: IRMAA lookback, SS breakeven, convert-or-not | M1 |
| M6 | Leaderboard + write-up | Public page and post, sent to Jump, Altruist and the labs' FS teams | Peyton approves before anything is published |
| Moonshot | Living benchmark | A scheduled job reruns new models as they ship and updates the leaderboard; law-year rollover each January | Scheduled task + keys |

## How it makes MoneyGuide better

- **Regression net.** 1,200 cases plus invariants now check the engine on every change. They already caught one bug, and that bug is now a permanent test in MoneyGuide.
- **AI-native MoneyGuide.** M4 turns the engine into tools Claude can call. That makes MoneyGuide something an advisor can *talk to*, with answers backed by tested math instead of model guesses. M4's chart is the proof that this matters.
- **Product roadmap from the data.** The mistakes models make most often show what advisors' AI will get wrong, which tells you what to build into MoneyGuide.

## Crew methods applied

- **Eval scientist:** held-out set, repeated runs to measure variance, and grading that tracks answers in the wrong format separately from wrong math.
- **CPA:** worked solutions and wording that matches the actual worksheets.
- **Adversarial question critic:** ambiguity review and dataset-health checks.
- **Short seller of the benchmark:** "numbers-only tasks are narrow." The answer is the v2 multi-step tasks and naming the limits in the write-up.
