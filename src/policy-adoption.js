const escapePolicy = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const displayDate = value => new Date(`${value}T12:00:00Z`).toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric',timeZone:'UTC'});

function renderArmaTracker(tracker) {
  if (!tracker) return '';
  return `<section id="arma-progress" class="clarity-tracker arma-tracker" aria-labelledby="arma-title">
    <div class="policy-section-heading"><div><p class="eyebrow">Legislative path · ${escapePolicy(tracker.bill)}</p><h4 id="arma-title">${escapePolicy(tracker.title)}</h4></div><span>Impact and legal status are separate</span></div>
    <ol>${tracker.stages.map(stage=>`<li class="${escapePolicy(stage.state)}"><i aria-hidden="true"></i><strong>${escapePolicy(stage.label)}</strong><span>${stage.date?displayDate(stage.date):'Pending'}</span></li>`).join('')}</ol>
    <div class="arma-context"><p><strong>Latest verified action:</strong> ${escapePolicy(tracker.status)}. <span>Checked ${displayDate(tracker.checked_on)}.</span></p><p>${escapePolicy(tracker.summary)}</p><p><strong>Bitcoin context:</strong> ${escapePolicy(tracker.impact)}</p><p><strong>Next to watch:</strong> ${escapePolicy(tracker.next_step)}</p></div>
    <details><summary>Official sources &amp; verification notes</summary><p>${escapePolicy(tracker.verification_note)}</p><p><a href="${escapePolicy(tracker.source_url)}" target="_blank" rel="noreferrer">GovInfo — official bill record ↗</a> · <a href="${escapePolicy(tracker.actions_url)}" target="_blank" rel="noreferrer">Congress.gov — latest actions ↗</a></p></details>
  </section>`;
}

export async function mountPolicyAdoption(target) {
  if (!target || target.dataset.policyMounted) return;
  target.dataset.policyMounted = 'loading';
  target.innerHTML = '<p>Loading verified policy evidence…</p>';
  try {
    const response = await fetch('/public/data/policy-adoption.json?v=arma-progress-v1',{cache:'no-store'});
    if(!response.ok) throw new Error('Policy snapshot unavailable');
    const data = await response.json();
    const sources = Object.fromEntries(data.sources.map(source => [source.id,source]));
    target.innerHTML = `<section id="policy-adoption" class="policy-adoption">
      <header class="policy-header"><div><p class="eyebrow">Policy &amp; sovereign adoption</p><h3>Verified institutional milestones</h3><p>Central-bank adoption, U.S. market-structure legislation and the U.S. government Bitcoin reserve—tracked separately.</p></div><span>Checked ${displayDate(data.as_of)}</span></header>
      <div class="policy-cards">${data.cards.map(card=>`<article class="policy-card ${escapePolicy(card.impact)}"><span>${escapePolicy(card.eyebrow)}</span><strong>${escapePolicy(card.status)}</strong><p>${escapePolicy(card.detail)}</p><small>${escapePolicy(card.note)}</small><em>${escapePolicy(card.confidence)}</em></article>`).join('')}</div>
      <section class="clarity-tracker" aria-labelledby="clarity-title"><div class="policy-section-heading"><div><p class="eyebrow">Legislative path</p><h4 id="clarity-title">CLARITY Act progress</h4></div><span>Impact and legal status are separate</span></div><ol>${data.clarity_stages.map(stage=>`<li class="${escapePolicy(stage.state)}"><i aria-hidden="true"></i><strong>${escapePolicy(stage.label)}</strong><span>${stage.date?displayDate(stage.date):'Pending'}</span></li>`).join('')}</ol></section>
      ${renderArmaTracker(data.arma_tracker)}
      <div class="policy-body"><section><div class="policy-section-heading"><div><p class="eyebrow">Evidence timeline</p><h4>What changed—and why it matters</h4></div></div><div class="policy-filters" role="group" aria-label="Filter policy evidence"><button class="active" type="button" data-policy-filter="all">All</button><button type="button" data-policy-filter="Central banks">Central banks</button><button type="button" data-policy-filter="CLARITY Act">CLARITY Act</button><button type="button" data-policy-filter="U.S. reserve">U.S. reserve</button></div><div class="policy-timeline">${data.events.slice().reverse().map(event=>{const source=sources[event.source_id];return `<article data-policy-lane="${escapePolicy(event.lane)}"><time datetime="${escapePolicy(event.date)}">${displayDate(event.date)}</time><div><span class="policy-lane">${escapePolicy(event.lane)}</span><h5>${escapePolicy(event.headline)}</h5><div class="policy-badges"><span>${escapePolicy(event.status)}</span><span class="impact ${escapePolicy(event.impact)}">${escapePolicy(event.impact)} for Bitcoin</span><span>Official source</span></div><p><b>What changed:</b> ${escapePolicy(event.change)}</p><p><b>Why it matters:</b> ${escapePolicy(event.why)}</p><a href="${escapePolicy(source.url)}" target="_blank" rel="noreferrer">${escapePolicy(source.label)} ↗</a></div></article>`}).join('')}</div></section>
      <aside><div class="policy-section-heading"><div><p class="eyebrow">Central-bank watch</p><h4>Verified positions</h4></div></div>${data.central_banks.map(bank=>{const source=sources[bank.source_id];return `<article class="bank-position"><div><strong>${escapePolicy(bank.jurisdiction)}</strong><span class="impact ${escapePolicy(bank.impact)}">${escapePolicy(bank.stage)}</span></div><p>${escapePolicy(bank.institution)}</p><dl><dt>Reserve status</dt><dd>${escapePolicy(bank.reserve_status)}</dd><dt>As of</dt><dd>${displayDate(bank.as_of)}</dd></dl><small>${escapePolicy(bank.summary)}</small><a href="${escapePolicy(source.url)}" target="_blank" rel="noreferrer">Official source ↗</a></article>`}).join('')}<div class="policy-guardrail"><strong>Classification guardrail</strong><p>A proposal is not adoption. A pilot outside reserves is not a reserve allocation. U.S. government holdings are not Federal Reserve holdings.</p></div></aside></div>
      <details><summary>Methodology, sources and limitations</summary><p>${escapePolicy(data.methodology)}</p><p>This is a dated research snapshot, not a comprehensive global register. “Public balance unavailable” means the cited primary sources do not provide a current fully reconciled Bitcoin balance.</p><p>${data.sources.map(source=>`<a href="${escapePolicy(source.url)}" target="_blank" rel="noreferrer">${escapePolicy(source.label)}</a>`).join(' · ')}</p></details>
    </section>`;
    target.querySelectorAll('[data-policy-filter]').forEach(button=>button.addEventListener('click',()=>{
      target.querySelectorAll('[data-policy-filter]').forEach(item=>item.classList.toggle('active',item===button));
      target.querySelectorAll('[data-policy-lane]').forEach(item=>{item.hidden=button.dataset.policyFilter!=='all'&&item.dataset.policyLane!==button.dataset.policyFilter;});
    }));
    target.dataset.policyMounted='ready';
  } catch(error) {
    target.innerHTML='<p>Policy evidence could not load. The other dashboard sections are unchanged.</p>';
    delete target.dataset.policyMounted;
    console.error('Policy adoption:',error);
  }
}
