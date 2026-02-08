from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Date, Numeric, ForeignKey, func, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    order_number: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    tracking_number: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    carrier: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    vendor_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    vendor_domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="ordered")
    order_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    total_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    items: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    estimated_delivery: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="orders")
    events = relationship("OrderEvent", back_populates="order", cascade="all, delete-orphan")


class OrderEvent(Base):
    __tablename__ = "order_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    event_type: Mapped[str] = mapped_column(String(50))
    old_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str] = mapped_column(String(50))
    source_email_message_id: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    source_email_uid: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_folder: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    source_account_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    llm_raw_response: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    order = relationship("Order", back_populates="events")
