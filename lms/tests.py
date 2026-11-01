from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.test import APITestCase

from lms.models import Course, Lesson, Subscription
from users.models import User


class ApiTests(APITestCase):
    def setUp(self):
        Group.objects.get_or_create(name="Moderators")

        self.owner = User.objects.create_user(
            email="owner@test.com", password="pass12345"
        )
        self.stranger = User.objects.create_user(
            email="stranger@test.com", password="pass12345"
        )
        self.moderator = User.objects.create_user(
            email="moder@test.com", password="pass12345"
        )
        self.moderator.groups.add(Group.objects.get(name="Moderators"))

        self.course = Course.objects.create(title="Курс владельца", owner=self.owner)

    def _token(self, user):
        r = self.client.post(
            "/api/token/",
            {
                "email": user.email,
                "password": "pass12345",
            },
            format="json",
        )
        return r.data["access"]

    # --- JWT ---
    def test_token_obtain(self):
        r = self.client.post(
            "/api/token/",
            {
                "email": "owner@test.com",
                "password": "pass12345",
            },
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("access", r.data)
        self.assertIn("refresh", r.data)

    # --- Анонимный доступ ---
    def test_anonymous_forbidden(self):
        r = self.client.get("/api/courses/")
        self.assertEqual(r.status_code, 401)

    # --- Регистрация ---
    def test_register(self):
        r = self.client.post(
            "/api/users/",
            {
                "email": "new@test.com",
                "password": "pass12345",
            },
            format="json",
        )
        self.assertEqual(r.status_code, 201)

    def test_register_duplicate_email(self):
        r = self.client.post(
            "/api/users/",
            {
                "email": "owner@test.com",
                "password": "pass12345",
            },
            format="json",
        )
        self.assertEqual(r.status_code, 400)

    # --- Модератор ---
    def test_moderator_can_update_any_course(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self._token(self.moderator)}"
        )
        r = self.client.patch(
            f"/api/courses/{self.course.id}/", {"title": "Изменено"}, format="json"
        )
        self.assertEqual(r.status_code, 200)

    def test_moderator_cannot_create_course(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self._token(self.moderator)}"
        )
        r = self.client.post("/api/courses/", {"title": "Новый"}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_moderator_cannot_delete_course(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self._token(self.moderator)}"
        )
        r = self.client.delete(f"/api/courses/{self.course.id}/")
        self.assertEqual(r.status_code, 403)

    # --- Владелец vs чужой ---
    def test_owner_sees_only_own_courses(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self._token(self.stranger)}"
        )
        r = self.client.get("/api/courses/")
        self.assertEqual(r.status_code, 200)
        # с пагинацией r.data = {'count': N, 'results': [...]}
        self.assertEqual(r.data["count"], 0)
        self.assertEqual(len(r.data["results"]), 0)

    def test_stranger_cannot_delete(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self._token(self.stranger)}"
        )
        r = self.client.delete(f"/api/courses/{self.course.id}/")
        self.assertIn(r.status_code, (403, 404))

    # --- lessons_count ---
    def test_course_lessons_count(self):
        Lesson.objects.create(course=self.course, title="У1", owner=self.owner)
        Lesson.objects.create(course=self.course, title="У2", owner=self.owner)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self._token(self.owner)}")
        r = self.client.get(f"/api/courses/{self.course.id}/")
        self.assertEqual(r.data["lessons_count"], 2)
        self.assertEqual(len(r.data["lessons"]), 2)

    # --- Профиль ---
    def test_own_profile_full(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self._token(self.owner)}")
        r = self.client.get(f"/api/users/{self.owner.id}/")
        self.assertIn("payments", r.data)

    def test_other_profile_public(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self._token(self.owner)}")
        r = self.client.get(f"/api/users/{self.stranger.id}/")
        self.assertNotIn("payments", r.data)
        self.assertNotIn("last_name", r.data)


class LessonCRUDTests(APITestCase):
    """CRUD уроков + проверка прав по ролям."""

    def setUp(self):
        self.owner = User.objects.create_user(
            email="owner@test.com", password="pass12345"
        )
        self.stranger = User.objects.create_user(
            email="stranger@test.com", password="pass12345"
        )
        self.moderator = User.objects.create_user(
            email="moder@test.com", password="pass12345"
        )
        g, _ = Group.objects.get_or_create(name="Moderators")
        self.moderator.groups.add(g)

        self.course = Course.objects.create(title="Курс", owner=self.owner)
        self.lesson = Lesson.objects.create(
            course=self.course,
            title="Урок владельца",
            video_link="https://youtube.com/watch?v=abc",
            owner=self.owner,
        )

    # --- CREATE ---
    def test_owner_can_create_lesson(self):
        self.client.force_authenticate(user=self.owner)
        data = {
            "course": self.course.id,
            "title": "Новый урок",
            "video_link": "https://youtube.com/watch?v=xyz",
        }
        response = self.client.post("/api/lessons/create/", data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Lesson.objects.count(), 2)
        # owner автоматически привязан
        new_lesson = Lesson.objects.latest("id")
        self.assertEqual(new_lesson.owner, self.owner)

    def test_create_lesson_with_wrong_link(self):
        self.client.force_authenticate(user=self.owner)
        data = {
            "course": self.course.id,
            "title": "Плохой урок",
            "video_link": "https://example.com/video",
        }
        response = self.client.post("/api/lessons/create/", data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("video_link", response.data)

    def test_moderator_cannot_create_lesson(self):
        self.client.force_authenticate(user=self.moderator)
        data = {"course": self.course.id, "title": "X"}
        response = self.client.post("/api/lessons/create/", data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_cannot_create_lesson(self):
        response = self.client.post("/api/lessons/create/", {"title": "X"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- READ (list) ---
    def test_owner_sees_only_own_lessons(self):
        Lesson.objects.create(course=self.course, title="Урок 2", owner=self.owner)
        self.client.force_authenticate(user=self.stranger)
        response = self.client.get("/api/lessons/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)

    def test_moderator_sees_all_lessons(self):
        Lesson.objects.create(course=self.course, title="Урок 2", owner=self.owner)
        self.client.force_authenticate(user=self.moderator)
        response = self.client.get("/api/lessons/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

    # --- READ (retrieve) ---
    def test_owner_can_retrieve_own_lesson(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(f"/api/lessons/{self.lesson.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Урок владельца")

    def test_stranger_cannot_retrieve_foreign_lesson(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.get(f"/api/lessons/{self.lesson.id}/")
        # get_queryset в RetrieveAPIView не фильтрует — доступ даёт permission
        self.assertIn(
            response.status_code,
            (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND),
        )

    def test_moderator_can_retrieve_any_lesson(self):
        self.client.force_authenticate(user=self.moderator)
        response = self.client.get(f"/api/lessons/{self.lesson.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # --- UPDATE ---
    def test_owner_can_update_own_lesson(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(
            f"/api/lessons/{self.lesson.id}/update/",
            {"title": "Обновлено"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.title, "Обновлено")

    def test_stranger_cannot_update_foreign_lesson(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.patch(
            f"/api/lessons/{self.lesson.id}/update/",
            {"title": "Взлом"},
        )
        self.assertIn(
            response.status_code,
            (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND),
        )

    def test_moderator_can_update_any_lesson(self):
        self.client.force_authenticate(user=self.moderator)
        response = self.client.patch(
            f"/api/lessons/{self.lesson.id}/update/",
            {"title": "Модератор"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # --- DELETE ---
    def test_owner_can_delete_own_lesson(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.delete(f"/api/lessons/{self.lesson.id}/delete/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Lesson.objects.filter(id=self.lesson.id).exists())

    def test_stranger_cannot_delete_foreign_lesson(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.delete(f"/api/lessons/{self.lesson.id}/delete/")
        self.assertIn(
            response.status_code,
            (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND),
        )

    def test_moderator_cannot_delete_lesson(self):
        self.client.force_authenticate(user=self.moderator)
        response = self.client.delete(f"/api/lessons/{self.lesson.id}/delete/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class SubscriptionTests(APITestCase):
    """Тесты toggle-подписки и поля is_subscribed."""

    def setUp(self):
        self.user = User.objects.create_user(email="u@test.com", password="pass12345")
        self.course = Course.objects.create(title="Курс", owner=self.user)

    def test_subscribe_creates_record(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post("/api/subscribe/", {"course_id": self.course.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "подписка добавлена")
        self.assertTrue(
            Subscription.objects.filter(user=self.user, course=self.course).exists()
        )

    def test_second_subscribe_removes_record(self):
        Subscription.objects.create(user=self.user, course=self.course)
        self.client.force_authenticate(user=self.user)
        response = self.client.post("/api/subscribe/", {"course_id": self.course.id})
        self.assertEqual(response.data["message"], "подписка удалена")
        self.assertFalse(
            Subscription.objects.filter(user=self.user, course=self.course).exists()
        )

    def test_subscribe_without_course_id(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post("/api/subscribe/", {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_subscribe_nonexistent_course(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post("/api/subscribe/", {"course_id": 99999})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_subscribe_requires_auth(self):
        response = self.client.post("/api/subscribe/", {"course_id": self.course.id})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unique_constraint(self):
        Subscription.objects.create(user=self.user, course=self.course)
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            Subscription.objects.create(user=self.user, course=self.course)

    def test_is_subscribed_field_true(self):
        Subscription.objects.create(user=self.user, course=self.course)
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"/api/courses/{self.course.id}/")
        self.assertTrue(response.data["is_subscribed"])

    def test_is_subscribed_field_false(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"/api/courses/{self.course.id}/")
        self.assertFalse(response.data["is_subscribed"])


class CoursePermissionsTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="o@t.com", password="pass12345")
        self.moderator = User.objects.create_user(email="m@t.com", password="pass12345")
        g, _ = Group.objects.get_or_create(name="Moderators")
        self.moderator.groups.add(g)
        self.course = Course.objects.create(title="Курс", owner=self.owner)

    def test_moderator_cannot_create_course(self):
        self.client.force_authenticate(user=self.moderator)
        r = self.client.post("/api/courses/", {"title": "X"})
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_moderator_cannot_delete_course(self):
        self.client.force_authenticate(user=self.moderator)
        r = self.client.delete(f"/api/courses/{self.course.id}/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_moderator_can_update_course(self):
        self.client.force_authenticate(user=self.moderator)
        r = self.client.patch(f"/api/courses/{self.course.id}/", {"title": "mod"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_stranger_cannot_see_foreign_course(self):
        stranger = User.objects.create_user(email="s@t.com", password="pass12345")
        self.client.force_authenticate(user=stranger)
        r = self.client.get(f"/api/courses/{self.course.id}/")
        self.assertIn(r.status_code, (403, 404))


class JWTTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="u@t.com", password="pass12345")

    def test_obtain_token(self):
        r = self.client.post(
            "/api/token/",
            {
                "email": "u@t.com",
                "password": "pass12345",
            },
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("access", r.data)
        self.assertIn("refresh", r.data)

    def test_invalid_credentials(self):
        r = self.client.post(
            "/api/token/",
            {
                "email": "u@t.com",
                "password": "wrong",
            },
            format="json",
        )
        self.assertEqual(r.status_code, 401)

    def test_refresh_token(self):
        r = self.client.post(
            "/api/token/",
            {
                "email": "u@t.com",
                "password": "pass12345",
            },
            format="json",
        )
        refresh = r.data["refresh"]
        r2 = self.client.post(
            "/api/token/refresh/", {"refresh": refresh}, format="json"
        )
        self.assertEqual(r2.status_code, 200)
        self.assertIn("access", r2.data)


def test_course_create_with_preview(self):
    from django.core.files.uploadedfile import SimpleUploadedFile

    self.client.force_authenticate(user=self.owner)
    image = SimpleUploadedFile(
        "test.jpg",
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01",  # минимальный JPEG
        content_type="image/jpeg",
    )
    r = self.client.post(
        "/api/courses/",
        {
            "title": "С картинкой",
            "preview": image,
        },
        format="multipart",
    )
    self.assertEqual(r.status_code, 201)


def test_validator_rejects_fake_youtube(self):
    self.client.force_authenticate(user=self.owner)
    for bad_url in [
        "https://youtube.com.evil.com/watch",
        "https://fakeyoutube.com/v",
        "https://youtube.co/v",
    ]:
        r = self.client.post(
            "/api/lessons/create/",
            {
                "course": self.course.id,
                "title": "x",
                "video_link": bad_url,
            },
        )
        self.assertEqual(r.status_code, 400, f"{bad_url} should be rejected")
