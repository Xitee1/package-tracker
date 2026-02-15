from importlib.metadata import PackageNotFoundError, version

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user

router = APIRouter(prefix="/api/v1", tags=["version"], dependencies=[Depends(get_current_user)])


@router.get("/version")
async def get_version():
    try:
        v = version("package-tracker")
    except PackageNotFoundError:
        v = "unknown"
    return {"version": v}
