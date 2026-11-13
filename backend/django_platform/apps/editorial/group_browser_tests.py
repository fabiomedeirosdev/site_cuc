import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import LiveServerTestCase, override_settings
from PIL import Image
from rest_framework.throttling import ScopedRateThrottle

from .models import EditorialGroup, Membership


class GroupCreationBrowserTests(LiveServerTestCase):
    host = "127.0.0.1"

    def test_group_creation_and_cover_upload_in_edge(self):
        for viewport in ["desktop", "tablet", "mobile", "small-mobile"]:
            user = get_user_model().objects.create_user(username=f"group-coordinator-{viewport}", email=f"{viewport}.group-coordinator@example.invalid", password="GroupBrowserTest!81-Pass")
            group = EditorialGroup.objects.create(name=f"Base {viewport}", slug=f"base-{viewport}", description="Grupo base")
            Membership.objects.create(group=group, user=user, role="coordinator")
        workspace = Path(__file__).resolve().parents[4]
        npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
        rates = {"login": "1000/minute", "account": "1000/minute"}
        with TemporaryDirectory() as directory:
            photo = Path(directory) / "foto-grupo.png"
            small_photo = Path(directory) / "foto-pequena.png"
            Image.new("RGB", (1600, 1000), "#b78a42").save(photo)
            Image.new("RGB", (400, 300), "#b78a42").save(small_photo)
            env = {**os.environ, "CUC_GROUPS_LIVE": "1", "CUC_API_TARGET": self.live_server_url, "CUC_GROUP_PHOTO": str(photo), "CUC_GROUP_SMALL_PHOTO": str(small_photo)}
            with override_settings(MEDIA_ROOT=Path(directory) / "media", CSRF_TRUSTED_ORIGINS=["http://127.0.0.1:5182"], CORS_ALLOWED_ORIGINS=["http://127.0.0.1:5182"]), patch.object(ScopedRateThrottle, "THROTTLE_RATES", rates):
                result = subprocess.run([npm, "run", "test:groups:live"], cwd=workspace / "frontend", env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8", errors="replace", timeout=360)
        print(result.stdout)
        self.assertEqual(result.returncode, 0, result.stdout)
