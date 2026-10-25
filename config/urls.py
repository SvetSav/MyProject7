from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from lms.views import (
    CourseViewSet,
    LessonListCreateView,
    LessonRetrieveUpdateDestroyView,
)
from users.views import UserRetrieveUpdateView

router = DefaultRouter()
router.register(r"courses", CourseViewSet, basename="course")

urlpatterns = [
    path("admin/", admin.site.urls),
    # Маршруты для курсов (ViewSet)
    path("api/", include(router.urls)),
    # Маршруты для уроков (Generic-классы)
    path("api/lessons/", LessonListCreateView.as_view(), name="lesson-list"),
    path(
        "api/lessons/<int:pk>/",
        LessonRetrieveUpdateDestroyView.as_view(),
        name="lesson-detail",
    ),
    # Дополнительное задание: редактирование профиля пользователя
    path("api/users/<int:pk>/", UserRetrieveUpdateView.as_view(), name="user-detail"),
]

# Для раздачи медиафайлов в режиме разработки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
