"""Shared schema types (see AGENTS.md: API layout rule)."""

from typing import Literal

Language = Literal["cs", "en", "de"]
Role = Literal["driver", "dispatcher", "company-admin", "system-admin"]
