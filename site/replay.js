// Fills replay.html from data/replays.json, which src/replay_site.py writes from graded Gauntlet runs.
(async () => {
  const data = await fetch('data/replays.json').then((r) => (r.ok ? r.json() : null)).catch(() => null);
  const view = document.getElementById('rp-view');
  const qSel = document.getElementById('rp-question');
  const mSel = document.getElementById('rp-model');
  if (!data?.replays?.length) { view.innerHTML = '<p class="rp-empty">No replays yet.</p>'; return; }
  const all = data.replays;
  const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const usd = (x) => (x < 0 ? '−' : '') + '$' + Math.abs(Math.round(x)).toLocaleString('en-US');
  const label = (r) => `${r.what}${r.ask_first ? ' · ask first' : ''} (${r.id.replace(/^g-/, '')})`;
  const key = (r) => `${r.id}|${r.ask_first}`;
  const mkey = (r) => `${r.model}|${r.engine}`;

  const questions = [...new Map(all.map((r) => [key(r), r])).values()];
  qSel.innerHTML = questions.map((r) => `<option value="${esc(key(r))}">${esc(label(r))}</option>`).join('');
  const fromHash = decodeURIComponent(location.hash.slice(1));
  if (questions.some((r) => key(r) === fromHash.split('~')[0])) qSel.value = fromHash.split('~')[0];

  function models() {
    const rs = all.filter((r) => key(r) === qSel.value);
    const keep = mSel.value;
    mSel.innerHTML = rs.map((r) => `<option value="${esc(mkey(r))}">${esc(r.model_name)} ${r.engine ? 'with the engine' : 'alone'}</option>`).join('');
    const want = fromHash.split('~')[1];
    if (rs.some((r) => mkey(r) === keep)) mSel.value = keep;
    else if (want && rs.some((r) => mkey(r) === want)) mSel.value = want;
    else if (rs.some((r) => r.engine)) mSel.value = mkey(rs.find((r) => r.engine));
  }

  function verdict(ok, yes, no) { return `<span class="rp-badge ${ok ? 'ok' : 'bad'}">${ok ? yes : no}</span>`; }

  function step(s, i) {
    if (s.kind === 'ask') {
      return `<li class="rp-step ask"><span class="rp-n">${i + 1}</span><div>
        <p class="rp-who">Asked the client</p><p class="rp-said">“${esc(s.q)}”</p>
        <p class="rp-who">The client</p><p class="rp-said">${esc(s.a)} ${s.revealed ? '<span class="rp-badge ok">got the missing fact</span>' : ''}</p></div></li>`;
    }
    return `<li class="rp-step${s.error ? ' err' : ''}"><span class="rp-n">${i + 1}</span><div>
      <p class="rp-who">Asked the engine · <code>${esc(s.name)}</code></p><p class="rp-said">${esc(s.asked)}</p>
      <p class="rp-who">${s.error ? 'The engine refused the call' : 'The engine answered'}</p><pre class="rp-got">${esc(s.got)}</pre></div></li>`;
  }

  function answerTable(r) {
    const rows = Object.entries(r.numbers).map(([k, x], i) => `<tr><td>${esc(r.asks[i] ?? k)}</td>
      <td class="num">${x.got == null ? '—' : usd(x.got)}</td><td class="num">${usd(x.key)}</td><td>${x.right ? '✓' : '✗'}</td></tr>`).join('');
    const pick = r.answer.find((l) => /^\W*(PICK|PLAN)/i.test(l)) ?? '—';
    return `<div class="table-wrap"><table class="rp-table"><thead><tr><th></th><th class="num">Said</th><th class="num">Key</th><th></th></tr></thead><tbody>
      <tr><td>The decision</td><td class="num">${esc(pick.replace(/^\W*(PICK|PLAN):\s*/i, ''))}</td><td class="num">${esc(r.key[0].replace(/^(PICK|PLAN):\s*/, ''))}</td><td>${r.decision_right ? '✓' : '✗'}</td></tr>
      ${rows}</tbody></table></div>`;
  }

  function render() {
    const r = all.find((x) => key(x) === qSel.value && mkey(x) === mSel.value);
    if (!r) return;
    history.replaceState(null, '', '#' + encodeURIComponent(`${key(r)}~${mkey(r)}`));
    const opts = (r.options ?? []).map((o) => `<li><b>${esc(o.letter)}.</b> ${esc(o.text)}</li>`).join('');
    const calls = r.steps.filter((s) => s.kind === 'tool');
    const alone = r.alone ? `<div class="rp-card rp-alone"><p class="label">The same model alone${r.ask_first ? ', same missing fact' : ''}</p>
      <p>${verdict(r.alone.great, 'Fully right', 'Not fully right')} ${r.alone.great ? '' : r.alone.lost ? `Its pick costs the household <b>${usd(r.alone.lost)}</b>.` : esc(r.alone.why ?? '')}</p>
      <pre class="rp-got">${esc(r.alone.answer.join('\n') || '(no answer lines)')}</pre></div>` : '';
    view.innerHTML = `
      <div class="rp-card"><p class="label">The question</p><h2 class="rp-h">${esc(r.what)}</h2>
        ${opts ? `<ul class="rp-opts">${opts}</ul>` : ''}
        ${r.withheld ? `<p class="rp-withheld">Left out of the notes on purpose: <b>${esc(r.withheld)}</b>. The model has to ask for it.</p>` : ''}</div>
      <div class="rp-card"><p class="label">${esc(r.model_name)} ${r.engine ? 'with the engine' : 'alone'}: ${calls.length} engine call${calls.length === 1 ? '' : 's'}${r.cost ? ` · cost ${r.cost < 0.01 ? 'under 1¢' : r.cost < 1 ? Math.round(r.cost * 100) + '¢' : '$' + r.cost.toFixed(2)}` : ''}</p>
        ${r.steps.length ? `<ol class="rp-steps">${r.steps.map(step).join('')}</ol>` : '<p>It answered without calling the engine.</p>'}</div>
      <div class="rp-split">
        <div class="rp-card"><p class="label">Its final answer</p><p>${verdict(r.great, 'Fully right', 'Not fully right')}</p>${answerTable(r)}</div>
        ${alone}
      </div>`;
  }

  qSel.addEventListener('change', () => { models(); render(); });
  mSel.addEventListener('change', render);
  models();
  render();
})();
