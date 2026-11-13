import re
from urllib.parse import parse_qs, urlparse

from rest_framework.exceptions import ValidationError


def video_id(value):
    if not value:
        return ""
    try:
        url = urlparse(value)
        if url.scheme != "https" or url.username or url.password or url.port not in [None, 443]:
            raise ValueError()
        host = (url.hostname or "").lower()
        if host == "youtu.be":
            candidate = url.path.strip("/")
        elif host in {"youtube.com", "www.youtube.com", "m.youtube.com", "www.youtube-nocookie.com"}:
            parts = url.path.strip("/").split("/")
            if parts[0] == "watch":
                candidate = parse_qs(url.query).get("v", [""])[0]
            elif len(parts) == 2 and parts[0] in {"embed", "shorts", "live"}:
                candidate = parts[1]
            else:
                raise ValueError()
        else:
            raise ValueError()
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate):
            raise ValueError()
        return candidate
    except (ValueError, IndexError):
        raise ValidationError("Use um link HTTPS válido de um vídeo do YouTube.")


def embed_url(value):
    identifier = video_id(value)
    return f"https://www.youtube-nocookie.com/embed/{identifier}" if identifier else ""
