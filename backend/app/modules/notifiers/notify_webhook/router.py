from fastapi import APIRouter, Depends
from app.api.deps import get_admin_user

router = APIRouter(tags=["notify-webhook"], dependencies=[Depends(get_admin_user)])


@router.get("/info")
async def get_info():
    return {"message": "Webhook notification module. No admin configuration required."}
