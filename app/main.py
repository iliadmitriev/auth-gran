from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1 import auth, users
from app.db.session import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(auth.router, prefix="/v1/auth")
app.include_router(users.router, prefix="/v1/users")
