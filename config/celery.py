import os

from celery import Celery

# Устанавливаем настройки Django по умолчанию
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")

# Загружаем настройки из Django (все настройки с префиксом CELERY_)
app.config_from_object("django.conf:settings", namespace="CELERY")

# Автоматически находим задачи в приложениях (tasks.py)
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
