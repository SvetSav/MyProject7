from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
    inline_serializer,
)
from rest_framework import generics, serializers, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.permissions import IsNotModerator, IsOwner, IsOwnerOrModerator

from .models import Course, Lesson, Subscription
from .paginators import CoursePaginator, LessonPaginator
from .serializers import CourseSerializer, LessonSerializer
from .tasks import send_course_update_notification


@extend_schema_view(
    list=extend_schema(
        summary="Список курсов",
        description="Возвращает пагинированный список курсов. "
        "Модераторы видят все курсы, обычные пользователи — только свои.",
        parameters=[
            OpenApiParameter(
                name="page",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Номер страницы",
            ),
            OpenApiParameter(
                name="page_size",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Количество элементов на странице (макс. 50)",
            ),
        ],
        tags=["Курсы"],
    ),
    retrieve=extend_schema(summary="Получить курс", tags=["Курсы"]),
    create=extend_schema(summary="Создать курс", tags=["Курсы"]),
    update=extend_schema(summary="Обновить курс", tags=["Курсы"]),
    partial_update=extend_schema(summary="Частично обновить курс", tags=["Курсы"]),
    destroy=extend_schema(summary="Удалить курс", tags=["Курсы"]),
)
# ViewSet
class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    pagination_class = CoursePaginator

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            self.permission_classes = [IsAuthenticated]
        elif self.action == "create":
            self.permission_classes = [IsAuthenticated, IsNotModerator]
        elif self.action in ["update", "partial_update"]:
            self.permission_classes = [IsAuthenticated, IsOwnerOrModerator]
        elif self.action == "destroy":
            self.permission_classes = [IsAuthenticated, IsOwner, IsNotModerator]
        return [permission() for permission in self.permission_classes]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Course.objects.none()
        if user.groups.filter(name="Moderators").exists() or user.is_superuser:
            return Course.objects.all()
        return Course.objects.filter(owner=user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        old_updated_at = serializer.instance.updated_at  # ← ДО save()
        course = serializer.save()

        threshold = timezone.now() - timedelta(hours=4)
        if old_updated_at is None or old_updated_at < threshold:
            send_course_update_notification.delay(course.id, course.title)


@extend_schema(
    summary="Список уроков",
    description=(
        "Возвращает пагинированный список уроков. "
        "Модераторы видят все уроки, обычные пользователи — только свои."
    ),
    parameters=[
        OpenApiParameter(
            name="page",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="Номер страницы.",
        ),
        OpenApiParameter(
            name="page_size",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="Количество элементов на странице (макс. 20).",
        ),
    ],
    responses={
        200: LessonSerializer(many=True),
        401: OpenApiResponse(description="Требуется авторизация (JWT)."),
    },
    tags=["Уроки"],
)
# Generic-классы
class LessonListAPIView(generics.ListAPIView):
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = LessonPaginator

    def get_queryset(self):
        user = self.request.user
        if user.groups.filter(name="Moderators").exists() or user.is_superuser:
            return Lesson.objects.all()
        return Lesson.objects.filter(owner=user)


@extend_schema(
    summary="Создать урок",
    description=(
        "Создаёт новый урок. Владелец (`owner`) автоматически привязывается к текущему "
        "пользователю. Модераторы не могут создавать уроки — только обычные пользователи. "
        "Поле `video_link` принимает только ссылки на `youtube.com` и `youtu.be`."
    ),
    request=LessonSerializer,
    responses={
        201: LessonSerializer,
        400: OpenApiResponse(
            description="Некорректные данные (например, не-YouTube ссылка в `video_link`).",
        ),
        401: OpenApiResponse(description="Требуется авторизация (JWT)."),
        403: OpenApiResponse(description="Модератор не может создавать уроки."),
    },
    examples=[
        OpenApiExample(
            "Корректный запрос",
            request_only=True,
            value={
                "course": 1,
                "title": "Введение в Python",
                "description": "Первый урок курса",
                "video_link": "https://youtube.com/watch?v=abc123",
            },
        ),
    ],
    tags=["Уроки"],
)
class LessonCreateAPIView(generics.CreateAPIView):
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated, IsNotModerator]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


@extend_schema(
    summary="Получить урок",
    description=(
        "Возвращает детальную информацию об уроке. " "Доступно владельцу и модераторам."
    ),
    responses={
        200: LessonSerializer,
        401: OpenApiResponse(description="Требуется авторизация (JWT)."),
        403: OpenApiResponse(description="Нет прав на просмотр чужого урока."),
        404: OpenApiResponse(description="Урок не найден."),
    },
    tags=["Уроки"],
)
class LessonRetrieveAPIView(generics.RetrieveAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrModerator]


@extend_schema(
    summary="Обновить урок",
    description=(
        "Обновляет урок. Владелец может редактировать свои уроки, "
        "модератор — любые. Поле `video_link` принимает только `youtube.com` и `youtu.be`."
    ),
    request=LessonSerializer,
    responses={
        200: LessonSerializer,
        400: OpenApiResponse(description="Некорректные данные."),
        401: OpenApiResponse(description="Требуется авторизация (JWT)."),
        403: OpenApiResponse(description="Нет прав на редактирование чужого урока."),
        404: OpenApiResponse(description="Урок не найден."),
    },
    tags=["Уроки"],
)
class LessonUpdateAPIView(generics.UpdateAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrModerator]


@extend_schema(
    summary="Удалить урок",
    description=(
        "Удаляет урок. Владелец может удалить свой урок, "
        "модератор — **не может** (по требованиям ТЗ)."
    ),
    responses={
        204: OpenApiResponse(description="Урок удалён."),
        401: OpenApiResponse(description="Требуется авторизация (JWT)."),
        403: OpenApiResponse(
            description="Модератор не может удалять уроки, "
            "или пользователь не является владельцем."
        ),
        404: OpenApiResponse(description="Урок не найден."),
    },
    tags=["Уроки"],
)
class LessonDestroyAPIView(generics.DestroyAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated, IsOwner, IsNotModerator]


@extend_schema_view(
    post=extend_schema(
        summary="Подписаться / отписаться от курса",
        description=(
            "Toggle-эндпоинт для управления подпиской на обновления курса. "
            "Если пользователь ещё не подписан — создаёт подписку. "
            "Если уже подписан — удаляет её. "
            "Используется метод POST, потому что операция меняет состояние."
        ),
        request=inline_serializer(
            name="SubscriptionRequest",
            fields={
                "course_id": serializers.IntegerField(
                    help_text="ID курса, на который оформляется подписка.",
                ),
            },
        ),
        responses={
            200: OpenApiResponse(
                description="Подписка создана или удалена.",
                response=inline_serializer(
                    name="SubscriptionResponse",
                    fields={
                        "message": serializers.CharField(
                            help_text="«подписка добавлена» или «подписка удалена».",
                        ),
                        "is_subscribed": serializers.BooleanField(
                            help_text="Текущее состояние подписки после операции.",
                        ),
                    },
                ),
                examples=[
                    OpenApiExample(
                        "Подписка добавлена",
                        value={"message": "подписка добавлена", "is_subscribed": True},
                        response_only=True,
                    ),
                    OpenApiExample(
                        "Подписка удалена",
                        value={"message": "подписка удалена", "is_subscribed": False},
                        response_only=True,
                    ),
                ],
            ),
            400: OpenApiResponse(
                description="Не передан `course_id` или некорректный формат.",
                response=inline_serializer(
                    name="SubscriptionError",
                    fields={"error": serializers.CharField()},
                ),
                examples=[
                    OpenApiExample(
                        "course_id отсутствует",
                        value={"error": "Не указан course_id"},
                        response_only=True,
                    ),
                ],
            ),
            401: OpenApiResponse(description="Требуется авторизация (JWT)."),
            404: OpenApiResponse(description="Курс с указанным ID не найден."),
        },
        tags=["Подписки"],
    ),
)
class SubscriptionAPIView(APIView):
    """Toggle-подписка: POST /api/subscribe/ с body {"course_id": <id>}"""

    def post(self, request, *args, **kwargs):
        user = request.user
        course_id = request.data.get("course_id")

        if not course_id:
            return Response(
                {"error": "Не указан course_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        course_item = get_object_or_404(Course, id=course_id)
        subs_item = Subscription.objects.filter(user=user, course=course_item)

        if subs_item.exists():
            subs_item.delete()
            message = "подписка удалена"
            is_subscribed = False
        else:
            Subscription.objects.create(user=user, course=course_item)
            message = "подписка добавлена"
            is_subscribed = True

        return Response(
            {
                "message": message,
                "is_subscribed": is_subscribed,
            }
        )
