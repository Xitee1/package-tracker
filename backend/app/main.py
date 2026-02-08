from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import engine, Base
from app.models import *  # noqa: F401, F403


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="Package Tracker", version="0.1.0", lifespan=lifespan)

from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.accounts import router as accounts_router
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(accounts_router)


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}
