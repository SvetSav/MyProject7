from rest_framework import status
from rest_framework.test import APITestCase

from lms.models import Course
from users.models import Payment, User


class UserAPITests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email="owner@test.com",
            password="pass12345",
            first_name="Иван",
            last_name="Петров",
        )
        self.stranger = User.objects.create_user(
            email="stranger@test.com", password="pass12345"
        )
        self.course = Course.objects.create(title="Курс", owner=self.owner)
        self.payment = Payment.objects.create(
            user=self.owner,
            paid_course=self.course,
            amount=1000,
            payment_method="cash",
        )

    # --- Регистрация ---
    def test_register_new_user(self):
        response = self.client.post(
            "/api/users/",
            {
                "email": "new@test.com",
                "password": "pass12345",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email="new@test.com").exists())

    def test_register_duplicate_email(self):
        response = self.client.post(
            "/api/users/",
            {
                "email": "owner@test.com",
                "password": "pass12345",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- Профиль ---
    def test_own_profile_full_info(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(f"/api/users/{self.owner.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("payments", response.data)
        self.assertEqual(response.data["last_name"], "Петров")

    def test_other_profile_public(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.get(f"/api/users/{self.owner.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("payments", response.data)
        self.assertNotIn("last_name", response.data)

    def test_edit_own_profile(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(
            f"/api/users/{self.owner.id}/",
            {"first_name": "Новое"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_cannot_edit_other_profile(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.patch(
            f"/api/users/{self.owner.id}/",
            {"first_name": "Взлом"},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # --- Платежи ---
    def test_payments_list(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get("/api/payments/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_payments_filter_by_method(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get("/api/payments/?payment_method=cash")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_payments_filter_by_course(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(f"/api/payments/?course={self.course.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_payments_requires_auth(self):
        response = self.client.get("/api/payments/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
