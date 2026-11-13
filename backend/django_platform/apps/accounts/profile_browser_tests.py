import json
import os
from contextlib import ExitStack
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.storage import FileSystemStorage
from django.test import LiveServerTestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle

from apps.editorial.models import EditorialGroup, Membership
from .models import Profile


class PublicProfileBrowserTests(LiveServerTestCase):
    host = "127.0.0.1"

    def test_profiles_and_contact_permissions_in_edge(self):
        confirmations = {}
        with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", EMAIL_HOST="smtp.example.invalid", DEFAULT_FROM_EMAIL="contato@example.test"):
            for viewport in ["desktop", "tablet", "mobile", "small-mobile"]:
                group = EditorialGroup.objects.create(name=f"Perfis {viewport}", slug=f"profiles-{viewport}")
                for role in ["developer", "coordinator", "subscriber"]:
                    create = get_user_model().objects.create_superuser if role == "developer" else get_user_model().objects.create_user
                    user = create(username=f"profiles-{viewport}-{role}", email=f"{viewport}.{role}@example.invalid", password="PublicProfilesBrowser!81-Pass")
                    user.profile.display_name = f"Pessoa {role} {viewport}"
                    user.profile.save()
                    if role == "coordinator":
                        Membership.objects.create(user=user, group=group, role="coordinator")
                    if role == "developer":
                        client = APIClient(enforce_csrf_checks=True)
                        client.force_login(user)
                        csrf = client.get("/api/auth/csrf").json()["csrf_token"]
                        result = client.post("/api/auth/email", {"new_email": f"confirmed.{viewport}@example.invalid", "current_password": "PublicProfilesBrowser!81-Pass"}, format="json", HTTP_X_CSRFTOKEN=csrf)
                        self.assertEqual(result.status_code, 200, result.content)
                        confirmations[viewport] = mail.outbox[-1].body.split("#token=")[1].split()[0]
        workspace = Path(__file__).resolve().parents[4]
        env = {**os.environ, "CUC_PROFILES_E2E": "1", "CUC_API_TARGET": self.live_server_url, "CUC_PROFILE_CONFIRMATIONS": json.dumps(confirmations)}
        npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
        rates = {"login": "1000/minute", "account": "1000/minute", "email_change": "1000/hour", "password_change": "1000/hour"}
        with TemporaryDirectory() as directory, ExitStack() as stack:
            photo = Path(directory) / "perfil.png"
            Image.new("RGB", (600, 800), "#a47a3a").save(photo)
            env["CUC_PROFILE_PHOTO"] = str(photo)
            stack.enter_context(patch.object(Profile._meta.get_field("avatar"), "storage", FileSystemStorage(location=Path(directory) / "photos")))
            stack.enter_context(patch.object(ScopedRateThrottle, "THROTTLE_RATES", rates))
            with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", EMAIL_HOST="smtp.example.invalid", DEFAULT_FROM_EMAIL="contato@example.test", CSRF_TRUSTED_ORIGINS=["http://127.0.0.1:5184"], CORS_ALLOWED_ORIGINS=["http://127.0.0.1:5184"]):
                result = subprocess.run([npm, "run", "test:profiles"], cwd=workspace / "frontend", env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8", errors="replace", timeout=360)
        print(result.stdout)
        self.assertEqual(result.returncode, 0, result.stdout)
