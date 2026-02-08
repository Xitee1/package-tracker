import asyncio
import email
import logging
from email.header import decode_header

import html2text
from aioimaplib import IMAP4_SSL
from sqlalchemy import select

from app.database import async_session
from app.models.email_account import EmailAccount, WatchedFolder
from app.services.email_processor import process_email

logger = logging.getLogger(__name__)
h2t = html2text.HTML2Text()
h2t.ignore_links = False

_running_tasks: dict[int, asyncio.Task] = {}


def _decode_header_value(value: str) -> str:
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


def _extract_body(msg: email.message.Message) -> str:
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


async def _watch_folder(account_id: int, folder_id: int):
    """Watch a single IMAP folder for new messages using IDLE + polling fallback."""
    while True:
        try:
            async with async_session() as db:
                account = await db.get(EmailAccount, account_id)
                folder = await db.get(WatchedFolder, folder_id)
                if not account or not folder or not account.is_active:
                    logger.info(f"Stopping watcher for folder {folder_id}: account/folder removed or inactive")
                    return

                from app.core.encryption import decrypt_value
                password = decrypt_value(account.imap_password_encrypted)

                imap = IMAP4_SSL(host=account.imap_host, port=account.imap_port)
                await imap.wait_hello_from_server()
                await imap.login(account.imap_user, password)
                await imap.select(folder.folder_path)

                # Fetch new messages since last seen UID
                search_criteria = f"UID {folder.last_seen_uid + 1}:*"
                _, data = await imap.uid_search(search_criteria)
                uids = data[0].split() if data[0] else []

                for uid_bytes in uids:
                    uid = int(uid_bytes)
                    if uid <= folder.last_seen_uid:
                        continue

                    _, msg_data = await imap.uid("fetch", str(uid), "(RFC822)")
                    if not msg_data or not msg_data[0]:
                        continue

                    raw_email = msg_data[0]
                    if isinstance(raw_email, (list, tuple)):
                        raw_email = raw_email[-1] if len(raw_email) > 1 else raw_email[0]
                    if isinstance(raw_email, bytes):
                        msg = email.message_from_bytes(raw_email)
                    else:
                        continue

                    subject = _decode_header_value(msg.get("Subject", ""))
                    sender = _decode_header_value(msg.get("From", ""))
                    message_id = msg.get("Message-ID", "")
                    body = _extract_body(msg)

                    await process_email(
                        subject=subject,
                        sender=sender,
                        body=body,
                        message_id=message_id,
                        email_uid=uid,
                        folder_path=folder.folder_path,
                        account_id=account_id,
                        user_id=account.user_id,
                        db=db,
                    )

                    folder.last_seen_uid = uid
                    await db.commit()

                # Try IDLE, fall back to polling
                try:
                    idle_task = await imap.idle_start(timeout=account.polling_interval_sec)
                    await asyncio.wait_for(idle_task, timeout=account.polling_interval_sec)
                except (asyncio.TimeoutError, Exception):
                    pass
                finally:
                    try:
                        await imap.idle_done()
                    except Exception:
                        pass
                    try:
                        await imap.logout()
                    except Exception:
                        pass

        except asyncio.CancelledError:
            logger.info(f"Watcher cancelled for folder {folder_id}")
            return
        except Exception as e:
            logger.error(f"Error watching folder {folder_id}: {e}")
            await asyncio.sleep(30)


async def start_all_watchers():
    """Start watchers for all active accounts and their watched folders."""
    async with async_session() as db:
        result = await db.execute(
            select(WatchedFolder)
            .join(EmailAccount)
            .where(EmailAccount.is_active == True)
        )
        folders = result.scalars().all()
        for folder in folders:
            key = folder.id
            if key not in _running_tasks:
                task = asyncio.create_task(_watch_folder(folder.account_id, folder.id))
                _running_tasks[key] = task
                logger.info(f"Started watcher for folder {folder.id} (account {folder.account_id})")


async def stop_all_watchers():
    """Stop all running watchers."""
    for key, task in _running_tasks.items():
        task.cancel()
    _running_tasks.clear()


async def restart_watchers():
    """Restart all watchers (call after account/folder changes)."""
    await stop_all_watchers()
    await start_all_watchers()
