from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import encrypt_value, decrypt_value
from app.database import get_db
from app.models.user import User
from app.modules._shared.email.imap_utils import test_imap_connection, list_imap_folders
from app.modules.providers.email_user.models import EmailAccount, WatchedFolder
from app.modules.providers.email_user.schemas import (
    CreateAccountRequest, UpdateAccountRequest, AccountResponse,
    WatchFolderRequest, UpdateWatchedFolderRequest, WatchedFolderResponse,
)
from app.api.deps import get_current_user
from app.modules.providers.email_user.service import restart_watchers, restart_single_watcher, is_folder_scanning

user_router = APIRouter(tags=["email-user"])


@user_router.get("/accounts", response_model=list[AccountResponse])
async def list_accounts(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EmailAccount).where(EmailAccount.user_id == user.id))
    return result.scalars().all()


@user_router.post("/accounts", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(req: CreateAccountRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    account = EmailAccount(
        user_id=user.id,
        name=req.name,
        imap_host=req.imap_host,
        imap_port=req.imap_port,
        imap_user=req.imap_user,
        imap_password_encrypted=encrypt_value(req.imap_password),
        use_ssl=req.use_ssl,
        polling_interval_sec=req.polling_interval_sec,
        use_polling=req.use_polling,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


@user_router.patch("/accounts/{account_id}", response_model=AccountResponse)
async def update_account(account_id: int, req: UpdateAccountRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    account = await db.get(EmailAccount, account_id)
    if not account or account.user_id != user.id:
        raise HTTPException(status_code=404, detail="Account not found")
    if req.use_polling is False and account.idle_supported is False:
        raise HTTPException(
            status_code=400,
            detail="This email provider does not support IMAP IDLE",
        )
    for field, value in req.model_dump(exclude_unset=True).items():
        if field == "imap_password" and value is not None:
            account.imap_password_encrypted = encrypt_value(value)
        elif hasattr(account, field):
            setattr(account, field, value)
    await db.commit()
    await db.refresh(account)
    return account


@user_router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(account_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    account = await db.get(EmailAccount, account_id)
    if not account or account.user_id != user.id:
        raise HTTPException(status_code=404, detail="Account not found")
    await db.delete(account)
    await db.commit()


@user_router.post("/accounts/{account_id}/test")
async def test_connection(account_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    account = await db.get(EmailAccount, account_id)
    if not account or account.user_id != user.id:
        raise HTTPException(status_code=404, detail="Account not found")
    password = decrypt_value(account.imap_password_encrypted)
    result = await test_imap_connection(
        host=account.imap_host,
        port=account.imap_port,
        user=account.imap_user,
        password=password,
        use_ssl=account.use_ssl,
    )
    return {"success": result.success, "message": result.message, "idle_supported": result.idle_supported}


@user_router.get("/accounts/{account_id}/folders", response_model=list[str])
async def list_folders(account_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    account = await db.get(EmailAccount, account_id)
    if not account or account.user_id != user.id:
        raise HTTPException(status_code=404, detail="Account not found")
    try:
        password = decrypt_value(account.imap_password_encrypted)
        result = await list_imap_folders(
            host=account.imap_host,
            port=account.imap_port,
            user=account.imap_user,
            password=password,
            use_ssl=account.use_ssl,
        )
        return result.folders
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to list folders: {e}")


@user_router.get("/accounts/{account_id}/folders/watched", response_model=list[WatchedFolderResponse])
async def list_watched(account_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    account = await db.get(EmailAccount, account_id)
    if not account or account.user_id != user.id:
        raise HTTPException(status_code=404, detail="Account not found")
    result = await db.execute(select(WatchedFolder).where(WatchedFolder.account_id == account_id))
    return result.scalars().all()


@user_router.post("/accounts/{account_id}/folders/watched", response_model=WatchedFolderResponse, status_code=status.HTTP_201_CREATED)
async def add_watched(account_id: int, req: WatchFolderRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    account = await db.get(EmailAccount, account_id)
    if not account or account.user_id != user.id:
        raise HTTPException(status_code=404, detail="Account not found")
    folder = WatchedFolder(account_id=account_id, folder_path=req.folder_path)
    db.add(folder)
    await db.commit()
    await db.refresh(folder)
    await restart_watchers()
    return folder


@user_router.delete("/accounts/{account_id}/folders/watched/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_watched(account_id: int, folder_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    account = await db.get(EmailAccount, account_id)
    if not account or account.user_id != user.id:
        raise HTTPException(status_code=404, detail="Account not found")
    folder = await db.get(WatchedFolder, folder_id)
    if not folder or folder.account_id != account_id:
        raise HTTPException(status_code=404, detail="Folder not found")
    await db.delete(folder)
    await db.commit()
    await restart_watchers()


@user_router.patch("/accounts/{account_id}/folders/watched/{folder_id}", response_model=WatchedFolderResponse)
async def update_watched(
    account_id: int, folder_id: int, req: UpdateWatchedFolderRequest,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    account = await db.get(EmailAccount, account_id)
    if not account or account.user_id != user.id:
        raise HTTPException(status_code=404, detail="Account not found")
    folder = await db.get(WatchedFolder, folder_id)
    if not folder or folder.account_id != account_id:
        raise HTTPException(status_code=404, detail="Folder not found")
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(folder, field, value)
    await db.commit()
    await db.refresh(folder)
    return folder


@user_router.post("/accounts/{account_id}/folders/watched/{folder_id}/scan")
async def scan_folder(
    account_id: int, folder_id: int,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    account = await db.get(EmailAccount, account_id)
    if not account or account.user_id != user.id:
        raise HTTPException(status_code=404, detail="Account not found")
    folder = await db.get(WatchedFolder, folder_id)
    if not folder or folder.account_id != account_id:
        raise HTTPException(status_code=404, detail="Folder not found")
    if is_folder_scanning(folder_id):
        raise HTTPException(status_code=409, detail="Folder is already being scanned")
    await restart_single_watcher(folder_id)
    return {"status": "scan_triggered"}
