# Scenario engine contract

Two engines implement `spec/RULES.md`: the MoneyGuide scenario runner (TypeScript, `~/moneyguide`) and the
clean-room engine in this folder (Python, written without ever reading MoneyGuide). Both take the same input and
produce the same output, so they can be compared field by field on thousands of generated households.

## Input

One JSON object, exactly the format of RULES.md Section 1:

```json
{
  "household": {"filing": "mfj", "state": "AZ", "people": [...], "accounts": [...], "income": [...],
                "spending_need": 90000, "itemized": {"salt_other": 0, "mortgage_interest": 0, "medical": 0, "charity_cash": 0},
                "prior_magi": {"2024": {"magi": 150000, "filing": "mfj"}, "2025": {"magi": 160000, "filing": "mfj"}}},
  "plans": [{"name": "A", "actions": []}, {"name": "B", "actions": [{"type": "roth_conversion", "from": "ira1", "amount": 50000, "years": [2026, 2027]}]}],
  "events": [{"type": "death", "person": "p2", "year": 2035}],
  "assumptions": {"return": 0.05, "inflation": 0.025, "first_year": 2026, "last_year": 2050, "heirs_tax_rate": 0.24,
                  "switches": {}}
}
```

Actions and events are objects with a `type` field (`roth_conversion`, `qcd`, `withdrawal`, `harvest_gains`,
`claim_social_security`, `death`) and the fields RULES.md 1.5 gives them. `years` is a list of years.

## Output

```json
{
  "plans": {
    "A": {
      "years": [
        {
          "year": 2026, "filing": "mfj", "alive": {"p1": true}, "age": {"p1": 70},
          "projected": false,
          "social_security": {"p1": 0.0},
          "rmd": {"ira1": 0.0},
          "qcd": {"ira1": 0.0},
          "conversion": {"ira1": 0.0},
          "distributions": {"ira1": 0.0},
          "sales": {"tax1": 0.0},
          "income": {"wages": 0.0, "pension": 0.0, "annuity_taxable": 0.0, "interest_taxable": 0.0,
                     "interest_tax_exempt": 0.0, "rental": 0.0, "ordinary_dividends": 0.0,
                     "qualified_dividends": 0.0, "capital_gain": 0.0, "ira_taxable": 0.0},
          "taxable_ss": 0.0, "agi": 0.0, "magi_irmaa": 0.0,
          "deduction_type": "standard", "deduction": 0.0, "senior_deduction": 0.0,
          "taxable_income": 0.0, "regular_tax": 0.0, "niit": 0.0, "additional_10pct": 0.0,
          "federal_tax": 0.0, "state_tax": 0.0,
          "medicare": {"p1": {"tier": 0, "premium": 0.0, "lookback_year": 2024}},
          "medicare_total": 0.0,
          "balances": {"ira1": 0.0},
          "basis8606": {"p1": 0.0},
          "unfunded_spending": 0.0,
          "flags": []
        }
      ],
      "totals": {"lifetime_tax": 0.0, "lifetime_tax_real": 0.0, "lifetime_medicare": 0.0,
                 "lifetime_medicare_real": 0.0, "end_wealth": 0.0, "end_wealth_real": 0.0}
    }
  }
}
```

Field meanings:

- `distributions`: every gross dollar out of each account that year (RMD, QCD, conversions, plan withdrawals,
  spending withdrawals). `sales`: proceeds sold from each taxable account.
- `deduction`: Form 1040 line 12 (standard, plus the non-itemizer charitable deduction where it applies, or
  itemized), not including the senior deduction, which is `senior_deduction`.
- `regular_tax`: Form 1040 line 16 (after the capital gains worksheet). `federal_tax` = `regular_tax` + `niit` +
  `additional_10pct`.
- `medicare`: one entry per living person enrolled that year; `premium` is the year's Part B + Part D IRMAA total.
- `projected`: true if any parameter used that year was projected (RULES.md Section 14).
- Every dollar figure rounded to cents. Years stop after the last person's death (RULES.md Section 13).

Two engines agree when every numeric field matches within $1.00 and every string and boolean is equal.

## Command

```bash
python3 -I checks/cleanroom/engine.py scenario.json > result.json
```
