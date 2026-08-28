const { Component } = React;
const EMPTY = { q: '', manufacturer: '', winch_type: '', capacity_kg: '', speed_range: '', suspension: '', speed_count: '', vfd: '', encoder_type: '', power_range: '', cantilever_required_kg: '', lift_height_required_m: '', groove_shape: '', undercut_angle: '', sheave_diameter_mm: '', rope_count: '', rope_diameter_mm: '', starts_per_hour: '', brake_voltage: '', weight_kg: '', placement_type: '' };
const fmt = (v, u = '') => (v === null || v === undefined || v === '') ? '—' : String(v).replace('.', ',') + (u ? ' ' + u : '');
const arr = v => Array.isArray(v) && v.length ? v.join(', ') : '—';
function params(f, extra = {}) { const p = new URLSearchParams(); Object.keys(f).forEach(k => { const v = f[k]; if (v === '' || v == null)
    return; if (k === 'speed_range') {
    const z = String(v).split('|');
    p.set('speed_min', z[0]);
    p.set('speed_max', z[1]);
}
else if (k === 'power_range') {
    const z = String(v).split('|');
    p.set('power_min', z[0]);
    p.set('power_max', z[1]);
}
else
    p.set(k, v); }); Object.keys(extra).forEach(k => p.set(k, String(extra[k]))); return p; }

const EXECUTION_DIFF_FIELDS=[
  {key:'capacity_kg',label:'Грузоподъёмность',fmt:v=>fmt(v,'кг')},
  {key:'speed_m_s',label:'Скорость',fmt:v=>fmt(v,'м/с')},
  {key:'power_kw',label:'Мощность',fmt:v=>fmt(v,'кВт')},
  {key:'suspensions',label:'Подвес',fmt:v=>arr(v)},
  {key:'sheave_diameter_mm',label:'КВШ',fmt:v=>fmt(v,'мм')},
  {key:'rope_counts',label:'Канаты',fmt:v=>arr(v)},
  {key:'rope_diameters_mm',label:'Ø каната',fmt:v=>arr(v)==='—'?'—':arr(v)+' мм'},
  {key:'max_cantilever_load_kg',label:'Консольная нагрузка',fmt:v=>fmt(v,'кг')},
  {key:'weight_kg',label:'Масса',fmt:v=>fmt(v,'кг')},
  {key:'nominal_current_a',label:'Ток',fmt:v=>fmt(v,'A')},
  {key:'nominal_rpm',label:'Обороты',fmt:v=>fmt(v,'об/мин')},
  {key:'frequency_hz',label:'Частота',fmt:v=>fmt(v,'Гц')},
  {key:'torque_nm',label:'Момент',fmt:v=>fmt(v,'Н·м')},
  {key:'undercut_angle',label:'Угол подреза',fmt:v=>v||'—'},
  {key:'groove_pitch_mm',label:'Шаг канавок',fmt:v=>fmt(v,'мм')},
  {key:'brake_voltage',label:'Тормоз',fmt:v=>v||'—'},
  {key:'winding_type',label:'Намотка',fmt:v=>v||'—'},
  {key:'placement_type',label:'Размещение',fmt:v=>v||'—'}
];
const executionValue=function(e){return function(v){var value=e[v];return Array.isArray(value)?JSON.stringify(value):String(value===null||value===undefined?'':value);};};
function executionDiffFields(execs){
  if(!execs||execs.length<2)return [];
  return EXECUTION_DIFF_FIELDS.filter(f=>{const vals=new Set(execs.map(e=>executionValue(e)(f.key)));return vals.size>1;});
}


function ExecutionSelector(props){
  var execs=Array.isArray(props.execs)?props.execs.filter(Boolean):[];
  if(execs.length<2) return null;
  var diffs=executionDiffFields(execs);
  var head=[
    React.createElement('th',{key:'pick',className:'pick-col'},'Выбор'),
    React.createElement('th',{key:'id'},'ID')
  ];
  diffs.forEach(function(f){ head.push(React.createElement('th',{key:f.key},f.label)); });
  var rows=execs.map(function(e){
    var selected=String(e.id)===String(props.selectedId);
    var cells=[
      React.createElement('td',{key:'pick',className:'pick-col'},
        React.createElement('button',{type:'button',className:'execution-radio-button '+(selected?'checked':''),onClick:function(ev){ev.stopPropagation();props.onSelect(e.id);},'aria-pressed':selected},selected?'●':'○'),
        selected?React.createElement('em',{className:'selected-badge'},'Выбрано'):null),
      React.createElement('td',{key:'id'},React.createElement('b',null,'#'+e.id))
    ];
    diffs.forEach(function(f){
      var val='—';
      try { val=f.fmt(e ? e[f.key] : null); } catch(err) { val='—'; }
      cells.push(React.createElement('td',{key:f.key,className:'diff-cell'},val));
    });
    return React.createElement('tr',{key:e.id,className:selected?'selected':'',onClick:function(){props.onSelect(e.id);},role:'button','aria-pressed':selected,tabIndex:0,onKeyDown:function(ev){if(ev.key==='Enter'||ev.key===' '){ev.preventDefault();props.onSelect(e.id);}}},cells);
  });
  return React.createElement('section',{className:'executions'},
    React.createElement('div',{className:'execution-title'},
      React.createElement('div',null,
        React.createElement('span',{className:'eyebrow orange'},'Исполнения модели'),
        React.createElement('h3',null,'Выберите конкретное исполнение'),
        React.createElement('p',{className:'execution-lead'},'От выбранного исполнения зависят расчёт стоимости, опросный лист и заказ.')),
      React.createElement('b',null,execs.length+' в базе')),
    React.createElement('div',{className:'execution-diff-note'},
      React.createElement('b',null,diffs.length?'Чем отличаются исполнения:':'Отличий в нормализованных характеристиках не найдено.'),
      diffs.length?' '+diffs.map(function(f){return f.label;}).join(', '):' Проверьте исходные строки Excel.'),
    React.createElement('div',{className:'execution-table-wrap'},
      React.createElement('table',{className:'execution-table execution-picker'},
        React.createElement('thead',null,React.createElement('tr',null,head)),
        React.createElement('tbody',null,rows))),
    React.createElement('p',{className:'execution-help'},'Нажмите на строку или переключатель. Показаны только характеристики, которыми исполнения реально отличаются.'));
}

class AppErrorBoundary extends Component {
  constructor(props){super(props);this.state={error:null};}
  componentDidCatch(error,info){console.error('LIFTORG_UI_ERROR',error,info);this.setState({error:error});}
  render(){
    if(this.state.error){
      return React.createElement('div',{style:{maxWidth:'900px',margin:'50px auto',padding:'24px',fontFamily:'Arial',border:'1px solid #e5e7eb',borderRadius:'16px'}},
        React.createElement('h2',null,'Ошибка интерфейса'),
        React.createElement('p',null,'Каталог не потерян. Произошла ошибка отображения одного из элементов.'),
        React.createElement('pre',{style:{whiteSpace:'pre-wrap',background:'#f7f8fa',padding:'12px',borderRadius:'10px'}},String(this.state.error&&this.state.error.message||this.state.error)),
        React.createElement('button',{onClick:function(){location.reload();}},'Перезагрузить интерфейс'),
        React.createElement('p',null,React.createElement('a',{href:'/legacy'},'Открыть резервный интерфейс')));
    }
    return this.props.children;
  }
}

function MachineVisual(props) {
    if(props && props.src) return React.createElement("div", { className: "machine-visual has-photo" }, React.createElement("img", { src: props.src, alt: props.alt || "Лебёдка", loading: "lazy", onError: e => { e.currentTarget.style.display="none"; } }));
    return React.createElement("div", { className: "machine-visual" },
        React.createElement("div", { className: "machine-body" }, React.createElement("i", null)),
        React.createElement("div", { className: "machine-wheel" }, React.createElement("i", null)),
        React.createElement("div", { className: "machine-shaft" }),
        React.createElement("span", null, "ФОТО МОДЕЛИ"));
}
function Field({ label, value, onChange, children, disabled = false }) { return React.createElement("label", { className: 'field ' + (disabled ? 'disabled' : '') },
    React.createElement("b", null, label),
    React.createElement("select", { value: value, disabled: disabled, onChange: e => onChange(e.target.value) }, children)); }
function Section({ id, title, subtitle, open, onToggle, children }) { return React.createElement("div", { className: 'f-section ' + (open ? 'open' : '') },
    React.createElement("button", { type: "button", className: "f-head", onClick: onToggle },
        React.createElement("em", null, id),
        React.createElement("span", null,
            React.createElement("b", null, title),
            React.createElement("small", null, subtitle)),
        React.createElement("i", null, open ? '−' : '+')),
    React.createElement("div", { className: "f-body" }, children)); }
function uniqFmt(values, unit='') {
    const a=(values||[]).filter(v=>v!==null&&v!==undefined&&v!=='');
    if(!a.length) return '—';
    const nums=a.map(Number).filter(v=>!isNaN(v)).sort((x,y)=>x-y);
    if(nums.length===a.length && nums.length>1) {
        const min=nums[0], max=nums[nums.length-1];
        if(min!==max) return fmt(min,unit)+' – '+fmt(max,unit);
    }
    return fmt(a[0],unit);
}
function ProductCard({ p, selected, onCompare, onDetails, onQuote, filters }) {
    const multi=(p.execution_count||1)>1;
    return React.createElement("article", { className: "product-card model-card" },
        React.createElement("div", { className: "media" },
            React.createElement(MachineVisual, { src: p.image_ref, alt: p.manufacturer + " " + p.model }),
            React.createElement("span", { className: "match " + (p.match_status === "needs_clarification" ? "warn" : "") }, p.match_status === "needs_clarification" ? "? Требует уточнения" : "✓ Подходит")),
        React.createElement("div", { className: "pc-body" },
            React.createElement("div", { className: "pc-head" },
                React.createElement("span", null, p.manufacturer),
                React.createElement("h3", null, p.model),
                React.createElement("small", null, p.winch_type || 'Тип уточняется')),
            multi && React.createElement("button", {className:"execution-badge", onClick:()=>onDetails(p.id)},
                React.createElement("b",null,p.execution_count), " исполнений", React.createElement("span",null,"Выбрать →")),
            React.createElement("div", { className: "spec-grid" },
                React.createElement("div", null,React.createElement("small", null, "Грузоподъёмность"),React.createElement("b", null, multi?uniqFmt(p.capacities,'кг'):fmt(p.capacity_kg,'кг'))),
                React.createElement("div", null,React.createElement("small", null, "Скорость"),React.createElement("b", null, multi?uniqFmt(p.speeds,'м/с'):fmt(p.speed_m_s,'м/с'))),
                React.createElement("div", null,React.createElement("small", null, "Мощность"),React.createElement("b", null, multi?uniqFmt(p.powers,'кВт'):fmt(p.power_kw,'кВт'))),
                React.createElement("div", null,React.createElement("small", null, "Подвес"),React.createElement("b", null, arr(p.suspensions))),
                React.createElement("div", null,React.createElement("small", null, "КВШ"),React.createElement("b", null, multi?uniqFmt(p.sheave_diameters,'мм'):fmt(p.sheave_diameter_mm,'мм'))),
                React.createElement("div", null,React.createElement("small", null, "Канаты"),React.createElement("b", null, arr(p.rope_counts), " × ", arr(p.rope_diameters_mm), " мм"))),
            React.createElement("div", { className: "mini-spec" },
                React.createElement("span", null,"Нагрузка ",React.createElement("b", null, fmt(p.max_cantilever_load_kg,'кг'))),
                React.createElement("span", null,"Масса ",React.createElement("b", null, multi?uniqFmt(p.weights,'кг'):fmt(p.weight_kg,'кг'))),
                React.createElement("span", null,"Угол ",React.createElement("b", null, fmt(p.undercut_angle_normalized,'°')))),
            p.match_summary && React.createElement("div", { className: "match-info" },
                React.createElement("b", null, p.match_status === "matched" ? (multi ? ("Есть полностью подтверждённые исполнения: "+(p.matched_execution_count||0)) : "Все выбранные параметры подтверждены") : "Требуется уточнение исходных данных"),
                multi ? React.createElement("small",null,"Подбор выполнен по исполнениям. Откройте модель и выберите конкретное исполнение для сравнения, расчёта или заявки.") : (p.clarifications&&p.clarifications.length?React.createElement("small",null,"Нужно уточнить: "+p.clarifications.slice(0,3).join(", ")):null)),
            React.createElement("div", { className: "pc-actions" },
                React.createElement("button", { className: 'compare ' + (selected ? 'active' : ''), onClick: () => multi?onDetails(p.id):onCompare(p), title: multi?"Сначала выберите исполнение":"Сравнить" }, multi?"⇄ Выбрать для сравнения":"⇄ Сравнить"),
                React.createElement("button", { className: "detail", onClick: () => onDetails(p.id) }, multi?"Исполнения":"Подробнее"),
                React.createElement("button", { className: "calc", onClick: () => multi?onDetails(p.id):onQuote(p) }, multi?"Выбрать и рассчитать":"Рассчитать"),
                React.createElement("a", { className: "detail", href: multi?('#model-'+p.id):('/product/' + p.id + '/inquiry?' + params(filters).toString()), onClick: e=>{if(multi){e.preventDefault();onDetails(p.id);}} }, multi?"Выбрать и заполнить опросник":"Заполнить опросный лист"),
                React.createElement("a", { className: "quote", href: multi?('#model-'+p.id):('/product/' + p.id + '/order?' + params(filters).toString()), onClick: e=>{if(multi){e.preventDefault();onDetails(p.id);}} }, multi?"Выбрать и заказать →":"Заказать лебёдку →"))));
}
class DetailsModal extends Component {
  constructor(props){super(props);this.state={data:null,group:null,error:'',selectedId:this.props.id};}
  componentDidMount(){
    Promise.all([
      fetch('/api/products/'+this.props.id).then(r=>r.json()),
      fetch('/api/products/'+this.props.id+'/custom-attributes').then(r=>r.json()).catch(()=>({items:[]})),
      fetch('/api/model-groups/'+this.props.id).then(r=>r.json()).catch(()=>null)
    ]).then(x=>{x[0].custom_attributes=x[1].items||[];this.setState({data:x[0],group:x[2],selectedId:x[0].id});}).catch(()=>this.setState({error:'Не удалось загрузить карточку'}));
  }
  selectExecution(id){
    Promise.all([fetch('/api/products/'+id).then(r=>r.json()),fetch('/api/products/'+id+'/custom-attributes').then(r=>r.json()).catch(()=>({items:[]}))])
      .then(x=>{x[0].custom_attributes=x[1].items||[];this.setState({data:x[0],selectedId:id});});
  }
  render(){
    const p=this.state.data, g=this.state.group;
    if(!p) return React.createElement('div',{className:'overlay',onMouseDown:e=>{if(e.target===e.currentTarget)this.props.onClose();}},React.createElement('div',{className:'modal'},React.createElement('button',{className:'close',onClick:this.props.onClose},'×'),React.createElement('div',{className:'loading'},this.state.error||'Загружаем технический паспорт…')));
    const rawRows=Object.keys(p.raw||{}).map(k=>React.createElement('div',{key:k},React.createElement('span',null,k),React.createElement('b',null,(p.raw[k]===null||p.raw[k]==='')?'—':String(p.raw[k]))));
    const groupExecs=(g&&Array.isArray(g.executions))?g.executions.filter(Boolean):[];
    const execs=groupExecs.length?groupExecs:[p];
    return React.createElement('div',{className:'overlay',onMouseDown:e=>{if(e.target===e.currentTarget)this.props.onClose();}},
      React.createElement('div',{className:'modal product-modal'},
        React.createElement('button',{className:'close',onClick:this.props.onClose},'×'),
        React.createElement('div',{className:'detail-hero'},React.createElement(MachineVisual,{src:p.image_ref,alt:p.manufacturer+' '+p.model}),React.createElement('div',null,
          React.createElement('span',{className:'eyebrow'},p.manufacturer),React.createElement('h2',null,p.model),React.createElement('p',null,p.winch_type||'Тип уточняется'),
          React.createElement('div',{className:'chips'},React.createElement('b',null,fmt(p.capacity_kg,'кг')),React.createElement('b',null,fmt(p.speed_m_s,'м/с')),React.createElement('b',null,fmt(p.power_kw,'кВт'))))),
        execs.length>1 && React.createElement(ExecutionSelector,{execs:execs,selectedId:this.state.selectedId,onSelect:(id)=>this.selectExecution(id)}),
        React.createElement('div',{className:'selected-execution'},React.createElement('span',null,'Выбранное исполнение'),React.createElement('b',null,'#'+p.id+' · '+fmt(p.capacity_kg,'кг')+' · '+fmt(p.speed_m_s,'м/с')+' · '+fmt(p.power_kw,'кВт'))),
        p.media&&p.media.length>0&&React.createElement('section',{className:'media-library-section'},
          React.createElement('div',{className:'execution-title'},React.createElement('div',null,React.createElement('span',{className:'eyebrow orange'},'Медиатека'),React.createElement('h3',null,'Фото, чертежи и документы'))),
          React.createElement('div',{className:'media-gallery-react'},p.media.map((m,i)=>m.media_kind==='document'?React.createElement('a',{key:i,className:'media-doc',href:m.url,target:'_blank'},'📄 '+(m.title||'Документ')):React.createElement('a',{key:i,className:'media-tile',href:m.url,target:'_blank'},React.createElement('img',{src:m.url,alt:m.title||p.model}),React.createElement('b',null,m.title||(m.media_kind==='drawing'?'Чертёж':'Фото')),React.createElement('small',null,m.media_kind==='drawing'?'Чертёж':'Фото'))))),
        React.createElement('div',{className:'tech-cols'},
          React.createElement(Tech,{title:'Основные',rows:[['Грузоподъёмность',fmt(p.capacity_kg,'кг')],['Скорость',fmt(p.speed_m_s,'м/с')],['Подвес',arr(p.suspensions)],['Количество скоростей',p.speed_count]]}),
          React.createElement(Tech,{title:'Привод',rows:[['Мощность',fmt(p.power_kw,'кВт')],['Ток',fmt(p.nominal_current_a,'A')],['Обороты',fmt(p.nominal_rpm,'об/мин')],['Частота',fmt(p.frequency_hz,'Гц')],['Крутящий момент',fmt(p.torque_nm,'Н·м')]]}),
          React.createElement(Tech,{title:'КВШ и канаты',rows:[['Диаметр КВШ',fmt(p.sheave_diameter_mm,'мм')],['Форма ручья',p.groove_shape],['Угол подреза',p.undercut_angle],['Канаты',arr(p.rope_counts)+' × '+arr(p.rope_diameters_mm)],['Шаг канавок',fmt(p.groove_pitch_mm,'мм')]]}),
          React.createElement(Tech,{title:'Эксплуатация',rows:[['Консольная нагрузка',fmt(p.max_cantilever_load_kg,'кг')],['Высота подъёма',fmt(p.max_lift_height_m,'м')],['Включений/час',p.starts_per_hour],['Масса',fmt(p.weight_kg,'кг')],['Тормоз',p.brake_voltage||p.brake_supply_voltage]]})),
        React.createElement('details',{className:'raw-details'},React.createElement('summary',null,'Все характеристики из исходного Excel'),React.createElement('div',{className:'raw-grid'},rawRows)),
        React.createElement('div',{className:'modal-actions'},
          React.createElement('button',{className:'detail '+(this.props.isCompared&&this.props.isCompared(p.id)?'dark':''),onClick:()=>this.props.onCompare(p)},this.props.isCompared&&this.props.isCompared(p.id)?'В сравнении':'Добавить исполнение к сравнению'),
          React.createElement('button',{className:'calc',onClick:()=>this.props.onQuote(p)},'Рассчитать стоимость'),
          React.createElement('a',{className:'detail',href:'/product/'+p.id+'/inquiry?'+params(this.props.filters).toString()},'Заполнить опросный лист'),
          React.createElement('a',{className:'quote',href:'/product/'+p.id+'/order?'+params(this.props.filters).toString()},'Заказать лебёдку →'))));
  }
}
function Tech({ title, rows }) { return React.createElement("section", { className: "tech" },
    React.createElement("h4", null, title),
    rows.map((r, i) => { var _a; return React.createElement("div", { key: i },
        React.createElement("span", null, r[0]),
        React.createElement("b", null, (_a = r[1]) !== null && _a !== void 0 ? _a : '—')); })); }
class CompareModal extends Component {
    constructor(p) { super(p); this.state = { data: null }; }
    componentDidMount() { this.load(this.props.items); }
    componentDidUpdate(prev) { if (prev.items.map(x => x.id).join(',') !== this.props.items.map(x => x.id).join(','))
        this.load(this.props.items); }
    load(items) { fetch('/api/compare', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ids: items.map(x => x.id) }) }).then(r => r.json()).then(data => this.setState({ data })); }
    render() { const d = this.state.data; return React.createElement("div", { className: "overlay" },
        React.createElement("div", { className: "modal compare-modal" },
            React.createElement("button", { className: "close", onClick: this.props.onClose }, "\u00D7"),
            React.createElement("span", { className: "eyebrow" }, "\u0418\u043D\u0436\u0435\u043D\u0435\u0440\u043D\u043E\u0435 \u0441\u0440\u0430\u0432\u043D\u0435\u043D\u0438\u0435"),
            React.createElement("h2", null,
                "\u0421\u0440\u0430\u0432\u043D\u0435\u043D\u0438\u0435 ",
                this.props.items.length,
                " \u043C\u043E\u0434\u0435\u043B\u0435\u0439"),
            !d ? React.createElement("div", { className: "loading" }, "\u0424\u043E\u0440\u043C\u0438\u0440\u0443\u0435\u043C \u0441\u0440\u0430\u0432\u043D\u0435\u043D\u0438\u0435\u2026") : React.createElement("div", { className: "compare-scroll" },
                React.createElement("table", null,
                    React.createElement("thead", null,
                        React.createElement("tr", null,
                            React.createElement("th", null, "\u041F\u0430\u0440\u0430\u043C\u0435\u0442\u0440"),
                            d.items.map(p => React.createElement("th", { key: p.id },
                                React.createElement(MachineVisual, { src: p.image_ref, alt: p.manufacturer + " " + p.model }),
                                React.createElement("small", null, p.manufacturer),
                                React.createElement("b", null, p.model),
                                React.createElement("button", { onClick: () => this.props.onRemove(p.id) }, "\u00D7"))))),
                    React.createElement("tbody", null, d.fields.map(f => React.createElement("tr", { key: f.key },
                        React.createElement("td", null, f.label),
                        d.items.map(p => React.createElement("td", { key: p.id }, fmt(p[f.key], f.unit)))))))))); }
}

class QuoteModal extends Component {
  constructor(props){
    super(props);
    this.state={meta:null,inputs:null,result:null,mode:'customer',loading:true,error:''};
  }
  componentDidMount(){
    fetch('/api/calculator/meta').then(r=>r.json()).then(meta=>{
      const inputs=Object.assign({}, (meta.baseline&&meta.baseline.inputs)||{});
      inputs.model=this.props.product.model||'Выбранная модель';
      if(this.props.product.manufacturer_price_cny) inputs.purchase_cny=this.props.product.manufacturer_price_cny;
      this.setState({meta:meta,inputs:inputs,loading:false});
    }).catch(()=>this.setState({loading:false,error:'Не удалось загрузить калькулятор'}));
  }
  setValue(k,v){ this.setState({inputs:Object.assign({},this.state.inputs,{[k]:v})}); }
  calc(){
    const body=Object.assign({},this.state.inputs,{mode:this.state.mode});
    Object.keys(body).forEach(k=>{
      if(k!=='model'&&k!=='mode'&&typeof body[k]==='string'&&body[k]!==''&&!isNaN(body[k])) body[k]=Number(body[k]);
    });
    this.setState({loading:true,error:''});
    fetch('/api/quote',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})
      .then(r=>{if(!r.ok) throw new Error(); return r.json();})
      .then(result=>this.setState({result:result,loading:false}))
      .catch(()=>this.setState({loading:false,error:'Ошибка расчёта'}));
  }
  render(){
    const inputs=this.state.inputs, result=this.state.result, mode=this.state.mode;
    const formChildren=[];
    formChildren.push(React.createElement('div',{className:'mode-tabs',key:'tabs'},
      React.createElement('button',{className:mode==='customer'?'active':'',onClick:()=>this.setState({mode:'customer'})},'Покупатель'),
      React.createElement('button',{className:mode==='employee'?'active':'',onClick:()=>this.setState({mode:'employee'})},'Сотрудник')));
    if(inputs){
      if(mode==='employee'){
        formChildren.push(React.createElement(CalcInput,{key:'purchase',label:'Закупочная цена',unit:'CNY',value:inputs.purchase_cny,onChange:v=>this.setValue('purchase_cny',v)}));
        formChildren.push(React.createElement(CalcInput,{key:'bank',label:'Комиссия банка',unit:'CNY',value:inputs.bank_commission_cny,onChange:v=>this.setValue('bank_commission_cny',v)}));
        formChildren.push(React.createElement(CalcInput,{key:'delivery',label:'Доставка',unit:'USD',value:inputs.rail_delivery_usd,onChange:v=>this.setValue('rail_delivery_usd',v)}));
        formChildren.push(React.createElement(CalcInput,{key:'production',label:'Срок производства',unit:'дн.',value:inputs.production_days,onChange:v=>this.setValue('production_days',v)}));
        formChildren.push(React.createElement(CalcInput,{key:'deliverydays',label:'Срок доставки',unit:'дн.',value:inputs.delivery_days,onChange:v=>this.setValue('delivery_days',v)}));
        formChildren.push(React.createElement(CalcInput,{key:'cny',label:'Курс CNY',unit:'₽',value:inputs.cny_rate,onChange:v=>this.setValue('cny_rate',v)}));
        formChildren.push(React.createElement(CalcInput,{key:'credit',label:'Кредитная ставка',unit:'доля',value:inputs.credit_rate,onChange:v=>this.setValue('credit_rate',v)}));
        formChildren.push(React.createElement(CalcInput,{key:'markup',label:'Наценка',unit:'доля',value:inputs.sales_markup,onChange:v=>this.setValue('sales_markup',v)}));
      } else {
        formChildren.push(React.createElement('div',{className:'buyer-calc-note',key:'buyer-note'},
          React.createElement('b',null,'Режим покупателя'),
          React.createElement('span',null,'Закупочная цена, стоимость доставки, срок производства и внутренняя экономика скрыты. Покупателю показывается только итоговая цена по сценариям оплаты.')));
      }
      formChildren.push(React.createElement('button',{key:'go',className:'quote big',onClick:()=>this.calc(),disabled:this.state.loading},this.state.loading?'Считаем…':'Рассчитать 4 сценария'));
    }
    const resultChildren=result?Object.keys(result.prices).map(k=>React.createElement('div',{className:'price-row',key:k},
      React.createElement('span',null,result.prices[k].label),React.createElement('b',null,fmt(result.prices[k].price_cny,'CNY')))):
      [React.createElement('div',{className:'calc-placeholder',key:'placeholder'},'Укажите данные и нажмите «Рассчитать». Формулы перенесены из Excel и проходят эталонную сверку.')];
    return React.createElement('div',{className:'overlay',onMouseDown:e=>{if(e.target===e.currentTarget)this.props.onClose();}},
      React.createElement('div',{className:'modal calc-modal'},
        React.createElement('button',{className:'close',onClick:this.props.onClose},'×'),
        React.createElement('span',{className:'eyebrow'},'Коммерческий калькулятор · Калькулятор-2.xlsx'),
        React.createElement('h2',null,'Расчёт стоимости · ',this.props.product.model),
        this.state.error?React.createElement('div',{className:'error'},this.state.error):null,
        !inputs?React.createElement('div',{className:'loading'},'Загружаем…'):
          React.createElement('div',{className:'calc-layout'},
            React.createElement('div',{className:'calc-form'},formChildren),
            React.createElement('div',{className:'calc-results'},resultChildren))));
  }
}
function CalcInput(props){
  return React.createElement('label',{className:'calc-input'},React.createElement('span',null,props.label),
    React.createElement('div',null,React.createElement('input',{type:'number',step:'any',value:props.value==null?'':props.value,onChange:e=>props.onChange(e.target.value)}),React.createElement('small',null,props.unit)));
}

class App extends Component {
    constructor(p) { super(p); this.state = { meta: null, filters: { ...EMPTY }, items: [], total: 0, exactTotal: 0, clarificationTotal: 0, executionTotal: 0, loading: true, more: false, error: '', sections: { main: true, drive: true, operation: false, ropes: false, electric: false }, compare: [], details: null, quoteProduct: null, compareOpen: false, mobile: false, dirty: false }; this.qTimer = null; }
    componentDidMount() { fetch('/api/meta').then(r => r.json()).then(meta => { this.setState({ meta }, () => this.search()); }).catch(() => this.setState({ error: 'Не удалось загрузить справочники', loading: false })); }
    setF(k, v) { const f = { ...this.state.filters, [k]: v }; if (k === 'winch_type' && String(v).indexOf('Безредукторная') === 0)
        f.speed_count = '1'; if (k === 'groove_shape')
        f.undercut_angle = ''; this.setState({ filters: f, dirty: true }); if (k === 'q') {
        clearTimeout(this.qTimer);
        this.qTimer = setTimeout(() => this.search(), 350);
    } }
    search(append = false) { const off = append ? this.state.items.length : 0; this.setState(append ? { more: true } : { loading: true, error: '' }); fetch('/api/search?' + params(this.state.filters, { limit: 12, offset: off })).then(r => { if (!r.ok)
        throw 0; return r.json(); }).then(d => this.setState({ items: append ? this.state.items.concat(d.items) : d.items, total: d.total, exactTotal: d.exact_total || 0, clarificationTotal: d.clarification_total || 0, executionTotal: d.execution_total || d.total || 0, loading: false, more: false, dirty: false })).catch(() => this.setState({ error: 'Не удалось выполнить подбор', loading: false, more: false })); }
    reset() { this.setState({ filters: { ...EMPTY } }, () => this.search()); }
    toggleCompare(p) { const a = this.state.compare; const found = a.some(x => x.id === p.id); this.setState({ compare: found ? a.filter(x => x.id !== p.id) : (a.length < 4 ? a.concat([p]) : a) }); }
    render() {
        const { meta, filters, items, total, exactTotal, clarificationTotal, executionTotal, loading, sections, compare } = this.state;
        const setSec = k => this.setState({ sections: { ...sections, [k]: !sections[k] } });
        const speedDisabled = String(filters.winch_type).indexOf('Безредукторная') === 0;
        const angles = meta && meta.undercut_angles && meta.undercut_angles[filters.groove_shape] || [];
        const activeCount = Object.values(filters).filter(v => v !== '' && v != null).length;
        return React.createElement("div", null,
            React.createElement("header", null,
                React.createElement("div", { className: "wrap header" },
                    React.createElement("div", { className: "brand" },
                        React.createElement("i", null, "L"),
                        React.createElement("b", null, "LIFTORG"),
                        React.createElement("small", null, "B2B engineering")),
                    React.createElement("nav", null,
                        React.createElement("a", { href: "#catalog" }, "\u041F\u043E\u0434\u0431\u043E\u0440"),
                        React.createElement("a", { href: "#catalog" }, "\u041A\u0430\u0442\u0430\u043B\u043E\u0433"),
                        React.createElement("a", { href: "#workflow" }, "\u041A\u0430\u043A \u0440\u0430\u0431\u043E\u0442\u0430\u0435\u0442"),
                        React.createElement("a", { href: "/admin", className: "admin-link" }, "Управление")),
                    React.createElement("a", { className: "outline", href: "#catalog" }, "\u041D\u0430\u0447\u0430\u0442\u044C \u043F\u043E\u0434\u0431\u043E\u0440 \u2192"))),
            React.createElement("section", { className: "hero" },
                React.createElement("div", { className: "wrap hero-grid" },
                    React.createElement("div", null,
                        React.createElement("span", { className: "eyebrow orange" }, "\u041F\u0440\u043E\u0444\u0435\u0441\u0441\u0438\u043E\u043D\u0430\u043B\u044C\u043D\u044B\u0439 \u043A\u0430\u0442\u0430\u043B\u043E\u0433"),
                        React.createElement("h1", null,
                            "\u0418\u043D\u0436\u0435\u043D\u0435\u0440\u043D\u044B\u0439 \u043F\u043E\u0434\u0431\u043E\u0440",
                            React.createElement("br", null),
                            React.createElement("em", null, "\u043B\u0438\u0444\u0442\u043E\u0432\u044B\u0445 \u043B\u0435\u0431\u0451\u0434\u043E\u043A")),
                        React.createElement("p", null, "\u0424\u0438\u043B\u044C\u0442\u0440\u0443\u0439\u0442\u0435 838 \u0438\u0441\u043F\u043E\u043B\u043D\u0435\u043D\u0438\u0439 \u043F\u043E \u0442\u0435\u0445\u043D\u0438\u0447\u0435\u0441\u043A\u0438\u043C \u043F\u0430\u0440\u0430\u043C\u0435\u0442\u0440\u0430\u043C, \u0441\u0440\u0430\u0432\u043D\u0438\u0432\u0430\u0439\u0442\u0435 2\u20134 \u043C\u043E\u0434\u0435\u043B\u0438 \u0438 \u0444\u043E\u0440\u043C\u0438\u0440\u0443\u0439\u0442\u0435 \u0437\u0430\u043F\u0440\u043E\u0441 \u043F\u0440\u043E\u0438\u0437\u0432\u043E\u0434\u0438\u0442\u0435\u043B\u044E."),
                        React.createElement("div", { className: "hero-actions" },
                            React.createElement("a", { className: "quote big", href: "#catalog" }, "\u041F\u043E\u0434\u043E\u0431\u0440\u0430\u0442\u044C \u043B\u0435\u0431\u0451\u0434\u043A\u0443 \u2192"),
                            React.createElement("b", null,
                                "838 ",
                                React.createElement("small", null, "\u0438\u0441\u043F\u043E\u043B\u043D\u0435\u043D\u0438\u0439 \u0432 \u0431\u0430\u0437\u0435")))),
                    React.createElement("div", { className: "hero-cards" },
                        React.createElement("div", { className: "floating back" },
                            React.createElement("small", null, "\u041A\u0430\u0442\u0430\u043B\u043E\u0433"),
                            React.createElement("b", null, "Nidec \u00B7 Sicor \u00B7 Torindrive")),
                        React.createElement("div", { className: "floating front" },
                            React.createElement("small", null, "\u0421\u0446\u0435\u043D\u0430\u0440\u0438\u0439 \u0438\u043D\u0436\u0435\u043D\u0435\u0440\u0430"),
                            React.createElement("b", null, "\u041F\u0430\u0440\u0430\u043C\u0435\u0442\u0440\u044B \u2192 \u043C\u043E\u0434\u0435\u043B\u044C \u2192 \u0437\u0430\u043F\u0440\u043E\u0441 \u2192 \u0446\u0435\u043D\u0430"),
                            React.createElement("div", null,
                                React.createElement("span", null, "1000 \u043A\u0433"),
                                React.createElement("span", null, "1,0\u20131,6 \u043C/\u0441"),
                                React.createElement("span", null, "2:1"),
                                React.createElement("span", null, "\u041A\u0412\u0428 400")))))),
            React.createElement("section", { id: "workflow", className: "workflow" },
                React.createElement("div", { className: "wrap" }, [['01', 'Параметры', 'Укажите требования'], ['02', 'Модель', 'Выберите вариант'], ['03', 'Запрос цены', 'Опросный лист'], ['04', 'Стоимость', 'Расчёт условий']].map((x, i) => React.createElement("div", { key: x[0], className: "workflow-fragment" },
                    React.createElement("div", { className: 'step ' + (i === 0 ? 'active' : '') },
                        React.createElement("i", null, x[0]),
                        React.createElement("span", null,
                            React.createElement("b", null, x[1]),
                            React.createElement("small", null, x[2]))),
                    i < 3 && React.createElement("hr", null))))),
            React.createElement("section", { id: "catalog", className: "catalog" },
                React.createElement("div", { className: "wrap grid" },
                    React.createElement("aside", { className: this.state.mobile ? 'filters show' : 'filters' },
                        React.createElement("div", { className: "filter-title" },
                            React.createElement("span", null,
                                React.createElement("small", { className: "eyebrow orange" }, "\u041F\u0430\u0440\u0430\u043C\u0435\u0442\u0440\u044B \u043F\u0440\u043E\u0435\u043A\u0442\u0430"),
                                React.createElement("h2", null, "\u0424\u0438\u043B\u044C\u0442\u0440\u044B")),
                            React.createElement("button", { onClick: () => this.reset() }, "\u21BB"),
                            React.createElement("button", { className: "mob-x", onClick: () => this.setState({ mobile: false }) }, "\u00D7")),
                        React.createElement("label", { className: "search" },
                            "\u2315",
                            React.createElement("input", { value: filters.q, onChange: e => this.setF('q', e.target.value), placeholder: "\u041C\u043E\u0434\u0435\u043B\u044C \u0438\u043B\u0438 ID" })),
                        React.createElement(Section, { id: "01", title: "\u041E\u0441\u043D\u043E\u0432\u043D\u043E\u0435", subtitle: "\u0422\u0438\u043F, \u043F\u0440\u043E\u0438\u0437\u0432\u043E\u0434\u0438\u0442\u0435\u043B\u044C, \u043F\u0440\u043E\u0435\u043A\u0442", open: sections.main, onToggle: () => setSec('main') },
                            React.createElement("div", { className: "fields" },
                                React.createElement(Field, { label: "\u041F\u0440\u043E\u0438\u0437\u0432\u043E\u0434\u0438\u0442\u0435\u043B\u044C", value: filters.manufacturer, onChange: v => this.setF('manufacturer', v) },
                                    React.createElement("option", { value: "" }, "\u041B\u044E\u0431\u043E\u0439"),
                                    meta && meta.manufacturers.map(x => React.createElement("option", { key: x }, x))),
                                React.createElement(Field, { label: "\u0422\u0438\u043F \u043B\u0435\u0431\u0451\u0434\u043A\u0438", value: filters.winch_type, onChange: v => this.setF('winch_type', v) },
                                    React.createElement("option", { value: "" }, "\u041B\u044E\u0431\u043E\u0439 \u0442\u0438\u043F"),
                                    meta && meta.winch_types.map(x => React.createElement("option", { key: x }, x))),
                                React.createElement(Field, { label: "\u0413\u0440\u0443\u0437\u043E\u043F\u043E\u0434\u044A\u0451\u043C\u043D\u043E\u0441\u0442\u044C", value: filters.capacity_kg, onChange: v => this.setF('capacity_kg', v) },
                                    React.createElement("option", { value: "" }, "\u041B\u044E\u0431\u0430\u044F"),
                                    meta && meta.capacities.map(x => React.createElement("option", { key: x, value: x }, fmt(x, 'кг')))),
                                React.createElement(Field, { label: "\u0421\u043A\u043E\u0440\u043E\u0441\u0442\u044C", value: filters.speed_range, onChange: v => this.setF('speed_range', v) },
                                    React.createElement("option", { value: "" }, "\u041B\u044E\u0431\u043E\u0439 \u0434\u0438\u0430\u043F\u0430\u0437\u043E\u043D"),
                                    meta && meta.speed_ranges.map(x => React.createElement("option", { key: x.label, value: x.min + '|' + x.max }, x.label))))),
                        React.createElement(Section, { id: "02", title: "\u041F\u0440\u0438\u0432\u043E\u0434", subtitle: "\u041F\u043E\u0434\u0432\u0435\u0441, \u043C\u043E\u0449\u043D\u043E\u0441\u0442\u044C, \u0427\u041F, \u044D\u043D\u043A\u043E\u0434\u0435\u0440", open: sections.drive, onToggle: () => setSec('drive') },
                            React.createElement("div", { className: "fields" },
                                React.createElement(Field, { label: "\u041A\u0440\u0430\u0442\u043D\u043E\u0441\u0442\u044C \u043F\u043E\u0434\u0432\u0435\u0441\u043A\u0438", value: filters.suspension, onChange: v => this.setF('suspension', v) },
                                    React.createElement("option", { value: "" }, "\u041B\u044E\u0431\u0430\u044F"),
                                    meta && meta.suspensions.map(x => React.createElement("option", { key: x }, x))),
                                React.createElement(Field, { label: "\u041C\u043E\u0449\u043D\u043E\u0441\u0442\u044C", value: filters.power_range, onChange: v => this.setF('power_range', v) },
                                    React.createElement("option", { value: "" }, "\u041B\u044E\u0431\u043E\u0439 \u0434\u0438\u0430\u043F\u0430\u0437\u043E\u043D"),
                                    meta && meta.power_ranges.map(x => React.createElement("option", { key: x.label, value: x.min + '|' + x.max }, x.label))),
                                React.createElement(Field, { label: "\u041A\u043E\u043B\u0438\u0447\u0435\u0441\u0442\u0432\u043E \u0441\u043A\u043E\u0440\u043E\u0441\u0442\u0435\u0439", value: filters.speed_count, disabled: speedDisabled, onChange: v => this.setF('speed_count', v) },
                                    React.createElement("option", { value: "" }, "1 \u0438\u043B\u0438 2"),
                                    React.createElement("option", { value: "1" }, "1 \u0441\u043A\u043E\u0440\u043E\u0441\u0442\u044C"),
                                    React.createElement("option", { value: "2" }, "2 \u0441\u043A\u043E\u0440\u043E\u0441\u0442\u0438")),
                                React.createElement(Field, { label: "\u041D\u0430\u043B\u0438\u0447\u0438\u0435 \u0427\u041F", value: filters.vfd, onChange: v => this.setF('vfd', v) },
                                    React.createElement("option", { value: "" }, "\u041D\u0435\u0432\u0430\u0436\u043D\u043E"),
                                    meta && meta.vfd_options.map(x => React.createElement("option", { key: x }, x))),
                                React.createElement(Field, { label: "\u042D\u043D\u043A\u043E\u0434\u0435\u0440", value: filters.encoder_type, onChange: v => this.setF('encoder_type', v) },
                                    React.createElement("option", { value: "" }, "\u041D\u0435\u0432\u0430\u0436\u043D\u043E"),
                                    meta && meta.encoder_types.map(x => React.createElement("option", { key: x }, x))))),
                        React.createElement(Section, { id: "03", title: "\u042D\u043A\u0441\u043F\u043B\u0443\u0430\u0442\u0430\u0446\u0438\u044F", subtitle: "\u041D\u0430\u0433\u0440\u0443\u0437\u043A\u0430, \u0432\u044B\u0441\u043E\u0442\u0430, \u0440\u0430\u0437\u043C\u0435\u0449\u0435\u043D\u0438\u0435", open: sections.operation, onToggle: () => setSec('operation') },
                            React.createElement("div", { className: "fields" },
                                React.createElement(Field, { label: "\u041A\u043E\u043D\u0441\u043E\u043B\u044C\u043D\u0430\u044F \u043D\u0430\u0433\u0440\u0443\u0437\u043A\u0430", value: filters.cantilever_required_kg, onChange: v => this.setF('cantilever_required_kg', v) },
                                    React.createElement("option", { value: "" }, "\u041D\u0435\u0432\u0430\u0436\u043D\u043E"),
                                    meta && meta.cantilever_limits.map(x => React.createElement("option", { key: x.value, value: x.value }, x.label))),
                                React.createElement(Field, { label: "\u0412\u044B\u0441\u043E\u0442\u0430 \u043F\u043E\u0434\u044A\u0451\u043C\u0430", value: filters.lift_height_required_m, onChange: v => this.setF('lift_height_required_m', v) },
                                    React.createElement("option", { value: "" }, "\u041D\u0435\u0432\u0430\u0436\u043D\u043E"),
                                    meta && meta.lift_height_limits.map(x => React.createElement("option", { key: x.value, value: x.value }, x.label))),
                                React.createElement(Field, { label: "\u0422\u0438\u043F \u0440\u0430\u0437\u043C\u0435\u0449\u0435\u043D\u0438\u044F", value: filters.placement_type, onChange: v => this.setF('placement_type', v) },
                                    React.createElement("option", { value: "" }, "\u041D\u0435\u0432\u0430\u0436\u043D\u043E"),
                                    meta && meta.placement_types.map(x => React.createElement("option", { key: x }, x))))),
                        React.createElement(Section, { id: "04", title: "\u041A\u0412\u0428 \u0438 \u043A\u0430\u043D\u0430\u0442\u044B", subtitle: "\u0413\u0435\u043E\u043C\u0435\u0442\u0440\u0438\u044F \u0438 \u043A\u0430\u043D\u0430\u0442\u044B", open: sections.ropes, onToggle: () => setSec('ropes') },
                            React.createElement("div", { className: "fields" },
                                React.createElement(Field, { label: "\u0424\u043E\u0440\u043C\u0430 \u0440\u0443\u0447\u044C\u044F", value: filters.groove_shape, onChange: v => this.setF('groove_shape', v) },
                                    React.createElement("option", { value: "" }, "\u041B\u044E\u0431\u0430\u044F"),
                                    meta && meta.groove_shapes.map(x => React.createElement("option", { key: x }, x))),
                                React.createElement(Field, { label: "\u0423\u0433\u043E\u043B \u043F\u043E\u0434\u0440\u0435\u0437\u0430", value: filters.undercut_angle, disabled: !filters.groove_shape, onChange: v => this.setF('undercut_angle', v) },
                                    React.createElement("option", { value: "" }, "\u041B\u044E\u0431\u043E\u0439"),
                                    angles.map(x => React.createElement("option", { key: x, value: x },
                                        x,
                                        "\u00B0"))),
                                React.createElement(Field, { label: "\u0414\u0438\u0430\u043C\u0435\u0442\u0440 \u041A\u0412\u0428", value: filters.sheave_diameter_mm, onChange: v => this.setF('sheave_diameter_mm', v) },
                                    React.createElement("option", { value: "" }, "\u041B\u044E\u0431\u043E\u0439"),
                                    meta && meta.sheave_diameters.map(x => React.createElement("option", { key: x, value: x }, fmt(x, 'мм')))),
                                React.createElement(Field, { label: "\u041A\u043E\u043B\u0438\u0447\u0435\u0441\u0442\u0432\u043E \u043A\u0430\u043D\u0430\u0442\u043E\u0432", value: filters.rope_count, onChange: v => this.setF('rope_count', v) },
                                    React.createElement("option", { value: "" }, "\u041B\u044E\u0431\u043E\u0435"),
                                    meta && meta.rope_counts.map(x => React.createElement("option", { key: x, value: x }, x))),
                                React.createElement(Field, { label: "\u0414\u0438\u0430\u043C\u0435\u0442\u0440 \u043A\u0430\u043D\u0430\u0442\u0430", value: filters.rope_diameter_mm, onChange: v => this.setF('rope_diameter_mm', v) },
                                    React.createElement("option", { value: "" }, "\u041B\u044E\u0431\u043E\u0439"),
                                    meta && meta.rope_diameters.map(x => React.createElement("option", { key: x, value: x }, fmt(x, 'мм')))))),
                        React.createElement(Section, { id: "05", title: "\u042D\u043B\u0435\u043A\u0442\u0440\u0438\u043A\u0430 \u0438 \u043F\u0440\u043E\u0447\u0435\u0435", subtitle: "\u0422\u043E\u0440\u043C\u043E\u0437, \u0432\u043A\u043B\u044E\u0447\u0435\u043D\u0438\u044F, \u043C\u0430\u0441\u0441\u0430", open: sections.electric, onToggle: () => setSec('electric') },
                            React.createElement("div", { className: "fields" },
                                React.createElement(Field, { label: "\u0412\u043A\u043B\u044E\u0447\u0435\u043D\u0438\u0439/\u0447\u0430\u0441", value: filters.starts_per_hour, onChange: v => this.setF('starts_per_hour', v) },
                                    React.createElement("option", { value: "" }, "\u041B\u044E\u0431\u043E\u0435"),
                                    meta && meta.starts_per_hour.map(x => React.createElement("option", { key: x, value: x }, x))),
                                React.createElement(Field, { label: "\u041F\u0438\u0442\u0430\u043D\u0438\u0435 \u0442\u043E\u0440\u043C\u043E\u0437\u0430", value: filters.brake_voltage, onChange: v => this.setF('brake_voltage', v) },
                                    React.createElement("option", { value: "" }, "\u041B\u044E\u0431\u043E\u0435"),
                                    meta && meta.brake_voltages.map(x => React.createElement("option", { key: x }, x))),
                                React.createElement(Field, { label: "\u041C\u0430\u0441\u0441\u0430", value: filters.weight_kg, onChange: v => this.setF('weight_kg', v) },
                                    React.createElement("option", { value: "" }, "\u041B\u044E\u0431\u0430\u044F"),
                                    meta && meta.weights.map(x => React.createElement("option", { key: x, value: x }, fmt(x, 'кг')))))),
                        React.createElement("div", { className: "filter-actions" },
                            React.createElement("button", { className: "apply " + (this.state.dirty ? "dirty" : ""), onClick: () => { this.search(); this.setState({ mobile: false }); } },
                                this.state.dirty ? "Применить параметры" : "Параметры применены",
                                activeCount ? React.createElement("b", null, activeCount) : null,
                                " →"),
                            activeCount ? React.createElement("button", { className: "reset-all", onClick: () => this.reset() }, "Сбросить все параметры") : null)),
                    React.createElement("div", { className: "results" },
                        React.createElement("div", { className: "result-head" },
                            React.createElement("div", null,
                                React.createElement("span", { className: "eyebrow orange" }, "\u041F\u043E\u0434\u0445\u043E\u0434\u044F\u0449\u0438\u0435 \u043C\u043E\u0434\u0435\u043B\u0438"),
                                React.createElement("h2", null, "\u0420\u0435\u0437\u0443\u043B\u044C\u0442\u0430\u0442\u044B \u043F\u043E\u0434\u0431\u043E\u0440\u0430"),
                                React.createElement("p", { className: "result-subtitle" }, "Сначала — полностью подтверждённые модели. Затем — кандидаты, где в исходных данных требуется уточнение.")),
                            React.createElement("div", null,
                                React.createElement("button", { className: "mobile-filter", onClick: () => this.setState({ mobile: true }) }, "\u2630 \u0424\u0438\u043B\u044C\u0442\u0440\u044B"),
                                React.createElement("span", { className: "count" },
                                    "Моделей: ", React.createElement("b", null, total), " · Точно ", React.createElement("b", null, exactTotal), " · Уточнить ", React.createElement("b", null, clarificationTotal), " · Исполнений: ", React.createElement("b", null, executionTotal)))),
                        React.createElement("div", { className: "note" }, "ⓘ Логика подбора: известное несовпадение исключает модель. Если параметр в исходном файле не заполнен, модель остаётся кандидатом и помечается «Требует уточнения»."),
                        this.state.error && React.createElement("div", { className: "error" }, this.state.error),
                        loading ? React.createElement("div", { className: "skeletons" }, [1, 2, 3, 4].map(x => React.createElement("i", { key: x }))) : items.length ? React.createElement("div", { className: "products" }, items.map(p => React.createElement(ProductCard, { key: p.id, p: p, filters: filters, selected: compare.some(x => x.id === p.id), onCompare: p => this.toggleCompare(p), onDetails: id => this.setState({ details: id }), onQuote: p => this.setState({ quoteProduct: p }) }))) : React.createElement("div", { className: "empty" },
                            React.createElement("b", null, "\u041F\u043E\u0434\u0445\u043E\u0434\u044F\u0449\u0438\u0445 \u043C\u043E\u0434\u0435\u043B\u0435\u0439 \u043D\u0435 \u043D\u0430\u0439\u0434\u0435\u043D\u043E"),
                            React.createElement("span", null, "\u0418\u0437\u043C\u0435\u043D\u0438\u0442\u0435 \u043F\u0430\u0440\u0430\u043C\u0435\u0442\u0440\u044B \u0438\u043B\u0438 \u0441\u0431\u0440\u043E\u0441\u044C\u0442\u0435 \u0444\u0438\u043B\u044C\u0442\u0440\u044B.")),
                        items.length < total && !loading && React.createElement("div", { className: "more" },
                            React.createElement("button", { disabled: this.state.more, onClick: () => this.search(true) }, this.state.more ? 'Загрузка…' : 'Показать ещё ↓'),
                            React.createElement("small", null,
                                "\u041F\u043E\u043A\u0430\u0437\u0430\u043D\u043E ",
                                items.length,
                                " \u0438\u0437 ",
                                total))))),
            compare.length > 0 && React.createElement("div", { className: "compare-dock" },
                React.createElement("div", null, compare.map(p => React.createElement("span", { key: p.id },
                    React.createElement("small", null, p.manufacturer),
                    React.createElement("b", null, p.model),
                    React.createElement("button", { onClick: () => this.toggleCompare(p) }, "\u00D7")))),
                React.createElement("aside", null,
                    React.createElement("small", null,
                        compare.length,
                        " \u0438\u0437 4"),
                    React.createElement("button", { disabled: compare.length < 2, onClick: () => this.setState({ compareOpen: true }) }, "\u21C4 \u0421\u0440\u0430\u0432\u043D\u0438\u0442\u044C"))),
            this.state.details && React.createElement(DetailsModal, { id: this.state.details, filters: filters, isCompared: id => compare.some(x => x.id === id), onClose: () => this.setState({ details: null }), onCompare: p => this.toggleCompare(p), onQuote: p => this.setState({ quoteProduct: p, details: null }) }),
            " ",
            this.state.compareOpen && React.createElement(CompareModal, { items: compare, onClose: () => this.setState({ compareOpen: false }), onRemove: id => this.setState({ compare: compare.filter(x => x.id !== id) }) }),
            this.state.quoteProduct && React.createElement(QuoteModal, { product: this.state.quoteProduct, onClose: () => this.setState({ quoteProduct: null }) }),
            React.createElement("footer", null,
                React.createElement("div", { className: "wrap" },
                    React.createElement("b", null, "LIFTORG B2B"),
                    React.createElement("span", null, "React engineering platform 4.2 \u00B7 \u0438\u0441\u0442\u043E\u0447\u043D\u0438\u043A \u0434\u0430\u043D\u043D\u044B\u0445: \u0430\u043A\u0442\u0443\u0430\u043B\u044C\u043D\u044B\u0435 \u0444\u0430\u0439\u043B\u044B \u0437\u0430\u043A\u0430\u0437\u0447\u0438\u043A\u0430"),
                    React.createElement("a", { href: "/legacy" }, "\u0420\u0435\u0437\u0435\u0440\u0432\u043D\u0430\u044F \u0441\u0435\u0440\u0432\u0435\u0440\u043D\u0430\u044F \u0432\u0435\u0440\u0441\u0438\u044F"))));
    }
}
(function(){var root=document.getElementById('root');try{if(!window.React||!window.ReactDOM)throw new Error('React runtime не загружен');ReactDOM.render(React.createElement(AppErrorBoundary,null,React.createElement(App,null)),root);}catch(err){console.error('LIFTORG_REACT_BOOT_ERROR',err);if(root)root.innerHTML='<div style="max-width:900px;margin:60px auto;padding:24px;font:16px Arial;border:1px solid #e5e7eb;border-radius:16px"><h2>Интерфейс не запустился</h2><pre style="white-space:pre-wrap;background:#f7f8fa;padding:12px;border-radius:10px">'+String(err&&(err.stack||err.message)||err)+'</pre><p><a href="/legacy">Открыть резервный интерфейс</a></p></div>';}})();
