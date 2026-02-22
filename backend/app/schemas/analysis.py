from pydantic import BaseModel
from typing import Optional


class ExtractedItem(BaseModel):
    name: str
    quantity: int = 1
    price: Optional[float] = None


class AnalysisResult(BaseModel):
    is_relevant: bool
    document_type: Optional[str] = None
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
    items: Optional[list[ExtractedItem]] = None
