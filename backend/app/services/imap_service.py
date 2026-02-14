import email
import logging

from aioimaplib import IMAP4_SSL

from app.core.encryption import decrypt_value
from app.services.imap_worker import _decode_header_value, _extract_body

logger = logging.getLogger(__name__)


async def fetch_email_by_uid(account, folder_path: str, uid: int) -> dict | None:
    """Fetch a single email from IMAP by UID. Returns dict or None if not found."""
    try:
        password = decrypt_value(account.imap_password_encrypted)
        imap = IMAP4_SSL(host=account.imap_host, port=account.imap_port)
        await imap.wait_hello_from_server()
        await imap.login(account.imap_user, password)
        await imap.select(folder_path)

        _, msg_data = await imap.uid("fetch", str(uid), "(RFC822)")

        try:
            await imap.logout()
        except Exception:
            pass

        if not msg_data or not msg_data[0]:
            return None

        raw_email = msg_data[0]
        if isinstance(raw_email, (list, tuple)):
            raw_email = raw_email[-1] if len(raw_email) > 1 else raw_email[0]

        if not isinstance(raw_email, bytes):
            return None

        msg = email.message_from_bytes(raw_email)
        subject = _decode_header_value(msg.get("Subject", ""))
        sender = _decode_header_value(msg.get("From", ""))
        date_str = msg.get("Date", "")
        body = _extract_body(msg)

        return {
            "subject": subject,
            "sender": sender,
            "date": date_str,
            "body_text": body,
        }
    except Exception as e:
        logger.error(f"Failed to fetch email UID {uid}: {e}")
        return None
