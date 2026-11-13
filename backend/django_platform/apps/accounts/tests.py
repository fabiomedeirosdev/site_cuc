from types import SimpleNamespace
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework.throttling import ScopedRateThrottle

from .forms import AccountCreationForm
from .policies import CONSUMPTION_PERMISSIONS, HasExclusiveContentAccess, IsReadOnlyConsumer


User = get_user_model()
PASSWORD = "LocalTest!9-Unique-Password"
NEW_PASSWORD = "DifferentLocalTest!8-Password"


class AccountTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="local-test", email="reader@example.invalid", password=PASSWORD)
        cls.user.groups.add(Group.objects.get(name="Assinantes"))
        cls.other = User.objects.create_user(username="other-test", email="other@example.invalid", password=PASSWORD)

    def setUp(self):
        cache.clear()
        self.client = APIClient(enforce_csrf_checks=True)

    def csrf(self, client=None):
        client = client or self.client
        response = client.get("/api/auth/csrf")
        self.assertEqual(response.status_code, 200)
        return response.json()["csrf_token"]

    def login(self, client=None, password=PASSWORD):
        client = client or self.client
        response = client.post("/api/auth/login", {"email": " READER@EXAMPLE.INVALID ", "password": password}, format="json", HTTP_X_CSRFTOKEN=self.csrf(client))
        self.assertEqual(response.status_code, 200, response.content)
        return response

    def test_csrf_cookie_and_session_are_http_only(self):
        response = self.login()
        self.assertTrue(response.cookies[settings.SESSION_COOKIE_NAME]["httponly"])
        self.assertEqual(response.cookies[settings.SESSION_COOKIE_NAME]["samesite"], "Lax")
        self.assertTrue(self.client.cookies[settings.CSRF_COOKIE_NAME]["httponly"])
        self.assertIn("no-store", response["Cache-Control"])

    def test_login_requires_csrf_even_without_prior_session(self):
        response = self.client.post("/api/auth/login", {"email": self.user.email, "password": PASSWORD}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.get("/api/auth/me").status_code, 403)

    def test_valid_login_rotates_session_and_csrf(self):
        old_csrf = self.csrf()
        session = self.client.session
        session["pre_login"] = "test"
        session.save()
        old_key = session.session_key
        response = self.login()
        self.assertNotEqual(self.client.session.session_key, old_key)
        self.assertNotEqual(response.json()["csrf_token"], old_csrf)
        self.assertEqual(self.client.get("/api/auth/me").json()["email"], self.user.email)

    def test_missing_user_wrong_password_and_inactive_user_have_same_error(self):
        messages = []
        for email, password in [("missing@example.invalid", PASSWORD), (self.user.email, "wrong-password")]:
            response = self.client.post("/api/auth/login", {"email": email, "password": password}, format="json", HTTP_X_CSRFTOKEN=self.csrf())
            self.assertEqual(response.status_code, 400)
            messages.append(response.json())
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        response = self.client.post("/api/auth/login", {"email": self.user.email, "password": PASSWORD}, format="json", HTTP_X_CSRFTOKEN=self.csrf())
        self.assertEqual(response.status_code, 400)
        self.assertEqual(messages[0], messages[1])
        self.assertEqual(messages[0], response.json())

    def test_login_throttles_repeated_attempts(self):
        with patch.object(ScopedRateThrottle, "THROTTLE_RATES", {"login": "2/minute", "account": "120/minute"}):
            for _ in range(2):
                response = self.client.post("/api/auth/login", {"email": self.user.email, "password": "wrong"}, format="json", HTTP_X_CSRFTOKEN=self.csrf())
                self.assertEqual(response.status_code, 400)
            response = self.client.post("/api/auth/login", {"email": self.user.email, "password": "wrong"}, format="json", HTTP_X_CSRFTOKEN=self.csrf())
            self.assertEqual(response.status_code, 429)

    def test_anonymous_users_cannot_access_or_modify_accounts(self):
        self.assertEqual(self.client.get("/api/auth/me").status_code, 403)
        response = self.client.patch("/api/auth/me", {"display_name": "Invalid"}, format="json", HTTP_X_CSRFTOKEN=self.csrf())
        self.assertEqual(response.status_code, 403)

    def test_profile_discloses_only_own_allowed_information(self):
        self.login()
        response = self.client.get("/api/auth/me")
        body = response.json()
        self.assertEqual(body["id"], self.user.pk)
        self.assertEqual(body["roles"], ["subscriber"])
        self.assertNotIn("password", body)
        self.assertNotIn("username", body)
        self.assertNotIn(self.other.email, str(body))
        self.assertEqual(body["subscription_status"], "none")
        self.assertFalse(body["exclusive_content_access"])
        for capability in CONSUMPTION_PERMISSIONS:
            self.assertTrue(body["capabilities"][capability])
        for capability in ["comment", "create_content", "edit_content", "publish_content", "manage_users"]:
            self.assertFalse(body["capabilities"][capability])
        self.assertIn("no-store", response["Cache-Control"])

    def test_can_change_own_display_name_without_changing_other_profile(self):
        response = self.login()
        response = self.client.patch("/api/auth/me", {"display_name": "Nome local de teste"}, format="json", HTTP_X_CSRFTOKEN=response.json()["csrf_token"])
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["display_name"], "Nome local de teste")
        self.other.profile.refresh_from_db()
        self.assertEqual(self.other.profile.display_name, "")

    def test_profile_rejects_identity_role_and_permission_escalation(self):
        response = self.login()
        for field, value in {"user": self.other.pk, "email": self.other.email, "roles": ["administrator"], "is_staff": True, "is_superuser": True, "groups": ["Coordenadores"], "exclusive_content_access": True}.items():
            with self.subTest(field=field):
                result = self.client.patch("/api/auth/me", {field: value}, format="json", HTTP_X_CSRFTOKEN=response.json()["csrf_token"])
                self.assertEqual(result.status_code, 400)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)

    def test_authenticated_writes_reject_missing_and_untrusted_csrf(self):
        self.login()
        self.assertEqual(self.client.patch("/api/auth/me", {"display_name": "Blocked"}, format="json").status_code, 403)
        result = self.client.patch("/api/auth/me", {"display_name": "Blocked"}, format="json", HTTP_X_CSRFTOKEN=self.csrf(), HTTP_ORIGIN="https://example.invalid")
        self.assertEqual(result.status_code, 403)

    def test_trusted_vite_origin_accepts_csrf(self):
        token = self.csrf()
        response = self.client.post("/api/auth/login", {"email": self.user.email, "password": PASSWORD}, format="json", HTTP_X_CSRFTOKEN=token, HTTP_ORIGIN="http://127.0.0.1:5173")
        self.assertEqual(response.status_code, 200)

    def test_logout_requires_csrf_and_invalidates_session(self):
        response = self.login()
        self.assertEqual(self.client.get("/api/auth/logout").status_code, 405)
        self.assertEqual(self.client.post("/api/auth/logout").status_code, 403)
        result = self.client.post("/api/auth/logout", HTTP_X_CSRFTOKEN=response.json()["csrf_token"])
        self.assertEqual(result.status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me").status_code, 403)

    def test_deactivated_account_loses_existing_session(self):
        self.login()
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        self.assertEqual(self.client.get("/api/auth/me").status_code, 403)

    def test_change_password_validates_old_and_new_passwords(self):
        response = self.login()
        for current, new in [("wrong", NEW_PASSWORD), (PASSWORD, "123"), (PASSWORD, PASSWORD)]:
            result = self.client.post("/api/auth/password", {"current_password": current, "new_password": new}, format="json", HTTP_X_CSRFTOKEN=response.json()["csrf_token"])
            self.assertEqual(result.status_code, 400)

    def test_password_change_preserves_current_session_and_revokes_other_sessions(self):
        response = self.login()
        other_session = APIClient(enforce_csrf_checks=True)
        self.login(other_session)
        result = self.client.post("/api/auth/password", {"current_password": PASSWORD, "new_password": NEW_PASSWORD}, format="json", HTTP_X_CSRFTOKEN=response.json()["csrf_token"])
        self.assertEqual(result.status_code, 200, result.content)
        self.assertEqual(self.client.get("/api/auth/me").status_code, 200)
        self.assertEqual(other_session.get("/api/auth/me").status_code, 403)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))
        self.assertNotEqual(self.user.password, NEW_PASSWORD)

    def test_subscriber_cannot_use_admin_or_public_provisioning_endpoints(self):
        self.login()
        self.assertEqual(self.client.get("/admin/").status_code, 302)
        for path in ["/api/auth/register", "/api/users", f"/api/auth/users/{self.other.pk}"]:
            self.assertEqual(self.client.post(path, {}, format="json").status_code, 404)

    def test_email_uniqueness_is_enforced_in_postgresql(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(username="duplicate", email=" READER@EXAMPLE.INVALID ", password=PASSWORD)

    def test_admin_creation_requires_unique_email_and_stores_password_hash(self):
        form = AccountCreationForm(data={"email": "created@example.invalid", "first_name": "Teste", "password1": PASSWORD, "password2": PASSWORD})
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertTrue(user.check_password(PASSWORD))
        self.assertTrue(hasattr(user, "profile"))
        duplicate = AccountCreationForm(data={"email": " CREATED@EXAMPLE.INVALID ", "password1": PASSWORD, "password2": PASSWORD})
        self.assertFalse(duplicate.is_valid())
        self.assertIn("email", duplicate.errors)

    def test_role_groups_do_not_grant_global_editorial_or_administration_rights(self):
        for name in ["Assinantes", "Facilitadores", "Coordenadores"]:
            permissions = set(Group.objects.get(name=name).permissions.values_list("codename", flat=True))
            self.assertFalse(any(permission.startswith(("add_", "change_", "delete_")) for permission in permissions))

    def test_read_only_policy_permits_only_consumption_and_exclusive_gate_stays_closed(self):
        factory = APIRequestFactory()
        for capability in CONSUMPTION_PERMISSIONS:
            view = SimpleNamespace(consumption_capability=capability)
            for method in ["get", "head", "post", "put", "patch", "delete"]:
                request = getattr(factory, method)("/")
                request.user = User.objects.get(pk=self.user.pk)
                self.assertEqual(IsReadOnlyConsumer().has_permission(request, view), method in ["get", "head"])
                self.assertFalse(HasExclusiveContentAccess().has_permission(request, view))
        request.user = self.other
        self.assertFalse(IsReadOnlyConsumer().has_permission(request, view))
        request.method = "GET"
        request.user = self.user
        self.user.is_active = False
        self.assertFalse(IsReadOnlyConsumer().has_permission(request, view))
