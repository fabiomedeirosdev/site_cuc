import hashlib
import imaplib
import re
import ssl
from email import policy
from email.parser import BytesParser
from email.utils import parseaddr
from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction

from .models import InboxMailbox, IncomingMessage


def webmail_url():
    value = settings.INBOX_WEBMAIL_URL
    parsed = urlparse(value)
    return value if parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password else ""


def import_message(raw, source_key, truncated=False):
    message = BytesParser(policy=policy.default).parsebytes(raw)
    sender = parseaddr(str(message.get("From", "")))[1]
    try:
        validate_email(sender)
    except ValidationError:
        sender = ""
    subject = " ".join(str(message.get("Subject", "Sem assunto")).replace("\x00", "").split())[:300] or "Sem assunto"
    body = ""
    if not truncated:
        part = message.get_body(preferencelist=("plain",))
        if part and part.get_content_type() == "text/plain":
            try:
                body = part.get_content()
            except (UnicodeError, LookupError):
                body = ""
    if not body:
        body = "Abra a caixa de e-mail para consultar esta mensagem e seus anexos."
    return IncomingMessage.objects.get_or_create(source_key=source_key, defaults={"sender": sender[:254], "subject": subject, "body": body.replace("\x00", "")[:30000]})


def synchronize_inbox(limit=50):
    if not (settings.INBOX_ENABLED and settings.INBOX_IMAP_HOST and settings.INBOX_IMAP_USER and settings.INBOX_IMAP_PASSWORD):
        raise ValueError("inbox_not_configured")
    identity = hashlib.sha256("\n".join([settings.INBOX_IMAP_HOST, settings.INBOX_IMAP_USER, settings.INBOX_IMAP_FOLDER]).encode()).hexdigest()
    created = 0
    # Conta dedicada de atendimento; não reutilizar credenciais SMTP implicitamente.
    with imaplib.IMAP4_SSL(settings.INBOX_IMAP_HOST, settings.INBOX_IMAP_PORT, ssl_context=ssl.create_default_context(), timeout=20) as mail:
        mail.login(settings.INBOX_IMAP_USER, settings.INBOX_IMAP_PASSWORD)
        status, _ = mail.select(settings.INBOX_IMAP_FOLDER, readonly=True)
        if status != "OK":
            raise ValueError("inbox_unavailable")
        _, validity = mail.response("UIDVALIDITY")
        if not validity or not validity[0] or not validity[0].isdigit():
            raise ValueError("inbox_invalid_response")
        validity = validity[0].decode("ascii")
        mailbox, _ = InboxMailbox.objects.get_or_create(key=identity)
        with transaction.atomic():
            mailbox = InboxMailbox.objects.select_for_update().get(pk=mailbox.pk)
            if mailbox.uid_validity != validity:
                mailbox.uid_validity = validity
                mailbox.last_uid = 0
            status, values = mail.uid("search", None, "UID", f"{mailbox.last_uid + 1}:*")
            if status != "OK":
                raise ValueError("inbox_search_failed")
            identifiers = sorted({int(uid) for uid in (values[0] or b"").split() if uid.isdigit() and int(uid) > mailbox.last_uid})[:limit]
            for uid in identifiers:
                status, sizes = mail.uid("fetch", str(uid), "(RFC822.SIZE)")
                match = re.search(rb"RFC822.SIZE (\d+)", b" ".join(value for value in sizes if isinstance(value, bytes))) if status == "OK" else None
                if not match:
                    raise ValueError("inbox_fetch_failed")
                large = int(match.group(1)) > 2 * 1024 * 1024
                query = "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT)])" if large else "(BODY.PEEK[])"
                status, values = mail.uid("fetch", str(uid), query)
                raw = next((value[1] for value in values if isinstance(value, tuple) and isinstance(value[1], bytes)), None) if status == "OK" else None
                if raw is None:
                    raise ValueError("inbox_fetch_failed")
                _, new = import_message(raw, f"{identity}:{validity}:{uid}", truncated=large)
                created += int(new)
                mailbox.last_uid = uid
            mailbox.save(update_fields=["uid_validity", "last_uid"])
    return created
