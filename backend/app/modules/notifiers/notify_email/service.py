import html
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.email_service import send_email

logger = logging.getLogger(__name__)

EVENT_LABELS = {
    "new_order": "New Order",
    "tracking_update": "Tracking Update",
    "package_delivered": "Package Delivered",
}


async def send_notification(
    user_id: int,
    event_type: str,
    event_data: dict,
    user_config: dict | None,
    db: AsyncSession,
) -> None:
    if not user_config or not user_config.get("email"):
        return
    if not user_config.get("verified"):
        return
    email = user_config["email"]
    event_label = EVENT_LABELS.get(event_type, event_type)
    vendor = html.escape(event_data.get("vendor_name", "Unknown"))
    order_number = html.escape(event_data.get("order_number", "N/A"))
    status = html.escape(event_data.get("status", ""))
    items_list = event_data.get("items", [])
    items_html = ""
    if items_list:
        items_html = "<ul>" + "".join(f"<li>{html.escape(str(item))}</li>" for item in items_list) + "</ul>"
    html_body = f"""
    <div style="font-family: sans-serif; max-width: 600px;">
        <h2>Package Tracker — {html.escape(event_label)}</h2>
        <p><strong>Vendor:</strong> {vendor}</p>
        <p><strong>Order:</strong> {order_number}</p>
        <p><strong>Status:</strong> {status}</p>
        {items_html}
    </div>
    """
    await send_email(to=email, subject=f"Package Tracker: {event_label} — {vendor}", html_body=html_body, db=db)
