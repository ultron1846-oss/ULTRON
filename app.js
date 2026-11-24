import { evaluateExpression, solveLinearEquation } from './math-engine.js?v=20261124-3';
import { supabaseBackendAudit, fetchSupabasePublicStatus } from './supabase-integration.js?v=20261124-3';
import { signInOwner, verifyOwner, signOutOwner } from './owner-auth.js?v=20261124-4';
import { saveExperience, saveMistake, getMemorySummary, listExperiences, exportMemory, importMemory } from './memory-store.js?v=20261124-3';

const pageNames = { overview:'Overview', learning:'Learn & practice', agent:'Math Agent', memory:'Memory vault', servers:'Servers & Colab', backend:'Supabase backend', settings:'Settings', owner:'Owner sign in' };
const topics = [
  {name:'Arithmetic',symbol:'＋',level:'AVAILABLE',desc:'Numbers, operations, fractions and ratios.',intro:'Arithmetic studies number systems and the operations used to calculate with them.',formula:'a + b · a − b · a × b · a ÷ b',example:'18 × 7 = 126',prereq:'Whole numbers'},
  {name:'Algebra',symbol:'x',level:'PLANNED',desc:'Expressions, equations and relationships.',intro:'Algebra represents unknown values with symbols and studies relationships between quantities.',formula:'ax + b = c',example:'2x + 3 = 11 → x = 4',prereq:'Arithmetic'},
  {name:'Geometry',symbol:'△',level:'PLANNED',desc:'Shapes, measurement and spatial reasoning.',intro:'Geometry studies points, lines, angles, shapes, distance and spatial relationships.',formula:'A rectangle = length × width',example:'A 4 by 3 rectangle has area 12 square units.',prereq:'Arithmetic'},
  {name:'Trigonometry',symbol:'∠',level:'PLANNED',desc:'Angles and relationships in triangles.',intro:'Trigonometry relates angles to side lengths and periodic functions.',formula:'sin θ = opposite / hypotenuse',example:'For a right triangle, use the side ratio relative to the chosen angle.',prereq:'Geometry'},
  {name:'Calculus',symbol:'∫',level:'PLANNED',desc:'Limits, derivatives and integrals.',intro:'Calculus studies change and accumulation through limits, derivatives and integrals.',formula:'d(xⁿ)/dx = n·xⁿ⁻¹',example:'The derivative of x² is 2x.',prereq:'Algebra and functions'},
  {name:'Linear algebra',symbol:'▦',level:'PLANNED',desc:'Vectors, matrices and linear systems.',intro:'Linear algebra studies vectors, matrices, linear transformations and systems of equations.',formula:'A x = b',example:'A matrix can represent a linear transformation.',prereq:'Algebra'},
  {name:'Probability',symbol:'P',level:'PLANNED',desc:'Chance, events and distributions.',intro:'Probability quantifies uncertainty and the likelihood of events.',formula:'P(A) = favourable outcomes / equally likely outcomes',example:'A fair coin has probability 1/2 of landing heads.',prereq:'Fractions'},
  {name:'Statistics',symbol:'σ',level:'PLANNED',desc:'Data, variation and inference.',intro:'Statistics describes data and supports conclusions while accounting for variation.',formula:'Mean = sum of values / number of values',example:'The mean of 2, 4 and 6 is 4.',prereq:'Arithmetic'},
  {name:'Number theory',symbol:'ℤ',level:'PLANNED',desc:'Integers, divisibility and primes.',intro:'Number theory investigates the properties and relationships of integers.',formula:'a = bq + r',example:'17 = 5 × 3 + 2.',prereq:'Arithmetic'},
  {name:'Logic & proofs',symbol:'∴',level:'PLANNED',desc:'Statements, arguments and proof methods.',intro:'Mathematical logic studies formal statements, valid inference and proof.',formula:'P and (P → Q) imply Q',example:'A proof must justify each inference from assumptions or established results.',prereq:'Foundational reasoning'}
];
const exercises = [
  {question:'18 × 7',answer:126,hint:'Split 7 into 5 + 2.',steps:'18 × 7 = 18 × (5 + 2) = 90 + 36 = 126.'},
  {question:'144 ÷ 12',answer:12,hint:'12 × 12 = 144.',steps:'144 ÷ 12 = 12 because 12 × 12 = 144.'},
  {question:'(15 + 9) ÷ 3',answer:8,hint:'Evaluate the parentheses first.',steps:'15 + 9 = 24, then 24 ÷ 3 = 8.'},
  {question:'3² + 4',answer:13,hint:'Square 3 before adding 4.',steps:'3² = 9, then 9 + 4 = 13.'}
];
const content=document.querySelector('#page-content');
const nav=document.querySelector('#navigation');
const safeGet=(key,fallback)=>{try{return localStorage.getItem(key)??fallback;}catch{return fallback;}};
const safeSet=(key,value)=>{try{localStorage.setItem(key,value);return true;}catch{return false;}};
const esc=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const card=(body,cls='')=>`<article class="panel ${cls}">${body}</article>`;
const heading=(eyebrow,title,subtitle,action='')=>`<div class="page-heading"><div><div class="eyebrow">${eyebrow}</div><h1>${title}</h1><p>${subtitle}</p></div>${action}</div>`;
function navigate(page){
 const key=pageNames[page]?page:'overview';
 try{
  const markup=render(key);
  content.innerHTML=markup;
  document.querySelector('#page-crumb').textContent=pageNames[key];
  nav.querySelectorAll('[data-page]').forEach(b=>b.classList.toggle('active',b.dataset.page===key));
  bind(key);
  try{history.replaceState(null,'',`#${key}`);}catch(error){console.warn('ULTRON could not update the address hash:',error);}
  document.querySelector('#sidebar').classList.remove('open');
  document.querySelector('#mobile-menu').setAttribute('aria-expanded','false');
  try{content.focus({preventScroll:true});}catch{content.focus();}
 }catch(error){
  console.error('ULTRON page render failed:',key,error);
  content.innerHTML=`<div class="page-heading"><div><div class="eyebrow">FRONTEND ERROR</div><h1>Could not open ${esc(pageNames[key])}</h1><p>The application caught an error instead of leaving the page blank.</p></div></div><div class="warning-banner" role="alert">${esc(error?.message||String(error))}</div><article class="panel"><h2>Recovery</h2><p class="muted">Try the Overview again. If this repeats, send the error text above so it can be traced to the exact module.</p><button class="outline-button" id="retry-overview" type="button">Reload overview</button></article>`;
  const retry=document.querySelector('#retry-overview');
  if(retry)retry.addEventListener('click',()=>navigate('overview'));
 }
}
function renderOverview(){
 const count=Number(safeGet('ultron-practice-count','0'))||0;
 const level=Math.min(10,Math.max(2,Number(safeGet('ultron-memory-level','6'))));
 return `${heading('CONTROL ROOM / PROJECT STATUS','ULTRON overview','A live map of what works today, what is being built next, and what remains safely disabled.','<button class="outline-button" data-page="agent">Open Math Agent →</button>')}
 <div class="hero-panel"><div><div class="eyebrow">CURRENT DEVELOPMENT STAGE</div><h2>Foundation workspace online</h2><p>ULTRON is an independent mathematics project. The browser currently provides a deterministic math engine, local practice and device-local memory. The neural model is not trained and no remote jobs are running.</p><div class="hero-meta">PUBLIC BROWSER ACCESS <i></i> MODEL UNTRAINED <i></i> TRAINING DISABLED</div></div><div class="hero-orbit" aria-hidden="true">◎</div></div>
 <div class="status-grid">
 ${[['MATH ENGINE','AVAILABLE','Arithmetic parser and limited linear equation solver.'],['LEARNING','READY','Topic roadmap and foundation exercises.'],['MEMORY VAULT','LOCAL','IndexedDB storage with manual JSON backup.'],['MODEL TRAINING','DISABLED','No model weights or training runs are active.']].map(([a,b,c])=>card(`<div class="mini-label">${a}</div><strong class="status-value">${b}</strong><p>${c}</p>`,'status-card')).join('')}
 </div>
 <div class="grid two-col">
 ${card('<div class="eyebrow">QUICK ACCESS / 01</div><h2>Math Agent</h2><p class="muted">Solve supported arithmetic expressions and simple linear equations using ULTRON’s local deterministic engine.</p><button class="outline-button" data-page="agent">Open Math Agent →</button>')}
 ${card(`<div class="eyebrow">QUICK ACCESS / 02</div><h2>Learning activity</h2><div class="big-number">${count}</div><p class="muted">Correct practice answers recorded in this browser.</p><button class="outline-button" data-page="learning">Continue practice →</button>`)}
 </div>
 <div class="grid two-col lower-grid">
 ${card('<div class="eyebrow">PROJECT ROADMAP / NEXT</div><h2>What is being built</h2><div class="capability-list"><div><b>1. Finish frontend verification</b><span class="tag available">CURRENT</span></div><div><b>2. Verify iPad navigation and storage</b><span class="tag planned">NEXT</span></div><div><b>3. Prepare Colab notebook integration</b><span class="tag planned">PLANNED</span></div><div><b>4. Validate checkpoints and resume flow</b><span class="tag planned">PLANNED</span></div></div>')}
 ${card('<div class="eyebrow">INFRASTRUCTURE / SELECTED</div><h2>Google Colab</h2><p class="muted">Colab is the selected future notebook environment. It is listed for planning only; ULTRON does not connect to it, allocate a runtime or submit jobs.</p><span class="status-pill">NOT CONNECTED</span><div style="margin-top:16px"><button class="outline-button" data-page="servers">View servers &amp; Colab →</button></div>')}
 </div>
 <div class="grid two-col lower-grid">
 ${card(`<div class="eyebrow">DEVICE MEMORY / PREFERENCE</div><h2>Preferred workload budget</h2><div class="big-number">${level} GB</div><p class="muted">Saved browser preference only. It does not allocate physical RAM or change a future Colab runtime.</p><button class="outline-button" data-page="settings">Open settings →</button>`)}
 ${card('<div class="eyebrow">BACKEND / STATUS</div><h2>Supabase connection</h2><p class="muted">The backend page checks the public read-only status endpoint. Private owner data remains protected and is not exposed to this public site.</p><button class="outline-button" data-page="backend">Inspect backend status →</button>')}
 </div>`;
}
function renderLearning(){
 const topicCards=topics.map((topic,index)=>`<button class="topic-card" type="button" data-topic-index="${index}" aria-pressed="${index===0?'true':'false'}"><span class="topic-symbol">${esc(topic.symbol)}</span><span><b>${esc(topic.name)}</b><small>${esc(topic.desc)}</small></span><span class="tag ${topic.level==='AVAILABLE'?'available':'planned'}">${esc(topic.level)}</span></button>`).join('');
 const exerciseIndex=Math.min(exercises.length-1,Math.max(0,Number(safeGet('ultron-practice-index','0'))%exercises.length));
 const exercise=exercises[exerciseIndex];
 const practiceCard=card(
  '<div class="eyebrow">FOUNDATION PRACTICE / LOCAL</div><h2>Practice an exercise</h2><p class="muted">These fixed, original exercises are checked locally by the deterministic arithmetic engine. Correct answers increase your local practice count; they do not train the neural model.</p><div class="practice-box"><div class="practice-meta"><span id="practice-number">EXERCISE '
  +(exerciseIndex+1)+' OF '+exercises.length
  +'</span><span id="practice-total">CORRECT: '+(Number(safeGet('ultron-practice-count','0'))||0)
  +'</span></div><h3 id="practice-question">'+esc(exercise.question)
  +' = ?</h3><label class="field-label" for="practice-answer">Your answer</label><input id="practice-answer" class="text-input" type="text" inputmode="decimal" autocomplete="off" placeholder="Enter your answer" maxlength="40"><div class="agent-actions"><button class="primary-button" id="practice-check" type="button">Check answer</button><button class="outline-button" id="practice-hint" type="button">Show hint</button><button class="outline-button" id="practice-next" type="button">Next exercise</button></div><p id="practice-feedback" class="practice-feedback" role="status" aria-live="polite">Work it out, then check your answer.</p><p id="practice-hint-text" class="muted small" hidden></p></div>'
 );
 return heading('LEARNING OPERATIONS / CORE PROCESS','Learn & practice','Explore the mathematics roadmap, work through verified foundation exercises and review your practice history.')
  +card('<div class="eyebrow">TOPIC LIBRARY</div><h2>Mathematics roadmap</h2><p class="muted">Select a topic to inspect its scope, prerequisite and a representative example. A planned topic is a learning outline, not a claim that the solver already supports it.</p><div class="topic-grid" id="topic-grid">'+topicCards+'</div><div class="topic-detail" id="topic-detail" aria-live="polite"><div class="eyebrow">AVAILABLE FOUNDATION</div><h3>Arithmetic</h3><p>Arithmetic studies number systems and the operations used to calculate with them.</p><p><b>Example:</b> 18 × 7 = 126</p><p class="muted">Prerequisite: Whole numbers</p></div>')
  +practiceCard
  +'<div class="grid two-col lower-grid">'
  +card('<div class="eyebrow">DATA QUALITY</div><h2>Verified learning material</h2><p class="muted">Practice material is checked before it is treated as trusted knowledge. Incorrect attempts can be stored locally as mistakes for later review.</p><ul class="feature-list"><li>Original problem statements</li><li>Deterministic answer checks</li><li>Topic and prerequisite labels</li><li>Local practice history</li></ul>')
  +card('<div class="eyebrow">MODEL SAFETY</div><h2>Practice is not training</h2><p class="muted">Completing exercises changes only local practice history. It does not generate a dataset, update neural weights, call a cloud notebook or launch a training process.</p><span class="status-pill">MODEL TRAINING DISABLED</span>')
  +'</div>';
}
function renderAgent(){
 return `${heading('MATHEMATICAL WORKSPACE / STAGE 1','Math Agent','ULTRON independently solves supported foundation questions, shows working and checks the answer through the deterministic math engine.','<span class="status-pill">LOCAL · DETERMINISTIC</span>')}
 ${card('<div class="eyebrow">CONVERSATIONAL MATHEMATICS / STAGE 1</div><h2>Talk through a maths question</h2><p class="muted">Enter a supported arithmetic expression or a one-variable linear equation. Unsupported requests are reported honestly; this is not a general-purpose AI model.</p><div class="chat-log" id="chat-log" aria-live="polite"><div class="chat-message system-message">Start with a simple arithmetic question, such as <b>12 + 5</b>, or an equation such as <b>2x + 3 = 11</b>.</div></div><label class="field-label" for="agent-input">Your message</label><textarea id="agent-input" rows="3" maxlength="240" placeholder="Example: What is 12 + 5? Or solve 2x + 3 = 11"></textarea><div class="agent-actions"><button class="primary-button" id="agent-send">Send</button><button class="outline-button" id="agent-reset">Reset conversation</button></div><div class="examples"><span>TRY:</span><button data-example="12 + 5">12 + 5</button><button data-example="(1/3) + (1/6)">(1/3) + (1/6)</button><button data-example="2x + 3 = 11">2x + 3 = 11</button></div>')}
 ${card('<div class="eyebrow">SUPPORTED OPERATIONS</div><h2>Current engine boundaries</h2><div class="capability-list"><div><b>Arithmetic</b><span class="tag available">SUPPORTED</span></div><div><b>Linear equations in x</b><span class="tag available">LIMITED</span></div><div><b>Symbolic algebra</b><span class="tag planned">NOT SUPPORTED</span></div><div><b>Calculus and proofs</b><span class="tag planned">NOT SUPPORTED</span></div></div>','compact-panel')}`;
}
function renderServers(){
 return `${heading('INFRASTRUCTURE / ORDERED ROTATION','Free compute servers','Provider directory is informational only. This page cannot start or control training.','<button class="outline-button" id="servers-refresh">↻ Refresh</button>')}
 <div id="server-alert" class="warning-banner" role="status">Loading provider directory…</div>
 ${card('<div class="eyebrow">ORDERED ROTATION</div><h2>Provider directory</h2><p class="muted">The directory is loaded from servers.json. Availability and free-tier terms can change; verify current provider terms directly before use.</p><div id="server-list" class="empty-state"><span>⌁</span><b>Checking directory</b><p>Provider information has not been verified yet.</p></div>')}
 ${card('<div class="eyebrow">EXECUTION SAFETY</div><h2>Informational only</h2><p class="muted">The public website does not authenticate with providers, submit jobs, allocate hosted memory or run training. No provider should be used until its terms and integration are independently verified.</p><span class="status-pill">REMOTE EXECUTION DISABLED</span>')}`;
}

function renderBackend(){
 const audit=supabaseBackendAudit;
 const rows=audit.services.map(service=>`<div class="capability-list"><div><b>${esc(service.name)}</b><span class="tag ${service.state==='active'?'available':'planned'}">${esc(service.label)}</span></div><p class="muted">${esc(service.detail)}</p></div>`).join('');
 const blockers=audit.blockers.map(item=>`<div class="warning-banner">${esc(item)}</div>`).join('');
 return `${heading('BACKEND / INTEGRATION AUDIT','Supabase backend','Live public status check, with private records and owner-only actions kept outside the public website.','<button class="outline-button" id="supabase-refresh" type="button">↻ Refresh status</button>')}
 <div class="status-grid">
 ${card('<div class="mini-label">PROJECT AUDIT</div><strong class="status-value">HEALTHY</strong><p>ultron-memory · ap-south-1 · inspected 24 Nov 2026.</p>','status-card')}
 ${card('<div class="mini-label">PUBLIC STATUS API</div><strong class="status-value" id="supabase-status">CHECKING</strong><p id="supabase-status-detail">Requesting generic read-only service state…</p><p class="muted small" id="supabase-status-checked">Last checked: pending</p>','status-card')}
 ${card('<div class="mini-label">DEVICE CONTROL</div><strong class="status-value">RETIRED · 410</strong><p>The deployed handler rejects legacy pairing requests.</p>','status-card')}
 ${card('<div class="mini-label">TRAINING CONTROL</div><strong class="status-value">OWNER-GATED</strong><p>Only generic public status is available here. No owner controls are exposed.</p>','status-card')}
 </div>
 ${card('<div class="eyebrow">DEPLOYED EDGE FUNCTIONS</div><h2>Service boundaries</h2>'+rows)}
 ${card('<div class="eyebrow">BACKEND SECURITY AUDIT</div><h2>Items kept outside the public frontend</h2>'+blockers)}
 ${card('<div class="eyebrow">PUBLIC WEBSITE CONTRACT</div><h2>No login. No private data. No execution.</h2><p class="muted">The browser calls only the training-control public_status action using the Supabase publishable key. The request is read-only and has a bounded timeout. It never queries database tables, sends an owner bearer token, or invokes health, status, start or stop.</p><p class="muted small">The existing experiences, knowledge, mistakes, checkpoints and backup records are owner-linked. Their row-level security is not weakened to support this no-login website. The Memory Vault therefore remains browser-local.</p><span class="status-pill">TRAINING DISABLED · REMOTE EXECUTION DISABLED</span>')}`;
}
function renderSettings(){
 const level=Math.min(10,Math.max(2,Number(safeGet('ultron-memory-level','6'))));
 return `${heading('DEVICE MEMORY SETTINGS','Settings','Local interface preferences. No account is required.')}
 ${card('<div class="eyebrow">DEVICE MEMORY SETTINGS</div><h2>Training RAM preference</h2><p class="muted">Choose a preferred memory budget for future approved remote workloads. This preference is saved in this browser only; it does not allocate device RAM or change hosted-runner memory.</p><div class="memory-box"><div class="memory-heading"><b>Preferred training memory</b><strong id="memory-value">'+level+' GB</strong></div><input class="memory-slider" id="memory-slider" type="range" min="2" max="10" step="1" value="'+level+'" aria-label="Preferred memory budget"><div class="slider-labels"><span>2 GB · Light</span><span>10 GB · High</span></div></div><div class="warning-banner">Saved in this browser only. This preference is not connected to remote training or hosted-runner memory controls.</div><p class="muted small">A future approved runtime would need to translate this preference into safe batch sizes and memory-aware settings. The slider does not change physical RAM or GPU VRAM today.</p>')}
 ${card('<div class="eyebrow">LOCAL DATA</div><h2>Browser storage</h2><p class="muted">Practice count and preferences are stored locally on this device when browser storage is available.</p><button class="outline-button" id="clear-local">Clear local preferences and practice count</button><p id="settings-result" class="muted" role="status"></p>')}`;
}
function renderMemory(){
 return `${heading('LOCAL-FIRST STORAGE / DEVICE MEMORY','Memory vault','Practice history is stored in this browser using IndexedDB. It is not uploaded to Supabase and does not sync between devices automatically.')}
 <div class="status-grid" id="memory-summary"><article class="panel status-card"><div class="mini-label">EXPERIENCES</div><strong class="status-value" id="memory-experiences">—</strong><p>Saved practice attempts</p></article><article class="panel status-card"><div class="mini-label">MISTAKES</div><strong class="status-value" id="memory-mistakes">—</strong><p>Incorrect attempts for review</p></article><article class="panel status-card"><div class="mini-label">KNOWLEDGE</div><strong class="status-value" id="memory-knowledge">—</strong><p>Reserved for future verified concepts</p></article><article class="panel status-card"><div class="mini-label">CHECKPOINTS</div><strong class="status-value" id="memory-checkpoints">—</strong><p>Reserved for future local checkpoints</p></article></div>
 ${card('<div class="eyebrow">DEVICE HISTORY</div><h2>Recent experiences</h2><p class="muted">History stays on this device and browser profile. Browser storage limits still apply; export backups periodically if you want to move the history to another device.</p><div id="memory-history" class="empty-state"><span>⌁</span><b>Loading local memory</b></div>')}
 ${card('<div class="eyebrow">PORTABILITY</div><h2>Backup and restore</h2><p class="muted">Export creates a JSON backup you can save and later import on another device. The backup may contain your entered practice content, so store it somewhere private.</p><div class="agent-actions"><button class="primary-button" id="memory-export" type="button">Export memory backup</button><label class="outline-button file-button" for="memory-import-file">Import backup</label><input id="memory-import-file" type="file" accept="application/json,.json" hidden></div><p id="memory-feedback" class="muted small" role="status"></p>')}
 ${card('<div class="eyebrow">PRIVACY BOUNDARY</div><h2>Local memory vs. Supabase</h2><p class="muted">The current Supabase memory tables are owner-protected. The public website does not read or write those private tables; the owner sign-in is limited to server-verified owner operations. The vault uses IndexedDB locally instead; no public RLS policy has been weakened.</p><span class="status-pill">NO LOGIN · NO CLOUD SYNC</span>')}`;
}

function renderOwner(){
 return heading('OWNER ACCESS / PRIVATE CONTROLS','Owner sign in','Sign in with the existing owner email and password. Public learning pages remain available without an account.')
 + card('<div class="eyebrow">SUPABASE AUTH / EXISTING ACCOUNT ONLY</div><h2>Owner session</h2><p class="muted">There is no public registration. Signing in does not grant owner privileges unless the backend verifies the configured owner identity.</p><div id="owner-auth-state" class="status-pill">CHECKING SESSION</div><form id="owner-signin-form" class="owner-form"><label class="field-label" for="owner-email">Owner email</label><div id="owner-credentials"><input class="text-input" id="owner-email" name="email" type="email" autocomplete="username" required maxlength="254" placeholder="Email address"><label class="field-label" for="owner-password">Password</label><input class="text-input" id="owner-password" name="password" type="password" autocomplete="current-password" required maxlength="256" placeholder="Password"><button class="primary-button" id="owner-signin" type="submit">Sign in</button></div><div class="agent-actions"><button class="outline-button" id="owner-check" type="button">Check connection</button><button class="outline-button" id="owner-signout" type="button" hidden>Sign out</button></div></form><p id="owner-auth-feedback" class="practice-feedback" role="status" aria-live="polite">Owner-only access is protected by server-side identity verification.</p><p class="muted small">Do not share your password. This website never creates accounts and never stores your password.</p>')
 + card('<div class="eyebrow">ACCESS BOUNDARY</div><h2>Public and owner areas</h2><ul class="feature-list"><li>Overview, learning, Math Agent and local memory remain public.</li><li>Owner identity is checked against the server-side owner configuration.</li><li>Non-owner accounts are denied even if they can authenticate.</li><li>Training and remote execution remain disabled unless separately authorized.</li></ul>');
}
function render(page){return ({owner:renderOwner,overview:renderOverview,learning:renderLearning,agent:renderAgent,memory:renderMemory,servers:renderServers,backend:renderBackend,settings:renderSettings})[page]();}
function addChat(role,text,extra=''){const node=document.createElement('div');node.className='chat-message '+(role==='user'?'user-message':'system-message');const label=document.createElement('b');label.textContent=role==='user'?'YOU':'ULTRON';const body=document.createElement('p');body.textContent=text;node.append(label,body);if(extra){const detail=document.createElement('small');detail.textContent=extra;node.append(detail);}document.querySelector('#chat-log').append(node);}
function answerAgent(){
 const input=document.querySelector('#agent-input');const raw=input.value.trim();if(!raw)return;
 addChat('user',raw);input.value='';
 const equation=raw.match(/(?:solve\s+)?([0-9xX+*/().\s^=-]+=[0-9xX+*/().\s^=-]+)/i);
 const expression=raw.replace(/^(what is|calculate|compute)\s+/i,'').replace(/[?]$/,'').trim();
 try{
  if(equation){const result=solveLinearEquation(equation[1].replace(/\s+/g,''));const text=result.kind==='unique'?`Solution: x = ${result.value}.`:result.kind==='none'?'This equation has no solution.':'Every real value of x is a solution.';addChat('assistant',text,'Solved by the deterministic linear-equation routine.');}
  else if(/^[0-9+*/().\s^×÷−-]+$/.test(expression)){const value=evaluateExpression(expression);addChat('assistant',`Result: ${value}`,`Expression: ${expression}. Evaluated by the deterministic arithmetic parser.`);}
  else addChat('assistant','I cannot safely identify a supported arithmetic expression or linear equation in that message. Try an expression such as (12 + 8) / 4 or an equation such as 2x + 3 = 11.','Unsupported requests are not guessed.');
 }catch(error){addChat('assistant',`I could not solve that input: ${error.message}`,'Check the syntax and supported-operation limits.');}
}
async function loadSupabaseStatus(){
 const status=document.querySelector('#supabase-status');
 const detail=document.querySelector('#supabase-status-detail');
 const checked=document.querySelector('#supabase-status-checked');
 const refresh=document.querySelector('#supabase-refresh');
 if(!status||!detail)return;
 if(refresh)refresh.disabled=true;
 status.textContent='CHECKING';
 detail.textContent='Requesting generic read-only service state…';
 if(checked)checked.textContent='Last checked: in progress';
 try{
  const result=await fetchSupabasePublicStatus();
  status.textContent='ONLINE';
  detail.textContent=`Control plane: online · Model: ${result.model_status||'unknown'} · Training: disabled · Remote execution: disabled.`;
  if(checked){
   const stamp=result.checked_at?new Date(result.checked_at):new Date();
   checked.textContent='Last checked: '+(Number.isNaN(stamp.getTime())?'just now':stamp.toLocaleString());
  }
 }catch(error){
  status.textContent='UNAVAILABLE';
  detail.textContent=error?.message||'The public status endpoint could not be reached.';
  if(checked)checked.textContent='Last checked: '+new Date().toLocaleString();
 }finally{
  if(refresh)refresh.disabled=false;
 }
}
function bindLearning(){
 const detail=document.querySelector('#topic-detail');
 content.querySelectorAll('[data-topic-index]').forEach(button=>button.addEventListener('click',()=>{
  const index=Number(button.dataset.topicIndex);const topic=topics[index];if(!topic)return;
  content.querySelectorAll('[data-topic-index]').forEach(item=>item.setAttribute('aria-pressed',String(item===button)));
  detail.innerHTML=`<div class="eyebrow">${esc(topic.level==='AVAILABLE'?'AVAILABLE FOUNDATION':'ROADMAP TOPIC')}</div><h3>${esc(topic.symbol)} ${esc(topic.name)}</h3><p>${esc(topic.intro)}</p><p><b>Core idea:</b> ${esc(topic.formula)}</p><p><b>Example:</b> ${esc(topic.example)}</p><p class="muted">Prerequisite: ${esc(topic.prereq)}</p>`;
 }));
 let index=Math.min(exercises.length-1,Math.max(0,Number(safeGet('ultron-practice-index','0'))%exercises.length));
 let completed=false;
 const question=document.querySelector('#practice-question');
 const input=document.querySelector('#practice-answer');
 const feedback=document.querySelector('#practice-feedback');
 const hint=document.querySelector('#practice-hint-text');
 const number=document.querySelector('#practice-number');
 const total=document.querySelector('#practice-total');
 const showExercise=()=>{
  const item=exercises[index];completed=false;question.textContent=item.question+' = ?';number.textContent=`EXERCISE ${index+1} OF ${exercises.length}`;input.value='';input.disabled=false;hint.hidden=true;hint.textContent='';feedback.textContent='Work it out, then check your answer.';feedback.className='practice-feedback';document.querySelector('#practice-check').disabled=false;
 };
 document.querySelector('#practice-check').addEventListener('click',async()=>{
  if(completed)return;const item=exercises[index];const value=input.value.trim();let numeric;
  try{if(!value)throw new Error('Enter an answer first.');numeric=evaluateExpression(value);}catch(error){feedback.textContent=error.message||'Enter a valid mathematical expression.';feedback.className='practice-feedback error';return;}
  const correct=Math.abs(numeric-item.answer)<1e-9;
  try{await saveExperience({prompt:item.question,answer:value,correct,topic:'Arithmetic',explanation:item.steps});if(!correct)await saveMistake({prompt:item.question,answer:value,correct:false,topic:'Arithmetic',explanation:item.steps});}catch(error){feedback.textContent=`Practice result recorded in this session, but local memory could not save it: ${error.message}`;feedback.className='practice-feedback error';}
  if(correct){completed=true;const count=(Number(safeGet('ultron-practice-count','0'))||0)+1;safeSet('ultron-practice-count',String(count));total.textContent='CORRECT: '+count;feedback.textContent='Correct. '+item.steps;feedback.className='practice-feedback success';input.disabled=true;document.querySelector('#practice-check').disabled=true;}
  else{feedback.textContent='Not quite. Try again, or reveal a hint. Incorrect attempts are kept in local memory when available.';feedback.className='practice-feedback error';}
 });
 document.querySelector('#practice-hint').addEventListener('click',()=>{hint.textContent=exercises[index].hint;hint.hidden=false;});
 document.querySelector('#practice-next').addEventListener('click',()=>{index=(index+1)%exercises.length;safeSet('ultron-practice-index',String(index));showExercise();});
 showExercise();
}
async function loadMemoryPage(){
 const feedback=document.querySelector('#memory-feedback');const history=document.querySelector('#memory-history');
 try{
  const summary=await getMemorySummary();
  for(const [key,id] of Object.entries({experiences:'memory-experiences',mistakes:'memory-mistakes',knowledge:'memory-knowledge',checkpoints:'memory-checkpoints'}))document.querySelector('#'+id).textContent=summary[key]??0;
  const records=await listExperiences(50);
  history.innerHTML=records.length?records.map(record=>`<div class="memory-record"><div><b>${esc(record.prompt)}</b><p>${esc(record.answer||'No answer recorded')} · ${esc(record.topic||'Uncategorized')}</p><small>${esc(new Date(record.createdAt).toLocaleString())}</small></div><span class="tag ${record.correct?'available':'planned'}">${record.correct?'CORRECT':'REVIEW'}</span></div>`).join(''):'<div class="empty-state"><span>—</span><b>No experiences saved yet</b><p>Complete a practice exercise to create your first local memory.</p></div>';
 }catch(error){history.innerHTML=`<div class="empty-state"><span>!</span><b>Local memory unavailable</b><p>${esc(error.message)}</p></div>`;feedback.textContent='This browser may not support IndexedDB or may be in a restricted private-browsing context.';}
 document.querySelector('#memory-export').addEventListener('click',async()=>{
  try{const backup=await exportMemory();const blob=new Blob([JSON.stringify(backup,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download='ultron-memory-backup.json';link.click();URL.revokeObjectURL(url);feedback.textContent='Memory backup prepared. Check your browser downloads.';}catch(error){feedback.textContent='Could not export memory: '+error.message;}
 });
 document.querySelector('#memory-import-file').addEventListener('change',async event=>{
  const file=event.target.files?.[0];if(!file)return;
  try{if(file.size>20*1024*1024)throw new Error('Backup file exceeds the 20 MB import limit.');const payload=JSON.parse(await file.text());const result=await importMemory(payload);feedback.textContent=`Imported ${result.imported} records. Refreshing memory view…`;navigate('memory');}catch(error){feedback.textContent='Import failed: '+error.message;}finally{event.target.value='';}
 });
}
async function loadServers(){
 const alert=document.querySelector('#server-alert');const list=document.querySelector('#server-list');if(!alert||!list)return;
 alert.textContent='Loading provider directory…';list.innerHTML='<div class="empty-state"><span>⌁</span><b>Checking directory</b></div>';
 try{
  const response=await fetch('./servers.json',{cache:'no-store'});
  if(!response.ok)throw new Error(`Could not load servers.json (HTTP ${response.status})`);
  const data=await response.json();const entries=Array.isArray(data)?data:data.providers;
  if(!Array.isArray(entries))throw new Error('Provider directory format is invalid.');
  alert.textContent='Provider directory loaded. Availability and terms still require direct verification.';
  list.innerHTML=entries.length?entries.map((item,i)=>{const url=typeof item.url==='string'&&/^https:\/\//i.test(item.url)?item.url:'';const label=String(item.status||'NOT VERIFIED');return `<div class="server-row"><span class="server-number">${i+1}</span><div><b>${esc(item.name||'Unnamed provider')}</b><p>${esc(item.description||item.capabilities||'No capability description supplied.')}</p><p>${esc(item.role||'Informational directory entry')}</p>${url?`<a class="server-link" href="${esc(url)}" target="_blank" rel="noopener noreferrer">Official provider site ↗</a>`:''}</div><span class="tag planned">${esc(label)}</span></div>`;}).join(''):'<div class="empty-state"><span>—</span><b>No providers listed</b><p>The directory contains no providers.</p></div>';
 }catch(error){alert.textContent=`Provider directory unavailable: ${error.message}. Provider terms metadata unavailable; verify current terms directly before using a provider.`;list.innerHTML='<div class="empty-state"><span>!</span><b>Provider directory unavailable</b><p>Check the deployed servers.json path and refresh. No provider is assumed available.</p></div>';}
}
async function bindOwner(){
 const form=document.querySelector('#owner-signin-form'),credentials=document.querySelector('#owner-credentials'),feedback=document.querySelector('#owner-auth-feedback'),state=document.querySelector('#owner-auth-state'),signin=document.querySelector('#owner-signin'),check=document.querySelector('#owner-check'),signout=document.querySelector('#owner-signout');
 const show=async()=>{try{const result=await verifyOwner();if(result.isOwner){state.textContent='OWNER VERIFIED';feedback.textContent='Signed in as '+(result.email||'owner')+'. Server-side owner verification succeeded.';credentials.hidden=true;signout.hidden=false;}else if(result.signedIn){state.textContent='NOT OWNER';feedback.textContent=result.message||'This account does not have owner access.';credentials.hidden=false;signout.hidden=false;}else{state.textContent='SIGNED OUT';feedback.textContent='Sign in with the existing owner email and password.';credentials.hidden=false;signout.hidden=true;}}catch(error){state.textContent='UNVERIFIED';feedback.textContent=error.message||'Could not verify owner session.';credentials.hidden=false;}};
 await show();
 form.addEventListener('submit',async event=>{event.preventDefault();signin.disabled=true;feedback.textContent='Signing in and verifying owner identity…';try{await signInOwner(document.querySelector('#owner-email').value,document.querySelector('#owner-password').value);document.querySelector('#owner-password').value='';await show();}catch(error){feedback.textContent=error.message||'Sign-in failed.';state.textContent='SIGN-IN FAILED';}finally{signin.disabled=false;}});
 check.addEventListener('click',show);
 signout.addEventListener('click',async()=>{signout.disabled=true;try{await signOutOwner();await show();}catch(error){feedback.textContent=error.message;}finally{signout.disabled=false;}});
}
function bind(page){
 if(page==='owner')bindOwner();
 if(page==='learning')bindLearning();
 if(page==='memory')loadMemoryPage();
 content.querySelectorAll('[data-page]').forEach(el=>el.addEventListener('click',()=>navigate(el.dataset.page)));
 if(page==='agent'){
  document.querySelector('#agent-send').addEventListener('click',answerAgent);
  document.querySelector('#agent-input').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();answerAgent();}});
  document.querySelector('#agent-reset').addEventListener('click',()=>{document.querySelector('#chat-log').innerHTML='<div class="chat-message system-message">Conversation reset. Enter a supported arithmetic expression or linear equation.</div>';});
  content.querySelectorAll('[data-example]').forEach(b=>b.addEventListener('click',()=>{document.querySelector('#agent-input').value=b.dataset.example;document.querySelector('#agent-input').focus();}));
 }
 if(page==='servers'){document.querySelector('#servers-refresh').addEventListener('click',loadServers);loadServers();}
 if(page==='backend'){document.querySelector('#supabase-refresh').addEventListener('click',loadSupabaseStatus);loadSupabaseStatus();}
 if(page==='settings'){
  const slider=document.querySelector('#memory-slider');
  slider.addEventListener('input',()=>{document.querySelector('#memory-value').textContent=slider.value+' GB';safeSet('ultron-memory-level',slider.value);});
  document.querySelector('#clear-local').addEventListener('click',()=>{try{['ultron-memory-level','ultron-practice-count'].forEach(k=>localStorage.removeItem(k));document.querySelector('#memory-value').textContent='6 GB';slider.value='6';document.querySelector('#settings-result').textContent='Local preferences and practice count cleared.';}catch{document.querySelector('#settings-result').textContent='Browser storage is unavailable.';}});
 }
}
nav.addEventListener('click',e=>{const b=e.target.closest('[data-page]');if(b)navigate(b.dataset.page);});
document.querySelector('#mobile-menu').addEventListener('click',()=>{const open=document.querySelector('#sidebar').classList.toggle('open');document.querySelector('#mobile-menu').setAttribute('aria-expanded',String(open));});
document.querySelector('#theme-toggle').addEventListener('click',()=>document.body.classList.toggle('soft-contrast'));
navigate(location.hash.slice(1)||'overview');
