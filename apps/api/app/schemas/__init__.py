"""Pydantic schemas package.

Layout rule (AGENTS.md): one module per entity/family; this __init__ is the
only aggregation point and re-exports every public name.
"""

from app.schemas.auth import LoginRequest, RefreshRequest, TokenPair
from app.schemas.common import Language, Role
from app.schemas.fleet import FleetCreate, FleetOut
from app.schemas.group import (
    GroupCreate,
    GroupDetailOut,
    GroupMove,
    GroupOut,
    GroupUpdate,
)
from app.schemas.user import ProfileUpdate, UserCreate, UserOut

__all__ = [
    "Language",
    "Role",
    "LoginRequest",
    "RefreshRequest",
    "TokenPair",
    "ProfileUpdate",
    "UserCreate",
    "UserOut",
    "GroupCreate",
    "GroupDetailOut",
    "GroupMove",
    "GroupOut",
    "GroupUpdate",
    "FleetCreate",
    "FleetOut",
]
