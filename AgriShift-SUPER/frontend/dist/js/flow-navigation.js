/* AgriShift Flow Navigation · locally bundled / no animation dependencies. */
(()=>{
  'use strict';
  const menu=document.getElementById('cinemaMenu');
  const curtain=document.getElementById('agriFlowCurtain');
  const curtainTitle=document.getElementById('agriFlowCurtainTitle');
  if(!menu || !curtain) return;
  const reduce=window.matchMedia('(prefers-reduced-motion: reduce)');
  const openers=[...document.querySelectorAll('[data-menu-open]')];
  const closer=menu.querySelector('[data-menu-close]');
  const links=[...menu.querySelectorAll('.agri-flow-menu-link')];
  const preview=menu.querySelector('#agriFlowPreviewImage');
  const previewCaption=menu.querySelector('.agri-flow-menu-preview figcaption');
  let previousFocus=null;
  let navigating=false;
  let scrollLock=0;
  const key='agrishift:flow-arrival';
  const titleKey='agrishift:flow-title';
  const safeGet=k=>{try{return sessionStorage.getItem(k)}catch{return null}};
  const safeSet=(k,v)=>{try{sessionStorage.setItem(k,v)}catch{}};
  const safeDel=k=>{try{sessionStorage.removeItem(k)}catch{}};
  const pathname=(url)=>{const p=url.pathname.replace(/\/index\.html$/,'/');return p.endsWith('/')?p:p.replace(/\/+$/,'')};
  function linkIsCurrent(a){
    let url;try{url=new URL(a.href,window.location.href)}catch{return false}
    return pathname(url)===pathname(window.location) && (!url.hash || url.hash===window.location.hash);
  }
  function markActive(){links.forEach(a=>{const yes=linkIsCurrent(a);a.classList.toggle('is-current',yes);if(yes)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current')});}
  function updatePreview(a){
    if(!preview || !a) return;
    const src=a.dataset.flowPreview;
    if(src && preview.getAttribute('src')!==src){preview.src=src;}
    if(previewCaption) previewCaption.textContent=(a.dataset.flowTitle||'AgriShift').toUpperCase();
  }
  function lockScroll(){scrollLock=window.scrollY;document.body.classList.add('cinema-menu-open');}
  function unlockScroll(){document.body.classList.remove('cinema-menu-open');}
  function openMenu(){
    if(navigating||menu.classList.contains('is-open'))return;
    previousFocus=document.activeElement;
    markActive();updatePreview(links.find(a=>a.classList.contains('is-current'))||links[0]);
    menu.inert=false;menu.setAttribute('aria-hidden','false');lockScroll();
    // Trigger presentation transition on a separate frame to keep staggered typography smooth.
    requestAnimationFrame(()=>{if(!menu.inert)menu.classList.add('is-open')});
    openers.forEach(b=>b.setAttribute('aria-expanded','true'));
    closer?.focus({preventScroll:true});
  }
  function closeMenu({restore=true}={}){
    if(!menu.classList.contains('is-open') && menu.inert)return;
    menu.classList.remove('is-open');
    menu.setAttribute('aria-hidden','true');menu.inert=true;
    unlockScroll();openers.forEach(b=>b.setAttribute('aria-expanded','false'));
    if(restore && previousFocus?.isConnected)previousFocus.focus({preventScroll:true});
  }
  openers.forEach(b=>b.addEventListener('click',openMenu));
  closer?.addEventListener('click',()=>closeMenu());
  for(const a of links){a.addEventListener('pointerenter',()=>updatePreview(a));a.addEventListener('focus',()=>updatePreview(a))}
  document.addEventListener('keydown',e=>{
    if(e.key==='Escape' && menu.classList.contains('is-open')){e.preventDefault();closeMenu();return}
    if(e.key!=='Tab'||!menu.classList.contains('is-open'))return;
    const tabbable=[...menu.querySelectorAll('a[href],button:not([disabled])')].filter(el=>!el.inert && el.getClientRects().length);
    if(!tabbable.length)return;
    const first=tabbable[0],last=tabbable[tabbable.length-1];
    if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus()}
    else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus()}
  });
  // Ordinary in-page buttons still scroll normally. The fullscreen-menu links
  // use the same dark curtain as cross-page navigation, even for local hashes.
  function finishSamePage(url){
    const hash=url.hash;
    closeMenu({restore:false});
    if(!hash){window.scrollTo({top:0,behavior:reduce.matches?'instant':'smooth'});return}
    let target=null;
    try{target=document.getElementById(decodeURIComponent(hash.slice(1)))}catch{}
    if(target){
      history.pushState(null,'',hash);
      setTimeout(()=>target.scrollIntoView({behavior:reduce.matches?'instant':'smooth',block:'start'}),reduce.matches?0:230);
    }
  }
  function titleFor(a){
    return (a?.dataset.flowTitle||a?.textContent?.replace(/↗/g,'')?.trim()||'AGRISHIFT')
      .replace(/\s+/g,' ').slice(0,32).toUpperCase();
  }
  function startCover(title){
    if(navigating)return false;
    navigating=true;
    if(curtainTitle)curtainTitle.textContent=title;
    curtain.style.transition='';
    curtain.classList.remove('is-revealing');
    curtain.classList.add('is-covering');
    curtain.style.pointerEvents='auto';
    document.body.classList.add('agri-flow-navigating');
    return true;
  }
  // Move the destination while it is completely hidden by the opaque curtain.
  // This avoids the long/uneven smooth scroll between distant dashboard sections.
  function jumpCovered(url){
    const hash=url.hash;
    let target=null;
    if(hash){try{target=document.getElementById(decodeURIComponent(hash.slice(1)))}catch{}}
    if(hash && !target)return false;
    closeMenu({restore:false});
    const root=document.documentElement;
    const original=root.style.scrollBehavior;
    root.style.scrollBehavior='auto';
    if(hash){
      history.pushState(null,'',url.pathname+window.location.search+hash);
      target.scrollIntoView({behavior:'instant',block:'start'});
    }else{
      history.pushState(null,'',url.pathname+window.location.search);
      window.scrollTo({top:0,behavior:'instant'});
    }
    root.style.scrollBehavior=original;
    return true;
  }
  function resetLocalCurtain(){
    // Do not animate back across the page while resetting to the hidden position.
    curtain.style.transition='none';
    document.documentElement.classList.remove('agri-flow-local-revealing');
    curtain.classList.remove('is-revealing','is-covering');
    curtain.style.pointerEvents='none';
    document.body.classList.remove('agri-flow-navigating');
    navigating=false;
    void curtain.offsetWidth;
    requestAnimationFrame(()=>{curtain.style.transition=''});
  }
  function transitionSamePage(url,a){
    if(!startCover(titleFor(a)))return;
    const coverTime=reduce.matches?30:810;
    setTimeout(()=>{
      if(!jumpCovered(url)){
        // A missing anchor should never trap the visitor behind an overlay.
        resetLocalCurtain();
        return;
      }
      document.documentElement.classList.add('agri-flow-local-revealing');
      // Keep the curtain opaque until reveal starts; switch both classes in
      // one frame so the page never flashes between the cover and reveal.
      requestAnimationFrame(()=>requestAnimationFrame(()=>{
        curtain.classList.remove('is-covering');
        curtain.classList.add('is-revealing');
        setTimeout(resetLocalCurtain,reduce.matches?60:870);
      }));
    },coverTime);
  }
  function navigate(url,a){
    const title=titleFor(a);
    if(!startCover(title))return;
    safeSet(key,'1');safeSet(titleKey,title);
    setTimeout(()=>window.location.assign(url.href),reduce.matches?40:810);
  }
  document.addEventListener('click',e=>{
    if(e.defaultPrevented||e.button!==0||e.metaKey||e.ctrlKey||e.shiftKey||e.altKey)return;
    const a=e.target.closest('a[href]');if(!a||a.hasAttribute('download')||a.target&&a.target!=='_self')return;
    if(a.getAttribute('href')?.startsWith('javascript:'))return;
    let target;try{target=new URL(a.href,window.location.href)}catch{return}
    if(target.origin!==window.location.origin || !['http:','https:','file:'].includes(target.protocol))return;
    const isHTML=target.pathname.endsWith('.html')||target.pathname.endsWith('/')||target.pathname===window.location.pathname;
    if(!isHTML)return;
    const sameDocument=pathname(target)===pathname(window.location)
      && (target.search===window.location.search || !target.search);
    if(sameDocument){
      if(!target.hash && !a.closest('#cinemaMenu'))return;
      e.preventDefault();
      if(a.closest('#cinemaMenu'))transitionSamePage(target,a);
      else finishSamePage(target);
      return;
    }
    e.preventDefault();navigate(target,a);
  },true);
  if(document.documentElement.classList.contains('agri-flow-arriving')){
    const title=safeGet(titleKey);
    if(curtainTitle)curtainTitle.textContent=(title||'AGRISHIFT').slice(0,32);
    safeDel(key);safeDel(titleKey);
    curtain.classList.remove('is-covering');
    curtain.style.pointerEvents='auto';
    // Reveal the destination from under the dark marine curtain, including deep links.
    requestAnimationFrame(()=>requestAnimationFrame(()=>curtain.classList.add('is-revealing')));
    setTimeout(()=>{
      // Reset the offscreen curtain without visibly sweeping back over the destination.
      curtain.style.transition='none';
      document.documentElement.classList.remove('agri-flow-arriving');
      curtain.classList.remove('is-revealing');
      curtain.style.pointerEvents='none';
      void curtain.offsetWidth;
      requestAnimationFrame(()=>{curtain.style.transition=''});
    },reduce.matches?90:840);
  }
  addEventListener('pageshow',e=>{
    if(e.persisted){navigating=false;curtain.classList.remove('is-covering','is-revealing');curtain.style.pointerEvents='none';document.body.classList.remove('agri-flow-navigating');closeMenu({restore:false})}
  });
})();
