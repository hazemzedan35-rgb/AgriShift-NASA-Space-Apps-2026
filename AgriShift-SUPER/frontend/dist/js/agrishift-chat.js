/* AgriShift floating assistant. Loaded on every page. Talks to the dashboard server at ENDPOINT.
 * AR/EN interface, formatted answers, and a Start button when the local server is not running. */
(()=>{
  'use strict';
  if(document.getElementById('agriChatRoot'))return;
  const config=window.AGRISHIFT_CHAT_CONFIG||{};
  const ENDPOINT=typeof config.endpoint==='string'?config.endpoint.trim():'';
  const STORAGE_KEY='agrishift:chat:session-v1',LANG_KEY='agrishift:chat:lang';
  const MAX_HISTORY=24,MAX_MESSAGE=2000,MAX_REPLY=6000;
  const SERVER='http://127.0.0.1:8000';
  const T={
    en:{dir:'ltr',lang:'ع',title:'AgriShift Assistant',sub:'Crop & climate assistant',launch:'Ask AgriShift',status:'Connecting when you send',ok:'Connected',fail:'Connection unavailable',
      wH:'Grow with clarity.',wP:'Ask about planting dates, soil, irrigation, pests and crop rotation. Answers use NASA POWER data and FAO methods.',ph:'Ask about your crops...',
      foot:'Research support only · Check local agricultural guidance',you:'YOU',sys:'SYSTEM',typing:'Searching sources and NASA data…',slow:'The request took too long. Please try again.',
      down:'The AgriShift server is not running.',start:'Start AgriShift',hint:'If nothing happens, double-click START-WINDOWS.bat in the project folder (run INSTALL-ONE-CLICK-START.bat once to enable this button).',
      waiting:'Starting the server… the first start can take up to a minute.',up:'The server is running. Ask your question again.',live:'Open the live dashboard',
      nokey:'The AI key is missing. Add GEMINI_API_KEY to the .env file, then restart the server.',busy:'Too many requests. Wait a minute and try again.',err:'Could not get a reply. Please try again.',
      chips:[['Best time to plant wheat','What is the best time of year to plant wheat?'],['Strawberry soil','What soil conditions are best for growing strawberries?'],['Rotation after maize','What is the best crop rotation after harvesting maize?'],['Plant details','Give me comprehensive details about the plant: ',1]]},
    ar:{dir:'rtl',lang:'EN',title:'مساعد AgriShift',sub:'مساعد المحاصيل والمناخ',launch:'اسأل AgriShift',status:'يتصل عند الإرسال',ok:'متصل',fail:'الاتصال غير متاح',
      wH:'ازرع بوضوح.',wP:'اسأل عن مواعيد الزراعة والتربة والري والآفات والدورة الزراعية. الإجابات تعتمد على بيانات NASA POWER ومنهج FAO.',ph:'اسأل عن محاصيلك...',
      foot:'دعم بحثي · راجع الإرشاد الزراعي المحلي',you:'أنت',sys:'النظام',typing:'جاري البحث في المصادر وبيانات NASA…',slow:'استغرق الطلب وقتًا طويلًا. حاول مرة أخرى.',
      down:'سيرفر AgriShift غير شغال.',start:'تشغيل AgriShift',hint:'لو لم يحدث شيء، اضغط مرتين على START-WINDOWS.bat في مجلد المشروع (وشغّل INSTALL-ONE-CLICK-START.bat مرة واحدة لتفعيل هذا الزر).',
      waiting:'جاري تشغيل السيرفر… أول تشغيل قد يستغرق دقيقة.',up:'السيرفر شغال. اسأل سؤالك مرة أخرى.',live:'افتح الداشبورد الحي',
      nokey:'مفتاح الذكاء الاصطناعي غير موجود. أضف GEMINI_API_KEY في ملف .env ثم أعد تشغيل السيرفر.',busy:'طلبات كثيرة. انتظر دقيقة وحاول مرة أخرى.',err:'تعذّر الحصول على رد. حاول مرة أخرى.',
      chips:[['أنسب وقت لزراعة القمح','ما هو أنسب وقت لزراعة القمح في السنة؟'],['تربة الفراولة','ما هي تفاصيل التربة المناسبة لزراعة الفراولة؟'],['الدورة بعد الذرة','ما هي الدورة الزراعية المثلى بعد حصاد الذرة؟'],['تفاصيل نبات','قدّم تفاصيل شاملة عن نبات: ',1]]}
  };
  let lang='en';
  try{lang=localStorage.getItem(LANG_KEY)||((navigator.language||'').toLowerCase().startsWith('ar')?'ar':'en')}catch{}
  if(!T[lang])lang='en';
  const tr=()=>T[lang];
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const md=t=>esc(t).replace(/^#{1,4}[ \t]*(.+)$\n?/gm,'<h4>$1</h4>').replace(/\*\*(.+?)\*\*/g,'<b>$1</b>').replace(/^[ \t]*[-*][ \t]+/gm,'• ')
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g,'<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
  const body=document.body;
  const root=document.createElement('aside');
  root.className='agri-chat-root';root.id='agriChatRoot';root.dataset.connected=ENDPOINT?'pending':'no';
  root.setAttribute('aria-label','AgriShift assistant');
  root.innerHTML=`
    <section class="agri-chat-panel" id="agriChatPanel" role="dialog" aria-label="AgriShift crop and climate assistant" aria-hidden="true" hidden>
      <header class="agri-chat-header">
        <span class="agri-chat-avatar"><img src="dist/img/agrishift-mark.svg" alt="" /></span>
        <span class="agri-chat-heading"><strong id="agriChatTitle"></strong><span class="agri-chat-status"><span class="agri-chat-dot" aria-hidden="true"></span><span id="agriChatStatus"></span></span></span>
        <span class="agri-chat-head-actions"><button class="agri-chat-action agri-chat-lang" id="agriChatLang" type="button" title="English / العربية" aria-label="Switch language"></button><button class="agri-chat-action" id="agriChatClear" type="button" title="Clear conversation" aria-label="Clear conversation"><svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14M10 10v7M14 10v7"/></svg></button><button class="agri-chat-action" id="agriChatClose" type="button" title="Close" aria-label="Close assistant"><svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg></button></span>
      </header>
      <div class="agri-chat-messages" id="agriChatMessages" role="log" aria-live="polite" aria-relevant="additions text">
        <div class="agri-chat-welcome" id="agriChatWelcome"><div class="agri-chat-welcome-icon" aria-hidden="true">✳</div><strong id="agriChatWH"></strong><p id="agriChatWP"></p></div>
      </div>
      <div class="agri-chat-suggestions" id="agriChatChips" aria-label="Suggested questions"></div>
      <form class="agri-chat-form" id="agriChatForm"><label class="agri-chat-input-wrap" for="agriChatInput"><textarea class="agri-chat-input" id="agriChatInput" rows="1" maxlength="${MAX_MESSAGE}" aria-label="Message the assistant"></textarea></label><button class="agri-chat-send" type="submit" id="agriChatSend" aria-label="Send message"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m5 12 14-7-4 14-3-7-7 0Z"/><path d="m12 12 7-7"/></svg></button></form>
      <div class="agri-chat-footnote" id="agriChatFoot"></div>
    </section>
    <button class="agri-chat-launch" id="agriChatLaunch" type="button" aria-expanded="false" aria-controls="agriChatPanel" aria-label="Open AgriShift assistant"><span class="agri-chat-launch-text"><strong id="agriChatLT"></strong><small id="agriChatLS"></small></span><span class="agri-chat-launch-disc"><img src="dist/img/agrishift-mark.svg" alt="" /></span></button>`;
  body.append(root);
  const $=sel=>root.querySelector(sel);
  const panel=$('#agriChatPanel'),launch=$('#agriChatLaunch'),input=$('#agriChatInput');
  const form=$('#agriChatForm'),send=$('#agriChatSend'),messages=$('#agriChatMessages'),status=$('#agriChatStatus'),chips=$('#agriChatChips');
  let history=[],pending=false,open=false,lastFocus=null,activeController=null,pollTimer=null;
  const safeGet=()=>{try{return sessionStorage.getItem(STORAGE_KEY)}catch{return null}};
  const safeSet=()=>{try{sessionStorage.setItem(STORAGE_KEY,JSON.stringify(history.slice(-MAX_HISTORY)))}catch{}};
  const safeRemove=()=>{try{sessionStorage.removeItem(STORAGE_KEY)}catch{}};
  function updateStatus(text,connected){status.textContent=text;root.dataset.connected=connected}
  function applyLang(){
    const t=tr();panel.dir=t.dir;
    $('#agriChatTitle').textContent=t.title;$('#agriChatLT').textContent=t.launch;$('#agriChatLS').textContent=t.sub;
    $('#agriChatWH').textContent=t.wH;$('#agriChatWP').textContent=t.wP;$('#agriChatFoot').textContent=t.foot;
    $('#agriChatLang').textContent=t.lang;input.placeholder=t.ph;
    if(root.dataset.connected==='pending'||root.dataset.connected==='no')status.textContent=t.status;
    chips.innerHTML='';
    t.chips.forEach(([label,prompt,fill])=>{const b=document.createElement('button');b.className='agri-chat-suggest';b.type='button';b.textContent=label;b.dataset.chatPrompt=prompt;if(fill)b.dataset.fill='1';chips.append(b)});
  }
  function addMessage(role,content,record=true){
    const t=tr(),div=document.createElement('div');div.className='agri-chat-message';div.dataset.role=role;
    const title=document.createElement('span');title.className='agri-chat-message-label';title.textContent=role==='user'?t.you:role==='assistant'?'AGRISHIFT':t.sys;
    const bubble=document.createElement('div');bubble.className='agri-chat-bubble';
    if(role==='assistant')bubble.innerHTML=md(content);else bubble.textContent=String(content??'');
    div.append(title,bubble);messages.append(div);
    if(record&&(role==='user'||role==='assistant')){
      history.push({role,content:String(content??'').slice(0,role==='assistant'?MAX_REPLY:MAX_MESSAGE)});
      history=history.slice(-MAX_HISTORY);safeSet();
    }
    messages.scrollTop=messages.scrollHeight;
    return div;
  }
  function renderHistory(){
    const raw=safeGet();if(!raw)return;
    try{const parsed=JSON.parse(raw);if(!Array.isArray(parsed))return;
      parsed.slice(-MAX_HISTORY).forEach(m=>{if((m?.role==='user'||m?.role==='assistant')&&typeof m.content==='string'&&m.content.length<=MAX_REPLY)addMessage(m.role,m.content,false)});
      history=parsed.filter(m=>(m?.role==='user'||m?.role==='assistant')&&typeof m.content==='string').slice(-MAX_HISTORY);
      if(history.length)$('#agriChatWelcome').style.display='none';
    }catch{safeRemove()}
  }
  function setOpen(value){
    if(open===value)return;
    open=value;
    if(open){
      lastFocus=document.activeElement;
      panel.hidden=false;panel.setAttribute('aria-hidden','false');
      root.classList.add('is-open');launch.setAttribute('aria-expanded','true');launch.setAttribute('aria-label','Close AgriShift assistant');
      setTimeout(()=>{if(open)input.focus({preventScroll:true})},60);
      messages.scrollTop=messages.scrollHeight;
    }else{
      root.classList.remove('is-open');launch.setAttribute('aria-expanded','false');launch.setAttribute('aria-label','Open AgriShift assistant');
      panel.setAttribute('aria-hidden','true');panel.hidden=true;
      if(lastFocus?.isConnected&&lastFocus!==document.body){lastFocus.focus({preventScroll:true})}else launch.focus({preventScroll:true});
    }
  }
  function setBusy(value){pending=value;send.disabled=value;input.disabled=value;root.querySelectorAll('[data-chat-prompt]').forEach(el=>el.disabled=value)}
  function typing(){
    const el=document.createElement('div');el.className='agri-chat-typing';el.setAttribute('aria-label',tr().typing);
    for(let i=0;i<3;i++)el.append(document.createElement('span'));
    const label=document.createElement('small');label.className='agri-chat-typing-label';label.textContent=tr().typing;el.append(label);
    messages.append(el);messages.scrollTop=messages.scrollHeight;return el;
  }
  // Server not running: show a Start button and wait until the server answers.
  function startHelp(){
    const t=tr();
    const div=addMessage('notice',t.down,false);
    const bubble=div.querySelector('.agri-chat-bubble');
    const a=document.createElement('a');a.className='agri-chat-start';a.href='agrishift://start';a.textContent=t.start;
    const hint=document.createElement('div');hint.className='agri-chat-start-hint';hint.textContent=t.hint;
    bubble.append(document.createElement('br'),a,hint);
    a.addEventListener('click',()=>{
      hint.textContent=t.waiting;clearInterval(pollTimer);let n=0;
      pollTimer=setInterval(async()=>{
        n++;
        try{await fetch(SERVER+'/assistant/api/health',{mode:'no-cors',cache:'no-store'});clearInterval(pollTimer);
          if(location.protocol==='file:'){const l=document.createElement('a');l.className='agri-chat-start';l.href=SERVER+'/dashboard.html';l.textContent=t.live;hint.replaceChildren(l)}
          else{hint.textContent=t.up;updateStatus(t.ok,'yes')}
        }catch{if(n>45){clearInterval(pollTimer);hint.textContent=t.hint}}
      },2000);
    });
  }
  function friendly(message){
    const t=tr();
    if(/not configured/i.test(message))return t.nokey;
    if(/too many requests/i.test(message)||/^429/.test(message))return t.busy;
    return message&&!/^HTTP \d+$/.test(message)&&!/^Unexpected/.test(message)?message:t.err;
  }
  async function ask(text){
    const query=text.trim();if(!query||pending)return;
    $('#agriChatWelcome').style.display='none';
    addMessage('user',query);input.value='';input.style.height='auto';
    setBusy(true);const indicator=typing();
    const controller=new AbortController();activeController=controller;
    const timeout=setTimeout(()=>controller.abort(),Math.max(3000,Number(config.timeoutMs)||25000));
    try{
      const createPayload=typeof config.createPayload==='function'?config.createPayload:(({message,history,page})=>({message,history,page}));
      const payload=createPayload({message:query,history:history.slice(0,-1),page:location.pathname+location.hash});
      const response=await fetch(ENDPOINT,{method:'POST',headers:{'Content-Type':'application/json','Accept':'application/json, text/plain'},body:JSON.stringify(payload),credentials:'same-origin',signal:controller.signal});
      const type=response.headers.get('content-type')||'';
      const data=type.includes('json')?await response.json().catch(()=>null):await response.text();
      if(!response.ok)throw new Error((data&&(data.detail||data.error))||`HTTP ${response.status}`);
      const getReply=typeof config.getReply==='function'?config.getReply:(d=>d?.reply??d?.answer??d?.message??d?.response);
      const answer=getReply(data);
      if(typeof answer!=='string'||!answer.trim())throw new Error('Unexpected reply format');
      indicator.remove();addMessage('assistant',answer);updateStatus(tr().ok,'yes');
    }catch(error){
      indicator.remove();
      if(error?.name==='AbortError'){addMessage('notice',tr().slow,false);updateStatus(tr().fail,'fail')}
      else if(error instanceof TypeError){startHelp();updateStatus(tr().fail,'fail')}
      else{addMessage('notice',friendly(String(error?.message||'')),false);updateStatus(tr().fail,'fail')}
    }finally{clearTimeout(timeout);activeController=null;setBusy(false);input.focus({preventScroll:true})}
  }
  applyLang();renderHistory();
  launch.addEventListener('click',()=>setOpen(!open));
  $('#agriChatClose').addEventListener('click',()=>setOpen(false));
  $('#agriChatLang').addEventListener('click',()=>{lang=lang==='en'?'ar':'en';try{localStorage.setItem(LANG_KEY,lang)}catch{}applyLang();input.focus({preventScroll:true})});
  $('#agriChatClear').addEventListener('click',()=>{
    if(activeController)activeController.abort();clearInterval(pollTimer);
    history=[];safeRemove();messages.querySelectorAll('.agri-chat-message,.agri-chat-typing').forEach(el=>el.remove());
    $('#agriChatWelcome').style.display='';input.value='';input.focus({preventScroll:true});
  });
  chips.addEventListener('click',e=>{const b=e.target.closest('[data-chat-prompt]');if(!b||b.disabled)return;
    if(b.dataset.fill){input.value=b.dataset.chatPrompt;input.focus();return}
    ask(b.dataset.chatPrompt||'')});
  form.addEventListener('submit',event=>{event.preventDefault();ask(input.value)});
  input.addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.shiftKey&&!event.isComposing){event.preventDefault();ask(input.value)}});
  input.addEventListener('input',()=>{input.style.height='auto';input.style.height=Math.min(input.scrollHeight,108)+'px'});
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&open){event.preventDefault();setOpen(false)}});
  document.addEventListener('pointerdown',event=>{if(open&&!root.contains(event.target)){setOpen(false)}});
  document.querySelectorAll('[data-menu-open]').forEach(button=>button.addEventListener('click',()=>{if(open)setOpen(false)}));
})();
