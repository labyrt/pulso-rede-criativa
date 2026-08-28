from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings


User = get_user_model()


@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class MobileChatHotfixTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="mobile_chat_tester",
            email="mobile-chat@test.dev",
            password="VeryStrong!123",
        )
        self.client.force_login(self.user)

    def test_messages_shell_loads_mobile_chat_hotfix_assets(self):
        response = self.client.get("/mensagens/")

        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertIn("webapp/mobile-chat-hotfix.css", html)
        self.assertIn("webapp/mobile-chat-hotfix.js", html)

    def test_mobile_chat_css_keeps_composer_above_bottom_navigation(self):
        source = Path(settings.BASE_DIR, "static", "webapp", "mobile-chat-hotfix.css").read_text(encoding="utf-8")

        self.assertIn('--pulso-mobile-nav-height: 66px', source)
        self.assertIn('env(safe-area-inset-bottom)', source)
        self.assertIn('body[data-section="messages"] .chat-form', source)
        self.assertIn('position: relative', source)
        self.assertIn('--pulso-visual-height', source)

    def test_mobile_chat_js_uses_clear_accessible_message_and_call_icons(self):
        source = Path(settings.BASE_DIR, "static", "webapp", "mobile-chat-hotfix.js").read_text(encoding="utf-8")

        self.assertIn('pulso-message-icon', source)
        self.assertIn('Iniciar ligação de áudio', source)
        self.assertIn('Iniciar ligação de vídeo', source)
        self.assertIn('window.visualViewport', source)
        self.assertIn('[data-nav="messages"]', source)
