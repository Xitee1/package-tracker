from fastapi import APIRouter, Depends
from app.api.deps import get_admin_user

router = APIRouter(tags=["notify-email"], dependencies=[Depends(get_admin_user)])


@router.get("/info")
async def get_info():
    return {"message": "Email notification module. Requires core SMTP to be configured."}
