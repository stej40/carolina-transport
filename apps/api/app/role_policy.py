"""Role-change policy: authority matrix and escalation guards.

Pure data-level functions shared by the user-management endpoints
(see openspec capability `identity-auth`, requirements added by
change user-role-assignment). Reason codes returned by
`evaluate_role_change` are ordered by precedence; the router maps them:

- self-change          -> 403
- authority            -> 403
- scope                -> 403
- last-system-admin    -> 409
"""

import uuid
from collections.abc import Iterable, Sequence
from typing import Literal

Role = Literal["driver", "dispatcher", "company-admin", "system-admin"]

ADMIN_ROLES: tuple[str, ...] = ("company-admin", "system-admin")

# Callers whose membership grants authority over each role (symmetric for
# grant and revoke).
ROLE_AUTHORITY: dict[str, frozenset[str]] = {
    "driver": frozenset({"dispatcher", *ADMIN_ROLES}),
    "dispatcher": frozenset(ADMIN_ROLES),
    "company-admin": frozenset({"system-admin"}),
    "system-admin": frozenset({"system-admin"}),
}

# A dispatcher without admin roles may only act on `driver`, and never on
# accounts already holding one of these.
DISPATCHER_PROTECTED_ROLES: frozenset[str] = frozenset({"dispatcher", *ADMIN_ROLES})

DenialCode = Literal["self-change", "authority", "scope", "last-system-admin"]


def _dispatcher_scope_denied(
    caller_roles: set[str],
    current: set[str],
    wanted: set[str],
    touched: set[str],
    target_group_id: uuid.UUID | None,
    caller_group_ids: set[uuid.UUID] | None,
) -> bool:
    """Dispatcher-without-admin may only act on driver for in-scope targets."""
    if "dispatcher" not in caller_roles or caller_roles & set(ADMIN_ROLES):
        return False
    if current & DISPATCHER_PROTECTED_ROLES or wanted & DISPATCHER_PROTECTED_ROLES:
        return True
    if "driver" not in touched:
        return False
    return (
        target_group_id is None
        or caller_group_ids is None
        or target_group_id not in caller_group_ids
    )


def denied_roles(caller_roles: Iterable[str], touched_roles: Iterable[str]) -> set[str]:
    """Touched roles the caller lacks authority over (empty = fully authorized)."""
    caller = set(caller_roles)
    return {role for role in touched_roles if not caller & ROLE_AUTHORITY[role]}


def evaluate_role_change(
    *,
    caller_roles: Sequence[str],
    caller_group_ids: set[uuid.UUID] | None,
    target_roles: Sequence[str],
    desired_roles: Sequence[str],
    target_group_id: uuid.UUID | None,
    caller_id: uuid.UUID,
    target_id: uuid.UUID,
    other_active_system_admins: bool,
) -> list[DenialCode]:
    """Return ordered denial codes for a full role replacement; [] means allowed.

    `target_group_id` is the target's *effective* home group after the change
    (request `group_id` when supplied, else the stored one). `caller_group_ids`
    is None for unrestricted (admin) callers, per `deps.get_scoped_group_ids`.
    """
    if caller_id == target_id:
        return ["self-change"]

    denials: list[DenialCode] = []
    current, wanted = set(target_roles), set(desired_roles)
    touched = current ^ wanted

    if denied_roles(caller_roles, touched):
        denials.append("authority")

    if _dispatcher_scope_denied(
        set(caller_roles), current, wanted, touched, target_group_id, caller_group_ids
    ):
        denials.append("scope")

    if "system-admin" in current - wanted and not other_active_system_admins:
        denials.append("last-system-admin")

    return denials


__all__ = [
    "ADMIN_ROLES",
    "DISPATCHER_PROTECTED_ROLES",
    "DenialCode",
    "ROLE_AUTHORITY",
    "denied_roles",
    "evaluate_role_change",
]
