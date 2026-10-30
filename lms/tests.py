from django.contrib.auth.models import Group
from rest_framework.test import APITestCase

from lms.models import Course, Lesson
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
        self.assertEqual(len(r.data), 0)  # курс владельца не виден

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
