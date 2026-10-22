// Fills the page from data/*.json, which src/build_site.py writes from the graded runs.
(async () => {
  const get = (name) => fetch(`data/${name}.json`).then((r) => (r.ok ? r.json() : null)).catch(() => null);
  const [models, mistakes, ruleEffect, examples, featured, meta, byMistake, tools, toolsPrivate] = await Promise.all(
    ['models', 'mistakes', 'rule_effect', 'examples', 'featured', 'meta', 'dollars_by_mistake', 'tools', 'tools_private'].map(get));

  const pct = (x) => (x == null ? '—' : `${Math.round(x * 100)}%`);
  const usd = (x, cents = false) => '$' + Number(x).toLocaleString('en-US', { minimumFractionDigits: cents ? 2 : 0, maximumFractionDigits: cents ? 2 : 0 });
  // Names come from models.json; when one model was run two ways (direct and via OpenRouter), say which.
  const byId = Object.fromEntries((models ?? []).map((m) => [m.model, m]));
  const dupes = new Set((models ?? []).map((m) => m.name).filter((n, i, all) => all.indexOf(n) !== i));
  const name = (id) => { const m = byId[id]; if (!m) return id; return dupes.has(m.name) && id.startsWith('or:') ? `${m.name} via OpenRouter` : m.name; };
  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
  const NS = 'http://www.w3.org/2000/svg';
  const svgEl = (tag, attrs) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); return e; };
  const LEAD = 'claude-sonnet-5-5';
  const lead = models?.find((m) => m.model === LEAD) ?? models?.[0];

  // Hero figures
  const rule = ruleEffect?.find((r) => r.model === LEAD && r.task === 'senior_phaseout');
  const fig = { single: lead && pct(lead.single_step_accuracy), stacked: lead && pct(lead.stacked_accuracy), rule: rule && pct(rule.with_rule),
                questions: meta && meta.questions.toLocaleString('en-US') };
  document.querySelectorAll('[data-k]').forEach((n) => { if (fig[n.dataset.k]) n.textContent = fig[n.dataset.k]; });

  // Worked question
  if (featured) {
    document.getElementById('featured-prompt').textContent = featured.prompt;
    const dl = document.getElementById('featured-answers');
    const row = (label, value, ok) => {
      const d = el('div'); d.append(el('dt', null, label));
      const dd = el('dd', null, value);
      if (ok != null) dd.append(el('span', `mark ${ok ? 'ok' : 'bad'}`, ok ? 'Right' : 'Wrong'));
      d.append(dd); dl.append(d);
    };
    row('Answer key', usd(featured.answer));
    for (const [m, r] of Object.entries(featured.replies)) row(name(m), usd(r.got), r.bucket === 'correct');
    for (const [m, r] of Object.entries(featured.with_rule || {})) row(`${name(m)}, given the rule`, usd(r.got), r.bucket === 'correct');

    const s = featured.steps;
    const lines = [
      ['31', 'Modified adjusted gross income', usd(s.agi, true)],
      ['32', 'Threshold, married filing jointly', usd(s.threshold, true)],
      ['33', 'Line 31 minus line 32', usd(s.agi - s.threshold, true)],
      ['34', 'Line 33 × 6%', usd(s.cut, true)],
      ['35', '$6,000 minus line 34', usd(6000 - s.cut, true)],
      ['36a', 'You, born before 1961: line 35', usd(6000 - s.cut, true)],
      ['36b', 'Your spouse, born before 1961: line 35', usd(6000 - s.cut, true)],
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
  if (models) {
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
  if (models) {
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
  if (tools) {
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
    const tbody = document.querySelector('#ladder tbody');
    const priv = Object.fromEntries((toolsPrivate?.stages ?? []).map((s) => [s.key, s]));
    for (const s of tools.hard.stages) {
      const tr = el('tr', s.key === 'v2' ? 'best' : null);
      tr.append(el('td', 'model', s.label), scoreCell(s), scoreCell(priv[s.key]));
      const off = el('td', 'overall', usd(s.dollars_off));
      if (priv[s.key]) off.append(el('span', 'ci', `held-out ${usd(priv[s.key].dollars_off)}`));
      tr.append(off); tbody.append(tr);
    }
    const p = tools.hard.pairs, fmtP = (x) => (x < 0.001 ? 'p < 0.001' : `p = ${x.toFixed(3)}`);
    document.getElementById('ladder-note').textContent = `The same ${tools.hard.questions} questions in every row (${tools.hard.tasks.length} tasks, 10 each). `
      + `The right number alone fixed ${p.none_to_v1.fixed} and broke ${p.none_to_v1.broken}; adding the rule and its source fixed ${p.v1_to_v2.fixed} more and broke ${p.v1_to_v2.broken} (${fmtP(p.v1_to_v2.p)}, paired). `
      + (toolsPrivate ? `On ${toolsPrivate.questions} held-out questions, never seen while the tools were built: ${toolsPrivate.pairs.none_to_v2.fixed} fixed, ${toolsPrivate.pairs.none_to_v2.broken} broken. ` : '')
      + 'Shaded bands are 95% intervals.';

    const q = tools.quote;
    document.getElementById('tools-quote').textContent = `“${q.text}”`;
    const dl = document.getElementById('tools-answers');
    const row = (label, value, ok) => {
      const d = el('div'); d.append(el('dt', null, label)); const dd = el('dd', null, value);
      if (ok != null) dd.append(el('span', `mark ${ok ? 'ok' : 'bad'}`, ok ? 'Right' : 'Wrong'));
      d.append(dd); dl.append(d);
    };
    row('Tool’s answer, and the key', usd(q.key));
    row('Haiku with tools 1.0', usd(q.answered), q.answered === q.key);
    row('Haiku with tools 1.1', usd(q.answered_v2), q.v2_right);

    const sd = q.v2_senior_deduction, ol = document.getElementById('tools-lines');
    for (const [what, amt, total] of [['MAGI over the $150,000 threshold', usd(sd.magi_over_threshold, true)],
      ['Reduction per person (6%)', usd(sd.reduction_per_person, true)], ['Senior deduction per person', usd(sd.per_person, true)],
      ['People 65 or older', String(sd.people)], ['Senior deduction', usd(sd.total, true), true]]) {
      const li = el('li', total ? 'total' : null); li.append(el('span', 'what', what), el('span', 'amt', amt)); ol.append(li);
    }
    document.getElementById('tools-rule').textContent = sd.rule;

    const w = tools.whole;
    document.getElementById('tools-whole').textContent = `Across all ${w.questions} questions, tools 1.0 lifted Haiku from ${pct(w.without.accuracy)} to ${pct(w.with.accuracy)} `
      + `(${w.fixed} fixed, ${w.broken} broken, ${fmtP(w.p)}); single-step questions were already at ${pct(w.by_tier['single-step'].without)}. `
      + `But ${w.overruled} of the ${w.misses} misses left were Haiku getting the right number from the tool and replacing it, every time saying so.`;
    document.getElementById('tools-private').textContent = toolsPrivate
      ? `On ${toolsPrivate.questions} private questions from a secret seed: ${pct(toolsPrivate.stages[0].accuracy)} without tools, ${pct(toolsPrivate.stages.at(-1).accuracy)} with tools 1.1. Both misses were Haiku overruling the tool again, with the rule in front of it.`
      : 'Held-out results aren’t published yet.';
  }

  // Charts are drawn at the container's width, so redraw on resize.
  const measure = (svg, text) => { const t = svgEl('text', { class: 'lbl' }); t.textContent = text; svg.append(t); const w = t.getComputedTextLength(); t.remove(); return w; };

  function ruleChart() {
    const box = document.getElementById('rule-chart');
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
        const tip = svgEl('title', {}); tip.textContent = `${name(m)}: ${n} × ${title.toLowerCase()}`; rect.append(tip); svg.append(rect);
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
    ['single-step', 'Single-step', 'One rule at a time: a tax bracket, an RMD divisor, a Social Security claiming factor, a Medicare premium tier.', 'single_step_accuracy'],
    ['multi-step', 'Multi-step', 'Two rules that interact, like a Roth conversion that also makes more Social Security taxable.', 'multi_step_accuracy'],
    ['stacked', 'Stacked', 'Tax, Social Security, the senior deduction and Medicare premiums meeting in one household.', 'stacked_accuracy'],
    ['compliance', 'Compliance review', 'A planted problem a reviewer must catch: a rollover issue, a missed sales-charge discount, a misleading sentence.', 'compliance_accuracy'],
  ];
  const fmtAnswer = (ex, v) => (ex.task === 'comms_review' ? (v === 'NONE' ? 'None' : `Sentences ${String(v).replace(/,/g, ', ')}`)
    : ex.task === 'breakpoint' ? `${v}%` : usd(v));
  if (examples) {
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
        for (const [m, r] of Object.entries(ex.replies)) k.append(item(name(m).replace('Claude ', ''), `${fmtAnswer(ex, r.got)} ${r.bucket === 'correct' ? '✓' : '✗'}`));
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

  const draw = () => { ruleChart(); mistakeChart(); valueChart(); };
  draw();
  // The browser jumped to a #section before the data filled in and moved it; jump again now that layout is final.
  if (location.hash) document.getElementById(location.hash.slice(1))?.scrollIntoView();
  let raf; addEventListener('resize', () => { cancelAnimationFrame(raf); raf = requestAnimationFrame(draw); });
})();
