from fastapi import APIRouter, Depends
from app.api.deps import get_admin_user
from app.services.imap_worker import _running_tasks

router = APIRouter(prefix="/api/v1/system", tags=["system"], dependencies=[Depends(get_admin_user)])


@router.get("/status")
async def system_status():
    workers = []
    for folder_id, task in _running_tasks.items():
        workers.append({
            "folder_id": folder_id,
            "running": not task.done(),
            "error": str(task.exception()) if task.done() and task.exception() else None,
        })
    return {"workers": workers, "total_workers": len(workers)}
