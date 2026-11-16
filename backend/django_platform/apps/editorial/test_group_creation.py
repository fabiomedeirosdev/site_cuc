from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from .models import EditorialGroup, Membership


def photo(width=1600, height=1000, image_format="PNG"):
    output = BytesIO()
    Image.new("RGB", (width, height), "#ac842f").save(output, image_format)
    return SimpleUploadedFile("grupo.png", output.getvalue(), content_type="image/png")


class GroupCreationTests(TestCase):
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
        cls.admin = users.objects.create_superuser(username="group-admin", email="group-admin@example.invalid", password="GroupTest!8")
        cls.coordinator = users.objects.create_user(username="group-coordinator", email="group-coordinator@example.invalid")
        cls.facilitator = users.objects.create_user(username="group-facilitator", email="group-facilitator@example.invalid")
        cls.reader = users.objects.create_user(username="group-reader", email="group-reader@example.invalid")
        cls.group = EditorialGroup.objects.create(name="Grupo existente", slug="creation-existing", description="Grupo de teste")
        cls.foreign = EditorialGroup.objects.create(name="Outro grupo", slug="creation-foreign", description="Outro escopo")
        Membership.objects.create(group=cls.group, user=cls.coordinator, role="coordinator")
        Membership.objects.create(group=cls.group, user=cls.facilitator, role="columnist")

    def setUp(self):
        cache.clear()
        self.client = APIClient(enforce_csrf_checks=True)
        self.base = "/api/management/groups"

    def login(self, user):
        self.client.force_login(user)
        self.token = self.client.get("/api/auth/csrf").json()["csrf_token"]

    def create(self, **changes):
        data = {"name": "Novo grupo de oração", "description": "Uma nova missão", "cover": "prayer", **changes}
        return self.client.post(self.base, data, format="multipart", HTTP_X_CSRFTOKEN=self.token)

    def test_only_active_admin_and_assigned_coordinator_can_create(self):
        self.assertEqual(self.client.post(self.base, {}).status_code, 403)
        for user in [self.facilitator, self.reader]:
            self.login(user)
            self.assertFalse(self.client.get("/api/auth/me").json()["can_create_groups"])
            self.assertEqual(self.create().status_code, 403)
        self.facilitator.groups.add(Group.objects.get(name="Coordenadores"))
        self.login(self.facilitator)
        self.assertEqual(self.create().status_code, 403)
        Membership.objects.filter(user=self.coordinator).delete()
        self.login(self.coordinator)
        self.assertEqual(self.create().status_code, 403)

    def test_admin_creates_group_with_existing_cover(self):
        self.login(self.admin)
        response = self.create(position=7)
        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        self.assertEqual(data["cover"], "prayer")
        self.assertIsNone(data["cover_url"])
        self.assertEqual(data["position"], 7)
        self.assertTrue(data["is_active"])
        self.assertEqual(self.client.get(f"/api/groups/{data['slug']}").status_code, 200)

    def test_coordinator_automatically_manages_created_group(self):
        self.login(self.coordinator)
        response = self.create()
        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        self.assertTrue(Membership.objects.filter(group_id=data["id"], user=self.coordinator, role="coordinator", is_public=False).exists())
        self.assertIn(data["id"], [group["id"] for group in self.client.get(self.base).json()])
        edit = self.client.patch(f"{self.base}/{data['id']}", {"description": "Descrição revisada"}, format="json", HTTP_X_CSRFTOKEN=self.token)
        self.assertEqual(edit.status_code, 200)

    def test_coordinator_cannot_override_scope_or_administrative_controls(self):
        self.login(self.coordinator)
        self.assertEqual(self.create(position=1).status_code, 403)
        self.assertEqual(self.create(is_active=False).status_code, 403)
        self.assertEqual(self.create(slug="manual", role="administrator").status_code, 400)
        response = self.client.patch(f"{self.base}/{self.foreign.pk}", {"custom_cover": photo(), "cover_alt": "Foto"}, format="multipart", HTTP_X_CSRFTOKEN=self.token)
        self.assertEqual(response.status_code, 404)

    def test_csrf_is_required_for_group_creation(self):
        self.login(self.admin)
        response = self.client.post(self.base, {"name": "Sem CSRF", "description": "Teste"}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_duplicate_names_receive_unique_stable_slugs(self):
        self.login(self.admin)
        first = self.create().json()
        second = self.create().json()
        self.assertNotEqual(first["slug"], second["slug"])
        self.assertTrue(first["slug"].startswith("novo-grupo-de-oracao-"))
        response = self.client.patch(f"{self.base}/{first['id']}", {"name": "Nome revisado"}, format="json", HTTP_X_CSRFTOKEN=self.token)
        self.assertEqual(response.json()["slug"], first["slug"])

    def test_upload_is_normalized_to_webp_and_appears_in_public_api(self):
        self.login(self.coordinator)
        response = self.create(custom_cover=photo(), cover_alt="Pessoas em oração")
        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        group = EditorialGroup.objects.get(pk=data["id"])
        self.assertTrue(data["cover_url"].endswith(".webp"))
        with Image.open(group.custom_cover.path) as image:
            self.assertEqual(image.size, (1600, 900))
            self.assertEqual(image.format, "WEBP")
            self.assertFalse(image.getexif())
        public = self.client.get(f"/api/groups/{group.slug}").json()
        self.assertEqual(public["cover_url"], data["cover_url"])
        image = self.client.get(public["cover_url"])
        self.assertEqual(image.status_code, 200)
        self.assertEqual(image["Content-Type"], "image/webp")
        self.assertEqual(b"".join(image.streaming_content)[:4], b"RIFF")
        self.assertEqual(public["cover_alt"], "Pessoas em oração")
        self.assertNotIn("custom_cover", public)

    def test_image_limits_and_actual_file_content_are_checked(self):
        self.login(self.admin)
        invalid = [photo(799, 450), photo(800, 449), photo(4097, 450), photo(800, 4097),
            SimpleUploadedFile("fake.jpg", b"not-an-image", content_type="image/jpeg"),
            SimpleUploadedFile("vector.svg", b"<svg></svg>", content_type="image/svg+xml"),
            SimpleUploadedFile("huge.png", b"x" * (5 * 1024 * 1024 + 1), content_type="image/png")]
        for upload in invalid:
            with self.subTest(upload=upload.name, size=upload.size):
                self.assertEqual(self.create(custom_cover=upload, cover_alt="Descrição").status_code, 400)

    def test_minimum_image_is_accepted_without_upscaling(self):
        self.login(self.admin)
        response = self.create(custom_cover=photo(800, 450), cover_alt="Foto pequena")
        self.assertEqual(response.status_code, 201, response.content)
        group = EditorialGroup.objects.get(pk=response.json()["id"])
        with Image.open(group.custom_cover.path) as image:
            self.assertEqual(image.size, (800, 450))

    def test_custom_image_requires_description_and_rejects_conflicting_source(self):
        self.login(self.admin)
        self.assertEqual(self.create(custom_cover=photo()).status_code, 400)
        self.assertEqual(self.create(custom_cover=photo(), cover_alt="Foto", remove_custom_cover=True).status_code, 400)

    def test_replace_cover_and_restore_any_original_preset(self):
        self.login(self.coordinator)
        original = self.create(custom_cover=photo(), cover_alt="Original").json()
        path = f"{self.base}/{original['id']}"
        response = self.client.patch(path, {"custom_cover": photo(1200, 900), "cover_alt": "Nova foto"}, format="multipart", HTTP_X_CSRFTOKEN=self.token)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertNotEqual(original["cover_url"], response.json()["cover_url"])
        response = self.client.patch(path, {"cover": "family", "remove_custom_cover": True}, format="json", HTTP_X_CSRFTOKEN=self.token)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIsNone(response.json()["cover_url"])
        self.assertEqual(response.json()["cover"], "family")
        self.assertEqual(response.json()["cover_alt"], "")
