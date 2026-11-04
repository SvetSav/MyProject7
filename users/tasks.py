from datetime import timedelta

from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


@shared_task
def deactivate_inactive_users():
    """
    Блокирует пользователей, которые не заходили более 30 дней.
    Обновление выполняется одним batch-запросом.
    """
    threshold = timezone.now() - timedelta(days=30)

    inactive_users = User.objects.filter(
        last_login__lt=threshold,
        is_active=True,
    )

    count = inactive_users.count()

    if count == 0:
        return "Нет неактивных пользователей для блокировки"

    # batch-обновление: один SQL-запрос вместо N
    updated = inactive_users.update(is_active=False)

    return f"Заблокировано пользователей: {updated}"
