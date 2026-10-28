"""Shared model helpers and constants (see AGENTS.md: API layout rule)."""

from datetime import UTC, datetime

ROLES = ("driver", "dispatcher", "company-admin", "system-admin")
ADMIN_ROLES = ("company-admin", "system-admin")
LANGUAGES = ("cs", "en", "de")


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


__all__ = ["ROLES", "ADMIN_ROLES", "LANGUAGES", "utcnow"]
