import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt_value
from app.models.smtp_config import SmtpConfig

logger = logging.getLogger(__name__)


async def get_smtp_config(db: AsyncSession) -> SmtpConfig | None:
    result = await db.execute(select(SmtpConfig))
    return result.scalar_one_or_none()


async def is_smtp_configured(db: AsyncSession) -> bool:
    return await get_smtp_config(db) is not None


async def send_email(
    to: str,
    subject: str,
    html_body: str,
    db: AsyncSession,
) -> None:
    """Send an email using the configured SMTP settings."""
    config = await get_smtp_config(db)
    if not config:
        raise RuntimeError("SMTP is not configured")

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{config.sender_name} <{config.sender_address}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))

    password = decrypt_value(config.password_encrypted) if config.password_encrypted else None

    await aiosmtplib.send(
        msg,
        hostname=config.host,
        port=config.port,
        username=config.username,
        password=password,
        use_tls=config.use_tls,
        start_tls=not config.use_tls,
    )
    logger.info(f"Email sent to {to}: {subject}")
