(() => {
 const dataElement=document.getElementById('history-dams');
 if(!dataElement)return;
 const dams=JSON.parse(dataElement.textContent);
 const slider=document.getElementById('history-year-slider');
 const yearDisplay=document.getElementById('history-year');
 const count=document.getElementById('history-count');
 const phase=document.getElementById('history-phase');
 const card=document.getElementById('history-card');
 const events=document.getElementById('history-events');
 const markers=document.getElementById('history-markers');
 let selectedId=null;
 const status=(dam,year)=>year<dam.constructionStart?'future':year<dam.firstOperation?'building':'operating';
 for(const dam of dams){
  const knot=document.createElement('button');knot.type='button';knot.textContent=`${dam.constructionStart} · ${dam.name}`;knot.dataset.year=dam.constructionStart;knot.dataset.dam=dam.id;knot.addEventListener('click',()=>setYear(dam.constructionStart,dam.id));events.append(knot);
  const group=document.createElementNS('http://www.w3.org/2000/svg','g');group.setAttribute('class','history-marker');group.setAttribute('role','button');group.setAttribute('tabindex','0');group.setAttribute('aria-label',dam.name);group.dataset.dam=dam.id;
  const circle=document.createElementNS('http://www.w3.org/2000/svg','circle');circle.setAttribute('cx',dam.mapX);circle.setAttribute('cy',dam.mapY);circle.setAttribute('r','10');group.append(circle);
  const label=document.createElementNS('http://www.w3.org/2000/svg','text');label.setAttribute('x',dam.mapX+17);label.setAttribute('y',dam.mapY+5);label.textContent=dam.name;group.append(label);
  group.addEventListener('click',()=>selectDam(dam.id));group.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();selectDam(dam.id);}});markers.append(group);
 }
 function selectDam(id){selectedId=id;render(Number(slider.value));}
 function setYear(year,id=null){slider.value=year;selectedId=id;render(year);}
 function render(year){
  yearDisplay.textContent=year;
  const operating=dams.filter(dam=>status(dam,year)==='operating').length;
  const building=dams.filter(dam=>status(dam,year)==='building').length;
  count.textContent=`${operating} operating · ${building} under construction`;
  const newest=[...dams].reverse().find(dam=>dam.constructionStart<=year);
  const focused=dams.find(dam=>dam.id===selectedId)||newest||dams[0];
  phase.textContent=year<focused.constructionStart?'Future station':status(focused,year)==='building'?'Construction underway':year<focused.fullPower?'First units generating':'Fully equipped';
  card.replaceChildren();
  const title=document.createElement('h3');title.textContent=focused.name;card.append(title);
  const place=document.createElement('p');place.textContent=focused.place;card.append(place);
  const details=document.createElement('dl');
  for(const [key,value] of [['Construction',focused.constructionPeriod],['First operation',focused.firstOperation],['Full power',focused.fullPower]]){const dt=document.createElement('dt');dt.textContent=key;const dd=document.createElement('dd');dd.textContent=value;details.append(dt,dd);}card.append(details);
  const text=document.createElement('p');text.textContent=focused.significance;card.append(text);
  const link=document.createElement('a');link.href=focused.source;link.target='_blank';link.rel='noreferrer';link.textContent='Read source ↗';card.append(link);
  for(const marker of markers.children){const dam=dams.find(item=>item.id===marker.dataset.dam);marker.setAttribute('class',`history-marker ${status(dam,year)}${dam.id===focused.id?' selected':''}`);marker.setAttribute('aria-label',`${dam.name}: ${status(dam,year)} in ${year}`);}
  for(const knot of events.children)knot.setAttribute('aria-pressed',String(knot.dataset.dam===focused.id && Number(knot.dataset.year)===year));
 }
 slider.addEventListener('input',()=>{selectedId=null;render(Number(slider.value));});
 render(Number(slider.value));
})();
