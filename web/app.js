// Fills the page from data/*.json, which src/build_site.py writes from the graded runs.
(async () => {
  const get = (name) => fetch(`data/${name}.json`, { cache: 'no-cache' }).then((r) => (r.ok ? r.json() : null)).catch(() => null);
  const [models, mistakes, ruleEffect, examples, featured, meta, byMistake, tools, toolsPrivate, gauntlet, harness, system] = await Promise.all(
    ['models', 'mistakes', 'rule_effect', 'examples', 'featured', 'meta', 'dollars_by_mistake', 'tools', 'tools_private', 'gauntlet', 'harness', 'system'].map(get));
  // Every page shares this script; each block below runs only if its page has the element it fills.
  const $ = (id) => document.getElementById(id);

  const pct = (x) => (x == null ? '—' : `${Math.round(x * 100)}%`);
  const usd = (x, cents = false) => '$' + Number(x).toLocaleString('en-US', { minimumFractionDigits: cents ? 2 : 0, maximumFractionDigits: cents ? 2 : 0 });
  // Names come from models.json; when one model was run two ways (direct and via OpenRouter), say which.
  const byId = Object.fromEntries((models ?? []).map((m) => [m.model, m]));
  const dupes = new Set((models ?? []).map((m) => m.name).filter((n, i, all) => all.indexOf(n) !== i));
  const name = (id) => { const m = byId[id]; if (!m) return id; return dupes.has(m.name) && id.startsWith('or:') ? `${m.name} (second way)` : m.name; }; // writer A, round 3: route named only in alone.html's technical toggle
  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
  const NS = 'http://www.w3.org/2000/svg';
  const svgEl = (tag, attrs) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); return e; };
  const LEAD = 'claude-sonnet-5-5';
  const lead = models?.find((m) => m.model === LEAD) ?? models?.[0];

  // Headline figures, wherever a page shows one (data-k="...")
  const stages = tools?.hard.stages, gRows = gauntlet?.rows ?? [];
  const openRow = (engine) => gRows.find((r) => r.open && r.engine === engine);
  const gSum = (engine) => { const rs = gRows.filter((r) => r.engine === engine); return `${rs.reduce((t, r) => t + r.great, 0)}/${rs.reduce((t, r) => t + r.questions, 0)}`; };
  // Models that gave the featured question's same wrong answer, counted once each, and the labs behind them
  const misread = featured ? Object.entries(featured.replies).filter(([, r]) => r.mistake === 'combined senior phase-out').map(([id]) => id) : [];
  const lab = (id) => (id.startsWith('or:') ? id.slice(3).split('/')[0] : 'anthropic');
  const misreadNames = new Set(misread.map((id) => byId[id]?.name ?? id)), misreadLabs = new Set(misread.map(lab));
  const h = harness?.[0], sys = system ?? {};
  const fig = {
    single: lead && pct(lead.single_step_accuracy), stacked: lead && pct(lead.stacked_accuracy),
    questions: meta && meta.questions.toLocaleString('en-US'),
    tools_from: stages && pct(stages[0].accuracy), tools_to: stages && pct(stages.at(-1).accuracy),
    private_tools: toolsPrivate && `${pct(toolsPrivate.stages[0].accuracy)} → ${pct(toolsPrivate.stages.at(-1).accuracy)}`,
    g_from: gRows.length ? gSum(false) : null, g_to: gRows.length ? gSum(true) : null,
    g_worst: gauntlet && usd(Math.max(...gauntlet.failures.map((f) => f.lost))),
    g_models: gRows.length ? String(new Set(gRows.map((r) => r.model)).size) : null,
    open_from: openRow(false) && `${openRow(false).great}/${openRow(false).questions}`, open_to: openRow(true) && `${openRow(true).great}/${openRow(true).questions}`,
    open_name: openRow(true)?.name,
    agree_models: misread.length ? String(misreadNames.size) : null,
    agree_cap: misread.length ? `models from ${misreadLabs.size} labs gave the same wrong answer to the same question` : null,
    chat_judge: sys.connector && `${sys.connector.judge_pass} / ${sys.connector.judge_of}`,
    cleanroom: sys.cleanroom && `${sys.cleanroom.agree.toLocaleString('en-US')} / ${sys.cleanroom.of.toLocaleString('en-US')}`,
    harness: h && `${name(h.direct)} was asked the same ${h.questions} questions directly and through OpenRouter. It scored ${pct(h.direct_accuracy)} both ways: no difference detected in this check.`,
  };
  document.querySelectorAll('[data-k]').forEach((n) => { if (fig[n.dataset.k]) n.textContent = fig[n.dataset.k]; });

  // Any number from any data file, with no page-specific code:
  //   <span data-v="v2:models.0.hard_alone" data-f="pct">—</span>
  // data-v = "<file in data/ without .json>:<dot path>" (array items by index, or by [key=value], e.g. models.[model=x].acc).
  // data-f = pct (0.73 → 73%), pct1, usd, int (1,234), frac (needs data-of: "<file>:<path>" → "22/30"), or raw (default).
  const files = {}; const load = async (f) => (files[f] ??= get(f));
  // [key=value] may contain dots (model names like "GPT-6.1 Sol"), so split on dots outside brackets only.
  const dig = (o, path) => path.match(/\[[^\]]*\]|[^.]+/g).reduce((x, k) => {
    if (x == null) return x;
    const m = k.match(/^\[(.+?)=(.+)\]$/);
    return m ? (Array.isArray(x) ? x.find((it) => String(it?.[m[1]]) === m[2]) : undefined) : x[k];
  }, o);
  const pick = async (ref) => { const i = ref.indexOf(':'); return dig(await load(ref.slice(0, i)), ref.slice(i + 1)); };
  const fmt = { pct: (x) => `${Math.round(x * 100)}%`, pct1: (x) => `${(x * 100).toFixed(1)}%`, usd: (x) => usd(x), int: (x) => Number(x).toLocaleString('en-US'), raw: (x) => String(x) };
  await Promise.all([...document.querySelectorAll('[data-v]')].map(async (n) => {
    const v = await pick(n.dataset.v);
    if (v == null) { console.warn('data-v not found:', n.dataset.v); return; }
    n.textContent = n.dataset.f === 'frac' ? `${v}/${await pick(n.dataset.of)}` : (fmt[n.dataset.f] ?? fmt.raw)(v);
  }));

  // Home: the system map. Each node's panel says what it is, why it exists and the number that proves it.
  if ($('map-panel')) {
    const sonnetG = gRows.find((r) => r.engine && r.model.includes('sonnet')), sonnetAlone = gRows.find((r) => !r.engine && r.model.includes('sonnet'));
    const NODES = {
      sources: ['Ground truth', 'Published rules',
        'IRS forms and publications, SSA’s operating manual (POMS) and Medicare’s premium tables, for tax years 2025 and 2026. Every rule in the engine cites where it comes from.',
        'When models disagree with the key, the published source decides, never a vote among models. That one rule settled every dispute so far.',
        fig.agree_models, fig.agree_cap ? `${fig.agree_cap}; Schedule 1-A Part V showed the key was right` : '', 'alone.html#worked'],
      engine: ['The asset', 'The planning engine',
        'Code for 2026 federal tax, taxable Social Security, required distributions and inherited IRAs, Medicare premiums, and 25-year retirement scenarios with a Roth-conversion solver. Every answer comes with a trace of the rules it used.',
        'Models do arithmetic fine but don’t reliably know this year’s rules. So the rules live in tested code, and the model’s job becomes choosing inputs and explaining the result.',
        fig.cleanroom, 'random households where a second, independently written engine agrees on every field, to the dollar', 'method.html'],
      proof: ['Proof', 'Independent checks',
        'A second engine written from the spec alone by an AI agent that was never allowed to read the first; PolicyEngine-US, an open-source tax model built by others; and rules that must hold for any household.',
        'A benchmark graded against a buggy key grades your own bug. Independent builds catch what self-review can’t: the second engine found a real bug in a 2027 tax threshold on its first run.',
        sys.policyengine && `${sys.policyengine.agree.toLocaleString('en-US')} / ${sys.policyengine.of.toLocaleString('en-US')}`, `tax answers that agree with PolicyEngine-US within ${sys.policyengine?.within ?? '$2'}`, 'method.html'],
      bench: ['Measure', 'PlannerBench',
        `${fig.questions ?? '2,800'} public questions across ${meta?.tasks ?? 14} tasks, plus a private held-out set, from one rule to many. A script grades every reply. ${models?.length ?? 7} model setups from ${new Set((models ?? []).map((m) => lab(m.model))).size || 5} labs so far.`,
        'Find out exactly where models fail before building anything. It turned up one misreading of a 2025 rule behind most of the misses.',
        fig.single && `${fig.single} → ${fig.stacked}`, 'Claude Sonnet 5.5 on one rule, then on several rules in one household', 'alone.html'],
      tools: ['Fix', 'MCP tools',
        `The engine as tools any model can call over the Model Context Protocol: ${(tools?.tools ?? []).map((t) => t.replace(/_/g, ' ')).join(', ')}, plus a scenario runner and a Roth-conversion solver.`,
        `Version 1.0 returned the right number, and the model replaced it with its own wrong rule on ${tools?.whole.overruled ?? 18} of its ${tools?.whole.misses ?? 22} misses. Version 1.1 shows the rule and cites the IRS form line. The lesson is about product design, not model size.`,
        fig.tools_from && `${fig.tools_from} → ${fig.tools_to}`, `Claude Haiku 5.5 on the 50 hardest questions${fig.private_tools ? `; ${fig.private_tools} on held-out ones` : ''}`, 'calculator.html#tools'],
      chat: ['Talk to it', 'In the chat',
        'A connector anyone can add to Claude or ChatGPT. A person asks in everyday words; the engine picks the one question that matters next, runs every plan, and replies with the answer, every assumption and the law behind each dollar. A card shows it inside the chat.',
        'A planning engine only helps if people can reach it where they already ask questions. Putting the engine in charge of the questions keeps the chat model from guessing facts or doing math.',
        fig.chat_judge, 'simulated clients get the same decision as with every fact known, within 6 questions, with no wasted questions', 'chat.html'],
      wizard: ['Use', 'Wizard',
        'A live meeting-copilot demo: as an advisor and client talk, the intake form fills itself in, and a planning question asked out loud becomes an engine card a few seconds later.',
        'Shows where the engine lives in a real workflow. Built to a generic intake form with fake households only; sensitive numbers are masked in the browser before any model sees them.',
        'Frozen', 'features frozen on purpose: it’s the demo, the engine is the product', 'built.html#wizard'],
      gauntlet: ['Prove it matters', 'The Gauntlet',
        `${gauntlet?.families ?? 10} families of real decisions (Roth conversions, claiming age, giving, inherited IRAs) for whole households, each stacking three or more rules over 25 years. Code proves no shortcut lands within 2% of the answer.`,
        'Single questions can be passed with a good guess. Decisions with dollars attached show what a mistake costs a family, and whether a model with the engine still overrules it.',
        fig.g_from && `${fig.g_from} → ${fig.g_to}`, `decisions fully right, alone vs. with the engine, across ${fig.g_models ?? 'all'} models (one open)${sonnetG && sonnetAlone ? `; Sonnet thought ${Math.round(sonnetAlone.output_tokens / sonnetG.output_tokens)}× less with it` : ''}`, 'calculator.html'],
    };
    const show = (key) => {
      const [kind, title, what, why, proof, cap, href] = NODES[key];
      $('mp-kind').textContent = kind; $('mp-title').textContent = title; $('mp-what').textContent = what; $('mp-why').textContent = why;
      $('mp-proof').textContent = proof ?? '—'; $('mp-proof-cap').textContent = cap; $('mp-link').href = href;
      document.querySelectorAll('.node').forEach((n) => n.setAttribute('aria-pressed', String(n.dataset.node === key)));
    };
    // On a phone the panel sits below the whole map, so bring it into view after a tap.
    document.querySelectorAll('.node').forEach((n) => n.addEventListener('click', () => {
      show(n.dataset.node);
      if (innerWidth < 640) $('map-panel').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }));
    show('engine');
  }

  // In the chat: real plan_check replies for the sample couple (data/connector.json, made by the engine repo's
  // verify/connector-sample.ts) and the connector's checks from system.json
  if (document.body.dataset.page === 'chat') {
    const cx = await get('connector'), cs = sys.connector;
    const a = cx?.answer, words = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten'];
    const C = {
      commit: cx?.engine_commit, ask: cx?.first.ask.question, ask_why: cx && `Why it matters: ${cx.first.ask.why}`,
      headline: a?.headline, subline: a?.subline, rejected: cx?.rejected.message,
      judge: cs && `${cs.judge_pass} / ${cs.judge_of}`, tests: cs && String(cs.engine_tests),
      drives: cs && `${cs.drive_notes.join(' + ')} notes`,
      advanced_n: cs && words[cs.advanced.length], advanced: cs && cs.advanced.map((t) => t.replace(/_/g, ' ')).join(', '),
    };
    document.querySelectorAll('[data-c]').forEach((n) => { if (C[n.dataset.c]) n.textContent = C[n.dataset.c]; });
    if (cx) {
      for (const r of cx.first.have_ready) $('c-ready').append(el('li', null, r));
      for (const k of a.key_numbers) { const d = el('div'); d.append(el('dt', null, k.label), el('dd', null, k.value)); $('c-keys').append(d); }
      const reasons = (side, id) => { for (const r of side.reasons) { const li = el('li'); li.append(el('span', null, r.text), el('b', null, usd(Math.abs(r.amount))), el('small', null, r.law)); $(id).append(li); } };
      reasons(a.costs_now, 'c-costs'); reasons(a.saves_later, 'c-saves');
      for (const s of a.assumed) $('c-assumed').append(el('li', null, s));
      $('c-sens').textContent = a.sensitivity.map((s) => `With ${s.if}, ${s.effect}.`).join(' ') || 'Nothing that was assumed would change the pick.';
      $('c-meta').textContent = `${a.said} facts said, ${a.assumed_n} assumed, ${a.worked_out} worked out · ${a.engine_runs.toLocaleString('en-US')} plans run for this one answer, ${a.seconds_local.toFixed(1)} s on a laptop`;
    }
  }

  // --- method (writer A) --- the proof stack, one card per independent check, each saying exactly what it covers.
  // round 2: the cards stay plain; file names, the two-routes check and reproduce.sh go in the technical toggle (#proof-tech).
  if ($('proofs') && sys.cleanroom) {
    const ratio = (o) => `${o.agree.toLocaleString('en-US')} / ${o.of.toLocaleString('en-US')}`;
    const cards = [
      [ratio(sys.cleanroom), 'Another engine, written without seeing the first', `A separate AI agent wrote another engine, in a different programming language, from the written rules alone, and was never allowed to read the first. Both run on random households; every number for every year must agree within ${sys.cleanroom.within}. Its first run found a real bug in the main engine. Every question in the newer, harder set also has to match it before it can be used.`, sys.cleanroom.source],
      [ratio(sys.policyengine), 'Outside tax code', `PolicyEngine-US, open-source tax software written by other people, recomputes every tax answer in the first test, all within ${sys.policyengine.within}, the new senior deduction included; and ${ratio({ agree: sys.policyengine.private_agree, of: sys.policyengine.private_of })} on the held-back questions (private ones never published). It doesn't model required withdrawals, Social Security claiming or Medicare premiums, so those rest on the published tables and the second engine.`, sys.policyengine.source],
      [ratio(sys.gauntlet_keys), 'Whole-household decisions, recomputed', 'Every option in every public whole-household question is rerun by the second engine, and its 2026 federal tax return by PolicyEngine, before the question can be used.', sys.gauntlet_keys.source],
      [ratio(sys.tools_check), 'The calculator can answer everything', `Before any model used the calculator, a script checked that calling it correctly reproduces every number answer in the first test${sys.tools_check.public_numeric ? `: the ${sys.tools_check.public_numeric.toLocaleString('en-US')} public questions that have a number, plus ${sys.tools_check.private_numeric.toLocaleString('en-US')} held-back ones. The other ${meta ? (meta.questions - sys.tools_check.public_numeric).toLocaleString('en-US') : ''} of the ${meta ? meta.questions.toLocaleString('en-US') : ''} public questions are compliance questions, answered with sentences or flags rather than a number, so there is nothing for a calculator to compute` : ''}.`, sys.tools_check.source],
    ];
    for (const [num, title, body] of cards) {
      const c = el('div', 'proof-card');
      c.append(el('b', null, num), el('span', 't', title), el('p', null, body));
      $('proofs').append(c);
    }
    if ($('proof-tech')) {
      const item = (b, t) => { const li = el('li'); li.append(el('b', null, b), document.createTextNode(' ' + t)); $('proof-tech').append(li); };
      if (h) item('Same model, two routes.', `${name(h.direct)} answered the same ${h.questions} questions directly and through OpenRouter (a service that relays requests to many models): ${pct(h.direct_accuracy)} and ${pct(h.openrouter_accuracy)}. No difference detected in this check, which is not proof the route never matters. (checks/HARNESS.md)`);
      item('One script rebuilds the first test.', `reproduce.sh (a script anyone can run from the code) re-checks the first test’s answer key, regrades every saved first-test reply, rebuilds its scores and the calculator runs on its ${tools?.hard.questions ?? 50} hardest questions, and compares them with the published copy; any difference fails it. It doesn’t regenerate the questions or cover the newer set.`);
      item('Where each check’s record lives.', cards.map(([, title, , src]) => `${title}: ${src}`).join(' · ') + '. (“engine repo” is the planning engine’s own code repository; verify/COMPARE.md there is the two engines’ comparison report.)');
    }
  }

  // Worked question
  if (featured && $('featured-prompt')) {
    document.getElementById('featured-prompt').textContent = featured.prompt;
    const dl = document.getElementById('featured-answers');
    const row = (label, value, ok) => {
      const d = el('div'); d.append(el('dt', null, label));
      const dd = el('dd', null, value);
      if (ok != null) dd.append(el('span', `mark ${ok ? 'ok' : 'bad'}`, ok ? 'Right' : 'Wrong'));
      d.append(dd); dl.append(d);
    };
    row('Answer key', usd(featured.answer));
    // A request that failed (rate limit, no reply) has no number to show and isn't graded right or wrong.
    for (const [m, r] of Object.entries(featured.replies)) r.got == null ? row(name(m), 'No answer') : row(name(m), usd(r.got), r.bucket === 'correct');
    for (const [m, r] of Object.entries(featured.with_rule || {})) row(`${name(m)}, given the rule`, usd(r.got), r.bucket === 'correct');

    const s = featured.steps;
    const lines = [
      ['31', 'Modified adjusted gross income', usd(s.agi, true)],
      ['32', 'Threshold, married filing jointly', usd(s.threshold, true)],
      ['33', 'Line 31 minus line 32', usd(s.agi - s.threshold, true)],
      ['34', 'Line 33 × 6%', usd(s.cut, true)],
      ['35', '$6,000 minus line 34', usd(6000 - s.cut, true)],
      // writer A: these are the 2025 form's lines and birth date (audit #9); alone.html labels the form as 2025
      ['36a', 'You, born before January 2, 1961: line 35', usd(6000 - s.cut, true)],
      ['36b', 'Your spouse, born before January 2, 1961: line 35', usd(6000 - s.cut, true)],
      ['37', 'Enhanced deduction for seniors', usd(s.per_spouse, true), true],
    ];
    const ol = document.getElementById('featured-lines');
    for (const [no, what, amt, total] of lines) {
      const li = el('li', total ? 'total' : null);
      li.append(el('span', 'no', no), el('span', 'what', what), el('span', 'amt', amt));
      ol.append(li);
    }
    const mis = document.getElementById('featured-misread');
    mis.textContent = '';
    mis.append(`They took the 6% once off the couple’s combined $12,000: $12,000 − ${usd(s.cut, true)} = `,
      el('span', 'amt', usd(s.combined, true)),
      `. That’s ${usd(s.combined - s.per_spouse, true)} too much deduction, so the tax came out at ${usd(s.tax_combined)} instead of ${usd(s.tax_key)}. The form takes the 6% off each spouse’s $6,000 (lines 35, 36a and 36b).`);
  }

  // Score table
  if (models && $('scores')) {
    const tbody = document.querySelector('#scores tbody');
    const cols = ['single_step', 'multi_step', 'stacked', 'compliance'];
    const range = (lo, hi) => (lo == null ? '' : `${Math.round(lo * 100)}–${Math.round(hi * 100)}`);
    for (const m of [...models].sort((a, b) => b.accuracy - a.accuracy)) {
      const tr = el('tr');
      const who = el('td', 'model', name(m.model));
      if (m.access) who.append(el('span', 'via', m.access + (m.open_weights ? ' · open weights' : '')));
      tr.append(who);
      for (const c of cols) {
        const v = m[`${c}_accuracy`], lo = m[`${c}_lo`], hi = m[`${c}_hi`];
        const td = el('td'); const cell = el('div', `cell${v != null && v < 0.5 ? ' low' : ''}`);
        // The track shows the 95% interval as a band, with the measured score as the solid bar.
        const track = el('div', 'track'); const band = el('div', 'band-ci'); const fill = el('div', 'fill');
        band.style.left = `${(lo ?? 0) * 100}%`; band.style.width = `${((hi ?? 0) - (lo ?? 0)) * 100}%`; fill.style.width = `${(v ?? 0) * 100}%`;
        track.append(band, fill);
        const val = el('span', 'v', pct(v)); val.append(el('span', 'ci', range(lo, hi)));
        cell.append(val, track); td.append(cell); tr.append(td);
      }
      const overall = el('td', 'overall', pct(m.accuracy)); overall.append(el('span', 'ci', range(m.lo, m.hi)));
      tr.append(overall, el('td', 'cost', m.truncated_rate ? pct(m.truncated_rate) : '—'),
        el('td', 'cost', m.cost_per_correct == null ? '—' : usd(m.cost_per_correct * 1000, true)));
      tbody.append(tr);
    }
  }

  // Dollars off: what each model's mistakes would cost a client who acted on them
  if (models && $('dollars')) {
    const tbody = document.querySelector('#dollars tbody');
    const scored = models.filter((m) => m.dollars).sort((a, b) => a.dollars.dollars_off_per_question - b.dollars.dollars_off_per_question);
    for (const m of scored) {
      const d = m.dollars, tr = el('tr');
      const who = el('td', 'model', name(m.model));
      if (m.access) who.append(el('span', 'via', m.access + (m.open_weights ? ' · open weights' : '')));
      const off = el('td', 'overall', usd(d.dollars_off_per_question)); off.append(el('span', 'ci', `${usd(d.dollars_lo)}–${usd(d.dollars_hi)}`));
      const mat = el('td', 'overall', pct(d.material_rate)); mat.append(el('span', 'ci', `${Math.round(d.material_lo * 100)}–${Math.round(d.material_hi * 100)}`));
      tr.append(who, off, mat, el('td', 'cost', d.median_miss == null ? '—' : usd(d.median_miss)),
        el('td', 'cost', d.worst_miss == null ? '—' : usd(d.worst_miss)), el('td', 'cost', String(d.questions)));
      tbody.append(tr);
    }
    const big = byMistake?.filter((r) => r.mistake !== 'unexplained').sort((a, b) => b.median_off - a.median_off);
    if (big?.length) {
      const top = big[0], tiny = big[big.length - 1];
      document.getElementById('dollars-note').textContent = `Not every mistake is equal. The ${top.mistake} mistake is rare (${top.count} times) but large: a typical miss of ${usd(top.median_off)} a year. `
        + `“${tiny.mistake}” happened ${tiny.count} times and is worth about ${usd(tiny.median_off, true)}. Typical miss is the median size of a wrong answer; ranges are 95% intervals.`;
    }
  }

  // With planning tools: the same hard questions without tools, with the right number, and with the rule shown
  const range = (lo, hi) => `${Math.round(lo * 100)}–${Math.round(hi * 100)}`;
  const scoreCell = (s) => {
    const td = el('td');
    if (!s) { td.append(el('span', 'ci', 'not asked')); return td; }
    const cell = el('div', `cell${s.accuracy < 0.5 ? ' low' : ''}`);
    const track = el('div', 'track'), band = el('div', 'band-ci'), fill = el('div', 'fill');
    band.style.left = `${s.lo * 100}%`; band.style.width = `${(s.hi - s.lo) * 100}%`; fill.style.width = `${s.accuracy * 100}%`;
    track.append(band, fill);
    const v = el('span', 'v', `${pct(s.accuracy)} · ${s.right}/${s.questions}`); v.append(el('span', 'ci', range(s.lo, s.hi)));
    cell.append(v, track); td.append(cell); return td;
  };

  // The Gauntlet: the same questions alone and with the engine's MCP tools (src/gauntlet_site.py)
  if (gauntlet && $('gauntlet-table')) {
    const tbody = document.querySelector('#gauntlet-table tbody');
    for (const r of gauntlet.rows) {
      const tr = el('tr', r.engine ? 'best' : null);
      tr.append(el('td', 'model', `${r.name}${r.engine ? ' + calculator' : ', on its own'}`),
        scoreCell({ accuracy: r.great / r.questions, right: r.great, questions: r.questions, lo: r.lo, hi: r.hi }),
        el('td', 'overall', `${r.out_of_room}`), el('td', 'overall', `${Math.round(r.output_tokens / 1000)}k tokens`),
        el('td', 'overall', usd(r.cost_per_question, true)));
      tbody.append(tr);
    }
    document.getElementById('gauntlet-note').textContent = `${gauntlet.questions} questions, one from each family plus a trap whose honest answer is “I can’t answer that.” `
      + 'Ran out of room: used its whole reply budget thinking and never answered (scored as not right). Sonnet alone shows 10 because one reply was cancelled to stay inside the run’s spending cap. Bars show 95% intervals.';
    const sb = gauntlet.side_by_side;
    document.getElementById('gauntlet-intro').textContent = sb.intro;
    const dl = document.getElementById('gauntlet-side');
    const row = (label, value, ok) => {
      const d = el('div'); d.append(el('dt', null, label));
      const dd = el('dd', null, value);
      if (ok != null) dd.append(el('span', `mark ${ok ? 'ok' : 'bad'}`, ok ? 'Right' : 'Wrong'));
      d.append(dd); dl.append(d);
    };
    const plan = (p) => {
      const m = p.match(/([\d,]+)\s*x\s*(\d+)/);
      if (!m) return p;
      return Number(m[1].replace(/,/g, '')) === 0 || m[2] === '0' ? 'Convert nothing' : `${usd(Number(m[1].replace(/,/g, '')))} a year × ${m[2]} years`;
    };
    row('The calculator’s best plan', sb.best);
    row(`${sb.model}, on its own`, `${plan(sb.alone)} (gives up ${usd(sb.alone_lost)})`, false);
    row(`${sb.model} + calculator`, plan(sb.engine), true);
    const ol = document.getElementById('gauntlet-failures');
    gauntlet.failures.forEach((f, i) => {
      const li = el('li');
      li.append(el('span', 'no', `${i + 1}`), el('span', 'what', `${f.what} (${f.model}, on its own)${f.shortcut ? `: it ${f.shortcut}` : ''}.${f.engine_great ? ' With the calculator: right.' : ''}`),
        el('span', 'amt', `−${usd(f.lost)}`));
      ol.append(li);
    });
    const ov = gauntlet.rows.filter((r) => r.engine).reduce((t, r) => t + r.overrides, 0);
    const withEngine = gauntlet.rows.filter((r) => r.engine);
    const allRight = withEngine.every((r) => r.great === r.questions);
    document.getElementById('gauntlet-overrides').textContent = `With the calculator, ${allRight ? `all ${withEngine.length} models made the right decision on every question, with every number within 2% of the key` : 'the models mostly made the right decision, with every number within 2% of the key'}${ov ? `, but went against it ${ov} times` : ', and never went against it'}. `
      + `They also thought far less: about ${Math.round(gauntlet.rows.find((r) => r.engine && r.model.includes('sonnet'))?.output_tokens / 1000)}k tokens for Sonnet instead of ${Math.round(gauntlet.rows.find((r) => !r.engine && r.model.includes('sonnet'))?.output_tokens / 1000)}k.`;
  }

  // Ask first: one decisive fact left out, a scripted client to ask (src/gauntlet_ask.py)
  const ask = gauntlet?.ask_first;
  if (ask && $('ask-table')) {
    const tbody = document.querySelector('#ask-table tbody');
    for (const r of ask.rows) {
      const tr = el('tr', r.engine ? 'best' : null);
      tr.append(el('td', 'model', `${r.name}${r.engine ? ' + calculator' : ', on its own'}`),
        scoreCell({ accuracy: r.great / r.questions, right: r.great, questions: r.questions, lo: r.lo, hi: r.hi }),
        el('td', 'overall', `${r.got_fact} of ${r.questions}`), el('td', 'overall', usd(r.cost_per_question, true)));
      tbody.append(tr);
    }
    const alone = ask.rows.find((r) => !r.engine);
    $('ask-note').textContent = `One question per family (the trap has nothing to leave out).${alone && alone.questions < 10 ? ` The alone run was stopped after ${alone.questions} questions: answering without the calculator took 10–15 minutes each.` : ''} `
      + 'Fully right is graded against the full facts, by the same grader as above. Bars show 95% intervals.';
    const quotes = $('ask-quotes');
    const clip = (t) => (t.length > 220 ? t.slice(0, t.lastIndexOf(' ', 210)) + ' …' : t);
    (ask.rows.find((r) => r.engine) ?? ask.rows[0]).quotes.forEach((q, i) => {
      const li = el('li'); li.append(el('span', 'no', `${i + 1}`), el('span', 'what', `“${clip(q.q.replace(/\*\*/g, ''))}”`), el('span', 'amt', ''));
      quotes.append(li);
    });
    const proof = $('ask-proof'), st = ask.stand_ins ?? {};
    const item = (b, t) => { const li = el('li'); li.append(el('b', null, b), document.createTextNode(' ' + t)); proof.append(li); };
    item('Every tested guess fails.', `Before a question is used, the engine answers it ${ask.guesses}–5 times with the missing fact guessed (none, half, 75%, 125%, 150%). All ${ask.all_guesses_wrong} of ${ask.built} questions grade wrong under every guess.`);
    item('The client never volunteers.', 'It’s code, not a model: it answers only a question on the missing fact’s topic, and says nothing new to anything else.');
    if (st.asker) item('Checked with stand-ins.', `A stand-in that asks the right question gets ${st.asker.great} of ${st.asker.of} fully right; one that guesses gets ${st.guesser?.great ?? '—'} of ${st.guesser?.of ?? '—'}; one that asks vague questions never gets the fact (${st.spammer?.got_fact ?? '—'} of ${st.spammer?.of ?? '—'}).`);
  }

  if (tools && $('ladder')) {
    const tbody = document.querySelector('#ladder tbody');
    const priv = Object.fromEntries((toolsPrivate?.stages ?? []).map((s) => [s.key, s]));
    for (const s of tools.hard.stages) {
      const tr = el('tr', s.key === 'v2' ? 'best' : null);
      // writer B: plain names for the three ways the questions were asked
      const LADDER = { none: 'On its own', v1: 'Calculator 1.0: just the number', v2: 'Calculator 1.1: the number, the rule and its source' };
      tr.append(el('td', 'model', LADDER[s.key] ?? s.label), scoreCell(s), scoreCell(priv[s.key]));
      const off = el('td', 'overall', usd(s.dollars_off));
      if (priv[s.key]) off.append(el('span', 'ci', `held-back ${usd(priv[s.key].dollars_off)}`));
      tr.append(off); tbody.append(tr);
    }
    const p = tools.hard.pairs, fmtP = (x) => (x < 0.001 ? 'p < 0.001' : `p = ${x.toFixed(3)}`);
    document.getElementById('ladder-note').textContent = `The same ${tools.hard.questions} questions in every row (${tools.hard.tasks.length} tasks, 10 each). `
      + `The right number alone fixed ${p.none_to_v1.fixed} and broke ${p.none_to_v1.broken}; adding the rule and its source fixed ${p.v1_to_v2.fixed} more and broke ${p.v1_to_v2.broken} (${fmtP(p.v1_to_v2.p)}: same questions both ways, so very unlikely to be luck). `
      + (toolsPrivate ? `On ${toolsPrivate.questions} held-back questions, never seen while the calculator was built: ${toolsPrivate.pairs.none_to_v2.fixed} fixed, ${toolsPrivate.pairs.none_to_v2.broken} broken. ` : '')
      + 'Shaded bands are 95% intervals.';

    const q = tools.quote;
    document.getElementById('tools-quote').textContent = `“${q.text}”`;
    const dl = document.getElementById('tools-answers');
    const row = (label, value, ok) => {
      const d = el('div'); d.append(el('dt', null, label)); const dd = el('dd', null, value);
      if (ok != null) dd.append(el('span', `mark ${ok ? 'ok' : 'bad'}`, ok ? 'Right' : 'Wrong'));
      d.append(dd); dl.append(d);
    };
    row('The calculator’s answer (and the key)', usd(q.key));
    row('Haiku with calculator 1.0', usd(q.answered), q.answered === q.key);
    row('Haiku with calculator 1.1', usd(q.answered_v2), q.v2_right);

    const sd = q.v2_senior_deduction, ol = document.getElementById('tools-lines');
    for (const [what, amt, total] of [['Income (MAGI) over the $150,000 threshold', usd(sd.magi_over_threshold, true)],
      ['Reduction per person (6%)', usd(sd.reduction_per_person, true)], ['Senior deduction per person', usd(sd.per_person, true)],
      ['People 65 or older', String(sd.people)], ['Senior deduction', usd(sd.total, true), true]]) {
      const li = el('li', total ? 'total' : null); li.append(el('span', 'what', what), el('span', 'amt', amt)); ol.append(li);
    }
    document.getElementById('tools-rule').textContent = sd.rule.replace(/^OBBBA senior deduction/, 'The senior deduction from the 2025 tax law (OBBBA)');

    const w = tools.whole;
    document.getElementById('tools-whole').textContent = `Across all ${w.questions} questions, calculator 1.0 lifted Haiku from ${pct(w.without.accuracy)} to ${pct(w.with.accuracy)} `
      + `(${w.fixed} fixed, ${w.broken} broken, ${fmtP(w.p)}); single-step questions were already at ${pct(w.by_tier['single-step'].without)}. `
      + `But ${w.overruled} of the ${w.misses} misses left were Haiku getting the right number from the calculator and replacing it with its own, every time saying so.`;
    document.getElementById('tools-private').textContent = toolsPrivate
      ? `On ${toolsPrivate.questions} questions held back from a secret seed and never used while building the calculator: ${pct(toolsPrivate.stages[0].accuracy)} on its own, ${pct(toolsPrivate.stages.at(-1).accuracy)} with calculator 1.1. Both misses were Haiku overruling the calculator again, with the rule in front of it.`
      : 'Held-out results aren’t published yet.';
  }

  // --- wrong-facts (writer B) ---
  // Wrong facts and With a calculator: tables and figures from data/v2.json. Plain numbers use data-v above; the ones
  // here need a calculation (a range across models, a pooled rate, a cost ratio) and fill <span data-w="key">.
  const v2 = document.querySelector('[data-w], #wf-table, #wf-kind, #calc-v2') ? await load('v2') : null;
  if (v2) {
    const M = v2.models, find = (s) => M.find((m) => m.model.includes(s));
    const both = (lo, hi, f) => (f(lo) === f(hi) ? f(lo) : `${f(lo).replace(/%$/, '')}–${f(hi)}`);
    const spread = (xs, f) => both(Math.min(...xs), Math.max(...xs), f);
    const KIND = { transposed: 'two digits swapped', impossible_age: 'an impossible age', spending: 'spending that can’t fit',
      conflict: 'two facts that conflict', over_limit: 'an amount over a legal limit' };
    const KINDS = { transposed: 'swapped digits', impossible_age: 'impossible ages', spending: 'impossible spending',
      conflict: 'facts that conflict', over_limit: 'amounts over a legal limit' };
    const TIER_W = { frontier: 'top-priced', mid: 'mid-priced', cheap: 'cheap or free' };
    // round 3: one label per price group on every page, and the plural used in sentences
    const TIER_G = { frontier: 'top-priced', mid: 'mid-priced', cheap: 'cheap and free' };
    const runs = (r) => `${r} run${r === 1 ? '' : 's'} per item`;
    // Every outcome a reply to a planted-mistake note can land in, in the order the page explains them.
    const OUT = [['caught', 'Caught it'], ['flagged_but_answered', 'Noticed, answered anyway'], ['silent_number', 'Missed it, answered anyway'],
      ['declined_other_reason', 'Declined for another reason'], ['ran_out_of_room', 'Ran out of room']]
      .filter(([k]) => M.some((m) => m.bad?.[k]?.rate != null));
    const sumAll = (o) => Object.values(o).reduce((s, n) => s + n, 0);
    const pooled = Object.entries(v2.bad_by_type_all_models).map(([t, o]) => [t, o.caught / sumAll(o)]).sort((a, b) => b[1] - a[1]);
    const lowCatch = M.filter((m) => m.bad).sort((a, b) => a.bad.caught.rate - b.bad.caught.rate).slice(0, 3);
    const weakTools = M.filter((m) => m.hard_tools && m.hard_tools.rate < 0.15);
    const ds = find('deepseek'), sonnet = find('claude-sonnet');
    const per1k = (x) => usd(x * 1000, true);
    const W = {
      low_caught: spread(lowCatch.map((m) => m.bad.caught.rate), pct),
      low_silent: spread(lowCatch.map((m) => m.bad.silent_number.rate), pct),
      all_caught: pct(v2.bad_outcomes_all_models.caught / sumAll(v2.bad_outcomes_all_models)),
      all_silent: pct(v2.bad_outcomes_all_models.silent_number / sumAll(v2.bad_outcomes_all_models)),
      all_replies: sumAll(v2.bad_outcomes_all_models).toLocaleString('en-US'),
      pooled_top_kind: KINDS[pooled[0][0]], pooled_top: pct(pooled[0][1]),
      pooled_low_kind: KINDS[pooled.at(-1)[0]], pooled_low: pct(pooled.at(-1)[1]),
      models_n: String(M.length),
      not_pattern: v2.catch_by_type?.models_with_another_type_below_over_limit?.join(' and '),
      cost_ratio: ds?.hard_tools && sonnet && String(Math.round(sonnet.hard.cost_per_correct / ds.hard_tools.cost_per_correct)),
      ds_tools_per1k: ds?.hard_tools && per1k(ds.hard_tools.cost_per_correct), sonnet_per1k: sonnet && per1k(sonnet.hard.cost_per_correct),
      weak_n: String(weakTools.length), weak_right: weakTools.length ? `${spread(weakTools.map((m) => m.hard_tools.k), String)} of ${weakTools[0].hard_tools.n}` : null,
      weak_called: weakTools.length ? spread(weakTools.map((m) => m.hard_tools.call_rate), pct) : null,
      spent: v2.spent_usd != null ? usd(v2.spent_usd, true) : null, // writer B, round 2: built.html
      // round 3: the models in each price group, and how the pooled reply count is made (files × runs per model)
      ...Object.fromEntries(Object.keys(TIER_G).map((t) => [`tier_${t}`, M.filter((m) => m.tier === t).map((m) => m.name).join(', ')])),
      cheap_n: ['no', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight'][M.filter((m) => m.tier === 'cheap').length] ?? String(M.filter((m) => m.tier === 'cheap').length),
      reps_breakdown: (() => {
        const times = ['', 'once', 'twice', 'three times', 'four times'];
        const parts = [...new Set(M.filter((m) => m.bad).map((m) => m.bad.reps))].sort((a, b) => a - b).map((r) => {
          const ms = M.filter((m) => m.bad?.reps === r), tiers = [...new Set(ms.map((m) => TIER_G[m.tier]))].join(' or ');
          return `${times[r] ?? `${r} times`} of each of the ${ms.length} ${tiers} models`;
        });
        return parts.length > 1 ? `${parts.slice(0, -1).join(', ')} and ${parts.at(-1)}` : parts[0];
      })(),
    };
    document.querySelectorAll('[data-w]').forEach((n) => { if (W[n.dataset.w] != null) n.textContent = W[n.dataset.w]; else console.warn('data-w not found:', n.dataset.w); });

    const who = (m, extra) => { const td = el('td', 'model', m.name); td.append(el('span', 'via', `${TIER_W[m.tier]} · ${extra}`)); return td; };
    const bar = (s) => {
      const td = el('td'); if (!s) { td.append(el('span', 'ci', 'not run')); return td; }
      const cell = el('div', `cell${s.rate < 0.5 ? ' low' : ''}`), track = el('div', 'track'), band = el('div', 'band-ci'), fill = el('div', 'fill');
      band.style.left = `${s.lo * 100}%`; band.style.width = `${(s.hi - s.lo) * 100}%`; fill.style.width = `${s.rate * 100}%`;
      track.append(band, fill); const v = el('span', 'v', pct(s.rate)); v.append(el('span', 'ci', range(s.lo, s.hi)));
      cell.append(v, track); td.append(cell); return td;
    };
    const head = (id, cols) => { const tr = document.querySelector(`#${id} thead tr`); tr.textContent = ''; cols.forEach(([t, r]) => { const th = el('th', r ? 'r' : null, t); th.scope = 'col'; tr.append(th); }); };

    // Wrong facts: what each model did with the 30 planted-mistake notes, and how often it refused a fine one
    if ($('wf-table')) {
      head('wf-table', [['Model'], ...OUT.map(([, t], i) => [t, i > 0]), [`False alarms, of ${M[0].bad.false_alarm.n} fine files`, true], [`Clean twins answered right, of ${M[0].bad.clean_correct.n}`, true]]);
      const tbody = document.querySelector('#wf-table tbody');
      for (const m of M.filter((x) => x.bad).sort((a, b) => (b.bad.caught.rate - b.bad.false_alarm.rate) - (a.bad.caught.rate - a.bad.false_alarm.rate))) {
        const tr = el('tr'); tr.append(who(m, runs(m.bad.reps)));
        OUT.forEach(([k], i) => tr.append(i === 0 ? bar(m.bad[k]) : el('td', 'cost', pct(m.bad[k]?.rate ?? 0))));
        tr.append(el('td', 'cost', pct(m.bad.false_alarm.rate)), el('td', 'cost', pct(m.bad.clean_correct.rate)));
        tbody.append(tr);
      }
    }
    // Caught, by kind of mistake: each model, then every model's replies pooled
    if ($('wf-kind')) {
      const kinds = Object.keys(KIND);
      head('wf-kind', [['Model'], ...kinds.map((k) => [KIND[k][0].toUpperCase() + KIND[k].slice(1), true])]);
      const tbody = document.querySelector('#wf-kind tbody');
      for (const m of M.filter((x) => x.bad)) {
        const tr = el('tr'); tr.append(who(m, runs(m.bad.reps)));
        kinds.forEach((k) => tr.append(el('td', 'cost', pct(m.bad.by_type[k]?.caught?.rate))));
        tbody.append(tr);
      }
      const tr = el('tr', 'best'), td = el('td', 'model', `All ${M.length} models together`); td.append(el('span', 'via', 'every reply, pooled'));
      tr.append(td); kinds.forEach((k) => tr.append(el('td', 'cost', pct(pooled.find(([t]) => t === k)?.[1])))); tbody.append(tr);
    }
    // With a calculator, November set: each model alone and with the planning engine to call
    const calcRows = (id, keep) => {
      if (!$(id)) return;
      head(id, [['Model'], ['On its own'], ['With the calculator'], ['Called it', true], ['Cost per 1,000 right, on its own → with it', true]]);
      const tbody = document.querySelector(`#${id} tbody`);
      const rows = M.filter((m) => !keep || keep.some((s) => m.model.includes(s)))
        .sort((a, b) => (b.hard_tools?.rate ?? b.hard.rate) - (a.hard_tools?.rate ?? a.hard.rate));
      for (const m of rows) {
        const tr = el('tr', m.hard_tools && m.hard_tools.rate - m.hard.rate > 0.3 ? 'best' : null);
        // writer B, round 2: say what each column averages, so a two-run score never sits unlabeled beside a one-run one
        const label = !m.hard_tools ? runs(m.hard.reps) : m.hard.reps > 1 ? `on its own: ${m.hard.reps} runs averaged · with it: ${runs(m.hard_tools.reps).replace(' per item', '')}` : 'one run each way';
        tr.append(who(m, label), bar(m.hard), bar(m.hard_tools),
          el('td', 'cost', m.hard_tools ? pct(m.hard_tools.call_rate) : '–'),
          el('td', 'cost', `${per1k(m.hard.cost_per_correct)}${m.hard_tools ? ` → ${per1k(m.hard_tools.cost_per_correct)}` : ''}`));
        tbody.append(tr);
      }
    };
    calcRows('calc-v2-key', ['deepseek', 'claude-sonnet', 'gpt-6.1-sol', 'gpt-oss', 'llama-4', 'mistral-small']);
    calcRows('calc-v2');
    if ($('calc-family')) {
      const FAM = { irmaa_headroom: 'Roth conversion, Medicare-safe', conv_cost_az: 'Roth conversion cost with Arizona tax', ss_muni_qcd: 'Taxable Social Security',
        inherited_rmd: 'Inherited IRA withdrawal', qcd_rmd_tax: 'Charity from a required withdrawal', widow_first_year: 'Widow’s first year', az_tax: 'Arizona tax' };
      head('calc-family', [['Model'], ...Object.values(FAM).map((t) => [t, true])]);
      const tbody = document.querySelector('#calc-family tbody');
      for (const m of [...M].sort((a, b) => (b.hard_tools?.rate ?? b.hard.rate) - (a.hard_tools?.rate ?? a.hard.rate))) {
        const tr = el('tr'); tr.append(who(m, m.hard_tools ? 'on its own → with it' : 'on its own'));
        Object.keys(FAM).forEach((f) => tr.append(el('td', 'cost', `${pct(m.hard.by_family[f]?.rate)}${m.hard_tools ? ` → ${pct(m.hard_tools.by_family?.[f]?.rate)}` : ''}`)));
        tbody.append(tr);
      }
    }

    // --- calculator, chat (writer B, round 2) ---
    // With a calculator, experiment 2: the paired comparison. Both columns are one run per question (the first run on
    // its own, the one run with the calculator), from v2.tool_effect; Sonnet on its own is the reference row.
    if ($('calc-paired')) {
      const wilson = (k, n) => { const z = 1.96, p = k / n, d = 1 + z * z / n, c = (p + z * z / (2 * n)) / d, w = (z * Math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d; return [Math.max(0, c - w), Math.min(1, c + w)]; };
      const frac = (k, n) => { const [lo, hi] = wilson(k, n), td = bar({ rate: k / n, lo, hi }); td.querySelector('.v').firstChild.textContent = `${pct(k / n)} · ${k}/${n}`; return td; };
      const tbody = document.querySelector('#calc-paired tbody');
      for (const t of [...v2.tool_effect].sort((a, b) => b.with - a.with)) {
        const m = M.find((x) => x.name === t.name), tr = el('tr', (t.with - t.without) / t.questions > 0.3 ? 'best' : null);
        tr.append(who(m, 'one run each way'), frac(t.without, t.questions), frac(t.with, t.questions),
          el('td', 'cost', `${t.fixed} / ${t.broken}`), el('td', 'cost', pct(m.hard_tools.call_rate)));
        tbody.append(tr);
      }
      const c = v2.comparisons?.[0];
      if (c && sonnet) {
        const tr = el('tr'); tr.append(who(sonnet, 'reference: not run with the calculator'), frac(c.b_right, c.questions), el('td', null, ''), el('td', 'cost', '–'), el('td', 'cost', '–'));
        tr.children[2].append(el('span', 'ci', 'not run')); tbody.append(tr);
      }
    }
  }

  // --- calculator, chat (writer B, round 2) --- Chat demo: each side's total, and why the totals don't add up to the
  // headline figures (each year's own dollars vs today's money; mcp/card.ts in the engine repo prints the same note)
  if (document.body.dataset.page === 'chat' && $('c-accounting')) {
    const cx = await get('connector'), a = cx?.answer;
    if (a) {
      const total = (side, id) => {
        const shown = side.reasons.reduce((t, r) => t + Math.abs(r.amount), 0), all = Math.abs(side.amount);
        const li = el('li', 'total'); li.append(el('span', null, `Total, ${side.years}${Math.round(shown) === Math.round(all) ? '' : ' (the biggest reasons are listed; smaller ones make up the rest)'}`), el('b', null, usd(all)));
        $(id).append(li);
      };
      total(a.costs_now, 'c-costs'); total(a.saves_later, 'c-saves');
      const k = (re) => a.key_numbers.find((n) => re.test(n.label))?.value;
      $('c-accounting').textContent = `How these fit the figures above: the costs and savings are each year’s own dollars, added up as they would appear on the tax returns. `
        + `The lifetime tax change (${k(/lifetime tax/i)}) and “better off” (${k(/better off/i)}) are in today’s money, which counts a dollar paid decades from now as worth less. `
        + '“Better off” also counts what’s left in every account at the end, so it isn’t the tax change alone. The two kinds of figure measure different things and aren’t meant to add up.';
    }
  }

  // Charts are drawn at the container's width, so redraw on resize.
  const measure = (svg, text) => { const t = svgEl('text', { class: 'lbl' }); t.textContent = text; svg.append(t); const w = t.getComputedTextLength(); t.remove(); return w; };

  function ruleChart() {
    const box = document.getElementById('rule-chart');
    if (!box) return;
    if (!ruleEffect?.length) { box.textContent = 'No run with the rule yet.'; return; }
    box.textContent = '';
    const rows = ruleEffect.map((r) => ({ ...r, label: `${name(r.model).replace('Claude ', '')} · ${r.task.replace(/_/g, ' ')}` }));
    const W = Math.max(280, box.clientWidth), rowH = 40, top = 8, bottom = 28;
    const svg = svgEl('svg', { viewBox: `0 0 ${W} ${top + rows.length * rowH + bottom}` });
    box.append(svg);
    const left = Math.max(...rows.map((r) => measure(svg, r.label))) + 16, right = 16;
    const x = (v) => left + v * (W - left - right);
    const H = top + rows.length * rowH;
    for (const t of [0, 0.25, 0.5, 0.75, 1]) {
      svg.append(svgEl('line', { x1: x(t), x2: x(t), y1: top, y2: H, style: 'stroke:var(--rule)' }));
      const lab = svgEl('text', { x: x(t), y: H + 18, 'text-anchor': 'middle' }); lab.textContent = pct(t); svg.append(lab);
    }
    rows.forEach((r, i) => {
      const y = top + i * rowH + rowH / 2;
      const lab = svgEl('text', { x: left - 12, y, dy: '0.32em', 'text-anchor': 'end', class: 'lbl' }); lab.textContent = r.label; svg.append(lab);
      svg.append(svgEl('line', { x1: x(r.without_rule), x2: x(r.with_rule), y1: y, y2: y, style: 'stroke:var(--accent);stroke-width:2' }));
      svg.append(svgEl('circle', { cx: x(r.without_rule), cy: y, r: 5, style: 'fill:var(--paper);stroke:var(--accent);stroke-width:2' }));
      svg.append(svgEl('circle', { cx: x(r.with_rule), cy: y, r: 5, style: 'fill:var(--accent)' }));
      const title = svgEl('title', {}); title.textContent = `${r.label}: ${pct(r.without_rule)} → ${pct(r.with_rule)}`; svg.lastChild.append(title);
    });
  }

  function mistakeChart() {
    const box = document.getElementById('mistake-chart');
    if (!box) return;
    if (!mistakes?.length) { box.textContent = 'No wrong answers yet.'; return; }
    box.textContent = '';
    const ms = [...new Set(mistakes.map((r) => r.model))];
    // Four groups keep the bars readable: the two stale-rule misreadings the story is about, other named
    // mistakes (wrong cents, one-step shortcuts, flagging a non-issue, ...), and wrong answers no rule explains.
    const GROUPS = [
      ['Senior deduction misread', (k) => k === 'combined senior phase-out', 'var(--bad)'],
      ['Pre-2022 RMD table', (k) => k === 'pre-2022 RMD table', 'var(--accent)'],
      ['Other named mistake', (k) => k !== 'unexplained', 'color-mix(in srgb, var(--accent) 45%, var(--muted))'],
      ['Unexplained', () => true, 'color-mix(in srgb, var(--muted) 40%, transparent)'],
    ];
    const group = (k) => GROUPS.findIndex(([, test]) => test(k));
    const count = (m, gi) => mistakes.filter((r) => r.model === m && group(r.mistake) === gi).reduce((s, r) => s + r.count, 0);
    const used = GROUPS.map((_, gi) => ms.some((m) => count(m, gi) > 0));
    const W = Math.max(280, box.clientWidth), rowH = 40, top = 8;
    const svg = svgEl('svg', {});
    box.append(svg);
    const left = Math.max(...ms.map((m) => measure(svg, name(m).replace('Claude ', '')))) + 16, right = 16;
    const totals = ms.map((m) => GROUPS.reduce((s, _, gi) => s + count(m, gi), 0));
    const x = (v) => left + (v / Math.max(...totals)) * (W - left - right);
    ms.forEach((m, i) => {
      const y = top + i * rowH;
      const lab = svgEl('text', { x: left - 12, y: y + 14, dy: '0.32em', 'text-anchor': 'end', class: 'lbl' }); lab.textContent = name(m).replace('Claude ', ''); svg.append(lab);
      let x0 = 0;
      GROUPS.forEach(([title, , color], gi) => {
        const n = count(m, gi);
        if (!n) return;
        const w = Math.max(0, x(x0 + n) - x(x0) - 2);
        const rect = svgEl('rect', { x: x(x0), y, width: w, height: 28, rx: 3, style: `fill:${color}` });
        const tip = svgEl('title', {}); tip.textContent = `${name(m)}: ${n} × ${title[0].toLowerCase() + title.slice(1)}`; rect.append(tip); svg.append(rect);
        if (w > 22) { const t = svgEl('text', { x: x(x0) + 8, y: y + 14, dy: '0.32em', style: `fill:${gi === 0 ? 'var(--paper)' : 'var(--ink)'};font-family:var(--mono)` }); t.textContent = n; svg.append(t); }
        x0 += n;
      });
    });
    // Legend under the bars, wrapping onto new lines at narrow widths
    let lx = left, ly = top + ms.length * rowH + 10;
    GROUPS.forEach(([title, , color], gi) => {
      if (!used[gi]) return;
      const t = svgEl('text', { x: 0, y: 0, dy: '0.32em' }); t.textContent = title; svg.append(t);
      const w = 16 + t.getComputedTextLength() + 20;
      if (lx + w > W - right && lx > left) { lx = left; ly += 20; }
      t.setAttribute('x', lx + 16); t.setAttribute('y', ly + 5);
      svg.append(svgEl('rect', { x: lx, y: ly, width: 10, height: 10, rx: 2, style: `fill:${color}` }));
      lx += w;
    });
    svg.setAttribute('viewBox', `0 0 ${W} ${ly + 22}`);
  }

  // Question tiers
  const TIERS = [
    ['single-step', 'One rule', 'One rule at a time: a tax bracket, an RMD divisor, a Social Security claiming factor, a Medicare premium tier.', 'single_step_accuracy'],
    ['multi-step', 'A few steps', 'Two rules that interact, like a Roth conversion that also makes more Social Security taxable (the “tax torpedo”).', 'multi_step_accuracy'],
    ['stacked', 'Several rules at once', 'Tax, Social Security, the senior deduction and Medicare’s income-based premiums (IRMAA) meeting in one household.', 'stacked_accuracy'],
    ['compliance', 'Compliance review', 'A planted problem a reviewer must catch: a rollover issue, a missed sales-charge discount, a misleading sentence.', 'compliance_accuracy'],
  ];
  const fmtAnswer = (ex, v) => (ex.task === 'comms_review' ? (v === 'NONE' ? 'None' : `Sentences ${String(v).replace(/,/g, ', ')}`)
    : ex.task === 'breakpoint' ? `${v}%` : usd(v));
  if (examples && $('tiers')) {
    const host = document.getElementById('tiers');
    for (const [key, title, blurb, col] of TIERS) {
      const ex = examples.find((e) => e.tier === key);
      const card = el('article', 'tier');
      const topRow = el('div', 'tier-top');
      topRow.append(el('span', 'tier-name', title));
      if (lead) topRow.append(el('span', 'tier-score', pct(lead[col])));
      card.append(topRow, el('p', 'tier-blurb', blurb));
      if (meta?.tiers?.[key]) { const t = el('div', 'tasks'); meta.tiers[key].forEach((n) => t.append(el('code', null, n))); card.append(t); }
      if (ex) {
        const d = el('details');
        d.append(el('summary', null, ex.title));
        d.append(el('p', 'q', ex.prompt));
        const k = el('div', 'key');
        const item = (label, v) => { const s = el('span'); s.append(`${label} `, el('b', null, v)); return s; };
        k.append(item('Answer key', fmtAnswer(ex, ex.answer)));
        // A reply with no number (ran out of room, or the request failed) says so instead of showing $0.
        for (const [m, r] of Object.entries(ex.replies)) k.append(item(name(m).replace('Claude ', ''), r.got == null ? (r.bucket === 'truncated' ? 'Ran out of room ✗' : 'No answer') : `${fmtAnswer(ex, r.got)} ${r.bucket === 'correct' ? '✓' : '✗'}`));
        d.append(k);
        card.append(d);
      }
      host.append(card);
    }
    if (lead) document.getElementById('questions-sub').append(` The score on each card is ${name(lead.model)}’s.`);
  }

  // Accuracy against what a right answer costs, on a log scale: up and to the left is better.
  function valueChart() {
    const box = document.getElementById('value-chart');
    if (!box) return;
    const pts = (models ?? []).filter((m) => m.cost_per_correct);
    if (!pts.length) { box.textContent = 'No priced runs yet.'; return; }
    box.textContent = '';
    const W = Math.max(300, box.clientWidth), H = W < 520 ? 440 : 340, L = 48, R = 16, T = 12, B = 44;
    const costs = pts.map((m) => m.cost_per_correct * 1000);
    const lo = Math.log10(Math.min(...costs) / 1.6), hi = Math.log10(Math.max(...costs) * 1.6);
    const x = (c) => L + ((Math.log10(c) - lo) / (hi - lo)) * (W - L - R);
    const y = (a) => T + (1 - a) * (H - T - B);
    const svg = svgEl('svg', { viewBox: `0 0 ${W} ${H}` });
    box.append(svg);
    for (const a of [0, 0.25, 0.5, 0.75, 1]) {
      svg.append(svgEl('line', { x1: L, x2: W - R, y1: y(a), y2: y(a), style: 'stroke:var(--rule)' }));
      const t = svgEl('text', { x: L - 8, y: y(a), dy: '0.32em', 'text-anchor': 'end' }); t.textContent = pct(a); svg.append(t);
    }
    for (let e = Math.ceil(lo); e <= Math.floor(hi); e++) {
      for (const k of [1, 3]) {
        const c = k * 10 ** e; if (Math.log10(c) < lo || Math.log10(c) > hi) continue;
        svg.append(svgEl('line', { x1: x(c), x2: x(c), y1: T, y2: H - B, style: 'stroke:var(--rule);stroke-dasharray:2 3' }));
        const t = svgEl('text', { x: x(c), y: H - B + 18, 'text-anchor': 'middle' }); t.textContent = usd(c, c < 1); svg.append(t);
      }
    }
    const cap = svgEl('text', { x: (L + W - R) / 2, y: H - 6, 'text-anchor': 'middle', class: 'lbl' }); cap.textContent = 'Cost per 1,000 right answers (log scale)'; svg.append(cap);
    // Dots and interval lines first, then labels, nudged apart vertically where models sit close together.
    const placed = [];
    for (const m of pts.sort((a, b) => b.accuracy - a.accuracy)) {
      const cx = x(m.cost_per_correct * 1000), cy = y(m.accuracy);
      svg.append(svgEl('line', { x1: cx, x2: cx, y1: y(m.hi), y2: y(m.lo), style: 'stroke:var(--accent);stroke-width:2;opacity:0.35' }));
      const dot = svgEl('circle', { cx, cy, r: 6, style: `fill:${m.open_weights ? 'var(--paper)' : 'var(--accent)'};stroke:var(--accent);stroke-width:2` });
      const title = svgEl('title', {}); title.textContent = `${name(m.model)}: ${pct(m.accuracy)} (${pct(m.lo)}–${pct(m.hi)}), ${usd(m.cost_per_correct * 1000, true)} per 1,000 right answers`;
      dot.append(title); svg.append(dot);
      placed.push({ m, cx, cy, ly: cy });
    }
    // Each label tries the right side, then the left, at growing vertical offsets, and takes the first spot that
    // overlaps no other label or dot and stays inside the plot. A leader line joins a moved label to its dot.
    const boxes = placed.map((p) => ({ x0: p.cx - 7, x1: p.cx + 7, y0: p.cy - 7, y1: p.cy + 7 }));
    const hit = (b) => boxes.some((o) => b.x0 < o.x1 && b.x1 > o.x0 && b.y0 < o.y1 && b.y1 > o.y0);
    placed.sort((a, b) => a.cy - b.cy);
    for (const p of placed) {
      const t = svgEl('text', { dy: '0.32em', class: 'lbl' }); t.textContent = name(p.m.model); svg.append(t);
      const w = t.getComputedTextLength(), h = 14;
      let spot = null;
      for (const dy of [0, 15, -15, 30, -30, 45, -45, 60, -60]) {
        for (const right of [true, false]) {
          const x0 = right ? p.cx + 11 : p.cx - 11 - w, ly = p.cy + dy;
          const b = { x0, x1: x0 + w, y0: ly - h / 2, y1: ly + h / 2 };
          if (b.x0 < L || b.x1 > W - R || b.y0 < T || b.y1 > H - B || hit(b)) continue;
          spot = { b, right, ly }; break;
        }
        if (spot) break;
      }
      spot ??= { b: { x0: p.cx + 11, x1: p.cx + 11 + w, y0: p.cy - 7, y1: p.cy + 7 }, right: true, ly: p.cy };
      boxes.push(spot.b);
      t.setAttribute('x', spot.right ? spot.b.x0 : spot.b.x1); t.setAttribute('y', spot.ly);
      if (!spot.right) t.setAttribute('text-anchor', 'end');
      if (Math.abs(spot.ly - p.cy) > 2)
        svg.append(svgEl('line', { x1: p.cx + (spot.right ? 6 : -6), y1: p.cy, x2: spot.right ? spot.b.x0 - 2 : spot.b.x1 + 2, y2: spot.ly, style: 'stroke:var(--muted);stroke-width:1' }));
    }
  }

  // --- home, alone, method (writer A) ---
  // Numbers the story pages say in sentences, worked out here from the data files so a regrade changes the words with it.
  // Fills <span data-k="a_*"> (the bake checks every data-k slot is filled) and the two short tables on alone.html.
  if (document.querySelector('[data-k^="a_"], #a-v1-top, #a-v2-top')) {
    const V2 = await load('v2'), A = {};
    const span = (xs) => { const [lo, hi] = [Math.min(...xs), Math.max(...xs)]; return pct(lo) === pct(hi) ? pct(lo) : `${pct(lo).replace('%', '')}–${pct(hi)}`; };
    const words = ['no', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven'];
    const vm = V2?.models ?? [], vName = (n) => vm.find((m) => m.name === n);
    const sol = vName('GPT-6.1 Sol'), son = vName('Claude Sonnet 5.5'), dsk = vName('DeepSeek V4.1 Flash'), BEST = ['GPT-6.1 Sol', 'Claude Sonnet 5.5'];
    const cheap = vm.filter((m) => m.tier === 'cheap');
    if (vm.length) {
      const under30 = cheap.filter((m) => m.hard.rate < 0.3).length;
      A.a_v2_models = String(vm.length);
      A.a_v2_labs = words[new Set(vm.map((m) => m.lab)).size];
      A.a_cheap_under30 = under30 === cheap.length ? `all ${cheap.length}` : `${under30} of the ${cheap.length}`;
      A.a_tools_weak = words[cheap.filter((m) => m !== dsk && m.hard_tools && m.hard_tools.rate < 0.1).length];
      // Wrong facts: the two best models' catch rate, and the three models that caught least (as on wrong-facts.html)
      A.a_best_caught = sol && son && span([sol.bad.caught.rate, son.bad.caught.rate]);
      const low3 = vm.filter((m) => m.bad).sort((a, b) => a.bad.caught.rate - b.bad.caught.rate).slice(0, 3);
      A.a_low_caught = span(low3.map((m) => m.bad.caught.rate));
      A.a_low_silent = span(low3.map((m) => m.bad.silent_number.rate));
      A.a_low_cheap = low3.every((m) => m.tier === 'cheap') ? 'Three of the cheap and free models' : 'Three models';
      A.a_low_names = low3.map((m) => m.name.replace(/ \(\d+\)$/, '')).join(', ').replace(/, ([^,]*)$/, ' and $1');
      // round 2: how many planted mistakes even the two best missed (home's straight answer)
      A.a_best_missed = sol && son && span([1 - sol.bad.caught.rate, 1 - son.bad.caught.rate]);
    }
    // round 3: ChatGPT (GPT-6 Luna on a subscription, data/luna.json). Its multi-step and stacked tiers are added together:
    // that is exactly the five chaining/stacking tasks (10 each) and doesn't depend on which tier senior_phaseout sits in.
    const LU = await load('luna');
    if (LU) {
      const ms = LU.first_test.multi_step, st = LU.first_test.stacked, k = ms.k + st.k, n = ms.n + st.n;
      Object.assign(A, { a_luna_hard_n: String(n), a_luna_hard_rate: pct(k / n), a_luna_hard_kn: `${k} of ${n}`,
        a_luna_missed: pct(1 - LU.bad.caught.rate), a_luna_hard_ci: range(LU.hard.lo, LU.hard.hi) + '%',
        a_luna_single_ci: range(LU.first_test.single_step.lo, LU.first_test.single_step.hi) + '%',
        a_luna_unnamed: String(LU.bad.judged - LU.bad.named.k),
        // structural pass: the second wrong-facts measure, "stopped and asked" = gave no number (caught + declined for another reason)
        a_luna_stopped: pct((LU.bad.caught.k + LU.bad.declined_other_reason.k) / LU.bad.caught.n) });
      // whole-household: one question per family plus one trap whose honest answer is "can't answer"
      const hh = LU.household, answerable = hh.n - 1;
      A.a_luna_household = `${hh.declined_answerable === answerable ? 'all' : hh.declined_answerable + ' of'} ${answerable} answerable ones`;
    }
    // round 3: home's reading path says how the 50 hardest first-test questions were picked (the multi-step and stacked kinds)
    if (meta?.tiers) A.a_hard_tasks = words[meta.tiers['multi-step'].length + meta.tiers.stacked.length];
    // round 2: first-test questions actually asked of each model (per-task count × tasks), next to the 2,800 generated
    const ft = sys.first_test;
    if (ft && meta) A.a_v1_per_model = `${ft.per_task_claude * meta.tasks}–${ft.per_task_openrouter * meta.tasks}`;
    // round 2: the worked question's table shows one row per setup; Claude Haiku 5.5 was asked two ways
    if (misread.length) A.a_misread_rows = words[misread.length];
    // First test: how much of the wrong-answer pile one misreading explains (both published runs, every model)
    if (mistakes?.length) {
      const SD = 'combined senior phase-out', sum = (f) => mistakes.filter(f).reduce((t, r) => t + r.count, 0);
      const wrong = sum(() => true), named = sum((r) => r.mistake !== 'unexplained'), sd = sum((r) => r.mistake === SD);
      Object.assign(A, { a_sd: String(sd), a_wrong: String(wrong), a_named: String(named), a_sd_of_wrong: pct(sd / wrong), a_sd_of_named: pct(sd / named),
        a_son_sd: `${sum((r) => r.model === LEAD && r.mistake === SD)} of its ${sum((r) => r.model === LEAD)}` });
    }
    const re = (m) => ruleEffect?.find((r) => r.model === m && r.task === 'senior_phaseout');
    if (re(LEAD)) A.a_rule_son = `${pct(re(LEAD).without_rule)} to ${pct(re(LEAD).with_rule)}`;
    if (re('claude-haiku-5-5')) A.a_rule_haiku = `${pct(re('claude-haiku-5-5').without_rule)} to ${pct(re('claude-haiku-5-5').with_rule)}`;
    if (models?.length) {
      const comp = models.map((m) => m.compliance_accuracy).filter((x) => x != null);
      A.a_comp = span(comp); A.a_setups = words[models.length] ?? String(models.length);
      A.a_v1_labs = words[new Set(models.map((m) => m.lab)).size];
      A.a_v1_models = words[new Set(models.map((m) => m.name)).size];
    }
    document.querySelectorAll('[data-k^="a_"]').forEach((n) => { if (A[n.dataset.k] != null) n.textContent = A[n.dataset.k]; else console.warn('data-k not found:', n.dataset.k); });

    // alone.html: two short tables up front (a few rows that tell the story); the full ones sit in <details>
    const bar = (v, lo, hi, extra) => {
      const td = el('td'); if (v == null) { td.append(el('span', 'ci', 'not run')); return td; }
      const cell = el('div', `cell${v < 0.5 ? ' low' : ''}`), track = el('div', 'track'), band = el('div', 'band-ci'), fill = el('div', 'fill');
      band.style.left = `${lo * 100}%`; band.style.width = `${(hi - lo) * 100}%`; fill.style.width = `${v * 100}%`;
      track.append(band, fill); const t = el('span', 'v', `${pct(v)}${extra ? ` · ${extra}` : ''}`); t.append(el('span', 'ci', range(lo, hi)));
      cell.append(t, track); td.append(cell); return td;
    };
    const who = (label, via) => { const td = el('td', 'model', label); if (via) td.append(el('span', 'via', via)); return td; };
    if ($('a-v1-top') && models) {
      const tb = document.querySelector('#a-v1-top tbody');
      for (const id of [LEAD, 'claude-haiku-5-5', 'or:deepseek/deepseek-v4.1-flash@deepinfra/fp8', 'or:z-ai/glm-5.3-flash@z-ai/fp8', 'or:openai/gpt-oss-120b@deepinfra/bf16']) {
        const m = byId[id]; if (!m) continue;
        const tr = el('tr'); tr.append(who(name(id), `${m.lab}${m.open_weights ? ' · free to download' : ''}`),
          bar(m.single_step_accuracy, m.single_step_lo, m.single_step_hi), bar(m.stacked_accuracy, m.stacked_lo, m.stacked_hi));
        tb.append(tr);
      }
    }
    const v2row = (m) => {
      const h = m.hard, tr = el('tr');
      // round 3: one group label per model, the same words as home's "How to read the numbers"
      const group = BEST.includes(m.name) ? 'the best models' : { frontier: 'top-priced', mid: 'mid-priced', cheap: 'cheap and free' }[m.tier] ?? '';
      tr.append(who(m.name, `${m.lab}${group ? ` · ${group}` : ''}`), bar(h.rate, h.lo, h.hi, `${h.k}/${h.n}`), el('td', 'cost', h.truncated ? pct(h.truncated) : '–'));
      return tr;
    };
    if ($('a-v2-top') && vm.length) {
      const tb = document.querySelector('#a-v2-top tbody');
      ['GPT-6.1 Sol', 'Claude Sonnet 5.5', 'Gemini 3.1 Pro', 'DeepSeek V4.1 Flash', 'Llama 4 Maverick'].map(vName).filter(Boolean)
        .sort((a, b) => b.hard.rate - a.hard.rate).forEach((m) => tb.append(v2row(m)));
    }
    if ($('a-v2-all') && vm.length) {
      const tb = document.querySelector('#a-v2-all tbody');
      for (const m of [...vm].sort((a, b) => b.hard.rate - a.hard.rate)) {
        const tr = v2row(m), h = m.hard;
        tr.append(el('td', 'cost', String(h.reps)), el('td', 'cost', h.cost_per_correct == null ? '–' : usd(h.cost_per_correct * 1000, true)));
        tb.append(tr);
      }
    }
    // round 2: the full first-test tables say who made each model; the route and host (with fp8/bf16) are listed
    // only in the technical toggle (#a-hosts), so a normal reader never meets "OpenRouter → DeepInfra (fp8)".
    if (models && $('scores')) {
      const plain = Object.fromEntries(models.map((m) => [m.access + (m.open_weights ? ' · open weights' : ''), `${m.lab}${m.open_weights ? ' · free to download' : ''}`]));
      document.querySelectorAll('#scores .via, #dollars .via').forEach((n) => { if (plain[n.textContent]) n.textContent = plain[n.textContent]; });
    }
    if (models && $('a-hosts')) {
      for (const m of models) { const li = el('li'); li.append(el('b', null, name(m.model)), document.createTextNode(` ${m.access}`)); $('a-hosts').append(li); }
    }
    // round 3: the compliance example quotes a rule number a normal reader can't use; say it in plain words instead
    document.querySelectorAll('#tiers details').forEach((d) => {
      const sm = d.querySelector('summary'), q = d.querySelector('p.q');
      if (!/Rule 2210/.test(sm?.textContent ?? '')) return;
      sm.textContent = 'Spotting misleading sentences in an email to clients';
      q.textContent = q.textContent.replace(/FINRA Rule 2210\(d\)\(1\)/g, '[The securities industry’s rule on advertising to clients]').replace(/Rule 2210\(d\)\(1\)/g, '[that rule]');
      q.after(el('p', 'rp-gloss', 'Rule numbers are replaced with plain words in brackets; the exact wording is in data/cases.jsonl in the code.'));
    });
    // A chart in a closed <details> has no width to draw at; open those for the drawing below and close them after it.
    const shut = [...document.querySelectorAll('details.draw-open:not([open])')];
    shut.forEach((d) => { d.open = true; });
    queueMicrotask(() => shut.forEach((d) => { d.open = false; }));
  }

  const draw = () => { ruleChart(); mistakeChart(); valueChart(); };
  draw();
  // The browser jumped to a #section before the data filled in and moved it; jump again now that layout is final.
  if (location.hash) document.getElementById(location.hash.slice(1))?.scrollIntoView();
  let raf; addEventListener('resize', () => { cancelAnimationFrame(raf); raf = requestAnimationFrame(draw); });
})();
