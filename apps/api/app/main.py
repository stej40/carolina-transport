from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.db import SessionLocal
from app.deps import AuthError
from app.idempotency import IdempotencyMiddleware
from app.routers import auth, drivers, fleet, groups, health, orders, transports, users
from app.routers import settings as settings_router

app = FastAPI(
    title="System KAROLINA API",
    version="0.1.0",
    docs_url="/api/docs" if settings.debug else None,
    openapi_url="/api/openapi.json" if settings.debug else None,
)
app.state.session_maker = SessionLocal

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Idempotency-Key"],
)
app.add_middleware(IdempotencyMiddleware)


@app.exception_handler(AuthError)
async def auth_error_handler(request: Request, exc: AuthError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(groups.router, prefix="/api/v1")
app.include_router(fleet.trucks_router, prefix="/api/v1")
app.include_router(fleet.trailers_router, prefix="/api/v1")
app.include_router(drivers.router, prefix="/api/v1")
app.include_router(orders.router, prefix="/api/v1")
app.include_router(transports.router, prefix="/api/v1")
app.include_router(settings_router.router, prefix="/api/v1")
