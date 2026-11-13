from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APIClient

from .models import EditorialGroup, Membership


class EditorialTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.coordinator = User.objects.create_user(username="editor", email="editor@example.invalid", password="OnlyTestPassword!81")
        cls.author = User.objects.create_user(username="author", email="author@example.invalid", password="OnlyTestPassword!81")
        cls.reader = User.objects.create_user(username="reader", email="reader@example.invalid", password="OnlyTestPassword!81")
        cls.other = User.objects.create_user(username="other", email="other@example.invalid", password="OnlyTestPassword!81")
        cls.admin = User.objects.create_superuser(username="admin", email="admin@example.invalid", password="OnlyTestPassword!81")
        cls.reader.groups.add(Group.objects.get(name="Assinantes"))
        cls.group = EditorialGroup.objects.create(name="Grupo de teste", slug="teste", description="Descrição local")
        cls.second = EditorialGroup.objects.create(name="Outro grupo", slug="outro", description="Outro escopo")
        cls.coordination = Membership.objects.create(group=cls.group, user=cls.coordinator, role="coordinator")
        cls.membership = Membership.objects.create(group=cls.group, user=cls.author, role="columnist")
        cls.foreign = Membership.objects.create(group=cls.second, user=cls.other, role="columnist")

    def setUp(self):
        cache.clear()
        self.client = APIClient(enforce_csrf_checks=True)
        self.base = "/api/editorial/groups/teste/members"

    def session(self, user):
        self.client.force_login(user)
        self.token = self.client.get("/api/auth/csrf").json()["csrf_token"]

    def write(self, method, path, data=None):
        return getattr(self.client, method)(path, data or {}, format="json", HTTP_X_CSRFTOKEN=self.token)

    def test_migration_prepares_only_known_groups_no_accounts(self):
        self.assertEqual(EditorialGroup.objects.filter(slug__in=["rhematerapia", "restaura-me", "promocao-a-vida", "grupo-cura"]).count(), 4)

    def test_catalog_is_public_paginated_and_hides_inactive_groups(self):
        self.second.is_active = False
        self.second.save()
        data = self.client.get("/api/groups").json()
        self.assertNotIn("outro", [g["slug"] for g in data["results"]])
        self.assertEqual(self.client.get("/api/groups/outro").status_code, 404)
        self.assertEqual(self.client.get("/api/groups/teste").status_code, 200)

    def test_public_team_is_opt_in_and_never_exposes_account_identifiers(self):
        self.assertEqual(self.client.get("/api/groups/teste").json()["team"], [])
        self.membership.is_public = True
        self.membership.save()
        body = self.client.get("/api/groups/teste").json()
        self.assertEqual(body["team"][0]["display_name"], "Integrante da comunidade")
        self.assertNotIn(self.author.email, str(body))
        self.assertNotIn("username", str(body))
        self.author.is_active = False
        self.author.save()
        self.assertEqual(self.client.get("/api/groups/teste").json()["team"], [])

    def test_columnists_directory_filters_visibility_role_and_active_group(self):
        self.membership.is_public = True
        self.membership.save()
        self.coordination.is_public = True
        self.coordination.save()
        data = self.client.get("/api/columnists").json()["results"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["group_slug"], "teste")
        self.group.is_active = False
        self.group.save()
        self.assertEqual(self.client.get("/api/columnists").json()["count"], 0)

    def test_anonymous_cannot_manage_memberships(self):
        self.assertEqual(self.client.get("/api/editorial/groups").status_code, 403)
        self.assertEqual(self.client.get(self.base).status_code, 403)

    def test_subscribers_and_columnists_cannot_manage_groups(self):
        for user in [self.reader, self.author]:
            self.session(user)
            self.assertEqual(self.client.get("/api/editorial/groups").json()["groups"], [])
            self.assertEqual(self.write("post", self.base, {"email": self.other.email}).status_code, 404)
            self.assertEqual(self.write("patch", f"{self.base}/{self.membership.pk}", {"is_public": True}).status_code, 404)

    def test_global_coordinator_role_does_not_grant_group_access(self):
        self.reader.groups.add(Group.objects.get(name="Coordenadores"))
        self.session(self.reader)
        self.assertEqual(self.client.get(self.base).status_code, 404)

    def test_coordinator_sees_only_assigned_group(self):
        self.session(self.coordinator)
        self.assertEqual([g["slug"] for g in self.client.get("/api/editorial/groups").json()["groups"]], ["teste"])
        self.assertEqual(self.client.get("/api/editorial/groups/outro/members").status_code, 404)
        self.assertIn("no-store", self.client.get(self.base)["Cache-Control"])

    def test_coordinator_can_add_existing_account_without_changing_global_roles(self):
        self.session(self.coordinator)
        response = self.write("post", self.base, {"email": " OTHER@EXAMPLE.INVALID "})
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["role"], "columnist")
        self.other.refresh_from_db()
        self.assertFalse(self.other.is_staff)
        self.assertFalse(self.other.is_superuser)
        self.assertFalse(self.other.groups.exists())

    def test_duplicate_unknown_and_inactive_accounts_do_not_create_links(self):
        self.session(self.admin)
        for email in [self.author.email, "missing@example.invalid"]:
            self.assertEqual(self.write("post", self.base, {"email": email}).status_code, 400)
        self.other.is_active = False
        self.other.save()
        self.assertEqual(self.write("post", self.base, {"email": self.other.email}).status_code, 400)
        self.assertEqual(self.group.memberships.count(), 2)

    def test_coordinator_cannot_promote_or_change_or_remove_coordinators(self):
        self.session(self.coordinator)
        self.assertEqual(self.write("post", self.base, {"email": self.other.email, "role": "coordinator"}).status_code, 403)
        self.assertEqual(self.write("patch", f"{self.base}/{self.membership.pk}", {"role": "coordinator"}).status_code, 403)
        self.assertEqual(self.write("patch", f"{self.base}/{self.coordination.pk}", {"is_public": True}).status_code, 403)
        self.assertEqual(self.write("delete", f"{self.base}/{self.coordination.pk}").status_code, 403)

    def test_cross_group_member_ids_cannot_be_modified(self):
        self.session(self.coordinator)
        for method in ["patch", "delete"]:
            self.assertEqual(self.write(method, f"{self.base}/{self.foreign.pk}", {"biography": "Inválido"}).status_code, 404)

    def test_coordinator_can_edit_presentation_and_remove_authorization(self):
        self.session(self.coordinator)
        path = f"{self.base}/{self.membership.pk}"
        self.assertEqual(self.write("patch", path, {"biography": "Apresentação", "is_public": True}).status_code, 200)
        self.assertEqual(self.client.get("/api/groups/teste").json()["team"][0]["biography"], "Apresentação")
        self.assertEqual(self.write("delete", path).status_code, 204)
        self.assertTrue(get_user_model().objects.filter(pk=self.author.pk).exists())

    def test_revoked_or_inactive_group_immediately_denies_management(self):
        self.session(self.coordinator)
        self.group.is_active = False
        self.group.save()
        self.assertEqual(self.client.get(self.base).status_code, 404)
        self.group.is_active = True
        self.group.save()
        self.coordination.delete()
        self.assertEqual(self.client.get(self.base).status_code, 404)

    def test_admin_can_assign_coordinators_and_manage_inactive_groups(self):
        self.session(self.admin)
        self.second.is_active = False
        self.second.save()
        response = self.write("post", "/api/editorial/groups/outro/members", {"email": self.reader.email, "role": "coordinator"})
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(self.write("patch", f"{self.base}/{self.membership.pk}", {"role": "coordinator"}).status_code, 200)

    def test_writes_require_csrf(self):
        self.session(self.coordinator)
        response = self.client.post(self.base, {"email": self.other.email}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_unknown_fields_and_account_replacement_are_rejected(self):
        self.session(self.coordinator)
        for data in [{"is_superuser": True}, {"group": self.second.pk}, {"email": self.other.email}, {"role": "admin"}]:
            self.assertEqual(self.write("patch", f"{self.base}/{self.membership.pk}", data).status_code, 400)

    def test_membership_is_unique_and_roles_are_constrained_by_database(self):
        for values in [{"user": self.author, "role": "columnist"}, {"user": self.reader, "role": "admin"}]:
            with self.assertRaises(IntegrityError), transaction.atomic():
                Membership.objects.create(group=self.group, **values)

    def test_coordinator_can_create_facilitator_account_without_technical_privileges(self):
        self.session(self.coordinator)
        response = self.write("post", self.base, {"email": "new-facilitator@example.invalid", "create_account": True, "display_name": "Novo facilitador", "password": "InitialFacilitator!81-Password"})
        self.assertEqual(response.status_code, 201, response.content)
        user = get_user_model().objects.get(email="new-facilitator@example.invalid")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password("InitialFacilitator!81-Password"))
        self.assertEqual(user.profile.display_name, "Novo facilitador")
        self.assertEqual(list(user.editorial_memberships.values_list("group_id", "role")), [(self.group.pk, "columnist")])
        self.assertNotIn("password", response.json())

    def test_create_access_validates_password_duplicates_scope_and_privileges(self):
        self.session(self.coordinator)
        data = {"email": "new-facilitator@example.invalid", "create_account": True, "display_name": "Pessoa nova", "password": "123"}
        before = get_user_model().objects.count()
        self.assertEqual(self.write("post", self.base, data).status_code, 400)
        data["password"] = "InitialFacilitator!81-Password"
        self.assertEqual(self.write("post", "/api/editorial/groups/outro/members", data).status_code, 404)
        self.assertEqual(self.write("post", self.base, {**data, "role": "coordinator"}).status_code, 403)
        self.assertEqual(self.write("post", self.base, {**data, "is_staff": True}).status_code, 400)
        self.assertEqual(self.write("post", self.base, {**data, "email": self.author.email}).status_code, 400)
        self.assertEqual(get_user_model().objects.count(), before)

    def test_account_reports_scope_without_opening_paid_or_editorial_content(self):
        self.session(self.coordinator)
        body = self.client.get("/api/auth/me").json()
        self.assertTrue(body["can_manage_editorial_groups"])
        self.assertEqual(body["editorial_groups"][0]["group__slug"], "teste")
        self.assertTrue(body["capabilities"]["publish_content"])
        self.assertFalse(body["exclusive_content_access"])
