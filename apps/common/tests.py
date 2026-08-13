import os
from io import BytesIO
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from PIL import Image

from .media import store_image


def valid_image():
    buffer = BytesIO()
    Image.new("RGB", (64, 64), "#5375ff").save(buffer, format="PNG")
    return SimpleUploadedFile("perfil.png", buffer.getvalue(), content_type="image/png")


class CloudinaryStorageTests(SimpleTestCase):
    @patch("apps.common.media.requests.post")
    @patch.dict(os.environ, {"CLOUDINARY_URL": "cloudinary://public-key:private-secret@pulso-cloud"})
    def test_validated_upload_uses_signed_server_side_request(self, post):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"secure_url": "https://res.cloudinary.com/pulso-cloud/image/upload/test.png"}
        post.return_value = response

        url = store_image(valid_image(), "posts")

        self.assertTrue(url.startswith("https://res.cloudinary.com/"))
        args, kwargs = post.call_args
        self.assertEqual(args[0], "https://api.cloudinary.com/v1_1/pulso-cloud/image/upload")
        self.assertEqual(kwargs["data"]["api_key"], "public-key")
        self.assertIn("signature", kwargs["data"])
        self.assertNotIn("private-secret", str(kwargs))
