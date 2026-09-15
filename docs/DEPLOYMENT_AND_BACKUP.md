# Развёртывание и резервное копирование

## Production/test server
Приложение работает в Docker Compose за Nginx. Внешний HTTP проксируется на приложение через локальный порт 8098.

## Persistent данные
Не должны зависеть от Docker image:
- `storage/` — рабочая SQLite БД;
- `media-library/` — загруженные/официальные материалы;
- `winches/` — legacy/family изображения.

## Перед обновлением
1. Проверить `git status`.
2. Сделать backup `storage/catalog.db`.
3. Убедиться, что persistent media существует на хосте.
4. Получить код из Git.
5. Проверить Python/JS syntax.
6. `docker compose up -d --build`.
7. Проверить `/api/version`, `/api/meta`, `/api/calculator/validate`, `/`, ключевую карточку и медиа.

## Git
- `main` — основная ветка.
- стабильные версии отмечаются аннотированными тегами (`v4.5.0` и далее).
- секреты и рабочая БД не коммитятся.

## Backup
Git защищает код и документацию, но не заменяет backup БД и persistent media. Для полного disaster recovery нужны отдельно: Git + catalog.db backup + media backup + `.env`/секреты в защищённом хранилище.
