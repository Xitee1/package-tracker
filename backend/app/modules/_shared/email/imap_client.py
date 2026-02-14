import email
import re
from email.header import decode_header

import html2text

h2t = html2text.HTML2Text()
h2t.ignore_links = False


def decode_header_value(value: str) -> str:
    if not value:
        return ""
    decoded_parts = decode_header(value)
    result = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(part)
    return " ".join(result)


def extract_email_from_header(from_header: str) -> str:
    """Extract bare email from 'Display Name <email@example.com>' format."""
    match = re.search(r"<([^>]+)>", from_header)
    if match:
        return match.group(1).lower()
    return from_header.strip().lower()


def extract_body(msg: email.message.Message) -> str:
    """Extract plain text body from email message."""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")
            elif content_type == "text/html":
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or "utf-8"
                return h2t.handle(payload.decode(charset, errors="replace"))
    else:
        payload = msg.get_payload(decode=True)
        charset = msg.get_content_charset() or "utf-8"
        text = payload.decode(charset, errors="replace")
        if msg.get_content_type() == "text/html":
            return h2t.handle(text)
        return text
    return ""
