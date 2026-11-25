'use strict';
const $=id=>document.getElementById(id);
const lineIcons={"music":"M9 18V5l12-2v13M9 18a3 2 0 1 1-6 0 3 2 0 0 1 6 0Zm12-2a3 2 0 1 1-6 0 3 2 0 0 1 6 0Z","movies":"M4 5h16v14H4zM9 9l6 3-6 3z","photos":"M3 4h18v16H3zM3 17l6-6 5 5 3-3 4 4M15 8h.01","files":"M3 6h7l2 3h9v11H3z","passwords":"M6 11h12v10H6zM8 11V7a4 4 0 0 1 8 0v4M12 15v2","tasks":"M5 3h14v18H5zM8 9l2 2 4-4M8 16h8","dns":"M12 3 4 6v6c0 4 4 7 8 9 4-2 8-5 8-9V6zM9 12l2 2 4-4","remote":"M8 6h8M8 18h8M4 8v8m16-8v8M4 12h16M7 9l-3 3 3 3m10-6 3 3-3 3","monitor":"M3 4h18v13H3zM8 21h8m-4-4v4M6 11h3l2-4 3 7 2-3h2","navidrome":"M4 4h16v16H4zM12 8a4 4 0 1 0 0 8 4 4 0 1 0 0-8Z","hardware":"M5 3h14v18H5zM8 7h8M8 11h8m0 6h.01","hdd":"M4 5h16v14H4zM7 15h10m-1-6h.01","overview":"M3 10l9-7 9 7v11H3zM9 21v-8h6v8","costing":"M12 2v20M17 7H9a3 3 0 0 0 0 6h6a3 3 0 0 1 0 6H7","orders":"M6 3h12v18H6zM9 8h6M9 12h6M9 16h3","installation":"M4 4h16v16H4zM8 8h8M8 12h8M8 16h4","support":"M4 13v-2a8 8 0 0 1 16 0v2M4 12h3v6H4zM17 12h3v6h-3zM20 18v2h-6","documents":"M5 3h9l5 5v13H5zM14 3v5h5M8 13h8m-8 4h6"};
function lineIcon(id){const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg'),p=document.createElementNS(ns,'path');for(const [k,v] of Object.entries({viewBox:'0 0 24 24',fill:'none',stroke:'currentColor','stroke-width':'1.65','stroke-linecap':'round','stroke-linejoin':'round','aria-hidden':'true'}))svg.setAttribute(k,v);p.setAttribute('d',lineIcons[id]||lineIcons.hardware);svg.append(p);return svg}

let init,report={offers:[],coverage:[]},visible=18,confirmed,costResult,editing=null,orders=[],cases=[];
const el=(tag,text,cls)=>{const x=document.createElement(tag);if(text!==undefined)x.textContent=text;if(cls)x.className=cls;return x};
function notice(s){$('status').textContent=translate(s)}
async function api(path,data){const response=await fetch('/api/'+path,data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-Jobbi-Request':'1'},body:JSON.stringify(data)});const j=await response.json();if(!response.ok)throw Error(j.error||'Request failed');return j}
function attempt(fn){return async(...args)=>{try{await fn(...args)}catch(e){notice(e.message)}}}
function link(url,label){const a=el('a',translate(label));try{const u=new URL(url);if(u.protocol==='https:'&&!u.username&&!u.password){a.href=u.href;a.target='_blank';a.rel='noopener noreferrer'}}catch{}return a}
function button(label,fn){const b=el('button',translate(label));b.type='button';b.onclick=attempt(fn);return b}
function formdata(id){return Object.fromEntries(new FormData($(id)))}
function fmt(n,cur){return new Intl.NumberFormat(uiLanguage==='es'?'es-MX':'en-US',{style:'currency',currency:cur}).format(Number(n))}
function currency(m){return m==='MX'?'MXN':'USD'}
function metric(target,label,value){const d=el('div',undefined,'metric');d.append(el('small',translate(label)),el('strong',value));target.append(d)}
function tab(name){if(!['overview','hardware','costing','orders','installation','support','documents'].includes(name))name='overview';for(const s of document.querySelectorAll('main>section'))s.hidden=s.id!==name;for(const b of document.querySelectorAll('nav button')){const active=b.dataset.tab===name;b.classList.toggle('active',active);if(active)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current')}if(location.hash!=='#'+name)history.replaceState(null,'','#'+name);window.scrollTo({top:0,behavior:'instant'})}
for(const b of document.querySelectorAll('nav button'))b.onclick=()=>tab(b.dataset.tab);tab(['overview','hardware','costing','orders','installation','support','documents'].includes(location.hash.slice(1))?location.hash.slice(1):'overview');
for(const b of document.querySelectorAll('nav [data-tab]')){const id=b.dataset.tab;let slot=b.querySelector('span[aria-hidden]');if(!slot){slot=document.createElement('span');slot.setAttribute('aria-hidden','true');b.prepend(slot)}slot.className='nav-icon';slot.replaceChildren(lineIcon(id))}
function renderOverview(){const box=$('overviewMetrics');box.replaceChildren();metric(box,'Active orders',orders.filter(o=>!['delivered','cancelled'].includes(o.stage)).length);metric(box,'Installations in progress',orders.filter(o=>o.stage==='installing').length);metric(box,'Open support cases',cases.filter(c=>c.status!=='resolved').length);metric(box,'Delivered',orders.filter(o=>o.stage==='delivered').length);$('overviewReminders').replaceChildren(...[...$('reminders').children].map(x=>x.cloneNode(true)));const recent=$('recentPayments');recent.replaceChildren();const payments=orders.flatMap(o=>o.transactions.map(t=>({...t,order:o.id,market:o.market}))).sort((a,b)=>String(b.recorded).localeCompare(String(a.recorded))).slice(0,4);for(const p of payments){const row=el('div',undefined,'recent-row');row.append(el('span',p.order+' · '+translate(p.kind)),el('strong',fmt(p.amount/100,currency(p.market))),el('small',p.recorded));recent.append(row)}if(!payments.length)recent.append(el('p',translate('No cash transactions yet.')))}
const opts=(s,rows)=>{s.replaceChildren();for(const [v,label] of rows)s.add(new Option(translate(label),v))};
function setReports(ids,selected){opts($('reports'),[['','Choose saved report'],...ids.map(x=>[x,x])]);$('reports').value=ids.includes(selected)?selected:ids[0]||''}
function refreshSuppliers(){const form=$('confirm');opts(form.elements.supplier,Object.keys(init.suppliers[form.elements.market.value]).map(x=>[x,x]))}
$('confirm').elements.market.onchange=refreshSuppliers;
function iso(){let x=new Date();return [x.getFullYear(),String(x.getMonth()+1).padStart(2,'0'),String(x.getDate()).padStart(2,'0')].join('-')}
$('confirm').elements.checked_date.value=iso();$('payment').elements.date.value=iso();
function queryOpts(){return {profile:$('profile').value,target:$('target').value,fx:$('fx').value}}
async function showLinks(){const entries=await api('links?profile='+encodeURIComponent($('profile').value));$('links').replaceChildren();for(const r of entries){let p=el('p');p.append(document.createTextNode(r.market+' · '+r.supplier+' · '+r.query+' — '),link(r.url,'Supplier search'),document.createTextNode(' · '),link(r.indexed,'Site search'));$('links').append(p)}}
function renderOffers(){
 const source=report.offers||[];$('summary').replaceChildren();metric($('summary'),'All retrieved',source.length);for(const d of ['candidate','review','reject'])metric($('summary'),d,source.filter(x=>x.decision===d).length);
 const filtered=source.filter(x=>(!$('part').value||x.part===$('part').value)&&(!$('marketFilter').value||x.market===$('marketFilter').value)&&(!$('decision').value||x.decision===$('decision').value)&&((x.title+' '+x.supplier).toLowerCase().includes($('filter').value.toLowerCase())));
 filtered.sort((a,b)=>a.currency.localeCompare(b.currency)||a.part.localeCompare(b.part)||(a.shipping===null?1:0)-(b.shipping===null?1:0)||((a.price===null?Infinity:Number(a.price))+Number(a.shipping||0))-((b.price===null?Infinity:Number(b.price))+Number(b.shipping||0)));
 $('offers').replaceChildren();
 for(const r of filtered.slice(0,visible)){
   const c=el('article',undefined,'offer');
   if($('images').checked&&r.image){try{const u=new URL(r.image);if(u.protocol==='https:'&&u.hostname==='i.ebayimg.com'){const i=el('img');i.src=u.href;i.alt='Listing photo';i.loading='lazy';i.referrerPolicy='no-referrer';c.append(i)}}catch{}}
   if(!c.querySelector('img')){const visual=el('div',undefined,'offer-visual');visual.setAttribute('aria-hidden','true');visual.append(lineIcon(r.part==='hdd'?'hdd':'hardware'));c.append(visual)}
   c.append(el('small',r.market+' · '+r.supplier+' · '+r.part),el('h3',r.title),el('b',r.price===null?'Unknown price':fmt(r.price,r.currency)),el('p','Shipping: '+(r.shipping===null?'unknown':fmt(r.shipping,r.currency))+' · '+(r.condition||'Unknown condition')),el('span',translate(r.decision),'decision '+r.decision),link(r.url,'Open listing'));
   const why=el('details');why.append(el('summary',translate('Screening details')),el('p',r.reason));c.append(why);
   if(r.decision!=='reject')c.append(el('br'),button('Review / confirm',()=>{const form=$('confirm');$('confirmPanel').open=true;form.reset();form.elements.part.value=r.part;form.elements.market.value=r.market;refreshSuppliers();form.elements.supplier.value=r.supplier;form.elements.url.value=r.url;form.elements.checked_date.value=iso();form.elements.available_quantity.value=init.profiles[$('profile').value].parts.find(x=>x.id===r.part).quantity;form.scrollIntoView({behavior:'smooth'});notice('Enter confirmed checkout costs and exact model; search prices were not copied.')}))
   $('offers').append(c);
 }
 if(!filtered.length)$('offers').append(el('p',translate('No results for these filters. Check provider coverage and supplier searches.')));
 $('more').hidden=filtered.length<=visible;
 $('coverage').textContent=(report.coverage||[]).map(x=>x.join(' | ')).join('\n');
}
for(const id of ['part','marketFilter','decision','filter','images'])$(id).addEventListener('input',()=>{visible=18;renderOffers()});
$('more').onclick=()=>{visible+=18;renderOffers()};
async function loadReport(){const id=$('reports').value;if(id){$('profile').value=id.split('-')[0];report=await api('report?id='+encodeURIComponent(id))}else report={offers:[],coverage:[]};visible=30;renderOffers();await showLinks();await recalc()}
$('reports').onchange=attempt(loadReport);
$('profile').onchange=attempt(async()=>{$('reports').value='';report={offers:[],coverage:[]};renderOffers();await showLinks();await recalc()});
$('target').onchange=attempt(recalc);$('fx').oninput=()=>{$('useBom').disabled=true;confirmed=null};
$('search').onclick=attempt(async()=>{await api('search',{...queryOpts(),markets:$('markets').value});$('search').disabled=true;notice('Search started. Existing reports remain available.')});
let lastJob='idle';
async function poll(){try{const x=await api('job');$('job').textContent=x.message;$('search').disabled=Boolean(init?.preview)||x.state==='running';if(x.state==='done'&&lastJob!=='done'){setReports(x.reports,x.reports[0]);await loadReport()}lastJob=x.state}catch(e){notice(e.message)}}
function renderConfirmed(x){confirmed=x;$('confirmed').replaceChildren();$('useBom').disabled=!x.bom.length;if(x.bom.length){$('confirmed').append(el('h3','Lowest complete confirmed build: '+fmt(x.total,x.currency)));for(const r of x.bom){const p=el('p');p.append(document.createTextNode(r.quantity+' × '+r.title+' · '+r.supplier+' · '+fmt(r.landed,r.currency)+' · '),link(r.url,'Listing'));$('confirmed').append(p)}}else $('confirmed').append(el('p',translate('No complete confirmed build for this profile and target.')));for(const r of x.saved){const p=el('p');const excluded=x.excluded.find(y=>y.url===r.url);p.append(document.createTextNode(r.market+' · '+r.exact_model+' · '+r.supplier+(excluded?' — excluded: '+excluded.reason:'')+' '),link(r.url,'Listing'),document.createTextNode(' '),button('Remove',async()=>renderConfirmed(await api('remove-offer',{...queryOpts(),part:r.part,url:r.url}))));$('confirmed').append(p)}}
async function recalc(){renderConfirmed(await api('confirmed',queryOpts()))}
$('recalc').onclick=attempt(recalc);
$('confirm').onsubmit=attempt(async e=>{e.preventDefault();const offer=formdata('confirm');offer.currency=currency(offer.market);renderConfirmed(await api('confirm',{...queryOpts(),offer}));notice('Confirmed offer saved.');e.target.reset();refreshSuppliers();e.target.elements.checked_date.value=iso()});
$('useBom').onclick=()=>{if(!confirmed?.bom.length)return;const f=$('cost');f.elements.market.value=$('target').value;f.elements.hardware.value=confirmed.total;tab('costing');notice('Confirmed landed hardware cost copied. Add all other costs.')};
$('cost').addEventListener('input',()=>{costResult=null;$('usePrice').disabled=true});
$('cost').onsubmit=attempt(async e=>{e.preventDefault();costResult=await api('cost',formdata('cost'));$('costResult').replaceChildren();for(const [key,label] of [['price','Proposed pre-tax price'],['cost','Estimated expenses'],['contribution','Contribution'],['minimum','Minimum target price']])metric($('costResult'),label,fmt(costResult[key],costResult.currency));metric($('costResult'),'Contribution margin',costResult.margin+'%');$('usePrice').disabled=false;notice('Calculation complete; verify tax and final agreed amount.')});
$('usePrice').onclick=()=>{if(!costResult)return;clearOrder();$('order').elements.market.value=costResult.currency==='MXN'?'MX':'US';$('order').elements.total.value=costResult.price;$('order').elements.months.value=$('cost').elements.months.value;tab('orders');$('orderPanel').open=true;notice('Pre-tax proposal copied; confirm agreed total before saving.')};
function clearOrder(){editing=null;$('order').reset();for(const n of ['id','market','total'])$('order').elements[n].disabled=false}
$('clearOrder').onclick=clearOrder;
async function loadOrders(){orders=await api('orders');refreshOperations();$('totals').replaceChildren();for(const m of ['US','MX']){const arr=orders.filter(x=>x.market===m);metric($('totals'),currency(m)+' net cash',fmt(arr.reduce((a,x)=>a+x.paid,0)/100,currency(m)));metric($('totals'),currency(m)+' unpaid original totals',fmt(arr.filter(x=>x.stage!=='cancelled').reduce((a,x)=>a+x.due,0)/100,currency(m)))}
opts($('payment').elements.id,orders.map(x=>[x.id,x.id+' · '+currency(x.market)]));$('orderList').replaceChildren();
for(const x of orders){const c=el('article',undefined,'ordercard');const cur=currency(x.market);c.append(el('h3',x.id+' · '+(x.label||'No reference')),el('p',(x.stage||'No details')+' · '+cur+' · Opened '+x.opened),el('p','Agreed '+fmt(x.total/100,cur)+' | Net received '+fmt(x.paid/100,cur)+' | Unpaid '+fmt(x.due/100,cur)),el('p','Delivered: '+(x.delivered||'—')+' · Support ends: '+(x.support_end||'—')+' · Hardware warranty: '+(x.warranty_end||'—')+' · Installation warranty: '+(x.installation_warranty_end||'—')));
 const detail=el('details');detail.append(el('summary',translate('Payment history and notes')));if(x.note)detail.append(el('p',x.note));for(const t of x.transactions)detail.append(el('p',t.recorded+' · '+t.id+' · '+t.kind+' · '+fmt(t.amount/100,cur)));c.append(detail);
 c.append(button('Edit order details',()=>{clearOrder();$('orderPanel').open=true;editing=x.id;const f=$('order');for(const key of ['id','label','market','stage','delivered','months','hardware_condition','note'])if(x[key]!=null)f.elements[key].value=x[key];f.elements.total.value=(x.total/100).toFixed(2);for(const key of ['id','market','total'])f.elements[key].disabled=true;f.scrollIntoView({behavior:'smooth'});notice('Editing '+x.id+'; original cash agreement cannot be changed here.')}));$('orderList').append(c)}}
$('order').onsubmit=attempt(async e=>{e.preventDefault();const data=formdata('order');if(editing)data.id=editing;await api(editing?'order-update':'order',data);clearOrder();await loadOrders();notice('Order saved.')});
$('payment').onsubmit=attempt(async e=>{e.preventDefault();await api('payment',formdata('payment'));e.target.reset();e.target.elements.date.value=iso();await loadOrders();notice('Cash recorded. Issue applicable receipt separately.')});
(async()=>{try{init=await api('init');if(init.preview){const banner=el('p',translate('Demo only · no login · use test records'),'tag');banner.id='demoNotice';document.querySelector('header').append(banner)}opts($('profile'),Object.entries(init.profiles).map(([id,p])=>[id,p.name]));$('profile').value='family';refreshSuppliers();setReports(init.reports);await loadReport();await loadOrders();await loadCases();await loadPlans();await poll();setInterval(poll,3000)}catch(e){notice(e.message)}})();

let planResult=null;
function downloadText(name,text,mime='text/plain'){const url=URL.createObjectURL(new Blob([text],{type:mime}));const a=el('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
for(const [id,label] of Object.entries({music:'Music',movies:'Movies',photos:'Photos',files:'Files',passwords:'Passwords',tasks:'Tasks',monitor:'Monitoring',remote:'Remote access'})){const l=el('label');const c=el('input');c.type='checkbox';c.name='apps';c.value=id;c.checked=true;l.append(c,document.createTextNode(label));$('planApps').append(l)}
function refreshOperations(){const choices=orders.map(o=>[o.id,o.id+' · '+(o.label||o.market)]);for(const [id,optional] of [['planForm',true],['caseForm',false],['handoffForm',false],['documentForm',false],['componentForm',false],['eventForm',false]]){const s=$(id).elements.order_id;const prev=s.value;opts(s,[...(optional?[['','No saved order']]:[]),...choices]);if([...s.options].some(x=>x.value===prev))s.value=prev}
refreshReceiptChoices();
$('reminders').replaceChildren();for(const o of orders){if(o.stage!=='delivered')continue;for(const [k,label] of [['support_end','Support'],['warranty_end','Hardware warranty'],['installation_warranty_end','Installation warranty']]){if(!o[k])continue;const days=Math.ceil((Date.parse(o[k])-Date.parse(iso()))/86400000);if(days<=30&&days>=0)$('reminders').append(el('p',o.id+' · '+label+' ends in '+days+' days ('+o[k]+')'))}}renderInstallRecords();if(!$('reminders').children.length)$('reminders').append(el('p',translate('No recorded expiry in the next 30 days.')));renderOverview()}
$('planForm').onsubmit=attempt(async e=>{e.preventDefault();const d=formdata('planForm');d.apps=[...$('planApps').querySelectorAll('input:checked')].map(x=>x.value);d.mirror=e.target.elements.mirror.checked;planResult=await api('plan',d);$('planOutput').textContent=planResult.note+'\n\n'+planResult.commands;$('downloadPlan').disabled=false;await loadPlans();notice('Plan generated; review and execute only on the customer host.')});
$('downloadPlan').onclick=()=>{if(planResult)downloadText(planResult.name+'-installation.txt',planResult.note+'\n\n'+planResult.commands)};
async function loadPlans(){const arr=await api('plans');$('savedPlans').replaceChildren();for(const x of arr){const p=el('p');p.append(document.createTextNode(x.order_id+' · '+x.plan.name+' · '+x.plan.tb+' TB '),button('View plan',()=>{$('planPanel').open=true;planResult=x.plan;$('planOutput').textContent=x.plan.note+'\n\n'+x.plan.commands;$('downloadPlan').disabled=false}));$('savedPlans').append(p)}}
async function loadCases(){const arr=await api('cases');cases=arr;renderOverview();$('caseList').replaceChildren();for(const x of arr){const c=el('article',undefined,'ordercard');c.append(el('h3',x.id+' · '+x.subject),el('p',x.order_id+' · '+x.category+' · '+x.status+' · '+x.updated),el('p',x.note),button('Edit',()=>{$('casePanel').open=true;for(const k of ['id','order_id','category','subject','status','note'])$('caseForm').elements[k].value=x[k]}));$('caseList').append(c)}}
$('caseForm').onsubmit=attempt(async e=>{e.preventDefault();await api('case',formdata('caseForm'));await loadCases();notice('Case saved.')});
$('handoffForm').onsubmit=attempt(async e=>{e.preventDefault();const d=formdata('handoffForm');const r=await api('handoff',d);downloadText(d.order_id+'-handoff-'+d.lang+'.txt',r.text);notice('Draft downloaded. Attach actual acceptance and warranty terms.')});

function refreshReceiptChoices(){
  const form=$('documentForm').elements;
  const receipt=form.kind.value==='receipt';
  form.transaction.parentElement.hidden=!receipt;
  form.transaction.required=receipt;
  const order=orders.find(row=>row.id===form.order_id.value);
  opts(form.transaction,(order?.transactions||[]).map(tx=>[tx.id,tx.id+' · '+tx.recorded+' · '+tx.kind]));
}
$('documentForm').elements.order_id.onchange=refreshReceiptChoices;
$('documentForm').elements.kind.onchange=refreshReceiptChoices;
$('documentForm').onsubmit=attempt(async event=>{
  event.preventDefault();
  const data=formdata('documentForm');
  const response=await api('document',data);
  const bytes=Uint8Array.from(atob(response.pdf),character=>character.charCodeAt(0));
  downloadText(data.order_id+'-'+data.kind+'-'+data.lang+'.pdf',bytes,'application/pdf');
});

function renderInstallRecords(){
  $('componentList').replaceChildren();
  $('eventList').replaceChildren();
  for(const order of orders){
    for(const row of order.components){
      const label=order.id+' · '+row.component+' · '+row.provider+' · '+row.expires;
      $('componentList').append(el('p',label));
      const days=(Date.parse(row.expires)-Date.parse(iso()))/86400000;
      if(days>=0&&days<=30)$('reminders').append(el('p',label+' · '+days+' days / días'));
    }
    for(const row of order.installation_events){
      $('eventList').append(el('p',[order.id,row.recorded,row.step,row.result,row.note].filter(Boolean).join(' · ')));
    }
  }
}
for(const [id,endpoint] of [['componentForm','component'],['eventForm','installation-event']]){
  $(id).onsubmit=attempt(async event=>{
    event.preventDefault();
    await api(endpoint,formdata(id));
    await loadOrders();
    notice('Saved / Guardado');
  });
}

document.addEventListener('jobbi-language',attempt(async()=>{
  renderOffers();
  if(confirmed)renderConfirmed(confirmed);
  await loadOrders();
  await loadPlans();
  await loadCases();
  await showLinks();
}));
