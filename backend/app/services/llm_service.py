import json
import litellm
from pydantic import BaseModel, ValidationError
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt_value
from app.models.llm_config import LLMConfig


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


class EmailItem(BaseModel):
    name: str
    quantity: int = 1
    price: Optional[float] = None


class EmailAnalysis(BaseModel):
    is_relevant: bool
    email_type: Optional[str] = None
    order_number: Optional[str] = None
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    vendor_name: Optional[str] = None
    vendor_domain: Optional[str] = None
    status: Optional[str] = None
    order_date: Optional[str] = None
    estimated_delivery: Optional[str] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = None
    items: Optional[list[EmailItem]] = None


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

If the email is NOT related to a purchase order or shipment, return: {"is_relevant": false}
Do not include any text outside the JSON object."""


async def analyze_email(subject: str, sender: str, body: str, db: AsyncSession) -> tuple[EmailAnalysis | None, dict]:
    """Analyze an email using the configured LLM. Returns (parsed_result, raw_response_dict)."""
    result = await db.execute(select(LLMConfig).where(LLMConfig.is_active == True))
    config = result.scalar_one_or_none()
    if not config:
        return None, {"error": "No LLM configured"}

    api_key = decrypt_value(config.api_key_encrypted) if config.api_key_encrypted else None

    user_message = f"Subject: {subject}\nFrom: {sender}\n\n{body}"
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    raw_text = None
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
