from io import BytesIO
import uuid
import warnings

from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework.exceptions import ValidationError


def clean_cover(upload):
    if upload.size > 5 * 1024 * 1024:
        raise ValidationError("A foto deve ter até 5 MB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(upload) as image:
                if image.format not in {"JPEG", "PNG", "WEBP"} or image.width * image.height > 20000000:
                    raise ValueError()
                image.load()
                clean = ImageOps.exif_transpose(image).convert("RGB")
                clean.thumbnail((2560, 2560))
                output = BytesIO()
                clean.save(output, "WEBP", quality=85)
        return ContentFile(output.getvalue(), name=f"{uuid.uuid4().hex}.webp")
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValidationError("Envie uma imagem JPG, PNG ou WebP válida, com até 20 megapixels.")
