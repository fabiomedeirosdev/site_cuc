import os
from pathlib import Path
import runpy
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.test import APIClient
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.urls import path
from apps.accounts.views import AccountAPIView, CsrfView


class CsrfProbeView(AccountAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        return Response({"ok": True})


urlpatterns = [path("api/auth/csrf", CsrfView.as_view()), path("api/probe", CsrfProbeView.as_view())]


class DomainConfigurationTests(SimpleTestCase):
    def configuration(self, debug, **extra):
        path = Path(__file__).resolve().parents[2] / "config" / "settings.py"
        with patch.dict(os.environ, {"DJANGO_DEBUG": "1" if debug else "0", "DJANGO_SECRET_KEY": "synthetic-test-key-for-settings", **extra}, clear=True), patch("dotenv.load_dotenv"):
            return runpy.run_path(str(path))

    def test_development_keeps_local_urls_and_does_not_trust_forwarded_headers(self):
        config = self.configuration(True)
        self.assertEqual(config["PUBLIC_FRONTEND_URL"], "http://127.0.0.1:5173")
        self.assertEqual(config["PUBLIC_API_URL"], "http://127.0.0.1:8000")
        self.assertEqual(config["ALLOWED_HOSTS"], ["127.0.0.1", "localhost"])
        self.assertNotIn("SECURE_PROXY_SSL_HEADER", config)

    def test_production_defaults_use_same_domain_for_site_api_and_email_links(self):
        config = self.configuration(False)
        self.assertEqual(config["PUBLIC_FRONTEND_URL"], "https://rhemacuc.com.br")
        self.assertEqual(config["PUBLIC_API_URL"], "https://rhemacuc.com.br")
        self.assertEqual(config["CSRF_TRUSTED_ORIGINS"], ["https://rhemacuc.com.br"])
        self.assertTrue(config["SESSION_COOKIE_SECURE"])
        self.assertTrue(config["CSRF_COOKIE_SECURE"])
        self.assertFalse(config["BILLING_ENABLED"])
        self.assertFalse(config["NEWSLETTER_ENABLED"])

    def test_https_proxy_requests_do_not_redirect_forever_and_http_redirects_to_domain(self):
        config = self.configuration(False, DJANGO_TRUST_PROXY_HEADERS="1")
        with self.settings(DEBUG=False, ALLOWED_HOSTS=config["ALLOWED_HOSTS"], SECURE_SSL_REDIRECT=True, SECURE_PROXY_SSL_HEADER=config["SECURE_PROXY_SSL_HEADER"]):
            client = APIClient()
            self.assertEqual(client.get("/api/health", HTTP_HOST="rhemacuc.com.br", HTTP_X_FORWARDED_PROTO="https").status_code, 200)
            response = client.get("/api/health", HTTP_HOST="rhemacuc.com.br")
            self.assertEqual(response.status_code, 301)
            self.assertEqual(response["Location"], "https://rhemacuc.com.br/api/health")

    def test_csrf_cookie_uses_https_and_root_path_on_production_domain(self):
        config = self.configuration(False, DJANGO_TRUST_PROXY_HEADERS="1")
        with self.settings(DEBUG=False, ALLOWED_HOSTS=config["ALLOWED_HOSTS"], SECURE_SSL_REDIRECT=True, SECURE_PROXY_SSL_HEADER=config["SECURE_PROXY_SSL_HEADER"], CSRF_COOKIE_SECURE=True):
            response = APIClient().get("/api/auth/csrf", HTTP_HOST="rhemacuc.com.br", HTTP_X_FORWARDED_PROTO="https")
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.cookies["csrftoken"]["secure"])
            self.assertEqual(response.cookies["csrftoken"]["path"], "/")
            self.assertEqual(response.cookies["csrftoken"]["domain"], "")

    def test_https_same_origin_writes_pass_csrf_and_foreign_origin_is_rejected(self):
        config = self.configuration(False, DJANGO_TRUST_PROXY_HEADERS="1")
        with self.settings(ROOT_URLCONF=__name__, DEBUG=False, ALLOWED_HOSTS=config["ALLOWED_HOSTS"], SECURE_SSL_REDIRECT=True, SECURE_PROXY_SSL_HEADER=config["SECURE_PROXY_SSL_HEADER"], CSRF_TRUSTED_ORIGINS=config["CSRF_TRUSTED_ORIGINS"]):
            client = APIClient(enforce_csrf_checks=True)
            headers = {"HTTP_HOST": "rhemacuc.com.br", "HTTP_X_FORWARDED_PROTO": "https"}
            token = client.get("/api/auth/csrf", **headers).json()["csrf_token"]
            response = client.post("/api/probe", {}, format="json", HTTP_X_CSRFTOKEN=token, HTTP_ORIGIN="https://rhemacuc.com.br", **headers)
            self.assertEqual(response.status_code, 200)
            response = client.post("/api/probe", {}, format="json", HTTP_X_CSRFTOKEN=token, HTTP_ORIGIN="https://example.invalid", **headers)
            self.assertEqual(response.status_code, 403)
