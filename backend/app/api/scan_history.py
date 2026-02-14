from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.models.email_scan import EmailScan
from app.models.email_account import EmailAccount
from app.schemas.scan_history import (
    EmailScanResponse,
    EmailScanListResponse,
    EmailContentResponse,
)
from app.api.deps import get_current_user
from app.services.imap_service import fetch_email_by_uid

router = APIRouter(prefix="/api/v1/scan-history", tags=["scan-history"])


def _base_query(user: User):
    """Return a base select for EmailScans belonging to the current user."""
    return (
        select(EmailScan)
        .join(EmailAccount, EmailScan.account_id == EmailAccount.id)
        .where(EmailAccount.user_id == user.id)
    )


def _scan_to_response(scan: EmailScan) -> EmailScanResponse:
    """Convert an EmailScan ORM object to an EmailScanResponse, populating account_name."""
    data = EmailScanResponse.model_validate(scan)
    if scan.account:
        data.account_name = scan.account.name
    return data


@router.get("", response_model=EmailScanListResponse)
async def list_scan_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    is_relevant: Optional[bool] = Query(None),
    account_id: Optional[int] = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = _base_query(user).options(selectinload(EmailScan.account))

    if is_relevant is not None:
        query = query.where(EmailScan.is_relevant == is_relevant)
    if account_id is not None:
        query = query.where(EmailScan.account_id == account_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Paginate
    query = query.order_by(EmailScan.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    scans = result.scalars().all()

    return EmailScanListResponse(
        items=[_scan_to_response(s) for s in scans],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{scan_id}", response_model=EmailScanResponse)
async def get_scan_detail(
    scan_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        _base_query(user)
        .options(selectinload(EmailScan.account))
        .where(EmailScan.id == scan_id)
    )
    result = await db.execute(query)
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return _scan_to_response(scan)


@router.delete("/{scan_id}", status_code=204)
async def delete_scan(
    scan_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = _base_query(user).where(EmailScan.id == scan_id)
    result = await db.execute(query)
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    await db.delete(scan)
    await db.commit()


@router.post("/{scan_id}/rescan", response_model=EmailScanResponse)
async def queue_rescan(
    scan_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        _base_query(user)
        .options(selectinload(EmailScan.account))
        .where(EmailScan.id == scan_id)
    )
    result = await db.execute(query)
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    scan.rescan_queued = True
    await db.commit()
    await db.refresh(scan)
    return _scan_to_response(scan)


@router.get("/{scan_id}/email", response_model=EmailContentResponse)
async def get_email_content(
    scan_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        _base_query(user)
        .options(selectinload(EmailScan.account))
        .where(EmailScan.id == scan_id)
    )
    result = await db.execute(query)
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    email_data = await fetch_email_by_uid(scan.account, scan.folder_path, scan.email_uid)
    if email_data is None:
        raise HTTPException(status_code=404, detail="Email not found on server")
    return EmailContentResponse(**email_data)
