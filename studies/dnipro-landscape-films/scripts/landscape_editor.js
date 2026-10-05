const tabButtons=[...document.querySelectorAll('[data-tab]')];
const saveAll=document.getElementById('save-all');
const editorStatus=document.getElementById('editor-status');
const drafts=new Map();
let revision=null, saving=false, connected=false;
const labelColors=JSON.parse(document.getElementById('label-colors').textContent);
const records=new Map();
function editorMessage(text,error=false){editorStatus.textContent=text;editorStatus.classList.toggle('error',error);}
function setMode(modeName){
 document.body.dataset.mode=modeName;
 for(const tab of tabButtons){const active=tab.dataset.tab===modeName;tab.setAttribute('aria-selected',String(active));tab.tabIndex=active?0:-1;}
 document.getElementById('gallery-workspace').hidden=modeName==='history';
 const history=document.getElementById('history-workspace');if(history)history.hidden=modeName!=='history';
 document.getElementById('frames-panel').setAttribute('aria-labelledby','tab-'+modeName);
}
for(const tab of tabButtons){tab.addEventListener('click',()=>setMode(tab.dataset.tab));tab.addEventListener('keydown',event=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){event.preventDefault();const index=tabButtons.indexOf(tab);const target=event.key==='Home'?tabButtons[0]:event.key==='End'?tabButtons.at(-1):tabButtons[(index+(event.key==='ArrowRight'?1:-1)+tabButtons.length)%tabButtons.length];target.focus();setMode(target.dataset.tab);}});}
for(const link of document.querySelectorAll('[data-history-frame-link]'))link.addEventListener('click',event=>{
 event.preventDefault();
 const card=document.getElementById('frame-'+link.dataset.historyFrameLink);if(!card)return;
 setMode('gallery');
 if(card.hidden)resetFilters();
 window.location.hash=card.id;
 card.scrollIntoView({block:'start',behavior:'smooth'});
 card.focus({preventScroll:true});
});
function paintTags(container,labels){
 container.replaceChildren();
 if(!labels.length){const span=document.createElement('span');span.className='muted';span.textContent='Not reviewed';container.append(span);return;}
 for(const label of labels){const span=document.createElement('span');span.className='tag';span.style.setProperty('--label-color',labelColors[label]||'#d4d4d4');span.textContent=label;container.append(span);}
}
function selectedLabels(card){return [...card.element.querySelectorAll('.edit-label:checked')].map(input=>input.value);}
function controls(){
 saveAll.disabled=!connected||saving||drafts.size===0;
 saveAll.textContent=saving?'Saving…':`Save changes${drafts.size?' ('+drafts.size+')':''}`;
 document.getElementById('discard-drafts').disabled=saving||drafts.size===0;
 for(const card of cards){for(const input of card.element.querySelectorAll('.edit-label'))input.disabled=!connected||saving;card.element.querySelector('.save-frame').disabled=!connected||saving;card.element.classList.toggle('has-draft',drafts.has(card.element.dataset.filename));}
 document.getElementById('draft-count').textContent=drafts.size?`${drafts.size} unsaved frame${drafts.size===1?'':'s'}`:'All changes saved';
}
function updateState(state,savedNames=[]){
 revision=state.revision;
 for(const name of savedNames)drafts.delete(name);
 for(const row of state.rows)records.set(row.filename,row);
 for(const card of cards){
  const row=records.get(card.element.dataset.filename);if(!row)continue;
  card.labels=row.labels;card.element.dataset.labels=JSON.stringify(row.labels);
  paintTags(card.element.querySelector('.your-labels'),row.human_labels);
  card.element.querySelector('.review').textContent=row.review_reasons.join('; ')||'No uncertainty rule triggered; predictions may still contain errors.';
  const selected=drafts.get(row.filename)||(row.human_labels.length?row.human_labels:row.model_labels);
  for(const input of card.element.querySelectorAll('.edit-label'))input.checked=selected.includes(input.value);
  card.element.querySelector('.edit-source').textContent=row.human_labels.length?'Editing your saved labels.':'Starting from the model prediction. Save to confirm or correct it.';
 }
 applyFilters();controls();
}
for(const card of cards){
 for(const input of card.element.querySelectorAll('.edit-label'))input.addEventListener('change',()=>{
  drafts.set(card.element.dataset.filename,selectedLabels(card));controls();
 });
 card.element.querySelector('.save-frame').addEventListener('click',()=>saveChanges([card.element.dataset.filename]));
}
async function saveChanges(names){
 if(!connected||saving)return;
 const changes=names.map(filename=>{const card=cards.find(c=>c.element.dataset.filename===filename);return {filename,labels:selectedLabels(card)};});
 if(changes.some(change=>!change.labels.length)){editorMessage('Choose at least one label for each frame. Use unknown when appropriate.',true);return;}
 for(const change of changes)drafts.set(change.filename,change.labels);
 saving=true;controls();editorMessage('Saving labels to the dataset…');
 try{
  const response=await fetch('/api/labels',{method:'POST',headers:{'Content-Type':'application/json','X-Landscape-Editor':'1'},body:JSON.stringify({revision,changes})});
  const data=await response.json();if(!response.ok)throw new Error(data.error||'Save failed.');
  updateState(data,names);editorMessage(`Saved ${names.length} frame${names.length===1?'':'s'} to the dataset. Gallery and CSV exports are updated.`);
 }catch(error){editorMessage(error.message+' Your selections remain on this page.',true);}
 finally{saving=false;controls();}
}
saveAll.addEventListener('click',()=>saveChanges([...drafts.keys()]));
document.getElementById('discard-drafts').addEventListener('click',()=>{drafts.clear();updateState({revision,rows:[...records.values()]});editorMessage('Unsaved changes discarded.');});
window.addEventListener('beforeunload',event=>{if(drafts.size){event.preventDefault();event.returnValue='';}});
async function connectEditor(){
 if(location.protocol==='file:'){editorMessage('To save labels, open the local app at http://127.0.0.1:8765. This file preview is read-only.');controls();return;}
 try{const response=await fetch('/api/state');if(!response.ok)throw new Error('Could not connect to the local app.');const data=await response.json();connected=true;updateState(data);editorMessage('Choose labels and save. Changes update the dataset and Gallery.');}
 catch(error){editorMessage('Editing unavailable: '+error.message,true);controls();}
}
setMode('gallery');controls();connectEditor();
