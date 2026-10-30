"""Portal settings schemas."""

from typing import Literal

from pydantic import BaseModel


class PortalSettingsOut(BaseModel):
    default_currency: str


class PortalSettingsUpdate(BaseModel):
    default_currency: Literal["CZK", "EUR"]
