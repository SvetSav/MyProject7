# LMS Project

Django REST Framework проект с кастомной моделью пользователя (авторизация по email), курсами и уроками.

## Стек

- Python 3.10+
- Django 4.2+
- Django REST Framework 3.14+
- django-filter
- Pillow (для ImageField)

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
GET/POST	        /api/courses/	        Список / создание курсов
GET/PUT/PATCH/DELETE	/api/courses/{id}/	Детали / обновление / удаление курса
GET/POST	        /api/lessons/	        Список / создание уроков
GET/PUT/PATCH/DELETE	/api/lessons/{id}/	Детали / обновление / удаление урока
GET/PUT/PATCH	        /api/users/{id}/	Просмотр / редактирование профиля (доп. задание)
GET/POST/PUT/DELETE     /api/payments/          CRUD по платежам + фильтрация
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
```
Для загрузки изображений (avatar, preview) используйте form-data с типом поля File.

