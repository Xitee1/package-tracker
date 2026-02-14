from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class OrderItemSchema(BaseModel):
    name: str
    quantity: int = 1
    price: Optional[float] = None


class OrderResponse(BaseModel):
    id: int
    order_number: Optional[str]
    tracking_number: Optional[str]
    carrier: Optional[str]
    vendor_name: Optional[str]
    vendor_domain: Optional[str]
    status: str
    order_date: Optional[date]
    total_amount: Optional[Decimal]
    currency: Optional[str]
    items: Optional[list[dict]]
    estimated_delivery: Optional[date]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrderStateResponse(BaseModel):
    id: int
    status: str
    source_type: str | None
    source_info: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class OrderDetailResponse(OrderResponse):
    states: list[OrderStateResponse]


class UpdateOrderRequest(BaseModel):
    order_number: Optional[str] = None
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    vendor_name: Optional[str] = None
    status: Optional[str] = None


class LinkOrderRequest(BaseModel):
    target_order_id: int
