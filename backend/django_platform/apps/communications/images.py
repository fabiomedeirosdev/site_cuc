from io import BytesIO
import uuid
import warnings

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework.exceptions import ValidationError


def communication_image_storage():
    return FileSystemStorage(location=settings.COMMUNICATIONS_MEDIA_ROOT)


def clean_communication_image(upload):
    if upload.size > 5 * 1024 * 1024:
        raise ValidationError("A imagem deve ter até 5 MB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(upload) as image:
                if image.format not in {"JPEG", "PNG", "WEBP"}:
                    raise ValueError()
                if image.width > 4096 or image.height > 4096:
                    raise ValidationError("A imagem deve ter no máximo 4096 × 4096 pixels.")
                image.load()
                clean = ImageOps.exif_transpose(image).convert("RGBA")
                if clean.width < 600 or clean.height < 300:
                    raise ValidationError("A imagem deve ter no mínimo 600 × 300 pixels.")
                clean.thumbnail((2000, 2000), Image.Resampling.LANCZOS)
                background = Image.new("RGB", clean.size, "white")
                background.paste(clean, mask=clean.getchannel("A"))
                output = BytesIO()
                background.save(output, "JPEG", quality=88)
        return ContentFile(output.getvalue(), name=f"{uuid.uuid4().hex}.jpg")
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValidationError("Envie uma imagem JPG, PNG ou WebP válida.")


def image_path(kind, instance):
    return f"/api/communication-images/{kind}/{instance.pk}" if instance.image else None
