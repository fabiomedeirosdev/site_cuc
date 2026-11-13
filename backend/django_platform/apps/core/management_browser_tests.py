"""Fluxo real do painel: Edge, React, Django e PostgreSQL temporário."""
import os
from pathlib import Path
import shutil
import subprocess
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import LiveServerTestCase, override_settings
from django.utils import timezone
from rest_framework.throttling import ScopedRateThrottle

from apps.content.models import Article, CoverImage
from apps.editorial.models import EditorialGroup, Membership


class ManagementBrowserTests(LiveServerTestCase):
    host = "127.0.0.1"

    def test_highlights_and_permissions_in_edge(self):
        for viewport in ["desktop", "tablet", "mobile", "small-mobile"]:
            group = EditorialGroup.objects.create(name=f"Gestão {viewport}", slug=f"management-{viewport}", description="Grupo de teste do painel")
            admin = get_user_model().objects.create_superuser(username=f"panel-admin-{viewport}", email=f"{viewport}.admin@example.invalid", password="PanelBrowserTest!81-Pass")
            coordinator = get_user_model().objects.create_user(username=f"panel-coordinator-{viewport}", email=f"{viewport}.coordinator@example.invalid", password="PanelBrowserTest!81-Pass")
            Membership.objects.create(user=coordinator, group=group, role="coordinator")
            cover = CoverImage.objects.create(owner=admin, file="covers/test-management.png")
            Article.objects.create(author=admin, group=group, title=f"Destaque real {viewport}", excerpt="Reflexão da comunidade", body="Texto exclusivo protegido.", audience="members", status="published", published_at=timezone.now(), cover=cover, cover_alt="Capa de teste")
        workspace = Path(__file__).resolve().parents[4]
        env = {**os.environ, "CUC_MANAGEMENT_LIVE": "1", "CUC_API_TARGET": self.live_server_url}
        npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
        rates = {"login": "1000/minute", "account": "1000/minute"}
        with override_settings(CSRF_TRUSTED_ORIGINS=["http://127.0.0.1:5181"], CORS_ALLOWED_ORIGINS=["http://127.0.0.1:5181"]), patch.object(ScopedRateThrottle, "THROTTLE_RATES", rates):
            result = subprocess.run([npm, "run", "test:management:live"], cwd=workspace / "frontend", env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8", errors="replace", timeout=300)
        print(result.stdout)
        self.assertEqual(result.returncode, 0, result.stdout)
