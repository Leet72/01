from __future__ import annotations
import html
from urllib.parse import urlencode


def fmt(v):
    if v in (None, ""): return "—"
    if isinstance(v, float) and v.is_integer(): return str(int(v))
    return str(v).replace('.', ',')

def fmt_speed(v):
    if v in (None, ''): return '—'
    try: return f"{float(v):.1f}".replace('.', ',')
    except Exception: return fmt(v)

def groove_label(v):
    z=str(v or '').strip().upper()
    return {'U':'U — U-образная с подрезом','V':'V — V-образная с подрезом','VH':'VH — V-образная закалённая с подрезом'}.get(z, v or 'По согласованию')

def fnum(v):
    if v in (None, ''): return None
    try: return float(str(v).replace(',', '.'))
    except: return None

def fint(v):
    if v in (None, ''): return None
    try: return int(float(str(v).replace(',', '.')))
    except: return None

def select(name,label,options,current='',any_label='Любое'):
    out=[f'<label class="server-field"><span>{html.escape(label)}</span><select name="{html.escape(name)}">']
    out.append(f'<option value="">{html.escape(any_label)}</option>')
    for value,text in options:
        sv=str(value); sel=' selected' if str(current)==sv else ''
        out.append(f'<option value="{html.escape(sv)}"{sel}>{html.escape(str(text))}</option>')
    out.append('</select></label>')
    return ''.join(out)

def range_select(name,label,ranges,current=''):
    opts=[('', 'Любой диапазон')]+[(f"{r['min']}|{r['max']}",r['label']) for r in ranges]
    return select(name,label,opts,current,any_label='Любой диапазон')

def card(x, query=''):
    mid=int(x.get('id') or 0)
    model=html.escape(str(x.get('model') or 'Без модели'))
    mfr=html.escape(str(x.get('manufacturer') or ''))
    specs=[
        ('Грузоподъёмность',f"{fmt(x.get('capacity_kg'))} кг"),('Скорость',f"{fmt(x.get('speed_m_s'))} м/с"),
        ('Мощность',f"{fmt(x.get('power_kw'))} кВт"),('Подвес',', '.join(map(str,x.get('suspensions') or [])) or '—'),
        ('КВШ',f"{fmt(x.get('sheave_diameter_mm'))} мм"),('Масса',f"{fmt(x.get('weight_kg'))} кг")]
    rows=''.join(f'<div class="spec"><small>{html.escape(a)}</small><b>{html.escape(str(b))}</b></div>' for a,b in specs)
    qs=('?'+query) if query else ''
    return f'''<article class="card" data-product-id="{mid}">
      <div class="card__top"><div><div class="card__mfr">{mfr}</div><h3>{model}</h3><div class="model-type">{html.escape(str(x.get('winch_type') or ''))}</div></div><span class="match-badge">Подходит</span></div>
      <div class="specs">{rows}</div>
      <div class="server-card-actions">
        <a class="server-link" href="/product/{mid}">Подробнее</a>
        <a class="server-link" href="/product/{mid}/inquiry{qs}">Заполнить опросный лист</a>
        <a class="server-link primary" href="/product/{mid}/order{qs}">Заказать лебёдку</a>
        <button type="button" class="server-link compare-button" data-product-id="{mid}" data-model="{model}">＋ Сравнить</button>
        <a class="server-link" href="/product/{mid}#calculator">Калькулятор</a>
      </div>
    </article>'''

def base_head(title='Liftorg — инженерный подбор'):
    return f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><link rel="stylesheet" href="/static/style.css?v=220"><style>
.server-shell{{max-width:1440px;margin:auto;padding:24px}}.server-layout{{display:grid;grid-template-columns:390px 1fr;gap:24px;align-items:start}}.server-filter{{position:sticky;top:12px;background:#f7fafc;border:1px solid #dce5eb;border-radius:18px;padding:18px}}.server-filter h2{{margin:0 0 4px}}.server-grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}.server-field{{display:flex;flex-direction:column;gap:5px;font-size:12px;font-weight:700;color:#52697b}}.server-field select,.server-field input,.question-field input,.question-field textarea,.question-field select{{width:100%;min-height:42px;border:1px solid #cedae3;border-radius:9px;background:white;padding:8px 10px;font-weight:700;color:#08243a}}.server-group{{margin:12px 0;border-top:1px solid #dbe5eb;padding-top:12px}}.server-group h3{{font-size:14px;margin:0 0 8px}}.server-actions{{display:flex;gap:8px;margin-top:16px}}.server-actions button,.server-actions a{{flex:1;text-align:center}}.server-results-head{{display:flex;justify-content:space-between;align-items:end;margin-bottom:14px}}.server-card-actions{{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px}}.server-link{{display:inline-flex;align-items:center;justify-content:center;min-height:42px;border-radius:9px;border:1px solid #ccd9e2;text-decoration:none;font-weight:800;color:#0b2a40;background:#fff;padding:0 12px;cursor:pointer}}.server-link.primary{{background:#ef543e;color:white;border-color:#ef543e}}.server-pagination{{display:flex;justify-content:center;gap:10px;margin:22px 0}}.tech-detail{{max-width:1180px;margin:30px auto;padding:0 22px}}.detail-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}}.detail-cell{{border:1px solid #dbe5eb;border-radius:10px;padding:12px}}.detail-cell small{{display:block;color:#718596}}.question-group{{border:1px solid #dce5eb;border-radius:14px;padding:16px;margin:14px 0}}.question-field{{display:grid;grid-template-columns:minmax(280px,1fr) minmax(220px,1fr);gap:12px;align-items:center;margin:8px 0}}.compare-tray-server{{position:fixed;left:50%;bottom:18px;transform:translateX(-50%);background:#09263a;color:#fff;border-radius:14px;padding:10px 14px;display:none;z-index:1000;box-shadow:0 10px 30px #0003}}.compare-tray-server.active{{display:flex;gap:12px;align-items:center}}@media(max-width:900px){{.server-layout{{grid-template-columns:1fr}}.server-filter{{position:static}}.server-grid{{grid-template-columns:1fr 1fr}}.detail-grid{{grid-template-columns:1fr 1fr}}}}@media(max-width:560px){{.server-grid,.detail-grid{{grid-template-columns:1fr}}.question-field{{grid-template-columns:1fr}}}}
</style></head><body><header class="header"><div class="shell nav"><a href="/" class="brand"><span class="brand-mark">L</span><b>LIFTORG</b></a><nav><a href="/#catalog">Подбор оборудования</a><a href="/admin">Администрирование</a></nav></div></header>'''

def parse_args(qp):
    sp=(qp.get('speed_range') or '').split('|'); pp=(qp.get('power_range') or '').split('|')
    return {
      'manufacturer':qp.get('manufacturer') or None,'winch_type':qp.get('winch_type') or None,'capacity_kg':fnum(qp.get('capacity_kg')),
      'speed_min':fnum(sp[0]) if len(sp)==2 else None,'speed_max':fnum(sp[1]) if len(sp)==2 else None,
      'suspension':qp.get('suspension') or None,'speed_count':fint(qp.get('speed_count')),'vfd':qp.get('vfd') or None,'encoder_type':qp.get('encoder_type') or None,
      'power_min':fnum(pp[0]) if len(pp)==2 else None,'power_max':fnum(pp[1]) if len(pp)==2 else None,
      'cantilever_required_kg':fnum(qp.get('cantilever_required_kg')),'lift_height_required_m':fnum(qp.get('lift_height_required_m')),
      'groove_shape':qp.get('groove_shape') or None,'undercut_angle':fint(qp.get('undercut_angle')),'sheave_diameter_mm':fnum(qp.get('sheave_diameter_mm')),
      'rope_count':fint(qp.get('rope_count')),'rope_diameter_mm':fnum(qp.get('rope_diameter_mm')),'starts_per_hour':fint(qp.get('starts_per_hour')),
      'brake_voltage':qp.get('brake_voltage') or None,'weight_kg':fnum(qp.get('weight_kg')),'placement_type':qp.get('placement_type') or None,
      'q':qp.get('q') or None,'frame_supply':qp.get('frame_supply') or None,'remote_release':qp.get('remote_release') or None,
      'limit':24,'offset':max(0,fint(qp.get('offset')) or 0)}

def render_index(request, ctx):
    qp=request.query_params; args=parse_args(qp); result=ctx['search'](**args); m=ctx['meta']()
    current_speed='' if args['speed_min'] is None else f"{args['speed_min']}|{args['speed_max']}"; current_power='' if args['power_min'] is None else f"{args['power_min']}|{args['power_max']}"
    cards=''.join(card(x,request.url.query) for x in result['items']) or '<div class="empty-state"><b>Ничего не найдено</b><span>Измените параметры подбора.</span></div>'
    out=[base_head(),'<main class="server-shell" id="catalog"><div class="server-layout"><form class="server-filter" method="get" action="/">']
    out.append('<span class="section-kicker">Инженерный конфигуратор</span><h2>Параметры подбора</h2><p>Серверная фильтрация: каталог работает даже без JavaScript.</p>')
    out.append('<div class="server-group"><h3>Основное</h3>')
    out.append(f'<label class="server-field"><span>Поиск модели / ID</span><input name="q" value="{html.escape(qp.get("q", ""))}" placeholder="Например WJC-1150"></label><div class="server-grid">')
    out.append(select('manufacturer','Производитель',[(x,x) for x in m['manufacturers']],args['manufacturer'] or ''))
    out.append(select('winch_type','Тип лебёдки',[(x,x) for x in m['winch_types']],args['winch_type'] or ''))
    out.append(select('capacity_kg','Грузоподъёмность',[(fmt(x),f'{fmt(x)} кг') for x in m['capacities']],fmt(args['capacity_kg']) if args['capacity_kg'] is not None else ''))
    out.append(range_select('speed_range','Скорость',m['speed_ranges'],current_speed)); out.append('</div></div>')
    out.append('<div class="server-group"><h3>Привод</h3><div class="server-grid">')
    out.append(select('suspension','Кратность подвески',[(x,x) for x in m['suspensions']],args['suspension'] or ''))
    out.append(select('speed_count','Количество скоростей',[(1,'1 скорость'),(2,'2 скорости')],str(args['speed_count'] or '')))
    out.append(select('vfd','Наличие ЧП',[(x,x) for x in m['vfd_options']],args['vfd'] or '','Неважно'))
    out.append(select('encoder_type','Энкодер',[(x,x) for x in m['encoder_types']],args['encoder_type'] or '','Неважно'))
    out.append(range_select('power_range','Мощность',m['power_ranges'],current_power)); out.append('</div></div>')
    out.append('<details class="server-group"><summary><b>Эксплуатация</b></summary><div class="server-grid" style="margin-top:10px">')
    out.append(select('cantilever_required_kg','Консольная нагрузка',[(x['value'],x['label']) for x in m['cantilever_limits']],fmt(args['cantilever_required_kg']) if args['cantilever_required_kg'] is not None else '','Неважно'))
    out.append(select('lift_height_required_m','Высота подъёма',[(x['value'],x['label']) for x in m['lift_height_limits']],fmt(args['lift_height_required_m']) if args['lift_height_required_m'] is not None else '','Неважно'))
    out.append(select('placement_type','Тип размещения',[(x,x) for x in m['placement_types']],args['placement_type'] or '','Неважно')); out.append('</div></details>')
    out.append('<details class="server-group"><summary><b>КВШ и канаты</b></summary><div class="server-grid" style="margin-top:10px">')
    out.append(select('groove_shape','Форма ручья',[(x,x) for x in m['groove_shapes']],args['groove_shape'] or ''))
    angles=sorted(set(sum(m['undercut_angles'].values(),[]))); out.append(select('undercut_angle','Угол подреза',[(x,str(x)) for x in angles],str(args['undercut_angle'] or '')))
    out.append(select('sheave_diameter_mm','Диаметр КВШ',[(fmt(x),f'{fmt(x)} мм') for x in m['sheave_diameters']],fmt(args['sheave_diameter_mm']) if args['sheave_diameter_mm'] is not None else ''))
    out.append(select('rope_count','Количество канатов',[(x,str(x)) for x in m['rope_counts']],str(args['rope_count'] or '')))
    out.append(select('rope_diameter_mm','Диаметр каната',[(fmt(x),f'{fmt(x)} мм') for x in m['rope_diameters']],fmt(args['rope_diameter_mm']) if args['rope_diameter_mm'] is not None else '')); out.append('</div></details>')
    out.append('<details class="server-group"><summary><b>Электрика и прочее</b></summary><div class="server-grid" style="margin-top:10px">')
    out.append(select('starts_per_hour','Включений/час',[(x,str(x)) for x in m['starts_per_hour']],str(args['starts_per_hour'] or '')))
    out.append(select('brake_voltage','Напряжение тормоза',[(x,x) for x in m['brake_voltages']],args['brake_voltage'] or ''))
    out.append(select('weight_kg','Масса',[(fmt(x),f'{fmt(x)} кг') for x in m['weights']],fmt(args['weight_kg']) if args['weight_kg'] is not None else ''))
    out.append(select('frame_supply','Поставка с рамой',[('Да','Да'),('Нет','Нет'),('По запросу','По запросу')],args['frame_supply'] or '','Неважно'))
    out.append(select('remote_release','Дистанционное расцепление',[('Да','Да'),('Нет','Нет'),('По запросу','По запросу')],args['remote_release'] or '','Неважно')); out.append('</div></details>')
    out.append('<input type="hidden" name="offset" value="0"><div class="server-actions"><button class="cta" type="submit">Показать подходящие</button><a class="server-link" href="/">Сбросить</a></div></form>')
    out.append(f'<section><div class="server-results-head"><div><span class="section-kicker">Результаты</span><h2>Подходящие модели</h2></div><div class="result-counter">Найдено {result["total"]} · показано {result["offset"]+result["count"]}</div></div><div class="cards">{cards}</div>')
    base=[(k,v) for k,v in qp.multi_items() if k!='offset' and v!='']
    out.append('<div class="server-pagination">')
    if result['offset']>0: out.append(f'<a class="server-link" href="/?{urlencode(base+[("offset",max(0,result["offset"]-24))])}">← Назад</a>')
    if result['has_more']: out.append(f'<a class="server-link primary" href="/?{urlencode(base+[("offset",result["offset"]+24)])}">Показать ещё →</a>')
    out.append('</div></section></div></main><div id="compare_tray_server" class="compare-tray-server"><span id="compare_text">Выбрано: 0 из 4</span><button id="compare_go" class="server-link primary" type="button">Сравнить</button><button id="compare_clear_server" class="server-link" type="button">Очистить</button></div><script src="/static/enhance.js?v=220" defer></script></body></html>')
    return ''.join(out)

def render_product(p):
    title=f"{p.get('manufacturer','')} {p.get('model','')}"
    gearless='безредукт' in str(p.get('winch_type') or '').lower()
    placement=p.get('placement_type_normalized') or p.get('placement_type') or '—'
    main=[('Грузоподъёмность, кг','capacity_kg'),('Скорость, м/с','speed_m_s'),('Подвес','suspensions')]
    if not gearless: main.append(('Количество скоростей','speed_count'))
    groups=[
      ('Основное',main),
      ('Привод',[('Мощность, кВт','power_kw'),('Ток, А','nominal_current_a'),('Номинальная частота вращения, об/мин','nominal_rpm'),('Номинальная частота, Гц','frequency_hz'),('Крутящий момент, Нм','torque_nm')]),
      ('КВШ и канаты',[('Диаметр КВШ, мм','sheave_diameter_mm'),('Форма ручья','groove_shape'),('Угол подреза','undercut_angle'),('Число канатов, шт. × Диаметр канатов, мм','rope_spec'),('Расстояние между канатами, мм','groove_pitch_mm')]),
      ('Эксплуатация',[('Консольная нагрузка, кг','max_cantilever_load_kg'),('Высота подъёма, м','max_lift_height_m'),('Включений в час','starts_per_hour'),('Режим работы','duty_cycle'),('Масса, кг','weight_kg')]),
      ('Тормоз',[('Напряжение тормоза, В','brake_voltage'),('Номинальный ток, А','brake_nominal_current_a')]),
    ]
    def value(key):
        if key=='speed_m_s': return fmt_speed(p.get(key))
        if key=='suspensions': return ', '.join(map(str,p.get(key) or [])) or '—'
        if key=='groove_shape': return groove_label(p.get(key))
        if key=='undercut_angle': return 'По согласованию' if p.get(key) in (None,'') else fmt(p.get(key))+'°'
        if key=='rope_spec': return f"{', '.join(map(str,p.get('rope_counts') or [])) or '—'} × {', '.join(fmt(x) for x in (p.get('rope_diameters_mm') or [])) or '—'}"
        if key=='max_lift_height_m' and p.get(key) in (None,''): return 'Определяется по результатам подбора'
        return fmt(p.get(key))
    blocks=[]
    for title_g,rows in groups:
        cells=''.join(f'<div class="detail-cell"><small>{html.escape(label)}</small><b>{html.escape(value(key))}</b></div>' for label,key in rows)
        blocks.append(f'<section class="product-spec-group"><h3>{html.escape(title_g)}</h3><div class="detail-grid">{cells}</div></section>')
    media=p.get('media') or []
    photos=[x for x in media if x.get('media_kind')=='photo']; drawings=[x for x in media if x.get('media_kind')=='drawing']; documents=[x for x in media if x.get('media_kind')=='document']
    gallery=[]
    for x in photos+drawings:
        url=html.escape(str(x.get('url') or '')); mt=html.escape(str(x.get('title') or ('Фото оборудования' if x.get('media_kind')=='photo' else 'Габаритный чертёж')))
        gallery.append(f'<a class="media-gallery-item" href="{url}" target="_blank"><img src="{url}" alt="{mt}"><span>{mt}</span><small>{"Фото" if x.get("media_kind")=="photo" else "Чертёж"}</small></a>')
    docs=''.join(f'<a class="server-link" href="{html.escape(str(x.get("url") or ""))}" target="_blank">📄 {html.escape(str(x.get("title") or "Документ"))}</a>' for x in documents)
    raw=p.get('raw') or {}; rawcells=''.join(f'<div class="detail-cell"><small>{html.escape(str(k))}</small><b>{html.escape(fmt(v))}</b></div>' for k,v in raw.items())
    chips=f'<span>{fmt(p.get("capacity_kg"))} кг</span><span>{fmt_speed(p.get("speed_m_s"))} м/с</span><span>{fmt(p.get("power_kw"))} кВт</span><span>Подвес {html.escape(", ".join(map(str,p.get("suspensions") or [])) or "—")}</span><span>{html.escape(str(placement))}</span>'
    return base_head(title)+f'''<style>.product-hero{{display:grid;grid-template-columns:320px 1fr;gap:24px;padding:22px;border:1px solid #dce6eb;border-radius:18px;background:#f4f8fa;margin:18px 0}}.product-hero img{{width:100%;height:240px;object-fit:contain;background:#fff;border-radius:13px}}.product-chips{{display:flex;flex-wrap:wrap;gap:7px;margin-top:14px}}.product-chips span{{background:#0d3046;color:#fff;padding:7px 10px;border-radius:8px;font-size:11px;font-weight:900}}.product-actions{{position:sticky;top:8px;z-index:5;display:grid;grid-template-columns:repeat(3,1fr);gap:8px;padding:10px;background:#ffffffed;border:1px solid #dce6eb;border-radius:13px;backdrop-filter:blur(10px)}}.product-spec-group{{margin:18px 0}}.product-spec-group h3{{margin:0 0 9px}}.media-gallery{{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:12px;margin:16px 0 22px}}.media-gallery-item{{border:1px solid #dbe5eb;border-radius:14px;overflow:hidden;background:#fff;text-decoration:none;color:#17384d}}.media-gallery-item img{{width:100%;height:180px;object-fit:contain;background:#f7fafc;display:block}}.media-gallery-item span,.media-gallery-item small{{display:block;padding:8px 10px 0;font-weight:800}}.media-gallery-item small{{padding:0 10px 10px;color:#758995;font-size:10px}}@media(max-width:760px){{.product-hero{{grid-template-columns:1fr}}.product-actions{{bottom:0;top:auto;grid-template-columns:1fr}}}}</style><main class="tech-detail"><a class="server-link" href="/">← К подбору</a><section class="product-hero"><div>{f'<img src="{html.escape(str(p.get("image_ref") or ""))}" alt="{html.escape(title)}">' if p.get('image_ref') else ''}</div><div><span class="section-kicker">Технический паспорт</span><h1>{html.escape(title)}</h1><p>{html.escape(str(p.get('winch_type') or ''))}</p><div class="product-chips">{chips}</div></div></section><div class="product-actions"><a class="server-link" href="/product/{p['id']}/inquiry">Опросный лист</a><a class="server-link primary" href="/product/{p['id']}/order">Заказать</a><a class="server-link" href="/#calculator">Рассчитать стоимость</a></div>{''.join(blocks)}<section class="product-spec-group"><h3>Габариты и присоединение</h3><p>Габаритные и присоединительные размеры, которых нет в структурированных данных, смотрите на техническом чертеже.</p></section>{('<section><span class="section-kicker">Технические материалы</span><h2>Фото, чертежи и документы</h2><div class="media-gallery">'+''.join(gallery)+'</div>'+('<div class="server-actions">'+docs+'</div>' if docs else '')+'</section>') if gallery or docs else ''}<details class="server-group"><summary><b>Все исходные характеристики</b></summary><div class="detail-grid" style="margin-top:12px">{rawcells}</div></details></main></body></html>'''

def prefill_value(field,p,qp):
    code=field.get('code')
    # TDNA-specific normalization: preserve engineering meaning while matching UI options.
    if code=='tdna_winch_type':
        wt=str(p.get('winch_type') or '').lower()
        if 'безредукт' in wt: return 'Безредукторная'
        if 'редукт' in wt: return 'Редукторная'
    if code=='tdna_machine_shape':
        wt=str(p.get('winch_type') or '').lower(); model=str(p.get('model') or '').upper()
        if model.startswith('WE-20-2000') or model.startswith('WE20-2000'): return 'Плоская таблетка'
        if 'таблет' in wt: return 'Таблетка'
        if 'боч' in wt: return 'Бочонок'
    if code=='tdna_existing_rope_diameter':
        vals=p.get('rope_diameters_mm') or []
        if not isinstance(vals,list): vals=[vals]
        if vals:
            try:
                v=float(vals[0]); return (str(int(v)) if v.is_integer() else str(v))+' мм'
            except Exception: return str(vals[0])
    key=field.get('autofill_product')
    if key:
        v=p.get(key)
        if isinstance(v,list): return ', '.join(map(str,v))
        return '' if v is None else str(v)
    fk=field.get('autofill_filter')
    if fk:
        # First prefer the exact value selected by the engineer in the current filter URL.
        try:
            if fk in qp and qp.get(fk) not in (None,''): return str(qp.get(fk))
        except Exception:
            pass
        fmap={'capacity':'capacity_kg','speed':'speed_m_s','speed_count':'speed_count','vfd':'vfd','encoder_type':'encoder','power':'power_kw','cantilever':'max_cantilever_load_kg','lift_height':'max_lift_height_m','sheave':'sheave_diameter_mm','rope_count':'rope_counts','rope_diameter':'rope_diameters_mm','groove_shape':'groove_shape','brake_voltage':'brake_voltage','weight':'weight_kg','frame_supply':'frame_supply','remote_release':'remote_release'}
        if fk in fmap:
            v=p.get(fmap[fk]); return ', '.join(map(str,v)) if isinstance(v,list) else ('' if v is None else str(v))
    return ''

def render_inquiry(p,fields,qp,success=None):
    """Two-level RFQ UX with engineering sketches and resilient draft saving."""
    groups={}
    for f in fields:
        if f.get('kind')=='heading':
            continue
        groups.setdefault(f.get('group') or 'Дополнительно',[]).append(f)

    sketch_for_group={
        'Данные для чертежа':[
            ('/static/survey-sketches/torin-machine-hand.png','Оригинальный эскиз Torin: левое / правое монтажное положение.'),
            ('/static/survey-sketches/torin-room-clearances.png','Оригинальный эскиз Torin: высота помещения, Rope Drop, расстояние до стены, Z1 и Z2.'),
        ],
        'Отводной блок и компоновка':[
            ('/static/survey-sketches/torin-beam-deflector.png','Оригинальный эскиз Torin: балки, CT, Wf/Ww, Ddef и Ys.'),
            ('/static/survey-sketches/torin-angle-layouts.png','Оригинальный эскиз Torin: схемы A/B/C/D и размеры X1/X2/X3.'),
        ],
        'Блоки / шкивы':[
            ('/static/survey-sketches/torin-sheave-types.png','Оригинальный эскиз Torin: схемы огибания канатом A/B/C и размеры L1–L6.'),
        ],
    }

    group_cards=[]
    for idx,(g,fs) in enumerate(groups.items(),1):
        fields_html=[]
        for f in fs:
            code=f['code']; label=html.escape(f['label']); val=html.escape(prefill_value(f,p,qp))
            kind=f.get('kind')
            readonly=' readonly' if f.get('readonly') else ''
            figure_html=f'<small class="figure-ref">См. рис. {html.escape(str(f.get("figure")))}</small>' if f.get('figure') else ''
            help_html=f'<small class="field-help">{html.escape(str(f.get("help")))}</small>' if f.get('help') else ''
            autofill_html='<small class="autofill-note">✓ заполнено из выбранного исполнения</small>' if val else ''
            if kind=='textarea':
                inp=f'<textarea name="{code}" rows="3" data-survey-field{readonly}>{val}</textarea>'
            elif kind=='select':
                options=[str(o) for o in f.get('options',[])]
                opts=['<option value="">Выберите</option>']
                if val and val not in options: opts.append(f'<option value="{val}" selected>{val}</option>')
                opts += [f'<option value="{html.escape(o)}"'+(' selected' if o==val else '')+f'>{html.escape(o)}</option>' for o in options]
                inp=f'<select name="{code}" data-survey-field>{"".join(opts)}</select>'
            elif kind=='checkbox':
                checked=' checked' if (val in ('Да','true','True','1') or (not val and f.get('default'))) else ''
                inp=f'<span class="check-control"><input type="checkbox" name="{code}" value="Да" data-survey-field{checked}><span>Добавить в запрос</span></span>'
            else:
                input_type='date' if kind=='date' else ('number' if kind=='number' else 'text')
                step=' step="any"' if input_type=='number' else ''
                inp=f'<input type="{input_type}" name="{code}" value="{val}" data-survey-field{readonly}{step}>'
            fields_html.append(f'<label class="survey-field"><span>{label}</span>{inp}{autofill_html}{figure_html}{help_html}</label>')

        sketches=sketch_for_group.get(g,[])
        sketch_html=''
        if sketches:
            parts=[]
            for src,caption in sketches:
                parts.append(f'<figure class="survey-figure"><button type="button" class="survey-image-button" data-survey-image="{src}" data-survey-caption="{html.escape(caption)}"><img src="{src}" alt="Схема Torin Drive для раздела {html.escape(g)}"><span>Увеличить схему ↗</span></button><figcaption>{html.escape(caption)}</figcaption></figure>')
            sketch_html=f'<aside class="survey-sketch"><div class="source-badge">Эскизы из TDNA Traction Survey</div>{"".join(parts)}<small>Если размер неизвестен — поле можно оставить пустым и уточнить с инженером позже.</small></aside>'
        open_attr=' open' if idx==1 else ''
        group_cards.append(f'''<details class="survey-section"{open_attr}>
            <summary><span class="survey-index">{idx:02d}</span><span><b>{html.escape(g)}</b><small>{len(fs)} полей · можно заполнить позже</small></span><span class="survey-chevron">⌄</span></summary>
            <div class="survey-section-body"><div class="survey-fields-grid">{"".join(fields_html)}</div>{sketch_html}</div>
        </details>''')

    notice=f'<div class="survey-success"><b>Запрос отправлен.</b> Номер: {html.escape(success)}</div>' if success else ''
    manufacturer=html.escape(str(p.get('manufacturer') or ''))
    model=html.escape(str(p.get('model') or ''))
    pid=int(p['id'])

    def _summary_value(v, suffix=''):
        if isinstance(v,list):
            v=', '.join(str(x) for x in v if x not in (None,''))
        if v in (None,''): return '—'
        return html.escape(str(v)) + ((' '+suffix) if suffix else '')

    wt=str(p.get('winch_type') or '')
    wt_low=wt.lower()
    model_raw=str(p.get('model') or '').upper()
    if model_raw.startswith('WE-20-2000') or model_raw.startswith('WE20-2000'):
        shape='Плоская таблетка'
    elif 'боч' in wt_low:
        shape='Бочонок'
    elif 'таблет' in wt_low:
        shape='Таблетка'
    else:
        shape='—'
    placement=str(p.get('placement_type') or '—')
    selection_rows=[
        ('Производитель', _summary_value(p.get('manufacturer'))),
        ('Модель / исполнение', _summary_value(p.get('model'))),
        ('ID исполнения', _summary_value(p.get('identification_number') or p.get('id'))),
        ('Тип лебёдки', _summary_value(p.get('winch_type'))),
        ('Тип размещения', _summary_value(placement)),
        ('Форма', _summary_value(shape)),
        ('Кратность подвески', _summary_value(p.get('suspensions'))),
        ('Грузоподъёмность', _summary_value(p.get('capacity_kg'),'кг')),
        ('Скорость', _summary_value(p.get('speed_m_s'),'м/с')),
        ('Диаметр каната', _summary_value(p.get('rope_diameters_mm'),'мм')),
    ]
    summary_html=''.join(f'<div class="selection-item"><small>{html.escape(str(k))}</small><b>{v}</b></div>' for k,v in selection_rows)

    return base_head('Инженерный запрос')+f'''<style>
    .survey-page{{max-width:1280px;margin:26px auto 70px;padding:0 24px;color:#0b2a40}}
    .survey-back{{margin-bottom:18px}}.survey-hero{{display:grid;grid-template-columns:1fr auto;gap:24px;align-items:end;margin-bottom:20px}}
    .survey-hero h1{{font-size:clamp(30px,4vw,52px);line-height:1;margin:7px 0 10px}}.survey-hero p{{max-width:760px;color:#657b8b;margin:0}}
    .survey-product{{border:1px solid #d9e4ea;border-radius:15px;padding:13px 16px;background:#fff;min-width:250px}}.survey-product small{{display:block;color:#7c8e99}}.survey-product b{{font-size:18px}}
    .selection-summary{{border:1px solid #d8e3e9;border-radius:18px;background:#f7fafc;padding:18px 20px;margin:18px 0}}.selection-summary-head{{display:flex;justify-content:space-between;gap:14px;align-items:center;margin-bottom:12px}}.selection-summary-head h2{{margin:0;font-size:20px}}.selection-summary-head p{{margin:3px 0 0;color:#718492}}.selection-grid{{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:9px}}.selection-item{{border:1px solid #dfe8ed;border-radius:11px;background:#fff;padding:9px 10px;min-width:0}}.selection-item small{{display:block;color:#82939e;font-size:9px;font-weight:900;text-transform:uppercase;letter-spacing:.04em;margin-bottom:3px}}.selection-item b{{display:block;color:#17384d;font-size:12px;overflow-wrap:anywhere}}
    .lead-card{{border:1px solid #d8e3e9;border-radius:20px;background:#fff;padding:20px;box-shadow:0 10px 30px #173b5010;margin:18px 0}}
    .lead-card-head{{display:flex;justify-content:space-between;gap:16px;align-items:start;margin-bottom:14px}}.lead-card h2{{margin:0;font-size:23px}}.lead-card p{{margin:4px 0 0;color:#718492}}
    .lead-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}.lead-grid label,.survey-field{{display:flex;flex-direction:column;gap:6px;color:#5e7484;font-size:12px;font-weight:800}}
    .lead-grid input,.lead-grid textarea,.survey-field input,.survey-field textarea,.survey-field select{{width:100%;min-height:46px;border:1px solid #cddbe3;border-radius:11px;background:#fff;padding:10px 12px;color:#102f43;font:inherit;font-weight:700;outline:none}}
    .lead-grid textarea{{grid-column:span 3;min-height:82px;resize:vertical}}.lead-grid input:focus,.survey-field input:focus,.survey-field textarea:focus,.survey-field select:focus{{border-color:#174b68;box-shadow:0 0 0 3px #174b6812}}
    .draft-status{{font-size:12px;font-weight:800;color:#648194;background:#eef5f7;border-radius:999px;padding:7px 11px;white-space:nowrap}}.draft-status.saved{{color:#197044;background:#e9f7ef}}.draft-status.error{{color:#9a4d10;background:#fff2df}}
    .engineering-intro{{display:flex;justify-content:space-between;gap:20px;align-items:center;border:1px solid #d9e4ea;border-radius:18px;padding:18px 20px;background:#f7fafc;margin:18px 0}}
    .engineering-intro h2{{font-size:22px;margin:0 0 4px}}.engineering-intro p{{margin:0;color:#6d8290}}.engineering-intro button{{flex:none}}
    .survey-section{{border:1px solid #d8e3e9;border-radius:16px;background:#fff;margin:10px 0;overflow:hidden}}.survey-section summary{{list-style:none;display:grid;grid-template-columns:46px 1fr 30px;gap:10px;align-items:center;cursor:pointer;padding:15px 17px}}
    .survey-section summary::-webkit-details-marker{{display:none}}.survey-index{{width:38px;height:34px;border-radius:9px;background:#edf5f7;display:grid;place-items:center;color:#5d7889;font-weight:900;font-size:12px}}.survey-section summary b{{display:block;font-size:15px}}.survey-section summary small{{display:block;color:#82939e;margin-top:2px}}.survey-chevron{{font-size:22px;color:#78909e}}
    .survey-section[open] .survey-chevron{{transform:rotate(180deg)}}.survey-section-body{{border-top:1px solid #e5edf1;padding:17px;display:grid;grid-template-columns:minmax(0,1fr) 330px;gap:18px}}
    .survey-fields-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}}.survey-field textarea{{min-height:86px;resize:vertical}}.survey-sketch{{border:1px solid #e0e8ed;border-radius:14px;padding:10px;background:#f9fbfc;align-self:start;position:sticky;top:90px}}.survey-sketch img{{width:100%;height:auto;display:block;border-radius:8px;background:#fff}}.survey-image-button{{display:block;width:100%;padding:0;border:0;background:transparent;cursor:zoom-in;text-align:left;position:relative}}.survey-image-button span{{position:absolute;right:8px;bottom:8px;background:#0b2e43e8;color:#fff;border-radius:8px;padding:6px 8px;font-size:10px;font-weight:900;box-shadow:0 4px 16px #0002}}.figure-ref{{display:inline-flex!important;width:max-content;background:#eef4f7;color:#355d73!important;border-radius:999px;padding:3px 7px;font-size:9px!important;font-weight:900!important}}.survey-lightbox{{position:fixed;inset:0;background:#061723df;z-index:9999;display:none;align-items:center;justify-content:center;padding:24px}}.survey-lightbox.open{{display:flex}}.survey-lightbox-card{{max-width:min(1200px,96vw);max-height:94vh;background:#fff;border-radius:18px;padding:14px;box-shadow:0 25px 90px #0008;display:flex;flex-direction:column;gap:10px}}.survey-lightbox-card img{{max-width:100%;max-height:82vh;object-fit:contain}}.survey-lightbox-top{{display:flex;justify-content:space-between;gap:15px;align-items:center;color:#17384d;font-size:12px;font-weight:800}}.survey-lightbox-close{{border:1px solid #cbd9e2;border-radius:9px;background:#fff;padding:7px 10px;cursor:pointer;font-weight:900}}.survey-sketch small{{display:block;color:#748895;line-height:1.4;padding:6px 5px 2px}}.survey-figure{{margin:0 0 12px}}.survey-figure figcaption{{font-size:11px;color:#6c808d;line-height:1.35;margin-top:5px}}.source-badge{{font-size:10px;font-weight:900;letter-spacing:.06em;text-transform:uppercase;color:#587585;margin:2px 4px 10px}}.field-help{{font-size:10px!important;font-weight:600!important;color:#8798a2!important;line-height:1.35}}.autofill-note{{font-size:10px!important;font-weight:800!important;color:#287a50!important}}.check-control{{min-height:46px;border:1px solid #cddbe3;border-radius:11px;padding:10px 12px;display:flex;align-items:center;gap:9px;background:#fff;color:#17384d;font-size:12px}}.check-control input{{width:18px!important;min-height:auto!important;height:18px;margin:0;padding:0}}
    .commercial-block{{border:1px solid #f1c9bf;background:#fff9f7;border-radius:18px;padding:20px;margin:18px 0}}.commercial-block h2{{margin:0 0 6px}}.commercial-block p{{color:#735f59;margin:0 0 16px}}.commercial-actions{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
    .survey-actions{{position:sticky;bottom:12px;display:flex;gap:10px;max-width:740px;margin:20px auto 0;padding:10px;background:#ffffffee;border:1px solid #dbe5ea;border-radius:15px;backdrop-filter:blur(10px);box-shadow:0 12px 36px #16364a20;z-index:20}}.survey-actions>*{{flex:1}}
    .survey-success{{border-radius:14px;background:#eaf8ef;border:1px solid #bfe5cb;padding:15px 17px;color:#16613b;margin:16px 0}}
    .optional-label{{display:inline-flex;border-radius:999px;background:#eff5f7;padding:6px 9px;color:#5a7585;font-size:11px;font-weight:900}}
    @media(max-width:900px){{.selection-grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}.survey-hero{{grid-template-columns:1fr}}.lead-grid{{grid-template-columns:1fr 1fr}}.lead-grid textarea{{grid-column:span 2}}.survey-section-body{{grid-template-columns:1fr}}.survey-sketch{{position:static;max-width:520px}}}}
    @media(max-width:620px){{.survey-page{{padding:0 14px}}.selection-grid{{grid-template-columns:1fr}}.lead-grid,.survey-fields-grid,.commercial-actions{{grid-template-columns:1fr}}.lead-grid textarea{{grid-column:auto}}.survey-actions{{position:static;flex-direction:column}}.engineering-intro{{align-items:start;flex-direction:column}}}}
    </style>
    <main class="survey-page">
      <div class="survey-back"><a class="server-link" href="/product/{pid}">← К модели</a></div>
      <section class="survey-hero">
        <div><span class="section-kicker">Инженерный опросный лист</span><h1>Заполнить опросный лист</h1><p>Этот путь нужен, когда требуется передать инженеру технические данные проекта. Для обычного заказа техническая форма необязательна. Черновик сохраняется автоматически.</p></div>
        <div class="survey-product"><small>Выбранная модель</small><b>{manufacturer} {model}</b><small>Параметры подбора и известные характеристики уже подставлены.</small></div>
      </section>
      {notice}
      <form method="post" id="survey-form" autocomplete="on">
        <input type="hidden" name="draft_token" id="draft-token">
        <section class="selection-summary">
          <div class="selection-summary-head"><div><span class="section-kicker">Уже известно из подбора</span><h2>Параметры выбранного исполнения</h2><p>Эти данные повторно не запрашиваем. Если что-то нужно изменить — вернитесь к подбору или выберите другое исполнение.</p></div></div>
          <div class="selection-grid">{summary_html}</div>
        </section>
        <section class="lead-card">
          <div class="lead-card-head"><div><span class="section-kicker">Шаг 1 · достаточно для связи</span><h2>Короткий запрос</h2><p>Не заставляем клиента заполнять весь инженерный опросник для первого обращения.</p></div><span class="draft-status" id="draft-status">Черновик включён</span></div>
          <div class="lead-grid">
            <label><span>Имя</span><input name="lead_name" data-survey-field placeholder="Как к вам обращаться"></label>
            <label><span>Компания</span><input name="lead_company" data-survey-field placeholder="Название компании"></label>
            <label><span>Телефон</span><input name="lead_phone" data-survey-field inputmode="tel" placeholder="+7 ..."></label>
            <label><span>E-mail</span><input name="lead_email" data-survey-field type="email" placeholder="mail@company.ru"></label>
            <label><span>Количество лебёдок</span><input name="batch_qty" data-survey-field type="number" min="1" placeholder="1"></label>
            <label><span>Желаемый срок</span><input name="desired_date" data-survey-field type="date"></label>
            <label><span>Комментарий</span><textarea name="lead_comment" data-survey-field placeholder="Что важно учесть в предложении"></textarea></label>
          </div>
        </section>

        <section class="engineering-intro" id="engineering-intro"><div><span class="optional-label">Необязательно для первого обращения</span><h2>Расширенный инженерный опросник</h2><p>Текст полей перенесён из переведённого опросника заказчика; зачёркнутые пункты исключены. Эскизы взяты из оригинального TDNA Traction Survey. Неизвестные значения можно оставить пустыми.</p></div><button type="button" class="server-link" id="open-engineering">Развернуть техническую часть</button></section>
        <div id="engineering-sections">{''.join(group_cards)}</div>

        <section class="commercial-block">
          <span class="section-kicker">Коммерческий запрос и поставка</span>
          <h2>Индивидуальное ценовое предложение</h2>
          <p>Запрос на индивидуальное ценовое предложение в зависимости от количества партии лебёдок и сроков производства.</p>
          <div class="commercial-actions">
            <label class="survey-field"><span>Количество партии</span><input type="number" min="1" name="commercial_batch_qty" data-survey-field placeholder="Например, 4"></label>
            <label class="survey-field"><span>Нужен срок производства к дате</span><input type="date" name="commercial_due_date" data-survey-field></label>
          </div>
        </section>

        <div class="survey-actions"><button class="cta" type="submit">Отправить запрос →</button><button class="server-link" type="button" id="save-now">Сохранить и продолжить позже</button><a class="server-link" href="/">Отмена</a></div>
      </form>
    </main>
    <div class="survey-lightbox" id="survey-lightbox" aria-hidden="true"><div class="survey-lightbox-card"><div class="survey-lightbox-top"><span id="survey-lightbox-caption">Инженерная схема</span><button type="button" class="survey-lightbox-close" id="survey-lightbox-close">Закрыть ✕</button></div><img id="survey-lightbox-image" alt="Увеличенная инженерная схема Torin"></div></div>
    <script>
    (function(){{
      const productId={pid};
      const form=document.getElementById('survey-form');
      const status=document.getElementById('draft-status');
      const tokenField=document.getElementById('draft-token');
      const key='liftorg-survey-{pid}';
      const url=new URL(location.href);
      let token=url.searchParams.get('draft')||localStorage.getItem(key+'-token');
      if(!token){{ token=(crypto.randomUUID?crypto.randomUUID():('draft-'+Date.now()+'-'+Math.random().toString(36).slice(2))).replace(/[^A-Za-z0-9_-]/g,''); }}
      localStorage.setItem(key+'-token',token);
      if(!url.searchParams.get('draft')){{url.searchParams.set('draft',token);history.replaceState(null,'',url.pathname+'?'+url.searchParams.toString());}}
      tokenField.value=token;
      let timer=null;

      function collect(){{
        const out={{}};
        form.querySelectorAll('[data-survey-field]').forEach(el=>{{
          if(el.type==='checkbox') out[el.name]=el.checked?'Да':'';
          else out[el.name]=el.value;
        }});
        return out;
      }}
      function apply(data){{
        if(!data) return;
        Object.entries(data).forEach(([name,value])=>{{
          const el=form.elements[name]; if(!el) return;
          if(el.type==='checkbox') el.checked=(value==='Да'||value===true);
          else if(!el.value) el.value=value==null?'':value;
        }});
      }}
      function setStatus(text,cls){{ status.textContent=text; status.className='draft-status '+(cls||''); }}
      async function saveDraft(manual){{
        const data=collect();
        localStorage.setItem(key,JSON.stringify(data));
        setStatus(manual?'Сохраняю…':'Автосохранение…','');
        try{{
          const r=await fetch('/api/inquiry-drafts/'+encodeURIComponent(token),{{method:'PUT',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{product_id:productId,answers:data}})}});
          if(!r.ok) throw new Error('HTTP '+r.status);
          setStatus(manual?'Сохранено. Можно продолжить позже':'Черновик сохранён','saved');
        }}catch(e){{ setStatus('Сохранено в этом браузере','error'); }}
      }}
      const local=localStorage.getItem(key); if(local){{try{{apply(JSON.parse(local));setStatus('Черновик восстановлен','saved')}}catch(e){{}}}}
      fetch('/api/inquiry-drafts/'+encodeURIComponent(token)).then(r=>r.json()).then(d=>{{if(d.found){{apply(d.answers);setStatus('Черновик восстановлен','saved')}}}}).catch(()=>{{}});
      form.addEventListener('input',()=>{{clearTimeout(timer);timer=setTimeout(()=>saveDraft(false),850)}});
      form.addEventListener('change',()=>{{clearTimeout(timer);timer=setTimeout(()=>saveDraft(false),350)}});
      document.getElementById('save-now').addEventListener('click',()=>saveDraft(true));
      const lightbox=document.getElementById('survey-lightbox');
      const lightboxImg=document.getElementById('survey-lightbox-image');
      const lightboxCaption=document.getElementById('survey-lightbox-caption');
      function closeLightbox(){{ lightbox.classList.remove('open'); lightbox.setAttribute('aria-hidden','true'); lightboxImg.removeAttribute('src'); }}
      document.querySelectorAll('[data-survey-image]').forEach(btn=>btn.addEventListener('click',()=>{{lightboxImg.src=btn.dataset.surveyImage;lightboxCaption.textContent=btn.dataset.surveyCaption||'Инженерная схема';lightbox.classList.add('open');lightbox.setAttribute('aria-hidden','false');}}));
      document.getElementById('survey-lightbox-close').addEventListener('click',closeLightbox);
      lightbox.addEventListener('click',e=>{{if(e.target===lightbox)closeLightbox();}});
      document.addEventListener('keydown',e=>{{if(e.key==='Escape')closeLightbox();}});
      document.getElementById('open-engineering').addEventListener('click',()=>{{document.querySelectorAll('.survey-section').forEach(x=>x.open=true);document.querySelector('.survey-section')?.scrollIntoView({{behavior:'smooth',block:'start'}});}});
      form.addEventListener('submit',()=>{{localStorage.removeItem(key);localStorage.removeItem(key+'-token');fetch('/api/inquiry-drafts/'+encodeURIComponent(token),{{method:'DELETE',keepalive:true}}).catch(()=>{{}});}});
    }})();
    </script></body></html>'''


def render_order(p, qp, success=None):
    """Short commercial order request without forcing the engineering questionnaire."""
    pid=int(p.get('id') or 0)
    manufacturer=html.escape(str(p.get('manufacturer') or ''))
    model=html.escape(str(p.get('model') or ''))
    notice=''
    if success:
        notice=f'<div class="success-box"><b>Запрос {html.escape(success)} отправлен.</b><span>Менеджер свяжется с вами для уточнения цены, количества и сроков производства.</span></div>'
    return base_head('Заказать лебёдку — Liftorg')+f'''
    <style>
      .order-page{{max-width:980px;margin:28px auto;padding:0 22px 70px}}.order-hero{{display:grid;grid-template-columns:1fr 320px;gap:18px;align-items:start;margin:20px 0}}.order-hero h1{{font-size:38px;margin:6px 0 10px}}.order-hero p{{color:#667d8f;line-height:1.6}}.order-product{{border:1px solid #dce5eb;border-radius:16px;padding:18px;background:#f8fbfd}}.order-product small{{display:block;color:#758b9b;margin-bottom:5px}}.order-product b{{font-size:18px;color:#0a2a40}}.order-card{{border:1px solid #dce5eb;border-radius:18px;padding:22px;background:#fff}}.order-card h2{{margin:4px 0 5px}}.order-grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:18px}}.order-field{{display:flex;flex-direction:column;gap:6px;font-size:13px;font-weight:800;color:#526b7d}}.order-field input,.order-field textarea{{width:100%;min-height:44px;border:1px solid #cedae3;border-radius:10px;padding:10px 12px;color:#08243a;font:inherit;background:#fff}}.order-field textarea{{min-height:105px;resize:vertical}}.order-field.full{{grid-column:1/-1}}.commercial-note{{margin:18px 0;padding:16px 18px;border-radius:13px;background:#fff5ef;border:1px solid #ffd6c9;color:#713425;line-height:1.5}}.order-actions{{display:flex;gap:10px;margin-top:18px}}.order-actions>*{{flex:1}}.success-box{{display:flex;flex-direction:column;gap:4px;background:#ebf8ef;border:1px solid #bfe8cb;color:#185b2d;border-radius:14px;padding:16px 18px;margin:14px 0}}@media(max-width:720px){{.order-hero{{grid-template-columns:1fr}}.order-grid{{grid-template-columns:1fr}}.order-field.full{{grid-column:auto}}.order-actions{{flex-direction:column}}}}
    </style>
    <main class="order-page">
      <a class="server-link" href="/product/{pid}">← К модели</a>
      <section class="order-hero">
        <div><span class="section-kicker">Коммерческий запрос и поставка</span><h1>Заказать лебёдку</h1><p>Для запроса цены не нужно заполнять технический опросный лист. Оставьте контактные данные, количество и желаемый срок — остальные детали менеджер уточнит отдельно.</p></div>
        <div class="order-product"><small>Выбранное исполнение</small><b>{manufacturer} {model}</b><small>Исполнение #{pid}</small></div>
      </section>
      {notice}
      <form method="post" class="order-card">
        <span class="section-kicker">Минимум данных для обращения</span><h2>Коммерческий запрос</h2>
        <div class="commercial-note">Запрос на индивидуальное ценовое предложение в зависимости от количества партии лебёдок и сроков производства.</div>
        <div class="order-grid">
          <label class="order-field"><span>Имя</span><input name="lead_name" required placeholder="Как к вам обращаться"></label>
          <label class="order-field"><span>Компания</span><input name="lead_company" placeholder="Название компании"></label>
          <label class="order-field"><span>Телефон</span><input name="lead_phone" inputmode="tel" placeholder="+7 ..."></label>
          <label class="order-field"><span>E-mail</span><input name="lead_email" type="email" placeholder="mail@company.ru"></label>
          <label class="order-field"><span>Количество партии</span><input name="commercial_batch_qty" type="number" min="1" required value="1"></label>
          <label class="order-field"><span>Желаемый срок производства</span><input name="commercial_due_date" type="date"></label>
          <label class="order-field full"><span>Комментарий</span><textarea name="lead_comment" placeholder="Дополнительные требования, город поставки, удобный способ связи"></textarea></label>
        </div>
        <div class="order-actions"><button class="cta" type="submit">Отправить запрос →</button><a class="server-link" href="/product/{pid}/inquiry">Заполнить опросный лист</a></div>
      </form>
    </main></body></html>'''
