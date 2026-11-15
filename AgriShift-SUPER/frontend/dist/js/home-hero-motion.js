/* AgriShift — automatically animated opening photography (Home only).
   Keeps the supplied images unchanged. No extra libraries or network calls. */
(()=>{
  'use strict';
  const stage=document.querySelector('.dispensa-home .pantry-cover-art');
  if(!stage) return;
  const photos=[...stage.querySelectorAll('.pantry-cover-frame')];
  if(!photos.length) return;

  const reduced=window.matchMedia('(prefers-reduced-motion: reduce)');
  const scene=stage.closest('.pantry-cover') || stage;
  const movement=[
    {x:5.5,y:9.5, speed:.00072, phase:0, depth:.55},
    {x:10.5,y:14.5,speed:.00093,phase:1.4,depth:1.15},
    {x:8.5,y:12.5,speed:.00081,phase:3,depth:-.88}
  ];
  let pointerTargetX=0,pointerTargetY=0,pointerX=0,pointerY=0;
  let scrollY=0,raf=0,visible=true,last=0;
  let startTime=performance.now();

  function reset(){
    photos.forEach(photo=>{
      photo.style.setProperty('--dp-mx','0px');
      photo.style.setProperty('--dp-my','0px');
    });
  }
  function stop(){
    if(raf){cancelAnimationFrame(raf);raf=0;}
  }
  function shouldAnimate(){return !document.hidden && visible && !reduced.matches;}
  function tick(now){
    raf=0;
    if(!shouldAnimate())return;
    // A maximum of 60 updates a second; only transform is changed, not layout.
    if(now-last>=15){
      last=now;
      pointerX+=(pointerTargetX-pointerX)*.075;
      pointerY+=(pointerTargetY-pointerY)*.075;
      const elapsed=now-startTime;
      photos.forEach((photo,i)=>{
        const p=movement[i] || movement[0];
        const dx=Math.sin(elapsed*p.speed+p.phase)*p.x;
        const dy=Math.cos(elapsed*p.speed*.91+p.phase)*p.y;
        const x=dx+pointerX*14*p.depth;
        const y=dy+pointerY*11*p.depth+scrollY*18*p.depth;
        photo.style.setProperty('--dp-mx',`${x.toFixed(2)}px`);
        photo.style.setProperty('--dp-my',`${y.toFixed(2)}px`);
      });
    }
    raf=requestAnimationFrame(tick);
  }
  function start(){
    if(!shouldAnimate() || raf)return;
    startTime=performance.now();
    raf=requestAnimationFrame(tick);
  }
  function refresh(){
    if(shouldAnimate()) start();
    else{stop();if(reduced.matches)reset();}
  }
  function handlePointer(e){
    if(e.pointerType==='touch'||reduced.matches)return;
    const r=scene.getBoundingClientRect();
    pointerTargetX=Math.max(-1,Math.min(1,((e.clientX-r.left)/Math.max(r.width,1)-.5)*2));
    pointerTargetY=Math.max(-1,Math.min(1,((e.clientY-r.top)/Math.max(r.height,1)-.5)*2));
  }
  function handleScroll(){
    if(reduced.matches)return;
    const r=stage.getBoundingClientRect();
    scrollY=Math.max(-1,Math.min(1,((innerHeight*.5)-(r.top+r.height*.5))/Math.max(innerHeight,1)));
  }
  scene.addEventListener('pointermove',handlePointer,{passive:true});
  scene.addEventListener('pointerleave',()=>{pointerTargetX=pointerTargetY=0;},{passive:true});
  window.addEventListener('scroll',handleScroll,{passive:true});
  window.addEventListener('resize',handleScroll,{passive:true});
  document.addEventListener('visibilitychange',refresh);
  if(reduced.addEventListener)reduced.addEventListener('change',refresh);
  else if(reduced.addListener)reduced.addListener(refresh);
  if('IntersectionObserver' in window){
    const observer=new IntersectionObserver(entries=>{
      visible=entries[0]?.isIntersecting ?? true;
      refresh();
    },{threshold:0});
    observer.observe(stage);
  }
  handleScroll();
  refresh();
})();
