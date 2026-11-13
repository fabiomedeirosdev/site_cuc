from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from apps.editorial.models import EditorialGroup, Membership
from .models import DEFAULT_FOUNDERS_STORY, FoundersPage


def photo(width=1200, height=800):
    output = BytesIO()
    Image.new("RGB", (width, height), "#a57a3b").save(output, "PNG")
    return SimpleUploadedFile("fundadores.png", output.getvalue(), content_type="image/png")


class FoundersTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.media = TemporaryDirectory()
        cls.override = override_settings(MEDIA_ROOT=cls.media.name)
        cls.override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.override.disable()
        cls.media.cleanup()

    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.developer = users.objects.create_superuser(username="founders-developer", email="founders-dev@example.invalid", password="FoundersTest!81-Pass")
        cls.coordinator = users.objects.create_user(username="founders-coordinator", email="founders-coord@example.invalid")
        cls.reader = users.objects.create_user(username="founders-reader", email="founders-reader@example.invalid")
        group = EditorialGroup.objects.create(name="Grupo", slug="founders-group")
        Membership.objects.create(user=cls.coordinator, group=group, role="coordinator")

    def setUp(self):
        cache.clear()
        self.client = APIClient(enforce_csrf_checks=True)

    def login(self, user):
        self.client.force_login(user)
        self.token = self.client.get("/api/auth/csrf").json()["csrf_token"]

    def save(self, **data):
        return self.client.patch("/api/management/founders", data, format="multipart", HTTP_X_CSRFTOKEN=self.token)

    def test_public_page_starts_with_existing_history_and_has_no_private_author_fields(self):
        response = self.client.get("/api/founders")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["title"], "Nossos fundadores")
        self.assertEqual(response.json()["body"], DEFAULT_FOUNDERS_STORY)
        self.assertIsNone(response.json()["photo_url"])
        self.assertNotIn("updated_by", response.json())
        self.assertIn("no-store", response["Cache-Control"])

    def test_only_developer_can_read_and_edit_management(self):
        self.assertEqual(self.client.get("/api/management/founders").status_code, 403)
        for user in [self.coordinator, self.reader]:
            self.login(user)
            self.assertEqual(self.client.get("/api/management/founders").status_code, 403)
            self.assertEqual(self.save(title="Bloqueado").status_code, 403)
        self.assertEqual(FoundersPage.objects.get().title, "Nossos fundadores")

    def test_developer_changes_title_story_and_photo_visible_to_visitors(self):
        self.login(self.developer)
        response = self.save(title="Nossos fundadores e sua missão", body="Primeiro parágrafo.\n\nA história da comunidade.", photo=photo(), photo_alt="Foto dos nossos fundadores")
        self.assertEqual(response.status_code, 200, response.content)
        page = FoundersPage.objects.get()
        self.assertEqual(page.updated_by, self.developer)
        self.assertTrue(page.photo.name.endswith(".jpg"))
        with Image.open(page.photo.path) as image:
            self.assertEqual(image.size, (1200, 800))
            self.assertFalse(image.getexif())
        self.client.logout()
        data = self.client.get("/api/founders").json()
        self.assertEqual(data["title"], "Nossos fundadores e sua missão")
        self.assertEqual(data["body"], "Primeiro parágrafo.\n\nA história da comunidade.")
        self.assertTrue(data["photo_url"].startswith("/media/institutional/founders/"))

    def test_editing_only_text_keeps_uploaded_photo(self):
        self.login(self.developer)
        original = self.save(photo=photo(), photo_alt="Foto dos fundadores").json()["photo_url"]
        updated = self.save(title="Título atualizado")
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["photo_url"], original)

    def test_csrf_and_field_restrictions(self):
        self.login(self.developer)
        self.assertEqual(self.client.patch("/api/management/founders", {"title": "Sem CSRF"}, format="json").status_code, 403)
        for fields in [{"updated_by": self.reader.pk}, {"id": 2}, {"title": ""}, {"body": ""}, {"photo_alt": ""}, {"body": "x" * 50001}]:
            with self.subTest(fields=list(fields)):
                self.assertEqual(self.save(**fields).status_code, 400)

    def test_invalid_images_are_rejected_without_changing_the_page(self):
        self.login(self.developer)
        for image in [photo(400, 200), SimpleUploadedFile("fake.jpg", b"not-an-image", content_type="image/jpeg"), SimpleUploadedFile("large.png", b"x" * (5 * 1024 * 1024 + 1), content_type="image/png")]:
            self.assertEqual(self.save(photo=image).status_code, 400)
        self.assertFalse(FoundersPage.objects.get().photo)

    def test_only_one_page_can_exist(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            FoundersPage.objects.create(pk=2)

    def test_public_defaults_remain_available_if_record_is_missing(self):
        FoundersPage.objects.all().delete()
        self.assertEqual(self.client.get("/api/founders").json()["body"], DEFAULT_FOUNDERS_STORY)
        self.assertEqual(FoundersPage.objects.count(), 0)
        self.login(self.developer)
        self.assertEqual(self.client.get("/api/management/founders").status_code, 200)
        self.assertEqual(FoundersPage.objects.count(), 1)
