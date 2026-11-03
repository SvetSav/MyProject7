# LMS Project

Django REST Framework проект с кастомной моделью пользователя (авторизация по email), курсами и уроками.

## Стек

- Python 3.10+
- Django 4.2+
- Django REST Framework 3.14+
- djangorestframework-simplejwt
- drf-spectacular (документация OpenAPI 3.0)
- drf-spectacular-sidecar (локальные UI без CDN)
- django-filter
- stripe (интеграция оплаты)
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

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Применить миграции
python manage.py migrate
# Если в репозитории нет готовых миграций, сначала выполните:
# python manage.py makemigrations users lms

# 5. Создать суперпользователя
#    Внимание: в качестве логина используется EMAIL, а не username.
python manage.py createsuperuser

# 6. Запустить сервер
python manage.py runserver

После запуска:

API доступно по адресу http://127.0.0.1:8000/api/

Админка: http://127.0.0.1:8000/admin/

# 7. Загрузить тестовые платежи (одно из двух)
python manage.py loaddata payments
### или, если фикстура не подходит по ID:
python manage.py load_payments

> ⚠️ Фикстура `payments.json` ссылается на конкретные ID пользователей, курсов и уроков.
> Если в вашей БД этих ID нет — используйте команду `load_payments`, она подставит
> случайные существующие объекты.
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