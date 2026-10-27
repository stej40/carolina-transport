import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.deps import ScopedGroupIds, Session, admin_only, group_in_scope, require_roles
from app.models import ADMIN_ROLES, Group, GroupMember, Trailer, Truck, User
from app.schemas import GroupCreate, GroupDetailOut, GroupOut, GroupUpdate, UserOut

router = APIRouter(prefix="/groups", tags=["groups"])

AdminGroup = Annotated[User, Depends(admin_only)]
group_reader = require_roles("dispatcher", *ADMIN_ROLES)
GroupCaller = Annotated[User, Depends(group_reader)]


async def _get_group_or_404(session: Session, group_id: uuid.UUID) -> Group:
    group = await session.get(Group, group_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


@router.post("", response_model=GroupOut, status_code=201)
async def create_group(body: GroupCreate, session: Session, caller: AdminGroup) -> Group:
    group = Group(name=body.name)
    session.add(group)
    await session.commit()
    return group


@router.get("", response_model=list[GroupOut])
async def list_groups(session: Session, scoped: ScopedGroupIds, caller: GroupCaller) -> list[Group]:
    stmt = select(Group).order_by(Group.name)
    if scoped is not None:
        if not scoped:
            return []
        stmt = stmt.where(Group.id.in_(scoped))
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/{group_id}", response_model=GroupDetailOut)
async def group_detail(
    group_id: uuid.UUID, session: Session, scoped: ScopedGroupIds, caller: GroupCaller
) -> GroupDetailOut:
    group = await _get_group_or_404(session, group_id)
    if not group_in_scope(scoped, group.id):
        raise HTTPException(status_code=404, detail="Group not found")
    members_result = await session.execute(
        select(User)
        .join(GroupMember, GroupMember.user_id == User.id)
        .where(GroupMember.group_id == group.id)
        .order_by(User.name)
    )
    users_result = await session.execute(
        select(User).where(User.group_id == group.id, User.is_active.is_(True)).order_by(User.name)
    )
    drivers = [u for u in users_result.scalars().all() if "driver" in u.roles]
    trucks_result = await session.execute(
        select(Truck).where(Truck.group_id == group.id).order_by(Truck.spz)
    )
    trailers_result = await session.execute(
        select(Trailer).where(Trailer.group_id == group.id).order_by(Trailer.spz)
    )
    return GroupDetailOut(
        id=group.id,
        name=group.name,
        members=[UserOut.model_validate(u) for u in members_result.scalars().all()],
        drivers=[UserOut.model_validate(u) for u in drivers],
        trucks=[t for t in trucks_result.scalars().all()],
        trailers=[t for t in trailers_result.scalars().all()],
    )


@router.patch("/{group_id}", response_model=GroupOut)
async def rename_group(
    group_id: uuid.UUID, body: GroupUpdate, session: Session, caller: AdminGroup
) -> Group:
    group = await _get_group_or_404(session, group_id)
    group.name = body.name
    session.add(group)
    await session.commit()
    return group


@router.put("/{group_id}/members/{user_id}", status_code=204)
async def add_member(
    group_id: uuid.UUID, user_id: uuid.UUID, session: Session, caller: AdminGroup
) -> None:
    group = await _get_group_or_404(session, group_id)
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if "dispatcher" not in user.roles:
        raise HTTPException(status_code=400, detail="Only dispatchers can join a group")
    existing = await session.get(GroupMember, (group.id, user.id))
    if existing is None:
        session.add(GroupMember(group_id=group.id, user_id=user.id))
        await session.commit()


@router.delete("/{group_id}/members/{user_id}", status_code=204)
async def remove_member(
    group_id: uuid.UUID, user_id: uuid.UUID, session: Session, caller: AdminGroup
) -> None:
    group = await _get_group_or_404(session, group_id)
    member = await session.get(GroupMember, (group.id, user_id))
    if member is None:
        raise HTTPException(status_code=404, detail="Not a member of this group")
    await session.delete(member)
    await session.commit()
