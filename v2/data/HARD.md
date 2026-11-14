# PlannerBench v2 hard tier

42 questions, 6 per family. Built by `v2/build_hard.py`. Every key is the Planning Engine's 2026 row and matched the clean-room engine within $1 on tax, AGI, MAGI, taxable Social Security, the senior deduction and every RMD.

| Family | What interacts | Published source | Tolerance |
|---|---|---|---|
| `irmaa_headroom` | IRMAA two years out; muni interest counts, only taxable Social Security counts | CMS 2026 Part B/IRMAA fact sheet (MAGI = AGI + tax-exempt interest; a tier starts above its threshold); IRS Pub 915 | ±$2 |
| `conv_cost_az` | conversion + Social Security torpedo + senior phase-out + Arizona | Rev. Proc. 2025-32; Schedule 1-A Part V; IRS Pub 915; A.R.S. §§43-1011, 43-1022(10) and (35), 43-1023, 43-1041 (Laws 2026 ch. 140) | ±$5 |
| `ss_muni_qcd` | taxable Social Security inside the phase-in; muni interest counts, the QCD doesn't | IRS Pub 915 Worksheet 1 (tax-exempt interest is added on line 3); IRC §408(d)(8) (a QCD is not in income) | ±$2 |
| `inherited_rmd` | annual RMD inside the 10-year window; longer of beneficiary's and owner's remaining life expectancy; no annual RMD if the owner died before the required beginning date | IRC §401(a)(9)(B), (H); Treas. Reg. §1.401(a)(9)-5(d); IRS Pub 590-B Table I (Single Life) | ±$2 |
| `qcd_rmd_tax` | RMD from the table, QCD counts toward it and stays out of income, then the usual tax stack | IRS Pub 590-B Table III (Uniform Lifetime) and QCD rules; IRC §408(d)(8); Pub 915; Rev. Proc. 2025-32; Schedule 1-A Part V | ±$5 |
| `widow_first_year` | single brackets + lost Social Security check + one senior deduction + RMD on the survivor's age | IRS Pub 590-B Table III and spousal rollover; Pub 915; Rev. Proc. 2025-32; Schedule 1-A Part V | ±$5 |
| `az_tax` | Arizona: Social Security out, senior deduction out, age-65 exemption, federal basic standard deduction, 2.5% | A.R.S. §43-1011 (2.5% flat rate), §43-1022(10) and (35), §43-1023 ($2,100 age-65 exemption), §43-1041 (Laws 2026 ch. 140); Pub 915; Schedule 1-A Part V | ±$5 |

## One example per family

**irmaa_headroom-00** (answer 38220)

> Use 2026 federal tax law (IRS Rev. Proc. 2025-32 and the One Big Beautiful Bill Act, including the $6,000 senior deduction). Standard deduction, no credits. Use the 2026 CMS Part B premiums and IRMAA tiers. Tamsin (born January 1960) and Mateo (born January 1959) are married, file jointly and are both enrolled in Medicare Part B. For 2026 they expect a pension of $54,000, traditional IRA withdrawals of $78,500, Social Security of $25,200 (Tamsin) and $21,600 (Mateo), and $7,500 of tax-exempt municipal bond interest. No other income. Medicare sets Part B premiums from the return two years earlier, so 2026 income sets 2028 premiums; assume the 2026 tiers still apply in 2028. What is the largest Roth conversion, in whole dollars, they can add in 2026 without raising their 2028 Part B premium above what it would be with no conversion? End your reply with a line of the form "ANSWER: <number>" with no $ sign or commas.

**conv_cost_az-00** (answer 16639)

> Use 2026 federal tax law (IRS Rev. Proc. 2025-32 and the One Big Beautiful Bill Act, including the $6,000 senior deduction). Standard deduction, no credits. They live in Arizona; use Arizona income tax law for 2026 as amended by Laws 2026, chapter 140 (which lets Arizona filers subtract the federal senior deduction). Odette (born January 1960) and Emeric (born January 1957) are married, file jointly and are both enrolled in Medicare Part B. In 2026 they have a pension of $53,500 and Social Security of $28,800 (Odette) and $25,200 (Emeric), and no other income. They are considering converting $80,000 from a traditional IRA to a Roth IRA in 2026. How much more total income tax, federal plus Arizona, would they owe for 2026 with the conversion than without it? Round to the nearest dollar. End your reply with a line of the form "ANSWER: <number>" with no $ sign or commas.

**ss_muni_qcd-00** (answer 6707)

> Use 2026 federal tax law (IRS Rev. Proc. 2025-32 and the One Big Beautiful Bill Act, including the $6,000 senior deduction). Standard deduction, no credits. Freya (born January 1950) is single. In 2026 total Social Security benefits are $33,000. Freya takes $21,097 out of a traditional IRA during the year; $9,500 of that goes straight from the IRA custodian to a qualified charity as a qualified charitable distribution and the rest comes to the household. They also receive $8,500 of tax-exempt municipal bond interest. No other income. How many dollars of their 2026 Social Security benefits are taxable? Round to the nearest dollar. End your reply with a line of the form "ANSWER: <number>" with no $ sign or commas.

**inherited_rmd-00** (answer 9960)

> Marisol, born in January 1964, is the sole beneficiary of a traditional IRA inherited from their father, who was born in January 1938 and died in 2021 at age 83, after starting required minimum distributions. Marisol is an ordinary adult-child beneficiary (not disabled or chronically ill) and has taken every distribution required so far. The inherited IRA was worth $248,000 on December 31, 2025. Under the SECURE Act and the final IRS regulations (and IRS Pub 590-B), what is the minimum Marisol must withdraw from the inherited IRA for 2026? Give 0 if no withdrawal is required for 2026. Round to the nearest dollar. End your reply with a line of the form "ANSWER: <number>" with no $ sign or commas.

**qcd_rmd_tax-00** (answer 9614)

> Use 2026 federal tax law (IRS Rev. Proc. 2025-32 and the One Big Beautiful Bill Act, including the $6,000 senior deduction). Standard deduction, no credits. Odette, born in January 1943, is single. Odette's only traditional IRA was worth $1,590,000 on December 31, 2025. In 2026 Odette takes exactly the required minimum distribution from it and no more, sending $53,500 of that directly from the IRA to a qualified charity as a qualified charitable distribution. Odette also has Social Security benefits of $36,000 and a pension of $24,000. No other income. What is Odette's total 2026 federal income tax? Round to the nearest dollar. End your reply with a line of the form "ANSWER: <number>" with no $ sign or commas.

**widow_first_year-00** (answer 916)

> Use 2026 federal tax law (IRS Rev. Proc. 2025-32 and the One Big Beautiful Bill Act, including the $6,000 senior deduction). Standard deduction, no credits. Compare two versions of 2026 for the same household, using 2026 law for both. Version 1: Tamsin (born January 1945) and Hollis (born January 1941) are married and file jointly. Tamsin's traditional IRA was worth $220,000 and Hollis's $790,000 on December 31, 2025; each takes exactly their own required minimum distribution. Social Security is $25,800 (Tamsin) and $34,800 (Hollis), and they have $6,500 of taxable interest. Version 2: Hollis died in 2025. Tamsin files as single for 2026, rolled Hollis's IRA into her own before December 31, 2025 (so her IRA held $1,010,000 on that date) and takes exactly her required minimum distribution, and receives the larger of the two Social Security benefits instead of her own, with the same taxable interest. No other income in either version. How many dollars more federal income tax does Tamsin owe in version 2 than the couple owes in version 1? Give a negative number if she owes less. Round to the nearest dollar. End your reply with a line of the form "ANSWER: <number>" with no $ sign or commas.

**az_tax-00** (answer 1892)

> Use 2026 federal tax law (IRS Rev. Proc. 2025-32 and the One Big Beautiful Bill Act, including the $6,000 senior deduction) and Arizona income tax law for 2026 as amended by Laws 2026, chapter 140 (which lets Arizona filers subtract the federal senior deduction, and sets the Arizona standard deduction equal to the federal basic standard deduction). Greta (born January 1958) and Lucian (born January 1952) are married Arizona residents who file jointly. In 2026 they have pension income of $115,000 (from a private employer), $7,500 of taxable interest and Social Security benefits of $48,000. No other income; they take the standard deduction on both returns and have no credits. What is their 2026 Arizona income tax? Round to the nearest dollar. End your reply with a line of the form "ANSWER: <number>" with no $ sign or commas.

