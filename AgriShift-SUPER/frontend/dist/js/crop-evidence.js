'use strict';
/* Source-traceable ECOCROP + FAO-56 + Egypt crop-calendar diagnostics. No invented suitability scores. */
(() => {
  const $=(q,root=document)=>root.querySelector(q);
  const form=$('#farmForm'),btn=$('#assess12Btn'),board=$('#cropAssessmentCards'),status=$('#cropAssessmentStatus');
  if(!form||!btn||!board||!status)return;
  let requestId=0,controller=null,lastEvidence=null;
  const exportBtn=$('#exportAssessmentBtn');
  const number=(v,dec=1)=>v===null||v===undefined||v===''||!Number.isFinite(Number(v))?'Unknown':Number(v).toLocaleString('en-US',{maximumFractionDigits:dec});
  const el=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=String(text);return n;};
  const bounds=(x,unit='')=>Array.isArray(x)&&x.length===2&&x.every(v=>Number.isFinite(v))?`${number(x[0])}–${number(x[1])}${unit}`:'Unreported';
  const fmt=(x)=>{
    if(!x)return 'Unknown';
    return ({unknown:'Unknown / input missing',within_reference_range:'Within published absolute range',outside_reference_range:'Outside published absolute range',
      within_reference_category:'Matches ECOCROP category',outside_reference_category:'Outside ECOCROP category',
      within_reference_threshold:'Below FAO salinity threshold',caution:'Caution — FAO threshold',
      regional_records_available:'Regional entries found',region_not_selected:'Region not selected',no_matching_regional_records:'No entry for this zone'})[x]||x;
  };
  function currentInputs(){
    const values=new FormData(form),result={};
    ['latitude','longitude','area_ha','water_budget_m3','irrigation_efficiency','planning_seasons'].forEach(k=>result[k]=Number(values.get(k)));
    ['first_winter_year','soil_awc_mm_per_m','soil_ece_ds_m','soil_ph'].forEach(k=>result[k]=values.get(k)===''?null:Number(values.get(k)));
    ['previous_crop','priority','soil_type','soil_drainage','calendar_zone'].forEach(k=>result[k]=String(values.get(k)||''));
    result.allowed_crops=[...form.querySelectorAll('input[name="allowed_crops"]:checked')].map(n=>n.value);
    return result;
  }
  function line(k,v){const row=el('div','agri-assess-line');row.append(el('span','',k),el('strong','',v));return row;}
  function dateLabel(d){return d&&d.day&&d.month?`${String(d.day).padStart(2,'0')}/${String(d.month).padStart(2,'0')}`:'Unknown';}
  function bullet(list,t){if(t)list.append(el('li','',t));}
  function card(c){
    const wrap=el('article','agri-assess-card');
    const top=el('div','agri-assess-top'),badge=el('span','agri-assess-pill',c.rotation_eligible?'ROTATION SCREEN':'ETc ONLY');
    top.append(el('span','agri-assess-name',c.name),badge);wrap.append(top);
    const data=c.quantitative_et,ind=c.suitability,eco=ind.climate_temperature,ph=ind.soil_ph,cal=ind.regional_calendar;
    const hero=el('div','agri-assess-etc');hero.append(el('strong','',number(data.crop_et_mm)),el('span','','mm ETc · '+data.growth_days+' modeled days'));wrap.append(hero);
    const rows=el('div','agri-assess-lines');
    rows.append(line('Irrigation proxy',data.gross_planning_proxy_m3===null?'Not modeled':number(data.gross_planning_proxy_m3,0)+' m³'));
    rows.append(line('Temperature · NASA 2025',`${number(eco.observed)}°C mean`));
    rows.append(line('ECOCROP optimal temperature',bounds(eco.optimal_bounds,'°C')));
    rows.append(line('Temperature screening',fmt(eco.status)));
    rows.append(line('Soil pH',ph.status==='unknown'?'Unknown — field input needed':`${number(ph.observed)} · ${fmt(ph.status)}`));
    rows.append(line('ECOCROP optimal soil pH',bounds(ph.optimal_bounds)));
    rows.append(line('Soil salinity',fmt(ind.soil_salinity.status)));
    rows.append(line('Soil texture / drainage',`${fmt(ind.soil_texture.status)} · ${fmt(ind.soil_drainage.status)}`));
    rows.append(line('Egypt regional crop calendar',fmt(cal.status)));
    rows.append(line('Annual NASA 2025 rainfall',number(ind.climate_observations.historical_annual_rain_mm,0)+' mm'));
    rows.append(line('Evidence coverage',`${ind.assessed_dimensions}/${ind.possible_dimensions} dimensions (not a suitability score)`));
    wrap.append(rows);
    if(ind.status==='partial_caution')wrap.classList.add('agri-assess-caution');
    const details=el('details','agri-assess-details'),summary=el('summary','','Source rows, reference limits & field cautions');details.append(summary);
    const list=el('ul');
    bullet(list,`ECOCROP: ${ind.ecocrop_species} (EcoPortCode ${ind.ecocrop_row_id}); ${ind.ecocrop_taxon_note}`);
    bullet(list,`Temperature absolute envelope: ${bounds(eco.absolute_bounds,'°C')}; optimal: ${bounds(eco.optimal_bounds,'°C')}. Seasonal mean uses historical 2025 NASA weather on FAO example dates, not forecasts.`);
    bullet(list,`pH absolute: ${bounds(ph.absolute_bounds)}. Measured pH: ${number(ph.observed)}.`);
    bullet(list,`Rainfed annual rainfall envelope: ${bounds(ind.climate_rainfall_rainfed_reference.absolute_bounds,' mm')}; modeled NASA year: ${number(ind.climate_rainfall_rainfed_reference.observed)} mm. NOT a veto for irrigated crops.`);
    bullet(list,`ECOCROP texture reference: ${ind.soil_texture.eco_absolute||'unreported'}; drainage reference: ${ind.soil_drainage.eco_absolute||'unreported'}.`);
    if(cal.entries?.length){for(const r of cal.entries){bullet(list,`FAO Egypt Crop Calendar: ${r.zone} · ${r.reported_crop} · sow ${dateLabel(r.sowing_window.start)}–${dateLabel(r.sowing_window.end)} · harvest ${dateLabel(r.harvest_window.start)}–${dateLabel(r.harvest_window.end)} · growth ${bounds(r.growing_days_range,' d')} · XLSX row ${r.source_excel_row}.`);}}
    else bullet(list,`Calendar: ${cal.note}`);
    bullet(list,`FAO example dates in ETc: ${data.planting_date} → ${data.harvest_estimated_date}. Regional calendar dates are an independent check and are not silently substituted in water calculations.`);
    bullet(list,`FAO-56 stages: ${data.growth_stage_reference}. ${data.coefficient_reference}. ${data.water_scope}.`);
    bullet(list,`Missing evidence: ${ind.missing_evidence.join(', ')}. Overall suitability: NOT assigned. Not field-validated.`);
    details.append(list);wrap.append(details);
    return wrap;
  }
  async function run(){
    if(!form.reportValidity()){status.textContent='Please correct farm inputs before assessing crops.';return;}
    const input=currentInputs();if(!Number.isFinite(input.latitude)||!Number.isFinite(input.longitude)){status.textContent='Enter valid coordinates.';return;}
    const id=++requestId;if(controller)controller.abort();controller=new AbortController();
    lastEvidence=null;if(exportBtn)exportBtn.disabled=true;
    btn.disabled=true;btn.textContent='Assessing NASA + FAO…';board.replaceChildren();
    status.textContent='Fetching source-location NASA weather and matching 12 ECOCROP species plus regional calendar evidence…';
    try{
      const timer=setTimeout(()=>controller.abort(),140000);let response;
      try{response=await fetch('/api/crop-assessment',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(input),signal:controller.signal})}
      finally{clearTimeout(timer);}
      if(!response.ok){let err=`HTTP ${response.status}`;try{const body=await response.json();err=typeof body.detail==='string'?body.detail:err}catch{}throw new Error(err);}
      const data=await response.json();if(id!==requestId)return;
      if(!Array.isArray(data.crops)||data.crops.length!==12)throw new Error('Expected 12 source profiles. Incomplete response.');
      data.crops.forEach(c=>board.append(card(c)));
      lastEvidence=data;if(exportBtn)exportBtn.disabled=false;
      status.textContent=`${data.crop_count}/12 source-traceable FAO-56 ETc models · ${data.data_coverage.ecocrop_verified_profiles}/12 ECOCROP species profiles · ${data.data_coverage.regional_calendar_crop_count}/12 calendar matches in ${data.calendar_zone==='unknown'?'no confirmed zone':data.calendar_zone}. Historical NASA 2025, not a forecast. Environmental screening, NOT field suitability certification.`;
    }catch(err){if(id!==requestId)return;status.textContent=`Assessment unavailable: ${err.message}. No data invented.`;}
    finally{if(id===requestId){btn.disabled=false;btn.textContent='Assess all 12 crops ↗';controller=null;}}
  }
  btn.addEventListener('click',run);
  exportBtn?.addEventListener('click',()=>{
    if(!lastEvidence)return;
    const blob=new Blob([JSON.stringify(lastEvidence,null,2)],{type:'application/json'});
    const link=el('a');link.href=URL.createObjectURL(blob);link.download='AgriShift-12crop-EcoCrop-FAO-evidence.json';
    document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(link.href),2000);
  });
  form.addEventListener('input',()=>{if(controller)controller.abort();requestId++;lastEvidence=null;if(exportBtn)exportBtn.disabled=true;board.replaceChildren();status.textContent='Farm information changed. Rerun to calculate a source-traceable assessment.';btn.disabled=false;btn.textContent='Assess all 12 crops ↗';});
})();
