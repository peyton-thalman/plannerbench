// The Gauntlet's outside checks. Every option of every question is run through two engines this project didn't
// derive from MoneyGuide's code:
//   1. the clean-room engine (checks/cleanroom, written from RULES.md alone): every field of every year, within $1;
//   2. PolicyEngine-US: every option's 2026 return (the year the tax numbers are graded on): federal tax, taxable
//      Social Security and the senior deduction, within $2.
// For how_much questions the solver's best plan is checked the same way. Any difference fails the build.
//
//   vite-node src/gauntlet/verify.ts            data/gauntlet.jsonl → checks/GAUNTLET.md
//   vite-node src/gauntlet/verify.ts private    private/gauntlet.jsonl → private/GAUNTLET.md (counts only)
import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { runPlan } from '../../../../moneyguide/src/scenario/run';
import type { Scenario, YearOut } from '../../../../moneyguide/src/scenario/types';

const PRIVATE = process.argv[2] === 'private';
const ROOT = new URL('../../', import.meta.url).pathname;
const cases = readFileSync(join(ROOT, PRIVATE ? 'private/gauntlet.jsonl' : 'data/gauntlet.jsonl'), 'utf8').trim().split('\n').map((l) => JSON.parse(l));
const dir = mkdtempSync(join(tmpdir(), 'gauntlet-'));

type Diff = { id: string; option: string; where: string; ours: unknown; theirs: unknown };
const diffs: Diff[] = [];

// Same normalization as ~/moneyguide/verify/compare.ts: list layout the contract leaves open isn't a disagreement.
const ONLY_IF_BOTH = /(^|\.)age\./;
function normalize(y: any) {
  const inc = y?.income;
  if (inc) { inc['pension+ira_taxable'] = (inc.pension ?? 0) + (inc.ira_taxable ?? 0); delete inc.pension; delete inc.ira_taxable; }
  return y;
}
function walk(id: string, option: string, path: string, a: any, b: any) {
  if ((a === undefined || b === undefined) && ONLY_IF_BOTH.test(path)) return;
  if (typeof a === 'number' || typeof b === 'number') {
    const x = typeof a === 'number' ? a : 0, y = typeof b === 'number' ? b : 0;
    if (Math.abs(x - y) > 1) diffs.push({ id, option, where: path, ours: a, theirs: b });
    return;
  }
  if (a && b && typeof a === 'object' && typeof b === 'object' && !Array.isArray(a)) {
    for (const k of new Set([...Object.keys(a), ...Object.keys(b)])) walk(id, option, path ? `${path}.${k}` : k, a[k], b[k]);
    return;
  }
  if (Array.isArray(a) && Array.isArray(b)) {
    if (path.endsWith('flags')) return;
    if (JSON.stringify([...a].sort()) !== JSON.stringify([...b].sort())) diffs.push({ id, option, where: path, ours: a, theirs: b });
    return;
  }
  if (a !== b && !(a === undefined && b === 0) && !(b === undefined && a === 0)) diffs.push({ id, option, where: path, ours: a, theirs: b });
}

/** One year of the engine's ledger as a PolicyEngine tax return (checks/pe_years.py). */
function peRow(rowId: string, sc: Scenario, y: YearOut) {
  const i = y.income;
  const people = sc.household.people.filter((p) => y.alive[p.id]);
  const inflate = (x = 0) => x * (1 + sc.assumptions.inflation) ** (y.year - sc.assumptions.first_year);
  return {
    id: rowId, year: y.year, filing: y.filing, ages: people.map((p) => y.age[p.id]), state: sc.household.state,
    wages: i.wages, ira: i.ira_taxable + i.annuity_taxable, pension: i.pension, taxable_interest: i.interest_taxable,
    tax_exempt_interest: i.interest_tax_exempt, qualified_dividends: i.qualified_dividends,
    ordinary_dividends: i.ordinary_dividends - i.qualified_dividends, ltcg: i.capital_gain,
    ss: people.map((p) => y.social_security[p.id] ?? 0),
    real_estate_tax: inflate(sc.household.itemized?.salt_other), mortgage_interest: inflate(sc.household.itemized?.mortgage_interest),
    medical: inflate(sc.household.itemized?.medical), charity_cash: inflate(sc.household.itemized?.charity_cash),
  };
}

const runs: { id: string; option: string; sc: Scenario }[] = [];
for (const c of cases) {
  if (!c.scenarios) continue;
  for (const [letter, sc] of Object.entries(c.scenarios as Record<string, Scenario>)) runs.push({ id: c.id, option: letter, sc });
  if (c.how_much) {
    const b = c.decision.best_flat;
    const sc: Scenario = structuredClone(c.scenarios.A);
    sc.plans = [{ name: 'best', actions: b.amount ? [{ type: 'roth_conversion', from: c.how_much.from, amount: b.amount, years: Array.from({ length: b.years }, (_, k) => 2026 + k) }] : [] }];
    runs.push({ id: c.id, option: 'best', sc });
  }
}

const peRows: ReturnType<typeof peRow>[] = [];
const ours: Record<string, YearOut> = {};
let n = 0;
for (const r of runs) {
  const out = runPlan(r.sc, r.sc.plans[0].name).out;
  const file = join(dir, `s${n++}.json`);
  writeFileSync(file, JSON.stringify(r.sc));
  let theirs: any;
  try {
    theirs = JSON.parse(execFileSync('python3', ['-I', join(ROOT, 'checks/cleanroom/engine.py'), file], { encoding: 'utf8', maxBuffer: 1 << 26 }));
  } catch (e) {
    diffs.push({ id: r.id, option: r.option, where: 'clean-room engine error', ours: '', theirs: String(e).slice(0, 300) });
    continue;
  }
  const t = theirs.plans[r.sc.plans[0].name];
  const ty = new Map((t.years as any[]).map((y) => [y.year, y]));
  if (out.years.length !== t.years.length) diffs.push({ id: r.id, option: r.option, where: 'number of years', ours: out.years.length, theirs: t.years.length });
  for (const y of out.years) if (ty.has(y.year)) walk(r.id, r.option, `${y.year}`, normalize(structuredClone(y)), normalize(ty.get(y.year)));
  walk(r.id, r.option, 'totals', out.totals, t.totals);
  const rowId = `${r.id}|${r.option}`;
  ours[rowId] = out.years[0];
  peRows.push(peRow(rowId, r.sc, out.years[0]));
}

writeFileSync(join(dir, 'pe-in.jsonl'), peRows.map((x) => JSON.stringify(x)).join('\n') + '\n');
execFileSync(join(ROOT, '.venv-pe/bin/python'), ['-I', join(ROOT, 'checks/pe_years.py'), join(dir, 'pe-in.jsonl'), join(dir, 'pe-out.jsonl')], { stdio: 'inherit' });
let peAgree = 0;
for (const line of readFileSync(join(dir, 'pe-out.jsonl'), 'utf8').trim().split('\n')) {
  const pe = JSON.parse(line);
  const y = ours[pe.id];
  const [id, option] = pe.id.split('|');
  let ok = true;
  for (const [mine, theirs] of [['federal_tax', 'federal_tax'], ['taxable_ss', 'taxable_ss'], ['senior_deduction', 'senior_deduction']] as const) {
    if (Math.abs((y as any)[mine] - pe[theirs]) > 2) { ok = false; diffs.push({ id, option, where: `PolicyEngine 2026 ${mine}`, ours: (y as any)[mine], theirs: pe[theirs] }); }
  }
  if (ok) peAgree++;
}

const bad = new Set(diffs.map((d) => `${d.id}|${d.option}`));
const lines = [
  `# Gauntlet answer-key check (${PRIVATE ? 'held-out set' : 'public dev set'})`,
  '',
  `${cases.length} questions (${cases.filter((c) => c.family === 'trap').length} traps, which have no numbers to check). ${runs.length} option runs.`,
  '',
  '| Check | Result |',
  '|---|---|',
  `| Clean-room engine, every field of every year within $1 | ${runs.length - new Set(diffs.filter((d) => !d.where.startsWith('PolicyEngine')).map((d) => `${d.id}|${d.option}`)).size}/${runs.length} option runs agree |`,
  `| PolicyEngine-US, 2026 federal tax, taxable Social Security and senior deduction within $2 | ${peAgree}/${peRows.length} returns agree |`,
  '',
  diffs.length ? '## Differences\n' : '**All checks pass.**',
  ...(PRIVATE ? (diffs.length ? [`${diffs.length} differences in ${bad.size} option runs (details withheld for the held-out set; rerun locally).`] : [])
    : diffs.slice(0, 200).map((d) => `- ${d.id} ${d.option} ${d.where}: ours ${JSON.stringify(d.ours)} vs theirs ${JSON.stringify(d.theirs)}`)),
];
writeFileSync(join(ROOT, PRIVATE ? 'private/GAUNTLET.md' : 'checks/GAUNTLET.md'), lines.join('\n') + '\n');
console.log(lines.slice(0, 9).join('\n'));
process.exit(diffs.length ? 1 : 0);
