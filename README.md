# SWAG OWNERS — антифрод по метаданным CDR

CatBoost оценивает завершённые вызовы, возвращает вероятность и рейтинг 0–100.
Оператор видит SHAP-объяснение, фиксирует результат разбора и настраивает пороги.
Содержание разговоров не анализируется. `auto_blocked` — решение в приложении;
команды телеком-оборудованию пока не отправляются.

## Запуск: от папки до входа

1. Установите и запустите **Docker Desktop**. Для полного датасета выделите Docker
   не менее 8 ГБ памяти. При первой сборке нужен интернет.
2. Откройте папку проекта в VS Code → **File → Open Folder**, затем
   **Terminal → New Terminal**. В терминале должна быть папка с `docker-compose.yml`.
3. Откройте единственный файл настроек **`.env` в корне**. Он уже заполнен.
   Данные входа: значения `OPERATOR_EMAIL` и `OPERATOR_PASSWORD` после `=`.
4. Выполните:

```bash
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

5. Дождитесь **healthy** у `db`, `backend`, `frontend`.
6. Откройте **http://localhost:8080**. Введите email и пароль из корневого `.env`
   и нажмите **«Войти»**. Единственная роль — `operator`.

Все команды одинаковы для macOS Terminal и Windows PowerShell.
Отдельная установка Python, Node.js, PostgreSQL и обучение модели для запуска не нужны.
Пароль из `.env` создаёт первый аккаунт только в пустой БД. После смены пароля
через интерфейс используйте новый пароль; изменение `.env` существующий аккаунт не меняет.

## Как устроен упрощённый Docker

Всего три сервиса. В Compose нет разделов `networks` и `volumes`, нет отдельного
контейнера миграций. Compose автоматически создаёт стандартную сеть для связи сервисов.

- `db`: образ PostgreSQL с готовыми SQL-файлами. База создаётся из `POSTGRES_DB`,
  таблицы — из `backend_antifrod/db/001_schema.sql`, справочники — из `002_reference.sql`.
  Все поля модели и ограничение `role = 'operator'` определены сразу в `CREATE TABLE`.
- `backend`: FastAPI и релизная модель; исходники копируются в образ явно.
- `frontend`: React и nginx; запросы `/api` отправляются backend.

**Данные БД находятся в слое контейнера** (`PGDATA=/var/lib/postgresql/local-data`).
Они сохраняются при `stop/start`, но **теряются при удалении или пересоздании `db`**.
Пустой служебный анонимный том, объявленный базовым образом PostgreSQL, не используется
для хранения БД. Это особенность базового образа, а не настройка Compose.

Обычная остановка и повторный запуск:

```bash
docker compose stop
docker compose start
```

`docker compose down` удаляет контейнер БД вместе с данными. Перед пересозданием
сделайте резервную копию, если хотите сохранить импорт и разборы.

### Резервная копия и восстановление

В обоих терминалах работают следующие команды — перенаправления бинарного вывода нет:

```bash
docker compose exec db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f /tmp/antifraud.dump'
docker compose cp db:/tmp/antifraud.dump ./antifraud.dump
```

Восстановление своей копии **заменяет текущие данные**:

```bash
docker compose stop backend frontend
docker compose cp ./antifraud.dump db:/tmp/antifraud.dump
docker compose exec db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner /tmp/antifraud.dump'
docker compose start backend frontend
```

## Загрузить данные

После входа: **«Записи CDR» → «Загрузить .cdr / .csv»**. Выберите файл и дождитесь
окончания фонового расчёта. Новая БД пустая; обученная модель не содержит исходные CDR.
Поддерживается `marked_dataset.csv`; метки `is_fraud` при импорте не определяют прогноз.
По умолчанию максимальный размер файла — 200 МБ.

Для большого CSV (замените путь на свой):

```bash
docker compose cp "/путь/marked_dataset.csv" backend:/app/marked_dataset.csv
docker compose exec backend python -m scripts.import_dataset /app/marked_dataset.csv
```

Каталог на хосте больше не монтируется. Кнопка импорта каталога читает `/app/cdr_out`
внутри backend; файлы можно предварительно скопировать туда через `docker compose cp`.
Прогресс CLI виден в терминале; веб-загрузка использует `/api/cdr/jobs/current`.

## Проверить

- Интерфейс: http://localhost:8080
- БД и модель: http://localhost:8080/health/db — `status: ok`, `schema: ml_operator_v1`,
  `engine: catboost`, хеш модели.
- Swagger: http://localhost:8000/docs
- Логи: `docker compose logs --tail=100 backend db`

HTTP smoke после импорта: `python3 scripts/smoke.py` (Windows: `py -3 scripts/smoke.py`).
Для разработки: Python 3.12, `pip install -r backend_antifrod/requirements.txt pytest httpx`.
Из `backend_antifrod`: `python -m pytest`. После добавления фото профиля прошли 60 тестов;
один исследовательский тест v1 пропущен, поскольку локальная модель v1 не поставляется.
PostgreSQL-тесты используют отдельную,
очищаемую базу из `TEST_DATABASE_URL` и создают её схему непосредственно SQL-файлами.

## Фото профиля

В разделе «Профиль» нажмите «Загрузить фото» или значок камеры. Поддерживаются
JPEG, PNG и WebP до 5 МБ и 20 млн пикселей. Фото можно заменить или удалить.
Сервер учитывает ориентацию, уменьшает изображение до 512×512 и сохраняет JPEG
в таблице `user_avatar`. Фото доступно владельцу через авторизованный профиль;
после повторного входа оно отображается в профиле и боковом меню.
API: `POST /api/auth/me/avatar` (multipart `file`), `DELETE /api/auth/me/avatar`;
`GET /api/auth/me` возвращает `avatar_url` (data URL либо null).

## Модель

Релиз: `backend_antifrod/models/release/`, CatBoost 1.2.8, 44 признака.
На отложенном временном test: precision 80,25%, recall 86,86%, FPR 2,37%, ROC-AUC 0,9888
при пороге модели 63. В приложении по умолчанию политика 40/70. Цель FPR ≤1% на test
не достигнута. Метрики относятся к исходной разметке хакатона; для независимой проверки
нужен новый закрытый период.

Обучение из `backend_antifrod`:

```bash
python -m ml.train --input /путь/marked_dataset.csv --config ml/configs/default.json --output artifacts/new-model
```

## Если возникла ошибка

| Симптом | Действие |
|---|---|
| Docker daemon недоступен | Запустить Docker Desktop |
| Compose не найден | Использовать Docker Desktop с Compose v2: `docker compose` |
| Нет конфигурации | Перейти в корень с `docker-compose.yml` |
| Занят 8080 | Изменить `FRONTEND_PORT`, `FRONTEND_URL`, `CORS_ORIGINS` в `.env` |
| Занят 8000 | Изменить `BACKEND_PORT` в `.env` |
| Ошибка скачивания | Проверить интернет, повторить сборку |
| Неверный пароль | Проверить данные созданного аккаунта; `.env` не сбрасывает пароль |
| Пустой обзор | Загрузить CDR и дождаться расчёта |
| БД не открывается после смены .env | Пароль в существующей БД не меняется от POSTGRES_PASSWORD |

## Материалы для сдачи

`docs/ready/` — актуальные PDF и DOCX: руководство, структура БД, API, тестирование,
развёртывание. `docs/presentation/` — презентация PPTX/PDF и `Текст_защиты.md`.
Подготовить единый архив: `python3 scripts/package_delivery.py`.
Архив содержит корневой `.env` для локального запуска; передавайте его вместе с проектом
только получателю сдачи. Исходные датасеты, кеши и локальные окружения не упаковываются.
