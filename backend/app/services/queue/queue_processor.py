import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analysers.llm.service import EmailAnalysis, analyze_email

logger = logging.getLogger(__name__)


async def process_raw_data(
    raw_data: dict, db: AsyncSession
) -> tuple[EmailAnalysis | None, dict]:
    """Process raw queue item data through the LLM.

    Returns (parsed_analysis, raw_llm_response_dict).
    Currently only handles email source type.
    """
    subject = raw_data.get("subject", "")
    sender = raw_data.get("sender", "")
    body = raw_data.get("body", "")

    return await analyze_email(subject, sender, body, db)
