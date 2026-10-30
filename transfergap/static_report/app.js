const $ = id => document.getElementById(id);
const pct = value => `${(100 * value).toFixed(1)}%`;
const pp = value => `${value >= 0 ? '+' : ''}${value.toFixed(1)} pp`;
const range = values => `[${values.map(x => x.toFixed(1)).join(', ')}] pp`;
const kOfN = row => `${row.successes}/${row.n}`;
const link = (name, label) => `<a href="../results/${name}/summary.md">${label} report ↗</a>`;

function armCard(name, row) {
  const before = row.heldout.full;
  const after = row.heldout[`full+${row.correction}`];
  const gain = row.paired_gain;
  const budget = Object.entries(row.budget).map(([stage, item]) => `
    <div class="bar-row"><span>${stage}</span><div class="track"><div class="fill" style="--width:${Math.max(0, Math.min(100, item.delta_pp + 20))}%"></div></div><strong>${pp(item.delta_pp)}</strong></div>`).join('');
  return `<article class="result-card"><div class="card-top"><div class="card-label">${name.toUpperCase()} + Robotiq 2F-85</div><span class="tag">HELD-OUT · n=60</span></div>
    <div class="big-number positive">${pp(gain.delta_pp)}</div><p class="metric-caption">paired correction gain · 95% CI ${range(gain.ci95_pp)}</p>
    <div class="comparison"><div><b>${pct(before.success_rate)}</b><span>Before · ${kOfN(before)}</span></div><div><b>${pct(after.success_rate)}</b><span>After look-again · ${kOfN(after)}</span></div></div>
    <div class="card-label">Development recovery by oracle stage</div>${budget}
    <div class="meta">Development seeds 0–59 · held-out 1000–1059 · source commit ${row.code_commit}</div></article>`;
}

function g1Condition(name, row) {
  const label = name === 'nominal_target' ? 'Nominal target' : 'True target oracle';
  const tier = ([title, rate]) => `<div class="tier"><b>${rate.k}/${rate.n}</b><span>${title} · ${pct(rate.rate)}</span></div>`;
  return `<div><div class="card-label">${label}</div><h3>${row.place.k}/${row.place.n} placed</h3>
    <div class="tier-list">${tier(['Touch', row.touch])}${tier(['Grasp', row.grasp])}${tier(['Place', row.place])}</div>
    <div class="tier-note">${row.place_seed_any.k}/${row.place_seed_any.n} seeds had at least one place; ${row.mixed_place_seeds} seeds had mixed repeat outcomes.</div></div>`;
}

function cosmosCard(version, row) {
  const s = row.success;
  const st = row.stage;
  const controls = row.static_controls ? `<p class="tier-note">Static controls: ${row.static_controls.said_success}/${row.static_controls.n} falsely marked successful.</p>` : '';
  return `<article class="result-card"><div class="card-top"><div class="card-label">COSMOS ${version.toUpperCase()}</div><span class="tag">${st.accuracy.n} CLIPS</span></div>
    <div class="big-number">${pct(s.accuracy.accuracy)}</div><p class="metric-caption">success detection · ${s.accuracy.correct}/${s.accuracy.n} correct · majority baseline ${pct(s.majority_baseline.accuracy)}</p>
    <div class="comparison"><div><b>${pct(st.accuracy.accuracy)}</b><span>Stage accuracy · ${st.accuracy.correct}/${st.accuracy.n}</span></div><div><b>${pct(st.majority_baseline.accuracy)}</b><span>Stage majority baseline</span></div></div>
    ${controls}<div class="meta">Camera: ${row.camera} · ${row.seeds} · source commit ${row.run_commit}</div></article>`;
}

fetch('data.json').then(response => { if (!response.ok) throw new Error('Could not load recorded data'); return response.json(); }).then(data => {
  $('arm-cards').innerHTML = Object.entries(data.arms).map(([name, row]) => armCard(name, row)).join('');
  $('g1-content').innerHTML = `<div class="tier-grid">${Object.entries(data.g1.conditions).map(([name, row]) => g1Condition(name, row)).join('')}</div>`;
  $('cosmos-cards').innerHTML = Object.entries(data.cosmos).map(([name, row]) => cosmosCard(name, row)).join('');
  $('arm-links').innerHTML = Object.entries(data.arms).map(([name, row]) => link(row.source, name.toUpperCase())).join('');
}).catch(error => { $('arm-cards').textContent = error.message; $('g1-content').textContent = 'Recorded data unavailable.'; $('cosmos-cards').textContent = 'Recorded data unavailable.'; });
