/* AgriShift Cinematic Experience — custom interactions, no external animation dependency. */
(()=>{
  'use strict';
  const reduce=window.matchMedia('(prefers-reduced-motion: reduce)');
  const $=(selector,scope=document)=>scope.querySelector(selector);
  const $$=(selector,scope=document)=>Array.from(scope.querySelectorAll(selector));
  // Fullscreen menu and page transitions are handled by flow-navigation.js.
  if('IntersectionObserver' in window){
    const observer=new IntersectionObserver(entries=>{
      entries.forEach(e=>{
        if(e.isIntersecting){e.target.classList.add('is-visible');observer.unobserve(e.target)}
      });
    },{threshold:.13,rootMargin:'0px 0px -28px 0px'});
    $$('[data-reveal],.atlas-card,.approach-steps article,.metric-tile,.rotation-card,.cinema-showcase').forEach(el=>{
      el.classList.add('cinema-reveal');observer.observe(el);
    });
  }
  // Keep the interface legible if a third-party image host is unreachable.
  $$('img[src^="https://"]').forEach(img=>{
    const fallback=()=>{img.classList.add('is-unavailable');img.closest('figure,article,section')?.classList.add('image-fallback')};
    img.addEventListener('error',fallback);
    if(img.complete && !img.naturalWidth) fallback();
  });
  const progress=$('#scrollProgressFill');
  const orbit=$('.cinema-orbit');
  const floating=$$('[data-depth]', orbit||document);
  const field=$('.cinema-field-photo');
  let needFrame=false;
  function paint(){
    needFrame=false;
    const max=document.documentElement.scrollHeight-window.innerHeight;
    if(progress)progress.style.transform=`scaleX(${max>0?Math.max(0,Math.min(1,scrollY/max)):0})`;
    if(reduce.matches)return;
    if(orbit){
      const bounds=orbit.getBoundingClientRect();
      if(bounds.bottom>0 && bounds.top<innerHeight){
        const amount=Math.max(-1,Math.min(1,(innerHeight/2-(bounds.y+bounds.height/2))/innerHeight));
        floating.forEach(el=>el.style.setProperty('--scroll-y',`${(amount*Number(el.dataset.depth||0)*2).toFixed(1)}px`));
      }
    }
    if(field){
      const b=field.parentElement.getBoundingClientRect();
      if(b.bottom>0 && b.top<innerHeight){
        const delta=((innerHeight/2)-(b.top+b.height/2))/innerHeight;
        field.style.setProperty('--scene-shift',`${(delta*36).toFixed(1)}px`);
      }
    }
  }
  addEventListener('scroll',()=>{if(!needFrame){needFrame=true;requestAnimationFrame(paint)}},{passive:true});
  addEventListener('resize',()=>{if(!needFrame){needFrame=true;requestAnimationFrame(paint)}},{passive:true});
  paint();
  if(orbit){
    let active=false;
    orbit.addEventListener('pointermove',e=>{
      if(reduce.matches||e.pointerType==='touch')return;
      const r=orbit.getBoundingClientRect();
      const nx=(e.clientX-(r.x+r.width/2))/Math.max(r.width,1);
      const ny=(e.clientY-(r.y+r.height/2))/Math.max(r.height,1);
      floating.forEach(el=>{
        const depth=Number(el.dataset.depth||0);
        el.style.setProperty('--pointer-x',`${(nx*depth*2.1).toFixed(1)}px`);
        el.style.setProperty('--pointer-y',`${(ny*depth*2.1).toFixed(1)}px`);
      });active=true;
    });
    orbit.addEventListener('pointerleave',()=>{
      if(!active)return;active=false;
      floating.forEach(el=>{el.style.setProperty('--pointer-x','0px');el.style.setProperty('--pointer-y','0px')});
    });
  }
  const track=$('#atlasTrack');
  const next=$('[data-atlas-next]');
  const prev=$('[data-atlas-prev]');
  function moveCard(dir){
    if(!track)return;
    const card=$('.atlas-card',track);
    if(!card)return;
    track.scrollBy({left:dir*(card.getBoundingClientRect().width+18),behavior:reduce.matches?'auto':'smooth'});
  }
  next?.addEventListener('click',()=>moveCard(1));
  prev?.addEventListener('click',()=>moveCard(-1));
  if(track){
    let pressed=false,start=0,scrollStart=0,moved=false;
    track.addEventListener('pointerdown',e=>{
      if(e.pointerType==='touch'||e.target.closest('a'))return;
      pressed=true;moved=false;start=e.clientX;scrollStart=track.scrollLeft;
    });
    track.addEventListener('pointermove',e=>{
      if(!pressed)return;
      const d=e.clientX-start;
      if(Math.abs(d)>6){moved=true;track.scrollLeft=scrollStart-d;track.classList.add('is-dragging')}
    });
    const stop=()=>{pressed=false;track.classList.remove('is-dragging')};
    window.addEventListener('pointerup',stop);
    track.addEventListener('dragstart',e=>e.preventDefault());
    track.addEventListener('click',e=>{if(moved){e.preventDefault();e.stopPropagation();moved=false;}},true);
  }
})();
