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
      const rows=fields.map(f=>`<tr><th>${esc(f.label)}</th>${items.map(i=>`<td>${esc(i[f.key])} ${esc(f.unit||'')}</td>`).join('')}</tr>`).join('');
      win.document.write(`<meta charset="utf-8"><title>Сравнение Liftorg</title><style>body{font:15px Arial;padding:28px;color:#08243a}table{border-collapse:collapse;width:100%}th,td{border:1px solid #ccd8e0;padding:12px;text-align:left}thead th{background:#f2f6f8}</style><h1>Сравнение лебёдок</h1><table><thead><tr><th>Параметр</th>${items.map(i=>`<th>${esc(i.manufacturer)}<br>${esc(i.model)}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table>`); win.document.close();
    } catch(e) { alert('Не удалось открыть сравнение'); }
  });
})();
