const tabButtons=[...document.querySelectorAll('[data-tab]')];
function setMode(modeName){
 document.body.dataset.mode=modeName;
 for(const tab of tabButtons){const active=tab.dataset.tab===modeName;tab.setAttribute('aria-selected',String(active));tab.tabIndex=active?0:-1;}
 document.getElementById('gallery-workspace').hidden=modeName==='history';
 const history=document.getElementById('history-workspace');if(history)history.hidden=modeName!=='history';
}
for(const tab of tabButtons){
 tab.addEventListener('click',()=>setMode(tab.dataset.tab));
 tab.addEventListener('keydown',event=>{
  if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
  event.preventDefault();const index=tabButtons.indexOf(tab);
  const target=event.key==='Home'?tabButtons[0]:event.key==='End'?tabButtons.at(-1):tabButtons[(index+(event.key==='ArrowRight'?1:-1)+tabButtons.length)%tabButtons.length];
  target.focus();setMode(target.dataset.tab);
 });
}
for(const link of document.querySelectorAll('[data-history-frame-link]'))link.addEventListener('click',event=>{
 event.preventDefault();const card=document.getElementById('frame-'+link.dataset.historyFrameLink);if(!card)return;
 setMode('gallery');if(card.hidden)resetFilters();window.location.hash=card.id;
 card.scrollIntoView({block:'start',behavior:'smooth'});card.focus({preventScroll:true});
});
setMode('gallery');
