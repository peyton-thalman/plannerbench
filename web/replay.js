// Fills replay.html from data/replays.json, which src/replay_site.py writes from graded Gauntlet runs.
(async () => {
  const data = await fetch('data/replays.json', { cache: 'no-cache' }).then((r) => (r.ok ? r.json() : null)).catch(() => null);
  const view = document.getElementById('rp-view');
  const qSel = document.getElementById('rp-question');
  const mSel = document.getElementById('rp-model');
  if (!data?.replays?.length) { view.innerHTML = '<p class="rp-empty">No replays yet.</p>'; return; }
  const all = data.replays;
  const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const usd = (x) => (x < 0 ? '−' : '') + '$' + Math.abs(Math.round(x)).toLocaleString('en-US');
  // Plain names for the selector and the heading; the question's own short title (r.what) uses planner shorthand.
  const PLAIN = { claim_age: 'Waiting to 70 for Social Security, and converting to a Roth before then',
    first_rmd: 'A Roth conversion in the first year IRA withdrawals are required',
    gains_vs_conversion: 'Selling investments at a 0% tax rate, or converting to a Roth',
    how_much: 'How much to convert to a Roth, and for how many years',
    inherited_ira: 'Emptying an inherited IRA within 10 years',
    muni_stack: 'A Roth conversion when tax-free bond interest still raises Medicare premiums',
    qcd_giving: 'Giving to charity by check, or straight from an IRA',
    senior_phaseout: 'A Roth conversion while the new tax break for people over 65 phases out',
    torpedo_irmaa: 'A Roth conversion that makes more Social Security taxable and raises Medicare premiums later',
    trap: 'A trap: a question the facts can’t settle',
    widow: 'A Roth conversion before or after a spouse dies' };
  const plain = (r) => PLAIN[Object.keys(PLAIN).find((k) => r.id.replace(/^g-/, '').startsWith(k))] ?? r.what;
  const label = (r) => `${plain(r)}${r.ask_first ? ' · one fact left out' : ''}`;
  const key = (r) => `${r.id}|${r.ask_first}`;
  const mkey = (r) => `${r.model}|${r.engine}`;
  const cents = (c) => (c < 0.01 ? 'under 1¢' : c < 1 ? `${Math.round(c * 100)}¢` : `$${c.toFixed(2)}`);

  const questions = [...new Map(all.map((r) => [key(r), r])).values()];
  qSel.innerHTML = questions.map((r) => `<option value="${esc(key(r))}">${esc(label(r))}</option>`).join('');
  // With no link to a replay, open on the example from With a calculator: DeepSeek V4.1 Flash sizing a Roth conversion,
  // which it got wrong on its own and right with the calculator (and the baked page shows this one).
  const start = all.find((r) => r.id === 'g-how_much-1' && !r.ask_first && r.engine && r.model.includes('deepseek'));
  const fromHash = decodeURIComponent(location.hash.slice(1)) || (start ? `${key(start)}~${mkey(start)}` : '');
  if (questions.some((r) => key(r) === fromHash.split('~')[0])) qSel.value = fromHash.split('~')[0];

  function models() {
    const rs = all.filter((r) => key(r) === qSel.value);
    const keep = mSel.value;
    mSel.innerHTML = rs.map((r) => `<option value="${esc(mkey(r))}">${esc(r.model_name)} ${r.engine ? 'with the calculator' : 'on its own'}</option>`).join('');
    const want = fromHash.split('~')[1];
    if (rs.some((r) => mkey(r) === keep)) mSel.value = keep;
    else if (want && rs.some((r) => mkey(r) === want)) mSel.value = want;
    else if (rs.some((r) => r.engine)) mSel.value = mkey(rs.find((r) => r.engine));
  }

  // "PICK: B" / "PLAN: 118000 x 8" / "PICK: CANT" in plain words
  const decision = (line) => {
    const v = String(line ?? '').replace(/^\W*(PICK|PLAN)\W*:\s*/i, '').replace(/\*/g, '').trim();
    if (!v) return '—';
    if (/^CANT/i.test(v)) return 'Can’t answer';
    if (/^CLOSE/i.test(v)) return `Close call: ${v.replace(/^CLOSE\s*/i, '').split(',').join(' or ')}`;
    const m = v.match(/([\d,]+)\s*x\s*(\d+)/i);
    if (m) return Number(m[1].replace(/,/g, '')) === 0 || m[2] === '0' ? 'Convert nothing' : `${usd(Number(m[1].replace(/,/g, '')))} a year × ${m[2]} years`;
    return /^[A-Z]$/.test(v) ? `Option ${v}` : v;
  };
  const pickOf = (lines) => (lines ?? []).find((l) => /^\W*(PICK|PLAN)/i.test(l));
  const cell = (text, ok, col) => `<td data-label="${esc(col)}" class="${ok == null ? '' : ok ? 'ok' : 'bad'}">${ok == null ? '' : `<span class="rp-mark" aria-label="${ok ? 'right' : 'wrong'}">${ok ? '✓' : '✗'}</span>`}${esc(text)}</td>`;

  function answers(r) {
    const a = r.alone;
    const run = r.engine ? 'With the calculator' : 'This run';
    const head = `<tr class="rp-head"><th scope="col"></th><th scope="col">Right answer</th><th scope="col">${run}</th>${a ? '<th scope="col">On its own</th>' : ''}</tr>`;
    const rows = [`<tr><th scope="row">The decision</th>${cell(decision(r.key[0]), null, 'Right answer')}${cell(decision(pickOf(r.answer)), r.decision_right, run)}${a ? cell(decision(pickOf(a.answer)), a.decision_right, 'On its own') : ''}</tr>`];
    Object.entries(r.numbers).forEach(([k, x], i) => {
      const ax = a?.numbers?.[k];
      rows.push(`<tr><th scope="row">${esc(r.asks[i] ?? k)}</th>${cell(usd(x.key), null, 'Right answer')}${cell(x.got == null ? '—' : usd(x.got), x.right, run)}${a ? cell(ax?.got == null ? '—' : usd(ax.got), ax?.right, 'On its own') : ''}</tr>`);
    });
    return `<table class="rp-answers" style="--cols:${a ? 3 : 2}">${head}${rows.join('')}</table>`;
  }

  function verdict(name, great, text) {
    return `<div class="rp-verdict ${great ? 'ok' : 'bad'}"><span class="rp-badge ${great ? 'ok' : 'bad'}">${great ? 'Fully right' : 'Not fully right'}</span>`
      + `<p><b>${esc(name)}.</b> ${esc(text)}</p></div>`;
  }

  const kv = (rows) => `<dl class="rp-kv">${rows.map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join('')}</dl>`;

  function said(s) {
    if (s.error) return `<p class="rp-err">${esc(s.error)}</p>${s.note ? `<p class="rp-note">${esc(s.note)}</p>` : ''}`;
    let h = '';
    if (s.headline) h += `<p class="rp-headline">${esc(s.headline)}</p>`;
    if (s.options) {
      h += `<table class="rp-options"><tbody>${s.options.map((o, i) => `<tr class="${i === 0 ? 'best' : ''}"><td>${esc(o.name)}${i === 0 ? ' <span class="rp-badge ok">best</span>' : ''}</td>`
        + `<td class="num">${usd(o.wealth)}</td><td class="num muted">${i === 0 ? '' : usd(o.behind)}</td></tr>`).join('')}</tbody></table>`;
    }
    if (s.facts) h += kv(s.facts);
    if (s.note) h += `<p class="rp-note">${esc(s.note)}</p>`;
    return h;
  }

  function step(s, i) {
    if (s.kind === 'ask') {
      return `<li class="rp-step ask"><span class="rp-n">${i + 1}</span><div class="rp-body">
        <h3 class="rp-title">Asked the client</h3>
        <p class="rp-bubble me">${esc(s.q)}</p>
        <p class="rp-bubble them">${esc(s.a)}</p>
        ${s.revealed ? '<p><span class="rp-badge ok">Got the missing fact</span></p>' : ''}</div></li>`;
    }
    const raw = `<details class="rp-raw"><summary>Show the raw call</summary><p class="rp-who">Sent</p><pre>${esc(s.raw_in)}</pre>`
      + `${s.raw_out ? `<p class="rp-who">Received</p><pre>${esc(s.raw_out)}</pre>` : ''}</details>`;
    return `<li class="rp-step${s.error ? ' err' : ''}"><span class="rp-n">${i + 1}</span><div class="rp-body">
      <h3 class="rp-title">${esc(s.title)} <code>${esc(s.tool)}</code></h3>
      <div class="rp-io">
        ${s.sent ? `<div><p class="rp-who">What it sent</p>${kv(s.sent)}</div>` : ''}
        <div><p class="rp-who">${s.error ? 'The calculator sent it back' : 'What the calculator said'}</p>${said(s)}</div>
      </div>
      ${s.hint ? `<p class="rp-hint">The calculator also suggested asking: “${esc(s.hint)}”</p>` : ''}
      ${raw}</div></li>`;
  }

  // The facts are the question exactly as the model read it; these one-line glosses help a reader without the jargon.
  const GLOSS = [[/\bPIA\b/, 'PIA: the monthly Social Security benefit at full retirement age.'],
    [/IRMAA/, 'MAGI and IRMAA: Medicare sets premiums from income two years earlier (MAGI); higher income adds a surcharge (IRMAA).'],
    [/8606/, 'After-tax basis (Form 8606): money already taxed, so it isn’t taxed again when it comes out.'],
    [/\bRMD/, 'RMD: the withdrawal the IRS requires from a traditional IRA each year from a set age.'],
    [/\bmuni/i, 'Muni interest: interest from state or city bonds; free of federal tax, but it still counts in the income Medicare uses for premiums.'],
    [/\bQCD/, 'QCD (qualified charitable distribution): a gift to charity straight from an IRA; it counts toward the required withdrawal and isn’t taxed.']];
  const gloss = (facts) => { const t = facts.join(' '), hits = GLOSS.filter(([re]) => re.test(t)).map(([, g]) => g); return hits.length ? `<p class="rp-gloss">${hits.map(esc).join(' ')}</p>` : ''; };

  function render() {
    const r = all.find((x) => key(x) === qSel.value && mkey(x) === mSel.value);
    if (!r) return;
    history.replaceState(null, '', '#' + encodeURIComponent(`${key(r)}~${mkey(r)}`));
    // Mark the chosen options in the markup too, so the baked page (no JavaScript) names the replay it shows.
    for (const sel of [qSel, mSel]) for (const o of sel.options) o.toggleAttribute('selected', o.value === sel.value);
    const opts = (r.options ?? []).map((o) => `<li><b>${esc(o.letter)}.</b> ${esc(o.text)}</li>`).join('');
    const calls = r.steps.filter((s) => s.kind === 'tool').length;
    const asks = r.steps.length - calls;
    const who = `${r.model_name} ${r.engine ? 'with the calculator' : 'on its own'}`;
    // The household first, in the question's own sentences, so the replay reads without opening any JSON.
    const hh = r.household ?? { intro: '', facts: [] };
    const asked = (r.asks ?? []).map((q) => `<li>${esc(q)}</li>`).join('');
    view.innerHTML = `
      <section class="rp-card"><p class="label">The household</p><h2 class="rp-h">${esc(plain(r))}</h2>
        ${hh.intro ? `<p class="rp-intro">${esc(hh.intro)}</p>` : ''}
        ${hh.facts.length ? `<p class="rp-who">What the model was told</p><ul class="rp-facts">${hh.facts.map((f) => `<li>${esc(f)}</li>`).join('')}</ul>` : ''}
        ${gloss(hh.facts)}
        ${r.withheld ? `<p class="rp-withheld">Left out of these notes on purpose: <b>${esc(r.withheld)}</b>. The model has to ask the client for it.</p>` : ''}</section>

      <section class="rp-card"><p class="label">The choice</p>
        ${String(r.id).startsWith('g-how_much')
          ? `<p class="rp-sub">Find the best plan: the same amount converted every year, for 1 to 10 years starting in 2026, any amount. “Best” means the most after-tax wealth; if no conversion is best, say 0. The two plans below aren’t the choices; they are only there to price the other numbers it had to give.</p>${opts ? `<ul class="rp-opts">${opts}</ul>` : ''}`
          : opts ? `<ul class="rp-opts">${opts}</ul>` : '<p class="rp-sub">How much to convert, and for how many years.</p>'}
        ${asked ? `<p class="rp-who">It also had to give these numbers</p><ol class="rp-asked">${asked}</ol>` : ''}</section>

      <section class="rp-card"><p class="label">How it did</p>
        <div class="rp-verdicts">${verdict(who, r.great, r.outcome)}${r.alone ? verdict(`${r.model_name} on its own`, r.alone.great, r.alone.outcome) : ''}</div>
        ${answers(r)}</section>

      <section class="rp-card"><p class="label">How it got there</p>
        <p class="rp-sub">${r.steps.length ? `${calls} call${calls === 1 ? '' : 's'} to the calculator${asks ? ` and ${asks} question${asks === 1 ? '' : 's'} to the client` : ''}, in order.` : 'It answered without calling the calculator.'}${r.cost ? ` Cost ${cents(r.cost)}.` : ''}</p>
        ${r.steps.length ? `<ol class="rp-steps">${r.steps.map(step).join('')}</ol>` : ''}</section>`;
  }

  qSel.addEventListener('change', () => { models(); render(); });
  mSel.addEventListener('change', render);
  models();
  render();
})();
