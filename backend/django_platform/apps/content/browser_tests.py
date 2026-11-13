import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import LiveServerTestCase, override_settings
from PIL import Image
from rest_framework.throttling import ScopedRateThrottle

from apps.editorial.models import EditorialGroup, Membership


class ContentBrowserTests(LiveServerTestCase):
    host = "127.0.0.1"

    def test_content_workflow_in_edge(self):
        User = get_user_model()
        for viewport in ["desktop", "tablet", "mobile", "small-mobile"]:
            group = EditorialGroup.objects.create(name=f"Formação {viewport}", slug=f"content-{viewport}", description="Grupo temporário")
            for role in ["columnist", "reader", "coordinator"]:
                user = User.objects.create_user(username=f"{viewport}-{role}", email=f"{viewport}.{role}@example.invalid", password="LocalContentTest!8-Password")
                user.profile.display_name = f"Pessoa {role} {viewport}"
                user.profile.save()
                if role != "reader":
                    Membership.objects.create(user=user, group=group, role=role)
        workspace = Path(__file__).resolve().parents[4]
        env = os.environ.copy()
        npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
        rates = {"login": "1000/minute", "account": "1000/minute", "password_change": "1000/hour"}
        with TemporaryDirectory() as directory:
            image_path = Path(directory) / "cover.png"
            Image.new("RGB", (800, 450), "#b78a42").save(image_path)
            env.update({"CUC_CONTENT_E2E": "1", "CUC_API_TARGET": self.live_server_url, "CUC_E2E_COVER": str(image_path)})
            command = [npm, "run", "test:content"]
            if env.get("CUC_CONTENT_E2E_GREP"):
                command += ["--", "--grep", env["CUC_CONTENT_E2E_GREP"]]
            with override_settings(MEDIA_ROOT=Path(directory) / "media", CSRF_TRUSTED_ORIGINS=["http://127.0.0.1:5176"], CORS_ALLOWED_ORIGINS=["http://127.0.0.1:5176"]), patch.object(ScopedRateThrottle, "THROTTLE_RATES", rates):
                result = subprocess.run(command, cwd=workspace / "frontend", env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8", errors="replace", timeout=360)
        encoding = sys.stdout.encoding or "utf-8"
        print(result.stdout.encode(encoding, errors="replace").decode(encoding))
        self.assertEqual(result.returncode, 0, result.stdout)
