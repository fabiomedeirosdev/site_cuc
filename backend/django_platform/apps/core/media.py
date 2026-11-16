from pathlib import PurePosixPath
from urllib.parse import quote

from django.core.exceptions import SuspiciousFileOperation
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404
from rest_framework.permissions import AllowAny

from apps.accounts.views import AccountAPIView


def public_image_url(image):
    return f"/api/public-images/{quote(image.name, safe='/')}" if image else None


class PublicImageView(AccountAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, name):
        # Only the existing public upload folders; private photos and notices
        # continue to use their own storage and permission checks.
        path = PurePosixPath(name)
        types = {".webp": "image/webp", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
        if (not name.startswith(("covers/", "group-covers/", "institutional/founders/"))
                or ".." in path.parts or "\\" in name or path.suffix.lower() not in types):
            raise Http404
        try:
            response = FileResponse(default_storage.open(name, "rb"), content_type=types[path.suffix.lower()])
        except (FileNotFoundError, SuspiciousFileOperation):
            raise Http404
        response["X-Content-Type-Options"] = "nosniff"
        return response
