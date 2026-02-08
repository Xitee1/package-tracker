import imaplib

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import encrypt_value, decrypt_value
from app.database import get_db
from app.models.user import User
from app.models.email_account import EmailAccount, WatchedFolder
from app.schemas.email_account import (
    CreateAccountRequest, UpdateAccountRequest, AccountResponse,
    WatchFolderRequest, WatchedFolderResponse,
)
from app.api.deps import get_current_user

router = APIRouter(prefix="/api/v1/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountResponse])
async def list_accounts(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EmailAccount).where(EmailAccount.user_id == user.id))
    return result.scalars().all()


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
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
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


@router.patch("/{account_id}", response_model=AccountResponse)
async def update_account(account_id: int, req: UpdateAccountRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    account = await db.get(EmailAccount, account_id)
    if not account or account.user_id != user.id:
        raise HTTPException(status_code=404, detail="Account not found")
    for field, value in req.model_dump(exclude_unset=True).items():
        if field == "imap_password" and value is not None:
            account.imap_password_encrypted = encrypt_value(value)
        elif hasattr(account, field):
            setattr(account, field, value)
    await db.commit()
    await db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(account_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    account = await db.get(EmailAccount, account_id)
    if not account or account.user_id != user.id:
        raise HTTPException(status_code=404, detail="Account not found")
    await db.delete(account)
    await db.commit()


@router.post("/{account_id}/test")
async def test_connection(account_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    account = await db.get(EmailAccount, account_id)
    if not account or account.user_id != user.id:
        raise HTTPException(status_code=404, detail="Account not found")
    try:
        password = decrypt_value(account.imap_password_encrypted)
        if account.use_ssl:
            mail = imaplib.IMAP4_SSL(account.imap_host, account.imap_port)
        else:
            mail = imaplib.IMAP4(account.imap_host, account.imap_port)
        mail.login(account.imap_user, password)
        mail.logout()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/{account_id}/folders", response_model=list[str])
async def list_folders(account_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    account = await db.get(EmailAccount, account_id)
    if not account or account.user_id != user.id:
        raise HTTPException(status_code=404, detail="Account not found")
    try:
        password = decrypt_value(account.imap_password_encrypted)
        if account.use_ssl:
            mail = imaplib.IMAP4_SSL(account.imap_host, account.imap_port)
        else:
            mail = imaplib.IMAP4(account.imap_host, account.imap_port)
        mail.login(account.imap_user, password)
        _, folder_list = mail.list()
        mail.logout()
        folders = []
        for item in folder_list:
            decoded = item.decode() if isinstance(item, bytes) else item
            parts = decoded.rsplit('" "', 1)
            if len(parts) == 2:
                folders.append(parts[1].strip('"'))
            else:
                parts = decoded.rsplit(" ", 1)
                folders.append(parts[-1].strip('"'))
        return folders
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to list folders: {e}")


# --- Watched Folders ---

@router.get("/{account_id}/folders/watched", response_model=list[WatchedFolderResponse])
async def list_watched(account_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    account = await db.get(EmailAccount, account_id)
    if not account or account.user_id != user.id:
        raise HTTPException(status_code=404, detail="Account not found")
    result = await db.execute(select(WatchedFolder).where(WatchedFolder.account_id == account_id))
    return result.scalars().all()


@router.post("/{account_id}/folders/watched", response_model=WatchedFolderResponse, status_code=status.HTTP_201_CREATED)
async def add_watched(account_id: int, req: WatchFolderRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    account = await db.get(EmailAccount, account_id)
    if not account or account.user_id != user.id:
        raise HTTPException(status_code=404, detail="Account not found")
    folder = WatchedFolder(account_id=account_id, folder_path=req.folder_path)
    db.add(folder)
    await db.commit()
    await db.refresh(folder)
    return folder


@router.delete("/{account_id}/folders/watched/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_watched(account_id: int, folder_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    account = await db.get(EmailAccount, account_id)
    if not account or account.user_id != user.id:
        raise HTTPException(status_code=404, detail="Account not found")
    folder = await db.get(WatchedFolder, folder_id)
    if not folder or folder.account_id != account_id:
        raise HTTPException(status_code=404, detail="Folder not found")
    await db.delete(folder)
    await db.commit()
