const compareIds=new Set();
const compareProducts=new Map();
const $ = id => document.getElementById(id);
let currentModel = 'Модель ещё не выбрана';
let currentProductId = null;
let currentProduct = null;
let questionnaireSchema = null;
let lastQuoteResponse = null;
let meta = null;
let searchOffset = 0;
const PAGE_SIZE = 24;

function fmt(v){
  if(v === null || v === undefined || v === '') return '—';
  return typeof v === 'number' ? v.toLocaleString('ru-RU',{maximumFractionDigits:2}) : String(v).replace('.', ',');
}
function fill(id, arr, labelFn=null){
  const s=$(id); if(!s) return;
  (arr||[]).forEach(v=>{ const o=document.createElement('option'); o.value=v; o.textContent=labelFn?labelFn(v):fmt(v); s.appendChild(o); });
}
function fillRanges(id, arr){
  const s=$(id); if(!s) return;
  (arr||[]).forEach(r=>{ const o=document.createElement('option'); o.value=`${r.min}:${r.max}`; o.textContent=r.label; s.appendChild(o); });
}
function fillValueLabels(id, arr){
  const s=$(id); if(!s) return;
  (arr||[]).forEach(r=>{ const o=document.createElement('option'); o.value=r.value; o.textContent=r.label; s.appendChild(o); });
}
function selectedLabel(id){ const el=$(id); return el && el.value ? el.options[el.selectedIndex].textContent : null; }

const FILTERS=[
 ['q','Модель / ID'],['manufacturer','Производитель'],['winch_type','Тип'],['capacity','Грузоподъёмность'],['speed','Скорость'],['suspension','Подвес'],['speed_count','Кол-во скоростей'],['vfd','ЧП'],['encoder_type','Энкодер'],['power','Мощность'],['cantilever','Консольная нагрузка'],['lift_height','Высота'],['groove_shape','Ручей'],['undercut_angle','Угол'],['sheave','КВШ'],['rope_count','Канаты'],['rope_diameter','Диаметр канатов'],['starts_per_hour','Включений/час'],['brake_voltage','Тормоз'],['weight','Масса'],['frame_supply','Рама'],['remote_release','Расцепление'],['placement_type','Размещение']
];
const UNITS={capacity:' кг',sheave:' мм',rope_diameter:' мм',weight:' кг'};

function activeFilterCount(){ return FILTERS.filter(([id])=>$(id) && $(id).value).length; }
function renderActiveFilters(){
  const active=FILTERS.filter(([id])=>$(id) && $(id).value);
  $('active_filters').innerHTML=active.map(([id,label])=>`<span class="active-filter">${label}: <b>${selectedLabel(id)}${UNITS[id]||''}</b></span>`).join('');
  const n=active.length;
  $('mobile_filter_badge').textContent=n;
  $('mobile_filter_badge_bottom').textContent=n;
  $('filter_count_hint').textContent=n ? `Выбрано параметров: ${n}` : 'Можно начать с 2–4 основных параметров';
}
function buildSearchParams(){
  const p=new URLSearchParams();
  const direct=[['q','q'],['manufacturer','manufacturer'],['winch_type','winch_type'],['capacity','capacity_kg'],['suspension','suspension'],['speed_count','speed_count'],['vfd','vfd'],['encoder_type','encoder_type'],['cantilever','cantilever_required_kg'],['lift_height','lift_height_required_m'],['groove_shape','groove_shape'],['undercut_angle','undercut_angle'],['sheave','sheave_diameter_mm'],['rope_count','rope_count'],['rope_diameter','rope_diameter_mm'],['starts_per_hour','starts_per_hour'],['brake_voltage','brake_voltage'],['weight','weight_kg'],['frame_supply','frame_supply'],['remote_release','remote_release'],['placement_type','placement_type']];
  direct.forEach(([id,k])=>{if($(id) && $(id).value)p.set(k,$(id).value)});
  if($('speed').value){const [mn,mx]=$('speed').value.split(':');p.set('speed_min',mn);p.set('speed_max',mx);}
  if($('power').value){const [mn,mx]=$('power').value.split(':');p.set('power_min',mn);p.set('power_max',mx);}
  p.set('limit',String(PAGE_SIZE)); p.set('offset',String(searchOffset)); return p;
}
function cardHtml(x){
  const suspension=(x.suspensions||[]).join(', ')||'—', ropes=(x.rope_counts||[]).join(', ')||'—', ropeDia=(x.rope_diameters_mm||[]).map(fmt).join(', ')||'—';
  return `<article class="card" data-product-id="${x.id}"><div class="card__top"><div><div class="card__mfr">${x.manufacturer||'Производитель'}</div><h3>${x.model||'Без модели'}</h3><div class="model-type">${x.winch_type||'Тип не уточнён'}</div></div><span class="match-badge">Подходит</span></div>
  <div class="specs">
    <div class="spec"><small>Грузоподъёмность</small><b>${fmt(x.capacity_kg)} кг</b></div><div class="spec"><small>Скорость</small><b>${fmt(x.speed_m_s)} м/с</b></div>
    <div class="spec"><small>Мощность</small><b>${fmt(x.power_kw)} кВт</b></div><div class="spec"><small>Количество скоростей</small><b>${fmt(x.speed_count_normalized ?? x.speed_count)}</b></div><div class="spec"><small>Подвес</small><b>${suspension}</b></div>
    <div class="spec"><small>КВШ</small><b>${fmt(x.sheave_diameter_mm)} мм</b></div><div class="spec"><small>Канаты</small><b>${ropes} × ${ropeDia} мм</b></div>
    <div class="spec"><small>Консольная нагрузка</small><b>${fmt(x.max_cantilever_load_kg)} кг</b></div><div class="spec"><small>Высота подъёма</small><b>${fmt(x.max_lift_height_m)} м</b></div>
    <div class="spec"><small>Ручей / угол</small><b>${x.groove_shape_normalized||'—'} / ${fmt(x.undercut_angle_normalized)}°</b></div><div class="spec"><small>Тормоз</small><b>${x.brake_voltage_normalized||'—'}</b></div>
    <div class="spec"><small>Включений/час</small><b>${fmt(x.starts_per_hour)}</b></div><div class="spec"><small>Масса</small><b>${fmt(x.weight_kg)} кг</b></div>
    <div class="spec"><small>Размещение</small><b>${x.placement_type_normalized||'—'}</b></div>
  </div><div class="card__footer"><span class="card__note">Данные из актуального Excel · строка ${x.source_row||'—'}</span><div class="card__actions"><button class="ghost-button compare-button" data-compare-id="${x.id}" data-action="compare" data-product-id="${x.id}">Сравнить</button><button class="details-btn" data-action="details" data-product-id="${x.id}">Подробнее</button><a class="details-btn" href="/product/${x.id}/inquiry">Заполнить опросный лист</a><a class="request-price" href="/product/${x.id}/order">Заказать лебёдку</a><button class="use" data-action="choose" data-product-id="${x.id}">Выбрать →</button></div></div></article>`;
}
function updateAngleOptions(){
  const shape=$('groove_shape').value, angle=$('undercut_angle');
  angle.innerHTML='';
  if(!shape){ angle.disabled=true; angle.innerHTML='<option value="">Сначала форма ручья</option>'; return; }
  angle.disabled=false; angle.appendChild(new Option('Любой угол',''));
  (meta.undercut_angles[shape]||[]).forEach(v=>angle.appendChild(new Option(`${v}°`,v)));
}
function updateSpeedCountOptions(){
  const type=$('winch_type').value, s=$('speed_count'), hint=$('speed_count_hint');
  const previous=s.value;
  s.innerHTML='';
  if(!type){
    s.disabled=true;
    s.appendChild(new Option('Сначала выберите тип лебёдки',''));
    if(hint) hint.textContent='У безредукторных всегда 1 скорость';
    return;
  }
  if(type==='Безредукторная таблетка' || type==='Безредукторная бочонок'){
    s.disabled=true;
    s.appendChild(new Option('1 скорость','1'));
    s.value='1';
    if(hint) hint.textContent='Для безредукторных значение фиксировано';
    return;
  }
  if(type==='Редукторная'){
    s.disabled=false;
    s.appendChild(new Option('1 скорость','1'));
    s.appendChild(new Option('2 скорости','2'));
    s.value=(previous==='1'||previous==='2')?previous:'1';
    if(hint) hint.textContent='Для редукторных: 1 или 2 скорости';
    return;
  }
  s.disabled=true;
  s.appendChild(new Option('Сначала выберите тип лебёдки',''));
}

function renderCoverage(){
  const c=meta.data_coverage||{}, bits=[];
  if(c.max_lift_height<meta.count) bits.push(`высота заполнена у ${c.max_lift_height} из ${meta.count}`);
  if(c.vfd_explicit<meta.count) bits.push(`ЧП явно указан у ${c.vfd_explicit}`);
  if(c.encoder_type_explicit<meta.count) bits.push(`тип энкодера указан у ${c.encoder_type_explicit}`);
  if(c.placement_type<meta.count) bits.push(`тип размещения указан у ${c.placement_type}`);
  $('coverage').innerHTML=bits.length?`<b>Важно по исходным данным:</b> ${bits.join(' · ')}. Поэтому эти фильтры пока могут сильнее сужать выдачу.`:'';
}
function openFilters(){
  if(innerWidth>820){ document.getElementById('selector').scrollIntoView({behavior:'smooth',block:'start'}); return; }
  document.querySelector('.selector-toolbar').classList.add('mobile-open');
  $('drawer_backdrop').classList.add('visible'); document.body.classList.add('drawer-open');
}
function closeFilters(){
  document.querySelector('.selector-toolbar').classList.remove('mobile-open');
  $('drawer_backdrop').classList.remove('visible'); document.body.classList.remove('drawer-open');
}

async function init(){
  meta=await fetch('/api/meta').then(r=>r.json());
  fill('manufacturer',meta.manufacturers); fill('winch_type',meta.winch_types); fill('capacity',meta.capacities);
  fillRanges('speed',meta.speed_ranges); fill('suspension',meta.suspensions); updateSpeedCountOptions();
  fill('vfd',meta.vfd_options); fill('encoder_type',meta.encoder_types); fillRanges('power',meta.power_ranges);
  fillValueLabels('cantilever',meta.cantilever_limits); fillValueLabels('lift_height',meta.lift_height_limits); fill('groove_shape',meta.groove_shapes);
  fill('sheave',meta.sheave_diameters); fill('rope_count',meta.rope_counts); fill('rope_diameter',meta.rope_diameters); fill('starts_per_hour',meta.starts_per_hour); fill('brake_voltage',meta.brake_voltages); fill('weight',meta.weights); fill('frame_supply',meta.frame_options); fill('remote_release',meta.remote_release_options); fill('placement_type',meta.placement_types);
  const placementCoverage=(meta.data_coverage||{}).placement_type||0;
  if(placementCoverage===0){ $('placement_type').disabled=true; $('placement_type').innerHTML='<option value="">Нет данных в текущей базе</option>'; $('placement_hint').textContent='Для текущей базы нет классифицируемых MR/MRL значений.'; }
  $('hero_count').textContent=meta.count.toLocaleString('ru-RU'); renderCoverage(); renderActiveFilters();
  if(window.__INITIAL_SEARCH__){
    // SSR уже вывел первые карточки. Не перерисовываем их JavaScript-ом:
    // обновляем только счётчики и пагинацию. Это исключает конфликт SSR/JS.
    const d=window.__INITIAL_SEARCH__;
    const shown=Math.min((d.offset||0)+(d.count||0),d.total||0);
    const counter=$('counter');if(counter)counter.textContent=d.total?`Найдено ${Number(d.total).toLocaleString('ru-RU')} · показано ${shown.toLocaleString('ru-RU')}`:'Ничего не найдено';
    const label=$('search_label');if(label)label.textContent=d.total?`Показать ${Number(d.total).toLocaleString('ru-RU')} моделей`:'Показать подходящие';
    const wrap=$('load_more_wrap');if(wrap)wrap.classList.toggle('hidden',!d.has_more);
    const more=$('load_more');if(more)more.textContent=`Показать ещё ${Math.min(PAGE_SIZE,Math.max(0,(d.total||0)-shown))}`;
  }else{
    await search(true);
  }
  // Калькулятор не должен блокировать появление каталога.
  quote().catch(e=>console.error('quote init failed',e));
  validateCalculator().catch(e=>console.error('validation init failed',e));
}
function renderSearchResponse(d, reset=true){
  const grid=$('results_grid');
  renderActiveFilters();
  const cards=(d.items||[]).map(x=>{
    try{return cardHtml(x)}catch(err){console.error('card render failed',x&&x.id,err);return ''}
  }).join('');
  if(reset){
    grid.innerHTML=cards||'<div class="empty-state"><b>Подходящих вариантов не найдено</b><span>Попробуйте убрать один из фильтров.</span></div>';
  }else if(cards){
    grid.insertAdjacentHTML('beforeend',cards);
  }
  const shown=Math.min((d.offset||0)+(d.count||0),d.total||0);
  if($('counter')) $('counter').textContent=d.total?`Найдено ${Number(d.total).toLocaleString('ru-RU')} · показано ${shown.toLocaleString('ru-RU')}`:'Ничего не найдено';
  if($('search_label')) $('search_label').textContent=d.total?`Показать ${Number(d.total).toLocaleString('ru-RU')} моделей`:'Показать подходящие';
  if($('load_more_wrap')) $('load_more_wrap').classList.toggle('hidden',!d.has_more);
  if($('load_more')){
    $('load_more').disabled=false;
    $('load_more').textContent=`Показать ещё ${Math.min(PAGE_SIZE,Math.max(0,(d.total||0)-shown))}`;
  }
}

async function search(reset=true){
  const grid=$('results_grid');
  if(reset){searchOffset=0;grid.innerHTML='<div class="empty-state"><b>Ищем подходящие модели…</b><span>Загрузка каталога</span></div>';}else{$('load_more').disabled=true;$('load_more').textContent='Загружаем…';}
  const controller=new AbortController();
  const timer=setTimeout(()=>controller.abort(),12000);
  try{
    const response=await fetch('/api/search?'+buildSearchParams(),{signal:controller.signal,cache:'no-store'});
    if(!response.ok) throw new Error(`HTTP ${response.status}`);
    const d=await response.json();
    renderSearchResponse(d,reset);
  }catch(e){
    console.error('search failed',e);
    if(reset) grid.innerHTML=`<div class="empty-state error"><b>Не удалось загрузить модели</b><span>${e.name==='AbortError'?'Ответ сервера занял слишком много времени':'Ошибка загрузки каталога'}</span><button class="details-btn" onclick="search(true)">Повторить</button></div>`;
    $('counter').textContent='Ошибка загрузки';
  }finally{
    clearTimeout(timer);
    if($('load_more')){$('load_more').disabled=false;}
  }
}
async function loadMore(){searchOffset+=PAGE_SIZE;await search(false);}
async function choose(id){
  const x=await fetch('/api/products/'+id).then(r=>r.json());
  currentProductId=id; currentProduct=x; currentModel=`${x.manufacturer||''} ${x.model||''}`.trim();
  $('selected_model').textContent=currentModel;
  if(x.manufacturer_price_cny && $('purchase')) $('purchase').value=x.manufacturer_price_cny;
  await quote(); document.querySelector('#calc').scrollIntoView({behavior:'smooth',block:'start'});
}
function calcBody(){
  return {
    model:currentModel, mode:$('mode').value,
    purchase_cny:+$('purchase').value, bank_commission_cny:+$('bank').value, bank_commission_eur:+$('bank_eur').value,
    rail_delivery_usd:+$('delivery').value, delivery_days:+$('delivery_days').value, production_days:+$('production_days').value, supply_days:+$('supply_days').value,
    qty_container:+$('qty').value, eur_rate:+$('eur').value, usd_rate:+$('usd').value, cny_rate:+$('cny').value,
    credit_rate:+$('credit').value, supplier_agent_rate:+$('agent').value, client_conversion_additive:+$('client_conversion').value,
    cny_conversion_markup:+$('conversion_markup').value, currency_control_rate:+$('currency_control').value,
    svh_rub:+$('svh').value, broker_rub:+$('broker').value, overhead_ratio:+$('overhead').value,
    sales_markup:+$('markup').value, discount:+$('discount').value, last_mile_cny:+$('last_mile').value,
    pass_price_cny:+$('pass_price').value, defer_days:+$('defer').value,
    delivery_first_share:+$('delivery_first_share').value, delivery_second_share:+$('delivery_second_share').value,
    supplier_first_share:+$('supplier_first_share').value, supplier_second_share:+$('supplier_second_share').value
  };
}
function rub(v){return `${Number(v||0).toLocaleString('ru-RU',{maximumFractionDigits:0})} ₽`;}
function cny(v){return `${Number(v||0).toLocaleString('ru-RU',{maximumFractionDigits:2})} CNY`;}
function renderInternal(d){
  if(!d.internal){$('internal_cards').innerHTML='';$('internal').textContent='';return;}
  const first=d.internal.postpay||Object.values(d.internal)[0]||{};
  const cards=[['Себестоимость',cny(first.cost_cny)],['Кредитные расходы',rub(first.credit_cost_rub)],['Адм. расходы',cny(first.admin_cny)],['Наценка',cny(first.markup_cny)],['Поставщик',rub(first.supplier_total_rub)],['Валютный контроль',rub(first.currency_control_rub)],['Объём продажи',rub(first.volume_sale_rub)],['Разница к проходной',cny(first.profit_vs_pass_cny)]];
  $('internal_cards').innerHTML=cards.map(([a,b])=>`<div class="internal-card"><small>${a}</small><b>${b}</b></div>`).join('');
  $('internal').textContent=JSON.stringify(d.internal,null,2);
}
async function quote(){
  const employee=$('mode').value==='employee', body=calcBody();
  const d=await fetch('/api/quote',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}).then(r=>r.json());
  const keys=Object.keys(d.prices), min=Math.min(...keys.map(k=>d.prices[k].price_cny));
  $('prices').innerHTML=keys.map(k=>{const x=d.prices[k];return `<div class="price"><span>${x.label}</span><strong>${x.price_cny.toLocaleString('ru-RU')} CNY</strong><small>${x.price_cny===min?'Минимальная стоимость':'Расчёт по выбранным условиям'}</small></div>`}).join('');
  lastQuoteResponse=d;
  renderInternal(d);
  $('internal_wrap').classList.toggle('hidden',!employee); $('reverse_panel').classList.toggle('hidden',!employee);
}
async function validateCalculator(){
  const d=await fetch('/api/calculator/validate').then(r=>r.json());
  const el=$('calc_validation'); if(!el)return;
  el.className='calc-validation '+(d.ok?'ok':'bad');
  el.textContent=d.ok?'✓ Формулы сверены с исходным Excel: все 4 сценария совпадают.':'⚠ Есть расхождение с эталонным Excel — требуется проверка.';
}
async function reverseQuote(){
  const body={...calcBody(),target_sale_cny:+$('target_sale').value,scenario:$('reverse_scenario').value};
  const d=await fetch('/api/quote/reverse',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}).then(r=>r.json());
  $('reverse_result').innerHTML=`<div class="reverse-card"><div><span>Условия</span><strong>${d.label}</strong></div><div><span>Целевая цена</span><strong>${cny(d.target_sale_cny)}</strong></div><div><span>Расчётная закупка</span><strong>${cny(d.purchase_cny)}</strong></div><div><span>Проверка</span><strong>${cny(d.calculated_sale_cny)}</strong></div></div>`;
}
function setCalcDefaults(){
 const v={purchase:6200,bank:470,bank_eur:100,delivery:9000,delivery_days:25,production_days:21,supply_days:55,qty:67,eur:94.94,usd:81,cny:11.1209,credit:.27,agent:.02,client_conversion:.02,conversion_markup:.04,currency_control:.006,svh:20000,broker:20000,overhead:.11957242476804819,markup:.15,discount:0,last_mile:0,pass_price:10960,defer:60,delivery_first_share:.5,delivery_second_share:.5,supplier_first_share:.5,supplier_second_share:.5};
 Object.entries(v).forEach(([k,val])=>{if($(k))$(k).value=val}); quote();
}

function bindClick(id,handler){const el=$(id);if(el)el.addEventListener('click',handler);}
function bindChange(id,handler){const el=$(id);if(el)el.addEventListener('change',handler);}
function bindUI(){
  document.querySelectorAll('[data-goto]').forEach(b=>b.addEventListener('click',()=>{const el=document.getElementById(b.dataset.goto);if(el)el.scrollIntoView({behavior:'smooth',block:'start'});}));
  bindClick('search',async()=>{await search(true);closeFilters();const r=$('results');if(r)r.scrollIntoView({behavior:'smooth',block:'start'});});
  bindClick('reset',()=>{document.querySelectorAll('#selector select').forEach(s=>s.selectedIndex=0);const q=$('q');if(q)q.value='';updateAngleOptions();updateSpeedCountOptions();renderActiveFilters();search(true);});
  bindClick('load_more',loadMore);
  bindClick('quote',quote);
  bindClick('reverse_quote',reverseQuote);
  bindClick('calc_defaults',setCalcDefaults);
  bindChange('mode',()=>{const panel=$('employee_inputs');if(panel)panel.classList.toggle('hidden',$('mode').value!=='employee');quote();});
  bindChange('groove_shape',()=>{updateAngleOptions();renderActiveFilters();});
  bindChange('winch_type',()=>{updateSpeedCountOptions();renderActiveFilters();});
  document.querySelectorAll('#selector select').forEach(s=>s.addEventListener('change',renderActiveFilters));
  const q=$('q');if(q)q.addEventListener('input',renderActiveFilters);
  bindClick('mobile_filters',openFilters);
  bindClick('mobile_filters_bottom',openFilters);
  bindClick('mobile_close',closeFilters);
  bindClick('drawer_backdrop',closeFilters);
  bindClick('compare_open',openCompare);
  bindClick('compare_clear',()=>{compareIds.clear();compareProducts.clear();updateCompareTray();});
  document.addEventListener('keydown',e=>{if(e.key==='Escape'){closeFilters();if($('product_modal')&&!$('product_modal').classList.contains('hidden'))closeProduct();if($('inquiry_modal')&&!$('inquiry_modal').classList.contains('hidden'))closeInquiry();if($('compare_modal')&&!$('compare_modal').classList.contains('hidden'))closeCompare();}});

  // Один делегированный обработчик для карточек: работает и для SSR, и для карточек после AJAX.
  document.addEventListener('click',e=>{
    const b=e.target.closest('[data-action]');if(!b)return;
    const id=Number(b.dataset.productId||b.closest('[data-product-id]')?.dataset.productId||0);
    const action=b.dataset.action;
    if(action==='compare'&&id)toggleCompare(id);
    if(action==='details'&&id)showProduct(id);
    if(action==='inquiry'&&id)openInquiry(id);
    if(action==='choose'&&id)choose(id);
  });
}

async function bootstrap(){
  try{
    bindUI();
    await init();
    startCompareObserver();
    document.documentElement.classList.add('js-ready');
  }catch(e){
    console.error('BOOTSTRAP FAILED',e);
    document.documentElement.classList.add('js-error');
    const c=$('counter');if(c&&c.textContent.includes('Загрузка'))c.textContent='838 моделей загружены';
  }
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bootstrap,{once:true});else bootstrap();


function filterSnapshot(){
  const out={};
  FILTERS.forEach(([id,label])=>{const el=$(id);if(el&&el.value)out[label]=selectedLabel(id)+(UNITS[id]||'')});
  return out;
}
function productValue(p,k){
  if(!p)return '';
  let v=p[k];
  if(k==='placement_type') v=p.placement_type||p.placement_type_normalized;
  if(k==='suspensions'&&Array.isArray(v)) v=v.join(', ');
  if((k==='rope_counts'||k==='rope_diameters_mm')&&Array.isArray(v)) v=v.join(', ');
  if(k==='vfd_brand'&&!v) v=p.vfd_normalized;
  if(k==='encoder_brand'&&!v) v=p.encoder_type_normalized;
  if(k==='groove_shape'&&!v) v=p.groove_shape_normalized;
  if(k==='brake_voltage'&&!v) v=p.brake_voltage_normalized;
  if(typeof v==='boolean') return v?'Да':'Нет';
  if(v==='on_request') return 'По запросу';
  return v??'';
}
function filterAutofill(key){
  const ids={winch_type:'winch_type',placement_type:'placement_type',starts_per_hour:'starts_per_hour',suspension:'suspension',capacity:'capacity',speed:'speed',speed_count:'speed_count',vfd:'vfd',encoder_type:'encoder_type',power:'power',cantilever:'cantilever',lift_height:'lift_height',sheave:'sheave',rope_count:'rope_count',rope_diameter:'rope_diameter',groove_shape:'groove_shape',brake_voltage:'brake_voltage',weight:'weight',frame_supply:'frame_supply',remote_release:'remote_release'};
  const id=ids[key],el=id?$(id):null; return el&&el.value?selectedLabel(id):'';
}
function inquiryFieldHtml(f,p){
  if(f.kind==='heading')return `<div class="q-heading">${f.label}</div>`;
  let value=''; let auto=false;
  if(f.autofill_filter){value=filterAutofill(f.autofill_filter);auto=!!value;}
  if(!value&&f.autofill_product){value=productValue(p,f.autofill_product);auto=!!value;}
  const cls=`q-field ${f.kind==='textarea'?'full':''} ${auto?'autofilled':''}`;
  const autoTag=auto?'<span class="q-auto">Заполнено автоматически</span>':'';
  const val=String(value??'').replace(/"/g,'&quot;');
  if(f.kind==='select')return `<div class="${cls}"><label>${f.label}</label>${autoTag}<select data-qcode="${f.code}" data-qlabel="${encodeURIComponent(f.label)}"><option value="">— выберите —</option>${(f.options||[]).map(o=>`<option value="${o}" ${String(o)===String(value)?'selected':''}>${o}</option>`).join('')}</select></div>`;
  if(f.kind==='checkbox')return `<div class="${cls} q-check"><input type="checkbox" data-qcode="${f.code}" data-qlabel="${encodeURIComponent(f.label)}" ${value?'checked':''}><label>${f.label}</label>${autoTag}</div>`;
  if(f.kind==='textarea')return `<div class="${cls}"><label>${f.label}</label>${autoTag}<textarea data-qcode="${f.code}" data-qlabel="${encodeURIComponent(f.label)}">${String(value??'')}</textarea></div>`;
  return `<div class="${cls}"><label>${f.label}</label>${autoTag}<input type="${f.kind==='date'?'date':f.kind==='number'?'number':'text'}" step="${f.kind==='number'?'any':''}" value="${val}" data-qcode="${f.code}" data-qlabel="${encodeURIComponent(f.label)}"></div>`;
}
async function openInquiry(id){
  currentProductId=id; currentProduct=await fetch('/api/products/'+id).then(r=>r.json()); currentModel=`${currentProduct.manufacturer||''} ${currentProduct.model||''}`.trim();
  $('selected_model').textContent=currentModel;
  if(!questionnaireSchema)questionnaireSchema=await fetch('/api/questionnaire/schema').then(r=>r.json());
  $('inquiry_product_title').textContent=`${currentModel} · опросный лист из «${questionnaireSchema.source_sheet}»`;
  $('inquiry_form').innerHTML=questionnaireSchema.groups.map((g,i)=>`<details class="q-group" ${i<2?'open':''}><summary>${g.name}<span>${g.fields.filter(f=>f.kind!=='heading').length} полей</span></summary><div class="q-fields">${g.fields.map(f=>inquiryFieldHtml(f,currentProduct)).join('')}</div></details>`).join('');
  $('inquiry_status').textContent=''; $('inquiry_modal').classList.remove('hidden'); document.body.style.overflow='hidden';
}
function closeInquiry(){$('inquiry_modal').classList.add('hidden');document.body.style.overflow='';}
async function submitInquiry(){
  if(!currentProductId)return alert('Сначала выберите лебёдку');
  const answers={}; document.querySelectorAll('#inquiry_form [data-qcode]').forEach(el=>{const label=decodeURIComponent(el.dataset.qlabel||el.dataset.qcode);let v=el.type==='checkbox'?el.checked:el.value;if(v!==''&&v!==false)answers[label]=v;});
  const btn=$('inquiry_send');btn.disabled=true;btn.textContent='Отправляем…';
  const body={product_id:currentProductId,filters:filterSnapshot(),answers,quote:lastQuoteResponse};
  const r=await fetch('/api/inquiries',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const d=await r.json();
  btn.disabled=false;btn.textContent='Отправить запрос цены →';
  if(d.ok){$('inquiry_status').className='inquiry-success';$('inquiry_status').textContent=`Запрос ${d.number} сохранён. Статус: новый.`;}else{$('inquiry_status').textContent=d.detail||'Не удалось отправить запрос';}
}

async function showProduct(id){
 const x=await fetch('/api/products/'+id).then(r=>r.json());
 const labels={nominal_current_a:'Номинальный ток, А',nominal_rpm:'Номинальные обороты, об/мин',frequency_hz:'Частота, Гц',torque_nm:'Крутящий момент, Н·м',groove_pitch_mm:'Шаг канавок КВШ, мм',groove_open_angle:'Угол раскрытия канавки',handwheel:'Маховик',remote_release:'Дистанционное расцепление',inertia_kgm2:'Момент инерции, кг·м²',w1:'W1',w2:'W2',h2:'h2',d4:'d4',d5:'d5',winding_type:'Тип намотки',frame_supply:'Поставка с рамой',frame_code:'Код рамы',duty_cycle:'Duty cycle',gear_ratio:'Передаточное число',vfd_brand:'Бренд ЧП',encoder_brand:'Бренд энкодера'};
 const val=v=>v===true?'Да':v===false?'Нет':v==='on_request'?'По запросу':(v??'—');
 const tech=Object.entries(labels).map(([k,l])=>`<div class="detail-item"><small>${l}</small><b>${val(x[k])}</b></div>`).join('');
 const raw=Object.entries(x.raw||{}).filter(([,v])=>v!==null&&v!=='').map(([k,v])=>`<tr><td>${k}</td><td>${val(v)}</td></tr>`).join('');
 $('product_modal_body').innerHTML=`<div class="detail-title"><span class="section-kicker">${x.manufacturer||''}</span><h2>${x.model||''}</h2><p>${x.winch_type||''}</p></div><div class="detail-grid">${tech}</div><h3>Все исходные характеристики</h3><table class="raw-table">${raw}</table>`;
 $('product_modal').classList.remove('hidden'); document.body.style.overflow='hidden';
}
function closeProduct(){$('product_modal').classList.add('hidden');document.body.style.overflow='';}


// --- Engineering compare ----------------------------------------------------
function compareLabel(p){return `${p.manufacturer||''} ${p.model||''}`.trim() || `#${p.id}`;}
function updateCompareTray(){
  const tray=$('compare_tray'); if(!tray)return;
  $('compare_count').textContent=`${compareIds.size} из 4`;
  $('compare_open').disabled=compareIds.size<2;
  tray.classList.toggle('hidden',compareIds.size===0);
  $('compare_chips').innerHTML=[...compareIds].map(id=>{const p=compareProducts.get(id)||{};return `<button class="compare-chip" type="button" onclick="toggleCompare(${id})">${compareLabel(p)} <span>×</span></button>`}).join('');
  document.querySelectorAll('[data-compare-id]').forEach(btn=>{const id=+btn.dataset.compareId;const on=compareIds.has(id);btn.classList.toggle('active',on);btn.textContent=on?'✓ В сравнении':'Сравнить';});
}
async function toggleCompare(id){
  id=+id;
  if(compareIds.has(id)){compareIds.delete(id);compareProducts.delete(id);updateCompareTray();return;}
  if(compareIds.size>=4){alert('Можно сравнить не более 4 лебёдок');return;}
  let p=compareProducts.get(id);
  if(!p){p=await fetch('/api/products/'+id).then(r=>r.json());compareProducts.set(id,p);}
  compareIds.add(id);updateCompareTray();
}
function productImage(p){
  const url=p.image_url||p.photo_url||p.image_ref;
  if(url && (url.startsWith('http://')||url.startsWith('https://')))return `<img src="${url}" alt="${compareLabel(p)}" loading="lazy" onerror="this.parentNode.innerHTML=engineeringPlaceholder('${(p.manufacturer||'').replace(/'/g,'')}')">`;
  return engineeringPlaceholder(p.manufacturer||'');
}
function engineeringPlaceholder(manufacturer){
  const ab=(manufacturer||'L').slice(0,2).toUpperCase();
  return `<div class="engineering-placeholder"><span>${ab}</span><svg viewBox="0 0 240 150" aria-hidden="true"><circle cx="148" cy="77" r="47"></circle><circle cx="148" cy="77" r="12"></circle><rect x="38" y="48" width="76" height="58" rx="9"></rect><path d="M114 59h24M114 95h24M148 30v20M148 104v20"></path></svg></div>`;
}
function compareValue(p,key,unit){let v=p?.[key];if(v===null||v===undefined||v==='')return '<span class="compare-empty">—</span>';if(Array.isArray(v))v=v.join(', ');return `${v}${unit?' '+unit:''}`;}
async function openCompare(){
  if(compareIds.size<2)return;
  const d=await fetch('/api/compare',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ids:[...compareIds]})}).then(r=>r.json());
  d.items.forEach(p=>compareProducts.set(+p.id,p));
  const cols=d.items.map(p=>`<th><div class="compare-product-head"><div class="compare-photo">${productImage(p)}</div><span>${p.manufacturer||''}</span><strong>${p.model||''}</strong><small>${p.winch_type||''}</small><button class="text-button" onclick="showProduct(${p.id})">Все характеристики</button></div></th>`).join('');
  const rows=d.fields.map(f=>{const vals=d.items.map(p=>String(p[f.key]??''));const diff=new Set(vals).size>1;return `<tr class="${diff?'compare-diff':''}"><th>${f.label}</th>${d.items.map(p=>`<td>${compareValue(p,f.key,f.unit)}</td>`).join('')}</tr>`}).join('');
  $('compare_table_wrap').innerHTML=`<div class="compare-scroll"><table class="compare-table"><thead><tr><th>Параметр</th>${cols}</tr></thead><tbody>${rows}</tbody></table></div><div class="compare-note">Различающиеся строки подсвечены. Сравнение: фотография, мощность, максимальная консольная нагрузка, угол подреза, диаметр КВШ и масса.</div>`;
  $('compare_modal').classList.remove('hidden');document.body.style.overflow='hidden';
}
function closeCompare(){$('compare_modal').classList.add('hidden');document.body.style.overflow='';}
function injectCompareButtons(){
  document.querySelectorAll('[data-product-id]').forEach(card=>{const id=+card.dataset.productId;if(!id||card.querySelector('[data-compare-id]'))return;const actions=card.querySelector('.product-card__actions,.card-actions,.result-actions');if(actions){const b=document.createElement('button');b.type='button';b.className='ghost-button compare-button';b.dataset.compareId=id;b.textContent='Сравнить';b.onclick=()=>toggleCompare(id);actions.prepend(b);}});
  // fallback for cards without data-product-id: parse buttons calling showProduct/openInquiry
  document.querySelectorAll('button[onclick*="showProduct("],button[onclick*="openInquiry("]').forEach(btn=>{const card=btn.closest('.product-card,.result-card,.card');if(!card||card.querySelector('[data-compare-id]'))return;const m=(btn.getAttribute('onclick')||'').match(/\((\d+)\)/);if(!m)return;const id=+m[1];card.dataset.productId=id;const actions=btn.parentElement;const b=document.createElement('button');b.type='button';b.className='ghost-button compare-button';b.dataset.compareId=id;b.textContent='Сравнить';b.onclick=()=>toggleCompare(id);actions.prepend(b);});
  updateCompareTray();
}
const compareObserver=new MutationObserver(()=>injectCompareButtons());
function startCompareObserver(){const r=$('results');if(r)compareObserver.observe(r,{childList:true,subtree:true});setTimeout(injectCompareButtons,100);}
