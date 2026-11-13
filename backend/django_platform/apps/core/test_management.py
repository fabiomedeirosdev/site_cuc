from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.billing.models import Checkout, ConsumerRequest, Subscription
from apps.content.models import Article, CoverImage
from apps.editorial.models import EditorialGroup, Membership


class ManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.admin = users.objects.create_superuser(username="panel-admin", email="admin@example.invalid", password="PanelTest!92-Pass")
        cls.coordinator = users.objects.create_user(username="panel-coordinator", email="coordinator@example.invalid")
        cls.author = users.objects.create_user(username="panel-author", email="author@example.invalid")
        cls.reader = users.objects.create_user(username="panel-reader", email="reader@example.invalid")
        cls.group = EditorialGroup.objects.create(name="Painel", slug="panel", description="Grupo de teste")
        cls.foreign = EditorialGroup.objects.create(name="Outro grupo", slug="panel-other", description="Outro escopo")
        Membership.objects.create(user=cls.coordinator, group=cls.group, role="coordinator")
        cls.author_link = Membership.objects.create(user=cls.author, group=cls.group, role="columnist")
        cls.cover = CoverImage.objects.create(owner=cls.author, file="covers/test.png")
        cls.article = Article.objects.create(author=cls.author, group=cls.group, title="Publicação", body="Texto exclusivo", audience="members", status="published", published_at=timezone.now(), cover=cls.cover, cover_alt="Capa")
        cls.other_article = Article.objects.create(author=cls.admin, group=cls.foreign, title="Outro grupo", body="Texto", status="published", published_at=timezone.now(), cover=cls.cover)
        cls.draft = Article.objects.create(author=cls.author, group=cls.group, title="Rascunho", body="Texto", cover=cls.cover)
        checkout = Checkout.objects.create(legal_version="test")
        cls.subscription = Subscription.objects.create(provider_id="panel-test", checkout=checkout, user=cls.reader, email=cls.reader.email, paid_until=timezone.now() + timedelta(days=5))
        cls.ticket = ConsumerRequest.objects.create(subscription=cls.subscription, kind="privacy", message="Solicitação de teste")

    def setUp(self):
        cache.clear()
        self.client = APIClient(enforce_csrf_checks=True)

    def login(self, user):
        self.client.force_login(user)
        self.token = self.client.get("/api/auth/csrf").json()["csrf_token"]

    def patch(self, path, data):
        return self.client.patch(path, data, format="json", HTTP_X_CSRFTOKEN=self.token)

    def highlight(self, article, featured=True, position=0):
        return self.patch(f"/api/management/highlights/{article.pk}", {"is_featured": featured, "featured_position": position})

    def test_anonymous_and_subscribers_cannot_open_panel(self):
        for path in ["dashboard", "users", "subscriptions", "requests", "groups", "highlights"]:
            self.assertEqual(self.client.get("/api/management/" + path).status_code, 403)
        self.login(self.reader)
        self.assertFalse(self.client.get("/api/auth/me").json()["can_access_panel"])
        self.assertEqual(self.client.get("/api/management/dashboard").status_code, 403)

    def test_dashboard_is_scoped_and_financial_data_is_admin_only(self):
        self.login(self.coordinator)
        data = self.client.get("/api/management/dashboard").json()
        self.assertEqual(data["totals"]["contents"], 2)
        self.assertEqual(sum(row["total"] for row in data["activity"]), 1)
        self.assertEqual(len(data["activity"]), 6)
        self.assertNotIn("subscriptions", data["totals"])
        self.assertNotIn(self.other_article.pk, [row["id"] for row in data["recent"]])
        for path in ["users", "subscriptions", "requests"]:
            self.assertEqual(self.client.get("/api/management/" + path).status_code, 403)
        self.login(self.admin)
        data = self.client.get("/api/management/dashboard").json()
        self.assertEqual(data["totals"]["contents"], 3)
        self.assertEqual(data["totals"]["subscriptions"], 1)
        self.assertEqual(data["totals"]["requests"], 1)

    def test_facilitator_can_view_own_work_but_cannot_choose_highlights(self):
        self.login(self.author)
        self.assertEqual(self.client.get("/api/management/dashboard").status_code, 200)
        self.assertEqual(self.highlight(self.article).status_code, 404)
        self.assertEqual(self.client.get("/api/management/highlights").json()["count"], 0)

    def test_coordinator_controls_only_own_group_and_admin_controls_all(self):
        self.login(self.coordinator)
        self.assertEqual(self.highlight(self.article, position=3).status_code, 200)
        self.assertEqual(self.highlight(self.other_article).status_code, 404)
        self.assertEqual(self.client.get("/api/management/highlights").json()["count"], 2)
        self.login(self.admin)
        self.assertEqual(self.highlight(self.other_article, position=1).status_code, 200)
        self.client.logout()
        feed = self.client.get("/api/articles?featured=1").json()["results"]
        self.assertEqual([row["id"] for row in feed], [self.other_article.pk, self.article.pk])
        self.assertNotIn("body", feed[1])
        self.assertIsNone(self.client.get(f"/api/articles/{self.article.pk}").json()["body"])

    def test_draft_and_missing_cover_cannot_be_featured(self):
        self.login(self.coordinator)
        self.assertEqual(self.highlight(self.draft).status_code, 400)
        self.article.cover = None
        self.article.save()
        self.assertEqual(self.highlight(self.article).status_code, 400)

    def test_revoking_author_group_or_publication_removes_public_highlight(self):
        self.login(self.coordinator)
        self.highlight(self.article)
        self.article.status = "draft"
        self.article.save()
        self.assertEqual(self.client.get("/api/articles?featured=1").json()["count"], 0)
        self.article.status = "published"
        self.article.save()
        self.author_link.delete()
        self.assertEqual(self.client.get("/api/articles?featured=1").json()["count"], 0)
        self.assertEqual(self.highlight(self.article).status_code, 400)
        self.assertEqual(self.highlight(self.article, featured=False).status_code, 200)

    def test_highlight_input_is_validated_and_requires_csrf(self):
        self.login(self.coordinator)
        path = f"/api/management/highlights/{self.article.pk}"
        self.assertEqual(self.client.patch(path, {"is_featured": True}, format="json").status_code, 403)
        self.assertEqual(self.highlight(self.article, position=-1).status_code, 400)
        self.assertEqual(self.patch(path, {"is_featured": True, "featured_position": 0, "author": self.reader.pk}).status_code, 400)

    def test_coordinator_can_update_page_but_cannot_disable_group(self):
        self.login(self.coordinator)
        path = f"/api/management/groups/{self.group.pk}"
        self.assertEqual(self.patch(path, {"description": "Nova apresentação"}).status_code, 200)
        self.assertEqual(self.patch(path, {"is_active": False}).status_code, 403)
        self.assertEqual(self.patch(f"/api/management/groups/{self.foreign.pk}", {"name": "Inválido"}).status_code, 404)
        self.login(self.admin)
        self.assertEqual(self.patch(path, {"is_active": False, "position": 9}).status_code, 200)
        self.assertEqual(self.client.get(f"/api/articles/{self.article.pk}").status_code, 404)

    def test_admin_can_suspend_readers_but_not_administrative_accounts(self):
        self.login(self.admin)
        self.assertEqual(self.patch(f"/api/management/users/{self.reader.pk}", {"is_active": False}).status_code, 200)
        self.reader.refresh_from_db()
        self.assertFalse(self.reader.is_active)
        self.assertEqual(self.patch(f"/api/management/users/{self.admin.pk}", {"is_active": False}).status_code, 403)
        self.assertEqual(self.patch(f"/api/management/users/{self.author.pk}", {"is_superuser": True}).status_code, 400)
        self.assertEqual(self.client.get("/api/management/users?q=reader").json()["count"], 1)

    def test_resolution_is_idempotent_and_does_not_modify_billing(self):
        self.login(self.admin)
        path = f"/api/management/requests/{self.ticket.pk}"
        response = self.patch(path, {"resolved": True})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.patch(path, {"resolved": True}).json(), response.json())
        self.subscription.refresh_from_db()
        self.assertIsNone(self.subscription.canceled_at)
        self.assertEqual(self.client.get("/api/management/requests").json()["results"][0]["message"], "Solicitação de teste")

    def test_technical_admin_uses_site_identity_on_all_pages(self):
        self.login(self.admin)
        for path in ["/admin/", "/admin/auth/user/", f"/admin/auth/user/{self.reader.pk}/change/"]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "core/administration.css")
            self.assertContains(response, "Painel da comunidade")
