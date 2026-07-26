const money = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });
const num = new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 });
let logChart;
let movingAverageChart;
let dashboardIndex;
let activeAssetId;
let activeData;
let macroData;

function zoneClass(zone) {
  return String(zone).toLowerCase().replace(/\s+/g, '-');
}

function series(points, key) {
  return points.filter((p) => p[key] !== null && p[key] !== undefined).map((p) => ({ time: p.date, value: Number(p[key]) }));
}

function escapeHtml(value) {
  return String(value ?? '').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#039;');
}

function fmtMoney(value) {
  return value === null || value === undefined ? 'n/a' : money.format(value);
}

function fmtNum(value) {
  return value === null || value === undefined ? 'n/a' : num.format(value);
}

function fmtRatio(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n.toFixed(6) : 'n/a';
}

function isPositiveFinite(value) {
  const n = Number(value);
  return Number.isFinite(n) && n > 0;
}

function card(label, value, detail, cls = '') {
  return `<article class="status-card ${cls}"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong><small>${detail ?? ''}</small></article>`;
}

function sparkline(points, color = '#38bdf8') {
  const clean = (points ?? []).map((p) => Number(p.value)).filter(Number.isFinite);
  if (clean.length < 2) return '<div class="sparkline-empty">Snapshot only</div>';
  const width = 280;
  const height = 64;
  const min = Math.min(...clean);
  const max = Math.max(...clean);
  const range = Math.max(max - min, 1e-9);
  const path = clean.map((value, i) => {
    const x = (i / Math.max(clean.length - 1, 1)) * width;
    const y = height - 4 - ((value - min) / range) * (height - 8);
    return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  return `<svg class="sparkline" viewBox="0 0 ${width} ${height}" aria-hidden="true"><path d="${path}" stroke="${color}" /></svg>`;
}

function renderMacroCycle(data) {
  const panel = document.querySelector('#macroCyclePanel');
  if (!data || activeAssetId !== 'btc') {
    panel.hidden = true;
    return;
  }
  panel.hidden = false;
  const framework = data.framework;
  const indicators = data.indicators;
  document.querySelector('#macroCycleSummary').textContent = framework.summary;
  document.querySelector('#macroCycleCount').textContent = `${framework.fired_count} of 4 fired`;
  document.querySelector('#dominoSequence').innerHTML = framework.sequence.map((item, index) => `
    <article class="domino ${escapeHtml(item.status).replaceAll(' ', '-')}">
      <div class="domino-number">${escapeHtml(item.number)}</div>
      <div><span>${escapeHtml(item.status)}</span><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.detail)}</small></div>
      ${index < framework.sequence.length - 1 ? '<b class="domino-arrow">→</b>' : ''}
    </article>
  `).join('');
  const pmi = indicators.ism_pmi;
  const copper = indicators.copper_gold;
  const realized = indicators.btc_realized_volatility;
  const implied = indicators.btc_implied_volatility;
  document.querySelector('#macroIndicators').innerHTML = `
    <article class="macro-card"><span>ISM Manufacturing PMI</span><strong>${fmtNum(pmi.value)}</strong><small>${escapeHtml(pmi.date)} · ${escapeHtml(pmi.status)} · 50 threshold</small><div class="threshold-bar"><i style="width:${Math.min(100, Number(pmi.value))}%"></i><b style="left:50%"></b></div><em>Manual, video-sourced snapshot</em></article>
    <article class="macro-card"><span>Copper / Gold</span><strong>${fmtRatio(copper.value)}</strong><small>${fmtNum(copper.distance_above_3y_trend_pct)}% vs 3Y trend · ${escapeHtml(copper.status)}</small>${sparkline(copper.series, '#f59e0b')}<em>${escapeHtml(copper.method)}</em></article>
    <article class="macro-card"><span>BTC 90D Realized Vol</span><strong>${fmtNum(realized.value)}%</strong><small>Historical percentile ${fmtNum(realized.historical_percentile)} · ${escapeHtml(realized.status)}</small>${sparkline(realized.series, '#a78bfa')}<em>${escapeHtml(realized.method)}</em></article>
    <article class="macro-card"><span>BTC Implied Volatility</span><strong>${fmtNum(implied.value)}%</strong><small>Deribit DVOL · ${escapeHtml(implied.status)}</small><div class="vol-gauge"><i style="width:${Math.min(100, Number(implied.value))}%"></i></div><em>Options market expectation; complements realized volatility.</em></article>
  `;
  const oil = indicators.oil;
  document.querySelector('#macroRisk').innerHTML = `<div><span>Setup invalidation watch</span><strong>WTI ${fmtMoney(oil.value)} · ${escapeHtml(oil.status)}</strong><small>${fmtNum(oil.change_20d_pct)}% over 20 sessions. Persistent oil strength can revive inflation and tighten policy.</small></div>${sparkline(oil.series, oil.status === 'contained' ? '#22c55e' : '#f87171')}`;
  const pmiLimitation = data.sources?.pmi?.limitation ?? 'PMI is an explicit manual snapshot.';
  const errors = (data.refresh_errors ?? []).length ? `<p><strong>Refresh warnings:</strong> ${escapeHtml(data.refresh_errors.join(' | '))}</p>` : '';
  document.querySelector('#macroSources').innerHTML = `<p>${escapeHtml(framework.warning)}</p><p><strong>PMI:</strong> ${escapeHtml(pmiLimitation)}</p><p><strong>Copper, gold, oil:</strong> Yahoo Finance futures proxies. <strong>Implied volatility:</strong> Deribit DVOL public API. <strong>Realized volatility:</strong> local BTC daily history.</p>${errors}<p><a href="${escapeHtml(framework.source_video)}" target="_blank" rel="noreferrer">Source video</a></p>`;
}

function renderAssetButtons(index) {
  document.querySelector('#globalAsOf').textContent = `Updated ${new Date(index.generated_at).toLocaleString()}`;
  document.querySelector('#assetButtons').innerHTML = index.assets.map((asset) => `
    <button class="asset-button" type="button" data-asset-id="${escapeHtml(asset.id)}">
      <strong>${escapeHtml(asset.symbol)}</strong>
      <span>${escapeHtml(asset.name)}</span>
      <small>${fmtMoney(asset.latest.close)} · ${escapeHtml(asset.latest.zone)}</small>
    </button>
  `).join('');
  document.querySelectorAll('[data-asset-id]').forEach((button) => {
    button.addEventListener('click', () => selectAsset(button.dataset.assetId));
  });
  document.querySelector('#assetOverview').innerHTML = index.assets.map((asset) => `
    <article>
      <span>${escapeHtml(asset.name)}</span>
      <strong>${fmtMoney(asset.latest.close)}</strong>
      <small>${escapeHtml(asset.regime.label)} · ${escapeHtml(asset.latest.date)}</small>
    </article>
  `).join('');
}

function markActiveAsset() {
  document.querySelectorAll('[data-asset-id]').forEach((button) => button.classList.toggle('active', button.dataset.assetId === activeAssetId));
}

async function selectAsset(assetId) {
  activeAssetId = assetId;
  markActiveAsset();
  const asset = dashboardIndex.assets.find((a) => a.id === assetId);
  if (!asset) throw new Error(`Unknown asset ${assetId}`);
  const res = await fetch(asset.url, { cache: 'no-store' });
  if (!res.ok) throw new Error(`Data fetch failed for ${assetId}: ${res.status}`);
  activeData = await res.json();
  renderAll(activeData);
}

function renderStatus(data) {
  const l = data.latest;
  const zClass = zoneClass(l.zone);
  const source = data.source?.source ?? 'market feed';
  document.querySelector('#status').innerHTML = [
    card(data.asset.price_label, fmtMoney(l.close), `Source: ${escapeHtml(source)}`),
    card('Trend Fair Value', fmtMoney(l.trend), escapeHtml(data.source?.provenance ?? 'Long-term log regression')),
    card('Log Z-Score', fmtNum(l.z_score), 'Residual ÷ standard deviation', zClass),
    card('MVRV', l.latest_available_mvrv ? fmtNum(l.latest_available_mvrv) : 'n/a', l.latest_available_mvrv_date ? `Latest available: ${escapeHtml(l.latest_available_mvrv_date)}` : 'BTC-only on-chain metric'),
    card('Current Zone', l.zone, escapeHtml(l.zone_note), zClass),
    card('Regime', data.regime.label, `Score: ${data.regime.score}`, data.regime.score >= 2 ? 'constructive' : ''),
  ].join('');
  document.querySelector('#asOf').textContent = `As of ${l.date}`;
  document.querySelector('#chartTitle').textContent = `${data.asset.name} Cycle Charts`;
  document.querySelector('#chartSubtitle').textContent = `${data.asset.symbol} · log channel, moving averages, rainbow, and Elliott scenario lab`;
}

function renderLogChart(data) {
  const chartEl = document.querySelector('#logChart');
  if (logChart) logChart.remove();
  logChart = LightweightCharts.createChart(chartEl, {
    height: 620,
    layout: { background: { color: '#08111f' }, textColor: '#d7e2f2' },
    grid: { vertLines: { color: 'rgba(148, 163, 184, 0.15)' }, horzLines: { color: 'rgba(148, 163, 184, 0.15)' } },
    rightPriceScale: { mode: LightweightCharts.PriceScaleMode.Logarithmic, borderColor: 'rgba(148, 163, 184, 0.3)' },
    timeScale: { borderColor: 'rgba(148, 163, 184, 0.3)' },
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
  });
  const price = logChart.addLineSeries({ color: '#f8fafc', lineWidth: 2, title: `${data.asset.symbol} price` });
  const trend = logChart.addLineSeries({ color: '#38bdf8', lineWidth: 2, title: 'Trend' });
  const minus15 = logChart.addLineSeries({ color: '#22c55e', lineWidth: 2, title: '-1.5σ accumulation' });
  const minus2 = logChart.addLineSeries({ color: '#0ea5e9', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dashed, title: '-2σ deep value' });
  const plus2 = logChart.addLineSeries({ color: '#ef4444', lineWidth: 2, title: '+2σ take chips' });
  const plus1 = logChart.addLineSeries({ color: 'rgba(248, 113, 113, 0.55)', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dotted, title: '+1σ' });
  const minus1 = logChart.addLineSeries({ color: 'rgba(74, 222, 128, 0.55)', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dotted, title: '-1σ' });
  price.setData(series(data.points, 'close'));
  trend.setData(series(data.points, 'trend'));
  minus15.setData(series(data.points, 'band_minus_1_5'));
  minus2.setData(series(data.points, 'band_minus_2'));
  plus2.setData(series(data.points, 'band_plus_2'));
  plus1.setData(series(data.points, 'band_plus_1'));
  minus1.setData(series(data.points, 'band_minus_1'));
  logChart.timeScale().fitContent();
  logChart.applyOptions({ width: chartEl.clientWidth });
}

function renderMovingAverageChart(data) {
  const chartEl = document.querySelector('#movingAverageChart');
  const note = document.querySelector('#movingAverageNote');
  if (movingAverageChart) movingAverageChart.remove();
  movingAverageChart = LightweightCharts.createChart(chartEl, {
    height: 620,
    layout: { background: { color: '#08111f' }, textColor: '#d7e2f2' },
    grid: { vertLines: { color: 'rgba(148, 163, 184, 0.15)' }, horzLines: { color: 'rgba(148, 163, 184, 0.15)' } },
    rightPriceScale: { mode: LightweightCharts.PriceScaleMode.Logarithmic, borderColor: 'rgba(148, 163, 184, 0.3)' },
    timeScale: { borderColor: 'rgba(148, 163, 184, 0.3)' },
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
  });
  const price = movingAverageChart.addLineSeries({ color: '#f8fafc', lineWidth: 3, title: `${data.asset.symbol} price` });
  const ma50 = movingAverageChart.addLineSeries({ color: '#22d3ee', lineWidth: 2, title: '50D MA' });
  const ma100 = movingAverageChart.addLineSeries({ color: '#f59e0b', lineWidth: 2, title: '100D MA' });
  const ma200 = movingAverageChart.addLineSeries({ color: '#f472b6', lineWidth: 2, title: '200D MA' });
  const ma200w = movingAverageChart.addLineSeries({
    color: '#4ade80',
    lineWidth: 3,
    lineStyle: LightweightCharts.LineStyle.Dashed,
    title: '200W MA',
  });
  const ma200wData = series(data.points, 'ma_200w');
  price.setData(series(data.points, 'close'));
  ma50.setData(series(data.points, 'ma_50d'));
  ma100.setData(series(data.points, 'ma_100d'));
  ma200.setData(series(data.points, 'ma_200d'));
  ma200w.setData(ma200wData);
  note.hidden = ma200wData.length > 0;
  note.textContent = ma200wData.length > 0 ? '' : `${data.asset.name} does not yet have enough price history to calculate a 200W moving average.`;
  movingAverageChart.timeScale().fitContent();
  movingAverageChart.applyOptions({ width: chartEl.clientWidth });
}

function renderRainbowChart(data) {
  const target = document.querySelector('#rainbowChart');
  const summary = document.querySelector('#rainbowSummary');
  const rainbow = data.rainbow;
  const levelKeys = Array.from({ length: rainbow.bands.length + 1 }, (_, i) => `level_${i}`);
  const points = rainbow.points.filter((p) => ['close', 'trend', ...levelKeys].every((key) => isPositiveFinite(p[key])));
  if (points.length < 2) {
    target.innerHTML = `<div class="error"><strong>Rainbow chart unavailable</strong><p>Not enough positive finite band data for ${escapeHtml(data.asset.name)}.</p></div>`;
    summary.innerHTML = '';
    return;
  }
  const width = 1200;
  const height = 620;
  const pad = { top: 28, right: 112, bottom: 54, left: 78 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  const firstTime = Date.parse(points[0].date);
  const lastTime = Date.parse(points[points.length - 1].date);
  const values = [];
  for (const p of points) {
    values.push(p.close);
    for (const key of levelKeys) values.push(p[key]);
  }
  const finiteValues = values.map(Number).filter((v) => Number.isFinite(v) && v > 0);
  let minValue = Infinity;
  let maxValue = 0;
  for (const value of finiteValues) {
    if (value < minValue) minValue = value;
    if (value > maxValue) maxValue = value;
  }
  const minLog = Math.log(minValue * 0.82);
  const maxLog = Math.log(maxValue * 1.18);
  const x = (date) => pad.left + ((Date.parse(date) - firstTime) / Math.max(lastTime - firstTime, 1)) * plotW;
  const y = (value) => pad.top + (1 - ((Math.log(value) - minLog) / (maxLog - minLog))) * plotH;
  const pathFor = (key) => points.map((p, i) => `${i === 0 ? 'M' : 'L'}${x(p.date).toFixed(2)},${y(p[key]).toFixed(2)}`).join(' ');
  const bandPolygon = (lowerKey, upperKey) => {
    const top = points.map((p) => `${x(p.date).toFixed(2)},${y(p[upperKey]).toFixed(2)}`).join(' ');
    const bottom = [...points].reverse().map((p) => `${x(p.date).toFixed(2)},${y(p[lowerKey]).toFixed(2)}`).join(' ');
    return `${top} ${bottom}`;
  };
  const priceTicks = buildPriceTicks(Math.exp(minLog), Math.exp(maxLog));
  const years = [];
  for (let year = new Date(firstTime).getUTCFullYear() + 1; year <= new Date(lastTime).getUTCFullYear(); year += Math.max(1, Math.ceil((new Date(lastTime).getUTCFullYear() - new Date(firstTime).getUTCFullYear()) / 8))) years.push(`${year}-01-01`);
  const latest = points[points.length - 1];
  const bandMarkup = rainbow.bands.map((band) => `<polygon class="rainbow-band" points="${bandPolygon(`level_${band.lower_level}`, `level_${band.upper_level}`)}" fill="${band.color}" />`).join('');
  const gridMarkup = [
    ...priceTicks.map((tick) => `<g class="rainbow-grid"><line x1="${pad.left}" x2="${width - pad.right}" y1="${y(tick).toFixed(2)}" y2="${y(tick).toFixed(2)}" /><text x="${width - pad.right + 14}" y="${(y(tick) + 5).toFixed(2)}">${money.format(tick)}</text></g>`),
    ...years.map((date) => `<g class="rainbow-grid muted-grid"><line x1="${x(date).toFixed(2)}" x2="${x(date).toFixed(2)}" y1="${pad.top}" y2="${height - pad.bottom}" /><text x="${x(date).toFixed(2)}" y="${height - 18}">${date.slice(0, 4)}</text></g>`),
  ].join('');
  const latestX = x(latest.date);
  const latestY = y(latest.close);
  const legendMarkup = rainbow.bands.map((band) => `<span><b style="background:${band.color}"></b>${escapeHtml(band.label)}</span>`).join('');
  target.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHtml(data.asset.name)} Rainbow Chart"><rect width="${width}" height="${height}" rx="12" fill="#08111f" />${gridMarkup}${bandMarkup}<path class="rainbow-trend-line" d="${pathFor('trend')}" /><path class="rainbow-price-line" d="${pathFor('close')}" /><line class="rainbow-latest-line" x1="${latestX.toFixed(2)}" x2="${latestX.toFixed(2)}" y1="${pad.top}" y2="${height - pad.bottom}" /><circle class="rainbow-latest-dot" cx="${latestX.toFixed(2)}" cy="${latestY.toFixed(2)}" r="5" /><text class="rainbow-latest-label" x="${Math.min(latestX + 14, width - pad.right - 195).toFixed(2)}" y="${(latestY - 12).toFixed(2)}">${fmtMoney(latest.close)} · ${escapeHtml(latest.zone)}</text></svg><div class="rainbow-legend">${legendMarkup}</div>`;
  summary.innerHTML = `<article><span>Rainbow Zone</span><strong>${escapeHtml(rainbow.latest.zone)}</strong><small>Power-law residual: ${fmtNum(rainbow.latest.residual)}</small></article><article><span>Power-Law Trend</span><strong>${fmtMoney(rainbow.latest.trend)}</strong><small>Fit from ${escapeHtml(rainbow.model.fit_start_date)}; R² ${fmtNum(rainbow.model.r_squared)}</small></article><article><span>Band Range</span><strong>${fmtMoney(rainbow.latest.lower_band)} - ${fmtMoney(rainbow.latest.upper_band)}</strong><small>${escapeHtml(rainbow.model.warning)}</small></article>`;
}

function buildPriceTicks(min, max) {
  if (!Number.isFinite(min) || !Number.isFinite(max) || min <= 0 || max <= 0 || min >= max) {
    return [];
  }
  const ticks = [];
  const bases = [1, 2, 3, 5];
  const startPow = Math.max(-8, Math.floor(Math.log10(min)));
  const endPow = Math.min(12, Math.ceil(Math.log10(max)));
  for (let p = startPow; p <= endPow; p += 1) {
    for (const b of bases) {
      const v = b * 10 ** p;
      if (v >= min && v <= max) ticks.push(v);
    }
  }
  return ticks.slice(-8);
}

function renderScenario(scenario) {
  const targets = (scenario.target_zones_usd ?? []).map((v) => fmtMoney(v)).join(' / ');
  const notes = (scenario.notes ?? []).map((n) => `<li>${escapeHtml(n)}</li>`).join('');
  return `<p class="scenario-label">${escapeHtml(scenario.label)}</p><p>${escapeHtml(scenario.structure)}</p><dl class="scenario-grid"><dt>Current wave</dt><dd>${escapeHtml(scenario.current_wave ?? scenario.status)}</dd><dt>Confidence</dt><dd>${fmtNum((scenario.confidence ?? 0) * 100)}%</dd><dt>Invalidation</dt><dd>${fmtMoney(scenario.invalidation_level_usd)}</dd><dt>Confirmation</dt><dd>${fmtMoney(scenario.confirmation_level_usd)}</dd><dt>Targets</dt><dd>${targets || 'n/a'}</dd></dl><ul class="scenario-notes">${notes}</ul>`;
}

function renderElliottWave(data) {
  const wave = data.elliott_wave;
  const latest = data.latest;
  document.querySelector('#elliottSummary').innerHTML = [card('Wave Engine', wave.version, escapeHtml(wave.method)), card('Confluence Score', wave.confluence_score, 'Phase 2: fib + RSI + log + MVRV + trend'), card('Primary Confidence', `${fmtNum(wave.primary.confidence * 100)}%`, escapeHtml(wave.primary.current_wave)), card('Primary Invalidation', fmtMoney(wave.primary.invalidation_level_usd), 'Break below promotes alternate')].join('');
  const pivots = wave.pivots ?? [];
  const width = 1200;
  const height = 360;
  const pad = { top: 36, right: 56, bottom: 48, left: 70 };
  const firstTime = Date.parse(pivots[0]?.date ?? latest.date);
  const lastTime = Date.parse(pivots[pivots.length - 1]?.date ?? latest.date);
  const prices = pivots.map((p) => Number(p.price));
  prices.push(latest.close);
  const minLog = Math.log(Math.min(...prices) * 0.88);
  const maxLog = Math.log(Math.max(...prices) * 1.12);
  const x = (date) => pad.left + ((Date.parse(date) - firstTime) / Math.max(lastTime - firstTime, 1)) * (width - pad.left - pad.right);
  const y = (value) => pad.top + (1 - ((Math.log(value) - minLog) / (maxLog - minLog))) * (height - pad.top - pad.bottom);
  const path = pivots.map((p, i) => `${i === 0 ? 'M' : 'L'}${x(p.date).toFixed(2)},${y(p.price).toFixed(2)}`).join(' ');
  const labels = ['1', '2', '3', '4', '5', 'A', 'B', 'C', 'X', 'Y', 'Z'];
  const pivotMarkup = pivots.map((p, i) => `<g class="elliott-pivot ${escapeHtml(p.type)}"><circle cx="${x(p.date).toFixed(2)}" cy="${y(p.price).toFixed(2)}" r="7" /><text x="${x(p.date).toFixed(2)}" y="${(y(p.price) - 14).toFixed(2)}">${escapeHtml(labels[Math.max(0, labels.length - pivots.length + i)] ?? String(i + 1))}</text><title>${escapeHtml(p.date)} · ${escapeHtml(p.type)} · ${fmtMoney(p.price)}</title></g>`).join('');
  document.querySelector('#elliottChart').innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Elliott Wave pivot map"><rect width="${width}" height="${height}" rx="14" fill="#08111f" /><path class="elliott-path" d="${path}" />${pivotMarkup}<text class="elliott-caption" x="${pad.left}" y="${height - 18}">13% ZigZag pivots · scenario labels are candidates, not gospel from Mount TradingView</text></svg>`;
  document.querySelector('#elliottPrimary').innerHTML = renderScenario(wave.primary);
  document.querySelector('#elliottAlternate').innerHTML = renderScenario(wave.alternate);
  document.querySelector('#elliottConfluence').innerHTML = Object.entries(wave.phase2_confluence).map(([name, item]) => `<div class="component"><strong>${escapeHtml(name.replaceAll('_', ' '))}</strong><span>${item.score > 0 ? '+' : ''}${item.score}</span><small>${escapeHtml(item.detail)}</small></div>`).join('');
  document.querySelector('#elliottManual').innerHTML = `<p><strong>Status:</strong> ${escapeHtml(data.manual_thesis?.manual_elliott_wave_count?.status ?? 'Manual override available')}</p><p class="muted">Manual thesis files can be added under <code>data/manual/</code>. For now, algorithmic scenarios are clearly labeled as candidates.</p><ul class="scenario-notes">${(wave.limitations ?? []).map((n) => `<li>${escapeHtml(n)}</li>`).join('')}</ul>`;
}

function setupTabs() {
  const buttons = Array.from(document.querySelectorAll('[data-chart-tab]'));
  const panes = {
    log: document.querySelector('#logPane'),
    'moving-average': document.querySelector('#movingAveragePane'),
    rainbow: document.querySelector('#rainbowPane'),
    elliott: document.querySelector('#elliottPane'),
  };
  buttons.forEach((button) => {
    button.addEventListener('click', () => {
      const target = button.dataset.chartTab;
      buttons.forEach((b) => { const active = b === button; b.classList.toggle('active', active); b.setAttribute('aria-selected', String(active)); });
      Object.entries(panes).forEach(([name, pane]) => { const active = name === target; pane.classList.toggle('active', active); pane.hidden = !active; });
      if (target === 'log') logChart?.applyOptions({ width: document.querySelector('#logChart').clientWidth });
      if (target === 'moving-average' && activeData) renderMovingAverageChart(activeData);
      if (target === 'rainbow' && activeData) renderRainbowChart(activeData);
      if (target === 'elliott' && activeData) renderElliottWave(activeData);
    });
  });
}

function renderReadouts(data) {
  const l = data.latest;
  document.querySelector('#currentRead').innerHTML = `<p class="zone ${zoneClass(l.zone)}">${escapeHtml(l.zone)}</p><p>${escapeHtml(l.zone_note)}</p><dl><dt>-2σ deep value band</dt><dd>${fmtMoney(l.band_minus_2)}</dd><dt>-1.5σ accumulation band</dt><dd>${fmtMoney(l.band_minus_1_5)}</dd><dt>+2σ take-chips band</dt><dd>${fmtMoney(l.band_plus_2)}</dd><dt>Drawdown from ATH</dt><dd>${fmtNum(l.drawdown_from_ath_pct)}%</dd><dt>RSI 14D</dt><dd>${fmtNum(l.rsi_14d)}</dd><dt>MVRV</dt><dd>${l.latest_available_mvrv ? `${fmtNum(l.latest_available_mvrv)} <small class="muted">as of ${escapeHtml(l.latest_available_mvrv_date)}</small>` : 'n/a'}</dd><dt>50D moving average</dt><dd>${fmtMoney(l.ma_50d)}</dd><dt>100D moving average</dt><dd>${fmtMoney(l.ma_100d)}</dd><dt>200D moving average</dt><dd>${fmtMoney(l.ma_200d)}</dd><dt>200W moving average</dt><dd>${fmtMoney(l.ma_200w)}</dd></dl>`;
  document.querySelector('#regime').innerHTML = `<p class="big-score">${data.regime.score}</p><p><strong>${escapeHtml(data.regime.label)}</strong></p><p class="muted">${escapeHtml(data.regime.scale)}</p>`;
  document.querySelector('#components').innerHTML = data.regime.components.map((c) => `<div class="component"><strong>${escapeHtml(c.name)}</strong><span>${c.score > 0 ? '+' : ''}${c.score}</span><small>${escapeHtml(c.detail)}</small></div>`).join('');
  document.querySelector('#manual').innerHTML = `<p><strong>Source:</strong> ${escapeHtml(data.source?.source ?? 'market feed')}</p><p><strong>Provenance:</strong> ${escapeHtml(data.source?.provenance ?? 'n/a')}</p><p><strong>Symbol:</strong> ${escapeHtml(data.asset.symbol)}</p><p><strong>Rows:</strong> ${escapeHtml(data.source?.rows ?? data.points.length)}</p><p class="muted">${escapeHtml(data.source?.limitation ?? 'No limitations recorded.')}</p>`;
}

function renderAll(data) {
  renderStatus(data);
  renderMacroCycle(macroData);
  renderLogChart(data);
  if (!document.querySelector('#movingAveragePane').hidden) renderMovingAverageChart(data);
  renderRainbowChart(data);
  renderElliottWave(data);
  renderReadouts(data);
}

async function main() {
  const [res, macroRes] = await Promise.all([
    fetch('/public/data/assets.json', { cache: 'no-store' }),
    fetch('/public/data/macro-cycle.json', { cache: 'no-store' }),
  ]);
  if (!res.ok) throw new Error(`Asset index fetch failed: ${res.status}`);
  dashboardIndex = await res.json();
  macroData = macroRes.ok ? await macroRes.json() : null;
  renderAssetButtons(dashboardIndex);
  setupTabs();
  await selectAsset(dashboardIndex.assets[0].id);
  window.addEventListener('resize', () => {
    if (!document.querySelector('#logPane').hidden) logChart?.applyOptions({ width: document.querySelector('#logChart').clientWidth });
    if (!document.querySelector('#movingAveragePane').hidden) movingAverageChart?.applyOptions({ width: document.querySelector('#movingAverageChart').clientWidth });
  });
}

main().catch((err) => {
  document.body.innerHTML = `<main class="panel error"><h1>Dashboard failed to load</h1><pre>${escapeHtml(err.stack || err.message)}</pre></main>`;
});
