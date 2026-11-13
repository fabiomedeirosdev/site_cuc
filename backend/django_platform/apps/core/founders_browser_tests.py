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


class FoundersBrowserTests(LiveServerTestCase):
    host = "127.0.0.1"

    def test_founders_editing_and_public_navigation_in_edge(self):
        for viewport in ["desktop", "tablet", "mobile", "small-mobile"]:
            get_user_model().objects.create_superuser(username=f"founders-{viewport}", email=f"{viewport}.founders@example.invalid", password="FoundersBrowser!81-Pass")
        workspace = Path(__file__).resolve().parents[4]
        npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
        rates = {"login": "1000/minute", "account": "1000/minute"}
        with TemporaryDirectory() as directory:
            photo = Path(directory) / "fundadores.png"
            Image.new("RGB", (600, 800), "#a57a3b").save(photo)
            env = {**os.environ, "CUC_FOUNDERS_E2E": "1", "CUC_API_TARGET": self.live_server_url, "CUC_FOUNDERS_PHOTO": str(photo)}
            with override_settings(DEBUG=True, MEDIA_ROOT=Path(directory) / "media", CSRF_TRUSTED_ORIGINS=["http://127.0.0.1:5185"], CORS_ALLOWED_ORIGINS=["http://127.0.0.1:5185"]), patch.object(ScopedRateThrottle, "THROTTLE_RATES", rates):
                result = subprocess.run([npm, "run", "test:founders"], cwd=workspace / "frontend", env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8", errors="replace", timeout=300)
        print(result.stdout)
        self.assertEqual(result.returncode, 0, result.stdout)
