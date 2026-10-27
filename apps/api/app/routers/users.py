import uuid
from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.deps import Session, admin_only, require_roles
from app.models import ADMIN_ROLES, User
from app.schemas import UserCreate, UserOut
from app.security import hash_password

router = APIRouter(prefix="/users", tags=["users"])

AdminUser = Annotated[User, Depends(admin_only)]
user_reader = require_roles("dispatcher", *ADMIN_ROLES)


def _managing_admin_accounts_forbidden(caller: User, roles: Sequence[str]) -> bool:
    touches_admin = any(role in ADMIN_ROLES for role in roles)
    return touches_admin and "system-admin" not in caller.roles


@router.get("", response_model=list[UserOut], dependencies=[Depends(user_reader)])
async def list_users(session: Session) -> list[User]:
    result = await session.execute(select(User).order_by(User.name))
    return list(result.scalars().all())


@router.post("", response_model=UserOut, status_code=201)
async def create_user(body: UserCreate, session: Session, caller: AdminUser) -> User:
    if _managing_admin_accounts_forbidden(caller, body.roles):
        raise HTTPException(status_code=403, detail="Only a system-admin may create admin accounts")
    email = body.email.lower()
    dup = await session.execute(select(User).where(User.email == email))
    if dup.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="A user with this e-mail already exists")
    user = User(
        email=email,
        name=body.name,
        password_hash=hash_password(body.password),
        roles=list(body.roles),
    )
    session.add(user)
    await session.commit()
    return user


@router.post("/{user_id}/deactivate", response_model=UserOut)
async def deactivate_user(user_id: uuid.UUID, session: Session, caller: AdminUser) -> User:
    target = await session.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    if _managing_admin_accounts_forbidden(caller, target.roles):
        raise HTTPException(
            status_code=403, detail="Only a system-admin may deactivate admin accounts"
        )
    target.is_active = False
    session.add(target)
    await session.commit()
    return target
