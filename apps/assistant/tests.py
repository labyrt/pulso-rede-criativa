from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .views import build_caption_prompt, local_editor_fallback, looks_canned

User = get_user_model()


class AssistantTests(TestCase):
    @override_settings(GEMINI_API_KEY="")
    def test_local_fallback_preserves_voice_without_canned_opening(self):
        user = User.objects.create_user(username="tina", email="tina@test.dev", password="VeryStrong!123")
        client = APIClient()
        client.force_authenticate(user)
        draft = "Estou criando uma coleção com materiais reaproveitados."

        response = client.post(
            "/api/v1/ai/caption/",
            {"draft": draft, "category": "fashion"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["provider"], "local")
        self.assertTrue(response.data["degraded"])
        self.assertEqual(response.data["suggestion"], draft)
        self.assertFalse(looks_canned(response.data["suggestion"]))

    def test_local_editor_only_normalizes_noise(self):
        self.assertEqual(
            local_editor_fallback("  texto   com   espaço\n\n\n\noutra linha  "),
            "texto com espaço\n\noutra linha",
        )

    def test_prompt_explicitly_rejects_formulaic_copy(self):
        prompt = build_caption_prompt(
            draft="Meu processo começa na matéria.",
            category="arte",
            tone="íntimo",
            mode="natural",
        )
        self.assertIn("não substituir essa voz", prompt.lower())
        self.assertIn("não force gancho", prompt.lower())
        self.assertIn("hashtags somente quando", prompt.lower())
        self.assertIn("Meu processo começa na matéria.", prompt)

    def test_canned_detector_rejects_previous_templates(self):
        self.assertTrue(looks_canned("Um recorte do processo antes de ele virar resultado: teste"))
        self.assertFalse(looks_canned("O material mudou enquanto eu trabalhava nele."))
