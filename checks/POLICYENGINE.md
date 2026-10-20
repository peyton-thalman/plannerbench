# PolicyEngine-US check

Every tax answer recomputed by [PolicyEngine-US](https://github.com/PolicyEngine/policyengine-us), an open-source tax model this project didn't write. It's an outside reading of the same IRS rules.

**PASS: 1,600/1,600 agree within $2** (100.00%). Households where PolicyEngine found alternative minimum tax: 0.

| Task | Agree | What PolicyEngine computes |
|---|---|---|
| bracket_room | 200/200 | taxable income → room to the bracket top |
| conversion_all_in | 200/200 | tax part (Medicare part checked against CMS elsewhere) |
| federal_tax | 200/200 | income tax before credits |
| senior_phaseout | 200/200 | income tax before credits |
| tax_torpedo | 200/200 | tax with − without the conversion |
| taxable_ss | 200/200 | taxable Social Security |
| widow_all_in | 200/200 | tax part (Medicare part checked against CMS elsewhere) |
| widow_penalty | 200/200 | survivor's tax − couple's tax |

Not covered: rmd, ss_claim, irmaa and the compliance tasks (PolicyEngine doesn't model them). Those rest on the golden set and the two-way check.

