# Deploy v4.4.0 TDNA Survey

Версия разворачивается поверх текущей установленной Liftorg. Перед обновлением копируется актуальная SQLite БД из работающего контейнера и каталог изображений лебёдок из текущего проекта.

```bash
set -e
NEW=/opt/liftorg/liftorg_b2b_4.4.0_tdna_survey
BACKUP=/root/liftorg-v440-backup

rm -rf "$BACKUP"
mkdir -p "$BACKUP"
OLD_CONTAINER=$(docker ps --format '{{.Names}}' | grep -i liftorg | head -n1 || true)
if [ -n "$OLD_CONTAINER" ]; then
  docker cp "$OLD_CONTAINER:/app/storage/catalog.db" "$BACKUP/catalog.db" 2>/dev/null || true
fi

OLD_DIR=$(find /opt/liftorg -maxdepth 1 -type d -name 'liftorg_b2b_*' ! -name 'liftorg_b2b_4.4.0_tdna_survey' -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -n1 | cut -d' ' -f2-)
if [ -n "$OLD_DIR" ] && [ -d "$OLD_DIR/app/static/winches" ]; then
  cp -a "$OLD_DIR/app/static/winches" "$BACKUP/winches"
fi

rm -rf "$NEW"
unzip -o /root/liftorg_b2b_4.4.0_tdna_survey.zip -d /opt/liftorg

if [ -f "$BACKUP/catalog.db" ]; then cp -f "$BACKUP/catalog.db" "$NEW/storage/catalog.db"; fi
if [ -d "$BACKUP/winches" ]; then mkdir -p "$NEW/app/static/winches"; cp -a "$BACKUP/winches/." "$NEW/app/static/winches/"; fi

docker ps --format '{{.Names}}' | grep -i liftorg | xargs -r docker stop
docker ps -a --format '{{.Names}}' | grep -i liftorg | xargs -r docker rm
cd "$NEW"
docker compose up -d --build
sleep 7

curl -s http://127.0.0.1:8098/api/version; echo
curl -s http://127.0.0.1:8098/api/questionnaire/schema | python3 -c 'import json,sys; d=json.load(sys.stdin); print("survey:",d["field_count"],"fields /",len(d["groups"]),"groups")'
for f in torin-machine-hand.png torin-room-clearances.png torin-beam-deflector.png torin-angle-layouts.png torin-sheave-types.png; do
  printf "%s -> " "$f"
  curl -s -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:8098/static/survey-sketches/$f"
done
```


## v4.4.4 placement migration

При первом старте v4.4.4 существующая `catalog.db` автоматически получает `placement_type` для 832 классифицируемых исполнений, если поле было пустым. Ручные значения не перезаписываются. Рекомендуем до обновления сохранить копию `catalog.db`.


## v4.4.6

Обновление схемы БД не требуется. Изменяется только UI/schema инженерного опросника. Текущую `catalog.db` необходимо переносить без пересоздания.


## v4.4.6 — медиабиблиотека оборудования

Реализована управляемая медиабиблиотека без привязки к правке кода.

Правила наследования медиа:

1. `execution` — конкретное исполнение имеет наивысший приоритет;
2. `model` — если у исполнения нет своего фото, используются материалы модели;
3. `family` — если у модели нет собственного материала, используется семейство производителя;
4. старое `image_ref` остаётся безопасным fallback для обратной совместимости.

Одна модель/семейство/исполнение может иметь несколько материалов. Поддерживаемые типы: `photo`, `drawing`, `document`. Для фото можно назначить основное изображение и порядок сортировки. Основное фото автоматически используется в каталоге, карточке и сравнении.

Добавлена таблица SQLite `media_assets` со связями `manufacturer / family / model / product_id`, типом материала, URL, названием, признаком основного фото и сортировкой. При первом запуске существующие изображения из `image_ref` и сохранённые семейные файлы `/static/winches` автоматически регистрируются в медиабиблиотеке.

Администратор получает страницу `/admin/media`, где можно загрузить JPG/JPEG/PNG/WEBP/GIF/SVG/PDF, выбрать уровень привязки, тип материала, основное фото и порядок. В карточке позиции из `/admin` добавлена ссылка `Медиа`.

Публичный API `/api/products/{id}` теперь отдаёт `media`, `media_family`, `primary_image`; `/api/products/{id}/media` возвращает разрешённую галерею. Карточка оборудования показывает галерею `Фото / Чертежи / Документы`.

Важно для обновлений: вместе с БД необходимо сохранять оба каталога `/app/static/winches` и `/app/static/media-library`. Загруженные файлы не удаляются физически при удалении привязки из БД, чтобы не разрушать исторические snapshots заявок.


## v4.4.7 — разграничение видимости калькулятора

- В режиме «Покупатель» скрыты закупочная цена, стоимость доставки, срок производства, срок доставки и внутренние коэффициенты.
- Покупателю показываются только итоговые цены по 4 сценариям оплаты.
- В режиме «Сотрудник» сохранён полный набор внутренних параметров и расшифровка расчёта.
- Базовые формулы `Калькулятор-2.xlsx` не изменялись.
- Требование зафиксировано по обратной связи заказчика 27.08.2026.


## v4.4.8 — Persistent Media / media outside Docker image

- Каталог `media-library` вынесен в bind volume `./media-library:/app/app/static/media-library`.
- Каталог legacy-фото `winches` вынесен в bind volume `./winches:/app/app/static/winches`.
- Пользовательские фото, официальные PDF, CAD/ZIP и чертежи больше не запекаются в Docker image.
- Добавлен `.dockerignore`, исключающий `app/static/media-library/**` и `app/static/winches/**` из build context.
- Обновление приложения больше не должно удалять или повторно копировать медиабиблиотеку.
- Перед обновлением с v4.4.7 содержимое `app/static/media-library` и `app/static/winches` необходимо один раз перенести в новые корневые persistent-каталоги `media-library/` и `winches/`.
- SQLite остаётся persistent через `./storage:/app/storage`.
- Цель: Docker build содержит только код/статические UI-ресурсы, а тяжёлые и изменяемые медиа живут на хосте.


## v4.4.9 — Explicit Execution Selector

Обновление не требует миграции БД. При переходе с v4.4.8 сохранить `storage/`, `media-library/` и `winches/`, затем пересобрать контейнер.


## v4.4.9.1 — frontend boot hotfix
- Исправлена совместимость JS блока выбора исполнения.
- Убран потенциально проблемный новый синтаксис из runtime-критичного участка.
- Cache-version React assets изменён на `4491`, чтобы браузер не использовал старый app.js.
- БД, media-library и winches не изменяются.


## v4.4.9.2 — runtime fix execution selector
- Переписан селектор исполнений без динамического React.createElement.apply/IIFE.
- Добавлена фильтрация повреждённых/null execution records.
- Добавлен Error Boundary: ошибка одной UI-ветки больше не должна давать полностью белый экран.
- Cache-busting React assets: v=4492.
- БД, калькулятор и persistent media не изменяются.
