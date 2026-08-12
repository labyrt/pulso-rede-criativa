from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

User = get_user_model()


class AssistantTests(TestCase):
    def test_local_fallback_works_without_api_key(self):
        user = User.objects.create_user(username="tina", email="tina@test.dev", password="VeryStrong!123")
        client = APIClient()
        client.force_authenticate(user)
        response = client.post("/api/v1/ai/caption/", {"draft": "Estou criando uma coleção com materiais reaproveitados.", "category": "fashion"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["provider"], "local")
        self.assertIn("coleção", response.data["suggestion"])
