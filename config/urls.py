from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from lms.views import (
    CourseViewSet,
    LessonCreateAPIView,
    LessonDestroyAPIView,
    LessonListAPIView,
    LessonRetrieveAPIView,
    LessonUpdateAPIView,
    SubscriptionAPIView,
)
from users.views import PaymentViewSet, UserViewSet

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

from drf_spectacular.utils import extend_schema

from users.views import PaymentCreateAPIView, PaymentStatusAPIView
from django.http import JsonResponse

router = DefaultRouter()
router.register(r"courses", CourseViewSet, basename="course")
router.register(r"users", UserViewSet, basename="user")
router.register(r"payments", PaymentViewSet, basename="payment")

urlpatterns = [
    path('admin/', admin.site.urls),

    # --- JWT ---
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # --- Документация ---
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # маршруты платежей
    path('api/payments/create/', PaymentCreateAPIView.as_view(), name='payment-create'),
    path('api/payments/status/<str:session_id>/', PaymentStatusAPIView.as_view(), name='payment-status'),
    path('api/payments/success/', lambda r: JsonResponse({'status': 'success'}), name='payment-success'),
    path('api/payments/cancel/', lambda r: JsonResponse({'status': 'cancel'}), name='payment-cancel'),

    # --- Уроки (Generic) ---
    path('api/lessons/', LessonListAPIView.as_view(), name='lesson-list'),
    path('api/lessons/create/', LessonCreateAPIView.as_view(), name='lesson-create'),
    path('api/lessons/<int:pk>/', LessonRetrieveAPIView.as_view(), name='lesson-detail'),
    path('api/lessons/<int:pk>/update/', LessonUpdateAPIView.as_view(), name='lesson-update'),
    path('api/lessons/<int:pk>/delete/', LessonDestroyAPIView.as_view(), name='lesson-delete'),

    # --- Подписка ---
    path('api/subscribe/', SubscriptionAPIView.as_view(), name='subscribe'),
    # Роутер
    path('api/', include(router.urls)),
]

urlpatterns += [
    path('api/payments/success/', lambda r: JsonResponse({'status': 'success'}), name='payment-success'),
    path('api/payments/cancel/', lambda r: JsonResponse({'status': 'cancel'}), name='payment-cancel'),
]

# Для раздачи медиафайлов в режиме разработки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


TokenObtainPairView = extend_schema(
    summary='Получить JWT-токен',
    description='Возвращает пару `access` и `refresh` токенов по email и паролю.',
    tags=['Аутентификация'],
)(TokenObtainPairView)

TokenRefreshView = extend_schema(
    summary='Обновить access-токен',
    description='Принимает `refresh`-токен и возвращает новый `access`-токен.',
    tags=['Аутентификация'],
)(TokenRefreshView)
