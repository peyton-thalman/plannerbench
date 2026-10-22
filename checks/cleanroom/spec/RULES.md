# RULES.md — US retirement tax rules for a year-by-year calculator

Version 1.2, 2026-10-21 (v1.1: same-year conversions in Roth ordering, 7.5; SALT threshold arithmetic. v1.2, from a primary-source review of five questions: successor deadline only after an EDB, 6A.6; joint-account step-up by titling, 3.3; Arizona standard deduction follows the federal amount, 10.2; survivor base keeps delayed credits, 5.5). Law as enacted through that date, including P.L. 119-21 ("OBBBA", July 4, 2025)
and Arizona Laws 2026, ch. 140 (HB 4168, approved June 13, 2026).

This is a specification, not code. A programmer should be able to build a calculator from it alone. Every rule
names its legal source. **No dollar amounts or rates appear in the rules.** Rules refer to named parameters
(`like_this[year][filing]`); Appendix A lists every parameter, its meaning, and the document that supplies its
values. A separate parameter table supplies the numbers per year. The worked examples (Section 16) are the only
place numbers appear, and each example states the values it assumes.

Words used with a fixed meaning:

- **MUST** — required for two engines to agree.
- **Convention** — a modelling choice the law does not make for us (for example, the order of transactions within
  a year). Conventions are chosen once here and both engines follow them.
- **Reading** — where the law is unclear or recently changed, the interpretation this spec adopts, with the reason.
  Every reading is collected in Appendix C.
- **Switch** — a named boolean or enum in `assumptions.switches` that turns a reading or convention on or off.
  The default is the one stated. Appendix B lists them all.

---

## 0. Scope, notation, arithmetic

### 0.1 Scope

- Filing statuses: married filing jointly (`mfj`) and single (`single`). Includes the year of a death (joint return)
  and the years after it (survivor files single). Head of household, married filing separately and qualifying
  surviving spouse are out of scope (see 3.3).
- Federal income tax, net investment income tax, the 10% additional tax on early distributions, Arizona income tax
  (or no state tax), Medicare Part B premiums and Part D income-related amounts.
- Deterministic: one nominal return `assumptions.return` for every account and year, one inflation rate
  `assumptions.inflation` for projecting indexed amounts.
- Out of scope (Appendix D): AMT, payroll taxes, credits, the Social Security earnings test, ACA premium credits,
  state taxes other than Arizona, estate tax, and others listed there.

### 0.2 Notation

- `Y` is the calendar year being computed; `first_year ≤ Y ≤ last_year`.
- `filing` is the filing status of the return for year `Y` (Section 3).
- `P` ranges over people; `A` over accounts.
- `B0[A]` = balance of account `A` on Dec 31 of `Y−1` ("opening balance"). For `Y = first_year` this is the input
  `balance`.
- `max0(x)` = `max(0, x)`.
- `floor_to(x, u)` = largest multiple of `u` that is ≤ `x`. `round_to(x, u)` = nearest multiple of `u`, halves
  rounded up.

### 0.3 Arithmetic (MUST)

- Compute in double-precision floating point on dollars. **Do not round intermediate tax amounts to whole dollars**
  (the IRS forms allow whole-dollar rounding and the tax tables use $50-wide rows; this spec computes exact
  amounts; see switch `use_tax_table`, default `false`).
- The only rounding inside the computation is where a rule below says so: Social Security benefit rounding (5.6),
  Medicare premium rounding (12.5), and projected-parameter rounding (14).
- Report outputs rounded to cents. Two engines agree if every reported dollar figure matches within $1.00 per year.

---

## 1. Inputs

The input format is the one given in the brief. This section fixes meanings that the brief leaves open, and adds a
few optional fields (marked **added**) without which some rules cannot be applied. An engine MUST accept inputs that
omit the added fields and use the stated defaults.

### 1.1 Household and people

- `household.filing`: `"mfj"` or `"single"`. If `"mfj"`, `people` has exactly two entries; if `"single"`, one.
- `household.state`: `"AZ"` or `"none"`.
- `people[].born` (year), `born_month` (1–12, default 1). No day of birth is given. **Convention:** every person
  is treated as born on the 15th of `born_month`. This removes the "born on the 1st of the month" special cases in
  Social Security (20 CFR 404.2(c)(4), POMS RS 00615.003) and the "day before your 65th birthday" rule (IRS,
  Form 1040 instructions, "Age"). Those edge cases are out of scope.
- `people[].medicare` (bool): `true` means the person is (or will be, from the month they turn 65) enrolled in
  Medicare Part B and a Part D plan. `false` means no Medicare premiums are ever computed for them.
- `people[].social_security`:
  - `monthly_at_fra`: the primary insurance amount (PIA), in dollars of `first_year` (i.e., including all COLAs
    effective for January of `first_year`). **Convention:** it is increased by the projected COLA each later year
    whether or not the person has reached 62 (the real law wage-indexes before 62; out of scope).
  - `claim_age`: years, may be fractional. Converted to whole months: `claim_months = round(12 × claim_age)`.
  - `already_claimed_monthly` (optional): the monthly benefit actually payable for January of `first_year`
    (before any Medicare premium deduction). If present, the person is already entitled; `claim_age` is ignored
    for the person's own benefit and the rules in 5.3–5.5 use this amount.
  - **added** `claimed_at_months` (optional, only with `already_claimed_monthly`): the age in months at which the
    person became entitled. Needed only for the survivor limit in 5.5. Default: if
    `already_claimed_monthly < monthly_at_fra` assume the person claimed early with the reduction implied by the
    ratio; if `≥`, assume no early reduction.
- **added** `household.prior_magi` (optional): `{year: {magi, filing}}` for `first_year−2` and `first_year−1`.
  Used only for Medicare premiums in the first two plan years (12.2). Default: absent, in which case those years
  use the lowest tier and the output flags `irmaa_lookback_assumed = true`.
- **added** `household.prior_capital_loss_carryover` (optional, default 0).

### 1.2 Accounts

- `owner`: a person id, or `"joint"`. Only `taxable` and `cash` accounts may be `"joint"`. A joint account in a
  single household is treated as owned by the one person.
- `type`:
  - `traditional_ira` — a traditional IRA (SEP and SIMPLE IRAs, if present, are entered as `traditional_ira`).
  - `401k` — any employer plan pre-tax account (401(k), 403(b), governmental 457(b)). Treated as fully pre-tax
    (no after-tax basis inside the plan).
  - `roth_ira`, `inherited_ira`, `inherited_roth_ira`, `taxable`, `cash`.
- `after_tax_basis` (traditional_ira only): the owner's Form 8606 line 14 from the year before `first_year`.
  **Reading:** basis belongs to the person, not to an account (Form 8606 aggregates all of a person's traditional
  IRAs, Instructions for Form 8606, "Line 6"). The engine sums `after_tax_basis` over the person's
  `traditional_ira` accounts into one per-person figure `basis8606[P]`.
- `first_roth_year` (roth_ira, inherited_roth_ira): the first tax year for which any contribution or conversion was
  made to any Roth IRA of that owner (for inherited Roth: of the original owner). IRC §408A(d)(2)(B).
  Per person, the earliest across their Roth IRAs is used.
- **added** `contribution_basis` (roth_ira, optional, default 0): the owner's total regular Roth contributions not
  yet withdrawn. **added** `conversion_layers` (roth_ira, optional, default empty): list of
  `{year, taxable_amount, nontaxable_amount}` for conversions made in the five years before `first_year`.
  Without them, Roth ordering (7.5) treats the whole opening balance as earnings, which only matters for owners
  under 59½ or whose 5-year period is not met.
- `cost_basis`, `dividend_yield`, `qualified_share` (taxable). `dividend_yield` is a fraction of the opening
  balance paid as dividends each year; `qualified_share` is the fraction of dividends that are qualified dividends
  (IRC §1(h)(11)). **Convention:** all realized gains are long-term (all positions held more than one year).
- `inherited` (inherited_ira, inherited_roth_ira): `from_born` (original owner's birth year), `died` (year),
  `owner_had_reached_rbd` (optional; derived in 6.2 if absent), `beneficiary_class`. For `minor_child` the account
  owner's own `born` gives the child's age. A `designated` beneficiary is a designated beneficiary who is not an
  eligible designated beneficiary; `non_designated` covers an estate, charity or non-see-through trust as
  "beneficiary" (the household member is then treated as holding the account through it).

### 1.3 Income items

- `annual` is the amount for the year `max(start_year, first_year)`; each later year it is multiplied by
  `(1 + cola)`. Paid in years `start_year ≤ Y ≤ end_year`. `cola` may be 0.
- `pension`: fully taxable pension or annuity from a qualified plan (Form 1040 line 5b).
  `annuity_taxable`: the taxable part of a **nonqualified** annuity payment (Form 1040 line 5b; it is net
  investment income, see 9.13). `wages`: line 1a. `interest_taxable`: line 2b. `interest_tax_exempt`: line 2a.
  `rental`: net rental income after expenses and depreciation, Schedule E → Schedule 1 line 5; MUST be ≥ 0
  (passive losses are out of scope).
- An income item whose `owner` dies stops after the year of death, except `rental` and interest items, which
  continue (the survivor inherits the property). **Convention**; pensions with survivor options are out of scope.

### 1.4 Spending and itemized inputs

- `spending_need`: after-tax spending in `first_year` dollars; spending in year `Y` is
  `need[Y] = spending_need × (1+inflation)^(Y − first_year)`. Spending excludes federal tax, state tax and Medicare
  premiums, which are computed and paid separately (8.1).
- Itemized inputs (`salt_other` = state and local taxes other than income tax, e.g. property tax;
  `mortgage_interest`; `medical`; `charity_cash` = cash gifts to public charities, not to donor-advised funds) are
  in `first_year` dollars and inflate the same way. They are assumed to be paid out of `spending_need` (they are
  not extra outflows).
- After a death, `spending_need` continues unchanged unless the input gives `assumptions.survivor_spending_ratio`
  (**added**, default 1.0), which multiplies `need[Y]` for years after the first death.

### 1.5 Plans and events

- `roth_conversion {from, amount, years}`: convert `amount` (gross) from account `from` to the owner's Roth IRA in
  each listed year. `from` must be `traditional_ira` or `401k`. A conversion from an `inherited_ira` is not
  permitted (IRC §408(d)(3)(C); §402(c)(11)) and MUST be rejected as an input error.
- `qcd {from, amount, years}`: qualified charitable distribution from IRA `from` (7.2).
- `withdrawal {from, amount, years}`: an extra gross withdrawal from any account; the cash goes into the year's
  cash flow (8.1).
- `harvest_gains {amount, years}`: realize `amount` **of gain** (not proceeds) by selling and immediately
  rebuying in the household's taxable accounts (7.6).
- `claim_social_security {person, age}`: overrides `claim_age` for that person in that plan.
- `death {person, year}`: applies to all plans.
- If a requested amount exceeds what is available, it is reduced to what is available and the output records the
  shortfall (`action_clamped`).

### 1.6 Assumptions

`return`, `inflation`, `first_year`, `last_year`, `heirs_tax_rate`, plus **added** `chained_cpi_gap` (default 0;
projected chained-CPI growth = `inflation − chained_cpi_gap`), `medicare_growth` (default = `inflation`; growth of
Part B and Part D amounts), `cola` (default = `inflation`; projected Social Security COLA), `switches`
(Appendix B).

---

## 2. The year at a glance (ordered procedure)

**Timing convention (MUST).** Each account grows for the whole year on its opening balance, and **all
distributions, conversions, sales, deposits and transfers happen on December 31**, after growth, in the order
below. Income items, Social Security and Medicare premiums accrue during the year. Taxes for year `Y` are treated
as paid in year `Y`.

Why this convention: (1) RMDs are defined on the prior Dec 31 balance (§1.401(a)(9)-5(b)), so they are known before
anything else happens; (2) investment income (dividends, cash interest) depends only on opening balances, so it is
known before the spending solve and nothing is circular except tax-versus-withdrawal (solved in 8.3); (3) Form 8606
line 6 asks for the Dec 31 value, which is then exactly the post-transaction balance; (4) age tests "has the person
reached 59½ / 70½ by the time of the distribution" become "by Dec 31 of `Y`", with no partial-year guessing.

For each plan, for each year `Y` from `first_year` to `last_year` (stop after the year in which the last living
person dies; Section 13):

1. **Status** — ages, 59½/70½/65 tests, Medicare months, who is alive (Section 3.1).
2. **Filing status** for `Y` (Section 3.2).
3. **Social Security** benefits for `Y` (Section 5).
4. **RMDs** for `Y`, from opening balances (Sections 6 and 6A).
5. **Growth and investment income**: every balance becomes `B0 × (1 + return)`; dividends and cash interest are
   determined (Section 4).
6. **December 31 transactions**, in this order (Section 7):
   a. QCDs; b. remaining RMDs; c. plan `withdrawal` actions; d. Roth conversions; e. gain harvesting;
   f. spending withdrawals (solved together with tax, Section 8); g. deposit of any surplus to cash.
7. **Federal tax** (Section 9), **Arizona tax** (Section 10), **Medicare premiums** (Section 12) — 9 and 10 are
   evaluated inside the spending solve of step 6f.
8. **Closing balances**, basis carryforwards (Form 8606 line 14, Roth ledger, taxable cost basis, capital loss
   carryover) (Section 11).
9. **Death transitions** for anyone who died in `Y` (Section 3.3).
10. **Outputs and trace** (Sections 15, 17).

---

## 3. Status, filing status and deaths

### 3.1 Ages and tests for year `Y`

- `age[P] = Y − born[P]`: the age attained on the birthday in `Y`, which is also the age on Dec 31 of `Y`.
- **59½ test:** the person reaches 59½ in the month `born_month + 6` of year `born + 59` (if `born_month ≤ 6`)
  or month `born_month − 6` of year `born + 60` (if `born_month ≥ 7`). `over_59h[P][Y] = true` if that date is
  on or before Dec 31 of `Y`. Source: IRC §72(t)(2)(A)(i) ("on or after the date on which the employee attains
  age 59½"). With Dec 31 transactions (Section 2) any distribution in the year of reaching 59½ is after the date.
- **70½ test** (QCDs): same construction with 70; `over_70h[P][Y]`. Source: IRC §408(d)(8)(B)(ii).
- **65 test:** `is65[P][Y] = (age[P] ≥ 65)`. Source: IRC §63(f)(1)(A) ("attained age 65 before the close of his
  taxable year"); §151(d)(5)(C) uses the same test for the senior deduction (Schedule 1-A Part V).
- **Medicare months:** if `medicare[P]`: `medicare_months[P][Y] = 12` if `age[P] > 65`; `= 13 − born_month` if
  `age[P] = 65` (coverage starts the first day of the birthday month, 42 CFR 406.21 / 407.25 initial enrollment);
  `= 0` if `age[P] < 65`. Disability Medicare before 65 is out of scope.
- **Alive:** a person is alive in `Y` if they have no death event with `year < Y`. **Convention:** a person who
  dies in `Y` is treated as alive for all of `Y` — their income, Social Security, RMD, Medicare premiums and plan
  actions for `Y` all happen — and the death takes effect on Dec 31 of `Y` after step 6. (Real deaths happen
  mid-year; a year-granular model cannot place them, and this choice keeps the year-of-death return complete.)

### 3.2 Filing status for year `Y`

- `household.filing = single`: `single` every year.
- `household.filing = mfj`:
  - both alive in `Y` (including a death in `Y`): `mfj`. Source: IRC §6013(a)(2) (a joint return may be filed for
    the year a spouse dies); IRC §7703(a)(1) (marital status is determined at the close of the year, or at death).
  - years after the first death: `single`.
  - **Qualifying surviving spouse** (IRC §2(a)) requires a dependent child living with the survivor. The inputs
    have no dependents, so it never applies; out of scope. Head of household likewise.

### 3.3 Death transitions (applied at the end of year `D`, the year of death)

Let `d` be the person who died and `s` the survivor (if `mfj` and the other person is alive).

**If there is a survivor `s` (spouse):**

1. **Traditional IRAs of `d`** become `s`'s own traditional IRAs (spousal election to treat as own / rollover,
   IRC §408(d)(3)(C)(ii) excludes a spouse from the inherited-IRA rule; Treas. Reg. §1.408-8(c); Pub 590-B,
   "Inherited from spouse"). The account keeps its id; `owner` becomes `s`. `basis8606[s] += basis8606[d]`
   (Instructions for Form 8606: basis of an IRA treated as your own carries to your Form 8606). **Convention** —
   the election is made at once; staying a beneficiary is out of scope for the transition (but pre-existing
   inherited IRAs with `beneficiary_class: spouse` are supported, Section 6A).
2. **401(k) of `d`**: switch `spouse_401k_to_ira` (default `true`): rolled into a traditional IRA owned by `s`
   (type becomes `traditional_ira`; it then enters `s`'s Form 8606 line 6). If `false`, it stays a `401k` owned by
   `s`.
3. **Roth IRAs of `d`** become `s`'s own. `first_roth_year[s] = min(first_roth_year[s], first_roth_year[d])`
   (Treas. Reg. §1.408A-6, Q&A-7(b)). `d`'s contribution basis and conversion layers are added to `s`'s ledger
   with their original years.
4. **Inherited IRAs / inherited Roth IRAs held by `d`**: `s` becomes successor beneficiary. The account keeps its
   distribution schedule (Section 6A.6).
5. **Taxable accounts** owned by `d` or `"joint"` become owned by `s`. **Basis step-up** to the Dec 31 value
   (IRC §1014(a); **convention:** Dec 31 value stands in for date-of-death value):
   - owned by `d`: full step-up.
   - `"joint"` (v1.2): by the account's **added** input `titling`: `"community"` or `"community_with_survivorship"`
     → full step-up of both halves (IRC §1014(b)(6) requires community property under state law; A.R.S. §25-211,
     §33-431(C)); `"jtwros"` (joint tenancy with right of survivorship, a separate form of ownership under A.R.S.
     §33-431(B)) → step-up of half, a qualified joint interest (IRC §2040(b); Pub 559):
     `new_basis = 0.5 × old_basis + 0.5 × value`. If `titling` is absent: half, and the year's output flags
     `stepup_titling_assumed` (the follow-up question is how the account is titled). Switch `community_property`
     (default `false`) treats an untitled joint account as community property.
6. **Cash accounts** pass to `s` (no tax).
7. **Social Security**: survivor rules (5.5) apply from January of `D+1`.
8. **Medicare** premiums for `d` stop after `D`.
9. Plan actions naming `d` as person, or naming an account that now belongs to `s`, continue to apply to the
   account under its new owner (age tests then use `s`'s age). Actions naming `d` as `person`
   (`claim_social_security`) are void after `D`.

**If there is no survivor** (single household, or the second death): the simulation ends after year `D`.
End-of-plan wealth (15.3) is measured on Dec 31 of `D`, with the heirs' tax applied as usual.

---

## 4. Growth and investment income (step 5)

For every account: `grown[A] = B0[A] × (1 + return)`.

- **Taxable accounts:** `dividends[A] = dividend_yield[A] × B0[A]`. Qualified dividends
  `= qualified_share[A] × dividends[A]` (Form 1040 line 3a); all dividends are ordinary dividends (line 3b).
  Dividends are reinvested: they are already inside `grown[A]` (the return is total return), and
  `cost_basis[A] += dividends[A]`. Capital-gain distributions are not modelled separately.
- **Cash accounts:** `interest[A] = return × B0[A]`, taxable interest (line 2b), reinvested (inside `grown[A]`).
- **IRAs, 401(k), Roth:** growth is untaxed.
- **Roth ledger:** growth is earnings (does not change contribution basis or conversion layers).

---

## 5. Social Security benefits for year `Y`

Sources: Social Security Act §§202, 215, 216(l); 20 CFR 404.409 (full retirement age), 404.410 (reduction),
404.313 (delayed retirement credits), 404.304 (rounding), 404.338/404.339 (widow(er)s); POMS RS 00615.

### 5.1 Ages in months

`age_months[P](year y, month m) = 12 × (y − born) + (m − born_month)`.

`fra_months[P]` = full retirement age from `ss_fra_months[born]` (Social Security Act §216(l)(1); 20 CFR
404.409; e.g., 66 years for 1943–1954 births rising two months per year to 67 for 1960 and later).

`survivor_fra_months[P]` from `ss_survivor_fra_months[born]` (§216(l)(1) as applied to widow(er)s; POMS
RS 00615.301).

### 5.2 COLA and the primary insurance amount

- `cola[Y]` = published `ss_cola[Y]` (effective for benefits payable for December of `Y−1`, paid in January of `Y`;
  42 USC 415(i)) or, if unpublished, `assumptions.cola`. **Convention:** a COLA applies to all 12 months of the
  year it is paid in (it actually applies from the December benefit; the one-month shift is ignored).
- `PIA[P][first_year] = monthly_at_fra`. For `Y > first_year`:
  `PIA[P][Y] = floor_to(PIA[P][Y−1] × (1 + cola[Y]), 0.10)` (42 USC 415(i)(2)(A)(ii): increased PIA rounded down
  to a multiple of $0.10).

### 5.3 The person's own retirement benefit

- Entitlement month: `claim_months = clamp(round(12 × claim_age), ss_min_claim_months, ss_max_drc_months)`
  (62 and 70 in the parameter table). Benefits start in the calendar month where
  `age_months = claim_months`, i.e. year `born + floor((born_month − 1 + claim_months)/12)`, month
  `((born_month − 1 + claim_months) mod 12) + 1`.
- Factor (20 CFR 404.410, 404.313):
  - `early = max0(fra_months − claim_months)`;
    `reduction = ss_early_rate_1 × min(early, 36) + ss_early_rate_2 × max0(early − 36)` (5/9 of 1% for the first
    36 months, 5/12 of 1% beyond); `factor = 1 − reduction`.
  - `late = max0(min(claim_months, ss_max_drc_months) − fra_months)`;
    `factor = 1 + ss_drc_monthly_rate × late` (2/3 of 1% per month for births 1943+).
  - **Convention:** delayed credits are credited in full from the entitlement month (SSA actually credits some in
    the following January; ignored).
- Monthly own benefit in `Y`: `own[P][Y] = floor_to(PIA[P][Y] × factor, 0.10)`.
- If `already_claimed_monthly` is given: `own[P][first_year] = already_claimed_monthly`, and for later years
  `own[P][Y] = floor_to(own[P][Y−1] × (1 + cola[Y]), 0.10)`.

### 5.4 Spousal benefit (both spouses alive)

Source: Social Security Act §202(b),(c),(k)(3),(r) (deemed filing, as amended by Bipartisan Budget Act of 2015
§831 for people born after Jan 1, 1954); 20 CFR 404.410(a)(2).

- A person `P` with spouse `Q` is entitled to a spousal top-up starting the later of `P`'s and `Q`'s own
  entitlement months (deemed filing: `P` files for both at once).
- `excess = max0(ss_spousal_rate × PIA[Q][Y] − PIA[P][Y])`.
- Reduction if spousal entitlement is before `P`'s FRA, by `early_sp` months:
  `ss_spousal_rate_1 × min(early_sp, 36) + ss_early_rate_2 × max0(early_sp − 36)` (25/36 of 1% for the first
  36 months, 5/12 of 1% beyond). No delayed credits on spousal benefits.
- `spousal[P][Y] = floor_to(excess × (1 − spousal_reduction), 0.10)`.
- If `already_claimed_monthly` is given for `P`, it is assumed to already include any spousal top-up; no spousal
  amount is added.
- Ends after the year either spouse dies.

### 5.5 Survivor benefit (after spouse `d` died in year `D`)

Source: Social Security Act §202(e),(f), §202(e)(2)(D) and (f)(3)(D) (the "widow's limit"); 20 CFR 404.338,
404.410(b); POMS RS 00615.320.

- Start month: the later of January of `D+1` and the month the survivor `s` reaches `ss_survivor_min_months`
  (age 60).
- **Base:**
  - If `d` had claimed by the end of `D`: `base = PIA[d] × max(1, factor[d])` — i.e. `d`'s PIA plus any delayed
    credits; early reduction is not carried into the base (20 CFR 404.313(e)(1)). **v1.2:** for a person entered with
    `already_claimed_monthly` and no `claimed_at_months`, `factor[d] = already_claimed_monthly / monthly_at_fra` in
    `first_year` (so delayed credits above 1 are kept), or 1 if `monthly_at_fra` is 0.
  - If `d` had not claimed: `base = PIA[d] × (1 + ss_drc_monthly_rate × max0(min(age_months_at_death, ss_max_drc_months) − fra_months[d]))`,
    with `age_months_at_death` = `d`'s age in months in **November** of `D` (v1.2: credits count through the month
    before the month of death, POMS RS 00615.690; with the Dec 31 death convention that is November).
  - Base is indexed by COLA with `PIA[d]` (`PIA[d][Y]` keeps being updated by 5.2 after death).
- **Survivor's age reduction:** if the survivor benefit starts `early_s` months before `survivor_fra_months[s]`:
  `reduction_s = ss_survivor_max_reduction × early_s / (survivor_fra_months[s] − ss_survivor_min_months)`
  (the maximum reduction at 60, spread evenly over the months from 60 to survivor FRA).
  `widow = base × (1 − reduction_s)`.
- **Widow's limit (RIB-LIM):** if `d` had claimed before `d`'s FRA (factor < 1):
  `widow = min(widow, max(own[d] at death, ss_rib_lim_rate × PIA[d]))`, both terms indexed by COLA to `Y`.
- `survivor[s][Y] = floor_to(widow, 0.10)`.
- **The survivor keeps the larger:** each month, `s` receives `max(own[s] if s is entitled that month, survivor[s])`
  (Social Security Act §202(k)(3): when entitled to two benefits, the person is paid the larger). **Convention:**
  if `s` has not yet claimed their own benefit, `s` takes the survivor benefit from its start month and starts
  their own at their (unchanged) `claim_age`, being paid the larger each month. (Choosing to delay the survivor
  benefit for a higher amount is a strategy the plan input does not express; out of scope.)

### 5.6 Annual amount and rounding

- Monthly payable amount = `floor_to(own + spousal, 1.00)` while both alive, or `floor_to(max(own, survivor), 1.00)`
  for a survivor (42 USC 415(g): benefits payable are rounded down to the whole dollar). Switch
  `ss_dollar_rounding` (default `true`).
- `ss_benefits[P][Y]` = sum over the months of `Y` in which `P` is entitled. **Convention:** benefits are counted in
  the year of the month they are *for*, not the month they are paid (the December benefit is actually paid in
  January and reported on the next SSA-1099). Medicare premiums withheld from benefits do not reduce the reported
  benefit (Pub 915, "Medicare premiums").
- `SS_total[Y] = Σ ss_benefits[P][Y]` over people on the return (box 5 of Form SSA-1099, Form 1040 line 6a).

---

## 6. Required minimum distributions (owner's own accounts)

Sources: IRC §401(a)(9) (as amended by SECURE Act 2019 and SECURE 2.0 Act 2022 §107), §408(a)(6); Treas. Reg.
§§1.401(a)(9)-2, -5, -9, 1.408-8 (final regulations T.D. 10001, July 2024, applicable from 2025); Pub 590-B.

### 6.1 Who owes an RMD for year `Y`

Every `traditional_ira` and `401k` with an owner `P` whose **applicable age** is reached in or before `Y`.
Roth IRAs have no lifetime RMDs (IRC §408A(c)(5)).

`applicable_age[P]` from `rmd_applicable_age` by birth (IRC §401(a)(9)(C)(v); Reg. §1.401(a)(9)-2(b)(2)):

- born before July 1, 1949: 70½ (the year of reaching 70½ by 3.1);
- born July 1, 1949 – Dec 31, 1950: 72;
- born 1951–1959: 73;
- born 1960 or later: 75.

**Reading (1959):** the statute as written gives both 73 and 75 for people born in 1959. The proposed
regulations of July 2024 (89 FR 58644, proposed §1.401(a)(9)-2(b)(2)(v)) say 73. This spec uses 73.

`first_rmd_year[P]` = the year `P` reaches the applicable age. The **required beginning date** is April 1 of
`first_rmd_year + 1` (§401(a)(9)(C)(i)).

**First-year deferral (Convention):** the RMD for `first_rmd_year` may legally be taken by April 1 of the next
year (making two RMDs taxable that year). Default: it is taken in `first_rmd_year`. Switch
`defer_first_rmd` (default `false`); if `true`, the first-year RMD is taken in the next year in addition to that
year's RMD, and both are computed on their own prior-Dec-31 balances (Reg. §1.401(a)(9)-5(a)(2)).

The still-working exception for a 401(k) (§401(a)(9)(C)(i)(II)) is out of scope: RMDs from a `401k` start at the
applicable age even if the owner has `wages`.

### 6.2 Amount

`RMD[A][Y] = B0[A] / divisor` where `B0[A]` is the Dec 31 balance of `Y−1` (Reg. §1.401(a)(9)-5(b)).

- `divisor = uniform_lifetime_table[age[P]]` (Reg. §1.401(a)(9)-9(c)), age = age attained in `Y`.
- **Joint Life case:** if the owner is married, the spouse is the sole beneficiary for the whole year, and the
  spouse is more than 10 years younger, `divisor = joint_last_survivor_table[age[P]][age[spouse]]`
  (Reg. §1.401(a)(9)-5(c)(2), -9(d)). Marital status is fixed as of Jan 1 of `Y`
  (Reg. §1.401(a)(9)-5(c)(2)(ii)): a spouse dying during `Y` still counts. **Reading:** the inputs give no
  beneficiary designations. Switch `spouse_is_sole_beneficiary` (default `true` for `mfj` households) assumes
  each married owner's spouse is the sole beneficiary.
- If `grown[A] < RMD[A][Y]`, the RMD is `grown[A]`.

### 6.3 Aggregation and QCDs

- **IRAs:** a person's RMDs from all their `traditional_ira` accounts may be taken from any of them (Reg.
  §1.408-8(e)). `IRA_RMD[P][Y] = Σ RMD over P's traditional_ira`. QCDs from any of `P`'s traditional IRAs reduce it
  (IRC §408(d)(8); Pub 590-B, "Qualified charitable distributions ... count toward your RMD").
  `IRA_RMD_remaining[P] = max0(IRA_RMD[P] − QCD_from_own_IRAs[P])`, taken from `P`'s traditional IRAs **pro rata
  to their balances after QCDs** (convention).
- **401(k):** each plan's RMD comes from that plan (Reg. §1.401(a)(9)-8; no aggregation across plans). QCDs cannot
  come from a 401(k).
- **Inherited IRAs:** Section 6A.7.

### 6.4 Year of death

The RMD of a person who dies in `Y` is taken in `Y` (Section 3.1 convention: alive all year) and reported on the
joint return. In `Y+1` the survivor's RMD on the rolled-over accounts follows 6.1–6.2 with the survivor's own age
(the deceased's balance is part of the survivor's Dec 31 balance). If the survivor has not reached their
applicable age, no RMD is due. (SECURE 2.0 §327 election to be treated as the deceased employee: out of scope.)

### 6.5 RMD before conversion

An RMD is not an eligible rollover distribution and cannot be converted (IRC §402(c)(4)(B), §408(d)(3)(E);
Reg. §1.408A-4, Q&A-6(a)). The first dollars distributed in a year are treated as the RMD
(Reg. §1.402(c)-2, Q&A-7). Hence in step 6 the RMD (and any QCD) comes out before any conversion, and a
conversion is limited to `grown[A]` minus everything already distributed from `A` in steps a–c.

---

## 6A. Inherited IRAs and inherited Roth IRAs

Sources: IRC §401(a)(9)(B), (E), (H) (SECURE Act §401); Treas. Reg. §1.401(a)(9)-3 (death before RBD), -4
(beneficiaries, eligible designated beneficiaries, age of majority), -5(d)–(e) (applicable denominator after
death); IRS Notices 2022-53, 2023-54, 2024-35 (waivers); Pub 590-B chapter 1 "Inherited IRAs" and Table I.

### 6A.1 Did the owner die on or after the required beginning date?

If `owner_had_reached_rbd` is given, use it. Otherwise derive it: compute the owner's applicable age from
`from_born` (6.1, with `born_month = 1` since no month is given) and `rbd_year = first_rmd_year + 1`.
**Reading:** `owner_had_reached_rbd = (died ≥ rbd_year)` — death in the RBD year is treated as after April 1
(the input has no date). For `inherited_roth_ira` it is always `false` (a Roth IRA owner has no RBD, IRC
§408A(c)(5); Reg. §1.408A-6, Q&A-14(b)).

### 6A.2 Beneficiary classes

- **Eligible designated beneficiaries (EDB)** (IRC §401(a)(9)(E)(ii)): `spouse`, `minor_child` (of the owner, until
  age of majority), `disabled`, `chronically_ill`, `not_more_than_10_years_younger`.
- `designated`: a designated beneficiary that is not an EDB → 10-year rule.
- `non_designated`: no designated beneficiary → 5-year rule or owner's remaining life expectancy.

### 6A.3 Life-expectancy divisors

Let `D` = year of death, `b` = beneficiary.

- **Beneficiary, non-recalculated ("minus one"):** `LE_b[Y] = single_life_table[age_b(D+1)] − (Y − (D+1))`, where
  `age_b(D+1)` is the beneficiary's age attained in `D+1` (Reg. §1.401(a)(9)-5(d)(1)(ii)-(iii); Pub 590-B "the
  applicable denominator is reduced by one for each calendar year that has elapsed after the calendar year
  following the employee's death").
- **Spouse, recalculated:** `LE_s[Y] = single_life_table[age_s(Y)]` each year (Reg. §1.401(a)(9)-5(d)(1)(ii)(B)).
- **Owner's remaining life expectancy:** `LE_o[Y] = single_life_table[age_o(D)] − (Y − D)` where `age_o(D)` is the
  owner's age attained in `D` (Reg. §1.401(a)(9)-5(d)(1)(ii)(A), (d)(2)).
- **After the RBD**, the applicable denominator is the longer of the beneficiary's divisor and `LE_o[Y]`
  (Reg. §1.401(a)(9)-5(d)(1)(i)).
- A divisor ≤ 1 means the whole balance is distributed.
- RMD = `B0[A] / divisor` (prior Dec 31 balance).

### 6A.4 Rules by class

| Class | Owner died before RBD (or any inherited Roth) | Owner died on/after RBD |
|---|---|---|
| `designated` | No annual RMD; whole balance by Dec 31 of `D+10` (IRC §401(a)(9)(B)(ii), (H)(i); Reg. §1.401(a)(9)-3(c)(4)). | Annual RMD in `D+1 … D+9` with the longer of `LE_b` and `LE_o`; whole balance by Dec 31 of `D+10` (Reg. §1.401(a)(9)-5(d)(1)(i), -3(c)(4)). |
| `spouse` (sole beneficiary, not treated as own) | No RMD until the year the owner would have reached the applicable age (IRC §401(a)(9)(B)(iv)(I)); then annual with `LE_s` (recalculated). | Annual from `D+1` with the longer of `LE_s` and `LE_o`. |
| `disabled`, `chronically_ill`, `not_more_than_10_years_younger` | Annual from `D+1` with `LE_b` (Reg. §1.401(a)(9)-3(c)(5) default is the life-expectancy rule). | Annual from `D+1` with the longer of `LE_b` and `LE_o`. |
| `minor_child` | Annual from `D+1` with `LE_b` until the year the child reaches `minor_majority_age` (21, Reg. §1.401(a)(9)-4(e)(3)); annual RMDs continue after that, and the whole balance is due by Dec 31 of the 10th year after the year the child reaches 21 (IRC §401(a)(9)(E)(iii); Reg. §1.401(a)(9)-5(e)). | Same, with the longer of `LE_b` and `LE_o` for the annual amounts. |
| `non_designated` | No annual RMD; whole balance by Dec 31 of `D+5` (IRC §401(a)(9)(B)(ii); Reg. §1.401(a)(9)-3(c)(2)). | Annual from `D+1` with `LE_o` (Reg. §1.401(a)(9)-5(d)(2)); no 10-year limit. |

**Reading (EDB election):** an EDB whose owner died before the RBD may elect the 10-year rule instead. The spec uses
the regulation's default (life expectancy, Reg. §1.401(a)(9)-3(c)(5)); switch `edb_elects_10_year` (default
`false`).

### 6A.5 The waiver years

For `designated` beneficiaries whose owner died on/after the RBD in 2020–2023, the annual RMDs for 2021–2024 were
waived (Notices 2022-53, 2023-54, 2024-35); annual RMDs start in 2025 (final regs applicability). The divisor
still steps down by one for every elapsed year (the waiver excuses the distribution, not the clock), and the
`D+10` deadline is unchanged. Parameter `inherited_rmd_waiver_years`. Since `first_year ≥ 2025` in practice,
this affects only the divisor count.

### 6A.6 Successor beneficiary (the beneficiary dies)

When the holder of an inherited account dies with a spouse surviving (3.3 step 4): the successor continues the
same annual divisor schedule (the first beneficiary's non-recalculated divisor keeps stepping down by one), and:

- if the first beneficiary was an EDB on a life-expectancy schedule, the account must be emptied by Dec 31 of the
  10th year after the year the EDB died (IRC §401(a)(9)(H)(iii): on the death of an eligible designated beneficiary
  the remainder must be distributed within 10 years after that death);
- if the first beneficiary was on a 10-year or 5-year schedule, the original deadline stays.

Implement (v1.2): if the first beneficiary was an **eligible designated beneficiary** (`spouse`, `minor_child`,
`disabled`, `chronically_ill`, `not_more_than_10_years_younger`) on a life-expectancy schedule,
`deadline = min(existing_deadline, D_b + 10)` (Reg. §1.401(a)(9)-5(e)(3), (e)(4)), where `D_b` is the year the first
beneficiary died and `existing_deadline` is ∞ for life-expectancy schedules. Otherwise the deadline does not move: a
`designated` (non-EDB) beneficiary's successor keeps the original owner's `D + 10` (Reg. §1.401(a)(9)-5(e)(2)), and a
`non_designated` schedule on the owner's remaining life expectancy has no 10-year limit for any later holder (every
limit in -5(e)(2)–(4) requires a designated beneficiary). Annual RMDs continue on the first beneficiary's divisor
schedule (-5(d)(1)). **Reading:** a recalculated spouse divisor (`LE_s`) stops
recalculating at the spouse's death and continues as `LE_s` of the year of death minus one per later year (the
usual treatment of a recalculating life expectancy after death, Reg. §1.401(a)(9)-5(d)).

### 6A.7 Aggregation, QCDs and distributions in the deadline year

- Each inherited account's RMD is taken from that account (convention; Reg. §1.408-8(e) permits aggregation only
  among IRAs inherited from the same decedent).
- A QCD from an inherited IRA is allowed if the beneficiary is over 70½ (Pub 590-B, "QCDs"), and counts toward that
  account's RMD.
- In the deadline year the RMD is the entire grown balance.
- Inherited traditional IRAs have zero basis (convention; inherited basis is out of scope) and are **not** part of
  the beneficiary's own Form 8606 line 6 (Instructions for Form 8606, "Inherited IRAs": basis in inherited IRAs is
  tracked separately and not combined).
- Distributions from inherited accounts are never subject to the 10% additional tax (IRC §72(t)(2)(A)(ii)).

### 6A.8 Inherited Roth IRAs

- Distribution schedule: as the "died before RBD" column.
- Tax: a distribution is tax-free if `Y ≥ first_roth_year + 5` (owner's 5-taxable-year period; IRC
  §408A(d)(2)(A)(iii), (d)(2)(B); Reg. §1.408A-6, Q&A-7). Otherwise ordering 7.5 applies with the original owner's
  ledger: the inherited Roth's contribution basis and conversion layers are unknown, so **convention:** the
  opening balance is treated as earnings unless the input supplies `contribution_basis`; taxable earnings are
  included in income without the 10% tax.

---

## 7. December 31 transactions (step 6)

All amounts are taken from `grown[A]` (balance after growth), in this order.

### 7.1 Order (MUST)

a. QCDs → b. remaining RMDs (own and inherited) → c. plan `withdrawal` actions → d. Roth conversions → e. gain
harvesting → f. spending withdrawals (Section 8) → g. surplus deposit.

Why: RMDs must precede conversions (6.5); QCDs must come first so they count toward the RMD; explicit plan
actions come before the solver so the solver only fills the remaining gap; harvesting comes before spending
withdrawals so that withdrawals from a harvested account use the raised basis.

### 7.2 QCDs (step a)

Source: IRC §408(d)(8); Pub 590-B "Qualified Charitable Distributions"; Form 1040 instructions lines 4a–4b.

- Only from `traditional_ira` or `inherited_ira` (not a 401(k), not a Roth: §408(d)(8)(B)(i) "individual retirement
  plan other than an ongoing SEP or SIMPLE"); the account owner (beneficiary) must have `over_70h[P][Y]`. Otherwise
  the action is void and flagged.
- Per-person cap: `Σ QCD by P in Y ≤ qcd_limit[Y]` (indexed, §408(d)(8)(G)). Excess is clamped.
- Tax effect: excluded from gross income (included on line 4a, excluded from 4b, "QCD" written next to it).
  §408(d)(8)(D): the QCD is treated as coming first from the taxable part of the IRA, so **it does not use up
  basis**: QCDs are excluded from Form 8606 line 7 (Instructions for Form 8606, "Line 7": "a distribution doesn't
  include ... a qualified charitable distribution").
- No charitable deduction for a QCD (§408(d)(8)(E)); QCDs are not in `charity_cash` and are not subject to the
  0.5% floor or §68. The QCD is not cash available for spending.
- The anti-abuse reduction for post-70½ deductible contributions (§408(d)(8)(A) last sentence) and the one-time
  split-interest QCD are out of scope.

### 7.3 Remaining RMDs (step b)

Distribute the remaining RMD amounts (6.3, 6A.7). They are cash inflows.

### 7.4 Plan withdrawals and Roth conversions (steps c, d)

- `withdrawal`: distributed from `from`, cash inflow; taxed per account type (9.4–9.6).
- `roth_conversion`: amount (clamped to what is left in `from`) moves to the owner's Roth IRA. If the owner has no
  `roth_ira`, one is created with `first_roth_year = Y` (a conversion counts as a contribution for the 5-year
  period, Reg. §1.408A-6, Q&A-2). The converted amount is added to the Roth ledger as a conversion layer for year
  `Y` with its taxable and nontaxable parts (9.5). A conversion is not cash available for spending; its tax is paid
  from other sources through the spending solve.
- Converting from a `401k` (in-plan Roth rollover or direct rollover to a Roth IRA, IRC §402A(c)(4), §408A(d)(3),
  (e)) is fully taxable (no plan basis) and does not touch Form 8606 Part I.
- No 10% tax on the conversion itself (IRC §408A(d)(3)(A)(ii)).

### 7.5 Roth distributions (ordering, 5-year rules, penalty)

Sources: IRC §408A(d)(1)–(4); Reg. §1.408A-6 Q&A-1 to -9; Form 8606 Part III; IRC §72(t).

Per owner, all Roth IRAs are treated as one (§408A(d)(4)(A)).

- **Qualified distribution** — entirely tax-free, no penalty — if both: `Y ≥ first_roth_year[P] + 5` (five-taxable-
  year period, §408A(d)(2)(B)) and (`over_59h[P][Y]` or the owner is dead [inherited] or disabled)
  (§408A(d)(2)(A)).
- Otherwise, a distribution comes out in this order (§408A(d)(4)(B); Reg. §1.408A-6 Q&A-8):
  1. regular contributions (`contribution_basis`) — tax-free, no penalty;
  2. conversion layers, oldest year first; within a layer, the **taxable** part first, then the nontaxable part —
     never taxed again; but if the owner is under 59½ and `Y < layer_year + 5`, the 10% additional tax applies to
     the amount drawn from the layer's taxable part (§408A(d)(3)(F); the "conversion five-year rule", counted from
     Jan 1 of the conversion year);
  3. earnings — included in income (Form 1040 line 4b), plus the 10% additional tax if the owner is under 59½
     and not a beneficiary.
- **Same-year conversions count (v1.1).** The ordering is applied at the end of the year to the year's total
  Roth distributions, after adding the conversions made during that same year as a layer for year `Y` (Reg.
  §1.408A-6 Q&A-9(a): all distributions during a year are aggregated, and all conversion contributions received
  during the same year are aggregated). So a Roth withdrawal in the year of a conversion comes out of that conversion
  layer (already taxed) before any earnings.
- Two different five-year rules exist and MUST NOT be confused: the qualified-distribution clock
  (`first_roth_year`, one per person, never restarts) and the per-conversion penalty clock (one per layer).

### 7.6 Gain harvesting (step e)

`harvest_gains {amount}` realizes `G = min(amount, Σ max0(grown[A] − cost_basis[A]))` across the household's
taxable accounts, pro rata to each account's unrealized gain. For each account `cost_basis[A] += G_A`. No change
to the balance. Wash-sale rules do not apply to gains (IRC §1091 applies to losses only).

### 7.7 Taxable-account sales

Selling `w` from taxable account `A` with value `V = grown[A]` (less earlier sales this year) and basis `C`
(average cost, **convention**; specific-lot identification is out of scope):
`gain = w × (1 − C / V)` (may be negative), `C ← C × (1 − w / V)`.

### 7.8 Traditional distributions: taxable part

- `401k` and `inherited_ira`: fully taxable (zero basis).
- `traditional_ira`: taxable part from the owner's Form 8606 (9.5).

### 7.9 10% additional tax (computed in 9.12)

Applies to the taxable part of distributions from the owner's own `traditional_ira`/`401k` when not
`over_59h[P][Y]`, and to Roth amounts per 7.5. Not to RMDs (impossible before 59½ in scope), QCDs, conversions,
inherited accounts. Exceptions not modelled: disability, SEPP (§72(t)(2)(A)(iv)), separation from service at 55
for 401(k) (§72(t)(2)(A)(v); applies only to employer plans, not IRAs, §72(t)(3)(A)), and others in §72(t)(2).

---

## 8. Cash flow and the spending solve (steps 6f, 6g)

### 8.1 Cash inflows and outflows

Inflows for `Y` (fixed before the solve):
`wages + pension + annuity_taxable + interest_taxable + interest_tax_exempt + rental + SS_total
+ RMD cash (step b) + plan withdrawals (step c)`.
Investment income inside taxable and cash accounts (Section 4) is reinvested and is **not** an inflow. QCDs and
conversions are not inflows.

Outflows: `need[Y] + federal_tax[Y] + state_tax[Y] + medicare_premiums[Y]`.

`medicare_premiums[Y]` is known before the solve (it depends on tax year `Y−2`, Section 12) and so is not circular.

### 8.2 Sources, in order

The spending gap `W` (gross) is drawn from, in this order:

1. `cash` accounts (pro rata to balances);
2. `taxable` accounts (pro rata to balances; gains per 7.7);
3. "traditional": all `traditional_ira`, `401k` and `inherited_ira` accounts of everyone, pro rata to their
   balances after steps a–e (taxable parts per 7.8; 10% per 7.9);
4. "Roth": all `roth_ira` and `inherited_roth_ira`, pro rata (taxation per 7.5 / 6A.8).

Each source is exhausted before the next is touched. **Reading:** the brief says "traditional (pro-rata)"; this
spec includes inherited IRAs in that pool (they are pre-tax money of the household).

### 8.3 Solve (MUST)

Define `net(W)` = inflows + `W` − outflows, where federal and state tax are recomputed (Sections 9–10) with the
`W` allocation of 8.2. Because each marginal dollar of `W` raises total tax by less than a dollar (every marginal
rate, including the Social Security "torpedo", senior-deduction phase-out, NIIT and 10% stacking, is below 100%),
`net` is strictly increasing in `W`, so the answer is unique.

- If `net(0) ≥ 0`: `W = 0` and the surplus `net(0)` is deposited to cash (step g). If the household has no cash
  account, one is created (`owner = "joint"`, or the single person). Deposits are not taxed.
- Else find `W` in `[0, W_max]` (`W_max` = everything left in all four pools) by bisection: `lo = 0`,
  `hi = W_max`; repeat until `hi − lo < 0.005`: `mid = (lo+hi)/2`; if `net(mid) ≥ 0` then `hi = mid` else `lo = mid`.
  Use `W = hi`. Two engines agree to within cents.
- If `net(W_max) < 0`, take everything; report `unfunded[Y] = −net(W_max)`; the household is depleted.

---

## 9. Federal income tax (form order)

Line numbers follow the 2025 Form 1040 and the 2025 instructions; where numbering shifts in later years the line
**names** govern. All amounts for the household's return for year `Y`.

### 9.1 Income lines

- **1a Wages** = Σ `wages`.
- **2a Tax-exempt interest** = Σ `interest_tax_exempt` (not in AGI; used in 9.3, 9.6 and 12).
- **2b Taxable interest** = Σ `interest_taxable` + Σ cash-account interest (Section 4).
- **3b Ordinary dividends** = Σ taxable-account dividends; **3a Qualified dividends** = Σ qualified parts.
- **4a IRA distributions (gross)** = all distributions from `traditional_ira`, `inherited_ira`, `roth_ira`,
  `inherited_roth_ira`, including QCDs and IRA→Roth conversions.
  **4b Taxable amount** = taxable parts of traditional IRA distributions and conversions (9.5) + inherited IRA
  distributions + taxable Roth earnings (7.5, 6A.8). QCDs are excluded from 4b.
- **5a/5b Pensions and annuities** = `pension` + `annuity_taxable` + all `401k` distributions and 401(k)→Roth
  conversions (fully taxable).
- **6a Social Security benefits** = `SS_total`; **6b taxable** per 9.3.
- **7 Capital gain or (loss)** = net realized gains (7.6 is a realization; 7.7) minus the capital-loss carryover,
  per Schedule D: if the net is a loss, line 7 = `−min(|net|, capital_loss_limit[filing])` and the rest carries
  forward (IRC §1211(b), §1212(b)). All long-term. Harvested gains (7.6) are included.
- **8 Additional income (Schedule 1)** = `rental`.
- **9 Total income** = 1a + 2b + 3b + 4b + 5b + 6b + 7 + 8.
- **10 Adjustments** = 0 (none in scope).
- **11 AGI** = line 9.

### 9.2 Circularity of line 6b

6b depends on the other income; the other income does not depend on 6b. Compute `AGI_ex_SS` = 1a + 2b + 3b + 4b +
5b + 7 + 8 first, then 6b, then AGI = `AGI_ex_SS` + 6b.

### 9.3 Taxable Social Security (Pub 915 Worksheet 1; IRC §86)

Let `A = SS_total`.

1. `provisional = AGI_ex_SS + line 2a + ss_tax.first_rate × A` (Pub 915 Worksheet 1 lines 1–8: one-half of
   benefits, plus all other income including tax-exempt interest; IRC §86(b)(2)). Adjustments (worksheet line 7)
   are 0 in scope.
2. `base = ss_tax.base_amount[filing]`, `adj = ss_tax.adjusted_base_amount[filing]` (IRC §86(c); **not indexed**).
3. If `provisional ≤ base`: taxable = 0.
4. If `base < provisional ≤ adj`: taxable = `min(first_rate × A, first_rate × (provisional − base))`.
5. If `provisional > adj`: taxable = `min(second_rate × A, second_rate × (provisional − adj) +
   min(first_rate × A, first_rate × (adj − base)))` (IRC §86(a)(2)).

(`first_rate` = one-half, `second_rate` = 85%.) The lump-sum election (Pub 915 Worksheets 2–4) is out of scope.

### 9.4 Traditional distributions (lines 4b, 5b)

- `401k`, `inherited_ira`: 100% taxable.
- `traditional_ira`: 9.5.

### 9.5 Form 8606 Part I and II — per person (MUST)

Each person files their own Form 8606 with only their own `traditional_ira` accounts (IRC §408(d)(2): all IRAs of
the individual treated as one contract; §72 pro-rata rule). Lines (2025 Form 8606):

- Line 1 nondeductible contributions this year = 0 (none in scope). Line 2 = `basis8606[P]` (prior line 14).
  Line 3 = line 1 + line 2. Lines 4–5: line 4 = 0, line 5 = line 3.
- **Line 6** = value of all of `P`'s `traditional_ira` accounts on **Dec 31 of `Y`** (after all of step 6;
  includes neither `401k` nor `inherited_ira`; SEP/SIMPLE would be included).
- **Line 7** = distributions from those IRAs in `Y`, **excluding** conversions, QCDs and rollovers (spending,
  RMD and plan withdrawals).
- **Line 8** = conversions from those IRAs to Roth in `Y`.
- Line 9 = 6 + 7 + 8. If line 9 = 0, nothing is taxable and stop.
- **Line 10** = `min(1, line 5 / line 9)`. **Reading:** the form says "rounded to at least 3 places"; this spec
  uses the unrounded ratio (switch `round_8606_ratio_3dp`, default `false`).
- Line 11 = line 8 × line 10 (nontaxable part of conversions). Line 12 = line 7 × line 10 (nontaxable part of
  distributions). Line 13 = 11 + 12.
- **Line 14** = line 3 − line 13 → `basis8606[P]` for `Y+1`.
- Line 15c (taxable distributions) = line 7 − line 12. Line 18 (taxable conversions) = line 8 − line 11.
- 4b receives line 15c + line 18 (plus QCDs are excluded).
- Conversion layer for the Roth ledger: `taxable_amount = line 18`, `nontaxable_amount = line 11` (and, for a
  401(k) conversion, all taxable).

Within the spending solve (8.3), line 6 and line 7 change with `W`; recompute 9.5 for each trial `W`.

### 9.6 MAGI definitions

All are built from the same return. In scope, the foreign-income exclusions (§§911, 931, 933) are zero.

| Name | Definition | Used for | Source |
|---|---|---|---|
| `provisional_income` | `AGI_ex_SS + tax-exempt interest + ½ SS` | taxable SS | IRC §86(b)(2); Pub 915 Worksheet 1 |
| `magi_senior` | AGI (+ §§911/931/933 exclusions) | senior deduction phase-out | IRC §151(d)(5)(C)(iii); Schedule 1-A line 3 |
| `magi_salt` | AGI (+ §§911/931/933) | SALT phase-down | IRC §164(b)(7)(B)(iv) |
| `magi_niit` | AGI (+ §911 net) | NIIT | IRC §1411(d) |
| `magi_irmaa` | AGI + tax-exempt interest | IRMAA (2 years later) | SSA §1839(i)(4)(A); 20 CFR 418.1010(b) |
| `magi_aca` | AGI + tax-exempt interest + nontaxable SS (`SS_total − line 6b`) | **reported only**; no premium credit is modelled | IRC §36B(d)(2)(B) |

### 9.7 Standard deduction

- `std = standard_deduction[Y][filing] + additional_std_65[Y][married|unmarried] × n65` where `n65` = number of
  people on the return with `is65` (IRC §63(c)(1)–(3), (f)(1), (f)(3)); the `married` amount applies to `mfj`,
  `unmarried` to `single`. Blindness additions out of scope. In the year of death, a deceased spouse who was 65
  counts (IRC §63(f)(1)(B)).
- **Non-itemizer charitable deduction** (from 2026; IRC §170(p) as amended by OBBBA §70424):
  `nonitemizer_charity = min(charity_cash, nonitemizer_charitable_cap[filing])` for taxpayers who do not itemize.
  Not subject to the 0.5% floor (OBBBA §70425(a)(3)). Not indexed. Zero before `nonitemizer_charitable_first_year`.

### 9.8 Itemized deductions (Schedule A)

- **Medical (lines 1–4):** `max0(medical − medical_floor_rate × AGI)` (IRC §213(a)).
- **Taxes (lines 5–7):** `taxes = state_income_tax_paid + salt_other`. `state_income_tax_paid` = the Arizona tax for
  year `Y` (Section 10) — **convention:** state income tax is paid in the year it is owed (withholding/estimates
  exactly equal to the liability; refunds and balances due in the following year are ignored, so the prior-year
  state refund inclusion rule of §111 never arises).
  - `cap = salt_cap[Y]` (IRC §164(b)(6)(B), (b)(7)(A): a scheduled amount for 2025–2029, then the permanent amount).
    For years `< salt_phasedown_last_year + 1`:
    `cap = max(salt_floor, cap − salt_phasedown_rate × max0(magi_salt − salt_phasedown_threshold[Y]))`
    (IRC §164(b)(7)(B)(i)–(iii)). Single and MFJ have the same cap and threshold (the halving applies only to
    married filing separately).
  - `salt_deduction = min(taxes, cap)`.
- **Interest (line 8):** `mortgage_interest` (assumed qualified residence interest within limits, IRC §163(h)).
- **Gifts to charity (lines 11–14):** from 2026 (IRC §170(b)(1)(I), OBBBA §70425):
  `charity_item = min(max0(charity_cash − charitable_floor_rate × AGI), charitable_cash_ceiling_rate × AGI)`.
  **Reading:** floor first, then the 60% ceiling (the floor reduces "the contributions taken into account", the
  ceiling limits the deduction); excess over the ceiling would carry forward 5 years (§170(d)(1)); carryforwards
  are out of scope and the output flags any excess. Before 2026: no floor.
  The contribution base equals AGI in scope (§170(b)(1)(H)).
- `itemized_pre = medical_item + salt_deduction + mortgage_interest + charity_item`.
- **§68 limit** (2026 onward; IRC §68 as rewritten by OBBBA §70111):
  `reduction = itemized_limit_rate × min(itemized_pre, max0(TI_pre + itemized_pre − bracket37_start[Y][filing]))`
  where `TI_pre` = taxable income computed with `itemized_pre` (and the senior deduction) and without §68, so
  `TI_pre + itemized_pre = AGI − senior_deduction`, and `bracket37_start` is the lower edge of the 37% bracket in
  `ordinary_brackets[Y][filing]`. Applied after all other itemized limitations (§68(b)).
  `itemized = itemized_pre − reduction`.

### 9.9 Choosing standard or itemized

Itemize if `itemized > std + nonitemizer_charity`; otherwise take `std + nonitemizer_charity` (IRC §63(b), (e)).
Ties go to the standard deduction.

### 9.10 Senior deduction (2025–2028; Schedule 1-A Part V; IRC §151(d)(5)(C), OBBBA §70103)

For tax years `senior_deduction.first_year ≤ Y ≤ senior_deduction.last_year` (taxable years beginning before
2029); allowed to itemizers and non-itemizers; for married people only on a joint return (always the case in
scope); each person needs a valid SSN (assumed).

- `reduction = senior_deduction.phaseout_rate × max0(magi_senior − senior_deduction.threshold[filing])`
  (Schedule 1-A lines 31–34).
- For **each** person on the return with `is65`: `max0(senior_deduction.amount − reduction)` (line 35, entered once
  per qualifying spouse on lines 36a/36b). **The reduction is subtracted from each person's amount separately**, so
  a couple who both qualify lose twice the phase-out rate per dollar of MAGI over the threshold.
- `senior_deduction = Σ` (line 37 → Form 1040 line 13b).
- Not indexed. Zero outside the year window.

### 9.11 Taxable income and regular tax

- `deductions = (std + nonitemizer_charity or itemized) + senior_deduction` (lines 12, 13b, 14).
- `TI = max0(AGI − deductions)` (line 15).
- `QD = line 3a`; `CG = max0(line 7)` (if line 7 ≤ 0 it contributes nothing to the worksheet).
- If `QD + CG = 0`: `tax = ordinary_tax(TI)`, where `ordinary_tax(x)` applies `ordinary_brackets[Y][filing]`
  (IRC §1(j)(2) as made permanent by OBBBA §70101; the Tax Computation Worksheet, not the Tax Table).
- Otherwise, **Qualified Dividends and Capital Gain Tax Worksheet** (Form 1040 instructions, line 16; IRC §1(h),
  §1(j)(5)):
  1. L1 = TI. 2. L2 = QD. 3. L3 = CG. 4. L4 = L2 + L3. 5. L5 = max0(L1 − L4) (ordinary income).
  6. L6 = `cg_thresholds[Y][filing].zero_max`. 7. L7 = min(L1, L6). 8. L8 = min(L5, L7).
  9. L9 = L7 − L8 (**taxed at 0%**). 10. L10 = min(L1, L4). 11. L11 = L9. 12. L12 = L10 − L11.
  13. L13 = `cg_thresholds[Y][filing].fifteen_max`. 14. L14 = min(L1, L13). 15. L15 = L5 + L9.
  16. L16 = max0(L14 − L15). 17. L17 = min(L12, L16) (**taxed at 15%**). 18. L18 = L17 × `cg_rate_15`.
  19. L19 = L9 + L17. 20. L20 = L10 − L19 (**taxed at 20%**). 21. L21 = L20 × `cg_rate_20`.
  22. L22 = ordinary_tax(L5). 23. L23 = L18 + L21 + L22. 24. L24 = ordinary_tax(L1). 25. `tax = min(L23, L24)`.
- Unrecaptured §1250 gain and 28% collectibles gain are out of scope.

### 9.12 Other taxes (Schedule 2)

- **NIIT (Form 8960; IRC §1411):**
  `NII = max0(line 2b + line 3b + line 7 + rental + annuity_taxable)`, where `annuity_taxable` is included only
  if switch `annuity_is_nii` (default `true`). Line 7 is the Form 1040 amount, so a net capital loss (limited to
  `capital_loss_limit`) reduces NII, as on Form 8960 line 5a (Instructions for Form 8960, line 5a; Reg.
  §1.1411-4(d)).
  Excluded: wages, pensions, IRA/401(k)/Roth distributions and conversions, Social Security, tax-exempt interest
  (§1411(c)(5); Reg. §1.1411-8). Deductions allocable to NII (e.g. state tax on it, Form 8960 lines 9–10) are
  ignored (**convention**, conservative).
  `NIIT = niit.rate × min(NII, max0(magi_niit − niit.threshold[filing]))`. Thresholds are **not indexed**
  (§1411(b)).
- **10% additional tax (Form 5329 Part I; IRC §72(t)(1)):** `early_withdrawal_rate × (amounts identified in 7.5
  and 7.9)`. Also IRC §72(t) applies to a Roth conversion layer under §408A(d)(3)(F).
- **Credits:** none in scope.
- `federal_tax = tax + NIIT + additional_10pct`.

---

## 10. Arizona income tax (state = "AZ")

Sources: A.R.S. Title 43, chapter 10 as amended by Laws 2026, ch. 140 (HB 4168; §35 makes the amendments to
§§43-1022 and 43-1041 retroactive to tax years beginning after Dec 31, 2024, and to §§43-1021 and 43-1042 retroactive
to tax years beginning after Dec 31, 2025); A.R.S. §43-105 (Internal Revenue Code as in effect Jan 1, 2026);
2025 Arizona Form 140 and instructions.

Filing status: Arizona follows the federal status (A.R.S. §43-309; Form 140 instructions, "Filing status"); a
surviving spouse files joint for the year of death (Form 140 instructions, line 43 note).

**Conformity convention for future years:** A.R.S. §43-105 fixes the IRC as of Jan 1, 2026. Each year Arizona
updates this date. The spec assumes continued conformity (switch `az_assume_future_conformity`, default `true`).

### 10.1 Arizona gross income and AGI (Form 140 lines 12–42)

1. **Line 12:** federal AGI (Section 9.1).
2. **Additions (lines 13–18):** out-of-state municipal bond interest, A.R.S. §43-1021(3): add
   `interest_tax_exempt × (1 − az_muni_in_state_share)`; **added** assumption `az_muni_in_state_share`
   (default 0 = all out-of-state).
3. **Subtractions (lines 24–36):**
   - **Taxable Social Security** included in federal AGI (line 30; A.R.S. §43-1022(10)).
   - **25% of net long-term capital gain** from assets acquired after Dec 31, 2011 (line 24; A.R.S.
     §43-1022(22)(c)): `az_ltcg_subtraction_rate × max0(net long-term gain in federal AGI)`. Switch
     `az_ltcg_acquired_after_2011` (default `true`; if `false`, no subtraction). Note the statute treats inherited
     assets as acquired when the decedent acquired them.
   - **Government pension** (line 29a; A.R.S. §43-1022(2)–(3)): `min(pension, az_gov_pension_max)` per person,
     only if switch `az_pension_is_government` (default `false`).
   - **Senior deduction** (A.R.S. §43-1022(35), added by Laws 2026 ch. 140 §15; Form 140 "Other Subtractions",
     MCTCP worksheet): the amount deducted federally under IRC §151(d)(5)(C), i.e. `senior_deduction` from 9.10.
     **Status:** the brief asks that this be treated as unresolved. Arizona's 2025 forms included it under the
     Governor's Executive Order 2025-15 while the legislature had not acted (ADOR release, Jan 30, 2026), and
     Laws 2026 ch. 140 (signed June 13, 2026) then enacted the subtraction, retroactive to 2025. The spec makes it a
     switch `az_senior_subtraction` (default `true`, citing ch. 140), so a run can test either reading. Because the
     subtraction is "the amount deducted" federally, it becomes zero automatically after 2028.
4. **Exemptions (lines 38–41):** `az_age65_exemption × (number on the return with is65)` (A.R.S. §43-1023;
   Form 140 line 38). Blind and other exemptions out of scope.
5. **Line 42 Arizona AGI** = max0(line 12 + additions − subtractions − exemptions).

### 10.2 Arizona deduction (lines 43–44)

**Standard:** `az_standard_deduction[Y][filing]` (A.R.S. §43-1041(A), indexed "in the same manner" as the federal
basic standard deduction, §43-1041(H); no 65+ addition). **v1.2:** Laws 2026 ch. 140 set the 2025 amounts equal to the
federal 2025 basic standard deduction, so for every year `az_standard_deduction[Y][filing] =
standard_deduction[Y][filing]` (the federal basic amount, published or projected). Until ADOR publishes 2026 forms,
Arizona years from 2026 are labelled projected. Plus the **charitable increase** (§43-1041(I)):
- 2025: `az_charitable_std_increase_rate[Y] × (charitable deduction that would be allowed if itemized)`.
- 2026 onward (§43-1041(I)(2)): `min(charitable contributions, az_charitable_std_increase_cap[filing])`.
  Charitable contributions = `charity_cash`. **Reading:** QCDs are excluded (already excluded from AGI; counting them
  would double the benefit; the statute's "charitable contributions as defined in §170(c)" is a definition of the
  recipient, not of the tax treatment).

**Itemized** (A.R.S. §43-1042; Arizona may itemize regardless of the federal choice, Form 140 instructions line 43):
- Start from the federal Schedule A components of 9.8 with two Arizona substitutions:
  - medical: the full amount of `medical` (no AGI floor; §43-1042(B));
  - taxes: from 2026, `min(federal salt_deduction, az_salt_cap)` (§43-1042(D) as added by ch. 140).
    **Reading:** "that amount" is the federal SALT deduction, which includes the Arizona income tax itself; the
    spec follows the text (no subtraction of state income tax).
  - charitable: as federal (0.5% floor and ceiling, since §43-1042(A) takes deductions "allowable" under the IRC).
- §68 applies (§43-1042(A): "subject to the limits prescribed by sections 67, 68"). **Reading:** apply the federal
  §68 reduction formula to the Arizona itemized total using the *federal* `TI_pre + itemized` quantity and the
  federal 37% bracket start (Arizona has no 37% bracket of its own; the statute imports the federal limit).
- `az_itemized` = sum minus that reduction.

Deduction = `max(az_standard + charitable_increase, az_itemized)` (Form 140 line 43: "Your Arizona income tax will
be less if you take the larger").

### 10.3 Arizona tax

- **Line 45** `AZ_TI = max0(AZ_AGI − deduction)`. **Line 46** `AZ_tax = az_rate[Y] × AZ_TI` (A.R.S. §43-1011).
- Credits (dependent credit, family tax credit, property tax credit, charitable tax credits) out of scope.
- **Circularity:** the Arizona SALT deduction includes the Arizona tax. Solve `T = f(T)` by iteration from
  `T0 = f(0)`: `T_{k+1} = f(T_k)` until `|T_{k+1} − T_k| < 0.001` (converges because `|f′| ≤ az_rate < 1`).
  The federal return then uses the converged `T` in 9.8. Federal tax does not affect Arizona tax.
- `state = "none"`: `state_tax = 0`, `state_income_tax_paid = 0`.

---

## 11. Closing balances and carryforwards (step 8)

- Each account: `close[A] = grown[A] − distributions − conversions out + conversions in + deposits`
  (deposits only to cash). Closing balance becomes next year's `B0`.
- `basis8606[P] ←` Form 8606 line 14 (9.5).
- Roth ledger per owner: add this year's conversion layers; subtract withdrawals in the 7.5 order.
- Taxable `cost_basis`: + dividends (Section 4), + harvested gains (7.6), − basis of shares sold (7.7).
- Capital loss carryover (9.1 line 7).
- Death transitions (3.3) are applied after the closing balances.

---

## 12. Medicare premiums

Sources: Social Security Act §1839 (42 USC 1395r) (Part B premium, IRMAA §1839(i)); §1860D-13(a)(7) (Part D IRMAA);
20 CFR part 418 subparts B and C; CMS annual Part B premium notice (Federal Register) and Part D IRMAA fact sheet.

### 12.1 Who pays

Each person with `medicare_months[P][Y] > 0` pays, per month: Part B total premium and the Part D income-related
monthly adjustment amount (IRMAA). The Part D plan's base premium is not a federal amount; it is out of scope unless
an assumption `part_d_base_monthly` (**added**, default 0) is given.

### 12.2 Which year's income (lookback)

- Premium year `Y` uses the **tax return for `Y − irmaa_lookback_years`** (two years earlier; 20 CFR 418.1135(a)).
  (SSA uses the three-years-earlier return if the two-years-earlier one is not yet available, §418.1135(b); the
  spec always uses two.)
- MAGI = `magi_irmaa` of that return (9.6; 20 CFR 418.1010(b)(5)).
- **Filing status is the one on that earlier return** (20 CFR 418.1120(a): "We use your tax filing status and your
  modified adjusted gross income for the tax year"). So a survivor's premiums for `D+1` and `D+2` use the joint
  returns for `D−1` and `D` with the **joint** tiers, and from `D+3` the single return of `D+1` with single tiers.
- Lookback years before `first_year` use `household.prior_magi` (1.1); if absent, tier 0, flagged.
- **Life-changing event (form SSA-44, 20 CFR 418.1201–1205):** death of a spouse lets the survivor ask SSA to use
  a more recent year. Not applied to the main figures (default). The output reports
  `irmaa_ssa44_alternative[Y]` for `Y ∈ {D+1, D+2}`, computed from the single return of tax year `Y−1` if
  `Y−1 ≥ D+1`, else from tax year `D+1`; informational only, with no feedback into cash flow.

### 12.3 Tiers (boundaries)

`irmaa_tiers[premium_year][filing]` is an ordered list of `k = 0…5` with an upper bound for tiers 0–4.
Tier 0 if `MAGI ≤ upper_0`; tier `k` (1–4) if `upper_{k−1} < MAGI ≤ upper_k`; tier 5 if `MAGI ≥ lower_5`
(the top tier's lower bound is **inclusive**: "greater than or equal to", 20 CFR 418.1115(b)–(d); all others are
"greater than ... but less than or equal to"). For `mfj`, the lower tier bounds are twice the single bounds; the
top bound is separate (§1839(i)(3)(C)).

### 12.4 Amounts

- `part_b_monthly[Y][tier]`: tier 0 = the standard premium; tiers 1–5 = standard + IRMAA (CMS notice).
- `part_d_irmaa_monthly[Y][tier]` (tier 0 = 0).
- Person's premiums for `Y` = `medicare_months × (part_b_monthly + part_d_irmaa_monthly + part_d_base_monthly)`.
- Both spouses on a joint return get the same tier.
- Hold-harmless protection (§1839(f)) is out of scope.

### 12.5 Projection

- Standard Part B premium for unpublished years: `previous × (1 + medicare_growth)`, rounded to the nearest $0.10
  (42 USC 1395r(c)). Tier amounts: keep the last published ratio of each tier's premium to the standard premium
  (the law sets them as fixed shares of program cost: 35/50/65/80/85% versus 25% for the standard, §1839(i)(3)(A));
  then round to $0.10. Part D IRMAA: `previous × (1 + medicare_growth)`, rounded to $0.10.
- Tier bounds: Section 14 (CPI-U, nearest $1,000; the top bounds are frozen through premium year 2027 and indexed
  from 2028, §1839(i)(5)(C); 20 CFR 418.1115(e)(2)).

---

## 13. End of the simulation

- The simulation runs from `first_year` to `last_year`, or through the year in which the last person dies,
  whichever is earlier.
- RMDs, Medicare and tax for years after the last death are not computed (the estate and heirs are outside the
  household).

---

## 14. Parameters for years without published law

Every parameter value carries a label `published` (from a cited document) or `projected` (computed by this
section). Outputs MUST carry the labels used in each year (15.1).

### 14.1 Method (MUST)

For each indexed parameter: take the last published value as an **unrounded seed**. For each later year,
`unrounded[Y] = unrounded[Y−1] × (1 + g)` with the growth `g` named below, and `value[Y] = rounding(unrounded[Y])`.
Do not compound the rounded values. (The law indexes from a fixed base-year amount times a price-index ratio and then
rounds, which is equivalent to carrying an unrounded chain; the true base-year amounts and CPI values are not
re-derived here.)

### 14.2 Table

| Parameter | Indexed? | Growth `g` | Rounding | Source |
|---|---|---|---|---|
| `ordinary_brackets` thresholds | yes | chained CPI: `inflation − chained_cpi_gap` | down to a multiple of `bracket_rounding[filing]` (the 2026 published single amounts show the smaller single unit) | IRC §1(f)(3), (f)(7); §1(j)(3)(B) as amended by OBBBA §70101(b) |
| `cg_thresholds` | yes | chained CPI | down to $50 (all statuses) | §1(j)(5)(C) |
| `standard_deduction` | yes | chained CPI | down to $50 | §63(c)(7)(B), (c)(4) |
| `additional_std_65` | yes | chained CPI | down to $50 | §63(c)(4), (f) |
| `qcd_limit` | yes | chained CPI | nearest $1,000 | §408(d)(8)(G) |
| `capital_loss_limit` | **no** | — | — | §1211(b) |
| `senior_deduction.*` | **no**; applies 2025–2028 only | — | — | §151(d)(5)(C) |
| `nonitemizer_charitable_cap` | **no** | — | — | §170(p) |
| `salt_cap`, `salt_phasedown_threshold` | statutory schedule: 2025, 2026 fixed; ×1.01 for 2027–2029 (unrounded; statute gives no rounding); cap reverts to `salt_cap_permanent` from 2030; phase-down ends after 2029 | — | none | §164(b)(7)(A), (B)(ii) |
| `salt_floor` | **no** | — | — | §164(b)(7)(B)(iii) |
| `ss_tax.*` base amounts | **no** | — | — | §86(c) |
| `niit.threshold` | **no** | — | — | §1411(b) |
| `medical_floor_rate`, `charitable_floor_rate`, `charitable_cash_ceiling_rate`, `itemized_limit_rate` | **no** | — | — | §§213(a), 170(b)(1)(I), 170(b)(1)(G), 68 |
| `ss_cola` | projected = `assumptions.cola` | — | (benefits round down to $0.10 per 5.2) | 42 USC 415(i) |
| `irmaa_tiers` bounds | yes (top bound from 2028) | CPI-U = `inflation` | nearest $1,000; MFJ lower bounds = 2 × single | §1839(i)(5); 20 CFR 418.1115(e) |
| `part_b_monthly`, `part_d_irmaa_monthly` | projected | `medicare_growth` | nearest $0.10 | §1839(a)(3), (c) |
| `uniform_lifetime_table`, `single_life_table`, `joint_last_survivor_table` | fixed (2022 tables) | — | — | Reg. §1.401(a)(9)-9 |
| `az_standard_deduction` | yes, as federal basic | chained CPI | down to $50 (same as federal) | A.R.S. §43-1041(H) |
| `az_age65_exemption`, `az_gov_pension_max`, `az_charitable_std_increase_cap`, `az_salt_cap` | **no** | — | — | A.R.S. §§43-1023, 43-1022, 43-1041(I)(2), 43-1042(D) |
| `az_rate` | **no** (flat) | — | — | A.R.S. §43-1011 |

**Expirations and changes to apply automatically:** senior deduction ends after 2028 (and with it the Arizona
subtraction); SALT cap reverts after 2029 and its phase-down stops; the non-itemizer charitable deduction, 0.5%
floor and §68 2/37 limit start in 2026 and are permanent; the Arizona charitable standard-deduction increase switches
form in 2026; the Arizona $10,000 SALT limit starts in 2026.

**Reading (bracket indexing after OBBBA):** the 10% and 12% bracket tops index from a 2016 base and higher thresholds
from 2017 (OBBBA §70101(b)). Going forward they grow at the same yearly rate; only the rounding differs. Carrying an
unrounded chain per threshold, seeded from the last published values, reproduces this to within one rounding step.

---

## 15. Outputs and the comparison

### 15.1 Per plan, per year

Ages; filing status; parameter labels (published/projected) used; Social Security by person; RMD by account; QCDs;
plan withdrawals; conversions; harvested gains; spending withdrawals by account; every Form 1040 line in 9.1 and 9.11;
taxable SS; AGI and each MAGI; standard vs itemized and amounts; senior deduction; the QDCG worksheet lines; NIIT;
10% tax; federal tax; Arizona lines 12–46; state tax; Form 8606 lines 6–18 by person; Medicare tier and premiums by
person, with the lookback year and filing status used; closing balances, bases and Roth ledger; unfunded spending;
flags (`action_clamped`, `irmaa_lookback_assumed`, charitable excess, etc.).

### 15.2 Deflation

`real(x, Y) = x / (1 + inflation)^(Y − first_year)` for an amount in year `Y` (flows during `Y` and balances on
Dec 31 of `Y` use the same exponent). "First-year dollars" means dollars of `first_year`.

### 15.3 Lifetime totals and end wealth

- `lifetime_tax = Σ_Y (federal_tax + state_tax)`, nominal and real.
- `lifetime_medicare = Σ_Y medicare_premiums`, nominal and real.
- `end_wealth` on Dec 31 of the final simulated year:
  `(Σ traditional_ira + 401k + inherited_ira) × (1 − heirs_tax_rate) + Σ roth_ira + inherited_roth_ira + taxable +
  cash`. Taxable accounts are counted at full value (heirs receive a basis step-up, IRC §1014). Remaining Form 8606
  basis is ignored in this formula (switch `heirs_credit_8606_basis`, default `false`; if `true`, heirs' tax applies
  to `balance − basis8606`). Nominal and real.
- Plan comparison: differences of these totals, plan minus baseline.

---

## 16. Worked mini-examples

Each example states the parameter values it assumes. Values marked *illustrative* are made up for easy arithmetic and
are **not** the published amounts; values marked *table* come from the cited table.

### Example 1 — Pro-rata with basis, two years

Person P, age 60 (no RMD), `return = 0` for clarity. `traditional_ira` A = 90,000 and B = 10,000; `basis8606 = 20,000`;
a `401k` of 200,000 (ignored by Form 8606). Plan: convert 30,000 from A in each of two years. No other IRA
distributions.

Year 1: line 6 = 70,000 (Dec 31 value after the conversion); line 7 = 0; line 8 = 30,000; line 9 = 100,000;
line 10 = 20,000 / 100,000 = 0.200; line 11 = 6,000 nontaxable; line 18 = 24,000 taxable (Form 1040 line 4b);
line 14 = 20,000 − 6,000 = 14,000.

Year 2: line 6 = 40,000; line 8 = 30,000; line 9 = 70,000; line 10 = 14,000 / 70,000 = 0.200; nontaxable 6,000;
taxable 24,000; line 14 = 8,000.

Check: if the 401(k) had been rolled into an IRA before Year 1, line 9 = 300,000 and only 2,000 of the first 30,000
would be nontaxable. The 401(k) matters only if it is an IRA on Dec 31.

### Example 2 — RMD first, QCD counts, then conversion

P born 1951 (applicable age 73), age 75 in 2026. One `traditional_ira`, Dec 31 2025 balance 265,000; basis 0;
`return = 5%`. Plan for 2026: QCD 4,000 and conversion 50,000. *Table:* Uniform Lifetime divisor at 75 = 24.6.

- RMD = 265,000 / 24.6 = 10,772.36.
- Growth: 265,000 × 1.05 = 278,250.
- a. QCD 4,000 (P is over 70½) → remaining RMD = 6,772.36.
- b. Distribute 6,772.36 (cash inflow).
- d. Convert 50,000.
- Dec 31 IRA = 278,250 − 4,000 − 6,772.36 − 50,000 = 217,477.64.
- Form 1040: line 4a = 60,772.36; line 4b = 56,772.36 (QCD excluded). Form 8606 line 7 = 6,772.36 (QCD excluded);
  with zero basis nothing is nontaxable.
- If the plan had asked to convert the entire 278,250, only 278,250 − 4,000 − 6,772.36 = 267,477.64 could be
  converted (`action_clamped`).

### Example 3 — Inherited IRA, owner died after RBD, minus-one method

Owner born 1945 died 2022 (past RBD). Beneficiary class `designated`, born 1975. *Table* (Single Life Table, Reg.
§1.401(a)(9)-9(b)): age 48 → 38.1; age 77 → 13.3.

- Beneficiary's age in 2023 (= D+1) is 48: `LE_b[2023] = 38.1`.
- Owner's age in 2022 is 77: `LE_o[2022] = 13.3`, so `LE_o[2023] = 12.3`. Longer = 38.1 (beneficiary).
- 2024: 37.1; 2025: 36.1; 2026: 35.1. (2023 and 2024 RMDs waived by Notice 2024-35; the divisor still steps down.)
- 2026 RMD with a Dec 31 2025 balance of 351,000: 351,000 / 35.1 = 10,000.00.
- 2032 (= D+10): the entire balance must be distributed. Not subject to the 10% tax.
- Contrast: had the owner died **before** the RBD, there would be no annual RMD; only the 2032 deadline.

### Example 4 — Social Security "torpedo"

MFJ, `SS_total = 40,000`, no tax-exempt interest, other income (IRA) 30,000. *Statutory:* base 32,000, adjusted
base 44,000, rates ½ and 85%. *Illustrative:* the couple is in the 12% bracket throughout.

- provisional = 30,000 + 20,000 = 50,000 > 44,000.
- taxable SS = min(34,000, 0.85 × 6,000 + min(20,000, 0.5 × 12,000)) = 5,100 + 6,000 = 11,100.
- Add 1,000 of IRA withdrawal: provisional 51,000 → 0.85 × 7,000 + 6,000 = 11,950 (+850).
- Taxable income rises by 1,000 + 850 = 1,850; extra tax = 12% × 1,850 = 222, an effective 22.2% marginal rate on
  the 1,000.

### Example 5 — Senior deduction phase-out, per person

MFJ, both 65+, `magi_senior = 170,000`. *Statutory:* amount 6,000 per person, threshold 150,000 (joint), rate 6%.

- reduction = 0.06 × 20,000 = 1,200.
- Each spouse: 6,000 − 1,200 = 4,800. Total 9,600 (not 12,000 − 1,200).
- Marginal effect: each extra dollar of MAGI removes 0.12 of deduction; both amounts reach zero at MAGI 250,000.
- If only one spouse is 65+: 4,800 total; zero at 250,000 as well.
- In 2029 the deduction is zero regardless (expired).

### Example 6 — 0% gains pushed into 15%

MFJ. *Illustrative:* `zero_max = 100,000`, `fifteen_max = 600,000`; ordinary brackets: 12% on all ordinary income
in this range.

Before: ordinary taxable income (L5) = 80,000; long-term gain 30,000; TI = 110,000.
L7 = min(110,000, 100,000) = 100,000; L8 = min(80,000, 100,000) = 80,000; L9 = 20,000 at 0%;
L17 = 10,000 at 15% = 1,500.

Add a 10,000 Roth conversion: L5 = 90,000; TI = 120,000; L9 = 100,000 − 90,000 = 10,000 at 0%; L17 = 20,000 at 15%
= 3,000. Extra tax = 12% × 10,000 + (3,000 − 1,500) = 1,200 + 1,500 = 2,700: 27% on the 10,000 conversion, though
the bracket says 12%.

### Example 7 — IRMAA two-year lookback across a death

MFJ couple; spouse D dies in 2026. *Illustrative tiers for every premium year:* single tier-0 upper 100,000,
tier-1 upper 125,000, tier-2 upper 160,000; joint = double (200,000; 250,000; 320,000). MAGI: 2025 joint return
210,000; 2026 joint return 230,000; 2027 single return 120,000.

| Premium year | Tax year used | Filing status on that return | MAGI | Tier |
|---|---|---|---|---|
| 2027 | 2025 | mfj | 210,000 | 1 (200,000 < 210,000 ≤ 250,000) |
| 2028 | 2026 | mfj | 230,000 | 1 |
| 2029 | 2027 | single | 120,000 | 1 (100,000 < 120,000 ≤ 125,000) |

- 2026 premiums (both spouses, 12 months each) use the 2024 return.
- Had 2028 wrongly used the single table with 230,000, it would be above tier 2 — the lookback uses the filing status
  of the earlier return, not the survivor's current status.
- Boundary: a 2025 MAGI of exactly 200,000 is tier 0 (`≤` upper bound).
- The SSA-44 alternative for 2027 (computed from the 2027 single return: 120,000 → tier 1) and 2028 (same) is
  reported but not used.

### Example 8 — Survivor benefit and the widow's limit

D: PIA 2,000, FRA 67 (born 1960). S: own benefit 1,200, at survivor FRA when D dies. COLA 0 for clarity.
*Statutory:* early reduction 5/9% for 36 months then 5/12%; DRC 2/3% per month; RIB-LIM 82.5%.

- D claimed at 62 (60 months early): reduction = 36 × 5/9% + 24 × 5/12% = 20% + 10% = 30% → own[D] = 1,400.
  Survivor base = 2,000 (PIA; early reduction not carried); no survivor reduction (S at FRA) → 2,000; RIB-LIM:
  min(2,000, max(1,400, 0.825 × 2,000 = 1,650)) = 1,650. S is paid max(1,200, 1,650) = 1,650.
- D claimed at 70 (36 months late): own[D] = 2,000 × 1.24 = 2,480; survivor = 2,480; S is paid 2,480.
- D claimed at 62 and S takes the survivor benefit at 62 with survivor FRA 67 (84 months between 60 and 67; 60
  months early): reduction = 28.5% × 60/84 = 20.357%; widow = 2,000 × 0.79643 = 1,592.86; RIB-LIM cap 1,650 does not
  bind → 1,592.80 (dime) → paid 1,592 (dollar) if larger than S's own.

### Example 9 — §68 2/37 limit

MFJ 2026, AGI 1,000,000, no senior deduction, `itemized_pre = 60,000`. *Illustrative:* 37% bracket starts at 750,000.

- TI_pre + itemized_pre = 1,000,000; excess over 750,000 = 250,000; lesser of 60,000 and 250,000 = 60,000.
- reduction = 2/37 × 60,000 = 3,243.24; itemized = 56,756.76.

### Example 10 — SALT phase-down

MFJ 2026. *Statutory:* cap 40,400, threshold 505,000, rate 30%, floor 10,000. `magi_salt = 600,000`; taxes paid 35,000.

- cap = max(10,000, 40,400 − 0.30 × 95,000) = max(10,000, 11,900) = 11,900; deduction = min(35,000, 11,900) = 11,900.
- At MAGI 610,000: 40,400 − 31,500 = 8,900 → floor → 10,000.
- In 2030: cap = the permanent amount, no phase-down.

---

## 17. The "explain trace"

Goal: for each year, split the difference between two plans (plan B minus baseline A) in
`federal_tax + state_tax + medicare_premiums` into parts named after rules, such that the parts sum **exactly** to the
total.

### 17.1 Inputs to the year's tax computation

For a year, collect the **independent drivers** of that year's tax, in form order:

1. wages; 2. taxable interest; 3. dividends (ordinary and qualified); 4. traditional IRA distributions (gross, with
Form 8606 lines 6–8); 5. QCDs; 6. Roth distributions (taxable earnings); 7. 401(k) distributions and conversions;
8. pensions/annuities; 9. Social Security benefits; 10. realized capital gains (incl. harvested); 11. rental;
12. itemized inputs; 13. state tax inputs (none beyond the above); 14. the Medicare lookback MAGI and its filing status.

### 17.2 Level 1 — driver substitution (telescoping)

Start from plan A's year. For `k = 1 … 14`, replace driver `k` with plan B's value (keeping drivers `k+1…` at A's
values) and recompute the whole year (Sections 9, 10, 12, holding cash-flow withdrawals at the values given by the
drivers, i.e. no re-solve). `part_k = total(after k) − total(after k−1)`. After step 14 the computation equals plan B
exactly, so `Σ part_k = total_B − total_A`.

### 17.3 Level 2 — rule attribution within a driver step

Within step `k`, list the **derived quantities** in form order:
R1 taxable Social Security (9.3); R2 Form 8606 nontaxable part (9.5); R3 AGI; R4 senior deduction (9.10);
R5 SALT cap phase-down (9.8); R6 charitable floor and §68 (9.8); R7 standard-vs-itemized choice (9.9);
R8 regular tax incl. the QDCG worksheet split (9.11); R9 NIIT (9.12); R10 10% tax (9.12); R11 Arizona tax (10);
R12 Medicare tier (12).

Compute the step-`k` total with all derived quantities frozen at their "before step k" values except the driver's
direct effect on its own income line, AGI and taxable income ("direct effect", charged at the ordinary/QDCG rates in
force before the step). Then unfreeze R1, R2, … R12 one at a time in that order; each increment is that rule's part.
The increments telescope to `part_k`, so the level-2 parts also sum exactly to the total.

Report each year as a table `driver × rule`, plus row and column totals. Example reading: "Conversion 10,000 → direct
1,200; R1 torpedo +222; R4 senior deduction loss +144; R8 0%→15% gains +1,500; R12 (in year Y+2) IRMAA tier +…".

Medicare: the effect of year `Y` income on premiums appears in year `Y+2`'s trace under driver 14, labelled with the
source year.

---

## Appendix A — Parameters

Values per year come from the parameter table; this appendix names each and its source. "Statute" means the value is
written in the cited section; "annual" means the IRS/SSA/CMS/ADOR document for that year.

### A.1 Federal income tax

| Name | Meaning | Source |
|---|---|---|
| `ordinary_brackets[year][filing]` | list of (upper bound, rate) for taxable income | IRC §1(j)(2) (rates made permanent by OBBBA §70101); annual Rev. Proc. (2025: Rev. Proc. 2024-40 §2.01 as modified by OBBBA; 2026: Rev. Proc. 2025-32 §4.01) |
| `bracket37_start[year][filing]` | lower edge of the 37% bracket (derived from `ordinary_brackets`) | same |
| `bracket_rounding[filing]` | rounding unit for projected thresholds | IRC §1(f)(7); §1(j)(3)(B)(ii) |
| `cg_thresholds[year][filing].zero_max, .fifteen_max` | top of the 0% and 15% capital-gain rate ranges | IRC §1(h)(1), §1(j)(5)(B); annual Rev. Proc. |
| `cg_rate_15`, `cg_rate_20` | capital-gain rates | IRC §1(h)(1)(C), (D) |
| `standard_deduction[year][filing]` | basic standard deduction | IRC §63(c)(2), (c)(7) (OBBBA §70102); annual Rev. Proc. |
| `additional_std_65[year][married|unmarried]` | additional amount per person 65+ | IRC §63(c)(3), (f); annual Rev. Proc. |
| `senior_deduction.amount`, `.threshold[filing]`, `.phaseout_rate`, `.first_year`, `.last_year` | enhanced deduction for seniors | IRC §151(d)(5)(C) (OBBBA §70103); Schedule 1-A Part V |
| `nonitemizer_charitable_cap[filing]`, `nonitemizer_charitable_first_year` | non-itemizer charitable deduction | IRC §170(p) (OBBBA §70424) |
| `charitable_floor_rate`, `charitable_floor_first_year` | 0.5% floor | IRC §170(b)(1)(I) (OBBBA §70425) |
| `charitable_cash_ceiling_rate` | 60% of contribution base for cash | IRC §170(b)(1)(G) |
| `medical_floor_rate` | 7.5% of AGI | IRC §213(a) |
| `salt_cap[year]`, `salt_cap_permanent`, `salt_phasedown_threshold[year]`, `salt_phasedown_rate`, `salt_floor`, `salt_phasedown_last_year` | SALT limitation | IRC §164(b)(6), (b)(7) (OBBBA §70120) |
| `itemized_limit_rate`, `itemized_limit_first_year` | §68 2/37 reduction | IRC §68 (OBBBA §70111) |
| `ss_tax.base_amount[filing]`, `.adjusted_base_amount[filing]`, `.first_rate`, `.second_rate` | taxation of benefits | IRC §86(a)–(c); Pub 915 |
| `niit.rate`, `niit.threshold[filing]` | net investment income tax | IRC §1411(a), (b); Form 8960 |
| `early_withdrawal_rate` | 10% additional tax | IRC §72(t)(1); Form 5329 |
| `capital_loss_limit[filing]` | deductible net capital loss | IRC §1211(b) |
| `qcd_limit[year]` | per-person annual QCD cap | IRC §408(d)(8)(A), (G); annual IRS notice (2026: Notice 2025-67) |

### A.2 Distributions

| Name | Meaning | Source |
|---|---|---|
| `rmd_applicable_age` (by birth cohort) | RMD starting age | IRC §401(a)(9)(C)(v); Reg. §1.401(a)(9)-2(b); proposed §1.401(a)(9)-2(b)(2)(v) (89 FR 58644) for 1959 |
| `uniform_lifetime_table[age]` | owner divisor | Reg. §1.401(a)(9)-9(c) (Table 2) |
| `joint_last_survivor_table[age][age]` | owner divisor, spouse > 10 years younger | Reg. §1.401(a)(9)-9(d) |
| `single_life_table[age]` | beneficiary divisor | Reg. §1.401(a)(9)-9(b) (Table 1) |
| `minor_majority_age` | 21 | Reg. §1.401(a)(9)-4(e)(3) |
| `inherited_10_year`, `inherited_5_year` | deadline years | IRC §401(a)(9)(H)(i), (B)(ii) |
| `inherited_rmd_waiver_years` | 2021–2024 | Notices 2022-53, 2023-54, 2024-35 |
| `edb_age_gap` | "not more than 10 years younger" | IRC §401(a)(9)(E)(ii)(V) |
| `roth_five_year` | five-taxable-year period | IRC §408A(d)(2)(B), (d)(3)(F) |

### A.3 Social Security

| Name | Meaning | Source |
|---|---|---|
| `ss_fra_months[birth_year]` | full retirement age | SSA §216(l)(1); 20 CFR 404.409 |
| `ss_survivor_fra_months[birth_year]` | survivor FRA | SSA §216(l)(1); POMS RS 00615.301 |
| `ss_min_claim_months` (744), `ss_max_drc_months` (840) | earliest claim, latest credit | SSA §202(a), §202(w); 20 CFR 404.313 |
| `ss_early_rate_1`, `ss_early_rate_2` | 5/9% and 5/12% per month | SSA §202(q)(1), (9); 20 CFR 404.410 |
| `ss_spousal_rate_1` | 25/36% per month | SSA §202(q)(1); 20 CFR 404.410 |
| `ss_drc_monthly_rate` | 2/3% per month (born 1943+) | SSA §202(w)(6); 20 CFR 404.313 |
| `ss_spousal_rate` | one-half of the worker's PIA | SSA §202(b)(2), (c)(3) |
| `ss_survivor_max_reduction` (28.5%), `ss_survivor_min_months` (720) | widow(er) reduction at 60 | SSA §202(q)(1)(B); 20 CFR 404.410(b) |
| `ss_rib_lim_rate` | 82.5% | SSA §202(e)(2)(D), (f)(3)(D) |
| `ss_cola[year]` | COLA | 42 USC 415(i); annual SSA notice in the Federal Register |

### A.4 Medicare

| Name | Meaning | Source |
|---|---|---|
| `irmaa_lookback_years` | 2 | 20 CFR 418.1135(a) |
| `irmaa_tiers[premium_year][filing]` | MAGI bounds | SSA §1839(i)(2)–(5); 20 CFR 418.1115; CMS annual notice |
| `part_b_monthly[premium_year][tier]` | standard premium + IRMAA | SSA §1839(a), (i)(3); CMS annual Part B notice (Federal Register) |
| `part_d_irmaa_monthly[premium_year][tier]` | Part D IRMAA | SSA §1860D-13(a)(7); CMS annual announcement |
| `medicare_age` | 65 | SSA §226(a) |

### A.5 Arizona

| Name | Meaning | Source |
|---|---|---|
| `az_rate[year]` | flat rate | A.R.S. §43-1011; Form 140 line 46 |
| `az_standard_deduction[year][filing]` | standard deduction | A.R.S. §43-1041(A), (H) (Laws 2026 ch. 140 §16); Form 140 line 43 |
| `az_charitable_std_increase_rate[year]` (≤2025) | % of charitable deduction | A.R.S. §43-1041(I)(1); Form 140 line 44 |
| `az_charitable_std_increase_cap[filing]` (2026+) | cap on the increase | A.R.S. §43-1041(I)(2) |
| `az_age65_exemption` | per-person exemption | A.R.S. §43-1023; Form 140 line 38 |
| `az_gov_pension_max` | per-person government pension subtraction | A.R.S. §43-1022; Form 140 line 29a |
| `az_ltcg_subtraction_rate` | share of net LTCG subtracted | A.R.S. §43-1022(22)(c); Form 140 line 24 |
| `az_salt_cap` (2026+) | Arizona SALT limit | A.R.S. §43-1042(D) (Laws 2026 ch. 140 §17) |

### A.6 Assumptions (inputs, not law)

`return`, `inflation`, `chained_cpi_gap`, `cola`, `medicare_growth`, `heirs_tax_rate`, `survivor_spending_ratio`,
`part_d_base_monthly`, `az_muni_in_state_share`.

---

## Appendix B — Switches (defaults in bold)

| Switch | Default | Section |
|---|---|---|
| `use_tax_table` | **false** | 0.3 |
| `defer_first_rmd` | **false** | 6.1 |
| `spouse_is_sole_beneficiary` | **true** (mfj) | 6.2 |
| `edb_elects_10_year` | **false** | 6A.4 |
| `spouse_401k_to_ira` | **true** | 3.3 |
| `community_property` | **false** (v1.2: titling decides; this only covers untitled joint accounts) | 3.3 |
| `ss_dollar_rounding` | **true** | 5.6 |
| `round_8606_ratio_3dp` | **false** | 9.5 |
| `annuity_is_nii` | **true** | 9.12 |
| `az_senior_subtraction` | **true** | 10.1 |
| `az_ltcg_acquired_after_2011` | **true** | 10.1 |
| `az_pension_is_government` | **false** | 10.1 |
| `az_assume_future_conformity` | **true** | 10 |
| `heirs_credit_8606_basis` | **false** | 15.3 |

---

## Appendix C — Ambiguities and readings adopted

1. **Within-year timing** — law is silent; convention: growth on the opening balance, all transactions Dec 31
   (Section 2). Chosen to remove circularity and make Form 8606 line 6 and age tests exact.
2. **Death timing** — person treated as alive all of the year of death; transitions at Dec 31 (3.1).
3. **Born day** — 15th of `born_month` (1.1).
4. **1959 RMD age** — 73 per proposed reg. (6.1).
5. **First RMD deferral** — not deferred by default (6.1).
6. **Joint Life table** — needs beneficiary data the input lacks; spouse assumed sole beneficiary (6.2).
7. **Derived RBD** — death in the RBD year counts as after April 1 (6A.1).
8. **EDB default** — life-expectancy method (Reg. §1.401(a)(9)-3(c)(5)) (6A.4).
9. **Successor beneficiary deadline** — min(existing, 10 years after first beneficiary's death) (6A.6).
10. **IRA RMD aggregation** — remaining RMD taken pro rata across the person's IRAs (6.3).
11. **Form 8606 ratio** — unrounded (9.5).
12. **Charitable floor vs ceiling order** — floor first (9.8).
13. **State income tax in SALT** — current-year AZ liability treated as paid in the year (9.8).
14. **NIIT allocable deductions** — ignored (9.12).
15. **Inherited IRAs in the spending pool** — included with traditional (8.2).
16. **Roth contribution basis** — added optional input, default 0 (1.2).
17. **Survivor Social Security timing** — survivor benefit taken as soon as available; paid the larger (5.5).
18. **SS month attribution** — benefits counted by month of entitlement, not payment (5.6).
19. **PIA before 62** — COLA'd instead of wage-indexed (1.1).
20. **IRMAA first two years** — `prior_magi` or tier 0 (12.2). **SSA-44** — reported, not applied (12.2).
21. **Arizona senior subtraction** — the brief calls it unresolved; enacted text found (Laws 2026 ch. 140,
    A.R.S. §43-1022(35)); switch, default on (10.1).
22. **Arizona SALT includes AZ income tax** and is solved as a fixed point (10.2–10.3).
23. **Arizona §68** — federal formula applied to the Arizona itemized total (10.2).
24. **Arizona charitable increase excludes QCDs** (10.2).
25. **Arizona future conformity** assumed (10).
26. **Projection** — unrounded chain from the last published value (14.1).
27. **Spending solve** — bisection to half a cent (8.3).
28. **Average-cost basis** for taxable sales; all gains long-term (7.7, 1.2).

---

## Appendix D — Out of scope

AMT (IRC §55; OBBBA changed its phase-out; may bind for large SALT or gains — flag rather than compute);
payroll taxes on wages; the Social Security retirement earnings test (SSA §203(b), 20 CFR 404.415/404.430) for
wages before FRA; the still-working exception for 401(k) RMDs; Social Security taxation lump-sum election;
government pension offset/WEP (repealed by the Social Security Fairness Act, 2025, for benefits after Dec 2023);
head of household, married filing separately and qualifying surviving spouse; dependents and all credits (federal
and Arizona); ACA premium tax credits (MAGI is reported only); qualified business income, tips, overtime and car-loan
deductions; short-term gains, collectibles, §1250 recapture; capital-loss and charitable carryforward across years
other than the capital-loss carryover in 9.1; inherited IRA basis; SECURE 2.0 §327 spousal election; Part B hold
harmless; Medicare before 65; Part D base premiums (unless assumed); estate and inheritance taxes; other states;
underpayment penalties and timing of tax payments; disability; SEPP and other §72(t) exceptions.
