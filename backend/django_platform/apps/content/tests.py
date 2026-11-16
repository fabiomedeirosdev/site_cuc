from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from apps.editorial.models import EditorialGroup, Membership
from .models import Article, CoverImage


def photo_bytes():
    output = BytesIO()
    Image.new("RGB", (40, 30), "gold").save(output, "PNG")
    return output.getvalue()


class ContentTests(TestCase):
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
        User = get_user_model()
        cls.author = User.objects.create_user(username="writer", email="writer@example.invalid", password="OnlyTestPassword!81")
        cls.other = User.objects.create_user(username="other-writer", email="other-writer@example.invalid", password="OnlyTestPassword!81")
        cls.reader = User.objects.create_user(username="subscriber", email="subscriber@example.invalid", password="OnlyTestPassword!81")
        cls.coordinator = User.objects.create_user(username="coordinator", email="coordinator@example.invalid", password="OnlyTestPassword!81")
        cls.admin = User.objects.create_superuser(username="admin", email="admin@example.invalid", password="OnlyTestPassword!81")
        cls.group = EditorialGroup.objects.create(name="Formação de teste", slug="formacao-teste", description="Teste")
        cls.foreign = EditorialGroup.objects.create(name="Outro escopo", slug="outro-escopo", description="Teste")
        cls.link = Membership.objects.create(group=cls.group, user=cls.author, role="columnist")
        Membership.objects.create(group=cls.group, user=cls.other, role="columnist")
        Membership.objects.create(group=cls.group, user=cls.coordinator, role="coordinator")
        cls.reader.groups.add(Group.objects.get(name="Assinantes"))
        cls.cover = CoverImage.objects.create(owner=cls.author, file=ContentFile(photo_bytes(), name="cover.png"))
        cls.article = Article.objects.create(author=cls.author, group=cls.group, title="Rascunho", body="Texto de teste", cover=cls.cover, cover_alt="Foto de teste")

    def setUp(self):
        cache.clear()
        self.client = APIClient(enforce_csrf_checks=True)
        self.path = f"/api/editorial/articles/{self.article.pk}"

    def session(self, user):
        self.client.force_login(user)
        self.token = self.client.get("/api/auth/csrf").json()["csrf_token"]

    def write(self, method, path, data=None):
        return getattr(self.client, method)(path, data or {}, format="json", HTTP_X_CSRFTOKEN=self.token)

    def publish(self, audience="public"):
        self.session(self.author)
        response = self.write("patch", self.path, {"status": "published", "audience": audience, "video_url": "https://youtu.be/abcdefghijk"})
        self.assertEqual(response.status_code, 200, response.content)
        return response

    def test_only_assigned_columnists_or_admin_can_write(self):
        for user in [self.reader]:
            self.session(user)
            self.assertEqual(self.write("post", "/api/editorial/articles", {"title": "Inválido", "group": self.group.pk, "body": "Texto"}).status_code, 403)
            self.assertEqual(self.client.get("/api/editorial/author-groups").json(), [])
        self.reader.groups.add(Group.objects.get(name="Facilitadores"))
        self.assertEqual(self.write("post", "/api/editorial/articles", {}).status_code, 403)

    def test_anonymous_editor_is_closed(self):
        self.assertEqual(self.client.get(self.path).status_code, 403)
        self.assertEqual(self.client.post("/api/editorial/covers").status_code, 403)

    def test_author_can_create_edit_publish_and_delete_own_article(self):
        self.session(self.author)
        response = self.write("post", "/api/editorial/articles", {"title": "Novo artigo", "group": self.group.pk, "body": "Um texto **formatado**."})
        self.assertEqual(response.status_code, 201, response.content)
        path = f"/api/editorial/articles/{response.json()['id']}"
        self.assertEqual(self.write("patch", path, {"title": "Título editado"}).json()["title"], "Título editado")
        self.publish()
        self.assertEqual(self.client.get(f"/api/articles/{self.article.pk}").json()["body"], "Texto de teste")
        self.assertEqual(self.write("delete", path).status_code, 204)
        self.assertEqual(self.client.get(path).status_code, 404)

    def test_other_author_cannot_read_edit_or_delete_draft_even_in_same_group(self):
        self.session(self.other)
        for method in ["get", "patch", "delete"]:
            response = self.client.get(self.path) if method == "get" else self.write(method, self.path, {"title": "Outra pessoa"})
            self.assertEqual(response.status_code, 404)

    def test_coordinator_manages_facilitator_content_only_in_assigned_groups(self):
        outside = Article.objects.create(author=self.other, group=self.foreign, title="Fora do escopo", body="Outro grupo")
        self.session(self.coordinator)
        self.assertEqual(self.client.get(self.path).status_code, 200)
        self.assertEqual(self.write("patch", self.path, {"title": "Revisado pela coordenação", "status": "published"}).status_code, 200)
        self.article.refresh_from_db()
        self.assertEqual(self.article.author_id, self.author.pk)
        self.link.delete()
        self.assertEqual(self.write("patch", self.path, {"group": self.group.pk, "title": "Revisão do arquivo"}).status_code, 200)
        self.assertEqual(self.write("patch", self.path, {"group": self.foreign.pk}).status_code, 400)
        for method in ["patch", "delete"]:
            self.assertEqual(self.write(method, f"/api/editorial/articles/{outside.pk}", {"title": "Inválido"}).status_code, 404)
        self.assertEqual(self.write("delete", self.path).status_code, 204)

    def test_coordinator_can_replace_cover_and_facilitator_can_keep_editing(self):
        self.session(self.coordinator)
        upload = SimpleUploadedFile("review.png", photo_bytes(), "image/png")
        response = self.client.post("/api/editorial/covers", {"file": upload}, format="multipart", HTTP_X_CSRFTOKEN=self.token)
        self.assertEqual(response.status_code, 201)
        image = self.client.get(response.json()["url"])
        self.assertEqual(image.status_code, 200)
        self.assertEqual(image["Content-Type"], "image/webp")
        self.assertEqual(b"".join(image.streaming_content)[:4], b"RIFF")
        cover_id = response.json()["id"]
        self.assertEqual(self.write("patch", self.path, {"cover": cover_id}).status_code, 200)
        self.session(self.author)
        self.assertEqual(self.write("patch", self.path, {"body": "Texto revisado", "cover": cover_id}).status_code, 200)

    def test_coordinator_removal_immediately_revokes_access_to_others_content(self):
        self.session(self.coordinator)
        Membership.objects.filter(group=self.group, user=self.coordinator).delete()
        self.assertEqual(self.client.get(self.path).status_code, 404)

    def test_admin_can_manage_others_content_without_changing_authorship(self):
        self.session(self.admin)
        self.assertEqual(self.write("patch", self.path, {"title": "Revisado"}).status_code, 200)
        self.article.refresh_from_db()
        self.assertEqual(self.article.author_id, self.author.pk)

    def test_scope_and_foreign_cover_are_validated(self):
        self.session(self.other)
        for data in [{"title": "Escopo", "body": "Texto", "group": self.foreign.pk}, {"title": "Capa alheia", "body": "Texto", "group": self.group.pk, "cover": str(self.cover.pk)}]:
            self.assertEqual(self.write("post", "/api/editorial/articles", data).status_code, 400)

    def test_authorship_and_unknown_fields_cannot_be_injected(self):
        self.session(self.author)
        for data in [{"author": self.other.pk}, {"published_at": "2026-01-01"}, {"is_superuser": True}]:
            self.assertEqual(self.write("patch", self.path, data).status_code, 400)

    def test_publication_requires_cover_description_and_real_content(self):
        self.session(self.author)
        for data in [{"status": "published", "cover": None}, {"status": "published", "cover_alt": ""}, {"body": "", "video_url": ""}, {"title": "   "}]:
            self.assertEqual(self.write("patch", self.path, data).status_code, 400)

    def test_draft_is_not_public_and_unpublish_and_delete_remove_it_from_feed(self):
        self.assertEqual(self.client.get(f"/api/articles/{self.article.pk}").status_code, 404)
        self.publish()
        self.assertEqual(self.client.get("/api/articles").json()["count"], 1)
        self.assertEqual(self.write("patch", self.path, {"status": "draft"}).status_code, 200)
        self.assertEqual(self.client.get("/api/articles").json()["count"], 0)
        self.publish()
        self.write("delete", self.path)
        self.assertEqual(self.client.get("/api/articles").json()["count"], 0)

    def test_public_feed_contains_metadata_not_body_or_raw_video_link(self):
        self.publish()
        body = self.client.get("/api/articles").json()["results"][0]
        self.assertIn("cover_url", body)
        self.assertNotIn("body", body)
        self.assertNotIn("video_url", body)
        self.assertNotIn(self.author.email, str(body))
        self.assertEqual(self.client.get("/api/articles?q=ausente").json()["count"], 0)

    def test_exclusive_body_and_video_are_hidden_even_for_authenticated_subscribers(self):
        self.publish("members")
        self.session(self.reader)
        body = self.client.get(f"/api/articles/{self.article.pk}").json()
        self.assertTrue(body["is_locked"])
        self.assertIsNone(body["body"])
        self.assertIsNone(body["video_embed_url"])

    def test_youtube_links_are_normalized_to_allowlisted_embeds(self):
        self.publish()
        response = self.client.get(f"/api/articles/{self.article.pk}").json()
        self.assertEqual(response["video_embed_url"], "https://www.youtube-nocookie.com/embed/abcdefghijk")
        for url in ["https://youtube.com/shorts/abcdefghijk", "https://www.youtube.com/watch?v=abcdefghijk&t=5", "https://www.youtube.com/live/abcdefghijk"]:
            self.assertEqual(self.write("patch", self.path, {"video_url": url}).status_code, 200)

    def test_video_html_javascript_foreign_hosts_credentials_and_invalid_ids_are_rejected(self):
        self.session(self.author)
        for url in ["javascript:alert(1)", "https://youtube.com.evil.invalid/watch?v=abcdefghijk", "https://evil.invalid/abcdefghijk", "https://youtube.com@evil.invalid/watch?v=abcdefghijk", "https://www.youtube.com:444/watch?v=abcdefghijk", "https://youtu.be/invalid", '<iframe src="https://evil.invalid"></iframe>']:
            self.assertEqual(self.write("patch", self.path, {"video_url": url}).status_code, 400, url)

    def test_long_text_is_supported_and_bounded(self):
        self.session(self.author)
        self.assertEqual(self.write("patch", self.path, {"body": "A" * 150000}).status_code, 200)
        self.assertEqual(self.write("patch", self.path, {"body": "A" * 200001}).status_code, 400)

    def test_revoking_membership_or_deactivating_author_or_group_closes_editor_and_publication(self):
        self.publish()
        self.link.delete()
        self.assertEqual(self.client.get(self.path).status_code, 404)
        self.assertEqual(self.client.get("/api/articles").json()["count"], 0)
        Membership.objects.create(group=self.group, user=self.author, role="columnist")
        self.group.is_active = False
        self.group.save()
        self.assertEqual(self.client.get(self.path).status_code, 404)
        self.assertEqual(self.client.get("/api/articles").json()["count"], 0)

    def test_photo_upload_is_reencoded_and_preserves_only_a_generated_filename(self):
        self.session(self.author)
        upload = SimpleUploadedFile("original.png", photo_bytes(), "image/png")
        response = self.client.post("/api/editorial/covers", {"file": upload}, format="multipart", HTTP_X_CSRFTOKEN=self.token)
        self.assertEqual(response.status_code, 201, response.content)
        self.assertNotIn("original", response.json()["url"])
        cover = CoverImage.objects.get(pk=response.json()["id"])
        with Image.open(cover.file) as photo:
            self.assertEqual(photo.format, "WEBP")

    def test_svg_and_oversized_photos_and_subscriber_upload_are_rejected(self):
        self.session(self.author)
        for upload in [SimpleUploadedFile("x.svg", b'<svg><script>alert(1)</script></svg>', "image/svg+xml"), SimpleUploadedFile("large.jpg", b"0" * (5 * 1024 * 1024 + 1), "image/jpeg")]:
            self.assertEqual(self.client.post("/api/editorial/covers", {"file": upload}, format="multipart", HTTP_X_CSRFTOKEN=self.token).status_code, 400)
        self.session(self.reader)
        self.assertEqual(self.client.post("/api/editorial/covers", {"file": SimpleUploadedFile("x.png", photo_bytes())}, format="multipart", HTTP_X_CSRFTOKEN=self.token).status_code, 403)

    def test_csrf_is_required_for_content_writes(self):
        self.session(self.author)
        self.assertEqual(self.client.patch(self.path, {"title": "Sem CSRF"}, format="json").status_code, 403)
