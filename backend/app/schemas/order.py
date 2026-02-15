from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, field_validator


VALID_STATUSES = {"ordered", "shipment_preparing", "shipped", "in_transit", "out_for_delivery", "delivered"}


class ItemCreate(BaseModel):
    name: str
    quantity: int = 1
    price: Optional[float] = None

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Quantity must be at least 1")
        return v


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
    vendor_domain: Optional[str] = None
    status: Optional[str] = None
    order_date: Optional[date] = None
    total_amount: Optional[Decimal] = None
    currency: Optional[str] = None
    estimated_delivery: Optional[date] = None
    items: Optional[list[ItemCreate]] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_STATUSES:
            raise ValueError(f"Invalid status. Must be one of: {', '.join(sorted(VALID_STATUSES))}")
        return v


class LinkOrderRequest(BaseModel):
    target_order_id: int


class CreateOrderRequest(BaseModel):
    vendor_name: str
    order_number: Optional[str] = None
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    vendor_domain: Optional[str] = None
    status: str = "ordered"
    order_date: Optional[date] = None
    total_amount: Optional[Decimal] = None
    currency: Optional[str] = None
    estimated_delivery: Optional[date] = None
    items: Optional[list[ItemCreate]] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in VALID_STATUSES:
            raise ValueError(f"Invalid status. Must be one of: {', '.join(sorted(VALID_STATUSES))}")
        return v
