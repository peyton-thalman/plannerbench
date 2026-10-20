# Human audit pack

Check each with a calculator and the cited table. About 2 minutes each. Tick the box if you agree.

## [ ] rmd-087

> Under SECURE 2.0, a traditional IRA owner born in 1945 turns 81 in 2026. The IRA balance on December 31, 2025 was $1,446,000. Their spouse is not more than 10 years younger. What is the required minimum distribution for 2026, rounded to the nearest dollar? Answer 0 if no RMD is required for 2026.

- Born 1945 → RMD age 72; age 81 → required
- Divisor at 81 = 19.4
- 1,446,000 / 19.4 = 74,536

## [ ] tax_torpedo-108

> Use 2026 federal tax law (IRS Rev. Proc. 2025-32 and the One Big Beautiful Bill Act, including the $6,000 senior deduction). In 2026, a married couple filing jointly (both spouses age 65 or older) has $62,000 of traditional IRA distributions, $0 of long-term capital gains and qualified dividends, and $64,500 of Social Security benefits, with no wages. They take the standard deduction and have no credits. If they also convert $13,000 from a traditional IRA to a Roth IRA in 2026, by how many dollars does their total federal income tax (including any Net Investment Income Tax) go up? Round to the nearest dollar.

- Tax without the conversion = 7,090 (work it as a federal_tax case)
- Tax with 13,000 more IRA income = 9,383
- Taxable Social Security rises 48,712 → 54,825, so taxable income rises by more than the conversion
- Difference = 2,294 vs. 1,560 from conversion × bracket rate alone

## [ ] widow_all_in-058

> Use 2026 federal tax law (IRS Rev. Proc. 2025-32 and the One Big Beautiful Bill Act, including the $6,000 senior deduction). Use the 2026 CMS Part B premiums and IRMAA tiers. There is no tax-exempt interest, so MAGI for IRMAA equals AGI. A married couple, both age 65 or older and both enrolled in Medicare Part B, files jointly. They have $236,500 of traditional IRA distributions, $0 of long-term capital gains and qualified dividends, and Social Security benefits of $33,300 (spouse A) and $21,500 (spouse B), with no wages. Spouse B dies. In the survivor's first full year filing as single (no dependents), spouse A keeps the larger of the two Social Security benefits and has the same IRA distributions and gains. Using 2026 law and amounts for both years, standard deduction and no credits, and assuming each year's Part B premiums are set by that same year's income, how many dollars more does the survivor pay per year in federal income tax (including any Net Investment Income Tax) plus Part B premiums than the couple paid together? Give a negative number if the survivor pays less. Round to the nearest dollar.

- Tax-only part (what a one-step answer gives) = 10,770
- Medicare Part B change for the year = -1,948 (CMS 2026 tiers: joint [218000, 274000, 342000, 410000, 750000], single [109000, 137000, 171000, 205000, 500000])
- Total = 8,822

## [ ] widow_all_in-096

> Use 2026 federal tax law (IRS Rev. Proc. 2025-32 and the One Big Beautiful Bill Act, including the $6,000 senior deduction). Use the 2026 CMS Part B premiums and IRMAA tiers. There is no tax-exempt interest, so MAGI for IRMAA equals AGI. A married couple, both age 65 or older and both enrolled in Medicare Part B, files jointly. They have $61,000 of traditional IRA distributions, $31,000 of long-term capital gains and qualified dividends, and Social Security benefits of $29,600 (spouse A) and $19,800 (spouse B), with no wages. Spouse B dies. In the survivor's first full year filing as single (no dependents), spouse A keeps the larger of the two Social Security benefits and has the same IRA distributions and gains. Using 2026 law and amounts for both years, standard deduction and no credits, and assuming each year's Part B premiums are set by that same year's income, how many dollars more does the survivor pay per year in federal income tax (including any Net Investment Income Tax) plus Part B premiums than the couple paid together? Give a negative number if the survivor pays less. Round to the nearest dollar.

- Tax-only part (what a one-step answer gives) = 7,398
- Medicare Part B change for the year = -1,460 (CMS 2026 tiers: joint [218000, 274000, 342000, 410000, 750000], single [109000, 137000, 171000, 205000, 500000])
- Total = 5,938

## [ ] comms_review-050

> FINRA Rule 2210(d)(1) says retail communications may not contain any false, exaggerated, unwarranted, promissory or misleading statement or claim, and may not predict or project performance. A representative drafted this email to retail clients about a stock mutual fund:

1. Please read the prospectus, which describes the fund's fees, risks and objectives, before investing.
2. CDs are FDIC-insured up to $250,000 per depositor; mutual fund shares are not FDIC-insured.
3. We can meet to review whether this fund fits your goals and time horizon.
4. The fund's expense ratio is 0.65% a year, which is taken out of fund assets.
5. The fund is not guaranteed and can lose value, so you could lose money.
6. The fund invests mainly in large U.S. companies.

Which numbered sentences violate Rule 2210(d)(1)?

- Violations are guarantees, return predictions, 'virtually no risk', and calling the fund FDIC-insured (Rule 2210(d)(1)(A), (F))
- Answer: sentences NONE

## [ ] rmd-020

> Under SECURE 2.0, a traditional IRA owner born in 1948 turns 78 in 2026. The IRA balance on December 31, 2025 was $1,577,000. Their spouse is not more than 10 years younger. What is the required minimum distribution for 2026, rounded to the nearest dollar? Answer 0 if no RMD is required for 2026.

- Born 1948 → RMD age 72; age 78 → required
- Divisor at 78 = 22.0
- 1,577,000 / 22.0 = 71,682

## [ ] bracket_room-114

> Use 2026 federal tax law (IRS Rev. Proc. 2025-32 and the One Big Beautiful Bill Act, including the $6,000 senior deduction). In 2026, a single filer under age 65 has $66,000 of ordinary income (no Social Security, no capital gains) and takes the standard deduction. How large a Roth conversion can they do without any of it being taxed above the 22% bracket? Answer 0 if they are already above it.

- Taxable income = 66,000 − 16,100 = 49,900
- Top of 22% bracket (single) minus taxable = 55,800

## [ ] breakpoint-061

> A client is buying $239,000 of Class A shares of a mutual fund. The prospectus sales charge, as a percentage of the offering price, is: less than $50,000: 5.75%; $50,000 to less than $100,000: 4.50%; $100,000 to less than $250,000: 3.50%; $250,000 to less than $500,000: 2.50%; $500,000 to less than $1,000,000: 2.00%; $1,000,000 or more: 0%. Under the prospectus's rights of accumulation, the purchase is combined with the current value of holdings in the same fund family owned by the client, the client's spouse, and their children under age 21, in any type of account. Current holdings: the client's IRA in the same fund family, $0; the spouse's taxable account in the same fund family, $104,000; their 18-year-old child's account in the same fund family, $6,000; their 25-year-old child's account in the same fund family, $0; the client's brokerage holdings in a different fund family, $0. What sales charge percentage should this purchase receive?

- Counted: purchase 239,000 + client 0 + spouse 104,000 + minor child 6,000 = 349,000
- Not counted: adult child 0, other fund family 0
- Schedule row for 349,000 → 2.5%

## [ ] breakpoint-145

> A client is buying $29,000 of Class A shares of a mutual fund. The prospectus sales charge, as a percentage of the offering price, is: less than $50,000: 5.75%; $50,000 to less than $100,000: 4.50%; $100,000 to less than $250,000: 3.50%; $250,000 to less than $500,000: 2.50%; $500,000 to less than $1,000,000: 2.00%; $1,000,000 or more: 0%. Under the prospectus's rights of accumulation, the purchase is combined with the current value of holdings in the same fund family owned by the client, the client's spouse, and their children under age 21, in any type of account. Current holdings: the client's IRA in the same fund family, $90,000; the spouse's taxable account in the same fund family, $0; their 16-year-old child's account in the same fund family, $15,000; their 33-year-old child's account in the same fund family, $75,000; the client's brokerage holdings in a different fund family, $0. What sales charge percentage should this purchase receive?

- Counted: purchase 29,000 + client 90,000 + spouse 0 + minor child 15,000 = 134,000
- Not counted: adult child 75,000, other fund family 0
- Schedule row for 134,000 → 3.5%

## [ ] rollover_flags-079

> You are a supervisor reviewing a registered representative's rollover recommendation under Regulation Best Interest's Care Obligation and the factors in FINRA Regulatory Notice 13-45. The client is 58 and left their employer at age 56. They do not plan to withdraw anything until after age 59½. Their 401(k) is worth $370,000 and holds no employer stock. The 401(k)'s funds charge 0.04% a year in total. The recommendation is to roll the whole 401(k) into an IRA invested in funds charging 0.75% a year plus a 1% annual advisory fee.

Which of these issues apply to this client and should have been weighed before recommending the rollover?
- AGE55: The client left the employer in or after the year they turned 55, is under 59½, and plans withdrawals before 59½. Withdrawals from the 401(k) would avoid the 10% early-withdrawal penalty, but IRA withdrawals would not.
- NUA: Rolling low-basis employer stock into an IRA gives up net unrealized appreciation tax treatment.
- COST: The IRA would cost the client more each year than staying in the plan.

Answer with every code that applies, separated by commas, or NONE.

- Left employer at 56, now 58, withdrawals planned: no → AGE55 needs all three (55+ at separation, under 59½, withdrawing)
- IRA cost 1.75% vs. plan 0.04% → COST if the IRA is higher
- No employer stock → no NUA
- Answer: COST

## [ ] senior_phaseout-122

> Use 2026 federal tax law (IRS Rev. Proc. 2025-32 and the One Big Beautiful Bill Act, including the $6,000 senior deduction). In 2026, a married couple filing jointly (both spouses age 65 or older) has $155,000 of traditional IRA distributions, $0 of long-term capital gains and qualified dividends, and $61,100 of Social Security benefits, with no wages. They take the standard deduction and have no credits. What is their total federal income tax including any Net Investment Income Tax, rounded to the nearest dollar?

- AGI = 206,935 (taxable SS from Pub 915)
- Senior deduction per person = 6,000 − 6% × (206,935 − 150,000) = 2,583.90, × 2 = 5,167.80 (Schedule 1-A lines 35–37)
- Tax = 26,003

## [ ] rollover_flags-145

> You are a supervisor reviewing a registered representative's rollover recommendation under Regulation Best Interest's Care Obligation and the factors in FINRA Regulatory Notice 13-45. The client is 58 and left their employer at age 56. They plan to withdraw $40,000 a year starting now to cover expenses until they claim Social Security. Their 401(k) is worth $450,000, including $95,000 of the former employer's stock with a cost basis of $93,000. The 401(k)'s funds charge 0.05% a year in total. The recommendation is to roll the whole 401(k), employer stock included, into an IRA invested in funds charging 0.95% a year plus a 0.5% annual advisory fee.

Which of these issues apply to this client and should have been weighed before recommending the rollover?
- AGE55: The client left the employer in or after the year they turned 55, is under 59½, and plans withdrawals before 59½. Withdrawals from the 401(k) would avoid the 10% early-withdrawal penalty, but IRA withdrawals would not.
- NUA: Rolling low-basis employer stock into an IRA gives up net unrealized appreciation tax treatment.
- COST: The IRA would cost the client more each year than staying in the plan.

Answer with every code that applies, separated by commas, or NONE.

- Left employer at 56, now 58, withdrawals planned: yes → AGE55 needs all three (55+ at separation, under 59½, withdrawing)
- IRA cost 1.45% vs. plan 0.05% → COST if the IRA is higher
- Employer stock 95,000, basis 93,000 → NUA if basis is low
- Answer: AGE55,COST
