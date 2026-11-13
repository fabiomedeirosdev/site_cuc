"""Integração opt-in da Fase 4, exclusivamente em banco temporário."""
import os
from pathlib import Path
import shutil
import subprocess
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import LiveServerTestCase, override_settings
from rest_framework.throttling import ScopedRateThrottle

from .models import EditorialGroup, Membership


class EditorialBrowserTests(LiveServerTestCase):
    host = "127.0.0.1"

    def test_editorial_workflow_in_edge(self):
        User = get_user_model()
        for viewport in ["desktop", "tablet", "mobile", "small-mobile"]:
            people = {}
            for role in ["coordinator", "columnist", "reader", "admin"]:
                user = User.objects.create_user(
                    username=f"{viewport}-{role}", email=f"{viewport}.{role}@example.invalid",
                    password="LocalEditorialTest!8-Password",
                    is_staff=role == "admin", is_superuser=role == "admin",
                )
                user.profile.display_name = {"coordinator": "Coordenação de teste", "columnist": "Facilitador de teste", "reader": "Leitor de teste", "admin": "Administração de teste"}[role]
                user.profile.save()
                people[role] = user
            group = EditorialGroup.objects.create(name=f"Grupo {viewport}", slug=f"e2e-{viewport}", description="Grupo temporário para verificar o fluxo editorial.", cover="prayer")
            Membership.objects.create(group=group, user=people["coordinator"], role="coordinator")
        workspace = Path(__file__).resolve().parents[4]
        env = os.environ.copy()
        env.update({"CUC_EDITORIAL_E2E": "1", "CUC_API_TARGET": self.live_server_url})
        npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
        rates = {"login": "1000/minute", "account": "1000/minute", "password_change": "1000/hour"}
        with patch.object(ScopedRateThrottle, "THROTTLE_RATES", rates), override_settings(CSRF_TRUSTED_ORIGINS=["http://127.0.0.1:5175"], CORS_ALLOWED_ORIGINS=["http://127.0.0.1:5175"]):
            result = subprocess.run([npm, "run", "test:editorial"], cwd=workspace / "frontend", env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8", errors="replace", timeout=300)
        print(result.stdout)
        self.assertEqual(result.returncode, 0, result.stdout)
