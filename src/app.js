import { mountMarketSizes } from '/src/market-sizes.js?v=1';
import { mountReserveHoldings } from '/src/reserve-holdings.js';
import { mountPolicyAdoption } from '/src/policy-adoption.js?v=arma-progress-v1';
const moneyWhole = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });
const moneyCents = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2, maximumFractionDigits: 2 });
const moneySubDollar = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2, maximumFractionDigits: 4 });
const num = new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 });
let logChart;
let movingAverageChart;
let dashboardIndex;
let activeAssetId;
let activeData;
let macroData;
let macroDashboardData;
let macroSupplyData;
let fiscalFlowData;
let reserveShiftData;
let activeMacroRange = '10Y';
let activeHolderCountry;
let activeFiscalYear = 'current';

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
  if (value === null || value === undefined) return 'n/a';
  const amount = Number(value);
  if (!Number.isFinite(amount)) return 'n/a';
  if (Math.abs(amount) < 1) return moneySubDollar.format(amount);
  if (Math.abs(amount) < 100) return moneyCents.format(amount);
  return moneyWhole.format(amount);
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

function explainedStatusCard(label, value, { what, why, read }, cls = '') {
  return `<article class="status-card explained ${cls}">
    <span>${escapeHtml(label)}</span>
    <strong>${escapeHtml(value)}</strong>
    <div class="status-explanation">
      <p><b>What it is</b>${escapeHtml(what)}</p>
      <p><b>Why it matters</b>${escapeHtml(why)}</p>
      <p><b>Current read</b>${escapeHtml(read)}</p>
    </div>
  </article>`;
}

function clampScore(value) {
  if (value === null || value === undefined || value === '') return null;
  const n = Number(value);
  return Number.isFinite(n) ? Math.max(-2, Math.min(2, n)) : null;
}

function scoreReading(score, scale = 'valuation') {
  if (score === null) return { label: 'Context only', posture: 'Use with other signals', className: 'context' };
  if (scale === 'environment') {
    if (score <= -1.5) return { label: 'Strongly supportive', posture: 'Favors gradual accumulation', className: 'deep-value' };
    if (score <= -0.5) return { label: 'Supportive', posture: 'Constructive for Bitcoin', className: 'attractive' };
    if (score < 0.5) return { label: 'Neutral / mixed', posture: 'Maintain discipline; wait for confirmation', className: 'neutral' };
    if (score < 1.5) return { label: 'Restrictive', posture: 'Use caution with new exposure', className: 'stretched' };
    return { label: 'Strongly restrictive', posture: 'Prioritize risk control', className: 'take-profits' };
  }
  if (score <= -1.5) return { label: 'Deep value', posture: 'Strong accumulation zone', className: 'deep-value' };
  if (score <= -0.5) return { label: 'Attractive', posture: 'Accumulate gradually', className: 'attractive' };
  if (score < 0.5) return { label: 'Neutral / fair', posture: 'Hold or use regular DCA', className: 'neutral' };
  if (score < 1.5) return { label: 'Stretched', posture: 'Slow buying; consider trimming', className: 'stretched' };
  return { label: 'Take-profit zone', posture: 'Consider taking chips off the table', className: 'take-profits' };
}

function interpretationPanel({ score = null, scale = 'valuation', what, why, read, method = '' }) {
  const normalized = clampScore(score);
  const reading = scoreReading(normalized, scale);
  const marker = normalized === null ? 50 : ((normalized + 2) / 4) * 100;
  const scoreText = normalized === null ? 'Not scored' : `${normalized > 0 ? '+' : ''}${normalized.toFixed(1)}`;
  const scaleText = scale === 'environment' ? 'Supportive' : 'Cheap';
  const highText = scale === 'environment' ? 'Restrictive' : 'Take profits';
  return `<aside class="interpretation-card ${reading.className}">
    <div class="interpretation-head">
      <div><span>Bitcoin interpretation</span><strong>${escapeHtml(reading.label)}</strong></div>
      <b class="interpretation-score">${escapeHtml(scoreText)}</b>
    </div>
    <div class="opportunity-scale${normalized === null ? ' unscored' : ''}">
      <div class="opportunity-track"><i style="left:${marker.toFixed(1)}%"></i></div>
      <div class="opportunity-ticks"><span>−2<br><small>${scaleText}</small></span><span>−1</span><span>0<br><small>Neutral</small></span><span>+1</span><span>+2<br><small>${highText}</small></span></div>
    </div>
    <div class="interpretation-copy">
      <p><b>What it shows</b>${escapeHtml(what)}</p>
      <p><b>Why it matters</b>${escapeHtml(why)}</p>
      <p><b>Current read</b>${escapeHtml(read)}</p>
      <p><b>Investor posture</b>${escapeHtml(reading.posture)}</p>
    </div>
    ${method ? `<small class="interpretation-method">${escapeHtml(method)}</small>` : ''}
  </aside>`;
}

const MACRO_INTERPRETATION = {
  net_liquidity: ['The Fed balance sheet less Treasury cash and reverse repos.', 'It approximates dollars available to support financial-market liquidity.'],
  m2: ['The stock of widely held U.S. money and deposits.', 'Faster money growth can improve nominal liquidity available to risk assets.'],
  broad_dollar: ['The trade-weighted value of the U.S. dollar.', 'A stronger dollar often tightens global financial conditions; a weaker dollar can ease them.'],
  real_yield_10y: ['The inflation-adjusted yield on a 10-year Treasury.', 'High real yields raise the opportunity cost of holding a non-yielding asset such as Bitcoin.'],
  nfci: ['A broad measure of U.S. financial conditions.', 'Lower or negative readings indicate easier credit and risk conditions.'],
  wti: ['The benchmark U.S. crude-oil price.', 'Oil shocks can revive inflation pressure and delay easier monetary policy.'],
  credit_spread: ['The extra yield lower-quality corporate borrowers pay over Treasuries.', 'Widening spreads signal stress and reduced appetite for risk.'],
  debt_held_public: ['U.S. federal debt held outside government accounts.', 'It provides long-run fiscal context, but its level alone is not a Bitcoin timing signal.'],
  gross_debt: ['Total outstanding U.S. federal debt.', 'It frames long-run currency and fiscal concerns but does not provide a standalone entry signal.'],
  fed_treasuries: ['Treasury securities held by the Federal Reserve.', 'Rising Fed holdings can absorb duration and accompany easier liquidity conditions.'],
  exchange_reserve: ['Bitcoin held in exchange wallets tracked by Coin Metrics.', 'Lower custody inventory may reduce readily movable supply, although it is not the live quantity offered for sale.'],
};

function macroOpportunityScore(metric) {
  if (!metric || String(metric.supportive_when).toLowerCase().includes('context only')) return null;
  const percentile = Number(metric.percentile_since_2015);
  if (!Number.isFinite(percentile)) return null;
  const direction = String(metric.supportive_when).toLowerCase();
  const highIsSupportive = direction.includes('rising') || direction.includes('accelerating');
  const percentileScore = (percentile - 50) / 25;
  return clampScore(highIsSupportive ? -percentileScore : percentileScore);
}

function percentileBand(value) {
  const percentile = Number(value);
  if (!Number.isFinite(percentile)) return 'unavailable historical position';
  if (percentile <= 10) return 'near the bottom of its historical range';
  if (percentile <= 25) return 'low in its historical range';
  if (percentile < 40) return 'below the middle of its historical range';
  if (percentile <= 60) return 'near the middle of its historical range';
  if (percentile < 75) return 'above the middle of its historical range';
  if (percentile < 90) return 'high in its historical range';
  return 'near the top of its historical range';
}

function percentileExplanation(value, history = 'since 2015') {
  const percentile = Number(value);
  if (!Number.isFinite(percentile)) return 'Historical comparison is unavailable.';
  return `Percentile ${fmtNum(percentile)} means ${fmtNum(percentile)}% of readings ${history} were at or below this level and ${fmtNum(100 - percentile)}% were higher—${percentileBand(percentile)}.`;
}

function formatMacroDelta(metric) {
  const delta = Number(metric.change_3m);
  const percent = Number(metric.change_3m_pct);
  if (!Number.isFinite(delta) && !Number.isFinite(percent)) return 'The three-month change is unavailable.';
  const rose = delta > 0 || (!Number.isFinite(delta) && percent > 0);
  const fell = delta < 0 || (!Number.isFinite(delta) && percent < 0);
  const direction = rose ? 'rose' : fell ? 'fell' : 'was unchanged';
  let absolute = '';
  if (Number.isFinite(delta) && delta !== 0) {
    const amount = Math.abs(delta);
    if (metric.unit === 'USD billions') absolute = `$${fmtNum(amount)}B`;
    else if (metric.unit === 'USD trillions') absolute = `$${fmtNum(amount)}T`;
    else if (metric.unit === 'USD/barrel') absolute = `$${fmtNum(amount)} per barrel`;
    else if (metric.unit === '%') absolute = `${fmtNum(amount)} percentage points`;
    else if (metric.unit === 'BTC') absolute = `${new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(amount)} BTC`;
    else absolute = `${fmtNum(amount)} ${metric.unit ?? 'units'}`;
  }
  const percentText = Number.isFinite(percent) && percent !== 0 ? `${fmtNum(Math.abs(percent))}%` : '';
  const magnitude = [absolute, percentText ? `or ${percentText}` : ''].filter(Boolean).join(' ');
  return `Over three months it ${direction}${magnitude ? ` by ${magnitude}` : ''}.`;
}

function macroDirectionMeaning(metric) {
  const directionRule = String(metric.supportive_when ?? '').toLowerCase();
  const delta = Number(metric.change_3m);
  if (!Number.isFinite(delta) || delta === 0) return 'The recent direction is neutral.';
  if (directionRule.includes('context only')) return 'This change is fiscal context, not a direct Bitcoin buy or sell signal.';
  const highIsSupportive = directionRule.includes('rising') || directionRule.includes('accelerating');
  const supportive = highIsSupportive ? delta > 0 : delta < 0;
  return supportive
    ? `That recent direction is supportive for Bitcoin because this indicator is generally more favorable when ${highIsSupportive ? 'rising' : 'falling'}.`
    : `That recent direction is a Bitcoin headwind because this indicator is generally more favorable when ${highIsSupportive ? 'rising' : 'falling'}.`;
}

function macroMetaChange(metric) {
  const delta = Number(metric.change_3m);
  const percent = Number(metric.change_3m_pct);
  const direction = delta > 0 ? 'rose' : delta < 0 ? 'fell' : 'unchanged';
  const percentText = Number.isFinite(percent) ? ` ${fmtNum(Math.abs(percent))}%` : '';
  return `3 months: ${direction}${percentText}`;
}

function macroInterpretation(metric) {
  const copy = MACRO_INTERPRETATION[metric.key] ?? [`${metric.label} through time.`, 'It adds context to the broader Bitcoin investment environment.'];
  return interpretationPanel({
    score: macroOpportunityScore(metric),
    scale: 'environment',
    what: copy[0],
    why: copy[1],
    read: `${fmtMacroValue(metric)}. ${percentileExplanation(metric.percentile_since_2015)} ${formatMacroDelta(metric)} ${macroDirectionMeaning(metric)}`,
    method: 'Score maps the level’s percentile since 2015 onto −2 to +2, oriented so negative is more supportive for Bitcoin. It is context, not a forecast.',
  });
}

function cycleInterpretation(kind, indicator) {
  const definitions = {
    pmi: {
      score: clampScore(-(Number(indicator.value) - 50) / 5),
      what: 'Manufacturing activity relative to the 50 expansion threshold.',
      why: 'A strengthening business cycle can support risk appetite, although very late-cycle strength may eventually increase inflation pressure.',
      read: `PMI is ${fmtNum(indicator.value)}, or ${fmtNum(Math.abs(Number(indicator.value) - 50))} points ${Number(indicator.value) >= 50 ? 'above' : 'below'} the 50 threshold. That indicates ${Number(indicator.value) >= 50 ? 'moderate manufacturing expansion, a generally supportive growth backdrop' : 'manufacturing contraction, a weaker risk backdrop'}.`,
      method: 'Five PMI points from 50 equal roughly one environment-scale point.',
    },
    copper: {
      score: clampScore(-Number(indicator.distance_above_3y_trend_pct) / 20),
      what: 'Copper’s price relative to gold, its three-year trend, and its 200-day average.',
      why: 'Copper strength versus gold can indicate improving cyclical growth expectations before they appear in slower economic data.',
      read: `The ratio is ${fmtNum(indicator.distance_above_3y_trend_pct)}% above its three-year trend—roughly ${fmtNum(1 + Number(indicator.distance_above_3y_trend_pct) / 100)} times the modelled level. Together with price above its 200-day average, ${indicator.status === 'fired' ? 'this is a strong cyclical-growth signal' : 'the growth signal is not yet confirmed'}.`,
      method: 'Twenty percentage points above or below trend equal roughly one environment-scale point.',
    },
    realizedVol: {
      score: null,
      what: 'The annualized size of Bitcoin’s realized daily price swings over 90 days.',
      why: 'Low volatility can precede expansion, but it does not identify the direction of the next move.',
      read: `Realized volatility is ${fmtNum(indicator.value)}% annualized. ${percentileExplanation(indicator.historical_percentile, 'in the available history')} This means Bitcoin has been unusually quiet, or “coiled”; it does not predict whether the next expansion will be up or down.`,
      method: 'Not scored because volatility compression can resolve upward or downward.',
    },
    impliedVol: {
      score: null,
      what: 'The options market’s expectation of future Bitcoin volatility.',
      why: 'It measures expected movement and option pricing, not whether Bitcoin is cheap or expensive.',
      read: `DVOL is ${fmtNum(indicator.value)}%, meaning options are pricing roughly that level of annualized movement. Its ${indicator.status} classification describes expected movement size, not bullish or bearish direction.`,
      method: 'Not scored because implied volatility describes uncertainty, not directional opportunity.',
    },
    oil: {
      score: clampScore(((Number(indicator.value) - 80) / 20) + (Number(indicator.change_20d_pct) / 10)),
      what: 'WTI oil price and its recent rate of change.',
      why: 'A sustained oil shock can raise inflation pressure and keep monetary conditions tighter for longer.',
      read: `WTI is ${fmtMoney(indicator.value)} and has ${Number(indicator.change_20d_pct) < 0 ? 'fallen' : 'risen'} ${fmtNum(Math.abs(Number(indicator.change_20d_pct)))}% over 20 sessions. ${Number(indicator.change_20d_pct) < 0 ? 'The retreat reduces near-term inflation pressure and is supportive for easier policy.' : 'The rise increases inflation risk and is a potential Bitcoin headwind.'}`,
      method: 'Combines the $80 risk threshold with the 20-session trend on the environment scale.',
    },
  };
  const definition = definitions[kind];
  return interpretationPanel({ ...definition, scale: 'environment' });
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
  if (!data) return;
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
    <article class="macro-card"><span>ISM Manufacturing PMI</span><strong>${fmtNum(pmi.value)}</strong><small>${escapeHtml(pmi.date)} · ${escapeHtml(pmi.status)} · 50 threshold</small><div class="threshold-bar"><i style="width:${Math.min(100, Number(pmi.value))}%"></i><b style="left:50%"></b></div><em>Manual, video-sourced snapshot</em>${cycleInterpretation('pmi', pmi)}</article>
    <article class="macro-card"><span>Copper / Gold</span><strong>${fmtRatio(copper.value)}</strong><small>${fmtNum(copper.distance_above_3y_trend_pct)}% above 3Y trend · ${copper.status === 'fired' ? 'strong breakout' : escapeHtml(copper.status)}</small>${sparkline(copper.series, '#f59e0b')}<em>${escapeHtml(copper.method)}</em>${cycleInterpretation('copper', copper)}</article>
    <article class="macro-card"><span>BTC 90D Realized Vol</span><strong>${fmtNum(realized.value)}%</strong><small>${escapeHtml(percentileBand(realized.historical_percentile))} · ${escapeHtml(realized.status)}</small>${sparkline(realized.series, '#a78bfa')}<em>${escapeHtml(realized.method)}</em>${cycleInterpretation('realizedVol', realized)}</article>
    <article class="macro-card"><span>BTC Implied Volatility</span><strong>${fmtNum(implied.value)}%</strong><small>Deribit DVOL · ${escapeHtml(implied.status)}</small><div class="vol-gauge"><i style="width:${Math.min(100, Number(implied.value))}%"></i></div><em>Options market expectation; complements realized volatility.</em>${cycleInterpretation('impliedVol', implied)}</article>
  `;
  const oil = indicators.oil;
  document.querySelector('#macroRisk').innerHTML = `<div><span>Setup invalidation watch</span><strong>WTI ${fmtMoney(oil.value)} · ${escapeHtml(oil.status)}</strong><small>${Number(oil.change_20d_pct) < 0 ? 'Fell' : 'Rose'} ${fmtNum(Math.abs(Number(oil.change_20d_pct)))}% over 20 sessions · ${Number(oil.change_20d_pct) < 0 ? 'inflation pressure easing' : 'inflation pressure increasing'}.</small></div>${sparkline(oil.series, oil.status === 'contained' ? '#22c55e' : '#f87171')}<div class="macro-risk-interpretation">${cycleInterpretation('oil', oil)}</div>`;
}

function macroRangeStart(rows) {
  if (!rows?.length || activeMacroRange === 'Max') return null;
  const years = activeMacroRange === '1Y' ? 1 : activeMacroRange === '5Y' ? 5 : 10;
  const latest = new Date(`${rows[rows.length - 1].date}T00:00:00Z`);
  latest.setUTCFullYear(latest.getUTCFullYear() - years);
  return latest.toISOString().slice(0, 10);
}

function niceAxisStep(span, targetTicks = 5) {
  const rough = Math.max(span, 1e-9) / targetTicks;
  const magnitude = 10 ** Math.floor(Math.log10(rough));
  const normalized = rough / magnitude;
  const multiple = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 2.5 ? 2.5 : normalized <= 5 ? 5 : 10;
  return multiple * magnitude;
}

function fmtBtcAxis(value) {
  const absolute = Math.abs(value);
  if (absolute >= 1e6) return `${(value / 1e6).toFixed(absolute % 1e6 === 0 ? 1 : 2)}M`;
  if (absolute >= 1e3) return `${num.format(value / 1e3)}k`;
  return num.format(value);
}

function macroChart(rows, color = '#38bdf8', ariaLabel = 'Macro history', expanded = false) {
  const start = macroRangeStart(rows);
  const clean = (rows ?? [])
    .filter((row) => !start || row.date >= start)
    .map((row) => ({ date: row.date, value: Number(row.value) }))
    .filter((row) => Number.isFinite(row.value));
  if (clean.length < 2) return '<div class="macro-chart-empty">Historical series unavailable</div>';
  const width = expanded ? 1200 : 760;
  const height = expanded ? 390 : 230;
  const pad = expanded
    ? { top: 34, right: 24, bottom: 48, left: 86 }
    : { top: 20, right: 18, bottom: 34, left: 58 };
  const values = clean.map((row) => row.value);
  let min = Math.min(...values);
  let max = Math.max(...values);
  const range = Math.max(max - min, Math.abs(max) * 0.01, 1e-9);
  const yStep = expanded ? niceAxisStep(range, 5) : null;
  min = expanded ? Math.floor(min / yStep) * yStep : min - range * 0.08;
  max = expanded ? Math.ceil(max / yStep) * yStep : max + range * 0.08;
  const x = (index) => pad.left + (index / Math.max(clean.length - 1, 1)) * (width - pad.left - pad.right);
  const y = (value) => pad.top + (1 - (value - min) / (max - min)) * (height - pad.top - pad.bottom);
  const path = clean.map((row, index) => `${index ? 'L' : 'M'}${x(index).toFixed(1)},${y(row.value).toFixed(1)}`).join(' ');
  const zero = min < 0 && max > 0 ? `<line class="macro-zero" x1="${pad.left}" x2="${width - pad.right}" y1="${y(0).toFixed(1)}" y2="${y(0).toFixed(1)}" />` : '';
  const yTicks = expanded
    ? Array.from({ length: Math.round((max - min) / yStep) + 1 }, (_, index) => min + index * yStep)
    : [];
  const yearTicks = expanded
    ? clean.reduce((ticks, row, index) => {
      const year = row.date.slice(0, 4);
      if (!ticks.some((tick) => tick.year === year)) ticks.push({ year, index });
      return ticks;
    }, [])
    : [];
  const detailedGrid = expanded ? `${yTicks.map((tick) => `<g><line class="macro-grid" x1="${pad.left}" x2="${width - pad.right}" y1="${y(tick).toFixed(1)}" y2="${y(tick).toFixed(1)}"/><text class="macro-axis macro-y-tick end" x="${pad.left - 12}" y="${(y(tick) + 4).toFixed(1)}">${escapeHtml(fmtBtcAxis(tick))}</text></g>`).join('')}${yearTicks.map((tick) => `<g><line class="macro-grid macro-grid-year" x1="${x(tick.index).toFixed(1)}" x2="${x(tick.index).toFixed(1)}" y1="${pad.top}" y2="${height - pad.bottom}"/><text class="macro-axis macro-year-tick" text-anchor="middle" x="${x(tick.index).toFixed(1)}" y="${height - 17}">${tick.year}</text></g>`).join('')}<text class="macro-axis macro-axis-title" x="${pad.left}" y="18">BTC held</text>` : '';
  return `<svg class="macro-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHtml(ariaLabel)}">
    ${expanded ? detailedGrid : `<line class="macro-grid" x1="${pad.left}" x2="${width - pad.right}" y1="${y(max - (max - min) * .15).toFixed(1)}" y2="${y(max - (max - min) * .15).toFixed(1)}" /><line class="macro-grid" x1="${pad.left}" x2="${width - pad.right}" y1="${y(min + (max - min) * .15).toFixed(1)}" y2="${y(min + (max - min) * .15).toFixed(1)}" />`}
    ${zero}<path d="${path}" fill="none" stroke="${color}" stroke-width="3" vector-effect="non-scaling-stroke" />
    <circle cx="${x(clean.length - 1).toFixed(1)}" cy="${y(clean[clean.length - 1].value).toFixed(1)}" r="4" fill="${color}" />
    ${expanded ? '' : `<text class="macro-axis" x="${pad.left}" y="${height - 10}">${escapeHtml(clean[0].date.slice(0, 7))}</text><text class="macro-axis end" x="${width - pad.right}" y="${height - 10}">${escapeHtml(clean[clean.length - 1].date.slice(0, 7))}</text><text class="macro-axis" x="4" y="${(pad.top + 12).toFixed(1)}">${escapeHtml(fmtCompact(max))}</text><text class="macro-axis" x="4" y="${(height - pad.bottom).toFixed(1)}">${escapeHtml(fmtCompact(min))}</text>`}
  </svg>`;
}

function fmtCompact(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return 'n/a';
  if (Math.abs(n) >= 1000) return `${num.format(n / 1000)}k`;
  if (Math.abs(n) < 1 && n !== 0) return n.toFixed(2);
  return num.format(n);
}

function fmtMacroValue(metric) {
  if (!metric || metric.value === null || metric.value === undefined) return 'Unavailable';
  const value = Number(metric.value);
  if (metric.unit === 'USD/barrel') return `$${num.format(value)}`;
  if (metric.unit === '%') return `${num.format(value)}%`;
  if (metric.unit === 'USD trillions') return `$${num.format(value)}T`;
  if (metric.unit === 'USD billions') return `$${num.format(value)}B`;
  if (metric.unit === 'BTC') return `${new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(value)} BTC`;
  return `${num.format(value)} ${metric.unit ?? ''}`.trim();
}

function macroMetricCard(metric, color = '#38bdf8', expanded = false) {
  if (!metric) return '';
  return `<article class="macro-chart-card">
    <div class="macro-chart-title"><div><span>${escapeHtml(metric.label)}</span><strong>${escapeHtml(fmtMacroValue(metric))}</strong></div><small>${escapeHtml(metric.date ?? 'unavailable')}</small></div>
    ${macroChart(metric.series, color, `${metric.label} history`, expanded)}
    <div class="macro-chart-meta"><span>${escapeHtml(macroMetaChange(metric))}</span><span>${escapeHtml(percentileBand(metric.percentile_since_2015))} · percentile ${escapeHtml(fmtNum(metric.percentile_since_2015))}</span></div>
    <p>${escapeHtml(metric.supportive_when)}</p>
    <small>${escapeHtml(metric.source)} · ${escapeHtml(metric.cadence)}${metric.caveat ? ` · ${escapeHtml(metric.caveat)}` : ''}</small>
    ${macroInterpretation(metric)}
  </article>`;
}

function pillarClass(state) {
  const normalized = String(state).toLowerCase();
  if (normalized.includes('supportive') || normalized.includes('rising') || normalized.includes('available')) return 'supportive';
  if (normalized.includes('restrictive') || normalized.includes('falling') || normalized.includes('needed')) return 'restrictive';
  return 'mixed';
}

function renderHolderCountry(country) {
  activeHolderCountry = country;
  const holder = macroDashboardData?.holders?.holders?.find((item) => item.country === country);
  const target = document.querySelector('#holderCountryChart');
  if (!holder || !target) return;
  target.innerHTML = `<div class="macro-chart-title"><div><span>${escapeHtml(holder.country)}</span><strong>$${fmtNum(holder.value)}B</strong></div><small>${escapeHtml(holder.date)}</small></div>
    ${macroChart(holder.series, '#f59e0b', `${holder.country} U.S. Treasury holdings`)}
    <div class="macro-chart-meta"><span>3M ${holder.change_3m > 0 ? '+' : ''}${fmtNum(holder.change_3m)}B · ${escapeHtml(holder.trend_3m)}</span><span>12M ${holder.change_12m > 0 ? '+' : ''}${fmtNum(holder.change_12m)}B · ${escapeHtml(holder.trend_12m)}</span></div>
    ${interpretationPanel({ what: 'Reported Treasury securities attributed to this country or custody center.', why: 'Foreign demand helps show how U.S. debt issuance is being absorbed, but country attribution can reflect custodians rather than ultimate owners.', read: `${holder.country} is ${holder.trend_12m} over 12 months (${holder.change_12m > 0 ? '+' : ''}${fmtNum(holder.change_12m)}B). Treat this as fiscal-market context, not a direct Bitcoin valuation signal.`, method: 'Not scored: the direction of one holder’s Treasury position is not reliably bullish or bearish for Bitcoin on its own.' })}
    ${holder.custody_center ? '<p class="custody-note">Financial/custody center: location may not identify the ultimate owner.</p>' : ''}`;
  document.querySelectorAll('[data-holder-country]').forEach((button) => button.classList.toggle('active', button.dataset.holderCountry === country));
}

function holderTable(holders) {
  return `<div class="holder-table-wrap"><table class="holder-table"><thead><tr><th>Country / center</th><th>Holdings</th><th>3M</th><th>12M</th><th>Direction</th></tr></thead><tbody>${holders.map((holder) => `
    <tr><td><button type="button" data-holder-country="${escapeHtml(holder.country)}">${escapeHtml(holder.country)}${holder.custody_center ? '<sup>†</sup>' : ''}</button></td><td>$${fmtNum(holder.value)}B</td><td class="${holder.change_3m > 0 ? 'up' : holder.change_3m < 0 ? 'down' : ''}">${holder.change_3m > 0 ? '+' : ''}${fmtNum(holder.change_3m)}B</td><td class="${holder.change_12m > 0 ? 'up' : holder.change_12m < 0 ? 'down' : ''}">${holder.change_12m > 0 ? '+' : ''}${fmtNum(holder.change_12m)}B</td><td><span class="trend-chip ${escapeHtml(holder.trend_12m.replaceAll(' ', '-'))}">${escapeHtml(holder.trend_12m)}</span></td></tr>`).join('')}</tbody></table></div>`;
}

function fmtFiscal(value) {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return 'n/a';
  const absolute = Math.abs(amount);
  const formatted = absolute >= 1e12 ? `$${(absolute / 1e12).toFixed(2)}T` : `$${(absolute / 1e9).toFixed(1)}B`;
  return amount < 0 ? `−${formatted}` : formatted;
}

function formatFiscalDate(value) {
  const date = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) return String(value ?? '');
  return date.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric', timeZone: 'UTC' });
}

function fiscalRows(items, total, kind) {
  const max = Math.max(...items.map((item) => Math.abs(Number(item.amount_dollars))), 1);
  return items.map((item) => {
    const amount = Number(item.amount_dollars);
    const width = Math.max(4, Math.abs(amount) / max * 100);
    return `<li class="fiscal-flow-row ${kind}"><div><span>${escapeHtml(item.label)}</span><strong>${escapeHtml(fmtFiscal(amount))}</strong></div><i style="--flow-width:${width.toFixed(2)}%" aria-hidden="true"></i><small>${(Math.abs(amount) / Math.max(total, 1) * 100).toFixed(1)}% of ${kind === 'receipt' ? 'receipts' : 'positive outlays'}</small></li>`;
  }).join('');
}

function renderFiscalFlow() {
  const target = document.querySelector('#fiscalFlowExhibit');
  if (!target || !fiscalFlowData) return;
  const snapshot = activeFiscalYear === 'current' ? fiscalFlowData.current : fiscalFlowData.years.find((row) => String(row.fiscal_year) === activeFiscalYear);
  if (!snapshot) return;
  const isCurrent = snapshot.status === 'current-ytd';
  const options = [...fiscalFlowData.years.map((row) => `<option value="${row.fiscal_year}" ${String(row.fiscal_year) === activeFiscalYear ? 'selected' : ''}>FY${row.fiscal_year}</option>`), `<option value="current" ${activeFiscalYear === 'current' ? 'selected' : ''}>Current</option>`].join('');
  const balanceLabel = snapshot.deficit_dollars >= 0 ? 'Deficit' : 'Surplus';
  const debt = isCurrent ? fiscalFlowData.debt?.current : fiscalFlowData.debt?.by_fiscal_year?.[String(snapshot.fiscal_year)];
  const priorDebt = fiscalFlowData.debt?.by_fiscal_year?.[String(snapshot.fiscal_year - 1)];
  const debtChange = debt && priorDebt ? (Number(debt.total_public_debt_outstanding_dollars) / Number(priorDebt.total_public_debt_outstanding_dollars) - 1) * 100 : null;
  const debtChangeLabel = debtChange === null ? '' : `${debtChange >= 0 ? '+' : ''}${debtChange.toFixed(1)}% ${isCurrent ? `since FY${snapshot.fiscal_year - 1} close` : `vs FY${snapshot.fiscal_year - 1}`}`;
  const debtCard = debt ? `<div class="total-debt"><span>Total public debt</span><strong>${fmtFiscal(debt.total_public_debt_outstanding_dollars)}</strong><small>As of ${escapeHtml(debt.record_date)}${debtChangeLabel ? ` · ${escapeHtml(debtChangeLabel)}` : ''}</small></div>` : '';
  const positiveOutlayTotal = snapshot.positive_outlays.reduce((sum, item) => sum + Number(item.amount_dollars), 0);
  const comparison = snapshot.prior_year_same_period;
  const changed = comparison ? `<section class="fiscal-changed" aria-labelledby="fiscal-changed-title"><h5 id="fiscal-changed-title">What changed now</h5><p>Versus FY${comparison.fiscal_year} through the same period: receipts <strong>${comparison.receipt_change_dollars >= 0 ? '+' : ''}${fmtFiscal(comparison.receipt_change_dollars)}</strong>; net outlays <strong>${comparison.outlay_change_dollars >= 0 ? '+' : ''}${fmtFiscal(comparison.outlay_change_dollars)}</strong>; deficit <strong>${comparison.deficit_change_dollars >= 0 ? '+' : ''}${fmtFiscal(comparison.deficit_change_dollars)}</strong>; net interest <strong>${comparison.net_interest_change_dollars >= 0 ? '+' : ''}${fmtFiscal(comparison.net_interest_change_dollars)}</strong>.</p></section>` : '';
  const offsets = snapshot.offsetting_outlays.length ? `<details class="fiscal-offsets"><summary>Offsets / recoveries (${snapshot.offsetting_outlays.length})</summary><p>Negative functions reduce net outlays and are shown outside the positive flow.</p><ul>${snapshot.offsetting_outlays.map((item) => `<li><span>${escapeHtml(item.label)}</span><strong>${escapeHtml(fmtFiscal(item.amount_dollars))}</strong></li>`).join('')}</ul></details>` : '';
  target.innerHTML = `<div class="fiscal-flow-head"><div><p class="eyebrow">20-year official record</p><h4>U.S. Fiscal Flow</h4><p>Where federal receipts came from and where net outlays went.</p></div><label><span>Fiscal year</span><select id="fiscalYearSelect" aria-label="Choose U.S. fiscal year">${options}</select></label></div>
    <div class="fiscal-flow-meta"><span class="fiscal-badge ${isCurrent ? 'current' : 'frozen'}">${isCurrent ? 'YTD · refreshable' : 'Frozen year'}</span><strong>${isCurrent ? `FY${snapshot.fiscal_year} YTD through ${formatFiscalDate(snapshot.period_end)}` : `FY${snapshot.fiscal_year} final`}</strong><span>Source date ${escapeHtml(snapshot.period_end)} · ${escapeHtml(snapshot.precision)}</span></div>
    <div class="fiscal-sankey" role="group" aria-label="Receipts, deficit bridge, and outlays for ${escapeHtml(snapshot.label)}">
      <section><h5>Receipts by source <strong>${fmtFiscal(snapshot.total_receipts_dollars)}</strong></h5><ol>${fiscalRows(snapshot.receipts, snapshot.total_receipts_dollars, 'receipt')}</ol></section>
      <section class="fiscal-bridge"><div><span>Total receipts</span><strong>${fmtFiscal(snapshot.total_receipts_dollars)}</strong></div><div class="${snapshot.deficit_dollars >= 0 ? 'deficit' : 'surplus'}"><span>${balanceLabel}</span><strong>${fmtFiscal(Math.abs(snapshot.deficit_dollars))}</strong></div><div><span>Net outlays</span><strong>${fmtFiscal(snapshot.net_outlays_dollars)}</strong></div>${debtCard}<small>Receipts ${snapshot.deficit_dollars >= 0 ? '+ deficit' : '− surplus'} = net outlays. Total public debt is the accumulated outstanding stock, not the annual deficit.</small></section>
      <section><h5>Positive outlays by function <strong>${fmtFiscal(positiveOutlayTotal)}</strong></h5><ol>${fiscalRows(snapshot.positive_outlays, positiveOutlayTotal, 'outlay')}</ol></section>
    </div>
    <div class="fiscal-foot"><p><strong>Net interest:</strong> ${fmtFiscal(snapshot.net_interest_dollars)}</p>${offsets}</div>${changed}
    <p class="fiscal-context"><strong>Bitcoin relevance:</strong> fiscal pressure can shape Treasury issuance and liquidity conditions. This exhibit is context only, is excluded from the Bitcoin score, and is not a direct buy/sell signal. <a href="${escapeHtml(snapshot.source_url)}" target="_blank" rel="noreferrer">Fiscal-flow source</a>${fiscalFlowData.debt?.source_url ? ` · <a href="${escapeHtml(fiscalFlowData.debt.source_url)}" target="_blank" rel="noreferrer">Debt to the Penny source</a>` : ''}.</p>`;
  document.querySelector('#fiscalYearSelect')?.addEventListener('change', (event) => { activeFiscalYear = event.target.value; renderFiscalFlow(); });
}

function reserveShiftChart(data) {
  const rows = data?.chart?.series ?? [];
  if (rows.length < 2) return '<div class="macro-chart-empty">Reserve-shift history unavailable</div>';
  const width = 980;
  const height = 430;
  const pad = { top: 38, right: 116, bottom: 48, left: 66 };
  const min = 10;
  const max = 30;
  const x = (index) => pad.left + (index / Math.max(rows.length - 1, 1)) * (width - pad.left - pad.right);
  const y = (value) => pad.top + ((max - Number(value)) / (max - min)) * (height - pad.top - pad.bottom);
  const line = (key) => rows.map((row, index) => `${index ? 'L' : 'M'}${x(index).toFixed(1)},${y(row[key]).toFixed(1)}`).join(' ');
  const grid = [10, 15, 20, 25, 30].map((tick) => `<g><line class="reserve-grid" x1="${pad.left}" x2="${width - pad.right}" y1="${y(tick).toFixed(1)}" y2="${y(tick).toFixed(1)}"/><text class="reserve-axis" x="${pad.left - 12}" y="${(y(tick) + 4).toFixed(1)}" text-anchor="end">${tick}%</text></g>`).join('');
  const years = rows.map((row, index) => `<g><line class="reserve-year-grid" x1="${x(index).toFixed(1)}" x2="${x(index).toFixed(1)}" y1="${pad.top}" y2="${height - pad.bottom}"/><text class="reserve-axis" x="${x(index).toFixed(1)}" y="${height - 16}" text-anchor="middle">${escapeHtml(row.year)}</text></g>`).join('');
  const points = (key, cls) => rows.map((row, index) => `<g><circle class="reserve-point ${cls}" cx="${x(index).toFixed(1)}" cy="${y(row[key]).toFixed(1)}" r="6"/><text class="reserve-value ${cls}" x="${x(index).toFixed(1)}" y="${(y(row[key]) - 14).toFixed(1)}" text-anchor="middle">${escapeHtml(row[key])}%</text></g>`).join('');
  const last = rows.at(-1);
  return `<svg class="reserve-shift-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="Gold reserves versus U.S. debt holdings in foreign central-bank reserves from 2021 to 2025">
    <text class="reserve-axis-title" x="${pad.left}" y="20">${escapeHtml(data.chart.unit)} · ${escapeHtml(data.chart.cadence)}</text>
    ${grid}${years}
    <path class="reserve-line treasury" d="${line('us_debt')}"/>
    <path class="reserve-line gold" d="${line('gold')}"/>
    ${points('us_debt', 'treasury')}${points('gold', 'gold')}
    <text class="reserve-end-label gold" x="${x(rows.length - 1) + 18}" y="${y(last.gold) - 5}">Gold</text>
    <text class="reserve-end-label treasury" x="${x(rows.length - 1) + 18}" y="${y(last.us_debt) + 22}">U.S. debt</text>
  </svg>`;
}

function renderReserveShift() {
  mountReserveHoldings(document.querySelector('#macroReservesPane'));
  mountPolicyAdoption(document.querySelector('#macroPolicyPane'));
}

function renderMacroWorkspace() {
  const panel = document.querySelector('#macroCyclePanel');
  if (activeAssetId !== 'btc' || (!macroDashboardData && !macroData)) {
    panel.hidden = true;
    return;
  }
  panel.hidden = false;
  renderMacroCycle(macroData);
  if (!macroDashboardData) {
    document.querySelector('#macroAsOf').textContent = 'Long-history data unavailable';
    return;
  }
  const data = macroDashboardData;
  const metrics = data.metrics;
  document.querySelector('#macroAsOf').textContent = `Updated ${new Date(data.generated_at).toLocaleString()}`;
  document.querySelector('#macroPillars').innerHTML = data.pillars.map((pillar) => `<article class="macro-pillar ${pillarClass(pillar.state)}"><span>${escapeHtml(pillar.label)}</span><strong>${escapeHtml(pillar.state)}</strong><small>${escapeHtml(pillar.detail)}</small></article>`).join('');
  document.querySelector('#macroOverviewPane').innerHTML = `<div class="macro-section-heading"><div><h3>Macro overview</h3><p>Highest-signal long-cycle conditions first. Direction is context, not a mechanical Bitcoin forecast.</p></div></div><div class="macro-chart-grid overview">${macroMetricCard(metrics.net_liquidity, '#22d3ee')}${macroMetricCard(metrics.broad_dollar, '#f59e0b')}${macroMetricCard(metrics.real_yield_10y, '#f472b6')}</div>`;
  document.querySelector('#macroLiquidityPane').innerHTML = `<div class="macro-section-heading"><div><h3>Liquidity, rates &amp; conditions</h3><p>Quantity of liquidity plus the price and availability of risk capital.</p></div></div><div class="macro-chart-grid">${macroMetricCard(metrics.m2, '#22c55e')}${macroMetricCard(metrics.nfci, '#a78bfa')}${macroMetricCard(metrics.wti, '#f87171')}</div><details class="macro-detail"><summary>Credit-spread diagnostic</summary>${macroMetricCard(metrics.credit_spread, '#fb7185')}</details>`;
  const holders = data.holders.holders;
  document.querySelector('#macroFiscalPane').innerHTML = `<div class="macro-section-heading"><div><h3>U.S. debt, fiscal flow, absorption &amp; foreign holders</h3><p>How the federal budget flows, who is absorbing Treasury supply, and whether major reported foreign holders are buying or selling.</p></div><span class="pill">TIC as of ${escapeHtml(data.holders.as_of)}</span></div><article id="fiscalFlowExhibit" class="fiscal-flow-exhibit" aria-live="polite"></article><div class="macro-chart-grid fiscal">${macroMetricCard(metrics.debt_held_public, '#38bdf8')}${macroMetricCard(metrics.fed_treasuries, '#a78bfa')}</div><div class="holder-layout"><article id="holderCountryChart" class="macro-chart-card"></article>${holderTable(holders)}</div><p class="custody-note">† ${escapeHtml(data.holders.methodology_warning)}</p>`;
  renderFiscalFlow();
  renderReserveShift();
  document.querySelectorAll('[data-holder-country]').forEach((button) => button.addEventListener('click', () => renderHolderCountry(button.dataset.holderCountry)));
  renderHolderCountry(activeHolderCountry && holders.some((holder) => holder.country === activeHolderCountry) ? activeHolderCountry : holders[0]?.country);

  const exchangeReserve = (macroSupplyData?.exchange_metrics ?? []).find((metric) => metric.key === 'exchange_reserve');
  const exchangeCards = exchangeReserve ? macroMetricCard(exchangeReserve, '#22d3ee', true) : '';
  const providerMessage = exchangeCards ? '' : `<article class="provider-card"><span>BTC on tracked exchanges</span><strong>Provider connection needed</strong><p>${escapeHtml(macroSupplyData?.status_message ?? 'Configure an approved labelled-address provider.')}</p><small>The dashboard pipeline is ready for Glassnode and keeps this absence isolated from the macro charts.</small></article>`;
  document.querySelector('#macroSupplyPane').innerHTML = `<div class="macro-section-heading"><div><h3>BTC on tracked exchanges</h3><p>Ten years of the Bitcoin balance held by exchange wallets identified by Coin Metrics.</p></div></div><div class="supply-warning">${escapeHtml(macroSupplyData?.warning ?? 'Exchange custody inventory is not equivalent to coins offered for sale.')}</div><div class="macro-chart-grid supply">${exchangeCards}${providerMessage}</div>`;

  const refreshWarnings = (data.refresh_errors ?? []).filter((warning) => !warning.startsWith('Glassnode exchange supply'));
  document.querySelector('#macroSources').innerHTML = `<p>${escapeHtml(data.methodology.warning)}</p><p><strong>Net liquidity:</strong> ${escapeHtml(data.methodology.net_liquidity_formula)}. <strong>Treasury countries:</strong> ${escapeHtml(data.methodology.country_warning)}</p><p><strong>Official sources:</strong> Federal Reserve/FRED, U.S. Treasury FiscalData, and Treasury International Capital. <strong>BTC exchange balance:</strong> Coin Metrics Community API, metric SplyExNtv.</p>${refreshWarnings.length ? `<p><strong>Refresh warnings:</strong> ${escapeHtml(refreshWarnings.join(' | '))}</p>` : ''}<p><strong>Cycle Signals:</strong> ISM is a manual snapshot; copper, gold and oil are market proxies; DVOL is from Deribit.</p>`;
}

function activateMacroTab(target, { scroll = false } = {}) {
  const button = document.querySelector(`[data-macro-tab="${target}"]`);
  if (!button) return;
  document.querySelectorAll('[data-macro-tab]').forEach((item) => {
    const active = item === button;
    item.classList.toggle('active', active);
    item.setAttribute('aria-selected', String(active));
  });
  const panes = { overview: 'macroOverviewPane', liquidity: 'macroLiquidityPane', fiscal: 'macroFiscalPane', reserves: 'macroReservesPane', policy: 'macroPolicyPane', supply: 'macroSupplyPane', cycle: 'macroCyclePane' };
  Object.entries(panes).forEach(([key, id]) => {
    const pane = document.querySelector(`#${id}`);
    pane.hidden = key !== target;
    pane.classList.toggle('active', key === target);
  });
  if (scroll) document.querySelector('#macroCyclePanel')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function setupMacroControls() {
  document.querySelectorAll('[data-macro-tab]').forEach((button) => {
    button.addEventListener('click', () => activateMacroTab(button.dataset.macroTab));
  });
  document.querySelectorAll('[data-macro-range]').forEach((button) => {
    button.addEventListener('click', () => {
      activeMacroRange = button.dataset.macroRange;
      document.querySelectorAll('[data-macro-range]').forEach((item) => item.classList.toggle('active', item === button));
      renderMacroWorkspace();
    });
  });
}

function renderAssetButtons(index) {
  document.querySelector('#globalAsOf').textContent = `Updated ${new Date(index.generated_at).toLocaleString()}`;
  document.querySelector('#assetButtons').innerHTML = index.assets.map((asset) => `
    <button class="asset-button" type="button" data-asset-id="${escapeHtml(asset.id)}">
      <strong>${escapeHtml(asset.symbol)}</strong>
      <span>${escapeHtml(asset.name)}</span>
      <small>${asset.category ? `${escapeHtml(asset.category)} · ` : ''}${fmtMoney(asset.latest.close)} · ${escapeHtml(asset.latest.zone)}</small>
    </button>
  `).join('');
  document.querySelectorAll('[data-asset-id]').forEach((button) => {
    button.addEventListener('click', () => selectAsset(button.dataset.assetId));
  });
  document.querySelector('#assetOverview').innerHTML = index.assets.map((asset) => `
    <article>
      <span>${escapeHtml(asset.name)}</span>
      <strong>${fmtMoney(asset.latest.close)}</strong>
      <small>${asset.category ? `${escapeHtml(asset.category)} · ` : ''}${escapeHtml(asset.regime.label)} · ${escapeHtml(asset.latest.date)}</small>
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
  const trendGap = Number.isFinite(Number(l.close)) && Number.isFinite(Number(l.trend)) && Number(l.trend) !== 0
    ? (Number(l.close) / Number(l.trend) - 1) * 100
    : null;
  const trendGapText = trendGap === null
    ? 'Distance from trend is unavailable.'
    : `${data.asset.name} is ${fmtNum(Math.abs(trendGap))}% ${trendGap < 0 ? 'below' : 'above'} the model trend, which indicates ${trendGap < 0 ? 'a discount to the long-cycle reference' : 'a premium to the long-cycle reference'}.`;
  const zDirection = Number(l.z_score) < 0 ? 'below' : Number(l.z_score) > 0 ? 'above' : 'at';
  const mvrvAvailable = l.latest_available_mvrv !== null && l.latest_available_mvrv !== undefined;
  const mvrvValue = mvrvAvailable ? Number(l.latest_available_mvrv) : null;
  document.querySelector('#status').innerHTML = [
    explainedStatusCard(data.asset.price_label, fmtMoney(l.close), {
      what: `The latest closing market price for ${data.asset.name}.`,
      why: 'It anchors every valuation band, moving average, and risk comparison shown below.',
      read: `As of ${l.date}, sourced from ${source}. Price alone does not show whether the asset is cheap or expensive.`,
    }),
    explainedStatusCard('Trend Fair Value', fmtMoney(l.trend), {
      what: 'The price implied by the dashboard’s long-term logarithmic regression trend.',
      why: 'It provides a cycle-scale reference that adjusts for compounding rather than treating every dollar move equally.',
      read: `${trendGapText} This is a model estimate, not a guaranteed destination.`,
    }),
    explainedStatusCard('Log Z-Score', fmtNum(l.z_score), {
      what: 'The logarithmic price gap from trend, measured in historical standard deviations.',
      why: 'It makes unusually cheap and unusually stretched conditions comparable across long market cycles.',
      read: `${data.asset.name} is ${fmtNum(Math.abs(Number(l.z_score)))} standard deviations ${zDirection} trend. Negative readings are cheaper; positive readings are more stretched.`,
    }, zClass),
    explainedStatusCard('MVRV', mvrvAvailable ? fmtNum(mvrvValue) : 'n/a', {
      what: 'Bitcoin market value divided by realized value—an estimate of the network’s aggregate on-chain cost basis.',
      why: 'Lower values imply less unrealized profit in the network; higher values imply more embedded profit and potential selling pressure.',
      read: mvrvAvailable
        ? `The latest available reading is ${fmtNum(mvrvValue)} as of ${l.latest_available_mvrv_date}; market value was about ${fmtNum((mvrvValue - 1) * 100)}% above realized value, or ${fmtNum(mvrvValue)} times estimated aggregate cost basis. That indicates aggregate unrealized profit, but not a cycle top by itself.`
        : 'This Bitcoin-specific on-chain measure is unavailable for the selected asset.',
    }),
    explainedStatusCard('Current Zone', l.zone, {
      what: 'A plain-language classification of the current log-regression valuation band.',
      why: 'It converts the statistical reading into a quick cycle-level description.',
      read: l.zone_note,
    }, zClass),
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
    ...priceTicks.map((tick) => `<g class="rainbow-grid"><line x1="${pad.left}" x2="${width - pad.right}" y1="${y(tick).toFixed(2)}" y2="${y(tick).toFixed(2)}" /><text x="${width - pad.right + 14}" y="${(y(tick) + 5).toFixed(2)}">${fmtMoney(tick)}</text></g>`),
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
  const confidence = Number(scenario.confidence ?? 0) * 100;
  const confidenceMeaning = confidence < 50 ? 'low conviction; competing paths remain plausible' : confidence < 70 ? 'moderate conviction; confirmation is still required' : 'higher conviction, but invalidation still controls risk';
  return `<p class="scenario-label">${escapeHtml(scenario.label)}</p><p>${escapeHtml(scenario.structure)}</p><dl class="scenario-grid"><dt>Current wave</dt><dd>${escapeHtml(scenario.current_wave ?? scenario.status)}</dd><dt>Confidence</dt><dd>${fmtNum(confidence)}% <small class="metric-context">${escapeHtml(confidenceMeaning)}</small></dd><dt>Invalidation</dt><dd>${fmtMoney(scenario.invalidation_level_usd)}</dd><dt>Confirmation</dt><dd>${fmtMoney(scenario.confirmation_level_usd)}</dd><dt>Targets</dt><dd>${targets || 'n/a'}</dd></dl><ul class="scenario-notes">${notes}</ul>`;
}

function renderElliottWave(data) {
  const wave = data.elliott_wave;
  const latest = data.latest;
  const primaryConfidence = Number(wave.primary.confidence) * 100;
  document.querySelector('#elliottSummary').innerHTML = [card('Wave Engine', wave.version, escapeHtml(wave.method)), card('Confluence Score', wave.confluence_score, 'Agreement across Fibonacci, RSI, log value, MVRV, and trend; near zero means mixed evidence.'), card('Primary Confidence', `${fmtNum(primaryConfidence)}%`, `${primaryConfidence < 50 ? 'Low conviction' : primaryConfidence < 70 ? 'Moderate conviction' : 'Higher conviction'} · ${escapeHtml(wave.primary.current_wave)}`), card('Primary Invalidation', fmtMoney(wave.primary.invalidation_level_usd), 'A close below this level weakens the main scenario and promotes the alternate.')].join('');
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
  document.querySelector('#elliottInterpretation').innerHTML = interpretationPanel({
    what: 'A rule-based map of large price pivots and possible wave scenarios.',
    why: 'It defines confirmation, invalidation, and risk levels, but does not measure whether Bitcoin is cheap or expensive.',
    read: `${wave.primary.current_wave ?? wave.primary.status}; primary confidence is ${fmtNum(primaryConfidence)}%, which is ${primaryConfidence < 50 ? 'low conviction because competing paths remain plausible' : primaryConfidence < 70 ? 'moderate conviction and still needs price confirmation' : 'higher conviction but still governed by the invalidation level'}. Invalidation is ${fmtMoney(wave.primary.invalidation_level_usd)}.`,
    method: 'Not scored: Elliott scenarios describe market structure, so forcing them onto a valuation scale would create false precision.',
  });
  document.querySelector('#elliottPrimary').innerHTML = renderScenario(wave.primary);
  document.querySelector('#elliottAlternate').innerHTML = renderScenario(wave.alternate);
  document.querySelector('#elliottConfluence').innerHTML = Object.entries(wave.phase2_confluence).map(([name, item]) => `<div class="component"><strong>${escapeHtml(name.replaceAll('_', ' '))}</strong><span>${item.score > 0 ? '+' : ''}${item.score}</span><small>${escapeHtml(item.detail)}</small></div>`).join('');
  document.querySelector('#elliottManual').innerHTML = `<p><strong>Status:</strong> ${escapeHtml(data.manual_thesis?.manual_elliott_wave_count?.status ?? 'Manual override available')}</p><p class="muted">Manual thesis files can be added under <code>data/manual/</code>. For now, algorithmic scenarios are clearly labeled as candidates.</p><ul class="scenario-notes">${(wave.limitations ?? []).map((n) => `<li>${escapeHtml(n)}</li>`).join('')}</ul>`;
}

function movingAverageScore(latest) {
  const averages = [latest.ma_50d, latest.ma_100d, latest.ma_200d, latest.ma_200w]
    .map(Number)
    .filter((value) => Number.isFinite(value) && value > 0);
  if (!isPositiveFinite(latest.close) || !averages.length) return null;
  const meanLogDistance = averages.reduce((sum, average) => sum + Math.log(Number(latest.close) / average), 0) / averages.length;
  return clampScore(meanLogDistance / 0.15);
}

function renderChartInterpretations(data) {
  const latest = data.latest;
  document.querySelector('#logInterpretation').innerHTML = interpretationPanel({
    score: latest.z_score,
    what: 'Price relative to a long-term logarithmic trend and its historical deviation bands.',
    why: 'It provides cycle valuation context across assets whose prices compound over long periods.',
    read: `${data.asset.name} is ${fmtNum(latest.z_score)} standard deviations from log trend and is classified as ${latest.zone}.`,
    method: 'Direct log-regression z-score, capped visually at −2 to +2.',
  });

  const maValues = [latest.ma_50d, latest.ma_100d, latest.ma_200d, latest.ma_200w].filter(isPositiveFinite);
  const aboveCount = maValues.filter((average) => Number(latest.close) >= Number(average)).length;
  document.querySelector('#movingAverageInterpretation').innerHTML = interpretationPanel({
    score: movingAverageScore(latest),
    what: 'Price against the 50-day, 100-day, 200-day, and 200-week trend averages.',
    why: 'The averages show whether short-, medium-, and long-cycle momentum agree or conflict.',
    read: `${data.asset.name} is above ${aboveCount} of ${maValues.length} available key averages. Mixed placement calls for smaller steps rather than an all-or-nothing decision.`,
    method: 'Average logarithmic distance from the available key averages; approximately 15% distance equals one scale point.',
  });

  document.querySelector('#rainbowInterpretation').innerHTML = interpretationPanel({
    score: latest.z_score,
    what: 'Price inside historical power-law residual bands on a logarithmic scale.',
    why: 'It turns long-run compounding into intuitive valuation zones while preserving cycle context.',
    read: `${data.asset.name} is in the ${data.rainbow.latest.zone} band; the standardized log-trend reading is ${fmtNum(latest.z_score)}.`,
    method: 'Uses the same log-regression z-score as the common scale; rainbow colors remain a separate historical visualization.',
  });
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
  const drawdown = Number(l.drawdown_from_ath_pct);
  const drawdownMeaning = drawdown <= -50 ? 'major cycle reset; price has lost at least half its peak value' : drawdown <= -30 ? 'substantial reset from the peak' : drawdown <= -15 ? 'meaningful pullback from the peak' : 'close to the prior peak';
  const rsi = Number(l.rsi_14d);
  const rsiMeaning = rsi <= 30 ? 'oversold zone; selling has been unusually strong' : rsi >= 70 ? 'overbought zone; buying has been unusually strong' : 'neutral momentum; neither the 30 oversold nor 70 overbought threshold is active';
  document.querySelector('#currentRead').innerHTML = `<p class="zone ${zoneClass(l.zone)}">${escapeHtml(l.zone)}</p><p>${escapeHtml(l.zone_note)}</p><dl><dt>-2σ deep value band</dt><dd>${fmtMoney(l.band_minus_2)}</dd><dt>-1.5σ accumulation band</dt><dd>${fmtMoney(l.band_minus_1_5)}</dd><dt>+2σ take-chips band</dt><dd>${fmtMoney(l.band_plus_2)}</dd><dt>Drawdown from ATH</dt><dd>${fmtNum(drawdown)}% <small class="metric-context">${escapeHtml(drawdownMeaning)}</small></dd><dt>RSI 14D</dt><dd>${fmtNum(rsi)} <small class="metric-context">${escapeHtml(rsiMeaning)}</small></dd><dt>MVRV</dt><dd>${l.latest_available_mvrv ? `${fmtNum(l.latest_available_mvrv)} <small class="metric-context">1.0 means market value equals estimated aggregate cost basis · as of ${escapeHtml(l.latest_available_mvrv_date)}</small>` : 'n/a'}</dd><dt>50D moving average</dt><dd>${fmtMoney(l.ma_50d)}</dd><dt>100D moving average</dt><dd>${fmtMoney(l.ma_100d)}</dd><dt>200D moving average</dt><dd>${fmtMoney(l.ma_200d)}</dd><dt>200W moving average</dt><dd>${fmtMoney(l.ma_200w)}</dd></dl>`;
  document.querySelector('#manual').innerHTML = `<p><strong>Source:</strong> ${escapeHtml(data.source?.source ?? 'market feed')}</p><p><strong>Provenance:</strong> ${escapeHtml(data.source?.provenance ?? 'n/a')}</p><p><strong>Symbol:</strong> ${escapeHtml(data.asset.symbol)}</p><p><strong>Rows:</strong> ${escapeHtml(data.source?.rows ?? data.points.length)}</p><p class="muted">${escapeHtml(data.source?.limitation ?? 'No limitations recorded.')}</p>`;
}

function renderAll(data) {
  renderStatus(data);
  renderMacroWorkspace();
  renderLogChart(data);
  if (!document.querySelector('#movingAveragePane').hidden) renderMovingAverageChart(data);
  renderRainbowChart(data);
  renderElliottWave(data);
  renderChartInterpretations(data);
  renderReadouts(data);
}

async function main() {
  const [res, macroRes, macroDashboardRes, macroSupplyRes, fiscalFlowRes, reserveShiftRes] = await Promise.all([
    fetch('/public/data/assets.json', { cache: 'no-store' }),
    fetch('/public/data/macro-cycle.json', { cache: 'no-store' }),
    fetch('/public/data/btc-macro.json', { cache: 'no-store' }),
    fetch('/public/data/btc-market-supply.json', { cache: 'no-store' }),
    fetch('/public/data/fiscal-flow.json', { cache: 'no-store' }),
    fetch('/public/data/reserve-shift.json', { cache: 'no-store' }),
  ]);
  if (!res.ok) throw new Error(`Asset index fetch failed: ${res.status}`);
  dashboardIndex = await res.json();
  macroData = macroRes.ok ? await macroRes.json() : null;
  macroDashboardData = macroDashboardRes.ok ? await macroDashboardRes.json() : null;
  macroSupplyData = macroSupplyRes.ok ? await macroSupplyRes.json() : null;
  fiscalFlowData = fiscalFlowRes.ok ? await fiscalFlowRes.json() : null;
  reserveShiftData = reserveShiftRes.ok ? await reserveShiftRes.json() : null;
  renderAssetButtons(dashboardIndex);
  void mountMarketSizes(dashboardIndex);
  setupTabs();
  setupMacroControls();
  await selectAsset(dashboardIndex.assets[0].id);
  if (window.location.hash === '#reserve-shift') activateMacroTab('reserves', { scroll: true });
  if (window.location.hash === '#policy-adoption') activateMacroTab('policy', { scroll: true });
  window.addEventListener('hashchange', () => {
    if (window.location.hash === '#reserve-shift') activateMacroTab('reserves', { scroll: true });
    if (window.location.hash === '#policy-adoption') activateMacroTab('policy', { scroll: true });
  });
  window.addEventListener('resize', () => {
    if (!document.querySelector('#logPane').hidden) logChart?.applyOptions({ width: document.querySelector('#logChart').clientWidth });
    if (!document.querySelector('#movingAveragePane').hidden) movingAverageChart?.applyOptions({ width: document.querySelector('#movingAverageChart').clientWidth });
  });
}

main().catch((err) => {
  document.body.innerHTML = `<main class="panel error"><h1>Dashboard failed to load</h1><pre>${escapeHtml(err.stack || err.message)}</pre></main>`;
});
