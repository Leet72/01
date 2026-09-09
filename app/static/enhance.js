(() => {
  'use strict';
  const selected = new Map();
  const tray = document.getElementById('compare_tray_server');
  const text = document.getElementById('compare_text');
  const render = () => {
    if (!tray) return;
    tray.classList.toggle('active', selected.size > 0);
    if (text) text.textContent = `Выбрано: ${selected.size} из 4`;
    document.querySelectorAll('.compare-button').forEach(b => b.classList.toggle('is-selected', selected.has(Number(b.dataset.productId))));
  };
  document.addEventListener('click', e => {
    const b=e.target.closest('.compare-button');
    if (!b) return;
    const id=Number(b.dataset.productId); if (!id) return;
    if (selected.has(id)) selected.delete(id); else if (selected.size < 4) selected.set(id,b.dataset.model || String(id));
    render();
  });
  document.getElementById('compare_clear_server')?.addEventListener('click',()=>{selected.clear();render();});
  document.getElementById('compare_go')?.addEventListener('click',async()=>{
    if (selected.size < 2) { alert('Выберите минимум 2 модели'); return; }
    try {
      const r=await fetch('/api/compare',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ids:[...selected.keys()]})});
      const d=await r.json();
      const win=window.open('','_blank');
      const fields=d.fields||[], items=d.items||[];
      const esc=s=>String(s??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
      const val=(i,f)=>`${esc(i[f.key])}${f.unit?' '+esc(f.unit):''}`;
      const enriched=fields.map(f=>{const vv=items.map(i=>String(i[f.key]??''));return {...f,diff:new Set(vv).size>1};});
      const diff=enriched.filter(f=>f.diff);
      const makeRows=only=>enriched.filter(f=>!only||f.diff).map(f=>`<tr class="${f.diff?'diff':''}"><th>${esc(f.label)}</th>${items.map(i=>`<td>${val(i,f)}</td>`).join('')}</tr>`).join('');
      win.document.write(`<meta charset="utf-8"><title>Сравнение Liftorg</title><style>body{font:15px Arial;padding:28px;color:#08243a}button{padding:9px 12px;margin:0 6px 12px 0;border:1px solid #ccd8e0;border-radius:8px;background:#fff;font-weight:700}button.active{background:#08243a;color:#fff}table{border-collapse:collapse;width:100%}th,td{border:1px solid #ccd8e0;padding:12px;text-align:left}thead th{background:#f2f6f8}.diff td{background:#fff5d9;font-weight:700}p{color:#607687}</style><h1>Сравнение лебёдок</h1><p><b>Главные отличия:</b> ${diff.map(f=>esc(f.label)).join(', ')||'не найдены'}</p><button id="diff" class="active">Только отличия</button><button id="all">Все параметры</button><table><thead><tr><th>Параметр</th>${items.map(i=>`<th>${esc(i.manufacturer)}<br>${esc(i.model)}</th>`).join('')}</tr></thead><tbody id="rows">${makeRows(true)}</tbody></table><script>const rows=document.getElementById('rows'),d=document.getElementById('diff'),a=document.getElementById('all');d.onclick=()=>{rows.innerHTML=${JSON.stringify(makeRows(true))};d.className='active';a.className=''};a.onclick=()=>{rows.innerHTML=${JSON.stringify(makeRows(false))};a.className='active';d.className=''}</script>`); win.document.close();
    } catch(e) { alert('Не удалось открыть сравнение'); }
  });
})();
