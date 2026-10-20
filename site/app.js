// Fills the page from data/*.json, which src/build_site.py writes from the graded runs.
(async () => {
  const get = (name) => fetch(`data/${name}.json`).then((r) => (r.ok ? r.json() : null)).catch(() => null);
  const [models, mistakes, ruleEffect, examples, featured, meta] = await Promise.all(
    ['models', 'mistakes', 'rule_effect', 'examples', 'featured', 'meta'].map(get));

  const pct = (x) => (x == null ? '—' : `${Math.round(x * 100)}%`);
  const usd = (x, cents = false) => '$' + Number(x).toLocaleString('en-US', { minimumFractionDigits: cents ? 2 : 0, maximumFractionDigits: cents ? 2 : 0 });
  const name = (m) => m.replace(/^claude-/, 'Claude ').replace(/-(\d+)-(\d+)$/, ' $1.$2').replace(/ (\w)/, (s, c) => ' ' + c.toUpperCase());
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
      tr.append(el('td', 'model', name(m.model)));
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
      tr.append(overall, el('td', 'cost', m.cost_per_correct == null ? '—' : usd(m.cost_per_correct * 1000, true)));
      tbody.append(tr);
    }
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
    const kinds = [...new Set(mistakes.map((r) => r.mistake))].sort((a, b) => (a === 'unexplained') - (b === 'unexplained'));
    const W = Math.max(280, box.clientWidth), rowH = 40, top = 8;
    const svg = svgEl('svg', {});
    box.append(svg);
    const left = Math.max(...ms.map((m) => measure(svg, name(m).replace('Claude ', '')))) + 16, right = 16;
    const totals = ms.map((m) => mistakes.filter((r) => r.model === m).reduce((s, r) => s + r.count, 0));
    const x = (v) => left + (v / Math.max(...totals)) * (W - left - right);
    const fill = (k) => (k === 'unexplained' ? 'color-mix(in srgb, var(--muted) 40%, transparent)' : 'var(--bad)');
    ms.forEach((m, i) => {
      const y = top + i * rowH;
      const lab = svgEl('text', { x: left - 12, y: y + 14, dy: '0.32em', 'text-anchor': 'end', class: 'lbl' }); lab.textContent = name(m).replace('Claude ', ''); svg.append(lab);
      let x0 = 0;
      for (const k of kinds) {
        const r = mistakes.find((q) => q.model === m && q.mistake === k);
        if (!r) continue;
        const w = Math.max(0, x(x0 + r.count) - x(x0) - 2);
        svg.append(svgEl('rect', { x: x(x0), y, width: w, height: 28, rx: 3, style: `fill:${fill(k)}` }));
        if (w > 22) { const t = svgEl('text', { x: x(x0) + 8, y: y + 14, dy: '0.32em', style: `fill:${k === 'unexplained' ? 'var(--ink)' : 'var(--paper)'};font-family:var(--mono)` }); t.textContent = r.count; svg.append(t); }
        x0 += r.count;
      }
    });
    // Legend under the bars
    let lx = left; const ly = top + ms.length * rowH + 10;
    for (const k of kinds) {
      svg.append(svgEl('rect', { x: lx, y: ly, width: 10, height: 10, rx: 2, style: `fill:${fill(k)}` }));
      const t = svgEl('text', { x: lx + 16, y: ly + 5, dy: '0.32em' }); t.textContent = k === 'combined senior phase-out' ? 'Senior deduction misread' : k[0].toUpperCase() + k.slice(1); svg.append(t);
      lx += 16 + t.getComputedTextLength() + 20;
    }
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

  const draw = () => { ruleChart(); mistakeChart(); };
  draw();
  // The browser jumped to a #section before the data filled in and moved it; jump again now that layout is final.
  if (location.hash) document.getElementById(location.hash.slice(1))?.scrollIntoView();
  let raf; addEventListener('resize', () => { cancelAnimationFrame(raf); raf = requestAnimationFrame(draw); });
})();
