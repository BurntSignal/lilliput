'use strict';
const $ = s => document.querySelector(s);
const esc = value => String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const state = {world:null,tab:'town',open:null,serverOffset:0,requestCounter:0};
const placeName = id => state.world?.buildings.find(x=>x.id===id)?.name || id;
const initials = name => String(name).split(' ').map(p=>p[0]).join('').slice(0,2);
const pct = n => Math.round(n ?? 0) + '%';
const formatTime = ts => new Intl.DateTimeFormat('en-US',{timeZone:state.world?.timezone||'America/New_York',hour:'numeric',minute:'2-digit'}).format(new Date(ts*1000));
const formatStamp = ts => new Intl.DateTimeFormat('en-US',{timeZone:state.world?.timezone||'America/New_York',weekday:'short',month:'short',day:'numeric',hour:'numeric',minute:'2-digit'}).format(new Date(ts*1000));
const intervalTime = h => {const hour=(h%24+24)%24;return `${hour%12||12}:00 ${hour<12?'AM':'PM'}`;};
function setOnline(ok){$('#connection').textContent=ok?'Town is live':'Disconnected';$('.dot').classList.toggle('off',!ok);}
function setNotice(message){const el=$('#notice');el.textContent=message;el.classList.toggle('hidden',!message);}
function tickClock(){const timestamp=Date.now()+state.serverOffset;const zone=state.world?.timezone||'America/New_York';$('#clock').textContent=new Intl.DateTimeFormat('en-US',{timeZone:zone,hour:'numeric',minute:'2-digit'}).format(new Date(timestamp));$('#date').textContent=new Intl.DateTimeFormat('en-US',{timeZone:zone,weekday:'short',month:'short',day:'numeric'}).format(new Date(timestamp));}
function switchTab(tab){
  state.tab=tab;
  document.querySelectorAll('.tab').forEach(b=>{const current=b.dataset.tab===tab;b.classList.toggle('active',current);if(current)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');});
  document.querySelectorAll('.view').forEach(s=>s.classList.toggle('hidden',s.id!==`view-${tab}`));
  if(tab==='chronicle')fetchChronicle();
}
function renderStats(){
  const w=state.world;
  $('#stat-pop').textContent=w.count;
  $('#stat-food').textContent=pct(w.world.food);
  $('#stat-harmony').textContent=pct(w.world.harmony);
  $('#stat-prosperity').textContent=pct(w.world.prosperity);
  $('#people-count').textContent=w.count+' residents';
  $('.tab-count').textContent=w.count;
}
function renderTown(){
  const w=state.world;
  $('#town-grid').innerHTML=w.buildings.map(b=>{
    const here=w.people.filter(p=>p.location===b.id);
    return `<button type="button" class="place" data-place="${esc(b.id)}" aria-label="${esc(b.name)}, ${here.length} residents present">
      <span class="place-icon" aria-hidden="true">${b.icon}</span>
      <span class="place-name">${esc(b.name)}</span>
      <span class="place-meta"><span>${esc(b.kind)}</span><span class="${here.length?'occupancy':'place-empty'}">${here.length?`<b>${here.length}</b> here`:'Empty'}</span></span>
    </button>`;
  }).join('');
}
function renderPeople(){
  const query=$('#search').value.toLowerCase().trim();
  const w=state.world;
  const filtered=w.people.filter(p=>[p.name,p.job,p.action,p.temperament,...p.traits].join(' ').toLowerCase().includes(query));
  $('#people-grid').innerHTML=filtered.map(p=>`<button type="button" class="person-card" data-person="${esc(p.id)}" aria-label="View dossier for ${esc(p.name)}">
    <span class="avatar">${esc(initials(p.name))}</span><span class="person-main"><span class="person-name">${esc(p.name)}</span><br><span class="person-job">${esc(p.job)}</span><div class="person-action">${esc(p.action)} · ${esc(placeName(p.location))}</div></span>
  </button>`).join('') || '<div class="empty">No residents match that search.</div>';
}
function renderChronicle(events){
  const icons={social:'☕',life:'◦',town:'⌂',thought:'✧',milestone:'✦'};
  $('#chronicle').innerHTML=events.map(ev=>`<article class="event"><div class="event-icon" aria-hidden="true">${icons[ev.category]||'✧'}</div><div><p>${esc(ev.message)}</p><small>${esc(formatStamp(ev.ts))}</small></div></article>`).join('') || '<div class="empty">The story is just beginning.</div>';
}
async function fetchChronicle(){
  try{const res=await fetch('/api/chronicle',{cache:'no-store'});if(!res.ok)throw Error('chronicle');const data=await res.json();if(state.tab==='chronicle')renderChronicle(data.events);}
  catch{if(state.world)renderChronicle(state.world.events);}
}
async function refresh(){
  try{
    const response=await fetch('/api/world',{cache:'no-store'});
    if(!response.ok)throw new Error('Server unavailable');
    const w=await response.json();
    state.world=w;state.serverOffset=w.now_ts*1000-Date.now();
    setOnline(true);setNotice('');renderStats();renderTown();renderPeople();
    if(state.tab==='chronicle')fetchChronicle();
    tickClock();
  }catch(err){setOnline(false);setNotice('The town server is currently unreachable. Previously loaded information may be out of date.');}
}
function openDrawer(category,html,id){
  state.open=id;
  $('#drawer-category').textContent=category;
  $('#drawer-body').innerHTML=html;
  $('#overlay').classList.remove('hidden');
  document.body.style.overflow='hidden';
  $('.drawer').focus();
}
function closeDrawer(){
  state.requestCounter++;
  $('#overlay').classList.add('hidden');document.body.style.overflow='';state.open=null;
}
function needsBar(name,value){
  return `<div class="need"><span class="need-name">${esc(name)}</span><span class="need-bar" role="meter" aria-label="${esc(name)}" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Math.round(value)}"><span class="need-fill" style="display:block;width:${Math.max(0,Math.min(100,value))}%"></span></span><span class="need-score">${Math.round(value)}</span></div>`;
}
async function showPerson(id){
  const requestNumber=++state.requestCounter;
  try{
    const response=await fetch('/api/people/'+encodeURIComponent(id),{cache:'no-store'});
    if(!response.ok)throw new Error('Unable to load dossier');
    const p=await response.json();
    if(requestNumber!==state.requestCounter)return;
    const people=state.world?.people||[];
    const links=Object.entries(p.relationships||{}).sort((a,b)=>b[1]-a[1]).slice(0,7);
    const html=`<div class="dossier-profile"><div class="avatar big-avatar">${esc(initials(p.name))}</div><div><h2 class="dossier-title">${esc(p.name)}</h2><div class="dossier-sub">${esc(p.job)} · Age ${esc(p.age)}</div></div></div>
      <div class="tags">${p.traits.map(t=>`<span class="tag">${esc(t)}</span>`).join('')}<span class="tag">${esc(p.temperament)}</span></div>
      <section class="dossier-section"><h4>The person behind the name</h4><p>${esc(p.bio)}</p></section>
      <div class="status-current"><div>RIGHT NOW · ${esc(formatTime(Date.now()/1000+state.serverOffset/1000))}</div><strong>${esc(p.action)}</strong><span>📍 ${esc(placeName(p.location))}</span></div>
      <section class="dossier-section"><h4>Life & responsibilities</h4><div class="dossier-grid">
        <div class="dossier-tile"><span class="tile-label">Home</span><strong>${esc(placeName(p.home))}</strong></div>
        <div class="dossier-tile"><span class="tile-label">Workplace</span><strong>${esc(placeName(p.workplace))}</strong></div>
        <div class="dossier-tile"><span class="tile-label">Usual shift</span><strong>${esc(intervalTime(p.shift_start))}–${esc(intervalTime(p.shift_end))}</strong></div>
        <div class="dossier-tile"><span class="tile-label">Savings</span><strong>${esc(Math.round(p.money))} town coins</strong></div>
      </div></section>
      <section class="dossier-section"><h4>Personal ambition</h4><p>${esc(p.goal)}</p></section>
      <section class="dossier-section"><h4>Well-being</h4>${needsBar('Energy',p.energy)}${needsBar('Fullness',p.hunger)}${needsBar('Morale',p.mood)}${needsBar('Social',p.social)}${needsBar('Health',p.health)}</section>
      <section class="dossier-section"><h4>Thoughts</h4><p>“${esc(p.thought)}”</p><div style="font-size:11px;color:var(--muted);margin-top:7px">${state.world.ai_enabled?'Local AI enrichment configured; everyday actions remain autonomous.':'Built-in simulation personality · Optional local AI can be enabled.'}</div></section>
      <section class="dossier-section"><h4>Friends & acquaintances</h4>${links.length?links.map(([other,score])=>{
        const q=people.find(x=>x.id===other);
        return `<div class="relationship"><button class="person-link" type="button" data-person="${esc(other)}">${esc(q?.name||other)}</button><small>${score>=72?'Close friend':score>=52?'Friend':'Acquaintance'} · ${score}/100</small></div>`;
      }).join(''):'<p>Relationships will develop with time.</p>'}</section>
      <section class="dossier-section"><h4>Private journal</h4>${(p.journal||[]).map(j=>`<div class="journal-item"><p>${esc(j.text)}</p><small>${esc(formatStamp(j.ts))}</small></div>`).join('')}</section>`;
    openDrawer('RESIDENT DOSSIER',html,id);
  }catch(err){setNotice('Could not open that resident dossier.');}
}
function showPlace(id){
  ++state.requestCounter;
  const b=state.world?.buildings.find(x=>x.id===id);if(!b)return;
  const here=state.world.people.filter(p=>p.location===id);
  const html=`<div style="font-size:43px;margin-bottom:6px">${b.icon}</div><h2 class="dossier-title">${esc(b.name)}</h2><p class="place-description">${esc(b.description)}</p><div class="status-current"><div>HERE RIGHT NOW</div><strong>${here.length} ${here.length===1?'resident':'residents'}</strong><span>Movement follows the actual time of day.</span></div>
  <section class="dossier-section"><h4>Who is here</h4>${here.length?'<div class="place-people">'+here.map(p=>`<button type="button" class="place-person" data-person="${esc(p.id)}">${esc(p.name)} · ${esc(p.action)}</button>`).join('')+'</div>':'<p>Nobody is here at the moment. Check back later.</p>'}</section>`;
  openDrawer('TOWN LOCATION',html,'place:'+id);
}
function handleClick(e){
  const person=e.target.closest('[data-person]');
  if(person){showPerson(person.dataset.person);return;}
  const place=e.target.closest('[data-place]');if(place)showPlace(place.dataset.place);
}
document.addEventListener('click',handleClick);
document.querySelectorAll('.tab').forEach(b=>b.addEventListener('click',()=>switchTab(b.dataset.tab)));
$('#search').addEventListener('input',()=>{if(state.world)renderPeople();});
$('#drawer-close').addEventListener('click',closeDrawer);
$('#overlay-shade').addEventListener('click',closeDrawer);
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeDrawer();});
refresh();setInterval(refresh,30000);setInterval(tickClock,15000);
if('serviceWorker' in navigator&&window.isSecureContext){navigator.serviceWorker.register('/sw.js').catch(()=>{});}
