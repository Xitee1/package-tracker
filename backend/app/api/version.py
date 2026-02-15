from importlib.metadata import version

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user

router = APIRouter(prefix="/api/v1", tags=["version"], dependencies=[Depends(get_current_user)])


@router.get("/version")
async def get_version():
    return {"version": version("package-tracker")}
