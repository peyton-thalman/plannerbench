# Clean-room engine: notes on RULES.md

Written while building `engine.py` / `params.py` from `spec/RULES.md`, `CONTRACT.md` and `spec/law/*.json` only.
Each item says what was unclear, what this engine does, and where it might differ from another faithful reading.
Section numbers refer to RULES.md.

## A. Places RULES.md (or the contract) is incomplete, and how this engine fills the gap

1. **Input field names (1, CONTRACT).** RULES.md says the input format is "the one given in the brief", which is not
   in this folder. Field names were inferred from the text: people `id, born, born_month, medicare,
   social_security{monthly_at_fra, claim_age, already_claimed_monthly, claimed_at_months}`; accounts
   `id, owner, type, balance, after_tax_basis, first_roth_year, contribution_basis, conversion_layers, cost_basis,
   dividend_yield, qualified_share, inherited{from_born, died, owner_had_reached_rbd, beneficiary_class}`; income
   items `type, owner, annual, start_year, end_year, cola`. Defaults where RULES.md gives none: `born_month` 1,
   `medicare` false, `cost_basis` = balance, `dividend_yield` 0, `qualified_share` 1.0, `cola` 0, open-ended
   `start_year`/`end_year`, `claim_age` = full retirement age.
2. **Which keys appear in the per-account output maps (CONTRACT).** The contract example is one account per map.
   This engine uses: `rmd` = every traditional_ira, 401k, inherited_ira, inherited_roth_ira; `qcd` = traditional_ira
   and inherited_ira; `conversion` = traditional_ira and 401k; `distributions` and `balances` = every account
   (taxable sales and cash withdrawals count as "gross dollars out"); `sales` = taxable accounts. A comparator should
   treat a missing key as 0 or the two engines must agree on this list.
3. **Which people appear in per-person maps.** `alive` lists everyone; `age`, `social_security`, `basis8606` list
   people alive that year; `medicare` lists living people with Medicare months that year.
4. **What `rmd` reports.** The required amount for the account (`B0/divisor`, capped at the grown balance, plus any
   deferred first-year RMD), not the cash taken from that account after the QCD offset and the pro-rata IRA
   aggregation of 6.3.
5. **What the `income` block's fields mean.** `interest_taxable` = Form 1040 line 2b (input items plus cash-account
   interest). `pension` and `annuity_taxable` = the input items only. `ira_taxable` = line 4b plus the 401(k)
   distributions and 401(k) conversions that 9.1 puts on line 5b, so the block sums to AGI minus taxable Social
   Security. `capital_gain` = line 7 (after the carryover and the $3,000 limit).
6. **`basis8606` timing.** Reported as the person's own Form 8606 line 14 for that year, before the death transfer
   of 3.3 step 1 moves it to the survivor.
7. **Names of created accounts.** A conversion by someone with no Roth IRA creates `roth_ira_<person id>`; a surplus
   in a household with no cash account creates `cash` (owner `joint`, or the single person). RULES.md does not name
   them.
8. **Surplus after the bisection.** 8.3 says surplus is deposited when `net(0) ≥ 0`; after bisection `net(hi)` is a
   fraction of a cent. It is deposited too (step g), except that no new cash account is created for less than $0.01.
9. **Roth `first_roth_year` missing.** RULES.md treats it as a required input. If absent, this engine treats the
   five-year period as already met (`first_year − 5`); a Roth created by a conversion uses the conversion year.
10. **(Superseded by v1.2, see A3 item 33.) `already_claimed_monthly` ≥ `monthly_at_fra` (1.1, 5.5).** The default says "assume no early reduction". The
    engine uses factor = 1 (no delayed credits carried into the survivor base) because the excess could be a spousal
    top-up (5.4 says it is included). The other reading (factor = ratio) gives a larger survivor base.
11. **Spousal benefit when the worker had already claimed.** The worker's entitlement month is taken from
    `claimed_at_months` if given, else treated as before `first_year`; the spousal start is then the claimant's own
    entitlement month.
12. **Delayed retirement credit rate.** 2/3% per month is applied to every birth cohort (A.3 lists it "born 1943+";
    earlier cohorts are not modelled).
13. **Projected-parameter labels (14, CONTRACT `projected`).** The flag is true when any parameter *read* that year
    was projected. Consequences: (a) every year from 2027 is projected (the 2027 Rev. Proc. is unpublished); (b)
    **2026 is projected for every Arizona household**, because `az_standard_deduction` for 2026 is unpublished
    (v1.2: it equals the federal basic amount but is still labelled projected); (c) the 2027 SALT amounts (statutory
    101% schedule) and the 2027 COLA of 3.6% (ssa.gov, Federal Register notice pending) are treated as published.
14. **Part B tier amounts when projected (12.5 vs 14.1).** 12.5 says "keep the last published ratio of each tier's
    premium to the standard premium, then round to $0.10"; it does not say whether the ratio multiplies the rounded
    or unrounded standard premium. 14.1 ("do not compound the rounded values") suggests unrounded; this engine uses
    ratio × unrounded standard, then rounds. The other choice moves a premium by up to $0.10/month (≤ $1.20/year per
    person, which can exceed the $1.00 tolerance).
15. **IRMAA joint top threshold when indexed (2028+).** 12.3/14.2 give "MFJ lower bounds = 2 × single; the top bound
    is separate" but not how the joint top is indexed. This engine indexes $750,000 on its own chain (nearest $1,000,
    halves up). 1.5 × the rounded single top can differ by $500.
16. **Part D base premium (`part_d_base_monthly`).** Kept constant; RULES.md gives it no growth rule.
17. **Itemized inputs after a death.** `survivor_spending_ratio` scales `need` only; the itemized inputs keep
    inflating unscaled (1.4 says they are paid out of spending but gives no survivor rule).
18. **First-RMD deferral and death.** With `defer_first_rmd = true`, an owner who dies in the first RMD year takes
    that RMD in the year of death (6.4 says the decedent's RMD is taken in `Y`).
19. **Uniform Lifetime Table below age 72.** The 2022 table starts at 72; an owner below 72 can only owe an RMD in the
    pre-July-1949 70½ cohort, in years before `first_year`. The 72 row is used if ever reached.
20. **Joint and Last Survivor table.** Not in the law JSON (other.json says "not extracted"). Downloaded from eCFR
    (§1.401(a)(9)-9(d), Table 3) and parsed programmatically; spot values 75/60 = 28.3, 80/65 = 23.8. "More than 10
    years younger" is tested on ages attained in `Y` (birth months ignored).
21. **(Superseded by v1.2, see A3 item 30.) 6A.6 successor deadline.** The spec's "Implement" line, `deadline = min(existing, D_b + 10)` with ∞ for every
    life-expectancy schedule, is applied to every inherited account the deceased held, including a
    `non_designated` owner-life-expectancy schedule and a `spouse` class that had not started RMDs. See B.1.
22. **Waiver years (6A.5).** Applied only to `designated` beneficiaries whose owner died on/after the RBD in
    2020–2023. other.json also lists beneficiaries of EDBs who died 2020–2023; that case is not modelled.
23. **Flags vocabulary.** The contract gives none. This engine emits `action_clamped`, `action_void` (missing
    account), `qcd_void` (not an IRA, or holder under 70½), `irmaa_lookback_assumed`, `charitable_excess`. Flag lists
    will rarely match another engine string for string.
24. **Arizona 2025 SALT in Arizona itemized.** A.R.S. §43-1042(D) applies only from 2026, so 2025 uses the full
    federal SALT deduction (including the Arizona tax, solved as the 10.3 fixed point).
25. **Arizona §68.** Applied from 2026 only (the federal §68 rewrite starts 2026), using the federal
    `AGI − senior_deduction − bracket37_start` quantity (10.2 reading).
26. **`heirs_credit_8606_basis = true`.** 15.3 says heirs' tax applies to `balance − basis8606`; the engine applies it
    to total pre-tax balances minus total remaining basis (capped at the pre-tax total).
27. **Spending pools (8.2).** "Balances after steps a–e" are taken to include a Roth's same-year conversion inflow,
    so the Roth pool can pay out converted dollars in the same year.

## A2. Changes for RULES.md v1.1 (2026-10-21)

28. **Same-year conversions in Roth ordering (7.5 v1.1).** I checked this against the regulation (eCFR, Reg.
    §1.408A-6 Q&A-9, read 2026-10-21) and agree. Q&A-9(a) aggregates "all distributions from all an individual's Roth
    IRAs made during a taxable year", and 9(c) aggregates "all conversion contributions received during the same
    taxable year". So the Q&A-8 ordering is applied once at year end, to the year's total, with that year's
    conversions already in the basis. v1 of this engine ordered a step-c plan withdrawal before the step-d
    conversion layer existed, so it taxed same-year withdrawals as earnings whenever the five-year period was
    unmet. Now every `roth_ira` withdrawal (plan or spending) is ordered at year end, after the layer for `Y` is
    added. Inherited Roth IRAs are unchanged, since no conversion can go into them. Test:
    `RothOrdering.test_same_year_conversion_counts`.
29. **SALT phase-down threshold 2027–2029 (federal.json corrected).** No change was needed. `params.py` never read
    the JSON's 2027 figure; it computes `505,000 × 1.01^(Y−2026)` from the statute, giving 510,050 / 515,150.50 /
    520,302.005, which matches the corrected table. Test: `SaltThresholdSchedule`.

## A3. Changes for RULES.md v1.2 (2026-10-21), resolving B.1, B.2, B.3 and B.5

30. **Successor deadline (6A.6, resolves B.1).** `inherited_setup` now records whether the first beneficiary was an
    EDB on a life-expectancy schedule (an EDB that elected the 10-year rule is not). Only then does a holder's death
    set `deadline = min(existing, D_b + 10)`. A `designated` successor keeps `D + 10`; a `non_designated`
    owner-life-expectancy schedule keeps no limit. Test: `SuccessorAndStepUpV12.test_successor_deadlines`.
31. **Joint-account step-up by titling (3.3 step 5, resolves B.2).** The new optional account input `titling`
    (`community` / `community_with_survivorship` → full step-up; `jtwros` → half) is validated on input. If it is
    absent, the account gets half, or full when the switch `community_property` (now default `false`) is on.
    `stepup_titling_assumed` is flagged in the death year's row whenever `titling` is absent, including when the
    switch decides it, because the titling question is still open. **Inconsistency in v1.2:** Appendix B still
    lists `community_property` as "true if AZ"; I followed the amended 3.3 text (`false`). Test:
    `SuccessorAndStepUpV12.test_joint_titling`, `test_switch_default_false_in_az`.
32. **Arizona standard deduction (10.2, resolves B.3).** `az_standard_deduction[Y]` = the federal basic
    `standard_deduction[Y]` (2026: 32,200 / 16,100), and every year from 2026 is labelled projected. So `projected`
    stays true for 2026 in Arizona households (A.13). Test: `ArizonaStandardDeductionV12`.
33. **Survivor base (5.5, resolves B.5 / A.10).** An already-claimed worker with no `claimed_at_months` now has
    factor = `already_claimed_monthly / monthly_at_fra` with no cap at 1 (1 if `monthly_at_fra` is 0). The same factor
    drives the RIB-LIM test (factor < 1). A worker who dies unclaimed earns credits through November of `D`. Tests:
    `Example8Survivor.test_v12_already_claimed_ratio_keeps_drcs`,
    `test_v12_unclaimed_death_credits_through_november`.

## B. Places I believe RULES.md may be wrong about the law (followed anyway)

Status after v1.2: items 1, 2, 3 and 5 were adopted into the spec (see A3); item 4 is still open.

1. **Successor deadline for non-EDB schedules (6A.6).** IRC §401(a)(9)(H)(iii) imposes the 10-year limit on the death
   of an *eligible designated* beneficiary. Applying `D_b + 10` to a non-designated beneficiary on the owner's
   remaining life expectancy (6A.4 last row) goes beyond the statute; Reg. §1.401(a)(9)-5(d) generally lets the
   successor continue the owner's schedule. Low impact in practice; worth checking against the final regs.
2. **Community-property step-up for every "joint" account in Arizona (3.3 step 5, switch default).** IRC §1014(b)(6)
   steps up both halves only of property that *is* community property under state law (A.R.S. §25-211). A joint
   tenancy with right of survivorship titled account is not automatically community property, so a full step-up is
   a convention, not the law's default. The switch exists; the default may overstate the step-up.
3. **Arizona 2026 standard deduction (10.2, 14.2).** Section 14 projects it from the 2025 seed ($31,500 × 1.025 →
   $32,250 at the default 2.5% inflation). The likely ADOR figure tracks the federal basic amount ($32,200 MFJ /
   $16,100 single; other.json flags, A.R.S. §43-1041(H) "in the same manner in which the federal basic standard
   deduction is adjusted"). A literal reading of (H) as indexing from 2019 would give a much larger number. Until ADOR
   publishes the 2026 Form 140, all three are defensible; the spec's projection is the least likely to be exact.
4. **Arizona income tax inside Arizona itemized taxes (10.2 reading).** The spec keeps the Arizona income tax inside
   the Arizona SALT amount because §43-1042(D) says "that amount". I could not confirm from the statute text alone
   whether ADOR's Schedule A instructions remove Arizona income tax from the Arizona itemized deduction; worth
   checking the 2026 Form 140 Schedule A instructions when published (azdor.gov). Not changed.
5. **Survivor base for a worker who had already claimed with no `claimed_at_months` (5.5 with 1.1 default).** See
   A.10. Social Security pays a widow(er) the deceased's PIA plus delayed credits actually earned
   (20 CFR 404.313(e)); the default discards DRCs whenever `already_claimed_monthly ≥ monthly_at_fra`.

No disagreements were found with the law tables' numbers. The SALT 2027–2029 figures in federal.json are derived
(×1.01, unrounded); RULES 14.2 uses the same rule.

## C. Not implemented

- Section 17 explain trace (driver substitution and rule attribution). Not part of the CONTRACT output.
- 15.1 detail beyond the contract fields: per-person Form 8606 lines, QDCG worksheet lines, Arizona lines 12–46,
  `magi_aca` and the other MAGI definitions, parameter labels by name, SSA-44 alternative premiums (12.2). They are
  computed internally (8606, QDCG, AZ) but not printed, because the contract fixes the output shape.
- Switch `use_tax_table` (accepted, ignored; exact-dollar computation always). Switch `az_assume_future_conformity
  = false` changes nothing (there is no alternative Arizona law to apply).
- Everything in Appendix D.
