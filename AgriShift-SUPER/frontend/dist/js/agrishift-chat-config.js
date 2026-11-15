/* The chatbot runs inside the same FastAPI server at /assistant/api/chat.
   Gemini credentials are strictly server-side, never embed keys in JavaScript. */
window.AGRISHIFT_CHAT_CONFIG = {
  endpoint: '/assistant/api/chat',
  timeoutMs: 120000,
  createPayload: ({message, history, page}) => {
    const latInput=document.getElementById('latitude');
    const lonInput=document.getElementById('longitude');
    const hasLat=latInput && latInput.value.trim()!=='' && Number.isFinite(Number(latInput.value));
    const hasLon=lonInput && lonInput.value.trim()!=='' && Number.isFinite(Number(lonInput.value));
    const lat=hasLat?Number(latInput.value):30.5;
    const lon=hasLon?Number(lonInput.value):31.5;
    const msgs=history.filter(m=>m && (m.role==='user'||m.role==='assistant') && typeof m.content==='string')
      .slice(-11).map(m=>({role:m.role,content:m.content.slice(0,2000)}));
    msgs.push({role:'user',content:message});
    return {messages:msgs,lat,lon,
      place:hasLat&&hasLon ? `Farmer-selected coordinates ${lat}, ${lon}` : 'DEFAULT DEMONSTRATION POINT: Nile Delta reference (farm location not provided)',
      lang: /[\u0600-\u06FF]/.test(message)?'ar':'en'};
  },
  getReply: (data) => data?.reply ?? null
};
