# PlannerBench trust report

**All checks pass** on 2,800 cases.

| Layer | Result | Detail |
|---|---|---|
| Golden set (published answers) | PASS | 16/16 match IRS/SSA/CMS |
| Two-way check (engine vs. independent) | PASS | 2800/2800 agree |
| Invariants | PASS | 4,000 random households x 9 rules, 0 violations |
| Dataset health | PASS | 2800 unique prompts, no task dominated by one answer |
| Human audit pack | PASS | 12 random cases with worked solutions written to checks/AUDIT.md |
