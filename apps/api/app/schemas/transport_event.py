"""Transport event log schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class TransportEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transport_id: uuid.UUID | None
    order_id: uuid.UUID | None
    event_type: str
    from_state: str | None
    to_state: str | None
    actor_id: uuid.UUID | None
    payload: dict[str, Any]
    occurred_at: datetime
