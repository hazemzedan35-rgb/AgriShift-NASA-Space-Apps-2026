(()=>{
  "use strict";
  if(!document.getElementById('cropAtlasCarousel')) return;
  const crops=[
    {id:'wheat',name:'Winter wheat',season:'Cool season',family:'Poaceae',water:'Moderate',role:'Base cereal',status:'supported',analysis:true,summary:'A cool-season cereal commonly used as a stable base crop in rotation planning.',note:'Supported by the current backend model and available in the analysis form.',image:'dist/img/crops/wheat.webp'},
    {id:'faba',name:'Faba bean',season:'Cool season',family:'Fabaceae',water:'Moderate',role:'Nitrogen-supporting legume',status:'supported',analysis:true,summary:'A winter legume that diversifies the rotation and changes the crop-family sequence.',note:'Supported by the current backend model and available in the analysis form.',image:'dist/img/crops/faba.webp'},
    {id:'maize',name:'Grain maize',season:'Warm season',family:'Poaceae',water:'High',role:'Summer cereal',status:'supported',analysis:true,summary:'A warm-season cereal with relatively high modeled water demand compared with the winter crops.',note:'Supported by the current backend model and available in the analysis form.',image:'dist/img/crops/maize.webp'},
    {id:'sunflower',name:'Sunflower',season:'Warm season',family:'Asteraceae',water:'Moderate',role:'Oilseed option',status:'supported',analysis:true,summary:'A warm-season oilseed offering a different crop family and an alternative summer pathway.',note:'Supported by the current backend model and available in the analysis form.',image:'dist/img/crops/sunflower.webp'},
    {id:'rice',name:'Rice',season:'Warm season',family:'Poaceae',water:'Very high',role:'Paddy cereal',status:'limited',analysis:false,summary:'A major staple crop typically associated with high water requirements and region-specific management.',note:'Quantified FAO-56 ETc model only. Full gross water / multicut seasonal management is unknown, so this crop is excluded from rotation ranking.',image:'dist/img/crops/rice.webp'},
    {id:'cotton',name:'Cotton',season:'Warm season',family:'Malvaceae',water:'Moderate to high',role:'Fiber crop',status:'supported',analysis:true,summary:'A fiber crop with management considerations different from cereals and legumes.',note:'FAO-56 example ETc model is available and this annual crop can enter rotation comparison. Not site-calibrated or locally approved.',image:'dist/img/crops/cotton.webp'},
    {id:'potato',name:'Potato',season:'Cool to mild season',family:'Solanaceae',water:'Moderate',role:'Tuber crop',status:'supported',analysis:true,summary:'A widely grown tuber crop with distinct soil and disease-management implications in rotation.',note:'FAO-56 example ETc model is available and this annual crop can enter rotation comparison. Not site-calibrated or locally approved.',image:'dist/img/crops/potato.webp'},
    {id:'tomato',name:'Tomato',season:'Warm season',family:'Solanaceae',water:'Moderate',role:'High-value horticulture',status:'supported',analysis:true,summary:'A horticultural crop often managed differently from broadacre field crops.',note:'FAO-56 example ETc model is available and this annual crop can enter rotation comparison. Not site-calibrated or locally approved.',image:'dist/img/crops/tomato.webp'},
    {id:'onion',name:'Onion',season:'Cool to mild season',family:'Amaryllidaceae',water:'Moderate',role:'Bulb crop',status:'supported',analysis:true,summary:'A bulb crop important in many rotations, with its own management and storage considerations.',note:'FAO-56 example ETc model is available and this annual crop can enter rotation comparison. Not site-calibrated or locally approved.',image:'dist/img/crops/onion.webp'},
    {id:'sugarbeet',name:'Sugar beet',season:'Cool season',family:'Amaranthaceae',water:'Moderate',role:'Industrial root crop',status:'supported',analysis:true,summary:'A root crop often included for industrial and sugar production systems.',note:'FAO-56 example ETc model is available and this annual crop can enter rotation comparison. Not site-calibrated or locally approved.',image:'dist/img/crops/sugarbeet-team-photo.png'},
    {id:'alfalfa',name:'Alfalfa (hay)',season:'Multi-cut forage',family:'Fabaceae',water:'Moderate',role:'Forage legume',status:'limited',analysis:false,summary:'A forage legume with a very different rotation role from grain or oilseed crops.',note:'Quantified FAO-56 ETc model only. Full gross water / multicut seasonal management is unknown, so this crop is excluded from rotation ranking.',image:'dist/img/crops/alfalfa.webp'},
    {id:'sorghum',name:'Sorghum',season:'Warm season',family:'Poaceae',water:'Lower than maize',role:'Drought-tolerant cereal',status:'supported',analysis:true,summary:'A cereal known for its resilience and potential fit in water-constrained contexts.',note:'FAO-56 example ETc model is available and this annual crop can enter rotation comparison. Not site-calibrated or locally approved.',image:'dist/img/crops/sorghum.png'}
  ];
  const carousel=document.getElementById('cropAtlasCarousel');
  const detailEls={
    image:document.getElementById('cropDetailImage'),
    season:document.getElementById('cropDetailSeason'),
    support:document.getElementById('cropDetailSupport'),
    name:document.getElementById('cropDetailName'),
    summary:document.getElementById('cropDetailSummary'),
    family:document.getElementById('cropDetailFamily'),
    water:document.getElementById('cropDetailWater'),
    role:document.getElementById('cropDetailRole'),
    status:document.getElementById('cropDetailStatus'),
    note:document.getElementById('cropDetailNote'),
    apply:document.getElementById('cropApplyBtn')
  };
  const previousSelect=document.getElementById('previous_crop');
  const feedback=document.getElementById('feedback');
  let activeCard=null;
  function cardMarkup(c){
    const label=c.status==='supported'?'Rotation model':c.status==='limited'?'ETc only':'Visual library';
    return `<button class="crop-object" type="button" data-crop="${c.id}" aria-label="Open crop details for ${c.name}">
      <div class="crop-object-card">
        <div class="crop-object-shell"></div>
        <div class="crop-object-image"><img src="${c.image}" alt="${c.name}" loading="lazy"></div>
        <div class="crop-object-label">
          <small>${c.season}</small>
          <strong>${c.name}</strong>
          <span>${c.role}<b class="crop-pill ${c.status}">${label}</b></span>
        </div>
      </div>
    </button>`;
  }
  carousel.innerHTML=crops.map(cardMarkup).join('');
  function setActive(id){
    const crop=crops.find(c=>c.id===id) || crops[0];
    const nextCard=carousel.querySelector(`[data-crop="${crop.id}"]`);
    if(activeCard) activeCard.classList.remove('is-active');
    if(nextCard){ nextCard.classList.add('is-active'); activeCard=nextCard; }
    detailEls.image.src=crop.image; detailEls.image.alt=crop.name;
    detailEls.season.textContent=crop.season;
    detailEls.support.textContent=crop.status==='supported'?'Rotation model':crop.status==='limited'?'ETc only':'Visual library';
    detailEls.support.classList.toggle('visual',crop.status!=='supported');
    detailEls.name.textContent=crop.name;
    detailEls.summary.textContent=crop.summary;
    detailEls.family.textContent=crop.family;
    detailEls.water.textContent='See location-specific ETc assessment';
    detailEls.role.textContent=crop.role;
    detailEls.status.textContent=crop.analysis?'FAO-56 rotation comparison (example only)':crop.status==='limited'?'FAO-56 atmospheric ETc only':'Not currently supported by backend';
    detailEls.note.textContent=crop.note;
    detailEls.apply.hidden=!crop.analysis;
    detailEls.apply.dataset.crop=crop.id;
  }
  carousel.addEventListener('click',e=>{
    const card=e.target.closest('.crop-object');
    if(!card) return;
    setActive(card.dataset.crop);
  });
  detailEls.apply.addEventListener('click',()=>{
    const cropId=detailEls.apply.dataset.crop;
    if(!previousSelect || !cropId) return;
    previousSelect.value=cropId;
    previousSelect.dispatchEvent(new Event('change',{bubbles:true}));
    document.getElementById('farm')?.scrollIntoView({behavior:'smooth',block:'start'});
    if(feedback){
      const label=previousSelect.selectedOptions[0]?.textContent || cropId;
      feedback.textContent=`Previous crop set to ${label}. Continue in the decision studio to analyze supported rotations.`;
    }
  });
  setActive('wheat');
})()
