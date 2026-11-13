from io import BytesIO
import uuid
import warnings
import hashlib

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework.exceptions import ValidationError


def profile_image_storage():
    return FileSystemStorage(location=settings.PROFILE_MEDIA_ROOT)


def avatar_url(profile):
    if not profile.avatar:
        return None
    version = hashlib.sha256(profile.avatar.name.encode()).hexdigest()[:12]
    return f"/api/profiles/{profile.public_id}/photo?v={version}"


def clean_avatar(upload):
    if upload.size > 5 * 1024 * 1024:
        raise ValidationError("A foto deve ter até 5 MB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(upload) as image:
                if image.format not in {"JPEG", "PNG", "WEBP"}:
                    raise ValueError()
                if image.width > 4096 or image.height > 4096:
                    raise ValidationError("A foto deve ter no máximo 4096 × 4096 pixels.")
                image.load()
                clean = ImageOps.exif_transpose(image).convert("RGB")
                if min(clean.size) < 200:
                    raise ValidationError("A foto deve ter no mínimo 200 × 200 pixels.")
                side = min(512, *clean.size)
                clean = ImageOps.fit(clean, (side, side), method=Image.Resampling.LANCZOS)
                output = BytesIO()
                clean.save(output, "WEBP", quality=88)
        return ContentFile(output.getvalue(), name=f"{uuid.uuid4().hex}.webp")
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValidationError("Envie uma foto JPG, PNG ou WebP válida.")
