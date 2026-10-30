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
)
from users.views import PaymentViewSet, UserViewSet

router = DefaultRouter()
router.register(r"courses", CourseViewSet, basename="course")
router.register(r"users", UserViewSet, basename="user")
router.register(r"payments", PaymentViewSet, basename="payment")

urlpatterns = [
    path("admin/", admin.site.urls),
    # JWT
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # API
    path("api/", include(router.urls)),
    path("api/lessons/", LessonListAPIView.as_view(), name="lesson-list"),
    path("api/lessons/create/", LessonCreateAPIView.as_view(), name="lesson-create"),
    path(
        "api/lessons/<int:pk>/", LessonRetrieveAPIView.as_view(), name="lesson-detail"
    ),
    path(
        "api/lessons/<int:pk>/update/",
        LessonUpdateAPIView.as_view(),
        name="lesson-update",
    ),
    path(
        "api/lessons/<int:pk>/delete/",
        LessonDestroyAPIView.as_view(),
        name="lesson-delete",
    ),
]

# Для раздачи медиафайлов в режиме разработки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
