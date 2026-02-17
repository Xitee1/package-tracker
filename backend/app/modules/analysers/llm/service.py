import json
import litellm
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt_value
from app.modules.analysers.llm.models import LLMConfig
from app.schemas.email_analysis import EmailAnalysis, EmailItem  # noqa: F401

_active_requests: int = 0


async def check_configured() -> bool:
    """Return True if at least one active LLMConfig exists."""
    from app.database import async_session
    async with async_session() as db:
        result = await db.execute(select(LLMConfig).where(LLMConfig.is_active == True).limit(1))
        return result.scalar_one_or_none() is not None


async def get_status(db: AsyncSession) -> dict | None:
    """Status hook: return current LLM configuration summary."""
    result = await db.execute(select(LLMConfig).where(LLMConfig.is_active == True))
    config = result.scalar_one_or_none()
    if not config:
        return None
    return {
        "provider": config.provider,
        "model": config.model_name,
        "mode": "active" if _active_requests > 0 else "idle",
    }


async def call_llm(config: LLMConfig, api_key: str | None, messages: list[dict], **kwargs) -> str:
    """Call LLM via LiteLLM and return the response text."""
    model = f"{config.provider}/{config.model_name}" if config.provider != "openai" else config.model_name
    response = await litellm.acompletion(
        model=model,
        messages=messages,
        api_key=api_key,
        api_base=config.api_base_url or None,
        **kwargs,
    )
    return response.choices[0].message.content


SYSTEM_PROMPT = """You are an email analysis assistant. Analyze the provided email and extract purchase/shipping information.

Return ONLY valid JSON matching this schema:
{
  "is_relevant": true/false,
  "email_type": "order_confirmation" | "shipment_confirmation" | "shipment_update" | "delivery_confirmation",
  "order_number": "string or null",
  "tracking_number": "string or null",
  "carrier": "string or null",
  "vendor_name": "string or null",
  "vendor_domain": "string or null",
  "status": "ordered" | "shipment_preparing" | "shipped" | "in_transit" | "out_for_delivery" | "delivered",
  "order_date": "YYYY-MM-DD or null",
  "estimated_delivery": "YYYY-MM-DD or null",
  "total_amount": number or null,
  "currency": "string or null",
  "items": [{"name": "string", "quantity": number, "price": number or null}] or null
}

Rules:
- An email is ONLY relevant if at least an order_number OR a tracking_number can be extracted. If neither is present, return {"is_relevant": false}.
- For marketplace platforms (eBay, Amazon Marketplace, Etsy, etc.), include the seller/shop name in vendor_name, e.g. "eBay - elektro-computershop", "Amazon - TechStore GmbH". Use the format "Platform - Seller".
- Always extract the estimated delivery date when mentioned in the email (e.g. "voraussichtliche Lieferung", "estimated delivery", "Zustellung bis", "Lieferung zwischen"). Many order confirmations (especially eBay) include this directly.
- For order_date: extract the order/purchase date from the email body. If no explicit date is found in the body, use the Date header from the email metadata as fallback.
- If the email is NOT related to a purchase order or shipment, return: {"is_relevant": false}

Do not include any text outside the JSON object."""


async def analyze(raw_data: dict, db: AsyncSession) -> tuple[EmailAnalysis | None, dict]:
    """Analyze raw input data using the configured LLM. Returns (parsed_result, raw_response_dict)."""
    result = await db.execute(select(LLMConfig).where(LLMConfig.is_active == True))
    config = result.scalar_one_or_none()
    if not config:
        return None, {"error": "No LLM configured"}

    api_key = decrypt_value(config.api_key_encrypted) if config.api_key_encrypted else None

    user_message = json.dumps(raw_data, ensure_ascii=False, indent=2)
    prompt = config.system_prompt or SYSTEM_PROMPT
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": user_message},
    ]

    global _active_requests
    raw_text = None
    _active_requests += 1
    try:
        for attempt in range(2):
            try:
                raw_text = await call_llm(config, api_key, messages, max_tokens=2048)
                raw_dict = json.loads(raw_text)
                parsed = EmailAnalysis.model_validate(raw_dict)
                return parsed, raw_dict
            except (json.JSONDecodeError, ValidationError):
                if attempt == 0:
                    continue
                return None, {"error": "Failed to parse LLM response", "raw": raw_text}
            except Exception as e:
                return None, {"error": str(e)}
    finally:
        _active_requests -= 1
