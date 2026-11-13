from unittest.mock import patch

from django.conf import settings
from django.db import DatabaseError, connection
from django.test import SimpleTestCase, TestCase
from django.urls import path
from rest_framework.response import Response
from rest_framework.test import APIClient
from rest_framework.views import APIView


class HealthEndpointTests(SimpleTestCase):
    def test_health_endpoint_is_public_and_returns_status(self):
        response = APIClient().get("/api/health")

        self.assertEqual(response.status_code, 200)
        expected_environment = "development" if settings.DEBUG else "production"
        self.assertEqual(
            response.json(),
            {"status": "ok", "environment": expected_environment},
        )

    def test_health_refuses_writes(self):
        self.assertEqual(APIClient().post("/api/health").status_code, 405)

    def test_local_frontend_origin_is_allowed(self):
        response = APIClient().get("/api/health", HTTP_ORIGIN="http://127.0.0.1:5173")
        self.assertEqual(response["Access-Control-Allow-Origin"], "http://127.0.0.1:5173")

    def test_unknown_origin_is_not_allowed(self):
        response = APIClient().get("/api/health", HTTP_ORIGIN="https://example.invalid")
        self.assertNotIn("Access-Control-Allow-Origin", response)

    def test_email_backend_stays_in_memory(self):
        self.assertEqual(settings.EMAIL_BACKEND, "django.core.mail.backends.locmem.EmailBackend")

    def test_new_api_views_require_authentication(self):
        with self.settings(ROOT_URLCONF=__name__):
            response = APIClient().get("/protected")
        self.assertIn(response.status_code, (401, 403))


class ReadinessEndpointTests(TestCase):
    def test_readiness_queries_postgresql(self):
        self.assertEqual(connection.vendor, "postgresql")
        response = APIClient().get("/api/ready")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "database": "ok"})

    def test_database_failure_returns_503_without_details(self):
        with patch("apps.core.views.connection.cursor", side_effect=DatabaseError("secret")):
            response = APIClient().get("/api/ready")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unavailable", "database": "unavailable"})


class DefaultProtectedView(APIView):
    def get(self, request):
        return Response({"private": True})


urlpatterns = [path("protected", DefaultProtectedView.as_view())]
