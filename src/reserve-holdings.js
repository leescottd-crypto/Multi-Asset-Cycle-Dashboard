const esc = s => String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct = n => `${n.toFixed(n < 1 ? 3 : 1)}%`;
const usd = n => n >= 1e6 ? `$${(n/1e6).toFixed(2)}T` : `$${(n/1e3).toFixed(2)}B`;
const quarter = d => `Q${Math.ceil(Number(d.slice(5,7))/3)} ${d.slice(0,4)}`;

export async function mountReserveHoldings(target) {
  if (!target || target.dataset.reserveMounted) return;
  target.dataset.reserveMounted = 'loading';
  target.innerHTML = '<p>Loading dated reserve holdings…</p>';
  try {
    const response = await fetch('/public/data/reserve-holdings.json',{cache:'no-store'});
    if (!response.ok) throw new Error('Snapshot unavailable');
    const data = await response.json(), latest = data.series.at(-1);
    const defs = [
      {key:'treasuries',label:'U.S. Treasuries',color:'#b9c9cc',style:0,note:'Foreign official-sector holdings'},
      {key:'gold',label:'Gold',color:'#dba347',style:0,note:'World official monetary gold'},
      {key:'bitcoin',label:'Bitcoin*',color:'#86b99b',style:2,note:'Four tracked governments · incomplete'},
    ];
    target.innerHTML = `<section class="reserve-holdings"><header><div><p class="eyebrow">Reserve shift</p><h3>Treasuries, gold &amp; government Bitcoin</h3><p>Quarter-end holdings relative to world official reserves. Bitcoin* is a size comparison, not an official reserve share.</p></div><span>Through ${quarter(data.as_of)}</span></header>
      <div class="reserve-holdings-values">${defs.map(d=>`<div><span style="color:${d.color}">${d.label}</span><strong>${latest[d.key+'_pct'] === null ? 'Not reported' : pct(latest[d.key+'_pct'])}</strong><span>${latest[d.key+'_usd_m'] === null ? '' : usd(latest[d.key+'_usd_m'])} · ${quarter(latest.date)}</span><small>${d.note}</small></div>`).join('')}</div>
      <div class="reserve-holdings-chart" role="img" aria-label="Three-line reserve comparison: U.S. Treasuries, gold and a limited government Bitcoin sample"></div>
      <p class="reserve-holdings-cursor" aria-live="polite">Move over the chart to inspect a quarter. Drag or zoom to explore.</p>
      <div class="reserve-holdings-explanation"><div><h4>What it shows</h4><p>How large these holdings are relative to the same world reserve total. A value of 25% means holdings worth one quarter of that total. Other reserve assets are omitted; the lines do not add to 100%.</p></div><div><h4>How to read it</h4><p>Rising lines can reflect purchases, higher prices or a smaller denominator. Falling Treasury share alone does not prove selling. Bitcoin uses the same scale and has not been enlarged.</p></div><div><h4>Bitcoin context</h4><p>Diversification is long-term context, not proof that money leaving Treasuries enters Bitcoin. Use alongside valuation and liquidity evidence, not as a stand-alone trade signal. Line colours identify assets, not recommendations.</p></div></div>
      <details><summary>Coverage, sources &amp; update dates</summary><p>${esc(data.methodology)}</p><p>${esc(data.bitcoin_note)}</p><p>Earlier Bitcoin history is missing, not zero. Provider balances are carried between reports; values include price movements.</p><p>Gold workbook: ${esc(data.gold_source_file)}. Latest common quarter: ${quarter(data.as_of)}. Source check: ${esc(data.checked_at.slice(0,10))}.</p><p>${esc(data.refresh_note)}</p><p>${data.sources.map(s=>`<a href="${esc(s.url)}" target="_blank" rel="noreferrer">${esc(s.label)}</a>`).join(' · ')}</p></details></section>`;
    const coverageNote=document.createElement('p');
    coverageNote.textContent=`History: ${quarter(data.series[0].date)}–${quarter(data.as_of)}. Treasury benchmark and reporting changes can create breaks; these are not necessarily buying or selling.`;
    target.querySelector('.reserve-holdings-chart').before(coverageNote);
    if(data.treasury_history_note){
      const note=document.createElement('p');
      note.textContent=data.treasury_history_note;
      target.querySelector('details').append(note);
    }
    const chart = LightweightCharts.createChart(target.querySelector('.reserve-holdings-chart'),{
      autoSize:true,height:440,layout:{background:{type:'solid',color:'#07191d'},textColor:'#e5ddc9',fontSize:13},
      grid:{vertLines:{visible:false},horzLines:{color:'#253b3d'}},
      rightPriceScale:{borderColor:'#52625e',minimumWidth:135,scaleMargins:{top:0.1,bottom:0.06}},
      timeScale:{borderColor:'#52625e',timeVisible:false,rightOffset:2},localization:{priceFormatter:pct},
    });
    for (const d of defs) {
      const line = chart.addLineSeries({title:d.label,color:d.color,lineWidth:2,lineStyle:d.style,priceLineVisible:false,lastValueVisible:true,
        priceFormat:{type:'custom',formatter:pct,minMove:0.001},
        autoscaleInfoProvider:original=>{const range=original();if(range) range.priceRange.minValue=0;return range;}});
      line.setData(data.series.filter(r=>r[d.key+'_pct'] !== null).map(r=>({time:r.date,value:r[d.key+'_pct']})));
    }
    chart.timeScale().fitContent();
    // A hidden tab starts with zero width. Fit once it has its actual layout.
    const initialFit = new ResizeObserver(entries=>{
      const width=entries[0]?.contentRect.width;
      if(width>0){
        requestAnimationFrame(()=>{chart.resize(width,440);chart.timeScale().fitContent();});
        initialFit.disconnect();
      }
    });
    initialFit.observe(target.querySelector('.reserve-holdings-chart'));
    chart.subscribeCrosshairMove(event=>{
      const time=event.time;
      const date=typeof time==='string' ? time : time && typeof time==='object' ? `${time.year}-${String(time.month).padStart(2,'0')}-${String(time.day).padStart(2,'0')}` : null;
      const row=data.series.find(r=>r.date===date); if(!row) return;
      target.querySelector('.reserve-holdings-cursor').textContent = `${quarter(row.date)} — ` + defs.map(d=>`${d.label}: ${row[d.key+'_pct'] === null ? 'not reported' : pct(row[d.key+'_pct'])+' ('+usd(row[d.key+'_usd_m'])+')'}`).join(' · ');
    });
    document.addEventListener('click',event=>{
      const button=event.target.closest?.('[data-macro-range]'); if(!button) return;
      const years=parseInt(button.dataset.macroRange,10);
      if(!Number.isFinite(years)){chart.timeScale().fitContent();return;}
      const from=`${Number(data.as_of.slice(0,4))-years}${data.as_of.slice(4)}`;
      chart.timeScale().setVisibleRange({from:from<data.series[0].date?data.series[0].date:from,to:data.as_of});
    });
    target.dataset.reserveMounted='ready';
  } catch(error) {
    target.innerHTML='<p>Reserve holdings could not load. The other sections are unchanged. Reload to retry.</p>';
    delete target.dataset.reserveMounted;
    console.error('Reserve holdings:',error);
  }
}
