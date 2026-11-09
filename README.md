# LMS Project

Django REST Framework проект с кастомной моделью пользователя (авторизация по email), курсами и уроками.

## Стек

- Python 3.10+
- Django 6.0+
- Django REST Framework 3.18+
- djangorestframework-simplejwt
- drf-spectacular + drf-spectacular-sidecar
- django-filter
- **Celery 5.6+** (фоновые задачи)
- **Celery Beat + django-celery-beat** (периодические задачи)
- **Redis 7** (брокер и result backend)
- **django-environ** (переменные окружения)
- stripe (mock-режим)
- Pillow
- coverage

## Установка

```
# 1. Клонировать репозиторий
git clone <URL_репозитория>
cd <папка_проекта>

# 2. Создать и активировать виртуальное окружение
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

Настройки окружения
cp .env.example .env       # Windows: copy .env.example .env
# Отредактируйте .env: SECRET_KEY, CELERY_*, EMAIL_*

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Redis (Docker)
docker run -d --name redis -p 6379:6379 redis:7

# 5. Применить миграции
python manage.py migrate
# Если в репозитории нет готовых миграций, сначала выполните:
# python manage.py makemigrations users lms

# 6. Создать суперпользователя
#    Внимание: в качестве логина используется EMAIL, а не username.
python manage.py createsuperuser

# 7. Запустить сервер
python manage.py runserver

После запуска:

API доступно по адресу http://127.0.0.1:8000/api/

Админка: http://127.0.0.1:8000/admin/

# 8. Загрузить тестовые платежи (одно из двух)
python manage.py loaddata payments
### или, если фикстура не подходит по ID:
python manage.py load_payments

> ⚠️ Фикстура `payments.json` ссылается на конкретные ID пользователей, курсов и уроков.
> Если в вашей БД этих ID нет — используйте команду `load_payments`, она подставит
> случайные существующие объекты.

# 9. Три окна:
# Окно 1 — Django
python manage.py runserver

# Окно 2 — Worker
celery -A config worker -l info -P solo

# Окно 3 — Beat (опционально, для периодических задач)
celery -A config beat -l info
```

## Эндпоинты
```
Метод	                     URL	                    Описание
GET/POST	        /api/courses/	                  Список / создание курсов
GET/PUT/PATCH/DELETE	/api/courses/{id}/	          Детали / обновление / удаление курса
GET/POST	        /api/lessons/	                  Список / создание уроков
GET/PUT/PATCH/DELETE	/api/lessons/{id}/	          Детали / обновление / удаление урока
GET/PUT/PATCH	        /api/users/{id}/	          Просмотр / редактирование профиля (доп. задание)
GET/POST/PUT/DELETE     /api/payments/                    CRUD по платежам + фильтрация
POST	                /api/payments/create/	          Создаёт продукт, цену и сессию Stripe, сохраняет платёж, возвращает payment_url
GET	                /api/payments/status/{session_id}/ Проверяет и синхронизирует статус сессии (доп. задание)
```

## Особенности сериализаторов
CourseSerializer возвращает lessons_count (количество уроков) и lessons
(вложенный список уроков через LessonSerializer).

UserSerializer возвращает payments — историю платежей пользователя
(дополнительное задание).

## Фильтрация и сортировка платежей

- `?ordering=payment_date` — по дате оплаты (по возрастанию)
- `?ordering=-payment_date` — по дате оплаты (по убыванию)
- `?course=<id>` — только платежи за указанный курс
- `?lesson=<id>` — только платежи за указанный урок
- `?payment_method=cash` — только наличные
- `?payment_method=transfer` — только переводы на счёт

Примеры:
- `/api/payments/?course=1&payment_method=transfer`
- `/api/payments/?ordering=-payment_date`

## Тестирование

Проверка эндпоинтов выполняется через Postman.

```
Пример создания курса (POST /api/courses/):

Body → form-data:
title — текст
description — текст
preview — тип File, выбрать картинку


Пример создания урока (POST /api/lessons/):

Body → form-data:
course — id существующего курса (число)
title — текст
description — текст
video_link — URL
preview — тип File, выбрать картинку

Запуск автотестов:
python manage.py test
```
Для загрузки изображений (avatar, preview) используйте form-data с типом поля File.

## Аутентификация

Проект использует JWT. Все эндпоинты, кроме регистрации и получения токена,
требуют заголовок `Authorization: Bearer <access_token>`.

### Получение токена
POST /api/token/
Body: { "email": "...", "password": "..." }

### Обновление токена
POST /api/token/refresh/
Body: { "refresh": "..." }

## Роли

- **Обычный пользователь** — видит/редактирует/удаляет только свои курсы и уроки.
- **Moderators** (группа) — видит и редактирует любые курсы и уроки, но не может
  создавать и удалять. Назначается через админку.

## Регистрация
POST /api/users/
Body: { "email", "password", "first_name", "phone", "city" }
Доступна без токена.

## Подписки

- `POST /api/subscribe/` — подписаться или отписаться (toggle).
  Body: `{"course_id": <id>}`. Возвращает `{"message": "...", "is_subscribed": bool}`.
- Поле `is_subscribed` в `GET /api/courses/{id}/` показывает подписку текущего пользователя.

## Пагинация

- `/api/courses/?page=2&page_size=5` — 5 курсов на страницу, страница 2.
- `/api/lessons/?page=1&page_size=10` — 10 уроков на страницу.
- По умолчанию: курсы — 10, уроки — 5.

## Валидация

- `video_link` в уроках допускает только ссылки на `youtube.com` и `youtu.be`.
- Ссылки на другие домены отклоняются с ошибкой 400.

## Тесты

```
python manage.py test lms -v 2
coverage run --source='.' manage.py test lms
coverage report > coverage.txt
```

## Документация API

Проект использует **drf-spectacular** для генерации OpenAPI 3.0-схемы.

| Что | URL |
|-----|-----|
| Swagger UI (интерактивный) | `/api/docs/` |
| ReDoc (для чтения) | `/api/redoc/` |
| Схема OpenAPI (JSON/YAML) | `/api/schema/` |

### Генерация и валидация схемы

```
# Проверить схему на ошибки и предупреждения
python manage.py spectacular --color --file schema.yaml --validate

# Или без записи в файл
python manage.py spectacular --validate
```

Схема генерируется без warnings и errors. 
Если появились warnings — смотрите @extend_schema_field в lms/serializers.py и 
@extend_schema_view в lms/views.py / users/views.py.


## Локальные UI (без CDN)
Так как cdn.jsdelivr.net и cdn.redoc.ly могут быть недоступны из некоторых регионов, 
в проекте включён sidecar-режим — все JS/CSS-ресурсы Swagger UI и ReDoc отдаются локально через Django:

```
SPECTACULAR_SETTINGS = {
    ...
    'SWAGGER_UI_DIST': 'SIDECAR',
    'SWAGGER_UI_FAVICON_HREF': 'SIDECAR',
    'REDOC_DIST': 'SIDECAR',
}
```

Документация работает без доступа к интернету.

## Оплата через Stripe

### Режимы работы

Проект поддерживает **два режима** интеграции Stripe, управляемых переменной `STRIPE_MOCK`:

| Режим | `STRIPE_MOCK` | Что происходит |
|-------|---------------|----------------|
| Mock (по умолчанию) | `true` | Запросы к Stripe эмулируются. Создаются `prod_...`, `price_...`, `cs_test_...` локально. `payment_url` ведёт на локальную заглушку. Все поля сохраняются. Позволяет проверить всю логику без реального ключа. |
| Real | `false` | Реальные запросы к Stripe API. Требует настоящий `sk_test_51...`. Возвращает реальный `checkout.stripe.com` URL. |

### Настройка

```
# Mock (без ключа)
$env:STRIPE_MOCK = "true"

# Real
$env:STRIPE_SECRET_KEY = "sk_test_51..."
$env:STRIPE_MOCK = "false"
```

#### Пример запроса

body = '{"course_id":1,"amount":1500,"payment_method":"transfer"}'
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/payments/create/" -Method Post `
  -Headers @{ Authorization = "Bearer $adminToken" } `
  -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) `
  -ContentType "application/json; charset=utf-8"

Ответ: payment (со всеми stripe_* полями) + payment_url.

### Важно
Цена передаётся в копейках (amount × 100).
Все ID (stripe_product_id, stripe_price_id, stripe_session_id) и payment_link сохраняются в модели Payment.
Ошибки Stripe → 502 Bad Gateway с понятным сообщением.
В mock-режиме payment_url ведёт на /api/payments/success/?mock_session=... — это эмуляция успешной оплаты для проверки логики.

## Celery и фоновые задачи

Проект использует **Celery** для асинхронной обработки задач и **Celery Beat**
для периодических задач. В качестве брокера и хранилища результатов используется **Redis**.

### Архитектура

Django (API) ──► Redis (broker) ──► Celery Worker ──► Redis (result backend)
▲
│
Celery Beat (расписание)

### Реализованные задачи

| Задача | Модуль | Тип | Описание |
|--------|--------|-----|----------|
| `send_course_update_notification` | `lms.tasks` | событийная | Отправляет email подписчикам курса при его обновлении |
| `deactivate_inactive_users` | `users.tasks` | периодическая | Блокирует пользователей, не заходивших > 30 дней |

### Настройка Redis через `.env`

Настройки Redis вынесены в переменные окружения (`.env`):

```
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/1
```

⚠️ Важно: используйте 127.0.0.1, а не localhost — на Windows localhost
резолвится в IPv6 (::1), и Celery может не найти Docker-контейнер с Redis.

Пример .env.example — в корне репозитория. Скопируйте в .env и заполните своими значениями:

```
cp .env.example .env
```
### Запуск Redis
Проект рассчитан на Redis 7, запущенный локально на порту 6379. Проще всего — через Docker:

```
docker run -d --name redis -p 6379:6379 redis:7
```

Проверка:

```
docker exec -it redis redis-cli ping
```
#### Ожидаемо: PONG

⚠️ Redis 3.x (из winget) не подойдёт — он не поддерживает протокол RESP3
и команду HELLO, из-за чего Celery 5.6+ падает с ошибкой
unknown command 'HELLO'. Нужен Redis 6.0+.

### Запуск Celery
Понадобятся три отдельных окна PowerShell (все — с активированным venv, в папке проекта):

Окно 1 — Django-сервер
```
cd C:\Users\Honest\Desktop\MyProject7
.\.venv\Scripts\Activate.ps1
python manage.py runserver
```

Окно 2 — Celery Worker
```
cd C:\Users\Honest\Desktop\MyProject7
.\.venv\Scripts\Activate.ps1
celery -A config worker -l info -P solo
```
⚠️ Флаг -P solo обязателен на Windows — стандартный пул prefork
использует fork(), которого нет в Windows.

Ожидаемый вывод:
```
[tasks]
  . lms.tasks.send_course_update_notification
  . users.tasks.deactivate_inactive_users
[INFO/MainProcess] celery@... ready.
```

Окно 3 — Celery Beat (планировщик)
```
cd C:\Users\Honest\Desktop\MyProject7
.\.venv\Scripts\Activate.ps1
celery -A config beat -l info
```

Ожидаемый вывод:
```
beat: Starting...
DatabaseScheduler: Schedule changed.
```

### Расписание периодических задач
Так как используется DatabaseScheduler (из django-celery-beat), расписание
хранится в БД и управляется через админку:

http://127.0.0.1:8000/admin/django_celery_beat/periodictask/

Пример задачи:

| Поле                              | Значение      |
|-----------------------------------|---------------|
| Name | deactivate-inactive-users   |
| Task     | users.tasks.deactivate_inactive_users |
|      Schedule    |                 Crontab: hour=3, minute=0 (ежедневно в 03:00)                      |
|          Enabled        |           ✅                                                                         |


⚠️ Задачи из CELERY_BEAT_SCHEDULE в settings.py не подхватываются —
DatabaseScheduler читает расписание только из БД.

#### Таймзона
CELERY_TIMEZONE обязательно должен совпадать с TIME_ZONE в Django,
иначе задачи будут запускаться не в то время:

```
# config/settings.py
CELERY_TIMEZONE = TIME_ZONE
```

Проверка:
```
python manage.py shell -c "from django.conf import settings; print(settings.TIME_ZONE, settings.CELERY_TIMEZONE, settings.TIME_ZONE == settings.CELERY_TIMEZONE)"
```
#### Ожидаемо: UTC UTC True

### Логика уведомлений (доп. задание: < 4 часов)
При обновлении курса уведомление отправляется подписчикам только если
курс не обновлялся более 4 часов. Реализовано в CourseViewSet.perform_update:

```
def perform_update(self, serializer):
    old_updated_at = serializer.instance.updated_at   # до save()
    course = serializer.save()

    threshold = timezone.now() - timedelta(hours=4)
    if old_updated_at is None or old_updated_at < threshold:
        send_course_update_notification.delay(course.id, course.title)
```

### Email в режиме разработки
Для тестирования без реального SMTP включён console.EmailBackend —
письма печатаются в консоли Worker-а, а не отправляются:

```
# config/settings.py
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```
Для реальной отправки — настройте SMTP в .env (см. .env.example) и переключите
EMAIL_BACKEND на smtp.EmailBackend. Для Yandex/Gmail нужен пароль приложения,
а не обычный пароль от почты.

Проверка задач

Ручной вызов задачи блокировки:

```
python manage.py shell -c "from users.tasks import deactivate_inactive_users; print(deactivate_inactive_users.delay().get(timeout=30))"
```
# Ожидаемо: "Заблокировано пользователей: N"

Проверка email-уведомления:

Обновите курс через API (PATCH /api/courses/1/).

В окне Worker появится:

```
Task lms.tasks.send_course_update_notification[...] received
Task ... succeeded in 0.05s: Письма отправлены: N получателей
Текст письма будет напечатан в консоли (при console.EmailBackend).
```

## Переменные окружения

Настройки читаются из `.env` через `django-environ`. Шаблон — в `.env.example`.

| Переменная | Обязательна | Описание |
|-----------|-------------|----------|
| `SECRET_KEY` | Да | Секретный ключ Django |
| `DEBUG` | Да | `True` / `False` |
| `CELERY_BROKER_URL` | Да | URL брокера Redis (например, `redis://127.0.0.1:6379/0`) |
| `CELERY_RESULT_BACKEND` | Да | URL result backend (`redis://127.0.0.1:6379/1`) |
| `EMAIL_BACKEND` | Нет | По умолчанию `console`; для отправки — `smtp.EmailBackend` |
| `EMAIL_HOST` | Для SMTP | SMTP-хост (`smtp.yandex.ru`, `smtp.gmail.com`) |
| `EMAIL_PORT` | Для SMTP | `587` (TLS) или `465` (SSL) |
| `EMAIL_HOST_USER` | Для SMTP | Email-адрес |
| `EMAIL_HOST_PASSWORD` | Для SMTP | **Пароль приложения** (не обычный пароль) |
| `STRIPE_SECRET_KEY` | Для Stripe | `sk_test_51...` или пусто (mock-режим) |
| `STRIPE_MOCK` | Нет | `true` (по умолчанию) / `false` |

Пример `.env.example`:

```
SECRET_KEY=django-insecure-change-me
DEBUG=True

CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/1

EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
# EMAIL_HOST=smtp.yandex.ru
# EMAIL_PORT=587
# EMAIL_USE_TLS=True
# EMAIL_HOST_USER=your_email@yandex.ru
# EMAIL_HOST_PASSWORD=your_app_password

STRIPE_SECRET_KEY=
STRIPE_MOCK=true
```

## Запуск через Docker Compose

1. Подготовка

Скопируйте шаблон окружения и заполните значения:

```
cp .env.example .env
```
В .env укажите SECRET_KEY, POSTGRES_PASSWORD и, если нужно, настройки email/Stripe.

2. Запуск
```
docker compose up --build
```
Compose соберёт образ, запустит PostgreSQL, Redis, выполнит миграции (migrate), затем поднимет Django (web), Celery Worker и Celery Beat.

После старта API доступно по адресу http://127.0.0.1:8000/api/, документация — http://127.0.0.1:8000/api/docs/.

3. Создание суперпользователя
```
docker compose exec web python manage.py createsuperuser
```
Логин — email, не username.

4. Просмотр логов
```
docker compose logs -f web
docker compose logs -f celery_worker
docker compose logs -f celery_beat
```
5. Остановка
```
docker compose down
```
С volumes (удалить данные БД и Redis):
```
docker compose down -v
```
6. Пересборка после изменений
```
docker compose up --build
```
### Примечания
db и redis используют expose и доступны только внутри сети Compose. Наружу опубликован только web (порт 8000).

Данные PostgreSQL и Redis сохраняются в volumes postgres_data и redis_data.

migrate — одноразовый сервис; web, celery_worker и celery_beat стартуют только после успешных миграций.

В docker-compose.yml переменные CELERY_BROKER_URL и CELERY_RESULT_BACKEND переопределены на redis://redis:6379/0 и /1 
— внутри Compose используется имя сервиса redis.