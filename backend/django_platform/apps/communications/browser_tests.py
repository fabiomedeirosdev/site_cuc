import os
import json
import re
from pathlib import Path
import shutil
import subprocess
import sys
from contextlib import ExitStack
from datetime import timedelta
from tempfile import TemporaryDirectory
from unittest.mock import patch
from django.core.files.storage import FileSystemStorage
from django.utils import timezone
from PIL import Image
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import LiveServerTestCase, override_settings
from rest_framework.throttling import ScopedRateThrottle
from apps.editorial.models import EditorialGroup, Membership
from apps.billing.models import Checkout, Subscription
from .models import Campaign, Notice, NewsletterSettings
from .services import request_confirmation


class CommunicationsBrowserTests(LiveServerTestCase):
    host = "127.0.0.1"

    def test_agenda_mural_newsletter_and_delegation_in_edge(self):
        checkout = Checkout.objects.create(legal_version="browser-test")
        for viewport in ["desktop", "tablet", "mobile", "small-mobile"]:
            group = EditorialGroup.objects.create(name=f"Comunicação {viewport}", slug=f"communications-{viewport}")
            for role in ["coordinator", "helper"]:
                user = get_user_model().objects.create_user(username=f"{viewport}-{role}", email=f"{viewport}.{role}@example.invalid", password="CommunicationsTest!81-Password")
                user.profile.display_name = f"{role} {viewport}"
                user.profile.save()
                Membership.objects.create(user=user, group=group, role="coordinator" if role == "coordinator" else "columnist")
                if role == "helper":
                    Subscription.objects.create(user=user, email=user.email, checkout=checkout, provider_id=f"communications-{viewport}", status="ACTIVE", paid_until=timezone.now() + timedelta(days=10))
        workspace = Path(__file__).resolve().parents[4]
        env = {**os.environ, "CUC_COMMUNICATIONS_E2E": "1", "CUC_API_TARGET": self.live_server_url}
        invitations = {}
        with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            for viewport in ["desktop", "tablet", "mobile", "small-mobile"]:
                email = f"visitor.{viewport}@example.invalid"
                request_confirmation(email)
                invitations[viewport] = {"email": email, "token": re.search(r"#confirmar=([A-Za-z0-9_-]+)", mail.outbox[-1].body).group(1)}
        env["CUC_NEWSLETTER_FIXTURES"] = json.dumps(invitations)
        rates = {"login": "1000/minute", "account": "1000/minute", "newsletter": "1000/minute"}
        npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
        with TemporaryDirectory() as directory, ExitStack() as stack:
            photo = Path(directory) / "cartaz.png"
            Image.new("RGB", (1200, 1600), "#c19a4d").save(photo)
            env["CUC_COMMUNICATION_IMAGE"] = str(photo)
            storage = FileSystemStorage(location=Path(directory) / "protected")
            for model in [Notice, Campaign, NewsletterSettings]:
                stack.enter_context(patch.object(model._meta.get_field("image"), "storage", storage))
            with override_settings(DEBUG=True, NEWSLETTER_ENABLED=True, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", CSRF_TRUSTED_ORIGINS=["http://127.0.0.1:5178"], CORS_ALLOWED_ORIGINS=["http://127.0.0.1:5178"]), patch_rates(rates):
                result = subprocess.run([npm, "run", "test:communications"], cwd=workspace / "frontend", env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8", errors="replace", timeout=360)
        encoding = sys.stdout.encoding or "utf-8"
        print(result.stdout.encode(encoding, errors="replace").decode(encoding))
        self.assertEqual(result.returncode, 0, "Consulte o relatório em .local/phase7/report.")


def patch_rates(rates):
    from unittest.mock import patch
    return patch.object(ScopedRateThrottle, "THROTTLE_RATES", rates)
