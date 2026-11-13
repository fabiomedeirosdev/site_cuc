"""Integração opt-in: Edge + React + Vite + Django + PostgreSQL temporário."""
import os
from pathlib import Path
import shutil
import subprocess
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import LiveServerTestCase
from rest_framework.throttling import ScopedRateThrottle


class AuthenticationBrowserTests(LiveServerTestCase):
    host = "127.0.0.1"

    def test_authentication_in_edge(self):
        for viewport in ["desktop", "tablet", "mobile", "small-mobile"]:
            for scenario in ["reader", "profile", "password", "expiry"]:
                user = get_user_model().objects.create_user(
                    username=f"{viewport}-{scenario}",
                    email=f"{viewport}.{scenario}@example.invalid",
                    password="LocalBrowserTest!8-Password",
                )
                user.profile.display_name = "Assinante de teste"
                user.profile.save()
                user.groups.add(Group.objects.get(name="Assinantes"))
        workspace = Path(__file__).resolve().parents[4]
        env = os.environ.copy()
        env.update({"CUC_E2E": "1", "CUC_API_TARGET": self.live_server_url})
        # Quotas são testadas separadamente na API; esta bateria compartilha o IP.
        rates = {"login": "1000/minute", "account": "1000/minute", "password_change": "1000/hour"}
        npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
        self.assertIsNotNone(npm, "npm não encontrado")
        with patch.object(ScopedRateThrottle, "THROTTLE_RATES", rates):
            result = subprocess.run(
                [npm, "run", "test:auth"], cwd=workspace / "frontend", env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                encoding="utf-8", errors="replace", timeout=300,
            )
        print(result.stdout)
        self.assertEqual(result.returncode, 0, result.stdout)
