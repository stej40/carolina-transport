import uuid
from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.deps import ScopedGroupIds, Session, admin_only, require_roles
from app.models import ADMIN_ROLES, Group, User
from app.role_policy import DenialCode, denied_roles, evaluate_role_change
from app.schemas import UserCreate, UserOut, UserRolesReplace
from app.security import hash_password

router = APIRouter(prefix="/users", tags=["users"])

AdminUser = Annotated[User, Depends(admin_only)]
RoleCallerUser = Annotated[User, Depends(require_roles("dispatcher", *ADMIN_ROLES))]
user_reader = require_roles("dispatcher", *ADMIN_ROLES)

_DENIAL_HTTP: dict[DenialCode, tuple[int, str]] = {
    "self-change": (403, "You cannot change your own roles (use another admin or the seed script)"),
    "authority": (403, "Insufficient authority for one or more roles"),
    "scope": (403, "Target user is outside your group scope"),
    "last-system-admin": (409, "Cannot leave the system without an active system-admin"),
}


def _managing_admin_accounts_forbidden(caller: User, roles: Sequence[str]) -> bool:
    return bool(denied_roles(caller.roles, roles))


async def _other_active_system_admins(session: Session, exclude_id: uuid.UUID) -> bool:
    rows = await session.execute(select(User.roles).where(User.is_active, User.id != exclude_id))
    return any("system-admin" in roles for roles in rows.scalars())


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
    if (
        target.is_active
        and "system-admin" in target.roles
        and not await _other_active_system_admins(session, target.id)
    ):
        raise HTTPException(
            status_code=409, detail="Cannot deactivate the last active system-admin account"
        )
    target.is_active = False
    session.add(target)
    await session.commit()
    return target


@router.put(
    "/{user_id}/roles",
    response_model=UserOut,
    responses={
        403: {"description": "Self-change or caller lacks authority / target outside group scope"},
        404: {"description": "Active user or group not found"},
        409: {"description": "Change would leave no active system-admin"},
    },
)
async def replace_user_roles(
    user_id: uuid.UUID,
    body: UserRolesReplace,
    session: Session,
    caller: RoleCallerUser,
    scoped: ScopedGroupIds,
) -> User:
    target = await session.get(User, user_id)
    if target is None or not target.is_active:
        raise HTTPException(status_code=404, detail="User not found")
    if body.group_id is not None and await session.get(Group, body.group_id) is None:
        raise HTTPException(status_code=404, detail="Group not found")
    current, wanted = set(target.roles), set(body.roles)
    other_admins = True
    if "system-admin" in current - wanted:
        other_admins = await _other_active_system_admins(session, target.id)
    denials = evaluate_role_change(
        caller_roles=caller.roles,
        caller_group_ids=scoped,
        target_roles=target.roles,
        desired_roles=body.roles,
        target_group_id=body.group_id or target.group_id,
        caller_id=caller.id,
        target_id=target.id,
        other_active_system_admins=other_admins,
    )
    if denials:
        status_code, detail = _DENIAL_HTTP[denials[0]]
        raise HTTPException(status_code=status_code, detail=detail)
    target.roles = list(dict.fromkeys(body.roles))
    if body.group_id is not None:
        target.group_id = body.group_id
    session.add(target)
    await session.commit()
    return target
