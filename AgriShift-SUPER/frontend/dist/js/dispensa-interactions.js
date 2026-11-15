/* AgriShift original Field Collection interactions. Browser-native, no backend changes. */
(()=>{
  'use strict';
  if(!document.body.classList.contains('dispensa-edition')) return;
  const $=(s,root=document)=>root.querySelector(s);
  const $$=(s,root=document)=>[...root.querySelectorAll(s)];
  const reduced=window.matchMedia('(prefers-reduced-motion: reduce)');
  const cover=$('.pantry-cover-art');
  const field=$('.pantry-field-stage');
  const covers=$$('.pantry-cover-frame',cover||document);
  let cursorX=0,cursorY=0,scrollAmount=0,framePending=false;
  function paint(){
    framePending=false;
    if(reduced.matches){covers.forEach(f=>{f.style.setProperty('--dp-mx','0px');f.style.setProperty('--dp-my','0px')});return;}
    if(cover){
      const b=cover.getBoundingClientRect();
      if(b.bottom>0&&b.top<innerHeight){
        const offset=Math.max(-1,Math.min(1,(innerHeight*.5-b.top-b.height*.5)/innerHeight));
        covers.forEach((f,i)=>{
          const depth=[.75,1.5,-1.2][i]||1;
          f.style.setProperty('--dp-mx',`${(cursorX*depth*13).toFixed(1)}px`);
          f.style.setProperty('--dp-my',`${(cursorY*depth*8+offset*depth*18).toFixed(1)}px`);
        });
      }
    }
    if(field){
      const b=field.getBoundingClientRect();
      if(b.bottom>0&&b.top<innerHeight){
        const offset=(innerHeight*.5-b.top-b.height*.5)/innerHeight;
        field.style.setProperty('--dp-field-y',`${Math.max(-36,Math.min(36,offset*28)).toFixed(1)}px`);
      }
    }
  }
  function schedule(){if(!framePending){framePending=true;requestAnimationFrame(paint)}}
  cover?.addEventListener('pointermove',e=>{
    if(reduced.matches||e.pointerType==='touch')return;
    const b=cover.getBoundingClientRect();
    cursorX=(e.clientX-(b.left+b.width/2))/Math.max(b.width/2,1);
    cursorY=(e.clientY-(b.top+b.height/2))/Math.max(b.height/2,1);
    schedule();
  });
  cover?.addEventListener('pointerleave',()=>{cursorX=cursorY=0;schedule()});
  addEventListener('scroll',schedule,{passive:true});addEventListener('resize',schedule,{passive:true});schedule();
  // A crop card is interactive: select it as the previous crop for the actual model.
  $$('[data-set-previous]').forEach(button=>button.addEventListener('click',()=>{
    const select=$('#previous_crop');
    if(!select)return;
    select.value=button.dataset.setPrevious;
    select.dispatchEvent(new Event('change',{bubbles:true}));
    $('#farm')?.scrollIntoView({behavior:reduced.matches?'auto':'smooth',block:'start'});
    const feedback=$('#feedback');
    if(feedback)feedback.textContent=`Previous crop set to ${select.selectedOptions[0]?.textContent||select.value}. Run analysis to update modeled results.`;
  }));
  // Compact floating chapter index for desktop: authentic page navigation without duplicate forms.
  const labels=[['#overview','01','Cover'],['#field-collection','02','Winter'],['#warm-collection','03','Summer'],['#farm','04','Studio']];
  const rail=document.createElement('nav');rail.className='pantry-chapter-rail';rail.setAttribute('aria-label','Jump to collection chapter');
  labels.forEach(([href,label,title])=>{const a=document.createElement('a');a.href=href;a.textContent=label;a.title=title;a.setAttribute('aria-label',title);rail.append(a)});
  document.body.append(rail);
  if('IntersectionObserver' in window){
    const obs=new IntersectionObserver(entries=>entries.forEach(e=>{
      if(!e.isIntersecting)return;
      rail.querySelectorAll('a').forEach(a=>a.classList.toggle('active',a.getAttribute('href')==='#'+e.target.id));
    }),{rootMargin:'-20% 0px -65% 0px',threshold:0});
    labels.forEach(([href])=>{const el=$(href);if(el)obs.observe(el)});
  }
  // Explain missing images without substituting fabricated real-world photos.
  $$('.pantry-cover-frame img,.product-photo-wrap img,.pantry-field-photo img').forEach(img=>{
    const handle=()=>{img.parentElement.classList.add('image-fallback');img.style.opacity='0'};
    img.addEventListener('error',handle);
    if(img.complete&&!img.naturalWidth)handle();
  });
})();
