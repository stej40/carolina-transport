import uuid
from typing import Annotated, TypeVar, cast

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import ScopedGroupIds, Session, admin_only, group_in_scope, require_roles
from app.models import ADMIN_ROLES, Group, Trailer, Truck, User
from app.models.common import utcnow
from app.schemas import FleetCreate, FleetOut, FleetUpdate, GroupMove

FleetModel = TypeVar("FleetModel", Truck, Trailer)

fleet_writer = require_roles("dispatcher", *ADMIN_ROLES)
FleetCaller = Annotated[User, Depends(fleet_writer)]
AdminCaller = Annotated[User, Depends(admin_only)]


def normalize_spz(spz: str) -> str:
    return " ".join(spz.split()).upper()


def build_fleet_router(model: type[Truck] | type[Trailer], prefix: str, tag: str) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=[tag])

    async def _load_scoped(
        session: AsyncSession, scoped: set[uuid.UUID] | None, resource_id: uuid.UUID
    ) -> Truck | Trailer:
        resource = cast("Truck | Trailer | None", await session.get(model, resource_id))
        if (
            resource is None
            or resource.retired_at is not None
            or not group_in_scope(scoped, resource.group_id)
        ):
            raise HTTPException(status_code=404, detail="Not found")
        return resource

    @router.post("", response_model=FleetOut, status_code=201)
    async def register(
        body: FleetCreate, session: Session, scoped: ScopedGroupIds, caller: AdminCaller
    ) -> Truck | Trailer:
        group = await session.get(Group, body.group_id)
        if group is None or not group_in_scope(scoped, group.id):
            raise HTTPException(status_code=404, detail="Group not found")
        spz = normalize_spz(body.spz)
        dup = await session.execute(
            select(model).where(model.spz == spz, model.retired_at.is_(None))
        )
        if dup.scalar_one_or_none() is not None:
            raise HTTPException(status_code=409, detail="Registration mark already in use")
        resource = model(spz=spz, group_id=group.id, label=body.label)
        session.add(resource)
        await session.commit()
        return resource

    @router.get("", response_model=list[FleetOut])
    async def list_resources(
        session: Session,
        scoped: ScopedGroupIds,
        caller: FleetCaller,
        include_retired: Annotated[bool, Query()] = False,
    ) -> list[Truck | Trailer]:
        if include_retired and scoped is not None:
            raise HTTPException(status_code=403, detail="Retired fleet is admin-only")
        stmt = select(model).order_by(model.spz)
        if not include_retired:
            stmt = stmt.where(model.retired_at.is_(None))
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

    @router.patch("/{resource_id}", response_model=FleetOut)
    async def update_label(
        resource_id: uuid.UUID,
        body: FleetUpdate,
        session: Session,
        scoped: ScopedGroupIds,
        caller: FleetCaller,
    ) -> Truck | Trailer:
        resource = await _load_scoped(session, scoped, resource_id)
        if "label" in body.model_fields_set:
            resource.label = body.label
            session.add(resource)
            await session.commit()
        return resource

    @router.delete("/{resource_id}/group", status_code=204)
    async def unassign(
        resource_id: uuid.UUID, session: Session, scoped: ScopedGroupIds, caller: AdminCaller
    ) -> None:
        resource = await _load_scoped(session, scoped, resource_id)
        if resource.group_id is None:
            return
        resource.group_id = None
        session.add(resource)
        await session.commit()

    @router.delete("/{resource_id}", status_code=204)
    async def retire(resource_id: uuid.UUID, session: Session, caller: AdminCaller) -> None:
        resource = cast("Truck | Trailer | None", await session.get(model, resource_id))
        if resource is None:
            raise HTTPException(status_code=404, detail="Not found")
        if resource.retired_at is not None:
            return
        resource.retired_at = utcnow()
        session.add(resource)
        await session.commit()

    @router.post("/{resource_id}/restore", response_model=FleetOut)
    async def restore(
        resource_id: uuid.UUID, session: Session, caller: AdminCaller
    ) -> Truck | Trailer:
        resource = cast("Truck | Trailer | None", await session.get(model, resource_id))
        if resource is None:
            raise HTTPException(status_code=404, detail="Not found")
        if resource.retired_at is None:
            return resource
        dup = await session.execute(
            select(model)
            .where(
                model.spz == resource.spz,
                model.retired_at.is_(None),
                model.id != resource.id,
            )
            .limit(1)
        )
        if dup.scalar_one_or_none() is not None:
            raise HTTPException(status_code=409, detail="SPZ already in active use")
        resource.retired_at = None
        session.add(resource)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            raise HTTPException(status_code=409, detail="SPZ already in active use") from None
        return resource

    return router


trucks_router = build_fleet_router(Truck, "/trucks", "trucks")
trailers_router = build_fleet_router(Trailer, "/trailers", "trailers")
