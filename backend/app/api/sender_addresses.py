from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user_sender_address import UserSenderAddress
from app.schemas.sender_address import CreateSenderAddressRequest, SenderAddressResponse

router = APIRouter(prefix="/api/v1/sender-addresses", tags=["sender-addresses"])


@router.get("", response_model=list[SenderAddressResponse])
async def list_sender_addresses(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserSenderAddress).where(UserSenderAddress.user_id == user.id)
    )
    return result.scalars().all()


@router.post("", response_model=SenderAddressResponse, status_code=201)
async def create_sender_address(
    req: CreateSenderAddressRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Check uniqueness across all users
    existing = await db.execute(
        select(UserSenderAddress).where(
            UserSenderAddress.email_address == req.email_address.lower()
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email address already registered")

    addr = UserSenderAddress(user_id=user.id, email_address=req.email_address.lower())
    db.add(addr)
    await db.commit()
    await db.refresh(addr)
    return addr


@router.delete("/{address_id}", status_code=204)
async def delete_sender_address(
    address_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    addr = await db.get(UserSenderAddress, address_id)
    if not addr or addr.user_id != user.id:
        raise HTTPException(status_code=404, detail="Address not found")
    await db.delete(addr)
    await db.commit()
