// The words of a Gauntlet question: the facts of one household, the planning conventions every question shares, and
// the law tables. Conventions the engine chose (timing, which account pays, how future law is projected, how the end
// is valued) are always stated, so a model alone is never marked wrong for not guessing them. Law *tables* are given;
// how the rules interact is not, because that is what the Gauntlet tests.
import { medicareLaw, yearLaw } from '../../../../moneyguide/src/scenario/params';
import type { AccountIn, Scenario } from '../../../../moneyguide/src/scenario/types';

export const INFLATION = 0.025;
const G = { inflation: INFLATION, chainedGap: 0, medicare: INFLATION, cola: INFLATION };

export const usd = (x: number) => `${x < 0 ? '−' : ''}$${Math.abs(Math.round(x)).toLocaleString('en-US')}`;
const pct = (x: number) => `${Math.round(x * 1000) / 10}%`;
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

export type Names = Record<string, string>;

const TYPE: Record<AccountIn['type'], string> = {
  traditional_ira: 'traditional IRA', '401k': '401(k)', roth_ira: 'Roth IRA', inherited_ira: 'inherited traditional IRA',
  inherited_roth_ira: 'inherited Roth IRA', taxable: 'brokerage account', cash: 'savings (cash) account',
};

/** The household as a plain list of facts. Every input the engine reads appears here. */
export function facts(sc: Scenario, n: Names): string[] {
  const h = sc.household;
  const a = sc.assumptions;
  const who = (id: string) => (id === 'joint' ? (h.filing === 'mfj' ? 'Joint' : n[h.people[0].id] + "'s") : `${n[id]}'s`);
  const out: string[] = [];
  out.push(h.filing === 'mfj' ? 'Married, filing jointly.' : 'Single (files as single).');
  out.push(h.state === 'AZ' ? 'They live in Arizona.' : 'They live in a state with no income tax.');
  for (const p of h.people) {
    const age = a.first_year - p.born;
    let s = `${n[p.id]}: born ${MONTHS[(p.born_month ?? 1) - 1]} ${p.born} (turns ${age} in ${a.first_year}).`;
    s += p.medicare ? ' Enrolled in Medicare Part B and a Part D drug plan (or will be from age 65).' : ' Not on Medicare and never will be in this plan.';
    const ss = p.social_security;
    if (ss?.already_claimed_monthly !== undefined) {
      s += ` Already receiving Social Security: ${usd(ss.already_claimed_monthly)} a month as of January ${a.first_year}`;
      s += ss.already_claimed_monthly >= ss.monthly_at_fra ? ' (claimed at full retirement age).' : `; full-retirement-age amount ${usd(ss.monthly_at_fra)}.`;
    } else if (ss) {
      s += ` Not yet claiming Social Security. Full-retirement-age benefit (PIA): ${usd(ss.monthly_at_fra)} a month in ${a.first_year} dollars; plans to claim at ${ss.claim_age} unless an option says otherwise.`;
    }
    out.push(s);
  }
  for (const x of h.accounts) {
    let s = `${who(x.owner)} ${TYPE[x.type]}: ${usd(x.balance)} on December 31, ${a.first_year - 1}.`;
    if (x.type === 'traditional_ira') s += x.after_tax_basis ? ` Includes ${usd(x.after_tax_basis)} of after-tax (nondeductible) contributions (Form 8606 basis).` : ' All pre-tax (no after-tax basis).';
    if (x.type === 'roth_ira') s += ` First Roth contribution in ${x.first_roth_year}.`;
    if (x.type === 'taxable') s += ` Cost basis ${usd(x.cost_basis ?? x.balance)}; dividends ${pct(x.dividend_yield ?? 0)} of the opening balance each year, ${pct(x.qualified_share ?? 0)} of them qualified; all holdings long-term.`;
    if (x.inherited) {
      const i = x.inherited;
      s += ` Inherited from a parent born in ${i.from_born} who died in ${i.died}${i.owner_had_reached_rbd === false ? ' before their required beginning date' : ''}. ${n[x.owner]} is a non-eligible designated beneficiary (the 10-year rule applies).`;
    }
    out.push(s);
  }
  for (const i of h.income ?? []) {
    const kind = { pension: 'pension (fully taxable)', wages: 'wages', annuity_taxable: 'taxable part of a nonqualified annuity', interest_taxable: 'taxable interest', interest_tax_exempt: 'tax-exempt municipal bond interest', rental: 'net rental income' }[i.type];
    const raise = i.cola ? `rising ${pct(i.cola)} a year` : 'no raises';
    out.push(`${who(i.owner)} ${kind}: ${usd(i.annual)} a year from ${Math.max(i.start_year ?? a.first_year, a.first_year)}${i.end_year ? ` through ${i.end_year}` : ''}, ${raise}.`);
  }
  out.push(`Spending: ${usd(h.spending_need)} a year after tax in ${a.first_year} dollars, rising with inflation. Federal tax and Medicare premiums are paid on top of this.`);
  const it = h.itemized ?? {};
  const items = [
    it.salt_other ? `property tax ${usd(it.salt_other)}` : '', it.mortgage_interest ? `mortgage interest ${usd(it.mortgage_interest)}` : '',
    it.medical ? `medical expenses ${usd(it.medical)}` : '', it.charity_cash ? `cash gifts to charity ${usd(it.charity_cash)}` : '',
  ].filter(Boolean);
  out.push(items.length ? `Paid out of that spending each year (${a.first_year} dollars, rising with inflation): ${items.join(', ')}. No other deductible expenses.` : 'No mortgage, no large medical bills, no charitable gifts.');
  for (const [y, m] of Object.entries(h.prior_magi ?? {})) out.push(`Their ${y} MAGI (for Medicare IRMAA) was ${usd(m.magi)}, on a ${m.filing === 'mfj' ? 'joint' : 'single'} return.`);
  for (const e of sc.events ?? []) out.push(`For planning, assume ${n[e.person]} dies in ${e.year}. The survivor keeps spending the same amount.`);
  return out;
}

/** What every question assumes. Stated once, identically, in every prompt. */
export function conventions(sc: Scenario): string {
  const a = sc.assumptions;
  return [
    `Planning conventions (use these exactly):`,
    `- The plan runs from ${a.first_year} through ${a.last_year}, or through the year the last person dies if earlier.`,
    `- Every account earns ${pct(a.return)} a year on its opening balance. All RMDs, conversions, gifts, withdrawals and sales happen on December 31, after that year's growth. Savings interest is ${pct(a.return)} of the opening balance and is taxable interest.`,
    `- If an option asks to convert, give or withdraw more than an account holds, take what's left.\n` +
    `- Spending, federal tax and Medicare premiums are paid from savings first, then the brokerage account, then all traditional IRAs together (in proportion to their balances), then Roth IRAs. Spending a surplus is never assumed; any surplus goes to savings.`,
    `- Inflation is ${pct(INFLATION)} a year. After ${a.first_year}, tax brackets, standard deductions, capital-gain thresholds and IRMAA thresholds rise with inflation (IRMAA thresholds to the nearest $1,000; the top IRMAA threshold is frozen through 2027). Medicare premiums rise ${pct(INFLATION)} a year. Social Security gets a 3.6% COLA in 2027 and ${pct(INFLATION)} after.`,
    `- Medicare premiums for each year use the MAGI from the tax return two years earlier, with that return's filing status. Count Part B plus any Part D IRMAA surcharge, for every person on Medicare; ignore the Part D plan's own premium.`,
    `- "After-tax wealth" means everything left on December 31, ${a.last_year} (or the year of the last death), with traditional and inherited IRAs counted after the heirs' ${pct(a.heirs_tax_rate)} income tax, and Roth IRAs, brokerage and savings at full value, in ${a.first_year} dollars (divide by 1.025 per year).`,
  ].join('\n');
}

const brackets = (b: [number, number][]) => b.map(([top, r], i) => `${pct(r)} ${i ? `over ${usd(b[i - 1][0])}` : 'from $0'}`).join(', ');

/** 2026 federal law and the Medicare tables, in numbers. */
export function lawTables(): string {
  const y = yearLaw(2026, G);
  const m26 = medicareLaw(2026, G), m28 = medicareLaw(2028, G);
  const tiers = (m: typeof m26, f: 'mfj' | 'single') => m.tiers[f].map((t, i) => `${i === 4 ? '≥' : '>'} ${usd(t)}: Part B $${m.partB[i + 1].toFixed(2)}, Part D add $${m.partD[i + 1].toFixed(2)}`).join('; ');
  return [
    `2026 federal law (IRS Rev. Proc. 2025-32 and the One Big Beautiful Bill Act):`,
    `- Ordinary brackets, married filing jointly: ${brackets(y.ordinary.mfj)}. Single: ${brackets(y.ordinary.single)}.`,
    `- 0% long-term capital gain rate up to ${usd(y.ltcg.mfj.zero)} of taxable income (joint) / ${usd(y.ltcg.single.zero)} (single); 15% up to ${usd(y.ltcg.mfj.fifteen)} / ${usd(y.ltcg.single.fifteen)}; 20% above.`,
    `- Standard deduction ${usd(y.std.mfj)} joint / ${usd(y.std.single)} single, plus ${usd(y.std65.mfj)} per spouse 65 or older (joint) / ${usd(y.std65.single)} (single).`,
    `- Senior deduction (2025-2028 only): ${usd(y.senior.amount)} per person 65 or older; each person's amount is reduced by ${pct(y.senior.rate)} of MAGI over ${usd(y.senior.threshold.mfj)} (joint) / ${usd(y.senior.threshold.single)} (single).`,
    `- Non-itemizers may deduct up to ${usd(y.nonitemizerCap.mfj)} (joint) / ${usd(y.nonitemizerCap.single)} (single) of cash gifts to charity. Itemized charitable gifts are deductible only above 0.5% of AGI. SALT cap ${usd(y.salt.cap)}.`,
    `- Social Security base amounts ${usd(y.ssBase.mfj[0])} / ${usd(y.ssBase.mfj[1])} (joint), ${usd(y.ssBase.single[0])} / ${usd(y.ssBase.single[1])} (single). Net investment income tax ${pct(y.niit.rate)} over ${usd(y.niit.threshold.mfj)} / ${usd(y.niit.threshold.single)} MAGI. QCD limit ${usd(y.qcdLimit)} per person.`,
    `Medicare, monthly per person. 2026: standard Part B $${m26.partB[0].toFixed(2)}. Joint MAGI ${tiers(m26, 'mfj')}. Single MAGI ${tiers(m26, 'single')}.`,
    `Medicare 2028 (projected by the conventions above): standard Part B $${m28.partB[0].toFixed(2)}. Joint MAGI ${tiers(m28, 'mfj')}. Single MAGI ${tiers(m28, 'single')}.`,
  ].join('\n');
}

export const FORMAT_NOTE = (letters: string[], numbers: string[]) => [
  `Explain your reasoning, then end with these lines and nothing after them:`,
  `PICK: <${letters.join(', ')}>  (or PICK: CLOSE <letters> if the best options are within $1,000 of each other in after-tax wealth)`,
  ...numbers.map((id) => `${id}: <number, whole dollars, no $ sign or commas>`),
  `If the question can't be answered reliably from what's given, say why and end with PICK: CANT instead.`,
].join('\n');
