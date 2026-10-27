import uuid
from typing import Annotated, TypeVar, cast

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import ScopedGroupIds, Session, group_in_scope, require_roles
from app.models import ADMIN_ROLES, Group, Trailer, Truck, User
from app.schemas import FleetCreate, FleetOut, GroupMove

FleetModel = TypeVar("FleetModel", Truck, Trailer)

fleet_writer = require_roles("dispatcher", *ADMIN_ROLES)
FleetCaller = Annotated[User, Depends(fleet_writer)]


def normalize_spz(spz: str) -> str:
    return " ".join(spz.split()).upper()


def build_fleet_router(model: type[Truck] | type[Trailer], prefix: str, tag: str) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=[tag])

    async def _load_scoped(
        session: AsyncSession, scoped: set[uuid.UUID] | None, resource_id: uuid.UUID
    ) -> Truck | Trailer:
        resource = cast("Truck | Trailer | None", await session.get(model, resource_id))
        if resource is None or not group_in_scope(scoped, resource.group_id):
            raise HTTPException(status_code=404, detail="Not found")
        return resource

    @router.post("", response_model=FleetOut, status_code=201)
    async def register(
        body: FleetCreate, session: Session, scoped: ScopedGroupIds, caller: FleetCaller
    ) -> Truck | Trailer:
        group = await session.get(Group, body.group_id)
        if group is None or not group_in_scope(scoped, group.id):
            raise HTTPException(status_code=404, detail="Group not found")
        spz = normalize_spz(body.spz)
        dup = await session.execute(select(model).where(model.spz == spz))
        if dup.scalar_one_or_none() is not None:
            raise HTTPException(status_code=409, detail="Registration mark already in use")
        resource = model(spz=spz, group_id=group.id, label=body.label)
        session.add(resource)
        await session.commit()
        return resource

    @router.get("", response_model=list[FleetOut])
    async def list_resources(
        session: Session, scoped: ScopedGroupIds, caller: FleetCaller
    ) -> list[Truck | Trailer]:
        stmt = select(model).order_by(model.spz)
        if scoped is not None:
            if not scoped:
                return []
            stmt = stmt.where(model.group_id.in_(scoped))
        result = await session.execute(stmt)
        return cast("list[Truck | Trailer]", list(result.scalars().all()))

    @router.patch("/{resource_id}/group", response_model=FleetOut)
    async def move(
        resource_id: uuid.UUID,
        body: GroupMove,
        session: Session,
        scoped: ScopedGroupIds,
        caller: FleetCaller,
    ) -> Truck | Trailer:
        resource = await _load_scoped(session, scoped, resource_id)
        group = await session.get(Group, body.group_id)
        if group is None:
            raise HTTPException(status_code=404, detail="Group not found")
        if not group_in_scope(scoped, group.id):
            raise HTTPException(
                status_code=403, detail="Moving resources involving a foreign group is admin work"
            )
        resource.group_id = group.id
        session.add(resource)
        await session.commit()
        return resource

    return router


trucks_router = build_fleet_router(Truck, "/trucks", "trucks")
trailers_router = build_fleet_router(Trailer, "/trailers", "trailers")
