import uuid
from typing import Any

import pytest

from app.role_policy import denied_roles, evaluate_role_change

CALLER_ID = uuid.uuid4()
TARGET_ID = uuid.uuid4()
GROUP_A = uuid.uuid4()
GROUP_B = uuid.uuid4()

ALL_ROLES = ("driver", "dispatcher", "company-admin", "system-admin")

AUTHORITY_OK = {
    "driver": ("dispatcher", "company-admin", "system-admin"),
    "dispatcher": ("company-admin", "system-admin"),
    "company-admin": ("system-admin",),
    "system-admin": ("system-admin",),
}


def _change(
    caller_roles: list[str], current: list[str], desired: list[str], **kw: Any
) -> list[str]:
    params: dict[str, Any] = {
        "caller_group_ids": None,
        "target_group_id": None,
        "caller_id": CALLER_ID,
        "target_id": TARGET_ID,
        "other_active_system_admins": True,
    }
    params.update(kw)
    return evaluate_role_change(
        caller_roles=caller_roles, target_roles=current, desired_roles=desired, **params
    )


class TestDeniedRoles:
    @pytest.mark.parametrize("role", ALL_ROLES)
    def test_matrix_grant_side(self, role: str) -> None:
        allowed = set(AUTHORITY_OK[role])
        for caller in ALL_ROLES:
            touched = denied_roles([caller], [role])
            if caller in allowed:
                assert touched == set(), f"{caller} should manage {role}"
            else:
                assert touched == {role}, f"{caller} must not manage {role}"

    def test_multi_role_change_needs_every_authority(self) -> None:
        assert denied_roles(["company-admin"], ["dispatcher", "company-admin"]) == {"company-admin"}


class TestGuards:
    def test_self_change_short_circuits(self) -> None:
        assert _change(["system-admin"], ["system-admin"], ["dispatcher"], caller_id=TARGET_ID) == [
            "self-change"
        ]

    def test_last_system_admin_conflict(self) -> None:
        denials = _change(
            ["system-admin"],
            ["system-admin"],
            ["dispatcher"],
            other_active_system_admins=False,
        )
        assert denials == ["last-system-admin"]

    def test_grant_system_admin_needs_last_admin_check(self) -> None:
        assert (
            _change(["system-admin"], [], ["system-admin"], other_active_system_admins=False) == []
        )

    def test_noop_allowed_for_authorized_admin(self) -> None:
        assert _change(["company-admin"], ["driver"], ["driver"]) == []


class TestDispatcherScope:
    def test_grant_driver_in_own_group(self) -> None:
        assert (
            _change(
                ["dispatcher"], [], ["driver"], caller_group_ids={GROUP_A}, target_group_id=GROUP_A
            )
            == []
        )

    @pytest.mark.parametrize("target_group_id", [GROUP_B, None])
    def test_grant_driver_outside_scope(self, target_group_id: uuid.UUID | None) -> None:
        denials = _change(
            ["dispatcher"],
            [],
            ["driver"],
            caller_group_ids={GROUP_A},
            target_group_id=target_group_id,
        )
        assert denials == ["scope"]

    def test_revoke_driver_outside_scope(self) -> None:
        assert _change(
            ["dispatcher"], ["driver"], [], caller_group_ids={GROUP_A}, target_group_id=GROUP_B
        ) == ["scope"]

    def test_noop_on_dispatcher_account_still_rejected(self) -> None:
        assert _change(
            ["dispatcher"],
            ["dispatcher"],
            ["dispatcher"],
            caller_group_ids={GROUP_A},
            target_group_id=GROUP_A,
        ) == ["scope"]

    def test_dispatcher_touching_admin_roles_denied(self) -> None:
        denials = _change(["dispatcher"], ["company-admin"], [], caller_group_ids={GROUP_A})
        assert "authority" in denials and "scope" in denials

    def test_dispatcher_with_admin_role_is_unrestricted(self) -> None:
        assert _change(["dispatcher", "company-admin"], ["driver"], []) == []
