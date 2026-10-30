"""Transport state machine: the single owner of legal states and transitions.

Binding table from the mvp1-domain-discovery signed schema (AGENTS.md /
openspec change mvp1-transports-and-orders design.md - State machine), plus
the order_cancelled cascade event added by the Order cancellation requirement.
No state writes may bypass can_transition().
"""

STATE_DRAFT = "draft"
STATE_ASSIGNED = "assigned"
STATE_AT_LOADING = "at_loading"
STATE_IN_TRANSIT = "in_transit"
STATE_AT_UNLOADING = "at_unloading"
STATE_COMPLETED = "completed"
STATE_IN_REVIEW = "in_review"
STATE_READY_FOR_INVOICING = "ready_for_invoicing"
STATE_RETURNED = "returned"
STATE_CANCELLED = "cancelled"

STATES = (
    STATE_DRAFT,
    STATE_ASSIGNED,
    STATE_AT_LOADING,
    STATE_IN_TRANSIT,
    STATE_AT_UNLOADING,
    STATE_COMPLETED,
    STATE_IN_REVIEW,
    STATE_READY_FOR_INVOICING,
    STATE_RETURNED,
    STATE_CANCELLED,
)

# States that have not yet reached completed - the order-cancel cascade set.
NOT_YET_COMPLETED_STATES = (
    STATE_DRAFT,
    STATE_ASSIGNED,
    STATE_AT_LOADING,
    STATE_IN_TRANSIT,
    STATE_AT_UNLOADING,
)

EVENT_ASSIGN = "assign"
EVENT_UNASSIGN = "unassign"
EVENT_ARRIVE_LOADING = "arrive_loading"
EVENT_START_TRANSIT = "start_transit"
EVENT_ARRIVE_UNLOADING = "arrive_unloading"
EVENT_FINISH_UNLOADING = "finish_unloading"
EVENT_HAND_IN_DOCUMENTS = "hand_in_documents"
EVENT_ACCEPT = "accept"
EVENT_REJECT = "reject"
EVENT_RESUBMIT = "resubmit"
EVENT_CANCEL = "cancel"
EVENT_ORDER_CANCELLED = "order_cancelled"

_TRANSITIONS: dict[tuple[str, str], str] = {
    (STATE_DRAFT, EVENT_ASSIGN): STATE_ASSIGNED,
    (STATE_ASSIGNED, EVENT_UNASSIGN): STATE_DRAFT,
    (STATE_ASSIGNED, EVENT_ARRIVE_LOADING): STATE_AT_LOADING,
    (STATE_AT_LOADING, EVENT_START_TRANSIT): STATE_IN_TRANSIT,
    (STATE_IN_TRANSIT, EVENT_ARRIVE_UNLOADING): STATE_AT_UNLOADING,
    (STATE_AT_UNLOADING, EVENT_FINISH_UNLOADING): STATE_COMPLETED,
    (STATE_COMPLETED, EVENT_HAND_IN_DOCUMENTS): STATE_IN_REVIEW,
    (STATE_IN_REVIEW, EVENT_ACCEPT): STATE_READY_FOR_INVOICING,
    (STATE_IN_REVIEW, EVENT_REJECT): STATE_RETURNED,
    (STATE_RETURNED, EVENT_RESUBMIT): STATE_IN_REVIEW,
    (STATE_DRAFT, EVENT_CANCEL): STATE_CANCELLED,
    (STATE_ASSIGNED, EVENT_CANCEL): STATE_CANCELLED,
    **{(state, EVENT_ORDER_CANCELLED): STATE_CANCELLED for state in NOT_YET_COMPLETED_STATES},
}

# Events a currently-assigned driver may fire on a transport.
DRIVER_EVENTS = frozenset(
    {
        EVENT_ARRIVE_LOADING,
        EVENT_START_TRANSIT,
        EVENT_ARRIVE_UNLOADING,
        EVENT_FINISH_UNLOADING,
        EVENT_HAND_IN_DOCUMENTS,
        EVENT_RESUBMIT,
    }
)

# Events reserved for the back-office side (dispatcher/admin).
DISPATCHER_EVENTS = frozenset({EVENT_CANCEL, EVENT_ACCEPT, EVENT_REJECT})

# Never callable through the public transition endpoint.
INTERNAL_EVENTS = frozenset({EVENT_ASSIGN, EVENT_UNASSIGN, EVENT_ORDER_CANCELLED})


def can_transition(state: str, event: str) -> str | None:
    """Return the target state, or None when the transition is not allowed."""
    return _TRANSITIONS.get((state, event))
