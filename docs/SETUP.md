# Запуск SWAG OWNERS

[Описание проекта, условия задачи, оценивание и команда → README.md](README.md)

Инструкция по первому запуску, входу, загрузке данных и обслуживанию проекта.

## Клонирование репозитория

```bash
git clone https://github.com/ktokar06/antiford_swag_owners.git

cd antiford_swag_owners
```

## Запуск: от папки до входа

1. Установите и запустите **Docker Desktop**.
2. Откройте папку проекта в VS Code или в другом Ide 
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
- 
- Логи: `docker compose logs --tail=100 backend db`


## Обучение модели

Готовая модель поставляется в `backend_antifrod/models/release/`.
Для обычного запуска переобучение не требуется. Метрики и методика оценки — в
[основном README](README.md#как-оцениваем-качество).

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
