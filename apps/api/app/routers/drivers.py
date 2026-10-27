import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.deps import ScopedGroupIds, Session, group_in_scope, require_roles
from app.models import ADMIN_ROLES, Group, User
from app.schemas import GroupMove, UserOut

router = APIRouter(prefix="/drivers", tags=["drivers"])

DriverCaller = Annotated[User, Depends(require_roles("dispatcher", *ADMIN_ROLES))]


@router.put("/{user_id}/group", response_model=UserOut)
async def assign_driver_group(
    user_id: uuid.UUID,
    body: GroupMove,
    session: Session,
    scoped: ScopedGroupIds,
    caller: DriverCaller,
) -> User:
    driver = await session.get(User, user_id)
    if driver is None or not driver.is_active:
        raise HTTPException(status_code=404, detail="Driver not found")
    if "driver" not in driver.roles:
        raise HTTPException(status_code=400, detail="User is not a driver")
    group = await session.get(Group, body.group_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    if scoped is not None:
        if not group_in_scope(scoped, group.id):
            raise HTTPException(
                status_code=403, detail="Moving resources involving a foreign group is admin work"
            )
        if driver.group_id is not None and not group_in_scope(scoped, driver.group_id):
            raise HTTPException(
                status_code=403, detail="Moving resources involving a foreign group is admin work"
            )
    driver.group_id = group.id
    session.add(driver)
    await session.commit()
    return driver
