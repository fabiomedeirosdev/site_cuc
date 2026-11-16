from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.policies import profile_role
from apps.billing.models import Checkout, Subscription
from apps.billing.provider import PagBank, Snapshot
from apps.billing.services import synchronize
from apps.communications.policies import can_manage
from apps.content.models import Article
from apps.editorial.models import EditorialGroup, Membership
from apps.editorial.policies import managed_groups


class CommunityImprovementsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.developer = User.objects.create_user(username="dev-new", email="dev-new@example.invalid", is_superuser=True)
        cls.founder = User.objects.create_user(username="founder-new", email="founder-new@example.invalid")
        cls.founder.profile.community_role = "founder"
        cls.founder.profile.save()
        cls.helper = User.objects.create_user(username="helper-new", email="helper-new@example.invalid")
        cls.helper.profile.community_role = "columnist"
        cls.helper.profile.save()
        cls.reader = User.objects.create_user(username="reader-new", email="reader-new@example.invalid")
        cls.coordinator = User.objects.create_user(username="coord-new", email="coord-new@example.invalid")
        cls.group = EditorialGroup.objects.create(name="Grupo novo", slug="new-test-group")
        Membership.objects.create(group=cls.group, user=cls.coordinator, role="coordinator")
        Membership.objects.create(group=cls.group, user=cls.helper, role="columnist", is_public=True)
        cls.article = Article.objects.create(author=cls.helper, group=cls.group, title="Título", excerpt="Resumo exclusivo", body="Segredo exclusivo", audience="members", status="published")

    def setUp(self):
        self.client = APIClient()

    def login(self, user):
        self.client.force_authenticate(user)

    def test_founder_has_application_admin_without_django_superuser_or_membership(self):
        self.assertFalse(self.founder.is_superuser)
        self.assertFalse(self.founder.is_staff)
        self.assertFalse(self.founder.editorial_memberships.exists())
        self.login(self.founder)
        for url in ["/api/management/team", "/api/management/users", "/api/management/groups", "/api/management/founders"]:
            self.assertEqual(self.client.get(url).status_code, 200, url)
        self.assertEqual(profile_role(self.founder), ("founder", "Fundador(a)"))
        self.assertTrue(self.client.get("/api/auth/me").json()["can_access_panel"])

    def test_developer_and_founder_can_set_position_and_profile_cannot_escalate(self):
        for actor in [self.coordinator, self.helper, self.reader]:
            self.login(actor)
            self.assertEqual(self.client.patch(f"/api/management/team/{self.helper.pk}", {"position": 7}, format="json").status_code, 403)
        for actor in [self.developer, self.founder]:
            self.login(actor)
            self.assertEqual(self.client.patch(f"/api/management/team/{self.helper.pk}", {"position": 7}, format="json").status_code, 200)
        self.login(self.helper)
        self.assertEqual(self.client.patch("/api/auth/me", {"community_role": "founder"}, format="json").status_code, 400)

    def test_general_membership_and_coordinator_rules(self):
        self.login(self.founder)
        response = self.client.post("/api/management/team", {"email": self.reader.email, "role": "", "group": None}, format="json")
        self.assertEqual(response.status_code, 201)
        self.reader.refresh_from_db()
        self.assertEqual(profile_role(self.reader)[0], "subscriber")
        self.assertFalse(managed_groups(self.reader).exists())
        self.assertEqual(self.client.post("/api/management/team", {"email": self.reader.email, "role": "coordinator", "group": None}, format="json").status_code, 400)
        self.assertEqual(Membership.objects.get(user=self.coordinator).role, "coordinator")

    def test_create_general_account_and_reject_password_overwrite(self):
        self.login(self.developer)
        payload = {"email": "general@example.invalid", "display_name": "Novo membro", "password": "CommunityNew!73-unusual", "role": "founder", "group": None}
        self.assertEqual(self.client.post("/api/management/team", payload, format="json").status_code, 201)
        user = get_user_model().objects.get(email=payload["email"])
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.editorial_memberships.exists())
        self.assertEqual(self.client.post("/api/management/team", payload, format="json").status_code, 400)

    def test_delegation_independent_and_revocable_by_founder(self):
        self.login(self.founder)
        payload = {"facilitator": self.helper.pk, "can_edit_agenda": True, "can_edit_mural": False}
        self.assertEqual(self.client.put("/api/communications/delegation", payload, format="json").status_code, 200)
        self.login(self.helper)
        self.assertEqual(self.client.get("/api/communications/events").status_code, 200)
        for section in ["notices", "campaigns"]:
            self.assertEqual(self.client.get(f"/api/communications/{section}").status_code, 403)
            self.assertEqual(self.client.post(f"/api/communications/{section}", {}, format="json").status_code, 403)
        self.assertEqual(self.client.get("/api/communications/weekly").status_code, 403)
        self.assertEqual(self.client.post("/api/communications/preview", {}, format="json").status_code, 403)
        self.assertEqual(self.client.get("/api/management/users").status_code, 403)
        self.login(self.developer)
        payload.update(can_edit_agenda=False, can_edit_mural=True)
        self.assertEqual(self.client.put("/api/communications/delegation", payload, format="json").status_code, 200)
        self.login(self.helper)
        self.assertEqual(self.client.get("/api/communications/events").status_code, 403)
        self.assertEqual(self.client.get("/api/communications/notices").status_code, 200)
        self.login(self.founder)
        payload["can_edit_mural"] = False
        self.client.put("/api/communications/delegation", payload, format="json")
        self.assertFalse(can_manage(self.helper))

    def test_coordinator_keeps_edit_permissions_but_cannot_administer_delegation(self):
        self.login(self.coordinator)
        for kind in ["events", "notices", "campaigns"]:
            self.assertEqual(self.client.get(f"/api/communications/{kind}").status_code, 200)
        self.assertEqual(self.client.put("/api/communications/delegation", {"facilitator": self.helper.pk, "can_edit_agenda": True, "can_edit_mural": True}, format="json").status_code, 403)

    def test_exclusive_body_video_and_excerpt_not_exposed_to_public_or_expired(self):
        checkout = Checkout.objects.create()
        subscription = Subscription.objects.create(checkout=checkout, provider_id="test-exclusive", email=self.reader.email, user=self.reader, paid_until=timezone.now()-timedelta(days=1), status="ACTIVE")
        for user in [None, self.reader]:
            self.client.force_authenticate(user)
            response = self.client.get(f"/api/articles/{self.article.pk}").json()
            self.assertIsNone(response["body"])
            self.assertIsNone(response["video_embed_url"])
            self.assertEqual(response["excerpt"], "")
            self.assertNotIn("Resumo exclusivo", str(self.client.get(f"/api/articles?group={self.group.slug}").json()))
        subscription.paid_until = timezone.now()+timedelta(days=3)
        subscription.save()
        for user in [self.reader, self.founder, self.developer]:
            self.login(user)
            self.assertEqual(self.client.get(f"/api/articles/{self.article.pk}").json()["body"], self.article.body)

    def test_public_visibility_and_later_change(self):
        self.article.audience = "public"
        self.article.save()
        self.assertEqual(self.client.get(f"/api/articles/{self.article.pk}").json()["body"], self.article.body)
        self.login(self.coordinator)
        self.assertEqual(self.client.patch(f"/api/editorial/articles/{self.article.pk}", {"audience": "members", "status": "draft"}, format="json").status_code, 200)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(f"/api/articles/{self.article.pk}").status_code, 404)

    def test_manual_order_stable_for_profiles_facilitators_and_group_team(self):
        self.helper.profile.position = 0
        self.helper.profile.save()
        self.developer.profile.position = 100
        self.developer.profile.save()
        Membership.objects.create(user=self.developer, group=self.group, role="columnist", is_public=True)
        profiles = self.client.get("/api/profiles").json()["results"]
        self.assertEqual(profiles[-1]["public_id"], str(self.developer.profile.public_id))
        team = self.client.get(f"/api/groups/{self.group.slug}").json()["team"]
        self.assertEqual(team[-1]["profile_url"], f"/perfis/{self.developer.profile.public_id}")
        facilitators = self.client.get("/api/facilitators").json()["results"]
        self.assertEqual(facilitators[-1]["profile_url"], f"/perfis/{self.developer.profile.public_id}")

    def test_new_price_and_legacy_subscription_still_synchronizes_original_amount(self):
        self.assertEqual(settings.SUBSCRIPTION_AMOUNT_CENTS, 4800)
        self.assertEqual(Checkout.objects.create().amount, 4800)
        checkout = Checkout.objects.create(amount=4820, plan_id="PLAN_"+str(uuid4()))
        now = timezone.now()
        identifier = "SUBS_"+str(uuid4())
        snapshot = Snapshot(identifier, checkout.plan_id, self.reader.email, "ACTIVE", now, now-timedelta(days=5), now+timedelta(days=25), 4820, "BRL")
        with patch.object(PagBank, "subscription", return_value=snapshot):
            subscription = synchronize(identifier)
        self.assertEqual(subscription.checkout.amount, 4820)
        checkout.refresh_from_db()
        self.assertEqual(checkout.amount, 4820)

    def test_general_facilitator_is_listed_without_group(self):
        Membership.objects.filter(user=self.helper).delete()
        response = self.client.get("/api/facilitators").json()
        self.assertTrue(any(row["profile_url"] == f"/perfis/{self.helper.profile.public_id}" and row["group_slug"] == "" for row in response["results"]))

    def test_group_contact_fields_public_and_validated(self):
        self.login(self.founder)
        path = f"/api/management/groups/{self.group.pk}"
        data = {"address": "Rua da Comunidade, 10", "whatsapp": "5511986302883", "video_url": "https://youtu.be/dQw4w9WgXcQ"}
        self.assertEqual(self.client.patch(path, data, format="json").status_code, 200)
        self.assertEqual(self.client.patch(path, {"whatsapp": "javascript:alert(1)"}, format="json").status_code, 400)
        self.client.force_authenticate(None)
        response = self.client.get(f"/api/groups/{self.group.slug}").json()
        self.assertEqual(response["address"], data["address"])
        self.assertEqual(response["whatsapp"], data["whatsapp"])
        self.assertIn("youtube-nocookie.com/embed/dQw4w9WgXcQ", response["video_embed_url"])
