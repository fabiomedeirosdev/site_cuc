from io import BytesIO
import uuid
import warnings

from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework.exceptions import ValidationError


def clean_group_cover(upload):
    if upload.size > 5 * 1024 * 1024:
        raise ValidationError("A foto deve ter até 5 MB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(upload) as image:
                if image.format not in {"JPEG", "PNG", "WEBP"}:
                    raise ValueError()
                if image.width > 4096 or image.height > 4096:
                    raise ValidationError("A imagem deve ter no máximo 4096 × 4096 pixels.")
                image.load()
                clean = ImageOps.exif_transpose(image)
                if clean.width < 800 or clean.height < 450:
                    raise ValidationError("A imagem deve ter no mínimo 800 × 450 pixels. Recomendamos 1600 × 900 pixels.")
                width = min(1600, clean.width, clean.height * 16 // 9) // 16 * 16
                clean = ImageOps.fit(clean.convert("RGB"), (width, width * 9 // 16), method=Image.Resampling.LANCZOS)
                output = BytesIO()
                clean.save(output, "WEBP", quality=85)
        return ContentFile(output.getvalue(), name=f"{uuid.uuid4().hex}.webp")
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValidationError("Envie uma imagem JPG, PNG ou WebP válida.")
