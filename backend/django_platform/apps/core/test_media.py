from io import BytesIO
from tempfile import TemporaryDirectory

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import SimpleTestCase, override_settings
from PIL import Image

from .media import public_image_url


@override_settings(DEBUG=False, SECURE_SSL_REDIRECT=False)
class PublicImageTests(SimpleTestCase):
    def test_public_uploads_return_image_bytes_in_production(self):
        with TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            for folder, fmt, extension in [("covers", "WEBP", "webp"), ("group-covers", "WEBP", "webp"), ("institutional/founders", "JPEG", "jpg")]:
                with self.subTest(folder=folder):
                    output = BytesIO()
                    Image.new("RGB", (20, 20), "red").save(output, fmt)
                    name = default_storage.save(f"{folder}/2026/11/photo.{extension}", ContentFile(output.getvalue()))
                    response = self.client.get(public_image_url(ContentFile(b"", name=name)))
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response["Content-Type"], "image/webp" if fmt == "WEBP" else "image/jpeg")
                    self.assertEqual(response["X-Content-Type-Options"], "nosniff")
                    self.assertEqual(b"".join(response.streaming_content), output.getvalue())
                    response.close()

    def test_missing_private_and_unsafe_paths_are_not_served(self):
        for name in ["covers/missing.webp", "avatars/private.webp", "notices/private.jpg", "newsletters/private.jpg", "covers/../avatars/private.webp", "covers/file.html", "covers/..\\private.webp"]:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(f"/api/public-images/{name}").status_code, 404)

    def test_empty_image_has_no_url(self):
        self.assertIsNone(public_image_url(None))
