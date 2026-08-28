from __future__ import annotations

import json
import math
import os
import sqlite3
import secrets
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, Query, Depends, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv("CATALOG_DB", str(ROOT / "storage" / "catalog.db")))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
security = HTTPBasic()
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-me")
MANUFACTURER_PASSWORD = os.getenv("MANUFACTURER_PASSWORD", "Liftorg-Manufacturer-2026")
MANUFACTURER_USERS = {"nidec":"Nidec", "sicor":"Sicor", "torindrive":"Torindrive"}

def admin_auth():
    # TEST MODE: admin access without password. Re-enable auth before production.
    return "admin"

def manufacturer_auth(credentials: HTTPBasicCredentials = Depends(security)):
    manufacturer = MANUFACTURER_USERS.get(credentials.username.lower())
    pass_ok = secrets.compare_digest(credentials.password, MANUFACTURER_PASSWORD)
    if not manufacturer or not pass_ok:
        raise HTTPException(status_code=401, detail="Неверный доступ производителя", headers={"WWW-Authenticate": "Basic"})
    return manufacturer

def db_conn():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db_conn() as con:
        con.execute("CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, active INTEGER NOT NULL DEFAULT 1, payload TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        con.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, payload TEXT NOT NULL, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        con.execute("""CREATE TABLE IF NOT EXISTS attributes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            data_type TEXT NOT NULL DEFAULT 'text',
            unit TEXT,
            filter_type TEXT NOT NULL DEFAULT 'exact',
            options TEXT,
            is_filterable INTEGER NOT NULL DEFAULT 0,
            is_card_visible INTEGER NOT NULL DEFAULT 0,
            is_compare_visible INTEGER NOT NULL DEFAULT 0,
            is_required INTEGER NOT NULL DEFAULT 0,
            sort_order INTEGER NOT NULL DEFAULT 500,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS product_attribute_values (
            product_id INTEGER NOT NULL,
            attribute_id INTEGER NOT NULL,
            value TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(product_id,attribute_id)
        )""")

        con.execute("""CREATE TABLE IF NOT EXISTS inquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number TEXT UNIQUE,
            status TEXT NOT NULL DEFAULT 'new',
            product_id INTEGER,
            manufacturer TEXT,
            model TEXT,
            product_snapshot TEXT NOT NULL,
            filter_snapshot TEXT NOT NULL,
            answers TEXT NOT NULL,
            quote_snapshot TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        con.execute("CREATE INDEX IF NOT EXISTS idx_inquiries_status ON inquiries(status)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_inquiries_product ON inquiries(product_id)")
        con.execute("""CREATE TABLE IF NOT EXISTS inquiry_drafts (
            token TEXT PRIMARY KEY,
            product_id INTEGER NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        con.execute("CREATE INDEX IF NOT EXISTS idx_inquiry_drafts_product ON inquiry_drafts(product_id)")
        con.execute("""CREATE TABLE IF NOT EXISTS media_assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scope_type TEXT NOT NULL CHECK(scope_type IN ('family','model','execution')),
            manufacturer TEXT NOT NULL,
            family TEXT,
            model TEXT,
            product_id INTEGER,
            media_kind TEXT NOT NULL DEFAULT 'photo' CHECK(media_kind IN ('photo','drawing','document')),
            url TEXT NOT NULL,
            title TEXT,
            is_primary INTEGER NOT NULL DEFAULT 0,
            sort_order INTEGER NOT NULL DEFAULT 100,
            source TEXT NOT NULL DEFAULT 'admin',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        con.execute("CREATE INDEX IF NOT EXISTS idx_media_scope ON media_assets(scope_type,manufacturer,family,model,product_id)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_media_kind ON media_assets(media_kind,is_primary,sort_order)")
        count = con.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        if count == 0:
            seed = json.loads((ROOT / "data" / "products_full.json").read_text(encoding="utf-8"))
            for item in seed:
                item = dict(item)
                item.pop("id", None)
                con.execute("INSERT INTO products(active,payload) VALUES(1,?)", (json.dumps(item, ensure_ascii=False),))

def load_products(include_inactive: bool = False):
    sql = "SELECT id, active, payload FROM products" + ("" if include_inactive else " WHERE active=1") + " ORDER BY id"
    with db_conn() as con:
        rows = con.execute(sql).fetchall()
    out=[]
    for row in rows:
        p=json.loads(row["payload"]); p["id"]=row["id"]; p["active"]=bool(row["active"]); out.append(p)
    return out

def refresh_products():
    global PRODUCTS
    PRODUCTS = load_products(False)

init_db()
PRODUCTS: list[dict[str, Any]] = load_products(False)

MEDIA_DIR = ROOT / "app" / "static" / "media-library"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)


def media_family(manufacturer: Any, model: Any) -> str:
    """Stable engineering media family used only for inheritance, never for selection."""
    mfr = str(manufacturer or "").strip().lower()
    mdl = re.sub(r"\s+", "", str(model or "").upper())
    known = {
        "nidec": ["WJC", "WE", "WR", "VL"],
        "sicor": ["MR12C", "SG48"],
        "torindrive": ["GTW10X", "GTW9S", "ER1L", "ERSC"],
    }
    for prefix in known.get(mfr, []):
        if mdl.startswith(prefix):
            return prefix
    match = re.match(r"[A-ZА-Я]+[A-ZА-Я0-9]*", mdl)
    return match.group(0) if match else (mdl.split("-")[0] if mdl else "OTHER")


def _media_row_dict(r: sqlite3.Row) -> dict[str, Any]:
    d = dict(r)
    d["is_primary"] = bool(d.get("is_primary"))
    return d


def load_media_assets() -> list[dict[str, Any]]:
    with db_conn() as con:
        rows=con.execute("SELECT * FROM media_assets ORDER BY is_primary DESC,sort_order,id").fetchall()
    return [_media_row_dict(r) for r in rows]

MEDIA_ASSETS: list[dict[str, Any]] = []

def refresh_media():
    global MEDIA_ASSETS
    MEDIA_ASSETS = load_media_assets()


def resolve_media(p: dict[str, Any], include_documents: bool = True) -> list[dict[str, Any]]:
    """Resolve media with priority execution > model > family, without duplicate URLs."""
    pid = int(p.get("id") or 0)
    manufacturer = str(p.get("manufacturer") or "")
    model = str(p.get("model") or "")
    family = media_family(manufacturer, model)
    rows=[]
    for asset in MEDIA_ASSETS:
        if asset.get("manufacturer") != manufacturer:
            continue
        st=asset.get("scope_type")
        if st=="execution" and int(asset.get("product_id") or 0)==pid:
            priority=1
        elif st=="model" and asset.get("model")==model:
            priority=2
        elif st=="family" and asset.get("family")==family:
            priority=3
        else:
            continue
        rows.append((priority, asset))
    rows.sort(key=lambda z:(z[0], 0 if z[1].get("is_primary") else 1, int(z[1].get("sort_order") or 100), int(z[1].get("id") or 0)))
    out=[]; seen=set()
    for _, d0 in rows:
        d=dict(d0)
        if not include_documents and d.get("media_kind")=="document":
            continue
        if d.get("url") in seen:
            continue
        seen.add(d.get("url")); out.append(d)
    legacy = p.get("image_ref") or p.get("image_url") or p.get("photo_url")
    if legacy and legacy not in seen:
        out.append({"id":None,"scope_type":"legacy","manufacturer":manufacturer,"family":family,"model":model,"product_id":pid,"media_kind":"photo","url":legacy,"title":"Фото из исходной карточки","is_primary":not any(x.get("is_primary") for x in out),"sort_order":999,"source":"legacy"})
    return out


def attach_media(p: dict[str, Any]) -> dict[str, Any]:
    q=dict(p)
    media=resolve_media(q)
    q["media_family"] = media_family(q.get("manufacturer"), q.get("model"))
    q["media"] = media
    visual = next((x for x in media if x.get("media_kind")=="photo" and x.get("is_primary")), None) or next((x for x in media if x.get("media_kind")=="photo"), None)
    if visual:
        q["image_ref"] = visual.get("url")
    q["primary_image"] = visual.get("url") if visual else None
    return q


def bootstrap_legacy_media() -> int:
    """Promote existing family images into media library without changing product payloads."""
    changed=0
    with db_conn() as con:
        existing=con.execute("SELECT COUNT(*) FROM media_assets").fetchone()[0]
        if existing:
            return 0
        rows=con.execute("SELECT id,payload FROM products ORDER BY id").fetchall()
        seen=set()
        for r in rows:
            d=json.loads(r["payload"])
            url=d.get("image_ref") or d.get("image_url") or d.get("photo_url")
            if not url:
                continue
            mfr=str(d.get("manufacturer") or "")
            fam=media_family(mfr,d.get("model"))
            key=(mfr,fam,url)
            if key in seen:
                continue
            seen.add(key)
            con.execute("INSERT INTO media_assets(scope_type,manufacturer,family,media_kind,url,title,is_primary,sort_order,source) VALUES('family',?,?,?,?,?,1,100,'legacy-bootstrap')",(mfr,fam,'photo',url,f"{mfr} {fam} — основное фото"))
            changed += 1
        # Existing deployment keeps ten verified family files in /static/winches.
        # Bootstrap them even when historical payloads do not contain image_ref.
        known_files={
            ("Nidec","VL"):"nidec_vl.jpg", ("Nidec","WE"):"nidec_we.jpg",
            ("Nidec","WJC"):"nidec_wjc.jpg", ("Nidec","WR"):"nidec_wr.jpg",
            ("Sicor","MR12C"):"sicor_mr12c.jpg", ("Sicor","SG48"):"sicor_sg48.jpg",
            ("Torindrive","ER1L"):"torin_er1l.webp", ("Torindrive","ERSC"):"torin_ersc.png",
            ("Torindrive","GTW10X"):"torin_gtw10x.webp", ("Torindrive","GTW9S"):"torin_gtw9s.webp",
        }
        for (mfr,fam),filename in known_files.items():
            path=ROOT/"app"/"static"/"winches"/filename
            if not path.exists():
                continue
            url=f"/static/winches/{filename}"
            key=(mfr,fam,url)
            if key in seen:
                continue
            seen.add(key)
            con.execute("INSERT INTO media_assets(scope_type,manufacturer,family,media_kind,url,title,is_primary,sort_order,source) VALUES('family',?,?,?,?,?,1,100,'legacy-files-bootstrap')",(mfr,fam,'photo',url,f"{mfr} {fam} — основное фото"))
            changed += 1
    return changed

MEDIA_BOOTSTRAPPED = bootstrap_legacy_media()
refresh_media()

app = FastAPI(title="Liftorg B2B Engineering Catalog", version="4.4.10")
app.add_middleware(GZipMiddleware, minimum_size=800)
app.mount("/static", StaticFiles(directory=ROOT / "app" / "static"), name="static")
app.mount("/react-assets", StaticFiles(directory=ROOT / "app" / "react_dist"), name="react-assets")

# Диапазоны подтверждены в актуальном файле заказчика
# DOC-20260823-WA0001.xlsx, лист «Фильтры поиска и подбора лебедок».
# Границы включительные: скорость 1.0 м/с попадает и в 0.5–1.0, и в 1.0–1.6.
WINCH_TYPES = [
    "Редукторная",
    "Безредукторная таблетка",
    "Безредукторная объёмная таблетка",
    "Безредукторная бочонок",
]

SPEED_RANGES = [
    {"min": 0.25, "max": 0.5, "label": "0,25–0,5 м/с"},
    {"min": 0.5, "max": 1.0, "label": "0,5–1,0 м/с"},
    {"min": 1.0, "max": 1.6, "label": "1,0–1,6 м/с"},
    {"min": 1.6, "max": 2.0, "label": "1,6–2,0 м/с"},
    {"min": 2.0, "max": 4.0, "label": "2,0–4,0 м/с"},
    {"min": 4.0, "max": 8.0, "label": "4,0–8,0 м/с"},
]

# Диапазоны мощности из того же актуального листа заказчика.
# Границы также включительные: 3.5 кВт относится и к 2.5–3.5, и к 3.5–4.5.
POWER_RANGES = [
    {"min": 0.0, "max": 2.5, "label": "до 2,5 кВт"},
    {"min": 2.5, "max": 3.5, "label": "2,5–3,5 кВт"},
    {"min": 3.5, "max": 4.5, "label": "3,5–4,5 кВт"},
    {"min": 4.5, "max": 5.5, "label": "4,5–5,5 кВт"},
    {"min": 5.5, "max": 6.5, "label": "5,5–6,5 кВт"},
    {"min": 6.5, "max": 7.5, "label": "6,5–7,5 кВт"},
    {"min": 7.5, "max": 8.5, "label": "7,5–8,5 кВт"},
    {"min": 8.5, "max": 9.5, "label": "8,5–9,5 кВт"},
    {"min": 9.5, "max": 10.5, "label": "9,5–10,5 кВт"},
    {"min": 10.5, "max": 11.5, "label": "10,5–11,5 кВт"},
    {"min": 11.5, "max": 12.5, "label": "11,5–12,5 кВт"},
    {"min": 12.5, "max": 13.5, "label": "12,5–13,5 кВт"},
    {"min": 13.5, "max": 14.5, "label": "13,5–14,5 кВт"},
    {"min": 14.5, "max": 15.5, "label": "14,5–15,5 кВт"},
    {"min": 15.5, "max": 16.5, "label": "15,5–16,5 кВт"},
    {"min": 16.5, "max": 17.5, "label": "16,5–17,5 кВт"},
    {"min": 17.5, "max": 18.0, "label": "17,5–18,0 кВт"},
    # В исходной базе есть более мощные исполнения. Эти укрупнённые интервалы
    # оставлены только чтобы такие позиции не выпадали из тестовой версии.
    {"min": 18.0, "max": 25.0, "label": "18–25 кВт"},
    {"min": 25.0, "max": 35.0, "label": "25–35 кВт"},
    {"min": 35.0, "max": 50.0, "label": "35–50 кВт"},
    {"min": 50.0, "max": 75.0, "label": "50–75 кВт"},
    {"min": 75.0, "max": 110.0, "label": "75–110 кВт"},
]

CANTILEVER_LIMITS = [
    {"value": 3000, "label": "до 3 т"},
    {"value": 3500, "label": "до 3,5 т"},
    {"value": 4500, "label": "до 4,5 т"},
    {"value": 6000, "label": "до 6 т"},
]

LIFT_HEIGHT_LIMITS = [
    {"value": 30, "label": "до 30 м"},
    {"value": 50, "label": "до 50 м"},
    {"value": 60, "label": "до 60 м"},
    {"value": 70, "label": "до 70 м"},
]

ENCODER_TYPES = ["Инкрементальный", "Абсолютный", "Нет"]
VFD_OPTIONS = ["Да", "Нет"]
GROOVE_SHAPES = ["U-образная", "V-образная"]
UNDERCUT_ANGLES = {"U-образная": [90, 95, 100, 105], "V-образная": [45]}
BRAKE_VOLTAGES = ["AC 110", "AC 220", "DC 110", "DC 220"]
PLACEMENT_TYPES = ["В машинном помещении", "Без машинного помещения"]



def unique(field: str):
    vals = {p.get(field) for p in PRODUCTS if p.get(field) not in (None, "", [])}
    return sorted(vals, key=lambda x: (str(type(x)), x if isinstance(x, (int, float)) else str(x)))


def unique_nested(field: str):
    vals = set()
    for p in PRODUCTS:
        for x in p.get(field) or []:
            vals.add(x)
    return sorted(vals)



def _fmt_ssr(v):
    if v in (None, ""):
        return "—"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).replace(".", ",")


def _card_ssr(x):
    import html as _h
    mid=int(x.get("id") or 0)
    mfr=_h.escape(str(x.get("manufacturer") or "Производитель"))
    model=_h.escape(str(x.get("model") or "Без модели"))
    wtype=_h.escape(str(x.get("winch_type") or "Тип не уточнён"))
    susp=", ".join(map(str,x.get("suspensions") or [])) or "—"
    ropes=", ".join(map(str,x.get("rope_counts") or [])) or "—"
    rd=", ".join(_fmt_ssr(v) for v in (x.get("rope_diameters_mm") or [])) or "—"
    groove=_h.escape(str(x.get("groove_shape_normalized") or "—"))
    brake=_h.escape(str(x.get("brake_voltage_normalized") or "—"))
    placement=_h.escape(str(x.get("placement_type_normalized") or "—"))
    source_row=_fmt_ssr(x.get("source_row"))
    parts=[]
    parts.append(f'<article class="card" data-product-id="{mid}">')
    parts.append(f'<div class="card__top"><div><div class="card__mfr">{mfr}</div><h3>{model}</h3><div class="model-type">{wtype}</div></div><span class="match-badge">Подходит</span></div>')
    parts.append('<div class="specs">')
    specs=[
      ("Грузоподъёмность", f"{_fmt_ssr(x.get('capacity_kg'))} кг"),
      ("Скорость", f"{_fmt_ssr(x.get('speed_m_s'))} м/с"),
      ("Мощность", f"{_fmt_ssr(x.get('power_kw'))} кВт"),
      ("Количество скоростей", _fmt_ssr(x.get('speed_count_normalized') if x.get('speed_count_normalized') is not None else x.get('speed_count'))),
      ("Подвес", susp),("КВШ", f"{_fmt_ssr(x.get('sheave_diameter_mm'))} мм"),
      ("Канаты", f"{ropes} × {rd} мм"),
      ("Консольная нагрузка", f"{_fmt_ssr(x.get('max_cantilever_load_kg'))} кг"),
      ("Высота подъёма", f"{_fmt_ssr(x.get('max_lift_height_m'))} м"),
      ("Ручей / угол", f"{groove} / {_fmt_ssr(x.get('undercut_angle_normalized'))}°"),
      ("Тормоз", brake),("Включений/час", _fmt_ssr(x.get('starts_per_hour'))),
      ("Масса", f"{_fmt_ssr(x.get('weight_kg'))} кг"),("Размещение", placement)]
    for a,b in specs:
        parts.append(f'<div class="spec"><small>{_h.escape(str(a))}</small><b>{_h.escape(str(b))}</b></div>')
    parts.append('</div>')
    parts.append(f'<div class="card__footer"><span class="card__note">Данные из актуального Excel · строка {source_row}</span><div class="card__actions"><button class="ghost-button compare-button" data-compare-id="{mid}" data-action="compare" data-product-id="{mid}">Сравнить</button><button class="details-btn" data-action="details" data-product-id="{mid}">Подробнее</button><a class="details-btn" href="/product/{mid}/inquiry">Заполнить опросный лист</a><a class="request-price" href="/product/{mid}/order">Заказать лебёдку</a><button class="use" data-action="choose" data-product-id="{mid}">Выбрать →</button></div></div>')
    parts.append('</article>')
    return ''.join(parts)

@app.get("/")
def index():
    return FileResponse(ROOT / "app" / "react_dist" / "index.html", headers={"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0"})

@app.get("/legacy", response_class=HTMLResponse)
def legacy_index(request: Request):
    from .server_ui import render_index
    html = render_index(request, {"search":search, "meta":meta})
    return HTMLResponse(html, headers={"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0"})

@app.get("/admin", response_class=HTMLResponse)
def admin_page(_: str = Depends(admin_auth)):
    return (ROOT / "app" / "static" / "admin.html").read_text(encoding="utf-8")

@app.get("/admin/product/{product_id}", response_class=HTMLResponse)
def admin_product_page(product_id: int, _: str = Depends(admin_auth)):
    # The editor reads ?id=... and opens the requested product automatically.
    return (ROOT / "app" / "static" / "admin.html").read_text(encoding="utf-8")

@app.get("/admin/media", response_class=HTMLResponse)
def admin_media_page(_: str = Depends(admin_auth)):
    return (ROOT / "app" / "static" / "media.html").read_text(encoding="utf-8")

@app.get("/admin/attributes", response_class=HTMLResponse)
def admin_attributes_page(_: str = Depends(admin_auth)):
    return (ROOT / "app" / "static" / "attributes.html").read_text(encoding="utf-8")

@app.get("/admin/audit", response_class=HTMLResponse)
def admin_audit_page(_: str = Depends(admin_auth)):
    return (ROOT / "app" / "static" / "audit.html").read_text(encoding="utf-8")

@app.get("/admin/inquiries", response_class=HTMLResponse)
def admin_inquiries_page(_: str = Depends(admin_auth)):
    return (ROOT / "app" / "static" / "inquiries.html").read_text(encoding="utf-8")

@app.get("/manufacturer", response_class=HTMLResponse)
def manufacturer_page(_: str = Depends(manufacturer_auth)):
    return (ROOT / "app" / "static" / "manufacturer.html").read_text(encoding="utf-8")


def normalize_yes_no(v: Any) -> str | None:
    if v is True:
        return "Да"
    if v is False:
        return "Нет"
    if isinstance(v, str):
        t = v.strip().lower()
        if t in {"да", "yes", "true", "1", "+"}:
            return "Да"
        if t in {"нет", "no", "false", "0", "-"}:
            return "Нет"
    return None


def normalize_groove_shape(v: Any) -> str | None:
    if not v:
        return None
    t = str(v).upper().replace("Ё", "Е")
    if "U" in t or "У-ОБРАЗ" in t or "У ОБРАЗ" in t:
        return "U-образная"
    if "V" in t or "V-ОБРАЗ" in t:
        return "V-образная"
    return None


def parse_angle(v: Any) -> int | None:
    if v is None:
        return None
    import re
    m = re.search(r"(45|90|95|100|105)", str(v))
    return int(m.group(1)) if m else None


def normalize_brake_voltage(p: dict[str, Any]) -> str | None:
    raw = f"{p.get('brake_current_type') or ''} {p.get('brake_voltage') or ''}".lower()
    import re
    current = None
    if "постоян" in raw or "dc" in raw:
        current = "DC"
    elif "перемен" in raw or "ac" in raw:
        current = "AC"
    m = re.search(r"(?<!\d)(110|220)(?!\d)", raw)
    return f"{current} {m.group(1)}" if current and m else None



def placement_type_of(p: dict[str, Any]) -> str | None:
    """Тип размещения по подтверждённому инженерному правилу Заказчика 26.08.2026.

    Приоритет:
    1. Явно сохранённое/импортированное значение MR/MRL всегда имеет приоритет.
    2. Все безредукторные «бочонки» -> без машинного помещения (MRL).
    3. Плоские таблетки WE 06, WE 10, WE 20 -> MRL.
    4. Серия WJC-T по уточнению заказчика 28.08.2026 — объёмная таблетка, но установка MRL.
    5. Остальные безредукторные таблетки считаются объёмными -> машинное помещение (MR).

    Для типов, которые инженер пока не классифицировал (например отдельные Torindrive
    с общим типом «Безредукторная»), значение не придумывается и остаётся UNKNOWN.
    """
    raw = " ".join(str(p.get(k) or "") for k in (
        "placement_type", "placement", "machine_room_type", "mr_mrl", "installation_type"
    )).strip().lower()
    if raw:
        compact = raw.replace("ё", "е")
        if "mrl" in compact or "без машин" in compact:
            return "Без машинного помещения"
        if "mr" in compact or "машинн" in compact:
            return "В машинном помещении"

    winch_type = str(p.get("winch_type") or "").strip()
    model = re.sub(r"\s+", "", str(p.get("model") or "").upper())

    if winch_type == "Безредукторная бочонок":
        return "Без машинного помещения"

    if winch_type == "Безредукторная объёмная таблетка":
        if model.startswith("WJC") and bool(re.search(r"-T(?:$|[^A-Z0-9])", model)):
            return "Без машинного помещения"
        return "В машинном помещении"

    if winch_type == "Безредукторная таблетка":
        is_flat_we = model.startswith(("WE06-", "WE10-", "WE20-"))
        if is_flat_we:
            return "Без машинного помещения"
        return "В машинном помещении"

    return None


def placement_rule_source(p: dict[str, Any]) -> str | None:
    """Человекочитаемый источник классификации для аудита и админки."""
    if p.get("placement_type_source"):
        return str(p.get("placement_type_source"))
    raw = " ".join(str(p.get(k) or "") for k in (
        "placement_type", "placement", "machine_room_type", "mr_mrl", "installation_type"
    )).strip()
    if raw:
        return "Явное значение в данных/админке"
    winch_type = str(p.get("winch_type") or "").strip()
    model = re.sub(r"\s+", "", str(p.get("model") or "").upper())
    if winch_type == "Безредукторная бочонок":
        return "Правило 26.08.2026: все бочонки = MRL"
    if winch_type == "Безредукторная объёмная таблетка":
        if model.startswith("WJC") and bool(re.search(r"-T(?:$|[^A-Z0-9])", model)):
            return "Правило 28.08.2026: WJC-T = объёмная таблетка, MRL"
        return "Правило 26.08.2026: объёмная таблетка = MR"
    if winch_type == "Безредукторная таблетка":
        if model.startswith(("WE06-", "WE10-", "WE20-")):
            return "Правило 26.08.2026: плоская таблетка = MRL"
        return "Правило 26.08.2026: объёмная таблетка = MR"
    return None


def correct_wjc_t_classification_in_db() -> int:
    """Коррекция заказчика 28.08.2026: WJC-T — объёмная таблетка + MRL.

    Исправляет старую автоматическую классификацию, где WJC-T ошибочно
    называлась плоской таблеткой. Технические характеристики не меняются.
    """
    changed = 0
    with db_conn() as con:
        rows = con.execute("SELECT id,payload FROM products").fetchall()
        for row in rows:
            data = json.loads(row["payload"])
            model = re.sub(r"\s+", "", str(data.get("model") or "").upper())
            is_wjc_t = model.startswith("WJC") and bool(re.search(r"-T(?:$|[^A-Z0-9])", model))
            if not is_wjc_t:
                continue
            expected_type = "Безредукторная объёмная таблетка"
            expected_place = "Без машинного помещения"
            expected_source = "Правило 28.08.2026: WJC-T = объёмная таблетка, MRL"
            if (data.get("winch_type") == expected_type and
                data.get("placement_type") == expected_place and
                data.get("placement_type_source") == expected_source):
                continue
            data["winch_type"] = expected_type
            data["placement_type"] = expected_place
            data["placement_type_source"] = expected_source
            con.execute(
                "UPDATE products SET payload=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (json.dumps(data, ensure_ascii=False), row["id"]),
            )
            changed += 1
    if changed:
        refresh_products()
    return changed


def apply_placement_rules_to_db() -> int:
    """Материализует подтверждённую классификацию в SQLite для карточек/админки.

    Уже заданные вручную значения не перезаписываются. Для автоматически
    классифицированных строк сохраняется источник правила.
    """
    changed = 0
    with db_conn() as con:
        rows = con.execute("SELECT id,payload FROM products").fetchall()
        for row in rows:
            data = json.loads(row["payload"])
            if data.get("placement_type") not in (None, ""):
                continue
            derived = placement_type_of(data)
            source = placement_rule_source(data)
            if not derived or not source:
                continue
            data["placement_type"] = derived
            data["placement_type_source"] = source
            con.execute(
                "UPDATE products SET payload=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (json.dumps(data, ensure_ascii=False), row["id"]),
            )
            changed += 1
    if changed:
        refresh_products()
    return changed


# Коррекция WJC-T выполняется раньше общего правила размещения.
WJC_T_CORRECTIONS_APPLIED = correct_wjc_t_classification_in_db()
# Миграция безопасно выполняется при старте и сохраняет классификацию в восстановленной БД.
PLACEMENT_RULES_APPLIED = apply_placement_rules_to_db()

def encoder_type_of(p: dict[str, Any]) -> str | None:
    raw = " ".join(str(p.get(k) or "") for k in ("encoder_type", "encoder", "encoder_brand")).lower()
    if "инкрем" in raw:
        return "Инкрементальный"
    if "абсолют" in raw:
        return "Абсолютный"
    if p.get("encoder") is False:
        return "Нет"
    return None



# Полная трассировка исходных Excel-полей -> нормализованная БД / фильтры / карточка.
RAW_FIELD_MAP = {
    "Модель": ("model", "Карточка + поиск"),
    "Грузоподъёмность": ("capacity_kg", "Фильтр + карточка"),
    "Скорость": ("speed_m_s", "Диапазонный фильтр + карточка"),
    "Количество скоростей": ("speed_count", "Фильтр + инженерное правило"),
    "Наличие ЧП в системе управления": ("vfd", "Фильтр + карточка"),
    "Название производителя ЧП": ("vfd_brand", "Карточка / техданные"),
    "Наличие энкодера": ("encoder", "Фильтр + карточка"),
    "Название производителя энкодера": ("encoder_brand", "Карточка / техданные"),
    "Мощность": ("power_kw", "Диапазонный фильтр + карточка"),
    "Мощность кВт": ("power_kw", "Диапазонный фильтр + карточка"),
    "Максимальная консольная нагрузка, кг": ("max_cantilever_load_kg", "Фильтр + карточка"),
    "Высота подъёма": ("max_lift_height_m", "Фильтр + карточка"),
    "Кратность подвески": ("suspensions", "Фильтр + карточка"),
    "Форма ручья": ("groove_shape", "Фильтр + карточка"),
    "Угол подреза": ("undercut_angle", "Зависимый фильтр + карточка"),
    "Диаметр шкива, мм": ("sheave_diameter_mm", "Фильтр + карточка"),
    "Количество канатов": ("rope_counts", "Фильтр + карточка"),
    "Диаметр канатов": ("rope_diameters_mm", "Фильтр + карточка"),
    "Число включений в час": ("starts_per_hour", "Фильтр + карточка"),
    "Напряжение питание тормоза Тип тока AC/DC": ("brake_voltage", "Фильтр + карточка"),
    "Вес, кг": ("weight_kg", "Фильтр + карточка"),
    "Передаточное число": ("gear_ratio", "БД + карточка; фильтр пока скрыт"),
    "Дистан-ционное расцепление": ("remote_release", "БД + карточка; фильтр пока скрыт"),
    "Номинальный ток": ("nominal_current_a", "Техническая карточка"),
    "Номинальная скорость, об/мин": ("nominal_rpm", "Техническая карточка"),
    "Номинальная скорость, об/мин r.p.m.": ("nominal_rpm", "Техническая карточка"),
    "Номинальная скорость, об/мин rmp": ("nominal_rpm", "Техническая карточка"),
    "Частота, Гц": ("frequency_hz", "Техническая карточка"),
    "Крутящий момент, Н·м": ("torque_nm", "Техническая карточка"),
    "Шаг канавок КВШ, мм": ("groove_pitch_mm", "Техническая карточка"),
    "Угол раскрытия канавки": ("groove_open_angle", "Техническая карточка"),
    "Маховик": ("handwheel", "Техническая карточка"),
    "Момент инерции, кг·м²": ("inertia_kgm2", "Техническая карточка"),
    "W1": ("w1", "Технические размеры"), "W1/L1?": ("w1", "Технические размеры"),
    "W2": ("w2", "Технические размеры"), "W2/L2?": ("w2", "Технические размеры"),
    "h2": ("h2", "Технические размеры"), "h2/L3?": ("h2", "Технические размеры"),
    "d4": ("d4", "Технические размеры"), "d4/L4?": ("d4", "Технические размеры"),
    "d5": ("d5", "Технические размеры"), "d5/L5?": ("d5", "Технические размеры"),
    "Тип намотки обычная/перекрестная": ("winding_type", "Техническая карточка"),
    "поставка с рамой": ("frame_supply", "БД + фильтр"),
    "код рамы": ("frame_code", "Техническая карточка"),
    "duty cycle": ("duty_cycle", "Техническая карточка"),
    "Изображение": ("image_ref", "Карточка / изображение"),
    "Тип лебедки": ("winch_type", "Фильтр + карточка"),
}

def source_audit_data():
    raw_keys=set(); raw_counts={}
    for p in load_products(True):
        for k,v in (p.get("raw") or {}).items():
            raw_keys.add(k)
            if v not in (None, "", []): raw_counts[k]=raw_counts.get(k,0)+1
    rows=[]
    for key in sorted(raw_keys):
        mapped=RAW_FIELD_MAP.get(key)
        rows.append({"source_field":key,"db_field":mapped[0] if mapped else None,"usage":mapped[1] if mapped else "Сохранено в raw; требуется решение по нормализации","status":"mapped" if mapped else "raw_only","filled_products":raw_counts.get(key,0)})
    return rows

@app.get("/api/admin/audit")
def admin_audit(_: str=Depends(admin_auth)):
    wb=json.loads((ROOT/"data"/"workbook_reference.json").read_text(encoding="utf-8"))
    calc=json.loads((ROOT/"data"/"calculator_reference.json").read_text(encoding="utf-8"))
    audit=source_audit_data()
    return {"products_total":len(load_products(True)),"active_products":len(PRODUCTS),"source_sheets":[{"name":k,"rows":len(v)} for k,v in wb.items()],"raw_fields_total":len(audit),"mapped_fields":sum(x["status"]=="mapped" for x in audit),"raw_only_fields":sum(x["status"]=="raw_only" for x in audit),"fields":audit,"calculator_source":calc.get("source_file","Калькулятор-2.xlsx")}

@app.get("/api/admin/source-sheets")
def admin_source_sheets(_: str=Depends(admin_auth)):
    wb=json.loads((ROOT/"data"/"workbook_reference.json").read_text(encoding="utf-8"))
    return [{"name":k,"rows":len(v)} for k,v in wb.items()]

@app.get("/api/admin/source-sheet")
def admin_source_sheet(name:str, _: str=Depends(admin_auth)):
    wb=json.loads((ROOT/"data"/"workbook_reference.json").read_text(encoding="utf-8"))
    if name not in wb: raise HTTPException(404,"Лист не найден")
    return {"name":name,"rows":wb[name]}

@app.get("/api/meta")
def meta():
    brake_values = sorted({x for p in PRODUCTS if (x := normalize_brake_voltage(p))})
    groove_values = sorted({x for p in PRODUCTS if (x := normalize_groove_shape(p.get("groove_shape")))})
    angle_values = sorted({x for p in PRODUCTS if (x := parse_angle(p.get("undercut_angle")))})
    return {
        "count": len(PRODUCTS),
        "manufacturers": unique("manufacturer"),
        "winch_types": WINCH_TYPES,
        "capacities": unique("capacity_kg"),
        "speed_ranges": SPEED_RANGES,
        "power_ranges": POWER_RANGES,
        "suspensions": unique_nested("suspensions"),
        "speed_counts": [1, 2],
        "speed_count_rule": {"gearless": 1, "geared": [1, 2]},
        "vfd_options": VFD_OPTIONS,
        "encoder_types": ENCODER_TYPES,
        "cantilever_limits": CANTILEVER_LIMITS,
        "lift_height_limits": LIFT_HEIGHT_LIMITS,
        "groove_shapes": GROOVE_SHAPES if groove_values else GROOVE_SHAPES,
        "undercut_angles": UNDERCUT_ANGLES,
        "sheave_diameters": unique("sheave_diameter_mm"),
        "rope_counts": unique_nested("rope_counts"),
        "rope_diameters": unique_nested("rope_diameters_mm"),
        "starts_per_hour": unique("starts_per_hour"),
        "brake_voltages": BRAKE_VOLTAGES,
        "weights": unique("weight_kg"),
        "frame_options": ["Да", "Нет", "По запросу"],
        "remote_release_options": ["Да", "Нет", "По запросу"],
        "placement_types": PLACEMENT_TYPES,
        "data_coverage": {
            "max_lift_height": sum(p.get("max_lift_height_m") is not None for p in PRODUCTS),
            "vfd_explicit": sum(normalize_yes_no(p.get("vfd")) is not None for p in PRODUCTS),
            "encoder_type_explicit": sum(encoder_type_of(p) is not None for p in PRODUCTS),
            "brake_voltage": sum(normalize_brake_voltage(p) is not None for p in PRODUCTS),
            "placement_type": sum(placement_type_of(p) is not None for p in PRODUCTS),
            "frame_supply": sum(p.get("frame_supply") not in (None, "") for p in PRODUCTS),
            "remote_release": sum(p.get("remote_release") not in (None, "") for p in PRODUCTS),
            "gear_ratio": sum(p.get("gear_ratio") not in (None, "") for p in PRODUCTS),
        },
        "note": "v1.0: полный импорт актуального Excel: 838 исполнений, до 42 исходных полей на позицию, карточка с расширенными техданными и исходными значениями.",
    }



def eq_num(value, requested, tol=1e-6):
    if requested is None:
        return True
    if value is None:
        return False
    return abs(float(value) - float(requested)) <= tol


def in_inclusive_range(value, min_value, max_value, tol=1e-9):
    if min_value is None and max_value is None:
        return True
    if value is None:
        return False
    v = float(value)
    if min_value is not None and v < float(min_value) - tol:
        return False
    if max_value is not None and v > float(max_value) + tol:
        return False
    return True


@app.get("/api/search")
def search(
    manufacturer: str | None = None,
    winch_type: str | None = None,
    capacity_kg: float | None = None,
    speed_min: float | None = None,
    speed_max: float | None = None,
    suspension: str | None = None,
    speed_count: int | None = None,
    vfd: str | None = None,
    encoder_type: str | None = None,
    power_min: float | None = None,
    power_max: float | None = None,
    cantilever_required_kg: float | None = None,
    lift_height_required_m: float | None = None,
    groove_shape: str | None = None,
    undercut_angle: int | None = None,
    sheave_diameter_mm: float | None = None,
    rope_count: int | None = None,
    rope_diameter_mm: float | None = None,
    starts_per_hour: int | None = None,
    brake_voltage: str | None = None,
    weight_kg: float | None = None,
    placement_type: str | None = None,
    q: str | None = None,
    frame_supply: str | None = None,
    remote_release: str | None = None,
    include_unknowns: bool = True,
    group_models: bool = True,
    limit: int = Query(24, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Объяснимый инженерный подбор.

    PASS  — известное значение соответствует требованию.
    UNKNOWN — в исходнике нет значения; модель не исключается, а требует уточнения.
    FAIL — известное значение противоречит требованию; модель исключается.
    """
    if speed_count is not None and speed_count not in (1, 2):
        return {"count":0,"total":0,"exact_total":0,"clarification_total":0,"items":[]}
    if winch_type in ("Безредукторная таблетка","Безредукторная объёмная таблетка","Безредукторная бочонок") and speed_count == 2:
        return {"count":0,"total":0,"exact_total":0,"clarification_total":0,"items":[]}

    def missing(v): return v is None or v == "" or v == []
    def ev(label, selected, actual, predicate, actual_label=None):
        if selected in (None, "", []): return None
        if missing(actual): return {"field":label,"state":"unknown","expected":str(selected),"actual":None}
        ok=bool(predicate(actual))
        return {"field":label,"state":"pass" if ok else "fail","expected":str(selected),"actual": actual_label(actual) if actual_label else str(actual)}

    results=[]; exact=0; clarify=0; excluded=0
    for p in PRODUCTS:
        checks=[]
        # q / manufacturer / type are catalog identity fields; missing is a hard mismatch only when a different known value exists.
        if q and q.lower() not in f"{p.get('manufacturer','')} {p.get('model','')} {p.get('identification_number','')}".lower():
            continue
        for check in [
            ev("Производитель", manufacturer, p.get("manufacturer"), lambda a:a==manufacturer),
            ev("Тип лебёдки", winch_type, p.get("winch_type"), lambda a:a==winch_type),
            ev("Грузоподъёмность", capacity_kg, p.get("capacity_kg"), lambda a:eq_num(a,capacity_kg), lambda a:f"{a} кг"),
            ev("Скорость", f"{speed_min}–{speed_max}" if speed_min is not None or speed_max is not None else None, p.get("speed_m_s"), lambda a:in_inclusive_range(a,speed_min,speed_max), lambda a:f"{a} м/с"),
            ev("Кратность подвески", suspension, p.get("suspensions"), lambda a:suspension in (a or []), lambda a:", ".join(map(str,a))),
            ev("Количество скоростей", speed_count, 1 if p.get("winch_type") in ("Безредукторная таблетка","Безредукторная объёмная таблетка","Безредукторная бочонок","Безредукторная") else p.get("speed_count"), lambda a:eq_num(a,speed_count)),
            ev("Наличие ЧП", vfd, normalize_yes_no(p.get("vfd")), lambda a:a==vfd),
            ev("Энкодер", encoder_type, encoder_type_of(p), lambda a:a==encoder_type),
            ev("Мощность", f"{power_min}–{power_max}" if power_min is not None or power_max is not None else None, p.get("power_kw"), lambda a:in_inclusive_range(a,power_min,power_max), lambda a:f"{a} кВт"),
            ev("Макс. консольная нагрузка", cantilever_required_kg, p.get("max_cantilever_load_kg"), lambda a:float(a)>=float(cantilever_required_kg), lambda a:f"{a} кг"),
            ev("Макс. высота подъёма", lift_height_required_m, p.get("max_lift_height_m"), lambda a:float(a)>=float(lift_height_required_m), lambda a:f"{a} м"),
            ev("Форма ручья", groove_shape, normalize_groove_shape(p.get("groove_shape")), lambda a:a==groove_shape),
            ev("Угол подреза", undercut_angle, parse_angle(p.get("undercut_angle")), lambda a:a==undercut_angle, lambda a:f"{a}°"),
            ev("Диаметр КВШ", sheave_diameter_mm, p.get("sheave_diameter_mm"), lambda a:eq_num(a,sheave_diameter_mm), lambda a:f"{a} мм"),
            ev("Количество канатов", rope_count, p.get("rope_counts"), lambda a:rope_count in (a or []), lambda a:", ".join(map(str,a))),
            ev("Диаметр каната", rope_diameter_mm, p.get("rope_diameters_mm"), lambda a:any(eq_num(x,rope_diameter_mm) for x in (a or [])), lambda a:", ".join(map(str,a))),
            ev("Включений/час", starts_per_hour, p.get("starts_per_hour"), lambda a:eq_num(a,starts_per_hour)),
            ev("Питание тормоза", brake_voltage, normalize_brake_voltage(p), lambda a:a==brake_voltage),
            ev("Масса", weight_kg, p.get("weight_kg"), lambda a:eq_num(a,weight_kg), lambda a:f"{a} кг"),
            ev("Тип размещения", placement_type, placement_type_of(p), lambda a:a==placement_type),
        ]:
            if check: checks.append(check)
        def ynlabel(v):
            if v is True: return "Да"
            if v is False: return "Нет"
            if v == "on_request": return "По запросу"
            return None
        for check in [
            ev("Поставка с рамой", frame_supply, ynlabel(p.get("frame_supply")), lambda a:a==frame_supply),
            ev("Дистанционное расцепление", remote_release, ynlabel(p.get("remote_release")), lambda a:a==remote_release),
        ]:
            if check: checks.append(check)
        fails=[c for c in checks if c["state"]=="fail"]
        unknown=[c for c in checks if c["state"]=="unknown"]
        passed=[c for c in checks if c["state"]=="pass"]
        if fails:
            excluded += 1
            continue
        status="needs_clarification" if unknown else "matched"
        if status=="matched": exact += 1
        else:
            clarify += 1
            if not include_unknowns: continue
        item={k:p.get(k) for k in ["id","source_sheet","source_row","manufacturer","model","identification_number","image_ref","winch_type","capacity_kg","speed_m_s","power_kw","speed_count","suspensions","sheave_diameter_mm","rope_counts","rope_diameters_mm","max_cantilever_load_kg","max_lift_height_m","groove_shape","undercut_angle","starts_per_hour","weight_kg","manufacturer_price_cny","manufacturer_currency"]}
        item["image_ref"] = attach_media(dict(p)).get("image_ref")
        item["media_family"] = media_family(p.get("manufacturer"),p.get("model"))
        item.update({
            "groove_shape_normalized":normalize_groove_shape(p.get("groove_shape")),
            "undercut_angle_normalized":parse_angle(p.get("undercut_angle")),
            "brake_voltage_normalized":normalize_brake_voltage(p),
            "placement_type_normalized":placement_type_of(p),
            "placement_type_source":placement_rule_source(p),
            "speed_count_normalized":1 if p.get("winch_type") in ("Безредукторная таблетка","Безредукторная объёмная таблетка","Безредукторная бочонок","Безредукторная") else p.get("speed_count"),
            "match_status":status,
            "match_summary":{"passed":len(passed),"unknown":len(unknown),"selected":len(checks)},
            "match_checks":checks,
            "clarifications":[c["field"] for c in unknown],
        })
        results.append(item)
    # Сначала полностью подтверждённые, затем кандидаты с минимальным числом неизвестных.
    results.sort(key=lambda x:(0 if x["match_status"]=="matched" else 1, x["match_summary"]["unknown"], -x["match_summary"]["passed"], str(x.get("manufacturer") or ""), str(x.get("model") or "")))

    execution_total=len(results)
    execution_exact_total=exact
    execution_clarification_total=clarify

    if group_models:
        grouped={}
        order=[]
        for item in results:
            key=(str(item.get("manufacturer") or "").strip(), str(item.get("model") or "").strip())
            if key not in grouped:
                grouped[key]={
                    **item,
                    "execution_count":0,
                    "execution_ids":[],
                    "matched_execution_count":0,
                    "clarification_execution_count":0,
                    "capacities":[],
                    "speeds":[],
                    "powers":[],
                    "sheave_diameters":[],
                    "weights":[],
                }
                order.append(key)
            g=grouped[key]
            g["execution_count"] += 1
            g["execution_ids"].append(item["id"])
            if item["match_status"]=="matched": g["matched_execution_count"] += 1
            else: g["clarification_execution_count"] += 1
            for field,target in [("capacity_kg","capacities"),("speed_m_s","speeds"),("power_kw","powers"),("sheave_diameter_mm","sheave_diameters"),("weight_kg","weights")]:
                v=item.get(field)
                if v not in (None,"") and v not in g[target]: g[target].append(v)
            # If a later execution is fully confirmed while representative is only a candidate, promote it.
            if g.get("match_status")!="matched" and item.get("match_status")=="matched":
                keep={k:g[k] for k in ["execution_count","execution_ids","matched_execution_count","clarification_execution_count","capacities","speeds","powers","sheave_diameters","weights"]}
                g.clear(); g.update(item); g.update(keep)
        results=[grouped[k] for k in order]
        for g in results:
            g["is_model_group"]=True
            g["match_status"]="matched" if g["matched_execution_count"] else "needs_clarification"
        exact=sum(1 for g in results if g["match_status"]=="matched")
        clarify=sum(1 for g in results if g["match_status"]=="needs_clarification")

    total=len(results); items=results[offset:offset+limit]
    return {
        "count":len(items),"total":total,"exact_total":exact,"clarification_total":clarify,
        "execution_total":execution_total,"execution_exact_total":execution_exact_total,
        "execution_clarification_total":execution_clarification_total,"excluded_total":excluded,
        "offset":offset,"limit":limit,"has_more":offset+len(items)<total,"grouped_by_model":bool(group_models),"items":items
    }



@app.get("/api/model-groups/{product_id}")
def model_group(product_id:int):
    by_id={int(p["id"]):p for p in PRODUCTS}
    base=by_id.get(int(product_id))
    if not base:
        raise HTTPException(404,"Позиция не найдена")
    manufacturer=base.get("manufacturer")
    model=base.get("model")
    executions=[public_product(dict(p)) for p in PRODUCTS if p.get("manufacturer")==manufacturer and p.get("model")==model]
    executions.sort(key=lambda x:(float(x.get("capacity_kg") or 0),float(x.get("speed_m_s") or 0),float(x.get("power_kw") or 0),int(x.get("id") or 0)))
    return {
        "manufacturer":manufacturer,"model":model,"image_ref":attach_media(dict(base)).get("image_ref"),"media":resolve_media(dict(base)),
        "winch_type":base.get("winch_type"),"execution_count":len(executions),"executions":executions
    }

@app.get("/product/{product_id}", response_class=HTMLResponse)
def product_page(product_id:int):
    from .server_ui import render_product
    with db_conn() as con:
        row=con.execute("SELECT id,active,payload FROM products WHERE id=?",(product_id,)).fetchone()
    if not row or not row["active"]: raise HTTPException(404,"Лебёдка не найдена")
    p=json.loads(row["payload"]); p["id"]=row["id"]; p=attach_media(p)
    return HTMLResponse(render_product(p), headers={"Cache-Control":"no-store"})

@app.get("/product/{product_id}/inquiry", response_class=HTMLResponse)
def inquiry_page(product_id:int, request:Request):
    from .server_ui import render_inquiry
    with db_conn() as con:
        row=con.execute("SELECT id,active,payload FROM products WHERE id=?",(product_id,)).fetchone()
    if not row or not row["active"]: raise HTTPException(404,"Лебёдка не найдена")
    p=json.loads(row["payload"]); p["id"]=row["id"]
    return HTMLResponse(render_inquiry(p,QUESTIONNAIRE_FIELDS,request.query_params), headers={"Cache-Control":"no-store"})

@app.post("/product/{product_id}/inquiry", response_class=HTMLResponse)
async def inquiry_submit(product_id:int, request:Request):
    from .server_ui import render_inquiry
    from urllib.parse import parse_qs
    raw=(await request.body()).decode("utf-8",errors="replace"); form={k:(v[-1] if v else "") for k,v in parse_qs(raw,keep_blank_values=True).items()}
    with db_conn() as con:
        row=con.execute("SELECT id,active,payload FROM products WHERE id=?",(product_id,)).fetchone()
        if not row or not row["active"]: raise HTTPException(404,"Лебёдка не найдена")
        p=json.loads(row["payload"]); p["id"]=row["id"]
        cur=con.execute("""INSERT INTO inquiries(status,product_id,manufacturer,model,product_snapshot,filter_snapshot,answers,quote_snapshot) VALUES('new',?,?,?,?,?,?,?)""",(product_id,p.get("manufacturer"),p.get("model"),json.dumps(p,ensure_ascii=False),json.dumps(dict(request.query_params),ensure_ascii=False),json.dumps(form,ensure_ascii=False),None))
        iid=cur.lastrowid; number=f"LFT-{datetime.now().strftime('%Y%m%d')}-{iid:05d}"; con.execute("UPDATE inquiries SET number=? WHERE id=?",(number,iid))
    return HTMLResponse(render_inquiry(p,QUESTIONNAIRE_FIELDS,request.query_params,success=number), headers={"Cache-Control":"no-store"})

@app.get("/product/{product_id}/order", response_class=HTMLResponse)
def order_page(product_id:int, request:Request):
    from .server_ui import render_order
    with db_conn() as con:
        row=con.execute("SELECT id,active,payload FROM products WHERE id=?",(product_id,)).fetchone()
    if not row or not row["active"]: raise HTTPException(404,"Лебёдка не найдена")
    p=json.loads(row["payload"]); p["id"]=row["id"]
    return HTMLResponse(render_order(p,request.query_params), headers={"Cache-Control":"no-store"})

@app.post("/product/{product_id}/order", response_class=HTMLResponse)
async def order_submit(product_id:int, request:Request):
    from .server_ui import render_order
    from urllib.parse import parse_qs
    raw=(await request.body()).decode("utf-8",errors="replace")
    form={k:(v[-1] if v else "") for k,v in parse_qs(raw,keep_blank_values=True).items()}
    form["request_kind"]="direct_order"
    with db_conn() as con:
        row=con.execute("SELECT id,active,payload FROM products WHERE id=?",(product_id,)).fetchone()
        if not row or not row["active"]: raise HTTPException(404,"Лебёдка не найдена")
        p=json.loads(row["payload"]); p["id"]=row["id"]
        cur=con.execute("""INSERT INTO inquiries(status,product_id,manufacturer,model,product_snapshot,filter_snapshot,answers,quote_snapshot) VALUES('new',?,?,?,?,?,?,?)""",(product_id,p.get("manufacturer"),p.get("model"),json.dumps(p,ensure_ascii=False),json.dumps(dict(request.query_params),ensure_ascii=False),json.dumps(form,ensure_ascii=False),None))
        iid=cur.lastrowid; number=f"LFT-{datetime.now().strftime('%Y%m%d')}-{iid:05d}"; con.execute("UPDATE inquiries SET number=? WHERE id=?",(number,iid))
    return HTMLResponse(render_order(p,request.query_params,success=number), headers={"Cache-Control":"no-store"})

@app.get("/api/products/{product_id}")
def product(product_id: int):
    with db_conn() as con:
        row=con.execute("SELECT id,active,payload FROM products WHERE id=?",(product_id,)).fetchone()
    if not row or not row["active"]:
        return {"error":"not_found"}
    p=json.loads(row["payload"]); p["id"]=row["id"]; p["active"]=True; p=attach_media(p)
    p["placement_type_normalized"] = placement_type_of(p)
    p["placement_type_source"] = placement_rule_source(p)
    return p



# --- Engineering comparison / media -----------------------------------------
# Comparison fields are fixed by the customer's engineering requirement.
COMPARE_FIELDS = [
    {"key":"power_kw", "label":"Мощность", "unit":"кВт"},
    {"key":"max_cantilever_load_kg", "label":"Максимальная консольная нагрузка", "unit":"кг"},
    {"key":"undercut_angle", "label":"Угол подреза", "unit":""},
    {"key":"sheave_diameter_mm", "label":"Диаметр КВШ", "unit":"мм"},
    {"key":"weight_kg", "label":"Масса", "unit":"кг"},
]

def public_product(p: dict[str, Any]) -> dict[str, Any]:
    # Exclude internal commercial fields from engineer-facing endpoints.
    hidden={"manufacturer_price_cny","manufacturer_currency","manufacturer_price_note","manufacturer_price_updated_at"}
    enriched=attach_media(p)
    return {k:v for k,v in enriched.items() if k not in hidden}

class ComparePayload(BaseModel):
    ids: list[int] = Field(min_length=2, max_length=4)

@app.post("/api/compare")
def compare_products(body: ComparePayload):
    by_id={int(p["id"]):p for p in PRODUCTS}
    items=[]
    for pid in body.ids:
        p=by_id.get(int(pid))
        if not p:
            raise HTTPException(404, f"Позиция {pid} не найдена")
        items.append(public_product(p))
    return {"fields":COMPARE_FIELDS,"items":items,"count":len(items)}

@app.get("/api/compare/config")
def compare_config():
    return {"max_items":4,"min_items":2,"fields":COMPARE_FIELDS}


class ProductPayload(BaseModel):
    data: dict[str, Any]

@app.get("/api/admin/products")
def admin_products(q: str | None=None, limit: int=Query(50,ge=1,le=500), offset: int=Query(0,ge=0), _: str=Depends(admin_auth)):
    items=load_products(True)
    if q:
        qq=q.lower()
        items=[p for p in items if qq in f"{p.get('manufacturer','')} {p.get('model','')} {p.get('identification_number','')}".lower()]
    total=len(items)
    for p in items:
        p["placement_type_normalized"] = placement_type_of(p)
        p["placement_type_source"] = placement_rule_source(p)
    return {"total":total,"items":items[offset:offset+limit],"offset":offset,"limit":limit}

@app.get("/api/admin/products/{product_id}")
def admin_product(product_id:int, _: str=Depends(admin_auth)):
    with db_conn() as con:
        row=con.execute("SELECT id,active,payload FROM products WHERE id=?",(product_id,)).fetchone()
    if not row: raise HTTPException(404,"Позиция не найдена")
    p=json.loads(row["payload"]); p["id"]=row["id"]; p["active"]=bool(row["active"]); p["placement_type_normalized"]=placement_type_of(p); p["placement_type_source"]=placement_rule_source(p); return p

@app.post("/api/admin/products")
def admin_create(body: ProductPayload, _: str=Depends(admin_auth)):
    data=dict(body.data); data.pop("id",None); data.pop("active",None)
    if data.get("manufacturer_price_cny") is not None: data["manufacturer_price_updated_at"] = datetime.now(timezone.utc).isoformat()
    data.setdefault("raw", {})
    with db_conn() as con:
        cur=con.execute("INSERT INTO products(active,payload) VALUES(1,?)",(json.dumps(data,ensure_ascii=False),))
        pid=cur.lastrowid
    refresh_products()
    return {"ok":True,"id":pid}

@app.put("/api/admin/products/{product_id}")
def admin_update(product_id:int, body: ProductPayload, _: str=Depends(admin_auth)):
    data=dict(body.data); active=1 if data.pop("active",True) else 0; data.pop("id",None); data.setdefault("raw",{})
    with db_conn() as con:
        prev=con.execute("SELECT payload FROM products WHERE id=?",(product_id,)).fetchone()
        if prev:
            prev_data=json.loads(prev["payload"])
            if data.get("manufacturer_price_cny") != prev_data.get("manufacturer_price_cny"):
                data["manufacturer_price_updated_at"] = datetime.now(timezone.utc).isoformat()
        cur=con.execute("UPDATE products SET active=?,payload=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(active,json.dumps(data,ensure_ascii=False),product_id))
        if cur.rowcount==0: raise HTTPException(404,"Позиция не найдена")
    refresh_products(); return {"ok":True,"id":product_id}

@app.delete("/api/admin/products/{product_id}")
def admin_delete(product_id:int, _: str=Depends(admin_auth)):
    with db_conn() as con:
        cur=con.execute("UPDATE products SET active=0,updated_at=CURRENT_TIMESTAMP WHERE id=?",(product_id,))
        if cur.rowcount==0: raise HTTPException(404,"Позиция не найдена")
    refresh_products(); return {"ok":True}

@app.post("/api/admin/products/{product_id}/restore")
def admin_restore(product_id:int, _: str=Depends(admin_auth)):
    with db_conn() as con:
        cur=con.execute("UPDATE products SET active=1,updated_at=CURRENT_TIMESTAMP WHERE id=?",(product_id,))
        if cur.rowcount==0: raise HTTPException(404,"Позиция не найдена")
    refresh_products(); return {"ok":True}

@app.post("/api/admin/reseed")
def admin_reseed(_: str=Depends(admin_auth)):
    seed=json.loads((ROOT/"data"/"products_full.json").read_text(encoding="utf-8"))
    with db_conn() as con:
        con.execute("DELETE FROM products")
        for item in seed:
            item=dict(item); item.pop("id",None)
            con.execute("INSERT INTO products(active,payload) VALUES(1,?)",(json.dumps(item,ensure_ascii=False),))
    refresh_products(); return {"ok":True,"count":len(PRODUCTS)}




# -------------------- Медиабиблиотека ----------------------------------------
class MediaAssetPayload(BaseModel):
    scope_type: Literal["family","model","execution"]
    manufacturer: str
    family: str | None = None
    model: str | None = None
    product_id: int | None = None
    media_kind: Literal["photo","drawing","document"] = "photo"
    url: str
    title: str | None = None
    is_primary: bool = False
    sort_order: int = 100


def validate_media_scope(data: dict[str, Any]):
    st=data.get("scope_type")
    if st=="execution" and not data.get("product_id"):
        raise HTTPException(422,"Для уровня исполнения нужен product_id")
    if st=="model" and not data.get("model"):
        raise HTTPException(422,"Для уровня модели нужна model")
    if st=="family" and not data.get("family"):
        raise HTTPException(422,"Для уровня семейства нужна family")


def clear_primary_for_scope(con, data, exclude_id=None):
    if not data.get("is_primary") or data.get("media_kind")!="photo": return
    sql="UPDATE media_assets SET is_primary=0,updated_at=CURRENT_TIMESTAMP WHERE media_kind='photo' AND scope_type=? AND manufacturer=?"
    args=[data["scope_type"],data["manufacturer"]]
    if data["scope_type"]=="execution": sql+=" AND product_id=?"; args.append(data.get("product_id"))
    elif data["scope_type"]=="model": sql+=" AND model=?"; args.append(data.get("model"))
    else: sql+=" AND family=?"; args.append(data.get("family"))
    if exclude_id: sql+=" AND id<>?"; args.append(exclude_id)
    con.execute(sql,args)

@app.get("/api/admin/media")
def admin_media(product_id:int|None=None, manufacturer:str|None=None, model:str|None=None, family:str|None=None, _:str=Depends(admin_auth)):
    context=None
    if product_id is not None:
        with db_conn() as con: row=con.execute("SELECT payload FROM products WHERE id=?",(product_id,)).fetchone()
        if not row: raise HTTPException(404,"Позиция не найдена")
        p=json.loads(row["payload"]); p["id"]=product_id
        context={"manufacturer":str(p.get("manufacturer") or ""),"model":str(p.get("model") or ""),"family":media_family(p.get("manufacturer"),p.get("model"))}
    items=[]
    for x in MEDIA_ASSETS:
        if context:
            if x.get("manufacturer")!=context["manufacturer"]: continue
            st=x.get("scope_type")
            if st=="execution" and int(x.get("product_id") or 0)!=product_id: continue
            if st=="model" and x.get("model")!=context["model"]: continue
            if st=="family" and x.get("family")!=context["family"]: continue
        if manufacturer and x.get("manufacturer")!=manufacturer: continue
        if model and x.get("model")!=model: continue
        if family and x.get("family")!=family: continue
        items.append(dict(x))
    return {"total":len(items),"items":items}

@app.get("/api/products/{product_id}/media")
def product_media(product_id:int):
    with db_conn() as con: row=con.execute("SELECT id,active,payload FROM products WHERE id=?",(product_id,)).fetchone()
    if not row or not row["active"]: raise HTTPException(404,"Позиция не найдена")
    p=json.loads(row["payload"]); p["id"]=row["id"]
    return {"product_id":product_id,"family":media_family(p.get("manufacturer"),p.get("model")),"items":resolve_media(p)}

@app.post("/api/admin/media")
def create_media(body:MediaAssetPayload, _:str=Depends(admin_auth)):
    d=body.model_dump(); validate_media_scope(d)
    if not d.get("family") and d.get("model"): d["family"]=media_family(d.get("manufacturer"),d.get("model"))
    with db_conn() as con:
        clear_primary_for_scope(con,d)
        cur=con.execute("INSERT INTO media_assets(scope_type,manufacturer,family,model,product_id,media_kind,url,title,is_primary,sort_order,source) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(d["scope_type"],d["manufacturer"],d.get("family"),d.get("model"),d.get("product_id"),d["media_kind"],d["url"],d.get("title"),int(d["is_primary"]),d["sort_order"],"admin"))
    refresh_media()
    return {"ok":True,"id":cur.lastrowid}

@app.put("/api/admin/media/{media_id}")
def update_media(media_id:int, body:MediaAssetPayload, _:str=Depends(admin_auth)):
    d=body.model_dump(); validate_media_scope(d)
    if not d.get("family") and d.get("model"): d["family"]=media_family(d.get("manufacturer"),d.get("model"))
    with db_conn() as con:
        clear_primary_for_scope(con,d,media_id)
        cur=con.execute("UPDATE media_assets SET scope_type=?,manufacturer=?,family=?,model=?,product_id=?,media_kind=?,url=?,title=?,is_primary=?,sort_order=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(d["scope_type"],d["manufacturer"],d.get("family"),d.get("model"),d.get("product_id"),d["media_kind"],d["url"],d.get("title"),int(d["is_primary"]),d["sort_order"],media_id))
        if cur.rowcount==0: raise HTTPException(404,"Медиа не найдено")
    refresh_media()
    return {"ok":True}

@app.delete("/api/admin/media/{media_id}")
def delete_media(media_id:int, _:str=Depends(admin_auth)):
    with db_conn() as con:
        row=con.execute("SELECT url,source FROM media_assets WHERE id=?",(media_id,)).fetchone()
        if not row: raise HTTPException(404,"Медиа не найдено")
        con.execute("DELETE FROM media_assets WHERE id=?",(media_id,))
    # Uploaded files are intentionally retained on disk to avoid breaking historical snapshots.
    refresh_media()
    return {"ok":True}

@app.post("/api/admin/media/upload")
async def upload_media(file:UploadFile=File(...), scope_type:str=Form(...), manufacturer:str=Form(...), family:str|None=Form(None), model:str|None=Form(None), product_id:int|None=Form(None), media_kind:str=Form("photo"), title:str|None=Form(None), is_primary:bool=Form(False), sort_order:int=Form(100), _:str=Depends(admin_auth)):
    if scope_type not in {"family","model","execution"}: raise HTTPException(422,"Неверный уровень")
    if media_kind not in {"photo","drawing","document"}: raise HTTPException(422,"Неверный тип медиа")
    data={"scope_type":scope_type,"manufacturer":manufacturer,"family":family,"model":model,"product_id":product_id,"media_kind":media_kind,"is_primary":is_primary}
    validate_media_scope(data)
    allowed={".jpg",".jpeg",".png",".webp",".gif",".svg",".pdf"}
    ext=Path(file.filename or "").suffix.lower()
    if ext not in allowed: raise HTTPException(415,"Разрешены JPG, PNG, WEBP, GIF, SVG и PDF")
    raw=await file.read()
    if len(raw)>20*1024*1024: raise HTTPException(413,"Файл больше 20 МБ")
    safe=re.sub(r"[^a-zA-Z0-9_.-]+","-",Path(file.filename or ("media"+ext)).name).strip("-._") or ("media"+ext)
    stamp=datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    target=MEDIA_DIR/f"{stamp}-{safe}"
    target.write_bytes(raw)
    url=f"/static/media-library/{target.name}"
    fam=family or (media_family(manufacturer,model) if model else None)
    d={**data,"family":fam,"url":url,"title":title or Path(file.filename or "").stem,"sort_order":sort_order}
    with db_conn() as con:
        clear_primary_for_scope(con,d)
        cur=con.execute("INSERT INTO media_assets(scope_type,manufacturer,family,model,product_id,media_kind,url,title,is_primary,sort_order,source) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(scope_type,manufacturer,fam,model,product_id,media_kind,url,d["title"],int(is_primary),sort_order,"upload"))
    refresh_media()
    return {"ok":True,"id":cur.lastrowid,"url":url}

@app.get("/api/admin/media/context/{product_id}")
def media_context(product_id:int, _:str=Depends(admin_auth)):
    with db_conn() as con: row=con.execute("SELECT id,payload FROM products WHERE id=?",(product_id,)).fetchone()
    if not row: raise HTTPException(404,"Позиция не найдена")
    p=json.loads(row["payload"]); p["id"]=row["id"]
    return {"product_id":product_id,"manufacturer":p.get("manufacturer"),"model":p.get("model"),"family":media_family(p.get("manufacturer"),p.get("model")),"resolved":resolve_media(p)}

# -------------------- Динамические характеристики каталога --------------------
class AttributePayload(BaseModel):
    code: str
    name: str
    data_type: Literal["text","number","integer","boolean","enum","multienum","range"] = "text"
    unit: str | None = None
    filter_type: Literal["exact","range","max","min","enum","multienum","boolean","reference"] = "exact"
    options: list[str] = Field(default_factory=list)
    is_filterable: bool = False
    is_card_visible: bool = False
    is_compare_visible: bool = False
    is_required: bool = False
    sort_order: int = 500

@app.get("/api/admin/attributes")
def list_attributes(_:str=Depends(admin_auth)):
    with db_conn() as con: rows=con.execute("SELECT * FROM attributes ORDER BY sort_order,id").fetchall()
    return {"items":[{**dict(r),"options":json.loads(r["options"] or "[]")} for r in rows]}

@app.post("/api/admin/attributes")
def create_attribute(body:AttributePayload, _:str=Depends(admin_auth)):
    with db_conn() as con:
        try:
            cur=con.execute("INSERT INTO attributes(code,name,data_type,unit,filter_type,options,is_filterable,is_card_visible,is_compare_visible,is_required,sort_order) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(body.code.strip(),body.name.strip(),body.data_type,body.unit,body.filter_type,json.dumps(body.options,ensure_ascii=False),int(body.is_filterable),int(body.is_card_visible),int(body.is_compare_visible),int(body.is_required),body.sort_order))
        except sqlite3.IntegrityError: raise HTTPException(409,"Код характеристики уже существует")
    return {"ok":True,"id":cur.lastrowid}

@app.put("/api/admin/attributes/{attribute_id}")
def update_attribute(attribute_id:int, body:AttributePayload, _:str=Depends(admin_auth)):
    with db_conn() as con:
        cur=con.execute("UPDATE attributes SET code=?,name=?,data_type=?,unit=?,filter_type=?,options=?,is_filterable=?,is_card_visible=?,is_compare_visible=?,is_required=?,sort_order=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(body.code.strip(),body.name.strip(),body.data_type,body.unit,body.filter_type,json.dumps(body.options,ensure_ascii=False),int(body.is_filterable),int(body.is_card_visible),int(body.is_compare_visible),int(body.is_required),body.sort_order,attribute_id))
        if cur.rowcount==0: raise HTTPException(404,"Характеристика не найдена")
    return {"ok":True}

@app.delete("/api/admin/attributes/{attribute_id}")
def delete_attribute(attribute_id:int, _:str=Depends(admin_auth)):
    with db_conn() as con:
        con.execute("DELETE FROM product_attribute_values WHERE attribute_id=?",(attribute_id,)); con.execute("DELETE FROM attributes WHERE id=?",(attribute_id,))
    return {"ok":True}

class AttributeValuePayload(BaseModel): value: Any = None
@app.get("/api/admin/products/{product_id}/attributes")
def product_attributes(product_id:int, _:str=Depends(admin_auth)):
    with db_conn() as con:
        attrs=con.execute("SELECT * FROM attributes ORDER BY sort_order,id").fetchall(); vals={r["attribute_id"]:json.loads(r["value"]) if r["value"] else None for r in con.execute("SELECT * FROM product_attribute_values WHERE product_id=?",(product_id,)).fetchall()}
    return {"items":[{"attribute":{**dict(a),"options":json.loads(a["options"] or "[]")},"value":vals.get(a["id"])} for a in attrs]}
@app.put("/api/admin/products/{product_id}/attributes/{attribute_id}")
def set_product_attribute(product_id:int, attribute_id:int, body:AttributeValuePayload, _:str=Depends(admin_auth)):
    with db_conn() as con:
        con.execute("INSERT INTO product_attribute_values(product_id,attribute_id,value,updated_at) VALUES(?,?,?,CURRENT_TIMESTAMP) ON CONFLICT(product_id,attribute_id) DO UPDATE SET value=excluded.value,updated_at=CURRENT_TIMESTAMP",(product_id,attribute_id,json.dumps(body.value,ensure_ascii=False)))
    return {"ok":True}

@app.get("/api/products/{product_id}/custom-attributes")
def public_product_attributes(product_id:int):
    with db_conn() as con:
        rows=con.execute("SELECT a.*,v.value FROM attributes a JOIN product_attribute_values v ON v.attribute_id=a.id WHERE v.product_id=? ORDER BY a.sort_order,a.id",(product_id,)).fetchall()
    return {"items":[{"code":r["code"],"name":r["name"],"unit":r["unit"],"card":bool(r["is_card_visible"]),"compare":bool(r["is_compare_visible"]),"value":json.loads(r["value"]) if r["value"] else None} for r in rows]}


# -------------------- Кабинет производителя / цены --------------------
class ManufacturerPricePayload(BaseModel):
    price: float | None = Field(default=None, ge=0)
    currency: Literal["CNY","USD","EUR","RUB"] = "CNY"
    note: str | None = None

@app.get("/api/manufacturer/products")
def manufacturer_products(q:str|None=None, manufacturer:str=Depends(manufacturer_auth)):
    items=[p for p in load_products(True) if p.get("manufacturer")==manufacturer]
    if q:
        qq=q.lower(); items=[p for p in items if qq in f"{p.get('model','')} {p.get('identification_number','')}".lower()]
    return {"manufacturer":manufacturer,"total":len(items),"items":[{"id":p["id"],"active":p["active"],"model":p.get("model"),"identification_number":p.get("identification_number"),"capacity_kg":p.get("capacity_kg"),"speed_m_s":p.get("speed_m_s"),"manufacturer_price_cny":p.get("manufacturer_price_cny"),"manufacturer_currency":p.get("manufacturer_currency") or "CNY","manufacturer_price_note":p.get("manufacturer_price_note"),"manufacturer_price_updated_at":p.get("manufacturer_price_updated_at")} for p in items]}

@app.put("/api/manufacturer/products/{product_id}/price")
def manufacturer_set_price(product_id:int, body:ManufacturerPricePayload, manufacturer:str=Depends(manufacturer_auth)):
    with db_conn() as con:
        row=con.execute("SELECT payload FROM products WHERE id=?",(product_id,)).fetchone()
        if not row: raise HTTPException(404,"Позиция не найдена")
        data=json.loads(row["payload"])
        if data.get("manufacturer") != manufacturer: raise HTTPException(403,"Можно менять только свою номенклатуру")
        data["manufacturer_price_cny"]=body.price
        data["manufacturer_currency"]=body.currency
        data["manufacturer_price_note"]=body.note
        data["manufacturer_price_updated_at"]=datetime.now(timezone.utc).isoformat()
        con.execute("UPDATE products SET payload=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(json.dumps(data,ensure_ascii=False),product_id))
    refresh_products(); return {"ok":True,"updated_at":data["manufacturer_price_updated_at"]}


@app.get("/api/manufacturer/inquiries")
def manufacturer_inquiries(manufacturer:str=Depends(manufacturer_auth)):
    with db_conn() as con:
        rows=con.execute("SELECT id,number,status,model,answers,created_at FROM inquiries WHERE manufacturer=? ORDER BY id DESC",(manufacturer,)).fetchall()
    out=[]
    for r in rows:
        a=json.loads(r["answers"])
        company=a.get("Название компании Заказчика") or a.get("Customer /Покупатель") or "—"
        out.append({"id":r["id"],"number":r["number"],"status":r["status"],"model":r["model"],"company":company,"created_at":r["created_at"]})
    return {"manufacturer":manufacturer,"total":len(out),"items":out}

@app.get("/api/manufacturer/inquiries/{inquiry_id}")
def manufacturer_inquiry(inquiry_id:int, manufacturer:str=Depends(manufacturer_auth)):
    with db_conn() as con:
        r=con.execute("SELECT * FROM inquiries WHERE id=? AND manufacturer=?",(inquiry_id,manufacturer)).fetchone()
    if not r: raise HTTPException(404,"Запрос не найден")
    return {"id":r["id"],"number":r["number"],"status":r["status"],"model":r["model"],"created_at":r["created_at"],"answers":json.loads(r["answers"]),"filters":json.loads(r["filter_snapshot"])}

# -------------------- B2B опросный лист и запросы цены --------------------
QUESTIONNAIRE_SHEET = "Проект О.Л ВТМ + ФИЛЬТР"
QUESTIONNAIRE_HEADINGS = {1, 51, 57, 89, 97, 103, 121, 140}
QUESTIONNAIRE_SKIP = {151, 152, 153, 155}
QUESTIONNAIRE_GROUPS = [
    (2, 10, "Заказчик и проект"),
    (11, 30, "Параметры лифта и размещение"),
    (31, 50, "Лебёдка, привод и требования"),
    (52, 88, "Параметры подбора и карточки"),
    (90, 96, "Дополнительные расчётные параметры"),
    (98, 102, "Комплектация для расчёта"),
    (104, 139, "Монтаж, рама, отводные блоки и чертежи"),
    (141, 154, "Коммерческий запрос и поставка"),
]

QUESTIONNAIRE_OPTIONS = {
    54: ["Да", "Нет"], 60: WINCH_TYPES,
    61: ["Без машинного помещения", "Верхнее расположение", "Нижнее расположение", "В машинном помещении"],
    62: ["120", "160", "180"], 63: ["1:1", "2:1", "4:1"],
    67: ["1", "2"], 68: ["ABB", "Monarch", "KEP", "STEP", "Нет", "Другое"],
    70: ["Да", "Нет"], 73: ["Инкрементальный", "Абсолютный", "Нет", "Другое"],
    76: ["до 3 т", "до 3,5 т", "до 4,5 т", "до 6 т"],
    77: ["до 30 м", "до 50 м", "до 60 м", "до 70 м"],
    82: BRAKE_VOLTAGES, 85: ["Да", "Нет"], 86: ["Да", "Нет"],
    95: ["Да", "Нет"], 104: ["Да", "Нет"], 107: ["Правое", "Левое"],
    108: ["Да", "Нет"], 119: ["Да", "Нет"], 120: ["Оставить существующий", "Заменить на новый"],
    126: ["Да", "Нет"], 131: ["Готовые отверстия", "Предварительные отверстия"],
    145: ["100% предоплата", "50% предоплата / 50% перед отгрузкой", "100% перед отгрузкой", "100% после отгрузки, 30 дней"],
    150: ["Нет", "5%", "10%", "15%", "Другое"],
}

QUESTIONNAIRE_CHECKBOX_ROWS = {98,99,100,101,102}
QUESTIONNAIRE_TEXTAREA_ROWS = {42,43,44,49,50,57,87,89,92,118,127,140,144,154}

AUTO_FILTER_MAP = {
    60:"winch_type", 61:"placement_type", 62:"starts_per_hour", 63:"suspension",
    64:"capacity", 65:"speed", 67:"speed_count", 68:"vfd", 73:"encoder_type",
    74:"power", 76:"cantilever", 77:"lift_height", 78:"sheave", 79:"rope_count",
    80:"rope_diameter", 81:"groove_shape", 82:"brake_voltage", 84:"weight",
    85:"frame_supply", 86:"remote_release",
}
AUTO_PRODUCT_MAP = {
    58:"identification_number", 59:"manufacturer", 60:"winch_type", 61:"placement_type",
    62:"starts_per_hour", 63:"suspensions", 64:"capacity_kg", 65:"speed_m_s",
    67:"speed_count", 68:"vfd_brand", 73:"encoder_brand", 74:"power_kw",
    75:"gear_ratio", 76:"max_cantilever_load_kg", 77:"max_lift_height_m",
    78:"sheave_diameter_mm", 79:"rope_counts", 80:"rope_diameters_mm",
    81:"groove_shape", 82:"brake_voltage", 84:"weight_kg", 85:"frame_supply",
    86:"remote_release",
}


def _field_code(row: int) -> str:
    return f"q_{row}"


def _group_for_row(row: int) -> str:
    for a,b,name in QUESTIONNAIRE_GROUPS:
        if a <= row <= b:
            return name
    return "Дополнительные поля"


def _questionnaire_rows():
    wb = json.loads((ROOT / "data" / "workbook_reference.json").read_text(encoding="utf-8"))
    src = wb.get(QUESTIONNAIRE_SHEET, [])
    fields=[]
    for row, values in src:
        vals=[str(v).strip() for v in values if v not in (None, "")]
        if not vals or row in QUESTIONNAIRE_SKIP:
            continue
        label=vals[0]
        if row in QUESTIONNAIRE_HEADINGS:
            fields.append({"row":row,"code":_field_code(row),"label":label,"kind":"heading","group":_group_for_row(row)})
            continue
        kind="text"
        if row in QUESTIONNAIRE_CHECKBOX_ROWS: kind="checkbox"
        elif row in QUESTIONNAIRE_TEXTAREA_ROWS or len(label)>140: kind="textarea"
        elif row in QUESTIONNAIRE_OPTIONS: kind="select"
        elif any(x in label.lower() for x in ["дата", "date"]): kind="date"
        elif any(x in label.lower() for x in ["количество", "вес", "масса", "высота", "диаметр", "расстояние", "ширина", "толщина", "ускорение", "момент", "напряжение а"]): kind="number"
        f={"row":row,"code":_field_code(row),"label":label,"kind":kind,"group":_group_for_row(row),"source_sheet":QUESTIONNAIRE_SHEET}
        if row in QUESTIONNAIRE_OPTIONS: f["options"]=QUESTIONNAIRE_OPTIONS[row]
        if row in AUTO_FILTER_MAP: f["autofill_filter"]=AUTO_FILTER_MAP[row]
        if row in AUTO_PRODUCT_MAP: f["autofill_product"]=AUTO_PRODUCT_MAP[row]
        fields.append(f)
    return fields

QUESTIONNAIRE_FIELDS = _questionnaire_rows()
# --- TDNA survey v4.4 -------------------------------------------------------
# Source of truth: user-provided translated DOCX "для воплощения на сайте-1.docx"
# + TDNA Traction Survey PDF diagrams. Fully struck-through rows in the DOCX
# (project name, contract number, seismic execution, address, consultant) are
# intentionally excluded from the customer-facing engineering survey.
TDNA_SURVEY_SOURCE = "для воплощения на сайте-1.docx + TDNA Traction Survey.pdf"
TDNA_SURVEY_GROUPS = [
    "Основные параметры подбора",
    "Системные параметры (если известно)",
    "Комплектация для расчёта цены",
    "Данные для чертежа",
    "Отводной блок и компоновка",
    "Блоки / шкивы",
]
TDNA_SURVEY_FIELDS = [
    {"code":"tdna_floor_distance","label":"Расстояние между этажами, м","kind":"number","group":"Основные параметры подбора","help":"Укажите расстояние между соседними этажами в метрах, например 3,6 м. Если точного значения нет — поле можно оставить пустым.","source":"DOCX §1"},
    {"code":"tdna_match_existing_rope","label":"Диаметр нового каната должен соответствовать установленному?","kind":"select","options":["Да","Нет"],"group":"Основные параметры подбора","source":"DOCX §1"},
    {"code":"tdna_drive_output","label":"Выходное напряжение привода, В","kind":"select","options":["208–230 В","460–480 В"],"group":"Основные параметры подбора","source":"DOCX §1"},
    {"code":"tdna_drive_manufacturer","label":"Производитель привода","kind":"select","options":["KEB/Green","Yaskawa/Magnetek","Schindler","KONE","TKE","Otis","Другой"],"group":"Основные параметры подбора","autofill_product":"vfd_brand","source":"DOCX §1"},
    {"code":"tdna_encoder_cable_length","label":"Длина кабеля энкодера, м","kind":"select","options":["9,1 м","15,2 м","10 м","20 м","37 м","50 м","60 м"],"group":"Основные параметры подбора","help":"Укажите требуемую длину кабеля. Значения 9,1 и 15,2 м — перевод исходных 30/50 ft в СИ.","source":"DOCX §1"},
    {"code":"tdna_remote_brake_release","label":"Устройство дистанционного растормаживания","kind":"select","options":["Не требуется","8 м (стандарт)","10 м","12 м"],"group":"Основные параметры подбора","help":"Трос Боудена. Применимо как для лебёдок в машинном помещении, так и для безмашинных. Укажите требуемую длину.","source":"Замечание инженера 27.08.2026"},

    {"code":"tdna_empty_car_weight","label":"Масса пустой кабины, кг","kind":"number","group":"Системные параметры (если известно)","help":"Укажите массу пустой кабины в килограммах. Если неизвестно — оставьте пустым; инженер уточнит отдельно.","source":"DOCX §1"},
    {"code":"tdna_counterweight_pct","label":"Предпочтительный противовес (%)","kind":"number","group":"Системные параметры (если известно)","help":"Диапазон исходного опросника: 40–50 %.","source":"DOCX §1"},
    {"code":"tdna_emergency_brake","label":"Опция экстренного торможения","kind":"select","options":["TDNA Стандарт (по умолчанию)","HW Rope Gripper 620","HW Rope Gripper 622","HW Rope Gripper 624","HW Rope Gripper 626","Другое"],"group":"Системные параметры (если известно)","source":"DOCX §1"},
    {"code":"tdna_compensation_density","label":"Масса погонного метра компенсирующей цепи (если используется повторно)","kind":"number","group":"Системные параметры (если известно)","source":"DOCX §1"},
    {"code":"tdna_compensation_sheave_weight","label":"Вес установленного компенсационного шкива (кг)","kind":"number","group":"Системные параметры (если известно)","source":"DOCX §1"},
    {"code":"tdna_double_wrap","label":"Требуется двойное обёртывание тросов?","kind":"select","options":["Да","Нет"],"group":"Системные параметры (если известно)","source":"DOCX §1"},
    {"code":"tdna_acceleration","label":"Максимальное ускорение, м/с²","kind":"number","group":"Системные параметры (если известно)","source":"DOCX §1"},

    {"code":"quote_machine","label":"Лебёдка","kind":"checkbox","group":"Комплектация для расчёта цены","default":True,"source":"DOCX §1"},
    {"code":"quote_bedplate","label":"Подлебёдочная рама","kind":"checkbox","group":"Комплектация для расчёта цены","source":"DOCX §1"},
    {"code":"quote_rope_guard","label":"Защита от спадания канатов и ограждение","kind":"checkbox","group":"Комплектация для расчёта цены","source":"DOCX §1"},
    {"code":"quote_deflector","label":"Отводной блок","kind":"checkbox","group":"Комплектация для расчёта цены","source":"DOCX §1"},
    {"code":"quote_encoder_cable","label":"Кабель энкодера","kind":"checkbox","group":"Комплектация для расчёта цены","source":"DOCX §1"},

    {"code":"tdna_two_week","label":"Предпочтительный вариант с двухнедельным сроком выполнения заказа (если доступен)?","kind":"select","options":["Да","Нет"],"group":"Данные для чертежа","source":"DOCX §2"},
    {"code":"tdna_project_start","label":"Ориентировочная дата начала проекта","kind":"date","group":"Данные для чертежа","source":"DOCX §2"},
    {"code":"tdna_machine_hand","label":"Монтажное положение лебёдки: левое или правое","kind":"select","options":["Левое","Правое"],"group":"Данные для чертежа","help":"Выберите положение по виду сверху. См. рис. 1.","figure":"1","source":"DOCX §2 / Torin Ill.1"},
    {"code":"tdna_reassembly","label":"Услуга по сборке на месте","kind":"select","options":["Требуется","Не требуется"],"group":"Данные для чертежа","help":"В исходном Torin доступно только для крупных безредукторных TGL.","source":"DOCX §2"},
    {"code":"tdna_rope_drop_distance","label":"Rope Drop — расстояние между линиями канатов, мм","kind":"number","group":"Данные для чертежа","help":"Укажите размер в мм. См. рис. 2.","figure":"2","source":"DOCX §2 / Torin Ill.2"},
    {"code":"tdna_rope_to_wall","label":"Расстояние от каната до стены машинного помещения, мм","kind":"number","group":"Данные для чертежа","help":"Укажите минимальное расстояние от оси каната до стены в мм. См. рис. 2.","figure":"2","source":"DOCX §2 / Torin Ill.2"},
    {"code":"tdna_room_height","label":"Свободная высота машинного помещения, мм","kind":"number","group":"Данные для чертежа","help":"Укажите доступную высоту помещения в мм. См. рис. 2.","figure":"2","source":"DOCX §2 / Torin Ill.2"},
    {"code":"tdna_existing_beam_location","label":"Расположение существующей балки / опоры под лебёдку","kind":"select","options":["A — балка заделана в плиту (Embedded)","B — балка под плитой (Under Slab)","C — балки над и под плитой (Above & Under Beam)","D — балка над поверхностью плиты (Above Surface Beam)","E — конструкционная плита без отдельной балки (Structural Slab)"],"group":"Данные для чертежа","help":"Выберите вариант, наиболее похожий на существующую конструкцию. См. рис. 3. Если ни один не подходит — опишите в комментарии.","figure":"3","source":"DOCX §2 / Torin Ill.3"},
    {"code":"tdna_ct","label":"CT — толщина плиты перекрытия, мм","kind":"number","group":"Данные для чертежа","help":"Размер CT в мм. См. рис. 3.","figure":"3","source":"DOCX §2 / Torin Ill.3"},
    {"code":"tdna_wf","label":"Wf — ширина балки, мм","kind":"number","group":"Данные для чертежа","help":"Размер Wf в мм. См. рис. 3.","figure":"3","source":"DOCX §2 / Torin Ill.3"},
    {"code":"tdna_ww","label":"Ww — высота балки, мм","kind":"number","group":"Данные для чертежа","help":"Размер Ww в мм. См. рис. 3.","figure":"3","source":"DOCX §2 / Torin Ill.3"},
    {"code":"tdna_z1","label":"Z1, мм","kind":"number","group":"Данные для чертежа","help":"Расстояние Z1 в плане в мм. См. рис. 2.","figure":"2","source":"DOCX §2 / Torin Ill.2"},
    {"code":"tdna_z2","label":"Z2, мм","kind":"number","group":"Данные для чертежа","help":"Расстояние Z2 в плане в мм. См. рис. 2.","figure":"2","source":"DOCX §2 / Torin Ill.2"},

    {"code":"tdna_special_bedplate","label":"Специальная конфигурация опорной плиты","kind":"textarea","group":"Отводной блок и компоновка","source":"DOCX §2"},
    {"code":"tdna_deflector_below_slab","label":"Предпочтительно установить отводной блок под плитой перекрытия?","kind":"select","options":["Да","Нет"],"group":"Отводной блок и компоновка","source":"DOCX §2"},
    {"code":"tdna_keep_deflector","label":"Оставить существующий отводной блок или заменить на новый?","kind":"select","options":["Оставить существующий","Заменить на новый"],"group":"Отводной блок и компоновка","source":"DOCX §2"},
    {"code":"tdna_ddef","label":"Ddef — диаметр отводного блока, мм","kind":"number","group":"Отводной блок и компоновка","help":"Диаметр существующего отводного блока в мм. См. рис. 3.","figure":"3","source":"DOCX §2 / Torin Ill.3"},
    {"code":"tdna_deflector_grooves","label":"Число ручьёв существующего отводного блока","kind":"number","group":"Отводной блок и компоновка","source":"DOCX §2"},
    {"code":"tdna_deflector_pitch","label":"Шаг ручьёв — от центра каната до каната, мм","kind":"number","group":"Отводной блок и компоновка","autofill_product":"groove_pitch_mm","source":"DOCX §2"},
    {"code":"tdna_ys","label":"Ys — от низа плиты до оси отводного блока, мм","kind":"number","group":"Отводной блок и компоновка","help":"Размер Ys в мм. См. рис. 3.","figure":"3","source":"DOCX §2 / Torin Ill.3"},
    {"code":"tdna_rope_square","label":"Ось канатов расположена перпендикулярно стене?","kind":"select","options":["Да","Нет"],"group":"Отводной блок и компоновка","help":"Если нет — выберите угловую схему A/B/C/D ниже. См. рис. 4.","figure":"4","source":"DOCX §2 / Torin Ill.4"},
    {"code":"tdna_angle_profile","label":"Схема углового размещения A / B / C / D","kind":"select","options":["A","B","C","D"],"group":"Отводной блок и компоновка","help":"Выберите схему, соответствующую фактическому положению канатов и стен. См. рис. 4.","figure":"4","source":"DOCX §2 / Torin Ill.4"},
    {"code":"tdna_x1","label":"X1 — расстояние от каната кабины до стены, мм","kind":"number","group":"Отводной блок и компоновка","help":"Размер X1 в мм. См. рис. 4.","figure":"4","source":"DOCX §2 / Torin Ill.4"},
    {"code":"tdna_x2","label":"X2 — расстояние до стены по перпендикуляру, мм","kind":"number","group":"Отводной блок и компоновка","help":"Размер X2 в мм. См. рис. 4.","figure":"4","source":"DOCX §2 / Torin Ill.4"},
    {"code":"tdna_x3","label":"X3 — расстояние до смежной стены, мм","kind":"number","group":"Отводной блок и компоновка","help":"Размер X3 в мм. См. рис. 4.","figure":"4","source":"DOCX §2 / Torin Ill.4"},
    {"code":"tdna_bedplate_holes","label":"Предпочтительны готовые или предварительные отверстия в подрамнике?","kind":"select","options":["Готовые отверстия","Предварительные отверстия"],"group":"Отводной блок и компоновка","source":"DOCX §2"},
    {"code":"tdna_obstructions","label":"Дополнительные препятствия и размеры, не охваченные опросником","kind":"textarea","group":"Отводной блок и компоновка","help":"Например: hitchplates, governors, air ducts. Фото машинного помещения и существующего оборудования можно приложить на следующем этапе.","source":"Torin Survey §2"},

    {"code":"tdna_block_location","label":"Место установки блока","kind":"select","options":["В машинном помещении","На верхней балке кабины","На верхней балке противовеса","2:1 под кабиной","2:1 под противовесом"],"group":"Блоки / шкивы","source":"DOCX §3"},
    {"code":"tdna_sheave_type","label":"Тип отводного блока / схема огибания канатом","kind":"select","options":["A — Отводной блок, угол охвата < 90°","B — Угол охвата 90°","C — Угол охвата 180°"],"group":"Блоки / шкивы","help":"Выберите схему огибания канатом по оригинальному эскизу Torin (A/B/C). Эскиз можно увеличить по клику.","source":"DOCX §3 / Torin p.3"},
    {"code":"tdna_sheave_qty","label":"Количество","kind":"number","group":"Блоки / шкивы","source":"DOCX §3"},
    {"code":"tdna_sheave_diameter","label":"Диаметр шкива D (мм)","kind":"select","options":["400","520","640","762"],"group":"Блоки / шкивы","source":"DOCX §3"},
    {"code":"tdna_sheave_width","label":"Максимально допустимая ширина W, мм","kind":"number","group":"Блоки / шкивы","source":"DOCX §3"},
    {"code":"tdna_required_shaft_diameter","label":"Требуемый диаметр вала d, мм (если нужен)","kind":"number","group":"Блоки / шкивы","source":"DOCX §3"},
    {"code":"tdna_shaft_type","label":"Тип отводного блока / вала","kind":"select","options":["Shaft Type A","Shaft Type B"],"group":"Блоки / шкивы","source":"DOCX §3 / Torin p.3"},
    *[{"code":f"tdna_l{i}","label":f"L{i}, мм","kind":"number","group":"Блоки / шкивы","source":"DOCX §3 / Torin p.3"} for i in range(1,7)],
]
QUESTIONNAIRE_FIELDS = TDNA_SURVEY_FIELDS
QUESTIONNAIRE_SHEET = TDNA_SURVEY_SOURCE


class InquiryDraftPayload(BaseModel):
    product_id: int
    answers: dict[str, Any] = Field(default_factory=dict)

@app.get("/api/inquiry-drafts/{token}")
def get_inquiry_draft(token: str):
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,100}", token):
        raise HTTPException(400, "Некорректный токен черновика")
    with db_conn() as con:
        r=con.execute("SELECT product_id,payload,updated_at FROM inquiry_drafts WHERE token=?",(token,)).fetchone()
    if not r: return {"ok":True,"found":False}
    return {"ok":True,"found":True,"product_id":r["product_id"],"answers":json.loads(r["payload"]),"updated_at":r["updated_at"]}

@app.put("/api/inquiry-drafts/{token}")
def save_inquiry_draft(token: str, body: InquiryDraftPayload):
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,100}", token):
        raise HTTPException(400, "Некорректный токен черновика")
    payload=json.dumps(body.answers,ensure_ascii=False)
    with db_conn() as con:
        con.execute("""INSERT INTO inquiry_drafts(token,product_id,payload) VALUES(?,?,?)
            ON CONFLICT(token) DO UPDATE SET product_id=excluded.product_id,payload=excluded.payload,updated_at=CURRENT_TIMESTAMP""",
            (token,body.product_id,payload))
    return {"ok":True,"saved":True}

@app.delete("/api/inquiry-drafts/{token}")
def delete_inquiry_draft(token: str):
    with db_conn() as con:
        con.execute("DELETE FROM inquiry_drafts WHERE token=?",(token,))
    return {"ok":True}

@app.get("/api/questionnaire/schema")
def questionnaire_schema():
    groups=[]
    for name in TDNA_SURVEY_GROUPS:
        groups.append({"name":name,"fields":[f for f in QUESTIONNAIRE_FIELDS if f.get("group")==name]})
    return {"title":"Инженерный опросный лист Torin Drive — русская версия","source_sheet":TDNA_SURVEY_SOURCE,"groups":groups,"field_count":len(QUESTIONNAIRE_FIELDS),"excluded_struck_fields":["Название проекта","Номер договора","Требуется сейсмическое исполнение?","Адрес месторасположения проекта","Консультант"]}

class InquiryCreate(BaseModel):
    product_id: int
    filters: dict[str, Any] = Field(default_factory=dict)
    answers: dict[str, Any] = Field(default_factory=dict)
    quote: dict[str, Any] | None = None

class InquiryStatus(BaseModel):
    status: Literal["new","in_review","sent_to_manufacturer","quoted","closed","cancelled"]

@app.post("/api/inquiries")
def create_inquiry(body: InquiryCreate):
    with db_conn() as con:
        row=con.execute("SELECT id,active,payload FROM products WHERE id=?",(body.product_id,)).fetchone()
        if not row or not row["active"]: raise HTTPException(404,"Лебёдка не найдена")
        product=json.loads(row["payload"]); product["id"]=row["id"]
        cur=con.execute("""INSERT INTO inquiries(status,product_id,manufacturer,model,product_snapshot,filter_snapshot,answers,quote_snapshot)
            VALUES('new',?,?,?,?,?,?,?)""",(
            body.product_id, product.get("manufacturer"), product.get("model"),
            json.dumps(product,ensure_ascii=False), json.dumps(body.filters,ensure_ascii=False),
            json.dumps(body.answers,ensure_ascii=False), json.dumps(body.quote,ensure_ascii=False) if body.quote else None
        ))
        iid=cur.lastrowid
        number=f"LFT-{datetime.now().strftime('%Y%m%d')}-{iid:05d}"
        con.execute("UPDATE inquiries SET number=? WHERE id=?",(number,iid))
    return {"ok":True,"id":iid,"number":number,"status":"new"}

@app.get("/api/admin/inquiries")
def admin_inquiries(status: str|None=None, q: str|None=None, limit:int=Query(100,ge=1,le=500), offset:int=Query(0,ge=0), _:str=Depends(admin_auth)):
    sql="SELECT * FROM inquiries WHERE 1=1"; args=[]
    if status: sql+=" AND status=?"; args.append(status)
    if q: sql+=" AND (number LIKE ? OR manufacturer LIKE ? OR model LIKE ? OR answers LIKE ?)"; pat=f"%{q}%"; args += [pat,pat,pat,pat]
    sql+=" ORDER BY id DESC"
    with db_conn() as con:
        rows=con.execute(sql,args).fetchall()
    total=len(rows); rows=rows[offset:offset+limit]
    return {"total":total,"items":[{"id":r["id"],"number":r["number"],"status":r["status"],"manufacturer":r["manufacturer"],"model":r["model"],"created_at":r["created_at"]} for r in rows]}

@app.get("/api/admin/inquiries/{inquiry_id}")
def admin_inquiry(inquiry_id:int, _:str=Depends(admin_auth)):
    with db_conn() as con: r=con.execute("SELECT * FROM inquiries WHERE id=?",(inquiry_id,)).fetchone()
    if not r: raise HTTPException(404,"Запрос не найден")
    return {"id":r["id"],"number":r["number"],"status":r["status"],"manufacturer":r["manufacturer"],"model":r["model"],"created_at":r["created_at"],"updated_at":r["updated_at"],"product":json.loads(r["product_snapshot"]),"filters":json.loads(r["filter_snapshot"]),"answers":json.loads(r["answers"]),"quote":json.loads(r["quote_snapshot"]) if r["quote_snapshot"] else None}

@app.put("/api/admin/inquiries/{inquiry_id}/status")
def admin_inquiry_status(inquiry_id:int, body:InquiryStatus, _:str=Depends(admin_auth)):
    with db_conn() as con:
        cur=con.execute("UPDATE inquiries SET status=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(body.status,inquiry_id))
        if cur.rowcount==0: raise HTTPException(404,"Запрос не найден")
    return {"ok":True,"status":body.status}



# -------------------- Коммерческий калькулятор --------------------
# Полный цифровой перенос Калькулятор-2.xlsx: четыре сценария оплаты,
# все используемые переменные, промежуточные расчёты, эталонные значения
# и обратный расчёт закупочной цены под целевую цену продажи.
CALC_REFERENCE = json.loads((ROOT / "data" / "calculator_reference.json").read_text(encoding="utf-8"))
CALC_BASELINE = CALC_REFERENCE["baseline"]

class QuoteRequest(BaseModel):
    model: str = "Выбранная модель"
    purchase_cny: float = Field(6200, ge=0)
    bank_commission_cny: float = Field(470, ge=0)
    bank_commission_eur: float = Field(100, ge=0)
    rail_delivery_usd: float = Field(9000, ge=0)
    delivery_days: int = Field(25, ge=0)
    production_days: int = Field(21, ge=0)
    supply_days: int = Field(55, ge=0)
    qty_container: int = Field(67, ge=1)
    eur_rate: float = Field(94.94, gt=0)
    usd_rate: float = Field(81, gt=0)
    cny_rate: float = Field(11.1209, gt=0)
    credit_rate: float = Field(0.27, ge=0)
    unused_rate_b11: float = Field(0.05, ge=0)
    supplier_agent_rate: float = Field(0.02, ge=0)
    client_conversion_additive: float = Field(0.02, ge=0)
    cny_conversion_markup: float = Field(0.04, ge=0)
    currency_control_rate: float = Field(0.006, ge=0)
    svh_rub: float = Field(20000, ge=0)
    broker_rub: float = Field(20000, ge=0)
    overhead_ratio: float = Field(0.11957242476804819, ge=0)
    sales_markup: float = Field(0.15, ge=0)
    discount: float = Field(0, ge=0, le=1)
    last_mile_cny: float = Field(0, ge=0)
    pass_price_cny: float = Field(10960, ge=0)
    defer_days: int = Field(60, ge=0)
    delivery_first_share: float = Field(0.5, ge=0, le=1)
    delivery_second_share: float = Field(0.5, ge=0, le=1)
    supplier_first_share: float = Field(0.5, ge=0, le=1)
    supplier_second_share: float = Field(0.5, ge=0, le=1)
    mode: Literal["customer", "employee"] = "customer"

class ReverseQuoteRequest(QuoteRequest):
    target_sale_cny: float = Field(10000, gt=0)
    scenario: Literal["postpay", "50_50", "on_delivery", "prepay"] = "postpay"

SCENARIOS = {
    "postpay": {"label":"Постоплата", "client_first":0.0, "client_second":1.0, "defer_source":"request", "q_style":"standard", "sheet":"Пост оплата"},
    "50_50": {"label":"50/50", "client_first":0.5, "client_second":0.5, "defer_source":0, "q_style":"standard", "sheet":"50-50"},
    "on_delivery": {"label":"100% по доставке", "client_first":0.0, "client_second":1.0, "defer_source":0, "q_style":"delivery", "sheet":"100 по доставке"},
    "prepay": {"label":"Предоплата 100%", "client_first":1.0, "client_second":0.0, "defer_source":0, "q_style":"delivery", "sheet":"Предоплата"},
}

def calc_scenario(q: QuoteRequest, scenario: str):
    cfg = SCENARIOS[scenario]
    B=q.purchase_cny; C=q.bank_commission_cny; D=q.rail_delivery_usd; E=q.delivery_days
    J=q.qty_container; M=q.production_days; AI=q.supply_days
    AJ=q.defer_days if cfg["defer_source"]=="request" else int(cfg["defer_source"])

    # Строка 27 исходного Excel: 50/50 по доставке и оплате поставщику.
    F=D*q.usd_rate*q.delivery_first_share
    H=D*q.usd_rate*q.delivery_second_share
    K=((B+C)*J)*(1+q.supplier_agent_rate)
    L=K*(q.cny_rate*(1+q.cny_conversion_markup))
    N=L*q.supplier_first_share
    P=L*q.supplier_second_share
    R=L*q.currency_control_rate
    S=q.svh_rub; T=q.broker_rub

    # Клиентские платежи AK/AL зависят от итоговой AE. Решаем фиксированную
    # точку так же, как пересчёт Excel; при эталонных входах значения совпадают.
    price=max(B*1.5, 1.0)
    detail={}
    for _ in range(200):
        AE=price
        AG=AE*J
        # В файле формула именно CNY + 2%, то есть +0.02 к значению курса.
        AH=AG*(q.cny_rate+q.client_conversion_additive)
        AK=AH*cfg["client_first"]
        AL=AH*cfg["client_second"]

        G=((AI+AJ)-M)*(F*q.credit_rate/365)
        I=max(0, ((AI+AJ)-M-E)*(H*q.credit_rate/365))
        O=(AI+AJ)*((N-AK)*(q.credit_rate/365)) if N>AK else 0

        if cfg["q_style"]=="standard":
            if (AK-N)<0:
                Q=(AI+AJ-M)*(P*q.credit_rate/365) if P>(AK-N) else 0
            else:
                Q=(AI+AJ-M)*(P*q.credit_rate/365)
        else:
            # Буквальный смысл формулы Q из листов «100 по доставке»/«Предоплата».
            Q=(AI+AJ-M)*(P*q.credit_rate/365) if ((AK-N)<0 and P>(AK-N)) else 0

        U=G+I+O+Q+((AI+AJ)*((R+S+T)*q.credit_rate/365))
        W=B*q.overhead_ratio
        V=(((T+S+R+L+(D*q.usd_rate))/J)/q.cny_rate)+(U/q.cny_rate/J)+W
        X=V*q.sales_markup
        Z=V+X
        new_price=(Z-Z*q.discount)+q.last_mile_cny

        detail={
            "sheet":cfg["sheet"], "defer_days":AJ,
            "delivery_payment_1_rub":F, "delivery_credit_1_rub":G,
            "delivery_payment_2_rub":H, "delivery_credit_2_rub":I,
            "supplier_total_cny":K, "supplier_total_rub":L,
            "supplier_payment_1_rub":N, "supplier_credit_1_rub":O,
            "supplier_payment_2_rub":P, "supplier_credit_2_rub":Q,
            "currency_control_rub":R, "svh_rub":S, "broker_rub":T,
            "credit_cost_rub":U, "cost_cny":V, "admin_cny":W,
            "markup_cny":X, "cost_with_markup_cny":Z,
            "discount_rate":q.discount, "last_mile_cny":q.last_mile_cny,
            "sale_cny":new_price, "volume_sale_cny":new_price*J,
            "volume_sale_rub":new_price*J*(q.cny_rate+q.client_conversion_additive),
            "client_payment_1_rub":AK, "client_payment_2_rub":AL,
            "supply_days":AI, "pass_price_cny":q.pass_price_cny,
            "profit_vs_pass_cny":new_price-q.pass_price_cny,
        }
        if abs(new_price-price)<1e-10:
            price=new_price; break
        price=new_price
    return price, detail

@app.get("/api/calculator/meta")
def calculator_meta():
    return {
        "source":"Калькулятор-2.xlsx",
        "sheets":["Пост оплата","50-50","100 по доставке","Предоплата","Лист1"],
        "scenario_labels":{k:v["label"] for k,v in SCENARIOS.items()},
        "baseline":CALC_BASELINE,
        "formula_count":sum(len(x.get("formulas",[])) for x in CALC_REFERENCE["sheets"].values()),
        "note":"В проекте сохранены исходный XLSX, все значения/формулы листов и эталонная сверка.",
    }

@app.post("/api/quote")
def quote(q: QuoteRequest):
    prices={}; internal={}
    for key,cfg in SCENARIOS.items():
        price,detail=calc_scenario(q,key)
        prices[key]={"label":cfg["label"],"price_cny":round(price,2),"price_cny_exact":price}
        internal[key]=detail
    payload={"model":q.model,"prices":prices,"source":"Калькулятор-2.xlsx — полный перенос 4 сценариев"}
    if q.mode=="employee":
        payload["internal"]=internal
        payload["inputs"]=q.model_dump()
    return payload

@app.post("/api/quote/reverse")
def reverse_quote(q: ReverseQuoteRequest):
    # Обратный расчёт из Лист1: находим закупочную цену CNY, при которой
    # итоговая цена выбранного сценария равна заданной клиентом целевой цене.
    lo=0.0; hi=max(q.target_sale_cny*2, 1000.0)
    base=q.model_dump(exclude={"target_sale_cny","scenario"})
    # Расширяем верхнюю границу, если требуется.
    for _ in range(30):
        candidate=QuoteRequest(**{**base,"purchase_cny":hi})
        val,_=calc_scenario(candidate,q.scenario)
        if val>=q.target_sale_cny: break
        hi*=2
    for _ in range(100):
        mid=(lo+hi)/2
        candidate=QuoteRequest(**{**base,"purchase_cny":mid})
        val,_=calc_scenario(candidate,q.scenario)
        if val<q.target_sale_cny: lo=mid
        else: hi=mid
    purchase=(lo+hi)/2
    candidate=QuoteRequest(**{**base,"purchase_cny":purchase})
    price,detail=calc_scenario(candidate,q.scenario)
    return {
        "scenario":q.scenario,"label":SCENARIOS[q.scenario]["label"],
        "target_sale_cny":q.target_sale_cny,"purchase_cny":round(purchase,2),
        "calculated_sale_cny":round(price,2),"difference_cny":round(price-q.target_sale_cny,6),
        "internal":detail if q.mode=="employee" else None,
        "source":"Лист1 / Обратный расчет",
    }

@app.get("/api/calculator/validate")
def validate_calculator():
    q=QuoteRequest(**CALC_BASELINE["inputs"])
    rows={}; ok=True
    for key,expected in CALC_BASELINE["expected_prices"].items():
        actual,_=calc_scenario(q,key)
        diff=actual-float(expected)
        passed=abs(diff)<1e-6
        rows[key]={"label":SCENARIOS[key]["label"],"expected":expected,"actual":actual,"difference":diff,"ok":passed}
        ok=ok and passed
    return {"ok":ok,"source":"Калькулятор-2.xlsx / Лист1", "checks":rows}


@app.get("/api/health")
def health():
    try:
        with db_conn() as con:
            count=con.execute("SELECT COUNT(*) FROM products WHERE active=1").fetchone()[0]
        return {"ok":True,"version":"4.4.10","products":count,"database":"ok"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@app.get("/api/version")
def version_info():
    return {"version":"4.4.10","product":"Liftorg B2B Engineering Platform","spec":"MASTER_SPEC.md","mode":"react-model-groups+wjc-t-volume-mrl+execution-selector-runtime-fix+buyer-visibility+persistent-media+media-library+inheritance+admin-upload+placement-rules+tdna-clean-survey+selection-summary+tdna-si+ru-sheave-terminology+zoom-sketches+optional-survey+direct-order+autosave+explainable-search"}
