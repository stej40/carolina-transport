"""Company-wide portal settings (default currency)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import Session, require_roles
from app.models import ADMIN_ROLES, PortalSettings, User
from app.schemas import PortalSettingsOut, PortalSettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])

SettingsCaller = Annotated[User, Depends(require_roles("dispatcher", *ADMIN_ROLES))]


async def _settings_row(session: AsyncSession) -> PortalSettings:
    row: PortalSettings | None = (
        await session.execute(select(PortalSettings).limit(1))
    ).scalar_one_or_none()
    if row is None:
        row = PortalSettings()
        session.add(row)
        await session.commit()
    return row


@router.get("", response_model=PortalSettingsOut)
async def get_settings(session: Session, caller: SettingsCaller) -> PortalSettingsOut:
    row = await _settings_row(session)
    return PortalSettingsOut(default_currency=row.default_currency)


@router.put("", response_model=PortalSettingsOut)
async def update_settings(
    body: PortalSettingsUpdate, session: Session, caller: SettingsCaller
) -> PortalSettingsOut:
    row = await _settings_row(session)
    row.default_currency = body.default_currency
    session.add(row)
    await session.commit()
    return PortalSettingsOut(default_currency=row.default_currency)
