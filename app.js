import { evaluateExpression, solveLinearEquation } from './math-engine.js';
import { supabaseBackendAudit } from './supabase-integration.js';

const pageNames = { overview:'Overview', learning:'How ULTRON learns', agent:'Math Agent', servers:'Servers', backend:'Supabase backend', settings:'Settings' };
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
 document.querySelector('#page-crumb').textContent=pageNames[key];
 nav.querySelectorAll('[data-page]').forEach(b=>b.classList.toggle('active',b.dataset.page===key));
 content.innerHTML=render(key); bind(key);
 history.replaceState(null,'',`#${key}`);
 document.querySelector('#sidebar').classList.remove('open');
 document.querySelector('#mobile-menu').setAttribute('aria-expanded','false');
 content.focus({preventScroll:true});
}
function renderOverview(){
 const count=Number(safeGet('ultron-practice-count','0'));
 return `${heading('TRAINING OPERATIONS / OVERVIEW','System overview','Public browser mode · no account-specific data','<button class="outline-button" data-page="agent">Open Math Agent →</button>')}
 <div class="hero-panel"><div><div class="eyebrow">WHAT DO I DO NEXT?</div><h2>ULTRON is not training</h2><p>This public website provides the mathematics workspace and system information. The neural model is untrained and remote execution is not enabled.</p><div class="hero-meta">PUBLIC BROWSER ACCESS <i></i> NEURAL MODEL UNTRAINED <i></i> TRAINING DISABLED</div></div><div class="hero-orbit" aria-hidden="true">◎</div></div>
 <div class="status-grid">
 ${[['NEURAL MODEL','UNTRAINED','No neural weights have been trained.'],['MATH AGENT','AVAILABLE','Deterministic foundation solver.'],['PROOF CHECKER','LIMITED','No general proof checker is implemented.'],['TRAINING','DISABLED','No training run is authorized.']].map(([a,b,c])=>card(`<div class="mini-label">${a}</div><strong class="status-value">${b}</strong><p>${c}</p>`,'status-card')).join('')}
 </div>
 <div class="grid two-col">
 ${card('<div class="eyebrow">MODEL PROGRESS</div><h2>Neural model evaluation</h2><div class="empty-state"><span>—</span><b>Not available</b><p>No trained model or evaluation results exist yet.</p></div>')}
 ${card('<div class="eyebrow">TRAINING TELEMETRY</div><h2>Learning curve</h2><div class="empty-state"><span>—</span><b>No telemetry</b><p>Training is disabled. No loss values or training curves are being generated.</p></div>')}
 </div>
 <div class="grid two-col lower-grid">
 ${card(`<div class="eyebrow">MATHEMATICAL CAPABILITIES</div><h2>Available foundation</h2><div class="capability-list"><div><b>Arithmetic parser</b><span class="tag available">AVAILABLE</span></div><div><b>Linear equation solver</b><span class="tag available">LIMITED</span></div><div><b>Structured topic library</b><span class="tag planned">IN PROGRESS</span></div><div><b>General symbolic algebra</b><span class="tag planned">NOT IMPLEMENTED</span></div></div>`)}
 ${card(`<div class="eyebrow">LOCAL LEARNING</div><h2>Practice activity</h2><div class="big-number">${count}</div><p class="muted">Correct practice answers recorded in this browser.</p><button class="outline-button" data-page="learning">Open learning system →</button>`)}
 </div>`;
}
function renderLearning(){
 return `${heading('LEARNING OPERATIONS / CORE PROCESS','Learning system','ULTRON improves through verified examples, deliberate practice and evaluation—not by assuming that lower training loss means mathematical ability.')}
 ${card('<div class="eyebrow">THE IMPROVEMENT CYCLE</div><h2 class="cycle-title">Learn → test → diagnose → improve</h2><p class="muted">A learning process must be measured against correct answers and held-out problems. Actual model training remains disabled.</p><div class="cycle-grid">'+[['01','Generate','Create original math problems.'],['02','Verify','Check answers independently.'],['03','Learn','Study verified examples and concepts.'],['04','Evaluate','Test understanding on new problems.'],['05','Improve','Target weaknesses using evidence.']].map(([n,t,d])=>`<div class="cycle-step"><b>${n}</b><strong>${t}</strong><p>${d}</p></div>`).join('')+'</div>')}
 <div class="grid two-col lower-grid">${card('<div class="eyebrow">DATA QUALITY</div><h2>Verified learning material</h2><p class="muted">Examples should be checked before they become trusted learning material. Incorrect or ambiguous examples must be rejected or reviewed.</p><ul class="feature-list"><li>Original problem statements</li><li>Independent answer checks</li><li>Topic and difficulty labels</li><li>Held-out evaluation examples</li></ul>')}${card('<div class="eyebrow">MEASURED ABILITY</div><h2>Evidence of learning</h2><p class="muted">A learner's progress should come from completed work, repeated performance and mistake patterns—not invented percentages.</p><ul class="feature-list"><li>Exercise accuracy from recorded answers</li><li>Concept-specific review</li><li>Clear distinction between practice and model training</li><li>Transparent limitations</li></ul>')}</div>
 ${card('<div class="eyebrow">TRAINING SAFETY</div><h2>Training is disabled</h2><p class="muted">This page explains the intended learning lifecycle. It does not launch data generation, optimizers, background workers or cloud jobs.</p><span class="status-pill">DISABLED — AWAITING EXPLICIT AUTHORIZATION</span>')}`;
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
 return `${heading('BACKEND / INTEGRATION AUDIT','Supabase backend','Existing backend inspected against this public website. This is a configuration audit, not live telemetry.')}
 <div class="status-grid">
 ${card('<div class="mini-label">SUPABASE PROJECT</div><strong class="status-value">ACTIVE</strong><p>Project was healthy when inspected. No database changes were made.</p>','status-card')}
 ${card('<div class="mini-label">PUBLIC ACCESS</div><strong class="status-value">RESTRICTED</strong><p>Memory and training records are owner-scoped with row-level security.</p>','status-card')}
 ${card('<div class="mini-label">DEVICE CONTROL</div><strong class="status-value">RETIRED</strong><p>The deployed endpoint returns HTTP 410.</p>','status-card')}
 ${card('<div class="mini-label">TRAINING CONTROL</div><strong class="status-value">OWNER ONLY</strong><p>Requires a valid signed-in owner session. No public controls are exposed.</p>','status-card')}
 </div>
 ${card('<div class="eyebrow">DEPLOYED EDGE FUNCTIONS</div><h2>Existing service contracts</h2>'+rows)}
 ${card('<div class="eyebrow">INTEGRATION BLOCKERS</div><h2>What must be aligned before connection</h2>'+blockers)}
 ${card('<div class="eyebrow">PUBLIC WEBSITE SAFETY</div><h2>No login. No training actions.</h2><p class="muted">This website intentionally has no sign-in or account-specific history. The current database records are tied to an authenticated owner and cannot safely be read by the public dashboard. The frontend does not call owner-only functions, read protected tables, store credentials, dispatch workflows or start training.</p><p class="muted small">Next backend step: Codex should provide a narrowly scoped, unauthenticated health-only endpoint for this Pages origin, and align the server-side GitHub repository/origin configuration. It must not expose training controls or private run data.</p><span class="status-pill">TRAINING REMAINS DISABLED</span>')}`;
}

function renderSettings(){
 const level=Math.min(10,Math.max(2,Number(safeGet('ultron-memory-level','6'))));
 return `${heading('DEVICE MEMORY SETTINGS','Settings','Local interface preferences. No account is required.')}
 ${card('<div class="eyebrow">DEVICE MEMORY SETTINGS</div><h2>Training RAM preference</h2><p class="muted">Choose a preferred memory budget for future approved remote workloads. This preference is saved in this browser only; it does not allocate device RAM or change hosted-runner memory.</p><div class="memory-box"><div class="memory-heading"><b>Preferred training memory</b><strong id="memory-value">'+level+' GB</strong></div><input class="memory-slider" id="memory-slider" type="range" min="2" max="10" step="1" value="'+level+'" aria-label="Preferred memory budget"><div class="slider-labels"><span>2 GB · Light</span><span>10 GB · High</span></div></div><div class="warning-banner">Saved in this browser only. This preference is not connected to remote training or hosted-runner memory controls.</div><p class="muted small">A future approved runtime would need to translate this preference into safe batch sizes and memory-aware settings. The slider does not change physical RAM or GPU VRAM today.</p>')}
 ${card('<div class="eyebrow">LOCAL DATA</div><h2>Browser storage</h2><p class="muted">Practice count and preferences are stored locally on this device when browser storage is available.</p><button class="outline-button" id="clear-local">Clear local preferences and practice count</button><p id="settings-result" class="muted" role="status"></p>')}`;
}
function render(page){return ({overview:renderOverview,learning:renderLearning,agent:renderAgent,servers:renderServers,backend:renderBackend,settings:renderSettings})[page]();}
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
async function loadServers(){
 const alert=document.querySelector('#server-alert');const list=document.querySelector('#server-list');if(!alert||!list)return;
 alert.textContent='Loading provider directory…';list.innerHTML='<div class="empty-state"><span>⌁</span><b>Checking directory</b></div>';
 try{
  const response=await fetch('./servers.json',{cache:'no-store'});
  if(!response.ok)throw new Error(`Could not load servers.json (HTTP ${response.status})`);
  const data=await response.json();const entries=Array.isArray(data)?data:data.providers;
  if(!Array.isArray(entries))throw new Error('Provider directory format is invalid.');
  alert.textContent='Provider directory loaded. Availability and terms still require direct verification.';
  list.innerHTML=entries.length?entries.map((item,i)=>`<div class="server-row"><span class="server-number">${i+1}</span><div><b>${esc(item.name||'Unnamed provider')}</b><p>${esc(item.description||item.capabilities||'No capability description supplied.')}</p></div><span class="tag planned">UNVERIFIED</span></div>`).join(''):'<div class="empty-state"><span>—</span><b>No providers listed</b><p>The directory contains no providers.</p></div>';
 }catch(error){alert.textContent=`Provider directory unavailable: ${error.message}. Provider terms metadata unavailable; verify current terms directly before using a provider.`;list.innerHTML='<div class="empty-state"><span>!</span><b>Provider directory unavailable</b><p>Check the deployed servers.json path and refresh. No provider is assumed available.</p></div>';}
}
function bind(page){
 content.querySelectorAll('[data-page]').forEach(el=>el.addEventListener('click',()=>navigate(el.dataset.page)));
 if(page==='agent'){
  document.querySelector('#agent-send').addEventListener('click',answerAgent);
  document.querySelector('#agent-input').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();answerAgent();}});
  document.querySelector('#agent-reset').addEventListener('click',()=>{document.querySelector('#chat-log').innerHTML='<div class="chat-message system-message">Conversation reset. Enter a supported arithmetic expression or linear equation.</div>';});
  content.querySelectorAll('[data-example]').forEach(b=>b.addEventListener('click',()=>{document.querySelector('#agent-input').value=b.dataset.example;document.querySelector('#agent-input').focus();}));
 }
 if(page==='servers'){document.querySelector('#servers-refresh').addEventListener('click',loadServers);loadServers();}
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
