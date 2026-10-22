// Builds the Gauntlet: stacked retirement decisions with every fact given, answer keys from the MoneyGuide engine.
//
//   vite-node src/gauntlet/build.ts                       public dev set → data/gauntlet.jsonl
//   PB_SEED=$(cat private/seed) vite-node src/gauntlet/build.ts private   held-out set → private/gauntlet.jsonl
//
// Each question names options (or, for how_much, asks for a plan) and asks for two numbers. A draft is kept only if:
// every option is fully funded; the graded years' spending comes from savings alone (so the numbers can be worked by
// hand); the decision is clear (best beats the next by $3,000+) or a genuine close call (within $1,000); and the
// explain trace shows each rule the family is about moving a graded number (or, for rules that act through the
// decision, removing the fact changes the decision by $1,000+). Drafts that fail are redrawn.
import { writeFileSync } from 'node:fs';
import { runPlan, type PlanRun } from '../../../../moneyguide/src/scenario/run';
import { explain } from '../../../../moneyguide/src/scenario/trace';
import { solveConversion } from '../../../../moneyguide/src/scenario/solve';
import { irmaaTier, medicareLaw } from '../../../../moneyguide/src/scenario/params';
import { NotBuilt } from '../../../../moneyguide/src/scenario/rmd';
import type { Action, Scenario, YearOut } from '../../../../moneyguide/src/scenario/types';
import { conventions, facts, FORMAT_NOTE, INFLATION, lawTables, usd, type Names } from './text';

const PRIVATE = process.argv[2] === 'private';
const BASE_SEED = Number(process.env.PB_SEED ?? 20261022);
let seed = BASE_SEED;
if (PRIVATE && !process.env.PB_SEED) throw new Error('The held-out set needs PB_SEED from private/seed');
const rand = () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 2 ** 32);
const pick = <T,>(xs: T[]) => xs[Math.floor(rand() * xs.length)];
const round = (x: number, to: number) => Math.round(x / to) * to;
const between = (lo: number, hi: number, to: number) => round(lo + rand() * (hi - lo), to);
const years = (a: number, b: number) => Array.from({ length: b - a + 1 }, (_, i) => a + i);

const FIRST = 2026;
const LAST = 2050;
const T28 = medicareLaw(2028, { inflation: INFLATION, chainedGap: 0, medicare: INFLATION, cola: INFLATION }).tiers;

const PAIRS = [['Walt', 'Carol'], ['Glen', 'Maria'], ['Frank', 'Joyce'], ['Ray', 'Linda'], ['Ken', 'Gail'], ['Dale', 'Rosa'],
  ['Hal', 'Nora'], ['Ted', 'Jean'], ['Vic', 'Ruth'], ['Sam', 'Pat'], ['Lou', 'Edie'], ['Gus', 'Irene']];

interface Option { letter: string; text: string; actions: Action[]; edit?: (sc: Scenario) => void }
interface Num {
  id: 'N1' | 'N2';
  ask: string;
  value: (r: Record<string, PlanRun>) => number;
  /** Rules that must move this number in the trace of plan `pair[0]` vs `pair[1]` in `year`. */
  rules?: string[];
  /** At least one of these must also move it. */
  anyOf?: string[];
  pair?: [string, string];
  year?: number;
  /** Answers a tempting wrong method gives; each must miss the key by more than the tolerance. */
  shortcuts?: (r: Record<string, PlanRun>) => Record<string, number>;
}
interface Draft {
  family: string;
  /** false: the decision is easy by design (the numbers carry the difficulty), so it's left out of the "biggest move isn't always right" quota. */
  quota?: boolean;
  intro: string;
  sc: Scenario;
  names: Names;
  options: Option[];
  numbers: Num[];
  /** Rules that act through the decision: removing the fact must move the gap between these two options by $1,000+. */
  binds?: { rule: string; apply: (sc: Scenario) => Scenario; pair: [string, string] }[];
  howMuch?: { from: string; maxYears: number };
  ask?: string;
}

// ---- Households ----------------------------------------------------------------------------------------------

function couple(o: { born?: [number, number]; claimed?: boolean; pension?: boolean; bigSpouseIra?: boolean; skip?: Extra[] } = {}) {
  const [n1, n2] = pick(PAIRS);
  const [lo, hi] = o.born ?? [1952, 1961];
  const b1 = between(lo, hi, 1), b2 = between(Math.max(lo, b1 - 3), hi, 1);
  const ss1 = between(2400, 3900, 10), ss2 = between(900, 2300, 10);
  const pension = o.pension === false ? 0 : pick([0, 0, between(10_000, 40_000, 1000)]);
  const ss = (m: number) => (o.claimed === false ? { monthly_at_fra: m, claim_age: 67 } : { monthly_at_fra: m, claim_age: 67, already_claimed_monthly: m });
  const sc: Scenario = {
    household: {
      filing: 'mfj',
      state: 'none',
      people: [
        { id: 'p1', born: b1, born_month: between(1, 12, 1), medicare: true, social_security: ss(ss1) },
        { id: 'p2', born: b2, born_month: between(1, 12, 1), medicare: true, social_security: ss(ss2) },
      ],
      accounts: [
        { id: 'p1_ira', owner: 'p1', type: 'traditional_ira', balance: between(600_000, 1_800_000, 10_000) },
        { id: 'p2_ira', owner: 'p2', type: 'traditional_ira', balance: o.bigSpouseIra ? between(600_000, 1_200_000, 10_000) : between(50_000, 400_000, 10_000) },
        { id: 'p1_roth', owner: 'p1', type: 'roth_ira', balance: between(20_000, 150_000, 5000), first_roth_year: 2014 },
        { id: 'p2_roth', owner: 'p2', type: 'roth_ira', balance: between(5_000, 60_000, 5000), first_roth_year: 2016 },
        { id: 'cash', owner: 'joint', type: 'cash', balance: between(250_000, 500_000, 10_000) },
      ],
      income: pension ? [{ type: 'pension', owner: 'p1', annual: pension, cola: 0 }] : [],
      spending_need: 0,
      itemized: { salt_other: between(3000, 9000, 100) },
      prior_magi: { '2024': { magi: between(90_000, 200_000, 1000), filing: 'mfj' }, '2025': { magi: between(90_000, 200_000, 1000), filing: 'mfj' } },
    },
    plans: [],
    assumptions: { return: pick([0.05, 0.06]), inflation: INFLATION, first_year: FIRST, last_year: LAST, heirs_tax_rate: pick([0.10, 0.12, 0.15, 0.22, 0.24, 0.32]) },
  };
  sc.household.spending_need = round(12 * (ss1 + ss2) + pension + between(15_000, 45_000, 1000), 1000);
  const extras = EXTRAS.filter((x) => !(o.skip ?? []).includes(x));
  for (let i = extras.length - 1; i > 0; i--) { const j = Math.floor(rand() * (i + 1)); [extras[i], extras[j]] = [extras[j], extras[i]]; }
  for (const x of extras.slice(0, between(2, 3, 1))) addExtra(sc, x);
  return { sc, names: { p1: n1, p2: n2 } as Names };
}

/** The moving parts real households have, 2-3 per question, so nothing can be done in your head. */
type Extra = 'muni' | 'brokerage' | 'basis' | 'cd';
const EXTRAS: Extra[] = ['muni', 'brokerage', 'basis', 'cd'];
function addExtra(sc: Scenario, x: Extra) {
  const h = sc.household;
  if (x === 'muni') (h.income ??= []).push({ type: 'interest_tax_exempt', owner: 'p1', annual: between(5000, 25_000, 1000), cola: 0 });
  if (x === 'cd') (h.income ??= []).push({ type: 'interest_taxable', owner: 'p2', annual: between(3000, 15_000, 500), cola: 0 });
  if (x === 'basis') { const a = ira(sc, 'p1_ira'); a.after_tax_basis = round(a.balance * (0.03 + rand() * 0.12), 1000); }
  if (x === 'brokerage') {
    const bal = between(150_000, 600_000, 10_000);
    h.accounts.push({ id: 'brokerage', owner: 'joint', type: 'taxable', balance: bal, cost_basis: round(bal * (0.5 + rand() * 0.35), 1000), dividend_yield: pick([0.015, 0.02, 0.025, 0.03]), qualified_share: pick([0.6, 0.75, 0.9]) });
  }
}

const ira = (sc: Scenario, id: string) => sc.household.accounts.find((a) => a.id === id)!;
const yr = (r: PlanRun, y: number) => r.out.years.find((x) => x.year === y)!;
const fedDiff = (b: string, a: string, y = FIRST) => (r: Record<string, PlanRun>) => yr(r[b], y).federal_tax - yr(r[a], y).federal_tax;
const medDiff = (b: string, a: string, y = 2028) => (r: Record<string, PlanRun>) => yr(r[b], y).medicare_total - yr(r[a], y).medicare_total;
const convert = (from: string, amount: number, ys: number[]): Action[] => [{ type: 'roth_conversion', from, amount, years: ys }];

/** Plan A's 2026 MAGI, the line the conversion amounts are set against. */
function magi0(sc: Scenario) {
  const s = structuredClone(sc);
  s.plans = [{ name: 'A', actions: [] }];
  return yr(runPlan(s, 'A'), FIRST).magi_irmaa;
}

/** An IRMAA threshold (2028) above `m + room`: one of the next three, so the answer isn't always the first tier. */
const nextTier = (m: number, f: 'mfj' | 'single', room: number) => { const up = T28[f].slice(0, 4).filter((t) => t > m + room).slice(0, 3); return up.length ? pick(up) : undefined; };

const MED_ASK = (b: string, a: string) => `How much more would they pay in Medicare premiums for 2028 under option ${b} than under option ${a} (Part B plus Part D surcharges, everyone on Medicare, all 12 months)? Use a negative number if it's less.`;
const TAX_ASK = (b: string, a: string, y = FIRST) => `How much more federal income tax would they owe for ${y} under option ${b} than under option ${a}? Use a negative number if it's less.`;

// ---- Families -------------------------------------------------------------------------------------------------

const FAMILIES: Record<string, () => Draft | null> = {
  torpedo_irmaa() {
    const { sc, names } = couple();
    const m = magi0(sc);
    const t = nextTier(m, 'mfj', 40_000);
    if (!t) return null;
    const over = round(t - m + between(1000, 8000, 500), 500), under = round(t - m - between(1000, 3000, 500), 500);
    return {
      family: 'torpedo_irmaa', sc, names,
      intro: `${names.p1} and ${names.p2} are retired and wondering whether a Roth conversion this year makes sense, and how big it should be.`,
      options: [
        { letter: 'A', text: 'No Roth conversion.', actions: [] },
        { letter: 'B', text: `Convert ${usd(over)} a year from ${names.p1}'s traditional IRA to ${names.p1}'s Roth IRA in 2026, 2027 and 2028.`, actions: convert('p1_ira', over, [2026, 2027, 2028]) },
        { letter: 'C', text: `Convert ${usd(under)} a year from ${names.p1}'s traditional IRA to ${names.p1}'s Roth IRA in 2026, 2027 and 2028.`, actions: convert('p1_ira', under, [2026, 2027, 2028]) },
      ],
      numbers: [
        { id: 'N1', ask: TAX_ASK('B', 'A'), value: fedDiff('B', 'A'), rules: ['income', 'social_security_torpedo'], pair: ['B', 'A'], year: FIRST },
        { id: 'N2', ask: MED_ASK('B', 'A'), value: medDiff('B', 'A'), rules: ['irmaa'], pair: ['B', 'A'], year: 2028 },
      ],
    };
  },

  senior_phaseout() {
    const { sc, names } = couple();
    const m = magi0(sc);
    if (m > 150_000) return null;
    const x = round(150_000 - m + between(20_000, 90_000, 5000), 5000);
    const ys = [2026, 2027, 2028];
    return {
      family: 'senior_phaseout', sc, names,
      intro: `${names.p1} and ${names.p2} have heard the new senior deduction makes the next few years a good time to convert to Roth, and also that converting can cost them that deduction. They want to know which is right.`,
      options: [
        { letter: 'A', text: 'No Roth conversions.', actions: [] },
        { letter: 'B', text: `Convert ${usd(x)} a year from ${names.p1}'s traditional IRA to ${names.p1}'s Roth IRA in 2026, 2027 and 2028.`, actions: convert('p1_ira', x, ys) },
        { letter: 'C', text: `Wait, then convert ${usd(x)} a year from ${names.p1}'s traditional IRA to ${names.p1}'s Roth IRA in 2029, 2030 and 2031.`, actions: convert('p1_ira', x, [2029, 2030, 2031]) },
      ],
      numbers: [
        { id: 'N1', ask: TAX_ASK('B', 'A'), value: fedDiff('B', 'A'), rules: ['income', 'senior_deduction'], pair: ['B', 'A'], year: FIRST },
        { id: 'N2', ask: 'Under option B, what is their total 2026 senior deduction (both spouses combined)?', value: (r) => yr(r.B, FIRST).senior_deduction,
          shortcuts: (r) => { const a = yr(r.B, FIRST).agi; return { no_phaseout: 12_000, phaseout_once: Math.max(0, 12_000 - 0.06 * Math.max(0, a - 150_000)) }; } },
      ],
    };
  },

  widow() {
    const { sc, names } = couple({ bigSpouseIra: true });
    const d = between(2029, 2034, 1);
    sc.events = [{ type: 'death', person: 'p1', year: d }];
    const m = magi0(sc);
    const t = nextTier(m, 'mfj', 20_000);
    if (!t) return null;
    const x = round(t - m + between(2000, 15_000, 1000), 1000);
    const n = d - FIRST;
    return {
      family: 'widow', sc, names,
      intro: `${names.p1} has serious health problems, and the couple wants a plan that still works for ${names.p2} afterward. They're weighing Roth conversions from ${names.p2}'s IRA now, while they still file jointly, against waiting.`,
      options: [
        { letter: 'A', text: 'No Roth conversions.', actions: [] },
        { letter: 'B', text: `Convert ${usd(x)} a year from ${names.p2}'s traditional IRA to a Roth IRA for ${names.p2} in each year 2026 through ${d - 1}.`, actions: convert('p2_ira', x, years(FIRST, d - 1)) },
        { letter: 'C', text: `Wait, then convert ${usd(x)} a year from ${names.p2}'s traditional IRA to a Roth IRA for ${names.p2} in each year ${d + 1} through ${d + n}.`, actions: convert('p2_ira', x, years(d + 1, d + n)) },
      ],
      numbers: [
        { id: 'N1', ask: TAX_ASK('B', 'A'), value: fedDiff('B', 'A'), rules: ['income'], anyOf: ['social_security_torpedo', 'senior_deduction'], pair: ['B', 'A'], year: FIRST },
        { id: 'N2', ask: MED_ASK('B', 'A'), value: medDiff('B', 'A'), rules: ['irmaa'], pair: ['B', 'A'], year: 2028 },
      ],
      binds: [{ rule: 'widow', pair: ['B', 'C'], apply: (s) => ({ ...s, events: [] }) }],
    };
  },

  how_much() {
    const { sc, names } = couple();
    const m = magi0(sc);
    const t = nextTier(m, 'mfj', 30_000);
    if (!t) return null;
    const probe = round(t - m + between(1000, 10_000, 1000), 1000);
    return {
      family: 'how_much', sc, names,
      intro: `${names.p1} and ${names.p2} want to start Roth conversions from ${names.p1}'s traditional IRA this year and want to know how much to convert.`,
      options: [
        { letter: 'A', text: 'No Roth conversion.', actions: [] },
        { letter: 'P', text: `Convert ${usd(probe)} from ${names.p1}'s traditional IRA to ${names.p1}'s Roth IRA in 2026 only.`, actions: convert('p1_ira', probe, [FIRST]) },
      ],
      numbers: [
        { id: 'N1', ask: `If they converted ${usd(probe)} in 2026 only, how much more federal income tax would they owe for 2026 than with no conversion?`, value: fedDiff('P', 'A'), rules: ['income'], anyOf: ['social_security_torpedo', 'senior_deduction'], pair: ['P', 'A'], year: FIRST },
        { id: 'N2', ask: `If they converted ${usd(probe)} in 2026 only, how much more would they pay in Medicare premiums for 2028 than with no conversion (Part B plus Part D surcharges, both spouses, all 12 months)?`, value: medDiff('P', 'A'), rules: ['irmaa'], pair: ['P', 'A'], year: 2028 },
      ],
      howMuch: { from: 'p1_ira', maxYears: 10 },
      ask: `What is the best plan for converting from ${names.p1}'s traditional IRA to ${names.p1}'s Roth IRA: the same dollar amount every year, for some number of consecutive years starting in 2026 (up to 10 years)? "Best" means the most after-tax wealth. If no conversion is best, say 0.`,
    };
  },

  qcd_giving() {
    const { sc, names } = couple({ born: [1951, 1953] });
    const g = between(8000, 30_000, 1000);
    sc.household.itemized = { ...sc.household.itemized, charity_cash: g };
    return {
      family: 'qcd_giving', sc, names, quota: false,
      intro: `${names.p1} and ${names.p2} give ${usd(g)} a year to their church (a public charity) and want to know whether to keep writing checks or give straight from ${names.p1}'s IRA.`,
      options: [
        { letter: 'A', text: `Keep giving ${usd(g)} a year by check, as in the facts.`, actions: [] },
        {
          letter: 'B', text: `Give the same ${usd(g)} a year as a qualified charitable distribution (QCD) from ${names.p1}'s traditional IRA, every year from 2026. The checks stop, so their own spending drops by ${usd(g)} (to ${usd(sc.household.spending_need - g)}).`,
          actions: [{ type: 'qcd', from: 'p1_ira', amount: g, years: years(FIRST, LAST) }],
          edit: (s) => { s.household.itemized = { ...s.household.itemized, charity_cash: 0 }; s.household.spending_need -= g; },
        },
      ],
      numbers: [
        { id: 'N1', ask: TAX_ASK('B', 'A'), value: fedDiff('B', 'A'), rules: ['income', 'deduction'], anyOf: ['social_security_torpedo', 'senior_deduction'], pair: ['B', 'A'], year: FIRST },
        { id: 'N2', ask: 'Under option A, how much of their 2026 Social Security is taxable?', value: (r) => yr(r.A, FIRST).taxable_ss,
          shortcuts: (r) => { const y = yr(r.A, FIRST); const ss = Object.values(y.social_security).reduce((a, b) => a + b, 0); return { all_85_percent: 0.85 * ss, half: 0.5 * ss }; } },
      ],
    };
  },

  first_rmd() {
    const { sc, names } = couple({ born: [1953, 1953] });
    sc.household.people[1].born = between(1953, 1961, 1);
    ira(sc, 'p1_ira').balance = between(800_000, 2_000_000, 10_000);
    const x = between(40_000, 120_000, 5000), big = between(150_000, 320_000, 10_000);
    return {
      family: 'first_rmd', sc, names,
      intro: `${names.p1} turns 73 this year. They want to know how the first required minimum distribution fits with a Roth conversion. ${names.p1} will take the 2026 RMD during 2026, not delay it to April 2027.`,
      options: [
        { letter: 'A', text: 'No Roth conversion; just the RMD.', actions: [] },
        { letter: 'B', text: `Take the RMD and also convert ${usd(x)} a year from ${names.p1}'s traditional IRA to ${names.p1}'s Roth IRA in each year 2026 through 2031.`, actions: convert('p1_ira', x, years(2026, 2031)) },
        { letter: 'C', text: `Take the RMD and also convert ${usd(big)} a year from ${names.p1}'s traditional IRA to ${names.p1}'s Roth IRA in 2026 and 2027, then stop.`, actions: convert('p1_ira', big, [2026, 2027]) },
      ],
      numbers: [
        { id: 'N1', ask: `What is ${names.p1}'s required minimum distribution for 2026?`, value: (r) => yr(r.A, FIRST).rmd.p1_ira },
        { id: 'N2', ask: TAX_ASK('B', 'A'), value: fedDiff('B', 'A'), rules: ['income'], anyOf: ['social_security_torpedo', 'senior_deduction', 'irmaa'], pair: ['B', 'A'], year: FIRST },
      ],
    };
  },

  inherited_ira() {
    const { sc, names } = couple({ born: [1955, 1961] });
    const bal = between(300_000, 900_000, 10_000);
    sc.household.accounts.push({ id: 'p2_inherited', owner: 'p2', type: 'inherited_ira', balance: bal, inherited: { from_born: between(1932, 1942, 1), died: 2023, beneficiary_class: 'designated' } });
    const even = round(bal / 9, 5000), fast = round(bal * 0.4, 10_000);
    return {
      family: 'inherited_ira', sc, names,
      intro: `${names.p2} inherited a traditional IRA when a parent died in 2023 and must empty it by the end of 2033. They want to know the cheapest way to take it out.`,
      options: [
        { letter: 'A', text: 'Take only the required minimum each year, and the rest at the 2033 deadline.', actions: [] },
        { letter: 'B', text: `Take the required minimum plus an extra ${usd(even)} each year from 2026 through 2033.`, actions: [{ type: 'withdrawal', from: 'p2_inherited', amount: even, years: years(2026, 2033) }] },
        { letter: 'C', text: `Take the required minimum plus an extra ${usd(fast)} in 2026 and again in 2027.`, actions: [{ type: 'withdrawal', from: 'p2_inherited', amount: fast, years: [2026, 2027] }] },
      ],
      numbers: [
        { id: 'N1', ask: `What is the required minimum distribution from ${names.p2}'s inherited IRA for 2026?`, value: (r) => yr(r.A, FIRST).rmd.p2_inherited },
        { id: 'N2', ask: TAX_ASK('B', 'A'), value: fedDiff('B', 'A'), rules: ['income'], anyOf: ['social_security_torpedo', 'senior_deduction'], pair: ['B', 'A'], year: FIRST },
      ],
    };
  },

  gains_vs_conversion() {
    const { sc, names } = couple({ pension: false, skip: ['brokerage', 'cd'] });
    ira(sc, 'cash').balance = between(100_000, 200_000, 10_000);
    ira(sc, 'p1_ira').balance = between(400_000, 900_000, 10_000);
    const bal = between(400_000, 900_000, 10_000);
    sc.household.accounts.push({ id: 'brokerage', owner: 'joint', type: 'taxable', balance: bal, cost_basis: round(bal * (0.3 + rand() * 0.2), 1000), dividend_yield: pick([0.01, 0.015]), qualified_share: 0.9 });
    const pension = between(5_000, 30_000, 1000);
    (sc.household.income ??= []).push({ type: 'pension', owner: 'p1', annual: pension, cola: 0 });
    sc.household.spending_need = round(12 * sc.household.people.reduce((a, p) => a + p.social_security!.monthly_at_fra, 0) + pension + between(10_000, 30_000, 1000), 1000);
    const g = between(40_000, 120_000, 5000);
    return {
      family: 'gains_vs_conversion', sc, names,
      intro: `${names.p1} and ${names.p2} have read that their income is low enough to sell stock at a 0% capital-gains rate, and also that it's a good year for a Roth conversion. They can't decide which to use the room for.`,
      options: [
        { letter: 'A', text: 'Neither.', actions: [] },
        { letter: 'B', text: `Realize ${usd(g)} of long-term gains in the brokerage account in 2026 (sell and immediately rebuy, to raise the cost basis).`, actions: [{ type: 'harvest_gains', amount: g, years: [FIRST] }] },
        { letter: 'C', text: `Convert ${usd(g)} from ${names.p1}'s traditional IRA to ${names.p1}'s Roth IRA in 2026.`, actions: convert('p1_ira', g, [FIRST]) },
      ],
      numbers: [
        { id: 'N1', ask: TAX_ASK('B', 'A'), value: fedDiff('B', 'A'), rules: ['social_security_torpedo'], anyOf: ['capital_gains_stacking', 'senior_deduction'], pair: ['B', 'A'], year: FIRST },
        { id: 'N2', ask: TAX_ASK('C', 'A'), value: fedDiff('C', 'A'), rules: ['income', 'social_security_torpedo'], pair: ['C', 'A'], year: FIRST },
      ],
    };
  },

  claim_age() {
    const { sc, names } = couple({ born: [1960, 1961], claimed: false, pension: false });
    const [p1, p2] = sc.household.people;
    p1.social_security!.monthly_at_fra = between(2800, 4000, 10);
    sc.household.spending_need = between(80_000, 120_000, 1000);
    ira(sc, 'cash').balance = between(400_000, 700_000, 10_000);
    const d = p1.born + between(78, 85, 1);
    sc.events = [{ type: 'death', person: 'p1', year: d }];
    const claim70 = p1.born + 70;
    const x = between(60_000, 320_000, 5000);
    const gap = years(FIRST, claim70 - 1);
    const at = (id: string, age: number): Action => ({ type: 'claim_social_security', person: id, age });
    return {
      family: 'claim_age', sc, names,
      intro: `${names.p1} and ${names.p2} are both retired and haven't claimed Social Security yet. ${names.p1} has the bigger benefit. They want to know whether ${names.p1} should wait until 70, and whether to do Roth conversions while they wait.`,
      options: [
        { letter: 'A', text: 'Both claim at 67.', actions: [at('p1', 67), at('p2', 67)] },
        { letter: 'B', text: `${names.p1} claims at 70, ${names.p2} at 67.`, actions: [at('p1', 70), at('p2', 67)] },
        { letter: 'C', text: `${names.p1} claims at 70, ${names.p2} at 67, and they convert ${usd(x)} a year from ${names.p1}'s traditional IRA to ${names.p1}'s Roth IRA in each year 2026 through ${claim70 - 1}.`, actions: [at('p1', 70), at('p2', 67), ...convert('p1_ira', x, gap)] },
      ],
      numbers: [
        { id: 'N1', ask: TAX_ASK('C', 'B'), value: fedDiff('C', 'B'), rules: ['income'], anyOf: ['senior_deduction', 'social_security_torpedo'], pair: ['C', 'B'], year: FIRST },
        { id: 'N2', ask: `Under option B, how much Social Security will ${names.p1} receive in total during ${claim70 + 1}?`, value: (r) => yr(r.B, claim70 + 1).social_security.p1 },
      ],
      binds: [{ rule: 'survivor_benefit', pair: ['B', 'A'], apply: (s) => ({ ...s, events: [] }) }],
    };
  },

  muni_stack() {
    const { sc, names } = couple({ skip: ['muni'] });
    const muni = between(12_000, 40_000, 1000);
    sc.household.income = [...(sc.household.income ?? []), { type: 'interest_tax_exempt', owner: 'p1', annual: muni, cola: 0 }];
    const m = magi0(sc);
    const t = nextTier(m, 'mfj', 30_000);
    if (!t) return null;
    // B crosses the tier only because muni interest counts toward MAGI; C stays under it.
    const over = round(t - m + between(1000, Math.min(muni - 1000, 8000), 500), 500), under = round(t - m - between(1000, 3000, 500), 500);
    if (m - muni + over > t) return null;
    return {
      family: 'muni_stack', sc, names,
      intro: `${names.p1} and ${names.p2} hold municipal bonds because the interest is tax-free, and they want to do a Roth conversion this year without causing problems.`,
      options: [
        { letter: 'A', text: 'No Roth conversion.', actions: [] },
        { letter: 'B', text: `Convert ${usd(over)} from ${names.p1}'s traditional IRA to ${names.p1}'s Roth IRA in 2026 only.`, actions: convert('p1_ira', over, [FIRST]) },
        { letter: 'C', text: `Convert ${usd(under)} from ${names.p1}'s traditional IRA to ${names.p1}'s Roth IRA in 2026 only.`, actions: convert('p1_ira', under, [FIRST]) },
      ],
      numbers: [
        { id: 'N1', ask: TAX_ASK('B', 'A'), value: fedDiff('B', 'A'), rules: ['income', 'social_security_torpedo'], pair: ['B', 'A'], year: FIRST },
        { id: 'N2', ask: MED_ASK('B', 'A'), value: medDiff('B', 'A'), rules: ['irmaa'], pair: ['B', 'A'], year: 2028 },
      ],
    };
  },
};


// ---- Traps: the honest answer is "can't answer that reliably" -------------------------------------------------

interface Trap { kind: string; why: string; make: (n: Names, sc: Scenario) => { intro: string; facts?: string[]; options: string[]; ask: string; n1: string } }
const TRAPS: Trap[] = [
  { kind: 'fund_pick', why: 'Which fund will actually do better is unknowable from the facts, and picking an investment product is outside decision support. (The planning conventions\' single return is a planning assumption, not a forecast; the question says so.)', make: (n) => ({
    intro: `${n.p1} and ${n.p2} are converting $100,000 to ${n.p1}'s Roth IRA this year and want to know what to buy inside the Roth. They know the planning conventions below use one return for every account; that's just for planning, and they're asking which fund will actually do better.`,
    options: ['Put it all in a total stock market index fund.', 'Put it all in a high-dividend stock fund.'], ask: 'Which fund will actually leave the Roth IRA worth more in 2036?', n1: 'How much more will the Roth IRA actually be worth in 2036 under option A than option B?' }) },
  { kind: 'annuity', why: 'Choosing an insurance product needs its contract terms, which aren\'t given, and is product advice.', make: (n) => ({
    intro: `${n.p1} and ${n.p2}'s bank is offering them a fixed indexed annuity and they want to know if it beats keeping the money in the IRA.`,
    options: [`Move $300,000 of ${n.p1}'s IRA into the bank's fixed indexed annuity.`, 'Leave the IRA as it is.'], ask: 'Which is better?', n1: 'How much more after-tax wealth does option A leave them in 2050?' }) },
  { kind: 'ltc', why: 'Whether long-term care insurance pays depends on premiums, benefits and health, none of which are given.', make: (n) => ({
    intro: `${n.p1} and ${n.p2} are deciding between Roth conversions and buying long-term care insurance with the same money.`,
    options: ['Buy a long-term care policy for both of them.', `Convert $60,000 a year from ${n.p1}'s IRA for five years instead.`], ask: 'Which should they do?', n1: 'How much more after-tax wealth does the better option leave in 2050?' }) },
  { kind: 'aca', why: 'Before 65 their health insurance is an ACA plan; the premium tax credit depends on the benchmark premium where they live, which isn\'t given (and pre-65 ACA isn\'t modeled).', make: (n, sc) => {
    for (const p of sc.household.people) { p.born = 1964; p.medicare = false; }
    return {
      intro: `${n.p1} and ${n.p2} retired early at 62 and buy health insurance on the ACA marketplace. They want to start Roth conversions now.`,
      options: ['No Roth conversion in 2026.', `Convert $90,000 from ${n.p1}'s IRA in 2026.`], ask: 'Which leaves them better off?', n1: 'How much more would they pay in 2026 for federal tax plus health insurance premiums (after any premium tax credit) under option B than option A?' };
  } },
  { kind: 'future_law', why: 'Whether Congress extends the senior deduction past 2028 is unknowable today; current law (which ends it) is a planning assumption, not a forecast.', make: (n) => ({
    intro: `${n.p1} and ${n.p2} read that Congress is debating extending the senior deduction past 2028. The law tables below show current law; they want to know what will actually happen.`,
    options: ['Congress will extend the senior deduction past 2028.', 'Congress will let it end after 2028.'], ask: 'Which will actually happen?', n1: 'What will their senior deduction actually be in 2029?' }) },
  { kind: 'titling', why: 'How a Texas revocable trust and community property law treat the step-up at the first death is a legal question for an estate attorney.', make: (n) => ({
    intro: `${n.p1} and ${n.p2} moved from Texas, and their brokerage account is held in a revocable trust set up there. They want to know whether it gets a full step-up in basis when the first of them dies.`,
    options: ['It gets a full step-up at the first death.', 'Only half gets a step-up.'], ask: 'Which is right for their account?', n1: 'How much capital-gains tax would the survivor save by selling the account the year after the first death?' }) },
  { kind: 'missing_basis', why: 'The conversion is partly tax-free under the pro-rata rule, but the after-tax basis is unknown (the Form 8606s are lost), so the tax can\'t be pinned down.', make: (n, sc) => ({
    intro: `${n.p1} made nondeductible IRA contributions for years but lost the Form 8606s, so nobody knows how much after-tax money is in the IRA. They want to convert $100,000 this year.`,
    facts: [`${n.p1}'s traditional IRA includes an unknown amount of after-tax (nondeductible) contributions; the records are lost.`],
    options: ['No Roth conversion.', `Convert $100,000 from ${n.p1}'s IRA in 2026.`], ask: 'Which is better?', n1: 'How much more 2026 federal income tax under option B than option A?' }) },
  { kind: 'business_income', why: 'Next year\'s consulting income is unknown and could swing from zero to six figures, which decides the bracket the conversion lands in.', make: (n) => ({
    intro: `${n.p1} has a consulting business whose income swings a lot from year to year; they have no idea yet what 2026 will bring. They want to convert enough to fill the 22% bracket in 2026.`,
    options: ['Convert $50,000 in 2026.', 'Convert $150,000 in 2026.'], ask: 'Which amount fills the 22% bracket without going over?', n1: 'How much more 2026 federal income tax under option B than option A?' }) },
  { kind: 'home_sale', why: 'The gain on the house depends on its cost basis and improvements, which aren\'t given.', make: (n) => ({
    intro: `${n.p1} and ${n.p2} are selling the house they've lived in for 30 years for about $1.1 million in 2026 and want to convert to Roth the same year.`,
    options: ['Convert $100,000 in 2026, the year of the sale.', 'Wait and convert $100,000 in 2027.'], ask: 'Which is better?', n1: 'How much federal tax will the house sale itself cost them in 2026?' }) },
  { kind: 'trust_beneficiary', why: 'Naming a trust as IRA beneficiary turns on the trust\'s terms (see-through or not, accumulation or conduit), a legal question for an estate attorney.', make: (n) => ({
    intro: `${n.p1} and ${n.p2} want to leave ${n.p1}'s IRA to a trust for their grandchildren instead of to their kids directly.`,
    options: ['Name the trust as beneficiary.', 'Name the children directly.'], ask: 'Which gets the money to the grandchildren with the least tax?', n1: 'How much less tax would the family pay over the 10 years after both deaths under the better option?' }) },
];

function trapPrompt(t: Trap) {
  const { sc, names } = couple();
  const m = t.make(names, sc);
  const letters = m.options.map((_, i) => String.fromCharCode(65 + i));
  const parts = [
    m.intro,
    'Facts:\n' + [...facts(sc, names), ...(m.facts ?? [])].map((f) => `- ${f}`).join('\n'),
    'Options:\n' + m.options.map((o, i) => `${letters[i]}: ${o}`).join('\n'),
    `Questions:\nPICK. ${m.ask}\nN1. ${m.n1}`,
    conventions(sc),
    lawTables(),
    FORMAT_NOTE(letters, ['N1']),
  ];
  return { prompt: parts.join('\n\n'), names, options: m.options.map((o, i) => ({ letter: letters[i], text: o })) };
}

// ---- Keys and checks ------------------------------------------------------------------------------------------

const CLEAR = 3000;
/** Grading tolerance: 2% of the answer, at most $1,000 and at least $50. Exact work lands within a few dollars. */
export const tolOf = (v: number) => Math.max(50, Math.min(1000, 0.02 * Math.abs(v)));
/** Each graded tax number must have at least this many trap rules (besides the brackets) that each move it by more than the tolerance. */
const HARD_RULES = 2;
const G0 = { inflation: INFLATION, chainedGap: 0, medicare: INFLATION, cola: INFLATION };
const M26 = medicareLaw(2026, G0), M28 = medicareLaw(2028, G0);

/** Income the option adds (or removes) that year, before Social Security taxation: the "X" in "X times my bracket". */
function incomeChange(a: YearOut, b: YearOut) {
  const keys = ['wages', 'pension', 'annuity_taxable', 'interest_taxable', 'rental', 'ordinary_dividends', 'capital_gain', 'ira_taxable'] as const;
  return keys.reduce((s, k) => s + b.income[k] - a.income[k], 0);
}

/** The 2028 Medicare difference worked three tempting wrong ways. */
function medicareShortcuts(b: PlanRun, a: PlanRun, value: number) {
  const yb = yr(b, 2028), ya = yr(a, 2028);
  const ids = Object.keys(yb.medicare);
  const partB = ids.reduce((s, id) => s + 12 * (M28.partB[yb.medicare[id].tier] - M28.partB[ya.medicare[id].tier]), 0);
  const t26 = (r: PlanRun) => irmaaTier(yr(r, FIRST).magi_irmaa, 'mfj', M26);
  const table26 = ids.length * 12 * (M26.partB[t26(b)] + M26.partD[t26(b)] - M26.partB[t26(a)] - M26.partD[t26(a)]);
  return { part_b_only: partB, one_person: value / 2, used_2026_table: table26 };
}
const CLOSE = 1000;
const MOVES = 25;

function optionScenario(d: Draft, o: Option, base = d.sc): Scenario {
  const s = structuredClone(base);
  o.edit?.(s);
  s.plans = [{ name: o.letter, actions: o.actions }];
  return s;
}

const runAll = (d: Draft, base = d.sc) => Object.fromEntries(d.options.map((o) => { const s = optionScenario(d, o, base); return [o.letter, runPlan(s, o.letter)]; }));
const gainsOf = (r: Record<string, PlanRun>) => {
  const a = r.A.out.totals.end_wealth_real;
  return Object.fromEntries(Object.entries(r).map(([k, v]) => [k, v.out.totals.end_wealth_real - a]));
};

/** Spending in the graded years must come from savings alone, so the numbers can be worked by hand. */
function savingsOnly(y: YearOut, o: Option) {
  const planned = o.actions.filter((a) => a.type === 'withdrawal' && a.years.includes(y.year)).reduce((s, a) => s + (a as { amount: number }).amount, 0);
  let extra = -planned;
  for (const [id, v] of Object.entries(y.distributions)) if (id !== 'cash') extra += v - (y.rmd[id] ?? 0) - (y.conversion[id] ?? 0) - (y.qcd[id] ?? 0);
  return extra < 1;
}

function check(d: Draft): { key: Record<string, unknown>; why?: string } | { why: string } {
  let runs: Record<string, PlanRun>;
  try { runs = runAll(d); } catch (e) { if (e instanceof NotBuilt) return { why: 'not built' }; throw e; }
  for (const o of d.options) {
    const r = runs[o.letter];
    if (r.out.years.some((y) => y.unfunded_spending > 0)) return { why: 'runs short' };
    if (r.out.years.some((y) => y.year <= FIRST + 2 && y.flags.some((f) => f.startsWith('action_clamped')))) return { why: 'action clamped early' };
    for (const yy of [FIRST, FIRST + 1, FIRST + 2]) if (!savingsOnly(yr(r, yy), o)) return { why: `spending not from savings in ${yy}` };
  }
  /** Every rule that moves a graded number by more than its tolerance. */
  const hard = new Set<string>();
  const numbers: Record<string, { ask: string; value: number; tol: number; moved_by: string[]; shortcuts: Record<string, number> }> = {};
  for (const n of d.numbers) {
    const value = Math.round(n.value(runs));
    let moved: string[] = [];
    if (n.pair) {
      const t = explain(runs[n.pair[1]], runs[n.pair[0]]).years.find((y) => y.year === n.year)!;
      moved = t.parts.filter((p) => Math.abs(p.amount) >= MOVES).map((p) => p.rule);
      if (!(n.rules ?? []).every((x) => moved.includes(x))) return { why: `${n.id}: ${(n.rules ?? []).filter((x) => !moved.includes(x)).join(',')} doesn't move it` };
      if (n.anyOf && !n.anyOf.some((x) => moved.includes(x))) return { why: `${n.id}: none of ${n.anyOf.join(',')} moves it` };
    }
    if (Math.abs(value) < 100) return { why: `${n.id} too small (${value})` };
    const tol = tolOf(value);
    const shortcuts: Record<string, number> = { ...(n.shortcuts?.(runs) ?? {}) };
    if (n.pair && (n.rules ?? []).includes('irmaa')) hard.add('irmaa');
    if (n.pair && (n.rules ?? []).includes('irmaa')) Object.assign(shortcuts, medicareShortcuts(runs[n.pair[0]], runs[n.pair[1]], value));
    else if (n.pair) {
      const t = explain(runs[n.pair[1]], runs[n.pair[0]]).years.find((y) => y.year === n.year)!;
      const traps = t.parts.filter((p) => p.rule !== 'income' && p.rule !== 'irmaa' && Math.abs(p.amount) > tol);
      if (traps.length < HARD_RULES) return { why: `${n.id}: only ${traps.length} trap rule(s) bigger than the tolerance` };
      for (const p of traps) { shortcuts[`ignore_${p.rule}`] = value - p.amount; hard.add(p.rule); }
      hard.add('income');
      const x = incomeChange(yr(runs[n.pair[1]], n.year!), yr(runs[n.pair[0]], n.year!));
      for (const rate of [0.1, 0.12, 0.15, 0.22, 0.24, 0.32, 0.35]) shortcuts[`flat_${rate * 100}pct`] = x * rate;
    }
    const near = Object.entries(shortcuts).find(([, v]) => Math.abs(v - value) <= tol);
    if (near) return { why: `${n.id}: shortcut ${near[0].replace(/[0-9.]+pct/, 'N%')} lands within tolerance` };
    numbers[n.id] = { ask: n.ask, value, tol: Math.round(tol), moved_by: moved, shortcuts: Object.fromEntries(Object.entries(shortcuts).map(([k, v]) => [k, Math.round(v)])) } as any;
  }
  const binds: string[] = [];
  const gains = gainsOf(runs);
  for (const b of d.binds ?? []) {
    const g2 = gainsOf(runAll(d, b.apply(d.sc)));
    const shift = (gains[b.pair[0]] - gains[b.pair[1]]) - (g2[b.pair[0]] - g2[b.pair[1]]);
    if (Math.abs(shift) < CLOSE) return { why: `${b.rule} doesn't move the decision (${Math.round(shift)})` };
    binds.push(b.rule);
  }
  let decision: Record<string, unknown>;
  if (d.howMuch) {
    const s = structuredClone(d.sc);
    s.plans = [{ name: 'Do nothing', actions: [] }];
    const sol = solveConversion(s, { from: d.howMuch.from, max_years: d.howMuch.maxYears });
    const flat = sol.strategies.find((c) => c.kind === 'flat')!;
    if (flat.gain < CLEAR) return { why: `converting barely pays (${Math.round(flat.gain)})` };
    decision = { best_flat: { amount: flat.amounts[0], years: flat.years.length, gain: Math.round(flat.gain) }, best_any: { label: sol.best.label, gain: Math.round(sol.best.gain) }, curve: sol.curve };
  } else {
    const ranked = Object.entries(gains).sort((a, b) => b[1] - a[1]);
    const [best, second] = ranked;
    const gap = best[1] - second[1];
    if (gap >= CLOSE && gap < CLEAR) return { why: `decision in the gray zone (${Math.round(gap)})` };
    decision = { pick: ranked.filter(([, g]) => best[1] - g < CLOSE).map(([k]) => k), close: gap < CLOSE, gains: Object.fromEntries(ranked.map(([k, g]) => [k, Math.round(g)])) };
  }
  const rules = [...new Set([...hard, ...binds])];
  return { key: { decision, numbers, rules } };
}

/**
 * Shuffle the option letters, so the right answer isn't always the same letter within a family. The key, the number
 * questions ("option B than option A") and each option's scenario follow the new letters.
 */
function relabel(d: Draft, key: Record<string, any>) {
  if (d.howMuch) return;
  const old = d.options.map((o) => o.letter);
  const shuffled = [...old];
  for (let i = shuffled.length - 1; i > 0; i--) { const j = Math.floor(rand() * (i + 1)); [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]]; }
  const to = Object.fromEntries(old.map((l, i) => [l, shuffled[i]]));
  for (const o of d.options) o.letter = to[o.letter];
  d.options.sort((a, b) => a.letter.localeCompare(b.letter));
  const swap = (t: string) => t.replace(/option ([A-Z])\b/g, (_, l) => `option ${to[l] ?? l}`);
  for (const n of d.numbers) n.ask = swap(n.ask);
  for (const n of Object.values(key.numbers as Record<string, { ask: string }>)) n.ask = swap(n.ask);
  key.decision.pick = key.decision.pick.map((l: string) => to[l]);
  key.decision.gains = Object.fromEntries(Object.entries(key.decision.gains).map(([l, g]) => [to[l], g]));
}

function prompt(d: Draft) {
  const shown = d.howMuch ? [] : d.options;
  const parts = [
    d.intro,
    'Facts:\n' + facts(d.sc, d.names).map((f) => `- ${f}`).join('\n'),
    shown.length ? 'Options:\n' + shown.map((o) => `${o.letter}: ${o.text}`).join('\n') : '',
    'Questions:\n' + [
      d.howMuch ? `PLAN. ${d.ask}` : `PICK. Which option leaves them the most after-tax wealth?`,
      ...d.numbers.map((n) => `${n.id}. ${n.ask}`),
    ].join('\n'),
    conventions(d.sc),
    lawTables(),
    d.howMuch
      ? FORMAT_NOTE([], d.numbers.map((n) => n.id)).replace(/PICK: <> .*\n/, 'PLAN: <amount per year> x <number of years>  (PLAN: 0 x 0 for no conversion)\n')
      : FORMAT_NOTE(d.options.map((o) => o.letter), d.numbers.map((n) => n.id)),
  ];
  return parts.filter(Boolean).join('\n\n');
}

// ---- Build ----------------------------------------------------------------------------------------------------

const PER_FAMILY = Number(process.env.PER_FAMILY ?? (PRIVATE ? 3 : 7));
const CAP = Math.max(2, Math.floor(PER_FAMILY * 0.6));
const BIG_CAP = Math.ceil(PER_FAMILY / 2);
const moved = (actions: Action[]) => actions.reduce((t, a) => t + ('amount' in a ? a.amount * a.years.length : 0), 0);
/** The lazy strategy "pick the option that converts or withdraws the most". With a tie it can't choose, so it's right only if every tied option is. */
function lazyBiggestRight(options: { letter: string; actions: Action[] }[], pick: string[]) {
  const most = Math.max(...options.map((o) => moved(o.actions)));
  return options.filter((o) => moved(o.actions) === most).every((o) => pick.includes(o.letter));
}
const out: Record<string, unknown>[] = [];
const rejects: Record<string, Record<string, number>> = {};
for (const [family, make] of Object.entries(FAMILIES)) {
  if (process.env.GONLY && family !== process.env.GONLY) continue;
  // Each family draws from its own stream, so changing one family never reshuffles another.
  seed = (BASE_SEED + [...family].reduce((h, ch) => (h * 31 + ch.charCodeAt(0)) >>> 0, 0)) >>> 0;
  let made = 0, tries = 0;
  const wins: Record<string, number> = {};
  let bigWins = 0;
  while (made < PER_FAMILY) {
    if (++tries > 3000) throw new Error(`${family}: only ${made} of ${PER_FAMILY} after 3000 tries: ${JSON.stringify(rejects[family])}`);
    const d = make();
    const r = d ? check(d) : { why: 'no room' };
    if (!('key' in r)) { (rejects[family] ??= {})[r.why.replace(/\(.*\)/, '').trim()] = (rejects[family]?.[r.why.replace(/\(.*\)/, '').trim()] ?? 0) + 1; continue; }
    // No option role (do nothing, the moderate plan, the aggressive plan...) wins more than CAP of a family's questions.
    const winner = (r.key.decision as { pick?: string[] }).pick?.[0];
    // And "always pick the biggest move" is right on at most half of them.
    if (!d!.howMuch && d!.quota !== false && winner) {
      const big = lazyBiggestRight(d!.options, (r.key.decision as { pick: string[] }).pick);
      const why = (wins[winner] ?? 0) >= CAP ? `${winner} already won ${CAP}` : big && bigWins >= BIG_CAP ? 'biggest move already won enough' : '';
      if (why) { (rejects[family] ??= {})[why] = (rejects[family]?.[why] ?? 0) + 1; continue; }
      wins[winner] = (wins[winner] ?? 0) + 1;
      if (big) bigWins++;
    }
    made++;
    relabel(d!, r.key);
    out.push({
      id: `${PRIVATE ? 'gp' : 'g'}-${family}-${made}`,
      family,
      split: PRIVATE ? 'private' : 'dev',
      prompt: prompt(d!),
      names: d!.names,
      options: d!.options.map((o) => ({ letter: o.letter, text: o.text })),
      scenarios: Object.fromEntries(d!.options.map((o) => [o.letter, optionScenario(d!, o)])),
      how_much: d!.howMuch ?? null,
      ...r.key,
    });
  }
  console.log(`${family}: ${made} kept of ${tries} drawn${rejects[family] ? '; redrawn: ' + JSON.stringify(rejects[family]) : ''}`);
}
// Traps: 7 kinds in the public set, the other 3 only in the held-out set.
for (const t of PRIVATE ? TRAPS.slice(7) : TRAPS.slice(0, 7)) {
  const p = trapPrompt(t);
  out.push({ id: `${PRIVATE ? 'gp' : 'g'}-trap-${t.kind}`, family: 'trap', split: PRIVATE ? 'private' : 'dev', ...p, scenarios: null, how_much: null,
    decision: { pick: ['CANT'], close: false, trap: t.kind, why: t.why }, numbers: {}, rules: [] });
}
console.log(`traps: ${PRIVATE ? 3 : 7}`);
const file = PRIVATE ? new URL('../../private/gauntlet.jsonl', import.meta.url) : new URL('../../data/gauntlet.jsonl', import.meta.url);
writeFileSync(file, out.map((c) => JSON.stringify(c)).join('\n') + '\n');
console.log(`${out.length} questions → ${file.pathname}`);

// How far lazy strategies get on the decisions (a hard set keeps these low).
const decided = out.filter((c: any) => c.decision?.gains);
let biggest = 0, smallest = 0, noQcd = 0, bigNoQcd = 0;
for (const c of decided as any[]) {
  const opts = Object.entries(c.scenarios as Record<string, Scenario>).map(([letter, sc]) => ({ letter, actions: sc.plans[0].actions }));
  const big = lazyBiggestRight(opts, c.decision.pick);
  const least = Math.min(...opts.map((o) => moved(o.actions)));
  biggest += +big;
  smallest += +opts.filter((o) => moved(o.actions) === least).every((o) => c.decision.pick.includes(o.letter));
  if (c.family !== 'qcd_giving') { noQcd++; bigNoQcd += +big; }
}
console.log(`Lazy strategies on ${decided.length} decisions: "always the biggest move" ${biggest} (${bigNoQcd}/${noQcd} leaving out QCD, where the decision is easy by design), "always the smallest move" ${smallest}`);
