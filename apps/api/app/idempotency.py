"""Idempotency-Key middleware for all API write endpoints (offline outbox
replay safety, constraint 4).

Every POST/PATCH/PUT/DELETE under `/api/v1` except `/api/v1/auth/*` must
carry an `Idempotency-Key` header (missing -> 400); auth token endpoints are
exempt because their responses are credentials and must never enter the
plaintext replay cache. Keyed on (user, Idempotency-Key); the first request
under a key is executed and its JSON response stored (empty/non-JSON success
bodies are stored as a null body), replays of the identical request return
the stored result with `Idempotency-Replayed: true`. Same key with a
different payload is rejected (422). Non-2xx outcomes are not stored, so the
client may retry with the same key. Requests without a valid access token
pass through and are rejected by the endpoint's own auth dependency.
"""

import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import jwt
from sqlalchemy import delete
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.models import IdempotencyKey
from app.security import decode_access_token

IDEMPOTENT_METHODS = {"POST", "PATCH", "PUT", "DELETE"}
API_SCOPE_PREFIX = "/api/v1/"
AUTH_EXEMPT_PREFIX = "/api/v1/auth/"
RETENTION_DAYS = 30

MISSING_KEY_DETAIL = (
    "Missing required 'Idempotency-Key' header: every write must carry a unique "
    "key per intended operation so safe retries and offline replays return the "
    "original result instead of duplicating it."
)


def _requires_idempotency_key(method: str, path: str) -> bool:
    if method not in IDEMPOTENT_METHODS:
        return False
    if not path.startswith(API_SCOPE_PREFIX):
        return False
    return not path.startswith(AUTH_EXEMPT_PREFIX)


async def purge_stale_idempotency_keys(
    maker: async_sessionmaker[AsyncSession],
) -> int:
    """Delete replay rows older than the retention window (startup task)."""
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=RETENTION_DAYS)
    async with maker() as session:
        result = cast(
            "CursorResult[Any]",
            await session.execute(delete(IdempotencyKey).where(IdempotencyKey.created_at < cutoff)),
        )
        await session.commit()
    return result.rowcount


def _token_user_id(request: Request) -> uuid.UUID | None:
    header = request.headers.get("Authorization", "")
    if not header.lower().startswith("bearer "):
        return None
    try:
        payload = decode_access_token(header.split(" ", 1)[1])
    except (jwt.InvalidTokenError, jwt.PyJWTError):
        return None
    if payload.get("typ") != "access":
        return None
    try:
        return uuid.UUID(str(payload.get("sub", "")))
    except ValueError:
        return None


class IdempotencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if not _requires_idempotency_key(request.method, path):
            return await call_next(request)
        user_id = _token_user_id(request)
        if user_id is None:
            return await call_next(request)
        key = request.headers.get("Idempotency-Key")
        if not key:
            return JSONResponse(status_code=400, content={"detail": MISSING_KEY_DETAIL})

        body = await request.body()
        request_hash = hashlib.sha256(f"{request.method}\n{path}\n".encode() + body).hexdigest()
        maker = request.app.state.session_maker

        async with maker() as session:
            existing = await session.get(IdempotencyKey, (user_id, key))
            if existing is not None:
                if existing.response is None:
                    return JSONResponse(
                        status_code=409,
                        content={"detail": "Idempotent request already in flight"},
                    )
                if existing.request_hash != request_hash:
                    return JSONResponse(
                        status_code=422,
                        content={"detail": "Idempotency-Key reused with a different request"},
                    )
                stored: dict[str, Any] = existing.response
                replay_headers = {"Idempotency-Replayed": "true"}
                if stored["body"] is None:
                    return Response(status_code=int(stored["status"]), headers=replay_headers)
                return JSONResponse(
                    status_code=int(stored["status"]),
                    content=stored["body"],
                    headers=replay_headers,
                )
            session.add(IdempotencyKey(user_id=user_id, key=key, request_hash=request_hash))
            await session.commit()

        response = await call_next(request)
        stream = cast(Any, response).body_iterator
        chunks = [chunk async for chunk in stream]
        raw = b"".join(chunks)

        async with maker() as session:
            row = await session.get(IdempotencyKey, (user_id, key))
            if row is None:
                pass
            elif 200 <= response.status_code < 300:
                try:
                    parsed: Any = json.loads(raw)
                except (ValueError, UnicodeDecodeError):
                    parsed = None
                row.response = {"status": response.status_code, "body": parsed}
                await session.commit()
            else:
                await session.execute(
                    delete(IdempotencyKey).where(
                        IdempotencyKey.user_id == user_id, IdempotencyKey.key == key
                    )
                )
                await session.commit()

        headers = {k: v for k, v in response.headers.items() if k.lower() != "content-length"}
        rebuilt = Response(content=raw, status_code=response.status_code, headers=headers)
        if response.media_type:
            rebuilt.media_type = response.media_type
        return rebuilt
