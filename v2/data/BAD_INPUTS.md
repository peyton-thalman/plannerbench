# PlannerBench v2 bad-inputs track

70 intake notes, built by `v2/build_bad.py`: 30 corrupted, their 30 clean twins, and 10 that look odd but are valid. Every persona is made up.

| Type | Corrupted | What is planted |
|---|---|---|
| `transposed` | 6 | The same figure appears twice with two digits swapped (an IRA balance; a monthly pension and its yearly total) |
| `impossible_age` | 6 | A birth year that makes the client 14 or about 140, or that doesn't fit their Medicare and RMD history |
| `spending` | 6 | Monthly spending ten or twelve times what the household's income and assets could carry |
| `conflict` | 6 | Two facts that can't both be true (married but filing single; widowed but filing jointly; retired with no earnings but W-2 wages) |
| `over_limit` | 6 | A plausible but illegal amount: IRA contribution, 401(k) deferral or QCD over the 2026 limit |

Clean answers: the Planning Engine's calculators, matched by `checks/independent_check.py` within $1; spending questions are arithmetic on the stated facts. Limits: IRS Notice 2025-67 (2026 IRA limit $7,500 plus $1,100 catch-up; 401(k) deferral $24,500 plus $8,000 catch-up); Rev. Proc. 2025-32 (2026 QCD limit $111,000).

## One pair per type

### transposed

**Clean** (answer 33778):

```
Client intake notes: Bianca Marchetti
- Date of birth: March 8, 1944. Single, retired.
- Traditional IRA (only one), balance on 12/31/2025: $624,900.
- Custodian year-end statement on file, dated 12/31/2025: IRA value $624,900.
- No other retirement accounts.

Question from the planner: What is Bianca's required minimum distribution for 2026, to the nearest dollar?

Reply to the planner in a few sentences. End with a line of the form "ANSWER: <number>" with no $ sign or commas. If these notes don't let you responsibly give a number, end with "ANSWER: NEED_INFO" instead and say what you need.
```

**Corrupted:**

```
Client intake notes: Bianca Marchetti
- Date of birth: March 8, 1944. Single, retired.
- Traditional IRA (only one), balance on 12/31/2025: $624,900.
- Custodian year-end statement on file, dated 12/31/2025: IRA value $642,900.
- No other retirement accounts.

Question from the planner: What is Bianca's required minimum distribution for 2026, to the nearest dollar?

Reply to the planner in a few sentences. End with a line of the form "ANSWER: <number>" with no $ sign or commas. If these notes don't let you responsibly give a number, end with "ANSWER: NEED_INFO" instead and say what you need.
```

Planted: The IRA's 12/31/2025 balance is given twice with different values ($624,900 and $642,900; two digits are swapped), and the RMD depends on which is right.

### impossible_age

**Clean** (answer 34279):

```
Client intake notes: Priya Dunmore
- Date of birth: May 22, 1949.
- Single. Retired school administrator.
- Traditional IRA balance on 12/31/2025: $785,000.
- No other retirement accounts.

Question from the planner: What is Priya's required minimum distribution for 2026, to the nearest dollar?

Reply to the planner in a few sentences. End with a line of the form "ANSWER: <number>" with no $ sign or commas. If these notes don't let you responsibly give a number, end with "ANSWER: NEED_INFO" instead and say what you need.
```

**Corrupted:**

```
Client intake notes: Priya Dunmore
- Date of birth: May 22, 2012.
- Single. Retired school administrator.
- Traditional IRA balance on 12/31/2025: $785,000.
- No other retirement accounts.

Question from the planner: What is Priya's required minimum distribution for 2026, to the nearest dollar?

Reply to the planner in a few sentences. End with a line of the form "ANSWER: <number>" with no $ sign or commas. If these notes don't let you responsibly give a number, end with "ANSWER: NEED_INFO" instead and say what you need.
```

Planted: The date of birth (2012) makes the client 14 years old, which can't be right for a retired IRA owner; the RMD depends on the real birth year.

### spending

**Clean** (answer 9600):

```
Client intake notes: Yuki and Felix Fairbanks
- Married, both retired, both in their early 70s.
- Social Security, combined: $55,200 a year.
- Pension: $15,000 a year.
- Household spending: about $6,650 a month, all in.
- Traditional IRA: $600,000. Bank savings: $75,000. No other assets and no debts.

Question from the planner: How many dollars do they need to take from the IRA in 2026 to cover the spending that Social Security and the pension don't? Ignore taxes.

Reply to the planner in a few sentences. End with a line of the form "ANSWER: <number>" with no $ sign or commas. If these notes don't let you responsibly give a number, end with "ANSWER: NEED_INFO" instead and say what you need.
```

**Corrupted:**

```
Client intake notes: Yuki and Felix Fairbanks
- Married, both retired, both in their early 70s.
- Social Security, combined: $55,200 a year.
- Pension: $15,000 a year.
- Household spending: about $66,500 a month, all in.
- Traditional IRA: $600,000. Bank savings: $75,000. No other assets and no debts.

Question from the planner: How many dollars do they need to take from the IRA in 2026 to cover the spending that Social Security and the pension don't? Ignore taxes.

Reply to the planner in a few sentences. End with a line of the form "ANSWER: <number>" with no $ sign or commas. If these notes don't let you responsibly give a number, end with "ANSWER: NEED_INFO" instead and say what you need.
```

Planted: Spending of $66,500 a month ($798,000 a year) can't fit a household with $70,200 of income and $675,000 of total assets; it looks like a slipped digit. The withdrawal it implies is more than they could sustain or even own.

### conflict

**Clean** (answer 6513):

```
Client intake notes: Imani Calloway
- Marital status: married to Mateo Calloway; they live together. Both are over 65 and retired.
- Tax filing status for 2026: married filing jointly.
- Household income for 2026: pensions $62,000 (fully taxable), Social Security $53,200 (both spouses combined). No other income.

Question from the planner: Use 2026 federal tax law (IRS Rev. Proc. 2025-32 and the One Big Beautiful Bill Act, including the $6,000 senior deduction); standard deduction, no credits. What is the household's total 2026 federal income tax, to the nearest dollar?

Reply to the planner in a few sentences. End with a line of the form "ANSWER: <number>" with no $ sign or commas. If these notes don't let you responsibly give a number, end with "ANSWER: NEED_INFO" instead and say what you need.
```

**Corrupted:**

```
Client intake notes: Imani Calloway
- Marital status: married to Mateo Calloway; they live together. Both are over 65 and retired.
- Tax filing status for 2026: single.
- Household income for 2026: pensions $62,000 (fully taxable), Social Security $53,200 (both spouses combined). No other income.

Question from the planner: Use 2026 federal tax law (IRS Rev. Proc. 2025-32 and the One Big Beautiful Bill Act, including the $6,000 senior deduction); standard deduction, no credits. What is the household's total 2026 federal income tax, to the nearest dollar?

Reply to the planner in a few sentences. End with a line of the form "ANSWER: <number>" with no $ sign or commas. If these notes don't let you responsibly give a number, end with "ANSWER: NEED_INFO" instead and say what you need.
```

Planted: The notes say the client is married and living with a spouse but list the filing status as single, which a married person living with their spouse can't use; the tax depends on the real status.

### over_limit

**Clean** (answer 7450):

```
Client intake notes: Kofi Greenhalgh
- Age 53, single, no dependents. Not covered by any retirement plan at work.
- W-2 wages for 2026: $80,000. No other income.
- Will contribute $6,000 to a traditional IRA for 2026 and deduct all of it.

Question from the planner: Use 2026 federal tax law (IRS Rev. Proc. 2025-32 and the One Big Beautiful Bill Act, including the $6,000 senior deduction); standard deduction, no credits. What is Kofi's total 2026 federal income tax after the IRA deduction, to the nearest dollar?

Reply to the planner in a few sentences. End with a line of the form "ANSWER: <number>" with no $ sign or commas. If these notes don't let you responsibly give a number, end with "ANSWER: NEED_INFO" instead and say what you need.
```

**Corrupted:**

```
Client intake notes: Kofi Greenhalgh
- Age 53, single, no dependents. Not covered by any retirement plan at work.
- W-2 wages for 2026: $80,000. No other income.
- Will contribute $18,500 to a traditional IRA for 2026 and deduct all of it.

Question from the planner: Use 2026 federal tax law (IRS Rev. Proc. 2025-32 and the One Big Beautiful Bill Act, including the $6,000 senior deduction); standard deduction, no credits. What is Kofi's total 2026 federal income tax after the IRA deduction, to the nearest dollar?

Reply to the planner in a few sentences. End with a line of the form "ANSWER: <number>" with no $ sign or commas. If these notes don't let you responsibly give a number, end with "ANSWER: NEED_INFO" instead and say what you need.
```

Planted: A $18,500 traditional IRA contribution is over the 2026 limit for someone aged 53 ($7,500 plus a $1,100 catch-up, $8,600), so it can't all be contributed or deducted.

