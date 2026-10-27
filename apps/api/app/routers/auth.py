from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.deps import CurrentUser, Session
from app.models import RefreshToken, User, utcnow
from app.schemas import LoginRequest, ProfileUpdate, RefreshRequest, TokenPair, UserOut
from app.security import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _fail_unauthorized() -> HTTPException:
    return HTTPException(status_code=401, detail="Invalid credentials")


async def _issue_pair(session: Session, user: User) -> TokenPair:
    raw_refresh, expires_at = generate_refresh_token()
    token = RefreshToken(
        user_id=user.id, token_hash=hash_refresh_token(raw_refresh), expires_at=expires_at
    )
    session.add(token)
    access = create_access_token(user.id, user.roles)
    return TokenPair(access_token=access, refresh_token=raw_refresh)


async def _consume_refresh(session: Session, raw: str) -> User:
    result = await session.execute(
        select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw))
    )
    stored = result.scalar_one_or_none()
    now = datetime.now(UTC).replace(tzinfo=None)
    if stored is None or stored.revoked_at is not None or stored.expires_at < now:
        raise _fail_unauthorized()
    stored.revoked_at = now
    user = await session.get(User, stored.user_id)
    if user is None or not user.is_active:
        raise _fail_unauthorized()
    return user


@router.post("/login", response_model=TokenPair)
async def login(body: LoginRequest, session: Session) -> TokenPair:
    result = await session.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise _fail_unauthorized()
    if not verify_password(body.password, user.password_hash):
        # Constant-shape rejection: do not reveal whether the account exists.
        raise _fail_unauthorized()
    user.last_login_at = utcnow()
    session.add(user)
    pair = await _issue_pair(session, user)
    await session.commit()
    return pair


@router.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshRequest, session: Session) -> TokenPair:
    user = await _consume_refresh(session, body.refresh_token)
    pair = await _issue_pair(session, user)
    await session.commit()
    return pair


@router.post("/logout", status_code=204)
async def logout(body: RefreshRequest, session: Session) -> None:
    token_hash = hash_refresh_token(body.refresh_token)
    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    result = await session.execute(stmt)
    stored = result.scalar_one_or_none()
    if stored is not None and stored.revoked_at is None:
        stored.revoked_at = utcnow()
        session.add(stored)
    await session.commit()


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> User:
    return user


@router.patch("/me", response_model=UserOut)
async def update_me(body: ProfileUpdate, user: CurrentUser, session: Session) -> User:
    user.language = body.language
    session.add(user)
    await session.commit()
    return user
