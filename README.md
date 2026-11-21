# LMS Project

Django REST Framework проект для онлайн-обучения: курсы, уроки, пользователи с авторизацией по email, 
платежи через Stripe (mock-режим), подписки на обновления курсов, фоновые задачи (Celery), 
документация OpenAPI и автоматический CI/CD деплой на удалённый сервер.

## Стек

- Python 3.12 (в Docker) / 3.10+ (локально)
- Django 5.2+
- Django REST Framework 3.18+
- djangorestframework-simplejwt (JWT-авторизация)
- drf-spectacular + drf-spectacular-sidecar (OpenAPI 3.0)
- django-filter
- Celery 5.7 + Celery Beat + django-celery-beat
- Redis 7
- PostgreSQL 15
- django-environ
- Stripe (mock-режим)
- Pillow
- Gunicorn (WSGI-сервер в production)
- Nginx (reverse-proxy + статика)
- Docker + Docker Compose
- GitHub Actions (CI/CD)
- coverage

## Структура проекта

```
.
├── .github/
│   └── workflows/
│       └── deploy.yml          # CI/CD workflow
├── config/
│   ├── celery.py               # инстанс Celery
│   ├── settings.py             # настройки, env
│   ├── urls.py
│   └── __init__.py             # загрузка celery_app
├── lms/
│   ├── models.py               # Course, Lesson, Subscription
│   ├── serializers.py
│   ├── views.py
│   ├── tasks.py                # Celery-задачи
│   ├── stripe_service.py       # Stripe (mock + real)
│   ├── validators.py           # YouTubeOnlyValidator
│   └── paginators.py
├── users/
│   ├── models.py               # User, Payment
│   ├── tasks.py                # Celery-задачи
│   ├── views.py
│   ├── serializers.py
│   ├── permissions.py
│   └── filters.py
├── .env.template               # шаблон переменных окружения (коммитится)
├── .gitignore
├── Dockerfile                  # образ для production
├── docker-compose.yml          # сервисы: db, redis, web, celery, migrate
├── schema.yaml                 # OpenAPI-схема
├── coverage.txt                # отчёт покрытия тестами
├── manage.py
├── requirements.txt
└── README.md
```

## Быстрый старт (локально, без Docker)

```bash
# 1. Клонировать репозиторий
git clone https://github.com/SvetSav/MyProject7.git
cd MyProject7

# 2. Виртуальное окружение
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Зависимости
pip install -r requirements.txt

# 4. Настройки окружения
cp .env.template .env           # Windows: copy .env.template .env
# Отредактируйте .env: SECRET_KEY, ALLOWED_HOSTS, POSTGRES_*, EMAIL_*

# 5. Миграции
python manage.py migrate

# 6. Суперпользователь (логин — EMAIL, а не username)
python manage.py createsuperuser

# 7. Запуск
python manage.py runserver
```

После запуска:
- API: `http://127.0.0.1:8000/api/`
- Swagger UI: `http://127.0.0.1:8000/api/docs/`
- Админка: `http://127.0.0.1:8000/admin/`

## Быстрый старт (Docker Compose)

```bash
# 1. Настройки окружения
cp .env.template .env
# Отредактируйте .env

# 2. Запуск всех сервисов одной командой
docker compose up --build

# 3. Создать суперпользователя (логин — EMAIL)
docker compose exec web python manage.py createsuperuser
```

Что запустится:
- `db` — PostgreSQL 15 (volume `postgres_data`)
- `redis` — Redis 7 (volume `redis_data`)
- `migrate` — одноразовый сервис (миграции + `collectstatic`)
- `web` — Gunicorn (порт `127.0.0.1:8000`)
- `celery_worker` — Celery Worker
- `celery_beat` — Celery Beat (расписание из БД)

Остановка:
```bash
docker compose down          # остановить
docker compose down -v       # остановить + удалить volumes (данные БД!)
```

## Production-деплой

Приложение развёрнуто на удалённом сервере (Ubuntu 22.04, Yandex Cloud).

### Адреса

- API: `http://153.51.162.248/api/`
- Swagger UI: `http://153.51.162.248/api/docs/`
- ReDoc: `http://153.51.162.248/api/redoc/`
- Админка: `http://153.51.162.248/admin/`

### Архитектура

Все сервисы контейнеризованы и запускаются одной командой `docker compose up -d`:
```
Интернет → Nginx (контейнер, порт 80) → Gunicorn (контейнер web, 8000) → Django
│
├── PostgreSQL (контейнер db, volume)
├── Redis (контейнер redis, volume)
├── Celery Worker (контейнер)
└── Celery Beat (контейнер)
```

| Сервис | Контейнер | Порт | Описание |
|--------|-----------|------|----------|
| `nginx` | `nginx:1.25-alpine` | **80** | Reverse-proxy, раздаёт `/static/`, `/media/` |
| `web` | `myproject-web` | 8000 (внутренний) | Gunicorn + Django |
| `db` | `postgres:15-alpine` | 5432 (внутренний) | PostgreSQL, volume `postgres_data` |
| `redis` | `redis:7-alpine` | 6379 (внутренний) | Redis, volume `redis_data` |
| `celery_worker` | `myproject-celery_worker` | — | Celery Worker |
| `celery_beat` | `myproject-celery_beat` | — | Celery Beat (DatabaseScheduler) |
| `migrate` | `myproject-migrate` | — | Одноразовый (migrate + collectstatic) |

- **Наружу** открыт только порт **80** (Nginx). Порт 8000 у `web` — `expose`, не доступен снаружи.
- **PostgreSQL** и **Redis** — только внутри Docker-сети (`expose`).
- **Nginx** раздаёт статику из `/app/staticfiles/` (volume `./staticfiles`) и медиа из `/app/media/`.
- **UFW** открывает только 22 (SSH), 80 (HTTP), 443 (HTTPS).

### Переменные окружения

Все секреты вынесены в `.env` на сервере. Шаблон — `.env.template` в репозитории.

| Переменная | Описание |
|-----------|----------|
| `SECRET_KEY` | Секретный ключ Django |
| `DEBUG` | `False` в production |
| `ALLOWED_HOSTS` | Публичный IP сервера, `localhost`, `127.0.0.1` |
| `POSTGRES_DB` | Имя БД |
| `POSTGRES_USER` | Пользователь БД |
| `POSTGRES_PASSWORD` | Пароль БД |
| `CELERY_BROKER_URL` | `redis://redis:6379/0` |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/1` |
| `EMAIL_BACKEND` | `console` (или `smtp` для реальной отправки) |
| `EMAIL_HOST` | SMTP-хост (если `smtp`) |
| `EMAIL_PORT` | SMTP-порт (если `smtp`) |
| `EMAIL_USE_TLS` | `True` (если `smtp`) |
| `EMAIL_HOST_USER` | Логин SMTP (если `smtp`) |
| `EMAIL_HOST_PASSWORD` | Пароль приложения (если `smtp`) |
| `DEFAULT_FROM_EMAIL` | Адрес отправителя |
| `STRIPE_MOCK` | `true` (mock-режим) |
| `STRIPE_SECRET_KEY` | Ключ Stripe (если `STRIPE_MOCK=false`) |

> ⚠️ `.env` **не коммитится** (в `.gitignore`). Все значения для CI/CD передаются через **GitHub Secrets**.

### Авто-запуск и перезапуск

- **systemd** (`lms-compose.service`) — запускает `docker compose up -d` при загрузке сервера.
- **Docker** (`restart: unless-stopped` / `always`) — перезапускает упавшие контейнеры.
- **Nginx** — включён в автозапуск (`systemctl enable nginx`).

Проверка авто-перезапуска:

```bash
cd /var/www/myproject
docker compose exec web python -c "import os, signal; os.kill(1, signal.SIGTERM)"
sleep 5
docker compose ps -a web
docker inspect myproject-web-1 --format 'RestartCount: {{.RestartCount}}'
```

**Ожидаемо:** `web` снова `Up`, `RestartCount > 0`.

### Firewall (UFW)

Открыты только порты 22 (SSH), 80 (HTTP), 443 (HTTPS):

```bash
sudo ufw status verbose
```

### SSH-доступ к серверу

Для деплоя и отладки используется отдельный SSH-ключ (не пароль).

**Генерация ключа (один раз, на локальной машине):**

```powershell
ssh-keygen -t ed25519 -f $env:USERPROFILE\deploy_key -N '""'
```

- `deploy_key` — **приватный** ключ (для GitHub Secrets `SSH_PRIVATE_KEY`).
- `deploy_key.pub` — **публичный** ключ (добавляется в `~/.ssh/authorized_keys` на сервере).

**Добавление публичного ключа на сервер:**

```bash
mkdir -p ~/.ssh && chmod 700 ~/.ssh
echo "ssh-ed25519 AAAA... (ваш публичный ключ)" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

**Подключение:**

```powershell
ssh -i $env:USERPROFILE\deploy_key superuser1@153.51.162.248
```

> ⚠️ Приватный ключ **никогда** не коммитится в репозиторий. Он передаётся только через GitHub Secrets.

## Документация API

Проект использует **drf-spectacular** для генерации OpenAPI 3.0-схемы.

| Что | URL |
|-----|-----|
| Swagger UI (интерактивный) | `/api/docs/` |
| ReDoc (для чтения) | `/api/redoc/` |
| Схема OpenAPI (JSON/YAML) | `/api/schema/` |

### Генерация и валидация схемы

```bash
python manage.py spectacular --color --file schema.yaml --validate
```

Схема генерируется **без warnings и errors**.

### Локальные UI (без CDN)

Так как `cdn.jsdelivr.net` и `cdn.redoc.ly` могут быть недоступны из некоторых регионов, в проекте включён **sidecar-режим** — все JS/CSS-ресурсы Swagger UI и ReDoc отдаются локально через Django:

```python
SPECTACULAR_SETTINGS = {
    ...
    'SWAGGER_UI_DIST': 'SIDECAR',
    'SWAGGER_UI_FAVICON_HREF': 'SIDECAR',
    'REDOC_DIST': 'SIDECAR',
}
```

Документация работает **без доступа к интернету**.

## Эндпоинты

| Метод | URL | Описание |
|-------|-----|----------|
| POST | `/api/token/` | Получить JWT (access + refresh) по email и паролю |
| POST | `/api/token/refresh/` | Обновить access-токен |
| GET / POST | `/api/courses/` | Список / создание курсов |
| GET / PUT / PATCH / DELETE | `/api/courses/{id}/` | Детали / обновление / удаление курса |
| GET / POST | `/api/lessons/` | Список / создание уроков |
| GET / PUT / PATCH / DELETE | `/api/lessons/{id}/` | Детали / обновление / удаление урока |
| GET / POST / PUT / PATCH / DELETE | `/api/payments/` | CRUD по платежам + фильтрация |
| POST | `/api/payments/create/` | Создание платежа через Stripe (продукт + цена + сессия) |
| GET | `/api/payments/status/{session_id}/` | Проверка статуса Stripe-сессии (доп. задание) |
| POST | `/api/subscribe/` | Подписаться / отписаться от курса (toggle) |
| GET / POST | `/api/users/` | Список / регистрация пользователей |
| GET / PUT / PATCH | `/api/users/{id}/` | Просмотр / редактирование профиля |
| GET | `/api/schema/` | OpenAPI-схема |
| GET | `/api/docs/` | Swagger UI |
| GET | `/api/redoc/` | ReDoc |

## Аутентификация и роли

Проект использует **JWT**. Все эндпоинты, кроме регистрации (`POST /api/users/`) и получения токена (`POST /api/token/`), требуют заголовок `Authorization: Bearer <access_token>`.

### Получение токена

```
POST /api/token/
Body: { "email": "...", "password": "..." }
```

### Роли

- **Обычный пользователь** — видит/редактирует/удаляет только свои курсы и уроки.
- **Moderators** (группа) — видит и редактирует любые курсы и уроки, но **не может** создавать и удалять. Назначается через админку.

### Регистрация

```
POST /api/users/
Body: { "email", "password", "first_name", "phone", "city" }
```

Доступна без токена. Повторная регистрация с тем же email → `400 Bad Request`.

## Дополнительные возможности

### Валидация YouTube-ссылок

Поле `video_link` в уроках принимает **только** ссылки на `youtube.com` и `youtu.be`. Ссылки на другие домены отклоняются с сообщением «Ссылка должна вести только на youtube.com».

Реализовано в `lms/validators.py` (`YouTubeOnlyValidator`), подключено в `LessonSerializer.Meta.validators`.

### Фильтрация платежей

| Параметр | Описание |
|----------|----------|
| `?ordering=payment_date` | Сортировка по дате (возрастание) |
| `?ordering=-payment_date` | Сортировка по дате (убывание) |
| `?course=<id>` | Фильтр по курсу |
| `?lesson=<id>` | Фильтр по уроку |
| `?payment_method=cash` | Только наличные |
| `?payment_method=transfer` | Только переводы |

Пример: `/api/payments/?course=1&payment_method=transfer&ordering=-payment_date`

### Пагинация

- Курсы: 10 на страницу (`?page=2&page_size=5`)
- Уроки: 5 на страницу (`?page=1&page_size=10`)

Максимум: 50 для курсов, 20 для уроков.

### Подписки

- `POST /api/subscribe/` — подписаться или отписаться (toggle).
  - Body: `{"course_id": <id>}`
  - Ответ: `{"message": "...", "is_subscribed": true/false}`
- Поле `is_subscribed` в `GET /api/courses/{id}/` показывает подписку текущего пользователя.

### Celery и фоновые задачи

Проект использует **Celery** для асинхронной обработки задач и **Celery Beat** для периодических задач. Брокер и хранилище результатов — **Redis**.

#### Реализованные задачи

| Задача | Модуль | Тип | Описание |
|--------|--------|-----|----------|
| `send_course_update_notification` | `lms.tasks` | событийная | Отправляет email подписчикам курса при его обновлении |
| `deactivate_inactive_users` | `users.tasks` | периодическая | Блокирует пользователей, не заходивших > 30 дней |

#### Настройка Redis через `.env`

```env
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
```

> ⚠️ Используйте `127.0.0.1` (не `localhost`), если Redis работает локально. На Windows `localhost` резолвится в IPv6 (`::1`), и Celery может не найти Redis.

#### Запуск Celery

**Три отдельных окна** PowerShell (все — с активированным venv, в папке проекта):

**Окно 1 — Django-сервер:**
```powershell
cd C:\Users\Honest\Desktop\MyProject7
.\.venv\Scripts\Activate.ps1
python manage.py runserver
```

**Окно 2 — Celery Worker:**
```powershell
cd C:\Users\Honest\Desktop\MyProject7
.\.venv\Scripts\Activate.ps1
celery -A config worker -l info -P solo
```

> Флаг `-P solo` **обязателен на Windows** — стандартный пул `prefork` использует `fork()`, которого нет в Windows.

**Окно 3 — Celery Beat (планировщик):**
```powershell
cd C:\Users\Honest\Desktop\MyProject7
.\.venv\Scripts\Activate.ps1
celery -A config beat -l info
```

#### Расписание периодических задач

Так как используется `DatabaseScheduler` (из `django-celery-beat`), расписание хранится **в БД** и управляется через админку:

`http://127.0.0.1:8000/admin/django_celery_beat/periodictask/`

Пример задачи:

| Поле | Значение |
|------|----------|
| Name | `deactivate-inactive-users` |
| Task | `users.tasks.deactivate_inactive_users` |
| Schedule | Crontab: `hour=3, minute=0` (ежедневно в 03:00) |
| Enabled | ✅ |

#### Таймзона

`CELERY_TIMEZONE` **обязательно** должен совпадать с `TIME_ZONE` в Django:

```python
# config/settings.py
CELERY_TIMEZONE = TIME_ZONE
```

Проверка:

```bash
python manage.py shell -c "from django.conf import settings; print(settings.TIME_ZONE, settings.CELERY_TIMEZONE, settings.TIME_ZONE == settings.CELERY_TIMEZONE)"
# Ожидаемо: UTC UTC True
```

#### Логика уведомлений (доп. задание: < 4 часов)

При обновлении курса уведомление отправляется подписчикам **только если** курс не обновлялся более 4 часов:

```python
def perform_update(self, serializer):
    old_updated_at = serializer.instance.updated_at   # до save()
    course = serializer.save()

    threshold = timezone.now() - timedelta(hours=4)
    if old_updated_at is None or old_updated_at < threshold:
        send_course_update_notification.delay(course.id, course.title)
```

#### Проверка задач

```bash
# Ручной вызов задачи блокировки
python manage.py shell -c "from users.tasks import deactivate_inactive_users; print(deactivate_inactive_users.delay().get(timeout=30))"
# Ожидаемо: "Заблокировано пользователей: N" или "Нет неактивных пользователей для блокировки"
```

### Оплата через Stripe

#### Режимы работы

Проект поддерживает **два режима** интеграции Stripe, управляемых переменной `STRIPE_MOCK`:

| Режим | `STRIPE_MOCK` | Что происходит |
|-------|---------------|----------------|
| Mock (по умолчанию) | `true` | Запросы к Stripe эмулируются. Создаются `prod_...`, `price_...`, `cs_test_...` локально. `payment_url` ведёт на локальную заглушку. Все поля сохраняются. Позволяет проверить всю логику без реального ключа. |
| Real | `false` | Реальные запросы к Stripe API. Требует настоящий `sk_test_51...`. Возвращает реальный `checkout.stripe.com` URL. |

#### Настройка

```powershell
# Mock (без ключа)
$env:STRIPE_MOCK = "true"

# Real
$env:STRIPE_SECRET_KEY = "sk_test_51..."
$env:STRIPE_MOCK = "false"
```

#### Эндпоинты

| Метод | URL | Описание |
|-------|-----|----------|
| POST | `/api/payments/create/` | Создаёт продукт, цену и сессию Stripe, сохраняет платёж, возвращает `payment_url` |
| GET | `/api/payments/status/{session_id}/` | Проверяет и синхронизирует статус сессии (доп. задание) |

#### Пример запроса

```powershell
$body = '{"course_id":1,"amount":1500,"payment_method":"transfer"}'
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/payments/create/" -Method Post `
  -Headers @{ Authorization = "Bearer $adminToken" } `
  -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) `
  -ContentType "application/json; charset=utf-8"
```

Ответ: `payment` (со всеми `stripe_*` полями) + `payment_url`.

#### Важно

- Цена передаётся **в копейках** (`amount × 100`).
- Все ID (`stripe_product_id`, `stripe_price_id`, `stripe_session_id`) и `payment_link` сохраняются в модели `Payment`.
- Ошибки Stripe → `502 Bad Gateway` с понятным сообщением.
- В mock-режиме `payment_url` ведёт на `/api/payments/success/?mock_session=...` — эмуляция успешной оплаты для проверки логики.

## CI/CD (GitHub Actions)

Workflow: `.github/workflows/deploy.yml`.

### Триггеры

- **`push` в `develope`** → job'ы `test`, `lint` (деплой **не** запускается).
- **`push` в `main`** → job'ы `test`, `lint`, **`deploy`**.
- **`pull_request` в `main`** → job'ы `test`, `lint`.

### Этапы

1. **`test`** — устанавливает зависимости, запускает `python manage.py test` с переменными окружения для CI (SQLite, `console` email, `STRIPE_MOCK=true`).
2. **`lint`** — `flake8 . --select=E9,F63,F7,F82` (синтаксические ошибки). Запускается **после** `test` (`needs: test`).
3. **`deploy`** — `rsync` файлов на сервер + `ssh`-команды:
   - `docker compose up -d --build`
   - `python manage.py migrate`
   - `python manage.py collectstatic --noinput`

### GitHub Secrets

Для работы деплоя в настройках репозитория (**Settings → Secrets and variables → Actions**) должны быть:

| Секрет | Значение |
|--------|----------|
| `SSH_HOST` | Публичный IP сервера |
| `SSH_USER` | Пользователь на сервере (`superuser1`) |
| `SSH_PRIVATE_KEY` | Приватный SSH-ключ (содержимое `deploy_key`) |
| `DJANGO_SECRET_KEY` | Секретный ключ Django (генерируется) |
| `DJANGO_ALLOWED_HOSTS` | `IP,localhost,127.0.0.1` |
| `POSTGRES_DB` | `lms_db` |
| `POSTGRES_USER` | `lms_user` |
| `POSTGRES_PASSWORD` | Пароль БД |
| `DEFAULT_FROM_EMAIL` | `noreply@example.com` |

### Проверка workflow

1. Откройте `https://github.com/SvetSav/MyProject7/actions`.
2. Убедитесь, что последний запуск — зелёный.
3. В логах job'а `deploy` — успешные `docker compose up` и `migrate`.

### Как проверить, что деплой сработал

1. Внесите изменение в `README.md` (или любой файл).
2. Закоммитьте и запушьте в `main`:
   ```bash
   git checkout main
   git pull origin main
   # измените README.md
   git add README.md
   git commit -m "test: проверка деплоя"
   git push origin main
   ```
3. Дождитесь зелёного workflow в Actions.
4. На сервере:
   ```bash
   cd /var/www/myproject
   cat README.md | head -5   # должны увидеть изменения
   ```

## Тесты и покрытие

```bash
# Запустить все тесты
python manage.py test

# Запустить только тесты приложения lms
python manage.py test lms -v 2

# Покрытие тестами
pip install coverage
coverage run --source='.' manage.py test
coverage report > coverage.txt
coverage html      # HTML-отчёт в htmlcov/index.html
```

Текущее покрытие: **93%** (`coverage.txt` в корне репозитория).

## Переменные окружения

Настройки читаются из `.env` через `django-environ`. Шаблон — в `.env.template`.

| Переменная | Обязательна | Описание |
|-----------|-------------|----------|
| `SECRET_KEY` | Да | Секретный ключ Django |
| `DEBUG` | Да | `True` / `False` |
| `ALLOWED_HOSTS` | Да | Список хостов через запятую |
| `POSTGRES_DB` | Да (Docker) | Имя БД |
| `POSTGRES_USER` | Да (Docker) | Пользователь БД |
| `POSTGRES_PASSWORD` | Да (Docker) | Пароль БД |
| `CELERY_BROKER_URL` | Да | URL брокера Redis |
| `CELERY_RESULT_BACKEND` | Да | URL result backend |
| `EMAIL_BACKEND` | Нет | По умолчанию `console`; для отправки — `smtp` |
| `EMAIL_HOST` | Для SMTP | SMTP-хост |
| `EMAIL_PORT` | Для SMTP | `587` (TLS) или `465` (SSL) |
| `EMAIL_USE_TLS` | Для SMTP | `True` / `False` |
| `EMAIL_HOST_USER` | Для SMTP | Email-адрес |
| `EMAIL_HOST_PASSWORD` | Для SMTP | Пароль приложения (не обычный пароль) |
| `DEFAULT_FROM_EMAIL` | Да | Адрес отправителя |
| `STRIPE_MOCK` | Нет | `true` (по умолчанию) / `false` |
| `STRIPE_SECRET_KEY` | Для Stripe | `sk_test_51...` или пусто (mock) |

Пример `.env.template`:

```env
SECRET_KEY=django-insecure-change-me
DEBUG=False
ALLOWED_HOSTS=your-server-ip,localhost,127.0.0.1

POSTGRES_DB=lms_db
POSTGRES_USER=lms_user
POSTGRES_PASSWORD=change-me

CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
# EMAIL_HOST=smtp.yandex.ru
# EMAIL_PORT=587
# EMAIL_USE_TLS=True
# EMAIL_HOST_USER=your_email@yandex.ru
# EMAIL_HOST_PASSWORD=your_app_password
DEFAULT_FROM_EMAIL=noreply@example.com

STRIPE_SECRET_KEY=
STRIPE_MOCK=true
```

> ⚠️ `.env` **никогда не коммитится**. В репозитории только `.env.template` с placeholder-значениями.

## Чек-лист проверки работы

### 1. Сервер и приложение

- [ ] `http://153.51.162.248/api/docs/` — Swagger UI открывается
- [ ] `http://153.51.162.248/admin/` — админка открывается
- [ ] `curl -i http://127.0.0.1/api/` на сервере → `401 Unauthorized`
- [ ] `sudo systemctl status nginx` → `active (running)`

### 2. Безопасность

- [ ] `Test-NetConnection -ComputerName 153.51.162.248 -Port 8000` → `False`
- [ ] `sudo ufw status verbose` → только 22, 80, 443
- [ ] `ssh -i deploy_key superuser1@153.51.162.248` → вход без пароля
- [ ] `.env` отсутствует в `git ls-files`

### 3. Авто-перезапуск

- [ ] `sudo systemctl status lms-compose` → `active (exited)`
- [ ] `docker compose exec web python -c "import os, signal; os.kill(1, signal.SIGTERM)"` + `sleep 5` + `docker compose ps -a web` → `Up`, `RestartCount > 0`
- [ ] `sudo reboot` → после загрузки все контейнеры `Up`, Nginx `active`

### 4. CI/CD

- [ ] `https://github.com/SvetSav/MyProject7/actions` → последний запуск зелёный
- [ ] В `deploy.yml` порядок: `test` → `lint` → `deploy` (`needs`)
- [ ] В GitHub Secrets — 9 переменных
- [ ] PR `develope → main` смержен
- [ ] `deploy` job на `main` — зелёный
- [ ] После деплоя на сервере: `cat README.md` показывает изменения

### 5. Репозиторий

- [ ] `git ls-files | Select-String "\.env$|venv|__pycache__|patch\.json"` → пусто
- [ ] `.env.template` содержит все переменные, без реальных секретов
- [ ] `git log --oneline -10` — осмысленные коммиты
- [ ] PR содержит только нужные файлы

## Примечания

- Эндпоинты **не защищены авторизацией** только для `/api/token/` и `POST /api/users/` (регистрация). Остальные требуют JWT.
- Медиафайлы (аватарки, превью) раздаются через Nginx (`/media/`) или Django (в `DEBUG`).
- Статика (`/static/`) собирается через `collectstatic` и раздаётся Nginx.
- Модель пользователя использует `email` как `USERNAME_FIELD`.
- Celery Worker на Windows требует `-P solo`.
- Stripe работает в mock-режиме (без реальных ключей) — это позволяет проверить всю логику оплаты без внешних зависимостей.