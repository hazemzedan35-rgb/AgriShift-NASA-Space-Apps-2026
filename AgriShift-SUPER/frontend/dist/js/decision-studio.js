'use strict';
/*
 * AgriShift frontend-only controller.
 * Talks to the existing MVP API; never computes agricultural recommendations.
 * Saved example is explicitly identified as an offline reference, not a live analysis.
 */
(() => {
  const $ = (selector, root=document) => root.querySelector(selector);
  const state = {result:null,mode:null,requestId:0,controller:null,selected:new Set(),health:false};
  const form = $('#farmForm');
  const formKeys = ['latitude','longitude','planning_seasons','first_winter_year','area_ha','water_budget_m3','irrigation_efficiency','previous_crop','priority','soil_type','soil_awc_mm_per_m','soil_ece_ds_m','soil_ph','soil_drainage','calendar_zone'];
  const numericKeys = ['latitude','longitude','planning_seasons','area_ha','water_budget_m3','irrigation_efficiency'];
  const money = value => Number.isFinite(Number(value)) ? Number(value).toLocaleString('en-US',{maximumFractionDigits:1}) : '—';
  const short = value => Number.isFinite(Number(value)) ? Number(value).toLocaleString('en-US',{maximumFractionDigits:0}) : '—';
  const text = value => value===null || value===undefined || value==='' ? '—' : String(value);
  const node = (tag, className, content) => {
    const element=document.createElement(tag);
    if(className) element.className=className;
    if(content!==undefined) element.textContent=String(content);
    return element;
  };
  function status(message,kind=''){
    const e=$('#feedback');e.textContent=message;e.className='form-feedback'+(kind?' '+kind:'');
  }
  function banner(message,kind=''){
    const e=$('#resultsState');e.hidden=!message;
    e.className='results-state'+(kind?' '+kind:'');
    e.textContent=message||'';
  }
  function setServerStatus(mode){
    const el=$('#serverState');
    el.className='server-state '+(mode?'online':'offline');
    el.lastChild.textContent=mode?' API connected':' API unavailable';
    state.health=mode;
  }
  function getInputs(){
    const data=new FormData(form);
    const result={};
    formKeys.forEach(k=>result[k]=numericKeys.includes(k)?Number(data.get(k)):data.get(k));
    for(const k of ['first_winter_year','soil_awc_mm_per_m','soil_ece_ds_m','soil_ph','soil_ph']){
      result[k]=data.get(k)===''?null:Number(data.get(k));
    }
    result.allowed_crops=[...form.querySelectorAll('input[name="allowed_crops"]:checked')].map(el=>el.value);
    return result;
  }
  function populateInputs(data){
    for(const key of formKeys){
      const field=form.elements.namedItem(key);
      if(field&&data[key]!==undefined&&data[key]!==null)field.value=data[key];
      if(field&&data[key]===null)field.value='';
    }
    if(Array.isArray(data.allowed_crops)){
      form.querySelectorAll('input[name="allowed_crops"]').forEach(el=>{el.checked=data.allowed_crops.includes(el.value)});
    }
  }
  async function requestJson(url, options={}){
    const controller = new AbortController();
    const timeout=setTimeout(()=>controller.abort('timeout'),140000);
    if(options.signal){
      if(options.signal.aborted) controller.abort();
      else options.signal.addEventListener('abort',()=>controller.abort(),{once:true});
    }
    try{
      const response=await fetch(url,{...options,signal:controller.signal,cache:'no-store'});
      if(!response.ok){
        let message=`HTTP ${response.status}`;
        try{
          const error=await response.json();
          if(typeof error.detail==='string')message=error.detail;
          else if(Array.isArray(error.detail))message=error.detail.map(item=>item.msg||'Invalid input').join('; ').slice(0,280);
        }catch{}
        throw new Error(message);
      }
      const type=response.headers.get('content-type')||'';
      if(!type.includes('application/json'))throw new Error('Server did not return JSON. Check the API configuration.');
      return response.json();
    }finally{clearTimeout(timeout)}
  }
  function validResult(data){
    return data&&typeof data==='object'&&Array.isArray(data.plans)&&data.inputs&&data.climate;
  }
  function stopCurrentRequest(){
    state.requestId++;
    if(state.controller){state.controller.abort();state.controller=null;}
    $('#analyzeBtn').disabled=false;
    $('#analyzeBtn').textContent='Analyze rotation plans ↗';
  }
  function clearResult(reason){
    stopCurrentRequest();
    state.result=null;state.mode=null;state.selected.clear();
    renderSoil(null);
    $('#exportBtn').disabled=true;$('#resultHighlights').hidden=true;
    $('#resultSummary').textContent='Run an analysis to see candidate rotation plans.';
    $('#scenarioList').replaceChildren();
    const empty=node('div','empty-panel');
    empty.append(node('span','empty-icon','♧'),node('h3','',reason?'Inputs changed — rerun your analysis':'Your rotation comparison starts here'),node('p','',reason?'Previous results were cleared so they cannot be mistaken for results from your new inputs.':'Run an analysis to compare modeled water demand, budget status and crop-family trade-offs.'));
    $('#scenarioList').append(empty);
    $('#comparisonSection').hidden=true;
    $('#rankingNotice').textContent='This screen is a research demonstration, not agricultural guidance.';
    banner(reason?'Inputs have changed. Run a new analysis to update the results.':'');
    if(reason)renderSource(null,'');
  }
  function setClimate(climate,days){
    if(!climate||typeof climate!=='object')return;
    $('#temperature').textContent=money(climate.average_air_temperature_c);
    $('#rainfall').textContent=money(climate.annual_rain_mm);
    $('#et0annual').textContent=money(climate.annual_reference_et0_mm);
    $('#coverageDays').textContent=Number.isFinite(Number(days))?short(days):'365';
  }
  function renderMonthly(data){
    const target=$('#etoChart');target.replaceChildren();
    const months=Array.isArray(data?.months)?data.months:[];
    const values=months.map(row=>Number(row.daily_mean_mm));
    if(months.length!==12||values.some(x=>!Number.isFinite(x)||x<0)){
      target.append(node('div','chart-placeholder','Monthly ET₀ data are unavailable or incomplete.'));
      return;
    }
    const grid=node('div','chart-grid');
    const gridLines=node('div','chart-lines');
    const ymax=Math.max(1,Math.ceil(Math.max(...values)));
    for(let k=4;k>=0;k--){
      const l=node('span');l.append(node('i','',`${(ymax*k/4).toFixed(1)}`));gridLines.append(l);
    }
    const columns=node('div','bar-columns');
    const labels=node('div','chart-months');
    for(let i=0;i<12;i++){
      const label=months[i].month.slice(-2);
      const name=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][Math.max(0,Number(label)-1)]||label;
      const wrap=node('div','chart-bar-group');
      const bar=node('div','chart-bar');
      bar.style.height=`${Math.max(1,Math.min(100,values[i]/ymax*100))}%`;
      bar.tabIndex=0;
      bar.setAttribute('role','img');
      bar.setAttribute('aria-label',`${name} 2025: ${values[i].toFixed(2)} millimeters per day`);
      bar.title=`${name}: ${values[i].toFixed(2)} mm/day`;
      wrap.append(bar);columns.append(wrap);
      labels.append(node('span','',name));
    }
    grid.append(gridLines,columns,labels);target.append(grid);
  }
  function renderSoil(data){
    const outer=$('#soilInsight'),statusNode=$('#soilStatus'),details=$('#soilEvidenceText');
    if(!outer || !statusNode || !details)return;
    if(!data || typeof data!=='object'){
      outer.hidden=true;return;
    }
    outer.hidden=false;
    const awc=data.awc||{};
    const awcKnown=Number.isFinite(Number(awc.value_mm_per_m));
    const salinityKnown=Number.isFinite(Number(data.ece_ds_m)) && data.ece_ds_m !== null;
    statusNode.textContent=salinityKnown?'Soil ECe provided — provisional screen':'Soil ECe unknown — no salinity verdict';
    const sentences=[];
    if(awcKnown){
      sentences.push(`AWC: ${money(awc.value_mm_per_m)} mm/m (${text(awc.source_kind)}; not soil moisture).`);
    } else sentences.push('AWC: unknown; no field moisture has been measured.');
    if(salinityKnown){
      sentences.push(`Farmer-entered soil ECe: ${money(data.ece_ds_m)} dS/m. This number is not independently verified.`);
    } else sentences.push('Soil salinity: not tested. Unknown does not mean safe.');
    sentences.push('Crop-screening thresholds are indicative FAO-56 references only, not field-verified yield or irrigation advice.');
    details.textContent=sentences.join(' ');
  }
  function renderSource(climate,mode){
    const el=$('#sourceEvidence');if(!el)return;
    if(!climate){el.textContent='No climate analysis is available for the selected farm coordinates.';return;}
    const lat=climate.latitude,lon=climate.longitude;
    el.textContent=`${mode==='preview'?'SAVED DEMO':'HISTORICAL NASA POWER'} · ${lat}°, ${lon}° · ${climate.year||2025} · ${climate.source||'NASA POWER and FAO-56'} · Historical analogue, not a forecast or measured farm soil.`;
  }
  function getBudget(result){
    const b=Number(result?.inputs?.water_budget_m3);
    return Number.isFinite(b)&&b>=0?b:NaN;
  }
  function withinBudget(plan,budget){
    if(typeof plan.within_total_budget==='boolean')return plan.within_total_budget;
    return Number.isFinite(Number(plan.water_proxy_m3))&&Number(plan.water_proxy_m3)<=budget;
  }
  function getPlanId(plan,index){return String(plan.id??`plan-${index}`)}
  function getCrops(plan){return Array.isArray(plan.crops)?plan.crops:[]}
  function cropTitle(c){return text(c?.name??c?.crop_name??c?.id??'Crop')}
  function buildCard(plan,index,budget){
    const ok=withinBudget(plan,budget);
    const total=Number(plan.water_proxy_m3);
    const rank=Number.isFinite(Number(plan.rank))?Number(plan.rank):index+1;
    const card=node('article','rotation-card'+(rank===1&&ok?' featured':''));
    const top=node('div','card-top');
    top.append(node('span','plan-rank',`ROTATION ${String(rank).padStart(2,'0')}`),node('span','plan-status'+(ok?'':' over'),ok?'WITHIN TOTAL BUDGET':'EXCEEDS TOTAL BUDGET'));
    card.append(top);
    const timeline=node('div','crop-timeline');
    getCrops(plan).forEach((crop,i)=>{
      if(i)timeline.append(node('span','crop-sep','→'));
      timeline.append(node('span','crop-chip '+(crop.season==='winter'?'winter':'summer'),cropTitle(crop)));
    });
    if(!timeline.children.length)timeline.append(node('span','crop-chip','Crop details unavailable'));
    card.append(timeline);
    card.append(node('div','rotation-main-label','MODELED GROSS WATER PROXY'));
    const main=node('div','rotation-main-value');main.append(node('strong','',money(total)),node('span','','m³'));card.append(main);
    const bar=node('div','budget-bar');
    const fill=node('div','budget-fill'+(ok?'':' over'));
    const ratio=budget>0?total/budget*100:total>0?100:0;
    fill.style.width=`${Math.min(100,Math.max(0,Number.isFinite(ratio)?ratio:0))}%`;
    bar.setAttribute('role','img');
    bar.setAttribute('aria-label',budget>0?`${money(ratio)}% of total water budget`:'Total budget is zero');
    bar.append(fill);card.append(bar);
    const info=node('div','budget-details');
    const diff=Number(plan.budget_difference_m3);
    const note=Number.isFinite(diff)?(diff>=0?`${money(diff)} m³ remaining`:`${money(-diff)} m³ over budget`):'Budget difference unavailable';
    info.append(node('span','',budget>0?`${money(ratio)}% of supplied budget`:'Zero budget supplied'),node('span',Number.isFinite(diff)?(diff>=0?'positive':'negative'):'',note));card.append(info);
    const facts=node('div','rotation-facts');
    const displays=[['RELATIVE SCORE',plan.comparison_score==null?'—':`${money(plan.comparison_score)} / 100`],['FAMILY DIVERSITY',plan.diversity_heuristic==null?'—':`${money(plan.diversity_heuristic)} / 100`]];
    displays.forEach(([key,value])=>{const d=node('div');d.append(node('span','',key),node('b','',value));facts.append(d)});card.append(facts);
    const details=node('details');details.append(node('summary','','View method, dates & signals'));
    const ul=node('ul');
    getCrops(plan).forEach(c=>{
      const season=text(c.season).toUpperCase();
      const period=c.planting_date&&c.harvest_estimated_date?`${c.planting_date} – ${c.harvest_estimated_date}`:'dates not provided';
      ul.append(node('li','',`${season} · ${cropTitle(c)} · ${period}. Estimated ETc: ${money(c.crop_et_mm)} mm; gross planning proxy: ${money(c.gross_planning_proxy_m3)} m³.`));
    });
    (Array.isArray(plan.signals)?plan.signals:[]).forEach(s=>ul.append(node('li','',text(s))));
    const w=plan.comparison_weights;
    if(w&&Number.isFinite(Number(w.water))&&Number.isFinite(Number(w.diversity)))ul.append(node('li','',`Relative weighting: ${money(100*Number(w.water))}% water, ${money(100*Number(w.diversity))}% family diversity. Weights are design choices, not agronomic accuracy.`));
    if(!ul.children.length)ul.append(node('li','','Detailed assumptions were not returned by the API.'));
    details.append(ul);card.append(details);
    const compare=node('label','compare-control');
    const checkbox=node('input');checkbox.type='checkbox';checkbox.value=getPlanId(plan,index);checkbox.checked=state.selected.has(checkbox.value);checkbox.dataset.planId=checkbox.value;
    checkbox.disabled=!checkbox.checked&&state.selected.size>=3;
    compare.append(checkbox,node('span','','Compare this rotation'));card.append(compare);
    return card;
  }
  function renderComparison(){
    const selected=state.result?.plans?.filter((p,i)=>state.selected.has(getPlanId(p,i)))||[];
    const panel=$('#comparisonSection');panel.hidden=selected.length===0;
    if(!selected.length)return;
    $('#compareCount').textContent=`${selected.length} of 3 selected`;
    const table=$('#comparisonTable');table.replaceChildren();
    const heading=node('tr');heading.append(node('th','', 'METRIC'));
    selected.forEach(p=>heading.append(node('th','',`${getCrops(p).map(c=>cropTitle(c)).join(' → ')||text(p.id)}`)));
    const thead=node('thead');thead.append(heading);table.append(thead);
    const body=node('tbody');
    const b=getBudget(state.result);
    const rows=[['Gross water proxy',p=>`${money(p.water_proxy_m3)} m³`],['Total budget status',p=>withinBudget(p,b)?'Within budget':'Exceeds budget'],['Family diversity',p=>p.diversity_heuristic==null?'—':`${money(p.diversity_heuristic)} / 100`],['Relative model score',p=>p.comparison_score==null?'—':`${money(p.comparison_score)} / 100`]];
    rows.forEach(([label,fn])=>{const tr=node('tr');tr.append(node('th','',label));selected.forEach(p=>tr.append(node('td','',fn(p))));body.append(tr)});
    table.append(body);
    $$('#scenarioList input[type="checkbox"]').forEach(cb=>cb.disabled=!cb.checked&&state.selected.size>=3);
  }
  function $$(selector,root=document){return [...root.querySelectorAll(selector)]}
  function renderPlans(){
    if(!state.result)return;
    const r=state.result, plans=r.plans.slice(), budget=getBudget(r);
    const total=plans.length, within=plans.filter(p=>withinBudget(p,budget)).length;
    const min=Math.min(...plans.map(p=>Number(p.water_proxy_m3)).filter(Number.isFinite));
    $('#planTotal').textContent=String(total);
    $('#planWithin').textContent=String(within);
    $('#minWater').textContent=Number.isFinite(min)?short(min):'—';
    $('#resultHighlights').hidden=false;
    const filters=$('#filterPlans').value,sort=$('#sortPlans').value;
    const visible=plans.filter(p=>filters==='all'||withinBudget(p,budget)===(filters==='within'));
    if(sort==='water') visible.sort((a,b)=>Number(a.water_proxy_m3)-Number(b.water_proxy_m3));
    else visible.sort((a,b)=>Number(a.rank??99)-Number(b.rank??99));
    $('#resultSummary').textContent=`${visible.length} shown · ${total} modeled rotations · ${within} within budget`;
    const box=$('#scenarioList');box.replaceChildren();
    if(!visible.length){
      const empty=node('div','empty-panel');empty.append(node('h3','','No plans match this filter'),node('p','','Choose another filter to explore the available scenarios.'));box.append(empty);
    }else visible.forEach((p,i)=>box.append(buildCard(p,plans.indexOf(p),budget)));
    const count=getCrops(plans[0]||{}).length;
    $('#resultsSubtitle').textContent=`Ranked ${count||2}-season modeled candidates · ${state.mode==='preview'?'Saved example':'Current analysis'}`;
    const noneFit=plans.length>0&&within===0;
    $('#rankingNotice').textContent=noneFit?'No candidate fits the supplied total budget. A first-ranked plan is still not an approved agricultural recommendation.':'Ranking uses total budget screening and relative modeled water/family-diversity metrics. The score is NOT a probability of success, yield, or soil improvement.';
    renderComparison();
  }
  function acceptResult(data,mode){
    if(!validResult(data))throw new Error('Unexpected analysis response structure.');
    state.result=data;state.mode=mode;state.selected.clear();
    $('#filterPlans').value='all';$('#sortPlans').value='rank';
    $('#exportBtn').disabled=false;
    setClimate(data.climate,365);
    renderSource(data.climate,mode);
    renderSoil(data.soil_summary);
    if(mode==='live' && Array.isArray(data.climate?.monthly_eto)){
      renderMonthly({months:data.climate.monthly_eto});
    }
    banner(mode==='preview'?'SAVED EXAMPLE ONLY — This is a historical result from the supplied original backend. Editing inputs will clear it; no new analysis was performed.':'Analysis completed using the connected backend. Historical climate analogue, not a weather forecast.',mode==='preview'?'preview':'');
    renderPlans();
  }
  async function analyze(){
    if(!form.reportValidity()){status('Correct the highlighted farm input before analyzing.','error');return;}
    const data=getInputs();
    if(!numericKeys.every(k=>Number.isFinite(data[k]))){status('All numeric inputs must be finite numbers.','error');return;}
    if(!data.allowed_crops.length){status('Choose at least one supported crop.','error');return;}
    stopCurrentRequest();
    const requestId=state.requestId;
    state.result=null;state.selected.clear();$('#exportBtn').disabled=true;
    const btn=$('#analyzeBtn');btn.disabled=true;btn.textContent='Analyzing…';
    banner('Requesting a new analysis from the backend…');
    status('Calculating crop-water and rotation comparisons…');
    try{
      const controller=new AbortController();state.controller=controller;
      const result=await requestJson('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data),signal:controller.signal});
      if(requestId!==state.requestId)return;
      acceptResult(result,'live');
      status('Analysis complete. Compare the alternatives below.','success');
    }catch(e){
      if(requestId!==state.requestId)return;
      state.result=null;$('#exportBtn').disabled=true;
      $('#scenarioList').replaceChildren();
      const empty=node('div','empty-panel');empty.append(node('h3','','Analysis unavailable'),node('p','','Check the API connection and your input values, or open the saved reference example.'));$('#scenarioList').append(empty);
      $('#resultHighlights').hidden=true;$('#comparisonSection').hidden=true;
      banner('Analysis could not be completed; old results have been cleared.','error');
      status(`Could not analyze: ${e.message}.`,`error`);
    }finally{
      if(requestId===state.requestId){btn.disabled=false;btn.textContent='Analyze rotation plans ↗';state.controller=null;}
    }
  }
  async function preview(){
    stopCurrentRequest();
    const id=state.requestId;
    status('Loading the saved pilot reference report…');
    try{
      const [report,monthly]=await Promise.all([
        requestJson('dist/data/pilot-reference-report.json'),
        requestJson('dist/data/pilot-reference-monthly.json')
      ]);
      if(id!==state.requestId)return;
      populateInputs(report.inputs);
      acceptResult(report,'preview');renderMonthly(monthly);
      status('Saved 2025 pilot example loaded. This is not a live analysis.');
    }catch(e){
      if(id!==state.requestId)return;
      banner('Could not load the saved reference example.','error');
      status('Saved example unavailable: '+e.message,'error');
    }
  }
  function exportResult(){
    if(!state.result)return;
    const blob=new Blob([JSON.stringify(state.result,null,2)],{type:'application/json'});
    const uri=URL.createObjectURL(blob);const link=node('a');
    link.href=uri;link.download=state.mode==='preview'?'agrishift-SAVED-REFERENCE-example.json':'agrishift-live-analysis.json';
    document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(uri),1200);
  }
  function setMapFrame(lat, lon, label='Selected location'){
    const frame = $('#locationMapFrame');
    const title = $('#visualMapTitle');
    const link = $('#osmOpenLink');
    if(!frame || !Number.isFinite(lat) || !Number.isFinite(lon)) return;
    title.textContent = `Location context — ${label}`;
    const safeLabel=String(label).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
    frame.setAttribute('sandbox','');
    const latText = lat.toFixed(4);
    const lonText = lon.toFixed(4);
    frame.removeAttribute('src');
    frame.srcdoc = `<!doctype html><html><head><meta charset="utf-8"><style>
      body{margin:0;font-family:Arial,Helvetica,sans-serif;background:linear-gradient(180deg,#0a1a28,#10283d);color:#eef7fb;display:grid;place-items:center;height:100vh;}
      .shell{width:min(92%,700px);padding:28px;border-radius:26px;background:linear-gradient(180deg,rgba(255,255,255,.06),rgba(255,255,255,.03));border:1px solid rgba(255,255,255,.08);box-shadow:0 20px 40px rgba(0,0,0,.18)}
      .eyebrow{display:inline-block;padding:8px 12px;border-radius:999px;background:rgba(24,201,234,.12);border:1px solid rgba(24,201,234,.18);font-weight:700;font-size:12px;letter-spacing:1px;color:#bdf2ff}
      h3{margin:16px 0 8px;font-size:34px;line-height:1.05}
      p{margin:0 0 16px;color:#d2deea;line-height:1.6;font-size:14px}
      .grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin-top:18px}
      .cell{padding:16px;border-radius:18px;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.06)}
      .cell small{display:block;color:#91a6b9;font-size:11px;letter-spacing:1px;text-transform:uppercase;margin-bottom:6px}
      .cell strong{font-size:22px;color:#f4f8fc}
    </style></head><body><div class="shell"><span class="eyebrow">OFFLINE LOCATION PANEL</span><h3>${safeLabel}</h3><p>This offline build shows coordinate context without loading external map tiles. Use these coordinates with the crop gallery and the decision studio.</p><div class="grid"><div class="cell"><small>Latitude</small><strong>${latText}°</strong></div><div class="cell"><small>Longitude</small><strong>${lonText}°</strong></div></div></div></body></html>`;
    if(link){
      link.textContent = 'Offline bundle';
      link.removeAttribute('href');
      link.removeAttribute('target');
      link.setAttribute('aria-disabled','true');
      link.style.pointerEvents = 'none';
      link.style.opacity = '.7';
    }
  }
  let geoRequestId = 0;
  async function queryNearbyPhotos(lat, lon) {
    const requestId = ++geoRequestId;
    const box = $('#locationGallery');
    if (!box) return;
    box.replaceChildren(node('div','photo-placeholder','Loading bundled local reference visuals…'));
    const localPhotos = [
      {src:'dist/img/hero/fields-aerial.webp', title:'Landscape overview', note:'Bundled field visual · used for atmosphere and geographic context'},
      {src:'dist/img/hero/fields-patchwork.webp', title:'Patchwork farmland', note:'Bundled field visual · useful for broad land-use storytelling'},
      {src:'dist/img/crops/wheat.webp', title:'Winter wheat', note:'Bundled crop visual · winter cereal reference'},
      {src:'dist/img/crops/faba.webp', title:'Faba bean', note:'Bundled crop visual · winter legume reference'},
      {src:'dist/img/crops/maize.webp', title:'Grain maize', note:'Bundled crop visual · warm-season cereal reference'},
      {src:'dist/img/crops/sunflower.webp', title:'Sunflower', note:'Bundled crop visual · warm-season oilseed reference'}
    ];
    const rotation = Math.abs(Math.round((lat * 10) + (lon * 10))) % localPhotos.length;
    const ordered = localPhotos.slice(rotation).concat(localPhotos.slice(0, rotation)).slice(0, 6);
    if(requestId!==geoRequestId) return;
    box.replaceChildren();
    ordered.forEach(photo=>{
      const article=node('article','photo-card');
      const image=node('img'); image.src=photo.src; image.loading='lazy'; image.alt=photo.title;
      const body=node('div','photo-card-body');
      body.append(node('small','', 'OFFLINE REFERENCE'), node('strong','', photo.title), node('span','', photo.note));
      const a=node('a','photo-link','Asset notes ↗');
      a.href='PHOTO-CREDITS.md'; a.target='_blank';
      body.append(a); article.append(image, body); box.append(article);
    });
  }
  function updateVisualExplorer(){
    const latField=$('#visualLat'), lonField=$('#visualLon');
    if(!latField || !lonField || latField.value.trim()==='' || lonField.value.trim()==='') {
      status('Please enter both geographic coordinates.','error');return;
    }
    const lat=Number(latField.value), lon=Number(lonField.value);
    if(!Number.isFinite(lat) || !Number.isFinite(lon) || Math.abs(lat)>90 || Math.abs(lon)>180){
      status('Latitude must be between -90 and 90, and longitude between -180 and 180.','error');return;
    }
    const label=($('#visualPlace')?.value || 'Selected location').trim().slice(0,90);
    setMapFrame(lat,lon,label);
    queryNearbyPhotos(lat,lon);
  }
  function wireNavigation(){
    const aside=$('#sidebar'),backdrop=$('#navBackdrop'),toggle=$('#openSidebar');
    function close(){aside.classList.remove('open');backdrop.hidden=true;toggle.setAttribute('aria-expanded','false')}
    toggle.addEventListener('click',()=>{aside.classList.add('open');backdrop.hidden=false;toggle.setAttribute('aria-expanded','true')});
    $('#closeSidebar').addEventListener('click',close);backdrop.addEventListener('click',close);
    $$('.side-link').forEach(link=>link.addEventListener('click',()=>{
      $$('.side-link').forEach(a=>a.classList.remove('active'));link.classList.add('active');close();
    }));
    document.addEventListener('keydown',e=>{if(e.key==='Escape')close()});
  }
  async function initialize(){
    wireNavigation();
    form.addEventListener('submit',e=>{e.preventDefault();analyze()});
    form.addEventListener('input',()=>{if(state.result||state.controller)clearResult(true)});
    form.addEventListener('change',()=>{if(state.result||state.controller)clearResult(true)});
    ['latitude','longitude'].forEach(id=>{
      const input=document.getElementById(id);
      input?.addEventListener('input',()=>{
        ['temperature','rainfall','et0annual','coverageDays'].forEach(target=>{const node=document.getElementById(target);if(node)node.textContent='—';});
        const chart=document.getElementById('etoChart');
        if(chart)chart.replaceChildren(node('div','chart-placeholder','Location changed. Run an analysis to load NASA POWER 2025 data for these coordinates.'));
        const visual=document.getElementById(id==='latitude'?'visualLat':'visualLon');
        if(visual)visual.value=input.value;
      });
    });
    form.addEventListener('reset',()=>setTimeout(()=>{clearResult(true);status('Defaults restored. Run analysis again.');},0));
    $('#previewBtn').addEventListener('click',preview);
    $('#exportBtn').addEventListener('click',exportResult);
    $('#filterPlans').addEventListener('change',renderPlans);
    $('#sortPlans').addEventListener('change',renderPlans);
    const gps=document.getElementById('useGpsBtn');
    if(gps)gps.addEventListener('click',()=>{
      const feedback=document.getElementById('gpsFeedback');
      if(!('geolocation' in navigator)){
        feedback.textContent='Your browser does not support location access; enter farm coordinates manually.';return;
      }
      gps.disabled=true;feedback.textContent='Requesting permission for device GPS location…';
      navigator.geolocation.getCurrentPosition(({coords})=>{
        document.getElementById('latitude').value=coords.latitude.toFixed(4);
        document.getElementById('longitude').value=coords.longitude.toFixed(4);
        document.getElementById('latitude').dispatchEvent(new Event('input',{bubbles:true}));
        document.getElementById('longitude').dispatchEvent(new Event('input',{bubbles:true}));
        document.getElementById('latitude').dispatchEvent(new Event('change',{bubbles:true}));
        feedback.textContent=`Device location received (approx. ${Math.round(coords.accuracy)}m reported accuracy). Verify this is your FARM, not just your current location.`;
        gps.disabled=false;
      },err=>{
        feedback.textContent='GPS was not available or permission was denied. Enter your farm coordinates manually (HTTPS or localhost required).';
        gps.disabled=false;
      },{enableHighAccuracy:true,timeout:12000,maximumAge:30000});
    });
    $('#updateVisualsBtn')?.addEventListener('click', updateVisualExplorer);
    $('#refreshGalleryBtn')?.addEventListener('click', updateVisualExplorer);
    $('#usePilotVisualsBtn')?.addEventListener('click', ()=>{
      $('#visualLat').value = '30.5000';
      $('#visualLon').value = '31.5000';
      $('#visualPlace').value = 'Nile Delta pilot context';
      updateVisualExplorer();
    });
    $('#scenarioList').addEventListener('change',e=>{
      const cb=e.target;
      if(!cb.matches('input[type="checkbox"][data-plan-id]'))return;
      const id=cb.dataset.planId;
      if(cb.checked&&state.selected.size>=3){cb.checked=false;return;}
      if(cb.checked)state.selected.add(id);else state.selected.delete(id);
      renderComparison();
    });
    updateVisualExplorer();
    const outcome=await Promise.allSettled([
      requestJson('/api/health'),requestJson('/api/climate'),requestJson('/api/monthly')
    ]);
    const [health,climate,monthly]=outcome;
    const connected=health.status==='fulfilled'&&health.value?.ok===true;
    setServerStatus(connected);
    if(climate.status==='fulfilled')setClimate(climate.value,connected?health.value.date_count:365);
    if(monthly.status==='fulfilled')renderMonthly(monthly.value);
    else $('#etoChart').replaceChildren(node('div','chart-placeholder','Monthly data will appear when the backend connects or you open the saved example.'));
    // Load the labeled reference pilot only on first load. Once coordinates are edited,
    // previous metrics and chart are reset until a fresh location-specific analysis completes.
    if(connected)analyze();
    else{
      status('Backend is offline. Run python start_agrishift.py from the AgriShift-SUPER project root, or view the saved example.','error');
      banner('No API connection. A saved reference example is available, but the form cannot calculate new results until the backend is running.','preview');
      if(new URLSearchParams(location.search).get('preview')==='1')preview();
    }
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',initialize);else initialize();
})();
