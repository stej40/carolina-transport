"""Idempotency-Key middleware for domain write endpoints (offline outbox
replay safety, constraint 4).

Keyed on (user, Idempotency-Key); the first request under a key is executed
and its JSON response stored, replays of the identical request return the
stored result with `Idempotency-Replayed: true`. Same key with a different
payload is rejected (422). Non-2xx outcomes are not stored, so the client may
retry with the same key. Requests without the header, without a valid access
token, or outside the domain prefixes pass through untouched.
"""

import hashlib
import json
import uuid
from typing import Any, cast

import jwt
from sqlalchemy import delete
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.models import IdempotencyKey
from app.security import decode_access_token

IDEMPOTENT_METHODS = {"POST", "PATCH", "PUT", "DELETE"}
DOMAIN_PREFIXES = ("/api/v1/orders", "/api/v1/transports", "/api/v1/settings")


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
        if request.method not in IDEMPOTENT_METHODS or not path.startswith(DOMAIN_PREFIXES):
            return await call_next(request)
        key = request.headers.get("Idempotency-Key")
        user_id = _token_user_id(request)
        if not key or user_id is None:
            return await call_next(request)

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
                return JSONResponse(
                    status_code=int(stored["status"]),
                    content=stored["body"],
                    headers={"Idempotency-Replayed": "true"},
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
                    parsed = json.loads(raw)
                except (ValueError, UnicodeDecodeError):
                    parsed = None
                if parsed is not None:
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
