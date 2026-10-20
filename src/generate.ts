// Generates PlannerBench cases: client-style questions with exact answers computed by the MoneyGuide engine,
// whose own tests check it against IRS Rev. Proc. 2025-32, Pub 915, the Uniform Lifetime Table and SSA factors.
import { readFileSync, writeFileSync } from 'node:fs';
import { computeTax, taxableSocialSecurity, rmdDivisor, rmdStartAge, irmaaTier, IRMAA, type Filing } from '../../../moneyguide/src/engine/tax';
import { claimFactor } from '../../../moneyguide/src/engine/sim';

export interface Case {
  id: string;
  task: 'federal_tax' | 'taxable_ss' | 'rmd' | 'ss_claim' | 'bracket_room' | 'irmaa' | 'tax_torpedo' | 'widow_penalty'
    | 'senior_phaseout' | 'conversion_all_in' | 'widow_all_in'
    | 'rollover_flags' | 'breakpoint' | 'comms_review';
  prompt: string;
  inputs: Record<string, number | string | boolean | number[]>;
  /** A number, or for the compliance tasks a set of codes written sorted and comma-joined ("NONE" when empty). */
  answer: number | string;
  /** Absolute dollar tolerance for grading. */
  tol: number;
  /** The answer a one-step shortcut gives (multi-step tasks only), so the grader can tell "fell for the trap" from other mistakes. */
  naive?: number;
  /** Answers a specific misreading produces, by mistake name, so the grader can name the mistake. */
  misreadings?: Record<string, number | string>;
}

// Seeded PRNG so the benchmark is reproducible. The public set uses the seed below; the private held-out set uses
// PB_SEED, which lives only in private/seed, so a model trained on the public cases still meets new ones.
let seed = Number(process.env.PB_SEED ?? 20261020);
const rand = () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 2 ** 32);
const pick = <T,>(xs: T[]) => xs[Math.floor(rand() * xs.length)];
const round = (x: number, to: number) => Math.round(x / to) * to;
const between = (lo: number, hi: number, to: number) => round(lo + rand() * (hi - lo), to);
const usd = (x: number) => '$' + x.toLocaleString('en-US');
const who = (f: Filing) => (f === 'mfj' ? 'a married couple filing jointly' : 'a single filer');
/** Who is 65 or older, in words that fit the filing status (a single filer has no spouse). */
const ages = (f: Filing, over65: number) =>
  f === 'single' ? (over65 ? 'age 65 or older' : 'under age 65')
    : ['both spouses under age 65', 'one spouse age 65 or older, the other under 65', 'both spouses age 65 or older'][over65];

const fed = (filing: Filing, over65: number, ordinary: number, ltcg: number, ss: number) =>
  computeTax({ filing, year: 2026, index: 1, wages: 0, ordinary, ltcg, ssBenefits: ss, over65, stateRate: 0, stateTaxesSS: false });

/** Monthly Part B premium per person for a MAGI (no tax-exempt interest, so MAGI = AGI). */
const partB = (magi: number, filing: Filing) => IRMAA.partBTotal[irmaaTier(magi, filing, 1)];
const MEDICARE = 'Use the 2026 CMS Part B premiums and IRMAA tiers. There is no tax-exempt interest, so MAGI for IRMAA equals AGI. ';

const RULES = 'Use 2026 federal tax law (IRS Rev. Proc. 2025-32 and the One Big Beautiful Bill Act, including the $6,000 senior deduction). ';
const FORMAT = ' End your reply with a line of the form "ANSWER: <number>" with no $ sign or commas.';

const gens: Record<Case['task'], () => Omit<Case, 'id' | 'task'>> = {
  federal_tax() {
    const filing = pick<Filing>(['mfj', 'single']);
    const over65 = filing === 'mfj' ? pick([0, 1, 2]) : pick([0, 1]);
    const wages = over65 === 2 ? 0 : between(0, 220000, 1000);
    const ordinary = between(0, 90000, 500);
    const ltcg = pick([0, 0, between(2000, 60000, 500)]);
    const ss = over65 ? between(18000, 62000, 100) : 0;
    const t = computeTax({ filing, year: 2026, index: 1, wages, ordinary, ltcg, ssBenefits: ss, over65, stateRate: 0, stateTaxesSS: false });
    return {
      prompt: `${RULES}In 2026, ${who(filing)} (${ages(filing, over65)}) has ${usd(wages)} of wages, ${usd(ordinary)} of traditional IRA distributions, ${usd(ltcg)} of long-term capital gains and qualified dividends, and ${usd(ss)} of Social Security benefits. They take the standard deduction and have no credits. What is their total federal income tax including any Net Investment Income Tax, rounded to the nearest dollar?${FORMAT}`,
      inputs: { filing, over65, wages, ordinary, ltcg, ss },
      answer: Math.round(t.federal),
      tol: 2,
    };
  },
  taxable_ss() {
    const filing = pick<Filing>(['mfj', 'single']);
    const ss = between(15000, 60000, 100);
    const other = between(5000, 90000, 500);
    return {
      prompt: `Using the IRS Publication 915 worksheet, ${who(filing)} receives ${usd(ss)} of Social Security benefits and has ${usd(other)} of other income (no tax-exempt interest, no adjustments). How much of the Social Security is taxable, rounded to the nearest dollar?${FORMAT}`,
      inputs: { filing, ss, other },
      answer: Math.round(taxableSocialSecurity(ss, other, filing)),
      tol: 1,
    };
  },
  rmd() {
    const birthYear = between(1945, 1962, 1);
    const age = 2026 - birthYear;
    const balance = between(150000, 2500000, 1000);
    const required = age >= rmdStartAge(birthYear);
    return {
      prompt: `Under SECURE 2.0, a traditional IRA owner born in ${birthYear} turns ${age} in 2026. The IRA balance on December 31, 2025 was ${usd(balance)}. Their spouse is not more than 10 years younger. What is the required minimum distribution for 2026, rounded to the nearest dollar? Answer 0 if no RMD is required for 2026.${FORMAT}`,
      inputs: { birthYear, age, balance },
      answer: required ? Math.round(balance / rmdDivisor(age)) : 0,
      tol: 1,
    };
  },
  ss_claim() {
    const birthYear = between(1955, 1966, 1);
    const pia = between(1200, 4000, 10);
    const months = between(0, 96, 1);
    const claimAge = 62 + months / 12;
    const yrs = Math.floor(claimAge), mo = months % 12;
    return {
      prompt: `A worker born in ${birthYear} has a primary insurance amount (PIA) of ${usd(pia)}/month. They start retirement benefits at age ${yrs} and ${mo} month${mo === 1 ? '' : 's'}. Ignoring COLAs and the earnings test, what is their monthly benefit, rounded to the nearest dollar?${FORMAT}`,
      inputs: { birthYear, pia, claimAgeMonths: 744 + months },
      answer: Math.round(pia * claimFactor(claimAge, birthYear)),
      tol: 1,
    };
  },
  bracket_room() {
    const filing = pick<Filing>(['mfj', 'single']);
    const rate = pick([0.12, 0.22, 0.24]);
    const ordinary = between(20000, filing === 'mfj' ? 300000 : 150000, 500);
    const t = computeTax({ filing, year: 2026, index: 1, wages: 0, ordinary, ltcg: 0, ssBenefits: 0, over65: 0, stateRate: 0, stateTaxesSS: false });
    const tops = filing === 'mfj' ? { 0.12: 100800, 0.22: 211400, 0.24: 403550 } : { 0.12: 50400, 0.22: 105700, 0.24: 201775 };
    const room = Math.max(0, tops[rate as 0.12] - t.taxableIncome);
    return {
      prompt: `${RULES}In 2026, ${who(filing)} under age 65 has ${usd(ordinary)} of ordinary income (no Social Security, no capital gains) and takes the standard deduction. How large a Roth conversion can they do without any of it being taxed above the ${rate * 100}% bracket? Answer 0 if they are already above it.${FORMAT}`,
      inputs: { filing, ordinary, rate },
      answer: Math.round(room),
      tol: 1,
    };
  },
  irmaa() {
    const filing = pick<Filing>(['mfj', 'single']);
    const t = IRMAA.tiers[filing];
    // Cliffs are where people and models slip: a fifth of cases land exactly on a threshold, a third within $5k of one.
    const r = rand();
    const magi = r < 0.2 ? pick(t) : r < 0.55 ? round(pick(t) + between(-5000, 5000, 100), 100) : between(80000, 800000, 1000);
    return {
      prompt: `In 2026, a Medicare enrollee filing ${filing === 'mfj' ? 'jointly' : 'single'} had a 2024 modified adjusted gross income of ${usd(magi)}. What is their 2026 monthly Medicare Part B premium per person, including any IRMAA surcharge? Give dollars and cents.${FORMAT}`,
      inputs: { filing, magi },
      answer: IRMAA.partBTotal[irmaaTier(magi, filing, 1)],
      tol: 0.01,
    };
  },
  // v2 multi-step tasks: each is easy to do in one step and wrong when done that way.
  tax_torpedo() {
    // Retirees whose provisional income sits in the Social Security phase-in, where each converted dollar also
    // makes up to 85 cents of benefits taxable, can push gains out of the 0% band, and erodes the senior deduction.
    const filing = pick<Filing>(['mfj', 'single']);
    const over65 = filing === 'mfj' ? 2 : 1;
    const ss = filing === 'mfj' ? between(30000, 70000, 100) : between(18000, 42000, 100);
    const ordinary = filing === 'mfj' ? between(10000, 80000, 500) : between(5000, 45000, 500);
    const ltcg = pick([0, 0, between(5000, 40000, 500)]);
    const conversion = between(5000, 40000, 1000);
    const before = fed(filing, over65, ordinary, ltcg, ss);
    const after = fed(filing, over65, ordinary + conversion, ltcg, ss);
    return {
      prompt: `${RULES}In 2026, ${who(filing)} (${ages(filing, over65)}) has ${usd(ordinary)} of traditional IRA distributions, ${usd(ltcg)} of long-term capital gains and qualified dividends, and ${usd(ss)} of Social Security benefits, with no wages. They take the standard deduction and have no credits. If they also convert ${usd(conversion)} from a traditional IRA to a Roth IRA in 2026, by how many dollars does their total federal income tax (including any Net Investment Income Tax) go up? Round to the nearest dollar.${FORMAT}`,
      inputs: { filing, over65, ordinary, ltcg, ss, conversion },
      answer: Math.round(after.federal - before.federal),
      tol: 2,
      naive: Math.round(conversion * before.bracketRate),
    };
  },
  widow_penalty() {
    // After the first spouse dies the survivor files single (no dependents, so no qualifying-surviving-spouse status)
    // and keeps only the larger Social Security check, while the IRA withdrawals usually stay the same.
    const ssA = between(20000, 45000, 100);
    const ssB = between(10000, ssA, 100);
    const ordinary = between(20000, 140000, 500);
    const ltcg = pick([0, 0, between(5000, 40000, 500)]);
    const couple = fed('mfj', 2, ordinary, ltcg, ssA + ssB);
    const survivor = fed('single', 1, ordinary, ltcg, ssA);
    return {
      prompt: `${RULES}A married couple, both age 65 or older, files jointly. They have ${usd(ordinary)} of traditional IRA distributions, ${usd(ltcg)} of long-term capital gains and qualified dividends, and Social Security benefits of ${usd(ssA)} (spouse A) and ${usd(ssB)} (spouse B), with no wages. Spouse B dies. In the survivor's first full year filing as single (no dependents), spouse A keeps the larger of the two Social Security benefits and has the same IRA distributions and gains. Using 2026 law and amounts for both years, standard deduction and no credits, how many dollars more total federal income tax (including any Net Investment Income Tax) does the survivor owe than the couple did? Give a negative number if the survivor owes less. Round to the nearest dollar.${FORMAT}`,
      inputs: { ordinary, ltcg, ssA, ssB },
      answer: Math.round(survivor.federal - couple.federal),
      tol: 2,
    };
  },
  // v3 stacked tasks: several rules interact in one household, the way they do in a real review meeting.
  senior_phaseout() {
    // Aimed at the OBBBA phase-out band, where the pilot showed models taking 6% off the couple's combined $12,000
    // instead of off each spouse's $6,000 (Schedule 1-A Part V, lines 35-36b).
    const filing = pick<Filing>(['mfj', 'mfj', 'single']);
    const over65 = filing === 'mfj' ? 2 : 1;
    const ss = filing === 'mfj' ? between(30000, 75000, 100) : between(18000, 45000, 100);
    const ltcg = pick([0, between(5000, 50000, 500)]);
    const [lo, hi] = filing === 'mfj' ? [150000, 250000] : [75000, 175000];
    // Draw IRA income until AGI lands inside the band where the deduction is partly phased out.
    let ordinary = 0;
    for (let tries = 0; tries < 50; tries++) {
      ordinary = between(filing === 'mfj' ? 60000 : 30000, filing === 'mfj' ? 220000 : 150000, 500);
      const agi = fed(filing, over65, ordinary, ltcg, ss).agi;
      if (agi > lo + 2000 && agi < hi - 2000) break;
    }
    const t = fed(filing, over65, ordinary, ltcg, ss);
    return {
      prompt: `${RULES}In 2026, ${who(filing)} (${ages(filing, over65)}) has ${usd(ordinary)} of traditional IRA distributions, ${usd(ltcg)} of long-term capital gains and qualified dividends, and ${usd(ss)} of Social Security benefits, with no wages. They take the standard deduction and have no credits. What is their total federal income tax including any Net Investment Income Tax, rounded to the nearest dollar?${FORMAT}`,
      inputs: { filing, over65, ordinary, ltcg, ss },
      answer: Math.round(t.federal),
      tol: 2,
    };
  },
  conversion_all_in() {
    // The real cost of a Roth conversion: the tax torpedo plus an IRMAA cliff two years later.
    // Drawn so most conversions cross a cliff; the rest check that the model doesn't invent a surcharge.
    const filing = pick<Filing>(['mfj', 'single']);
    const over65 = filing === 'mfj' ? 2 : 1;
    const wantCross = rand() < 0.75;
    let ss = 0, ordinary = 0, ltcg = 0, conversion = 0;
    for (let tries = 0; tries < 200; tries++) {
      ss = filing === 'mfj' ? between(30000, 75000, 100) : between(18000, 45000, 100);
      ordinary = filing === 'mfj' ? between(80000, 330000, 500) : between(40000, 170000, 500);
      ltcg = pick([0, between(5000, 40000, 500)]);
      conversion = between(10000, 80000, 1000);
      const crosses = partB(fed(filing, over65, ordinary + conversion, ltcg, ss).agi, filing) > partB(fed(filing, over65, ordinary, ltcg, ss).agi, filing);
      if (crosses === wantCross) break;
    }
    const before = fed(filing, over65, ordinary, ltcg, ss);
    const after = fed(filing, over65, ordinary + conversion, ltcg, ss);
    const taxUp = after.federal - before.federal;
    const medicareUp = 12 * over65 * (partB(after.agi, filing) - partB(before.agi, filing));
    return {
      prompt: `${RULES}${MEDICARE}In 2026, ${who(filing)} (${ages(filing, over65)}, ${over65 === 2 ? 'both ' : ''}enrolled in Medicare Part B) has ${usd(ordinary)} of traditional IRA distributions, ${usd(ltcg)} of long-term capital gains and qualified dividends, and ${usd(ss)} of Social Security benefits, with no wages, standard deduction and no credits. They are considering converting ${usd(conversion)} from a traditional IRA to a Roth IRA in 2026. Medicare sets Part B premiums from the tax return two years earlier, so 2026 income sets 2028 premiums; assume the 2026 premiums and tiers still apply in 2028 and that nothing else changes. What is the total added cost of the conversion: the increase in 2026 federal income tax (including any Net Investment Income Tax) plus the increase in their combined 2028 Part B premiums for the full year? Round to the nearest dollar.${FORMAT}`,
      inputs: { filing, over65, ordinary, ltcg, ss, conversion },
      answer: Math.round(taxUp + medicareUp),
      tol: 2,
      naive: Math.round(taxUp),
    };
  },
  widow_all_in() {
    // The widow's penalty with Medicare included: single IRMAA tiers are half the joint ones, so the survivor can
    // land in a higher tier on the same income even though there is now one premium instead of two.
    const ssA = between(25000, 50000, 100);
    const ssB = between(10000, ssA, 100);
    const ordinary = between(60000, 260000, 500);
    const ltcg = pick([0, between(5000, 60000, 500)]);
    const couple = fed('mfj', 2, ordinary, ltcg, ssA + ssB);
    const survivor = fed('single', 1, ordinary, ltcg, ssA);
    const taxUp = survivor.federal - couple.federal;
    const medicareUp = 12 * partB(survivor.agi, 'single') - 24 * partB(couple.agi, 'mfj');
    return {
      prompt: `${RULES}${MEDICARE}A married couple, both age 65 or older and both enrolled in Medicare Part B, files jointly. They have ${usd(ordinary)} of traditional IRA distributions, ${usd(ltcg)} of long-term capital gains and qualified dividends, and Social Security benefits of ${usd(ssA)} (spouse A) and ${usd(ssB)} (spouse B), with no wages. Spouse B dies. In the survivor's first full year filing as single (no dependents), spouse A keeps the larger of the two Social Security benefits and has the same IRA distributions and gains. Using 2026 law and amounts for both years, standard deduction and no credits, and assuming each year's Part B premiums are set by that same year's income, how many dollars more does the survivor pay per year in federal income tax (including any Net Investment Income Tax) plus Part B premiums than the couple paid together? Give a negative number if the survivor pays less. Round to the nearest dollar.${FORMAT}`,
      inputs: { ordinary, ltcg, ssA, ssB },
      answer: Math.round(taxUp + medicareUp),
      tol: 2,
      naive: Math.round(taxUp),
    };
  },
  // Compliance track: a planted fact a reviewer must catch. Each issue is defined in the prompt and set by
  // construction, with a clear gap between cases that have it and cases that don't, so grading needs no judgment.
  rollover_flags() {
    const age55 = rand() < 0.5, nua = rand() < 0.5, cost = rand() < 0.5;
    // AGE55 holds only when all three conditions hold; a "no" case breaks exactly one, so it looks close.
    const breakAge = pick(['sep', 'age', 'plan'] as const);
    const sepAge = age55 || breakAge !== 'sep' ? between(55, 58, 1) : between(48, 53, 1);
    const age = age55 || breakAge !== 'age' ? Math.max(sepAge, between(55, 58, 1)) : between(61, 64, 1);
    const withdraws = age55 || breakAge !== 'plan';
    const balance = between(300000, 1500000, 10000);
    const hasStock = nua || rand() < 0.6;
    const stock = hasStock ? round(balance * (0.15 + rand() * 0.25), 1000) : 0;
    const basis = nua ? round(stock * (0.05 + rand() * 0.2), 1000) : round(stock * (0.85 + rand() * 0.15), 1000);
    const er401 = cost ? pick([0.04, 0.05, 0.1, 0.15]) : pick([1.1, 1.25, 1.4]);
    const erIra = cost ? pick([0.6, 0.75, 0.95]) : pick([0.05, 0.1]);
    const adv = cost ? pick([0.5, 1.0]) : pick([0, 0.25]);
    const codes = [age55 && 'AGE55', cost && 'COST', nua && hasStock && 'NUA'].filter(Boolean).sort().join(',') || 'NONE';
    return {
      prompt: `You are a supervisor reviewing a registered representative's rollover recommendation under Regulation Best Interest's Care Obligation and the factors in FINRA Regulatory Notice 13-45. The client is ${age} and left their employer at age ${sepAge}. ${withdraws ? `They plan to withdraw $${(between(30, 80, 5) * 1000).toLocaleString('en-US')} a year starting now to cover expenses until they claim Social Security.` : 'They do not plan to withdraw anything until after age 59½.'} Their 401(k) is worth ${usd(balance)}${hasStock ? `, including ${usd(stock)} of the former employer's stock with a cost basis of ${usd(basis)}` : ' and holds no employer stock'}. The 401(k)'s funds charge ${er401}% a year in total. The recommendation is to roll the whole 401(k)${hasStock ? ', employer stock included,' : ''} into an IRA invested in funds charging ${erIra}% a year plus a ${adv}% annual advisory fee.\n\nWhich of these issues apply to this client and should have been weighed before recommending the rollover?\n- AGE55: The client left the employer in or after the year they turned 55, is under 59½, and plans withdrawals before 59½. Withdrawals from the 401(k) would avoid the 10% early-withdrawal penalty, but IRA withdrawals would not.\n- NUA: Rolling low-basis employer stock into an IRA gives up net unrealized appreciation tax treatment.\n- COST: The IRA would cost the client more each year than staying in the plan.\n\nAnswer with every code that applies, separated by commas, or NONE. End your reply with a line of the form "ANSWER: <codes>".`,
      inputs: { age, sepAge, withdraws, hasStock, stock, basis, er401, erIra, adv },
      answer: codes,
      tol: 0,
    };
  },
  breakpoint() {
    // Breakpoints under rights of accumulation: the purchase plus same-family holdings of the client, spouse and
    // children under 21. An adult child's account and another fund family's holdings don't count.
    const purchase = between(20000, 240000, 1000);
    const own = pick([0, between(5000, 150000, 1000)]);
    const spouse = pick([0, between(5000, 150000, 1000)]);
    const minor = pick([0, 0, between(2000, 40000, 1000)]);
    const adult = pick([0, between(10000, 120000, 1000)]);
    const other = pick([0, between(20000, 200000, 1000)]);
    const minorAge = between(8, 19, 1), adultAge = between(22, 34, 1);
    const SCHEDULE: [number, number][] = [[50000, 5.75], [100000, 4.5], [250000, 3.5], [500000, 2.5], [1000000, 2.0], [Infinity, 0]];
    const charge = (x: number) => SCHEDULE.find(([top]) => x < top)![1];
    return {
      prompt: `A client is buying ${usd(purchase)} of Class A shares of a mutual fund. The prospectus sales charge, as a percentage of the offering price, is: less than $50,000: 5.75%; $50,000 to less than $100,000: 4.50%; $100,000 to less than $250,000: 3.50%; $250,000 to less than $500,000: 2.50%; $500,000 to less than $1,000,000: 2.00%; $1,000,000 or more: 0%. Under the prospectus's rights of accumulation, the purchase is combined with the current value of holdings in the same fund family owned by the client, the client's spouse, and their children under age 21, in any type of account. Current holdings: the client's IRA in the same fund family, ${usd(own)}; the spouse's taxable account in the same fund family, ${usd(spouse)}; their ${minorAge}-year-old child's account in the same fund family, ${usd(minor)}; their ${adultAge}-year-old child's account in the same fund family, ${usd(adult)}; the client's brokerage holdings in a different fund family, ${usd(other)}. What sales charge percentage should this purchase receive? End your reply with a line of the form "ANSWER: <number>" with no % sign.`,
      inputs: { purchase, own, spouse, minor, adult, other },
      answer: charge(purchase + own + spouse + minor),
      tol: 0.001,
      naive: charge(purchase),
      misreadings: { 'counted adult child': charge(purchase + own + spouse + minor + adult), 'counted other fund family': charge(purchase + own + spouse + minor + other) },
    };
  },
  comms_review() {
    // Violations are bright-line under Rule 2210(d)(1); every compliant sentence shares a keyword with a violation
    // ("guaranteed", "FDIC", a percentage), so matching words alone fails.
    const BAD = [
      'This fund is guaranteed to outperform the stock market over the next five years.',
      'You will earn at least 10% a year in this fund.',
      'There is virtually no risk of losing money with this fund.',
      'Like a bank CD, your investment in this fund is FDIC-insured.',
      'Our analysts project the fund will return 15% next year.',
      'This is a can\'t-miss opportunity that will double your money.',
    ];
    const OK = [
      'The fund invests mainly in large U.S. companies.',
      'The fund is not guaranteed and can lose value, so you could lose money.',
      'Past performance does not guarantee future results.',
      'Please read the prospectus, which describes the fund\'s fees, risks and objectives, before investing.',
      'The fund\'s expense ratio is 0.65% a year, which is taken out of fund assets.',
      'CDs are FDIC-insured up to $250,000 per depositor; mutual fund shares are not FDIC-insured.',
      'We can meet to review whether this fund fits your goals and time horizon.',
    ];
    const nBad = pick([0, 1, 1, 2, 2, 3]);
    const shuffle = <T,>(xs: T[]) => xs.map((x) => [rand(), x] as [number, T]).sort((a, b) => a[0] - b[0]).map((p) => p[1]);
    const bad = shuffle(BAD.map((_, i) => i)).slice(0, nBad);
    const ok = shuffle(OK.map((_, i) => i)).slice(0, 6 - nBad);
    const order = shuffle([...bad.map((i) => ({ bad: true, i })), ...ok.map((i) => ({ bad: false, i }))]);
    const lines = order.map((s, k) => `${k + 1}. ${s.bad ? BAD[s.i] : OK[s.i]}`);
    const flagged = order.map((s, k) => (s.bad ? k + 1 : 0)).filter(Boolean);
    return {
      prompt: `FINRA Rule 2210(d)(1) says retail communications may not contain any false, exaggerated, unwarranted, promissory or misleading statement or claim, and may not predict or project performance. A representative drafted this email to retail clients about a stock mutual fund:\n\n${lines.join('\n')}\n\nWhich numbered sentences violate Rule 2210(d)(1)? End your reply with a line of the form "ANSWER: <sentence numbers separated by commas>", or "ANSWER: NONE" if none do.`,
      inputs: { sentences: order.map((s) => (s.bad ? s.i : 100 + s.i)) },
      answer: flagged.join(',') || 'NONE',
      tol: 0,
    };
  },
};

const PER_TASK = Number(process.argv[2] ?? 50);
const cases: Case[] = [];
const seen = new Set<string>();
// The private set must not repeat a public question, or it isn't held out: PB_EXCLUDE names the public file.
if (process.env.PB_EXCLUDE)
  for (const l of readFileSync(process.env.PB_EXCLUDE, 'utf8').split('\n')) if (l.trim()) seen.add(JSON.parse(l).prompt);
for (const task of Object.keys(gens) as Case['task'][])
  for (let i = 0; i < PER_TASK; i++) {
    // A repeated question would count twice in a model's score, so redraw until it's new.
    let c = gens[task]();
    for (let tries = 0; seen.has(c.prompt) && tries < 100; tries++) c = gens[task]();
    seen.add(c.prompt);
    cases.push({ id: `${task}-${String(i).padStart(3, '0')}`, task, ...c });
  }

const OUT = process.argv[3] ?? new URL('../data/cases.jsonl', import.meta.url).pathname;
writeFileSync(OUT, cases.map((c) => JSON.stringify(c)).join('\n') + '\n');
console.log(`Wrote ${cases.length} cases (${PER_TASK} per task, seed ${process.env.PB_SEED ? 'private' : 'public'}) to ${OUT}`);
