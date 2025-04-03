from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.middleware import LoggingMiddleware
from app.api.v1 import auth, users
from app.config.settings import settings
from app.core.logging import configure_logging
from app.db.session import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan, title=settings.PROJECT_NAME)

configure_logging(debug=settings.DEBUG)

app.include_router(auth.router, prefix="/v1/auth")
app.include_router(users.router, prefix="/v1/users")

app.add_middleware(LoggingMiddleware)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
