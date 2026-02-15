import logging
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def send_notification(user_id: int, event_type: str, event_data: dict, user_config: dict | None, db: AsyncSession) -> None:
    if not user_config or not user_config.get("url"):
        return
    url = user_config["url"]
    headers = {"Content-Type": "application/json"}
    if user_config.get("auth_header_encrypted"):
        from app.core.encryption import decrypt_value
        headers["Authorization"] = decrypt_value(user_config["auth_header_encrypted"])
    payload = {"event": event_type, "data": event_data}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        logger.info(f"Webhook sent to {url} for user {user_id}, status {resp.status_code}")
