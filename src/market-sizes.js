const compactUSD = new Intl.NumberFormat('en-US', {
  style: 'currency', currency: 'USD', notation: 'compact', minimumFractionDigits: 0, maximumFractionDigits: 2,
});

export function formatMarketSize(value) {
  return typeof value === 'number' && Number.isFinite(value) && value > 0 ? compactUSD.format(value) : 'Unavailable';
}

function dateLabel(row) {
  if (row.as_of) return `As of ${row.as_of}`;
  if (row.observed_on) return `Checked ${row.observed_on}`;
  return 'No verified date';
}

function safeLink(url, label) {
  const link = document.createElement('a');
  if (!/^https:\/\//.test(url || '')) return document.createTextNode(label);
  link.href = url;
  link.textContent = label;
  link.target = '_blank';
  link.rel = 'noopener noreferrer';
  return link;
}

function sizeLine(row) {
  const line = document.createElement('span');
  line.className = 'asset-market-size';
  const label = document.createElement('span');
  label.textContent = `${row.label || 'Market cap'} `;
  const value = document.createElement('b');
  value.textContent = `${row.estimated && row.value_usd > 0 ? '≈' : ''}${formatMarketSize(row.value_usd)}`;
  line.append(label, value);
  line.title = `${row.method || 'No verified market-size observation.'} ${dateLabel(row)}. Source: ${row.source || 'unavailable'}.`;
  return line;
}

function notesPanel(assets, records) {
  const details = document.createElement('details');
  details.className = 'market-size-notes';
  const summary = document.createElement('summary');
  summary.textContent = 'Market size: definitions, dates & sources';
  const intro = document.createElement('p');
  intro.textContent = 'USD · T = trillion · B = billion · M = million. These are size measures, not buy/sell signals or money available to invest. Metals use estimated entire above-ground stocks, not ETF assets. The GLD and SLV chart prices are ETF share prices; metal values use separate spot prices per ounce. *Tracked index caps have incomplete coverage. Measures overlap and should not be added together.';
  const list = document.createElement('div');
  list.className = 'market-size-note-grid';
  for (const asset of assets) {
    const row = records[asset.id] || {};
    const article = document.createElement('article');
    const heading = document.createElement('h3');
    heading.textContent = `${asset.name} — ${row.label || 'Market cap'}`;
    const description = document.createElement('p');
    description.textContent = `${formatMarketSize(row.value_usd)} · ${dateLabel(row)}. ${row.method || 'No verified value available.'}`;
    const cadence = document.createElement('p');
    cadence.textContent = `${row.stock_as_of ? `Stock estimate: ${row.stock_as_of}. ` : ''}${row.price_usd_per_oz ? `Spot: $${row.price_usd_per_oz.toFixed(2)} per troy ounce. ` : ''}Updates: ${row.refresh_mode || 'unavailable'}.${row.status?.includes('failed') ? ' Latest refresh failed; previous value and original date retained.' : ''}`;
    article.append(heading, description, cadence, safeLink(row.source_url, row.source || 'Source unavailable'));
    if (row.price_source_url) article.append(document.createTextNode(' · '), safeLink(row.price_source_url, 'Spot price source'));
    list.append(article);
  }
  details.append(summary, intro, list);
  return details;
}

export async function mountMarketSizes(index) {
  if (!document.querySelector('link[data-market-sizes]')) {
    const style = document.createElement('link');
    style.rel = 'stylesheet';
    style.href = '/src/market-sizes.css?v=1';
    style.dataset.marketSizes = 'true';
    document.head.append(style);
  }
  let records = {};
  try {
    const response = await fetch('/public/data/market-sizes.json', { cache: 'no-store' });
    if (!response.ok) throw new Error('Market sizes unavailable');
    records = (await response.json()).assets || {};
  } catch (error) {
    console.warn('Market-size data unavailable; price charts remain available.');
  }
  for (const button of document.querySelectorAll('#assetButtons [data-asset-id]')) {
    button.querySelectorAll('.asset-market-size, .asset-market-size-date').forEach(node => node.remove());
    const row = records[button.dataset.assetId] || {};
    const date = document.createElement('span');
    date.className = 'asset-market-size-date';
    const dated = Date.parse(row.as_of || row.observed_on || '');
    const older = Number.isFinite(dated) && Date.now() - dated > 7 * 86400000;
    date.textContent = `${dateLabel(row)}${older ? ' · older data' : ''}${row.status?.includes('failed') ? ' · retained' : ''}`;
    button.append(sizeLine(row), date);
  }
  document.querySelector('.market-size-notes')?.remove();
  document.querySelector('#assetButtons')?.after(notesPanel(index.assets, records));
}
