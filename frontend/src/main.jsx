import React, { useEffect, useMemo, useRef, useState } from 'react'
import { createRoot } from 'react-dom/client'
import {
  Search, SlidersHorizontal, ChevronDown, ChevronUp, Scale, X, ArrowRight,
  RotateCcw, Layers3, FileText, Calculator, CheckCircle2, Menu, Image as ImageIcon,
  Loader2, ExternalLink, GitCompareArrows, Info, Gauge, Zap, Ruler, Weight,
  Cable, Settings2, Building2, ChevronRight, Check, AlertTriangle
} from 'lucide-react'
import './styles.css'

const initialFilters = {
  q:'', manufacturer:'', winch_type:'', capacity_kg:'', speed_range:'', suspension:'',
  speed_count:'', vfd:'', encoder_type:'', power_range:'', cantilever_required_kg:'',
  lift_height_required_m:'', groove_shape:'', undercut_angle:'', sheave_diameter_mm:'',
  rope_count:'', rope_diameter_mm:'', starts_per_hour:'', brake_voltage:'', weight_kg:'',
  placement_type:'', frame_supply:'', remote_release:''
}

const filterLabels = {
  q:'Поиск', manufacturer:'Производитель', winch_type:'Тип', capacity_kg:'Грузоподъёмность',
  speed_range:'Скорость', suspension:'Подвес', speed_count:'Скоростей', vfd:'ЧП', encoder_type:'Энкодер',
  power_range:'Мощность', cantilever_required_kg:'Консольная нагрузка', lift_height_required_m:'Высота',
  groove_shape:'Форма ручья', undercut_angle:'Угол подреза', sheave_diameter_mm:'КВШ', rope_count:'Канатов',
  rope_diameter_mm:'Диаметр каната', starts_per_hour:'Включений/час', brake_voltage:'Тормоз', weight_kg:'Масса',
  placement_type:'Размещение', frame_supply:'Рама', remote_release:'Расцепление'
}

function prettyFilterValue(k,v,meta){
  if(k==='speed_range'||k==='power_range'){ const [a,b]=String(v).split('|'); const unit=k==='speed_range'?'м/с':'кВт'; return `${String(a).replace('.',',')}–${String(b).replace('.',',')} ${unit}` }
  if(k==='capacity_kg'||k==='weight_kg'||k==='cantilever_required_kg') return `${String(v).replace('.',',')} кг`
  if(k==='lift_height_required_m') return `${v} м`
  if(k==='sheave_diameter_mm'||k==='rope_diameter_mm') return `${String(v).replace('.',',')} мм`
  if(k==='undercut_angle') return `${v}°`
  return String(v)
}

const fmt = (v, unit='') => (v===null || v===undefined || v==='') ? '—' : `${String(v).replace('.', ',')}${unit ? ' '+unit : ''}`
const arrayFmt = (v) => Array.isArray(v) && v.length ? v.join(', ') : '—'

function qsFromFilters(f, extra={}) {
  const p = new URLSearchParams()
  Object.entries(f).forEach(([k,v]) => {
    if (v === '' || v === null || v === undefined) return
    if (k === 'speed_range') {
      const [a,b] = String(v).split('|'); if(a) p.set('speed_min',a); if(b) p.set('speed_max',b); return
    }
    if (k === 'power_range') {
      const [a,b] = String(v).split('|'); if(a) p.set('power_min',a); if(b) p.set('power_max',b); return
    }
    p.set(k, v)
  })
  Object.entries(extra).forEach(([k,v]) => p.set(k,v))
  return p
}

function useDebounced(value, delay=350) {
  const [d,setD] = useState(value)
  useEffect(()=>{ const t=setTimeout(()=>setD(value),delay); return()=>clearTimeout(t)},[value,delay])
  return d
}

function LiftPlaceholder({type}) {
  return <div className="machine-visual" aria-label="Изображение лебёдки пока не привязано">
    <div className="machine-wheel"/><div className="machine-body"><div className="machine-ribs"/></div><div className="machine-shaft"/>
    <div className="visual-label"><ImageIcon size={14}/> Фото модели</div>
  </div>
}

function SelectField({label,value,onChange,children,disabled=false,hint}) {
  return <label className={`field ${disabled?'disabled':''}`}>
    <span>{label}</span>
    <select value={value} disabled={disabled} onChange={e=>onChange(e.target.value)}>{children}</select>
    {hint && <small>{hint}</small>}
  </label>
}

function FilterSection({title,subtitle,icon:Icon,open,setOpen,children,badge}) {
  return <section className={`filter-section ${open?'is-open':''}`}>
    <button className="filter-section-head" onClick={()=>setOpen(!open)} type="button">
      <div className="filter-icon"><Icon size={17}/></div>
      <div className="filter-head-copy"><strong>{title}</strong><small>{subtitle}</small></div>
      {badge ? <span className="section-badge">{badge}</span> : null}
      {open ? <ChevronUp size={17}/> : <ChevronDown size={17}/>} 
    </button>
    <div className="filter-section-body">{children}</div>
  </section>
}

function ProductCard({p, selected, onCompare, onDetails, filters}) {
  const rope = `${arrayFmt(p.rope_counts)} × ${arrayFmt((p.rope_diameters_mm||[]).map(x=>String(x).replace('.',',')))} мм`
  const needs = p.match_status === 'needs_clarification'
  const unknown = p.match_summary?.unknown || 0
  return <article className={`product-card enter-card ${needs?'needs-clarification':''}`}>
    <div className="product-media"><LiftPlaceholder type={p.winch_type}/><span className={`status-chip ${needs?'warning':''}`}>{needs?<AlertTriangle size={14}/>:<CheckCircle2 size={14}/>} {needs?'Требует уточнения':'Подходит'}</span></div>
    <div className="product-content">
      <div className="product-head"><div><div className="eyebrow">{p.manufacturer}</div><h3>{p.model}</h3><p>{p.winch_type || 'Тип уточняется'}</p></div></div>
      <div className="quick-specs">
        <div><span>Г/п</span><b>{fmt(p.capacity_kg,'кг')}</b></div>
        <div><span>Скорость</span><b>{fmt(p.speed_m_s,'м/с')}</b></div>
        <div><span>Мощность</span><b>{fmt(p.power_kw,'кВт')}</b></div>
        <div><span>Подвес</span><b>{arrayFmt(p.suspensions)}</b></div>
        <div><span>КВШ</span><b>{fmt(p.sheave_diameter_mm,'мм')}</b></div>
        <div><span>Канаты</span><b>{rope}</b></div>
      </div>
      <div className="engineering-strip">
        <span><Gauge size={14}/>{fmt(p.max_cantilever_load_kg,'кг')}</span>
        <span><Weight size={14}/>{fmt(p.weight_kg,'кг')}</span>
        <span><Ruler size={14}/>{fmt(p.undercut_angle_normalized,'°')}</span>
      </div>
      {needs && <div className="clarification-hint"><Info size={15}/><span>По выбранным параметрам подходит, но {unknown} {unknown===1?'поле требует':'поля требуют'} уточнения{p.clarifications?.length?`: ${p.clarifications.slice(0,2).join(', ')}${p.clarifications.length>2?'…':''}`:''}</span></div>}
      <div className="product-actions">
        <button className={`compare-toggle ${selected?'selected':''}`} type="button" onClick={()=>onCompare(p)}><GitCompareArrows size={17}/>{selected?'В сравнении':'Сравнить'}</button>
        <button className="secondary-btn" onClick={()=>onDetails(p.id)} type="button">Подробнее</button>
        <a className="primary-btn" href={`/product/${p.id}/inquiry?${qsFromFilters(filters).toString()}`}>Запросить цену <ArrowRight size={17}/></a>
      </div>
    </div>
  </article>
}

function DetailsModal({id,onClose,filters,onAddCompare,isCompared}) {
  const [p,setP]=useState(null); const [error,setError]=useState('')
  useEffect(()=>{let alive=true; fetch(`/api/products/${id}`).then(r=>r.json()).then(d=>alive&&setP(d)).catch(()=>alive&&setError('Не удалось загрузить карточку')); return()=>{alive=false}},[id])
  const sections = useMemo(()=>{
    if(!p) return []
    return [
      ['Основные', [['Производитель',p.manufacturer],['Модель',p.model],['Тип',p.winch_type],['Грузоподъёмность',fmt(p.capacity_kg,'кг')],['Скорость',fmt(p.speed_m_s,'м/с')],['Подвес',arrayFmt(p.suspensions)]]],
      ['Привод', [['Мощность',fmt(p.power_kw,'кВт')],['Ток',fmt(p.nominal_current_a,'A')],['Обороты',fmt(p.nominal_rpm,'об/мин')],['Частота',fmt(p.frequency_hz,'Гц')],['Крутящий момент',fmt(p.torque_nm,'Н·м')],['Количество скоростей',p.speed_count]]],
      ['КВШ и канаты', [['Диаметр КВШ',fmt(p.sheave_diameter_mm,'мм')],['Форма ручья',p.groove_shape],['Угол подреза',p.undercut_angle],['Кол-во канатов',arrayFmt(p.rope_counts)],['Диаметр канатов',arrayFmt(p.rope_diameters_mm)],['Шаг канавок',fmt(p.sheave_groove_pitch_mm,'мм')]]],
      ['Монтаж и эксплуатация', [['Консольная нагрузка',fmt(p.max_cantilever_load_kg,'кг')],['Высота подъёма',fmt(p.max_lift_height_m,'м')],['Включений/час',p.starts_per_hour],['Масса',fmt(p.weight_kg,'кг')],['Рама',String(p.frame_supply ?? '—')],['Размещение',p.placement_type_normalized||'—']]],
    ]
  },[p])
  return <div className="modal-backdrop" onMouseDown={e=>{if(e.target===e.currentTarget)onClose()}}>
    <div className="details-modal animate-pop">
      <button className="modal-close" onClick={onClose}><X/></button>
      {!p && !error && <div className="modal-loader"><Loader2 className="spin"/> Загружаем технический паспорт…</div>}
      {error && <div className="error-box">{error}</div>}
      {p && <>
        <div className="detail-hero"><LiftPlaceholder/><div><div className="eyebrow">{p.manufacturer}</div><h2>{p.model}</h2><p>{p.winch_type}</p><div className="detail-badges"><span>{fmt(p.capacity_kg,'кг')}</span><span>{fmt(p.speed_m_s,'м/с')}</span><span>{fmt(p.power_kw,'кВт')}</span></div></div></div>
        <div className="detail-sections">{sections.map(([title,rows])=><section key={title}><h4>{title}</h4><div className="detail-table">{rows.map(([k,v])=><div key={k}><span>{k}</span><b>{v??'—'}</b></div>)}</div></section>)}</div>
        <div className="modal-actions"><button className={`compare-toggle ${isCompared?'selected':''}`} onClick={()=>onAddCompare(p)}><GitCompareArrows size={17}/>{isCompared?'В сравнении':'Добавить к сравнению'}</button><a className="primary-btn" href={`/product/${p.id}/inquiry?${qsFromFilters(filters).toString()}`}>Запросить цену <ArrowRight size={17}/></a></div>
      </>}
    </div>
  </div>
}

function CompareModal({items,onClose,onRemove}) {
  const [data,setData]=useState(null)
  useEffect(()=>{fetch('/api/compare',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ids:items.map(x=>x.id)})}).then(r=>r.json()).then(setData)},[items])
  return <div className="modal-backdrop"><div className="compare-modal animate-pop"><button className="modal-close" onClick={onClose}><X/></button><div className="compare-title"><div><div className="eyebrow">Инженерное сравнение</div><h2>Сравнение {items.length} моделей</h2></div><span>до 4 моделей</span></div>
    {!data ? <div className="modal-loader"><Loader2 className="spin"/> Формируем сравнение…</div> : <div className="compare-scroll"><table><thead><tr><th>Параметр</th>{data.items.map(p=><th key={p.id}><LiftPlaceholder/><b>{p.manufacturer}</b><strong>{p.model}</strong><button className="mini-remove" onClick={()=>onRemove(p.id)}><X size={14}/></button></th>)}</tr></thead><tbody>{data.fields.map(f=><tr key={f.key}><td>{f.label}</td>{data.items.map(p=><td key={p.id}>{fmt(p[f.key],f.unit)}</td>)}</tr>)}</tbody></table></div>}
  </div></div>
}

function App(){
  const [meta,setMeta]=useState(null), [filters,setFilters]=useState(initialFilters), [items,setItems]=useState([]), [total,setTotal]=useState(0)
  const [loading,setLoading]=useState(true), [loadingMore,setLoadingMore]=useState(false), [error,setError]=useState('')
  const [matchStats,setMatchStats]=useState({exact:0,clarify:0,excluded:0})
  const [compare,setCompare]=useState([]), [compareOpen,setCompareOpen]=useState(false), [detailsId,setDetailsId]=useState(null), [mobileFilters,setMobileFilters]=useState(false)
  const [openSections,setOpenSections]=useState({main:true,drive:true,operation:false,ropes:false,electric:false})
  const debouncedQ=useDebounced(filters.q)
  const firstRun=useRef(true)

  useEffect(()=>{fetch('/api/meta').then(r=>r.json()).then(setMeta).catch(()=>setError('Не удалось загрузить справочники'))},[])
  const doSearch=async({append=false}={})=>{
    setError(''); append?setLoadingMore(true):setLoading(true)
    try { const offset=append?items.length:0; const p=qsFromFilters({...filters,q:debouncedQ},{limit:12,offset}); const r=await fetch(`/api/search?${p}`); if(!r.ok) throw new Error(); const d=await r.json(); setItems(prev=>append?[...prev,...d.items]:d.items); setTotal(d.total); setMatchStats({exact:d.exact_total||0,clarify:d.clarification_total||0,excluded:d.excluded_total||0}) }
    catch {setError('Не удалось выполнить подбор. Попробуйте ещё раз.')}
    finally {setLoading(false);setLoadingMore(false)}
  }
  useEffect(()=>{if(meta){doSearch();firstRun.current=false}},[meta])
  useEffect(()=>{if(!firstRun.current && meta) doSearch()},[debouncedQ])

  const setF=(k,v)=>setFilters(prev=>{const n={...prev,[k]:v}; if(k==='winch_type' && v.startsWith('Безредукторная')) n.speed_count='1'; if(k==='groove_shape'){n.undercut_angle='';} return n})
  const reset=()=>{setFilters(initialFilters);setTimeout(()=>doSearch(),0)}
  const activeCount=Object.values(filters).filter(Boolean).length
  const activeFilters=Object.entries(filters).filter(([,v])=>v!==''&&v!==null&&v!==undefined)
  const removeFilter=k=>setFilters(prev=>({...prev,[k]:'',...(k==='groove_shape'?{undercut_angle:''}:{})}))
  const toggleCompare=p=>setCompare(prev=>prev.some(x=>x.id===p.id)?prev.filter(x=>x.id!==p.id):prev.length<4?[...prev,p]:prev)
  const speedDisabled=filters.winch_type.startsWith('Безредукторная')
  const angleOptions=meta?.undercut_angles?.[filters.groove_shape]||[]

  return <div className="app-shell">
    <header className="topbar"><div className="container topbar-inner"><div className="brand"><div className="brand-mark">L</div><span>LIFTORG</span><em>B2B engineering</em></div><nav><a href="#catalog">Подбор</a><a href="#workflow">Как работает</a><a href="/admin">Управление каталогом</a></nav><a className="header-cta" href="#catalog">Начать подбор <ArrowRight size={16}/></a><button className="mobile-menu"><Menu/></button></div></header>

    <main>
      <section className="hero"><div className="container hero-grid"><div className="hero-copy"><div className="eyebrow accent">Профессиональный каталог</div><h1>Инженерный подбор<br/><span>лифтовых лебёдок</span></h1><p>Фильтруйте 838 исполнений по техническим параметрам, сравнивайте модели и формируйте запрос производителю.</p><div className="hero-actions"><a className="primary-btn large" href="#catalog">Подобрать лебёдку <ArrowRight/></a><div className="hero-count"><b>838</b><span>исполнений<br/>в базе</span></div></div></div>
      <div className="hero-visual"><div className="blueprint-card back"><span>Каталог</span><b>Nidec · Sicor · Torindrive</b></div><div className="blueprint-card front"><div className="flow-mini"><div><SlidersHorizontal/> Параметры</div><ChevronRight/><div><Layers3/> Модель</div><ChevronRight/><div><FileText/> Запрос</div></div><div className="hero-tags"><span>1000 кг</span><span>1,0–1,6 м/с</span><span>2:1</span><span>КВШ 400</span></div></div></div></div></section>

      <section className="workflow" id="workflow"><div className="container workflow-row">{[[1,'Параметры','Задайте требования',SlidersHorizontal],[2,'Модель','Выберите вариант',Layers3],[3,'Запрос цены','Опросный лист',FileText],[4,'Стоимость','Расчёт условий',Calculator]].map(([n,t,s,I],i)=><React.Fragment key={n}><div className={`workflow-step ${i===0?'active':''}`}><span>{String(n).padStart(2,'0')}</span><I/><div><b>{t}</b><small>{s}</small></div></div>{i<3&&<div className="workflow-line"/>}</React.Fragment>)}</div></section>

      <section className="catalog-section" id="catalog"><div className="container catalog-grid">
        <aside className={`filters-panel ${mobileFilters?'mobile-open':''}`}><div className="filters-top"><div><div className="eyebrow accent">Параметры проекта</div><h2>Фильтры</h2></div><button className="icon-btn" onClick={reset} title="Сбросить"><RotateCcw size={18}/></button><button className="mobile-close" onClick={()=>setMobileFilters(false)}><X/></button></div>
          <label className="search-field"><Search size={18}/><input value={filters.q} onChange={e=>setF('q',e.target.value)} placeholder="Модель или ID"/></label>
          <FilterSection title="Основное" subtitle="Тип, производитель, параметры" icon={SlidersHorizontal} open={openSections.main} setOpen={v=>setOpenSections(x=>({...x,main:v}))} badge="01"><div className="field-grid">
            <SelectField label="Производитель" value={filters.manufacturer} onChange={v=>setF('manufacturer',v)}><option value="">Любой</option>{meta?.manufacturers?.map(x=><option key={x}>{x}</option>)}</SelectField>
            <SelectField label="Тип лебёдки" value={filters.winch_type} onChange={v=>setF('winch_type',v)}><option value="">Любой тип</option>{meta?.winch_types?.map(x=><option key={x}>{x}</option>)}</SelectField>
            <SelectField label="Грузоподъёмность" value={filters.capacity_kg} onChange={v=>setF('capacity_kg',v)}><option value="">Любая</option>{meta?.capacities?.map(x=><option key={x} value={x}>{fmt(x,'кг')}</option>)}</SelectField>
            <SelectField label="Скорость" value={filters.speed_range} onChange={v=>setF('speed_range',v)}><option value="">Любой диапазон</option>{meta?.speed_ranges?.map(x=><option key={x.label} value={`${x.min}|${x.max}`}>{x.label}</option>)}</SelectField>
          </div></FilterSection>
          <FilterSection title="Привод" subtitle="Подвес, мощность, ЧП, энкодер" icon={Zap} open={openSections.drive} setOpen={v=>setOpenSections(x=>({...x,drive:v}))} badge="02"><div className="field-grid">
            <SelectField label="Кратность подвески" value={filters.suspension} onChange={v=>setF('suspension',v)}><option value="">Любая</option>{meta?.suspensions?.map(x=><option key={x}>{x}</option>)}</SelectField>
            <SelectField label="Мощность" value={filters.power_range} onChange={v=>setF('power_range',v)}><option value="">Любой диапазон</option>{meta?.power_ranges?.map(x=><option key={x.label} value={`${x.min}|${x.max}`}>{x.label}</option>)}</SelectField>
            <SelectField label="Количество скоростей" value={filters.speed_count} onChange={v=>setF('speed_count',v)} disabled={speedDisabled} hint={speedDisabled?'Для безредукторных — 1':''}><option value="">1 или 2</option><option value="1">1 скорость</option><option value="2">2 скорости</option></SelectField>
            <SelectField label="Наличие ЧП" value={filters.vfd} onChange={v=>setF('vfd',v)}><option value="">Неважно</option>{meta?.vfd_options?.map(x=><option key={x}>{x}</option>)}</SelectField>
            <SelectField label="Энкодер" value={filters.encoder_type} onChange={v=>setF('encoder_type',v)}><option value="">Неважно</option>{meta?.encoder_types?.map(x=><option key={x}>{x}</option>)}</SelectField>
          </div></FilterSection>
          <FilterSection title="Эксплуатация" subtitle="Нагрузка, высота, размещение" icon={Building2} open={openSections.operation} setOpen={v=>setOpenSections(x=>({...x,operation:v}))} badge="03"><div className="field-grid">
            <SelectField label="Консольная нагрузка" value={filters.cantilever_required_kg} onChange={v=>setF('cantilever_required_kg',v)}><option value="">Неважно</option>{meta?.cantilever_limits?.map(x=><option key={x.value} value={x.value}>{x.label}</option>)}</SelectField>
            <SelectField label="Высота подъёма" value={filters.lift_height_required_m} onChange={v=>setF('lift_height_required_m',v)}><option value="">Неважно</option>{meta?.lift_height_limits?.map(x=><option key={x.value} value={x.value}>{x.label}</option>)}</SelectField>
            <SelectField label="Тип размещения" value={filters.placement_type} onChange={v=>setF('placement_type',v)}><option value="">Неважно</option>{meta?.placement_types?.map(x=><option key={x}>{x}</option>)}</SelectField>
          </div></FilterSection>
          <FilterSection title="КВШ и канаты" subtitle="Геометрия и канаты" icon={Cable} open={openSections.ropes} setOpen={v=>setOpenSections(x=>({...x,ropes:v}))} badge="04"><div className="field-grid">
            <SelectField label="Форма ручья" value={filters.groove_shape} onChange={v=>setF('groove_shape',v)}><option value="">Любая</option>{meta?.groove_shapes?.map(x=><option key={x}>{x}</option>)}</SelectField>
            <SelectField label="Угол подреза" value={filters.undercut_angle} onChange={v=>setF('undercut_angle',v)} disabled={!filters.groove_shape}><option value="">Любой</option>{angleOptions.map(x=><option key={x} value={x}>{x}°</option>)}</SelectField>
            <SelectField label="Диаметр КВШ" value={filters.sheave_diameter_mm} onChange={v=>setF('sheave_diameter_mm',v)}><option value="">Любой</option>{meta?.sheave_diameters?.map(x=><option key={x} value={x}>{fmt(x,'мм')}</option>)}</SelectField>
            <SelectField label="Количество канатов" value={filters.rope_count} onChange={v=>setF('rope_count',v)}><option value="">Любое</option>{meta?.rope_counts?.map(x=><option key={x} value={x}>{x}</option>)}</SelectField>
            <SelectField label="Диаметр каната" value={filters.rope_diameter_mm} onChange={v=>setF('rope_diameter_mm',v)}><option value="">Любой</option>{meta?.rope_diameters?.map(x=><option key={x} value={x}>{fmt(x,'мм')}</option>)}</SelectField>
          </div></FilterSection>
          <FilterSection title="Электрика и прочее" subtitle="Тормоз, включения, масса" icon={Settings2} open={openSections.electric} setOpen={v=>setOpenSections(x=>({...x,electric:v}))} badge="05"><div className="field-grid">
            <SelectField label="Включений/час" value={filters.starts_per_hour} onChange={v=>setF('starts_per_hour',v)}><option value="">Любое</option>{meta?.starts_per_hour?.map(x=><option key={x} value={x}>{x}</option>)}</SelectField>
            <SelectField label="Питание тормоза" value={filters.brake_voltage} onChange={v=>setF('brake_voltage',v)}><option value="">Любое</option>{meta?.brake_voltages?.map(x=><option key={x}>{x}</option>)}</SelectField>
            <SelectField label="Масса" value={filters.weight_kg} onChange={v=>setF('weight_kg',v)}><option value="">Любая</option>{meta?.weights?.map(x=><option key={x} value={x}>{fmt(x,'кг')}</option>)}</SelectField>
          </div></FilterSection>
          <div className="filters-sticky-actions"><button className="apply-button" onClick={()=>{doSearch();setMobileFilters(false)}}><SlidersHorizontal size={18}/> Применить параметры {activeCount>0&&<span>{activeCount}</span>}</button>{activeCount>0&&<button className="reset-link" onClick={reset}>Сбросить все параметры</button>}</div>
        </aside>
        {mobileFilters && <div className="mobile-overlay" onClick={()=>setMobileFilters(false)}/>} 

        <div className="results-area">
          <div className="results-toolbar"><div><div className="eyebrow accent">Подходящие модели</div><h2>Результаты подбора</h2><p className="results-subtitle">Сначала показываем полностью подтверждённые модели, затем варианты, где в исходнике не хватает отдельных данных.</p></div><div className="toolbar-actions"><button className="mobile-filter-btn" onClick={()=>setMobileFilters(true)}><SlidersHorizontal size={17}/> Фильтры {activeCount>0&&<span>{activeCount}</span>}</button><div className="results-count">Кандидатов <b>{total}</b></div></div></div>
          <div className="match-summary"><div className="match-stat exact"><CheckCircle2 size={18}/><span><b>{matchStats.exact}</b> подтверждены</span></div><div className="match-stat clarify"><AlertTriangle size={18}/><span><b>{matchStats.clarify}</b> требуют уточнения</span></div>{activeCount>0&&<div className="match-stat muted"><X size={18}/><span><b>{matchStats.excluded}</b> исключены</span></div>}</div>
          {activeFilters.length>0&&<div className="active-filters"><span>Выбрано:</span>{activeFilters.map(([k,v])=><button key={k} onClick={()=>removeFilter(k)} title="Убрать фильтр"><small>{filterLabels[k]||k}</small><b>{prettyFilterValue(k,v,meta)}</b><X size={13}/></button>)}<button className="clear-all" onClick={reset}><RotateCcw size={14}/> Сбросить всё</button></div>}
          {meta?.data_coverage && <div className="coverage-note"><Info size={18}/><span><b>Как работает подбор:</b> если значение известно и не подходит — модель исключается. Если значения нет в исходных данных — модель остаётся кандидатом с пометкой «требует уточнения».</span></div>}
          {error && <div className="error-box"><AlertTriangle size={18}/>{error}</div>}
          {loading ? <div className="skeleton-grid">{Array.from({length:6}).map((_,i)=><div className="skeleton-card" key={i}/>)}</div> : items.length===0 ? <div className="empty-state"><Layers3 size={36}/><h3>Подходящих моделей не найдено</h3><p>Измените один или несколько параметров.</p><button onClick={reset}>Сбросить фильтры</button></div> : <div className="product-grid">{items.map(p=><ProductCard key={p.id} p={p} filters={filters} selected={compare.some(x=>x.id===p.id)} onCompare={toggleCompare} onDetails={setDetailsId}/>)}</div>}
          {!loading && items.length<total && <div className="load-more-wrap"><button className="load-more" onClick={()=>doSearch({append:true})} disabled={loadingMore}>{loadingMore?<><Loader2 className="spin"/> Загружаем</>:<>Показать ещё <ChevronDown size={18}/></>}</button><small>Показано {items.length} из {total}</small></div>}
        </div>
      </div></section>
    </main>

    {compare.length>0 && <div className="compare-dock animate-up"><div className="compare-dock-items">{compare.map(p=><div key={p.id}><span>{p.manufacturer}</span><b>{p.model}</b><button onClick={()=>toggleCompare(p)}><X size={14}/></button></div>)}{Array.from({length:4-compare.length}).map((_,i)=><div className="compare-empty" key={i}>+ модель</div>)}</div><div className="compare-dock-actions"><span>{compare.length} из 4</span><button disabled={compare.length<2} onClick={()=>setCompareOpen(true)}><Scale size={18}/> Сравнить</button></div></div>}
    {detailsId && <DetailsModal id={detailsId} filters={filters} onClose={()=>setDetailsId(null)} onAddCompare={toggleCompare} isCompared={compare.some(x=>x.id===detailsId)}/>} 
    {compareOpen && <CompareModal items={compare} onClose={()=>setCompareOpen(false)} onRemove={id=>setCompare(x=>x.filter(p=>p.id!==id))}/>} 
    <footer><div className="container"><div className="brand compact"><div className="brand-mark">L</div><span>LIFTORG</span></div><p>B2B engineering catalog · UX v4.1 · данные из актуальных файлов заказчика</p><a href="/legacy">Резервная серверная версия</a></div></footer>
  </div>
}

createRoot(document.getElementById('root')).render(<App/>)
