import uuid
from typing import Annotated, Any

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import User
from app.security import decode_access_token

Session = Annotated[AsyncSession, Depends(get_session)]
bearer_scheme = HTTPBearer(auto_error=False)


class AuthError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Session,
) -> User:
    if credentials is None or not credentials.credentials:
        raise AuthError(401, "Not authenticated")
    try:
        payload: dict[str, Any] = decode_access_token(credentials.credentials)
    except (jwt.InvalidTokenError, jwt.PyJWTError):
        raise AuthError(401, "Invalid or expired token") from None
    if payload.get("typ") != "access":
        raise AuthError(401, "Invalid token type")
    try:
        user_id = uuid.UUID(str(payload.get("sub", "")))
    except ValueError:
        raise AuthError(401, "Invalid token subject") from None
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise AuthError(401, "User no longer exists")
    return user


def require_roles(*roles: str) -> Any:
    async def checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        if not any(role in user.roles for role in roles):
            raise AuthError(403, "Insufficient role")
        return user

    return checker


CurrentUser = Annotated[User, Depends(get_current_user)]

dispatcher_only = require_roles("dispatcher")
admin_only = require_roles("company-admin", "system-admin")

__all__ = [
    "CurrentUser",
    "Session",
    "admin_only",
    "dispatcher_only",
    "get_current_user",
    "require_roles",
]
