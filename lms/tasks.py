from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from .models import Subscription


@shared_task
def send_course_update_notification(course_id, course_title):
    """
    Отправляет письмо всем подписчикам курса при его обновлении.
    """
    subscribers = Subscription.objects.filter(course_id=course_id).select_related(
        "user"
    )

    emails = [sub.user.email for sub in subscribers if sub.user.email]

    if not emails:
        return f"Нет подписчиков у курса {course_id}"

    subject = f"Обновление курса: {course_title}"
    message = (
        f"Курс «{course_title}» был обновлён.\n\n"
        f"Перейдите на платформу, чтобы увидеть изменения."
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=emails,
        fail_silently=False,
    )

    return f"Письма отправлены: {len(emails)} получателей"
