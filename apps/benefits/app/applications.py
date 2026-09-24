"""Benefits' runtime state for the application protocol (docs/design.md §6).

In-memory, per process, volatile — same decision as the Wallet's and Payroll's
(docs/decisions.md). One process serves every request (render.yaml, one worker), so no lock is
needed here. Everything is lost on restart, which the intent accepts.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import uuid4

from app.eligibility import Determination
from app.verify import Outcome

PENDING_TTL = timedelta(minutes=15)


@dataclass
class PendingRequest:
    created_at: datetime


@dataclass
class Presented:
    """One credential from a presentation, kept verbatim for the admin view."""

    token: str
    kind: str  # "identity" | "income"
    outcome: Outcome


@dataclass
class Facts:
    region: str
    county: str
    paystubs: list[dict]  # {"employer", "pay_date", "gross_pay"}, in presented order


@dataclass
class Application:
    id: str
    received_at: datetime
    subject_id: str | None  # read even from an unverified identity credential
    name: str | None  # "Given Family"
    presented: list[Presented]
    same_subject: bool | None
    outcome: str  # "decided" | "refused"
    reason: str | None = None  # set when refused
    facts: Facts | None = None  # set when decided
    determination: Determination | None = None  # set when decided
    issued: dict[str, tuple[str, str]] = field(default_factory=dict)  # program -> (id, jwt); #106


@dataclass
class Connection:
    connected_at: datetime
    application_id: str
    connection_id: str


_pending: dict[str, PendingRequest] = {}
_applications: list[Application] = []  # newest last
_connections: dict[str, Connection] = {}  # subject id -> Connection
_by_connection_id: dict[str, str] = {}  # connection id -> subject id


def _prune_stale(now: datetime) -> None:
    stale = [rid for rid, r in _pending.items() if now - r.created_at > PENDING_TTL]
    for rid in stale:
        del _pending[rid]


def create_request(now: datetime) -> str:
    """Records a pending request and returns its id. Bounds memory by pruning old ones."""
    _prune_stale(now)
    request_id = uuid4().hex
    _pending[request_id] = PendingRequest(created_at=now)
    return request_id


def peek_request(request_id: str, now: datetime) -> PendingRequest | None:
    """For the by-reference GET: doesn't remove it, so it can be fetched any number of times
    until a presentation answers it (docs/design.md §2)."""
    request = _pending.get(request_id)
    if request is None or now - request.created_at > PENDING_TTL:
        return None
    return request


def pop_request(request_id: str, now: datetime) -> PendingRequest | None:
    """One-shot: posting a presentation removes it, whatever the presentation turns out to
    verify as. None if unknown, already answered, or expired."""
    request = _pending.pop(request_id, None)
    if request is None or now - request.created_at > PENDING_TTL:
        return None
    return request


def record_application(
    *,
    subject_id: str | None,
    name: str | None,
    presented: list[Presented],
    same_subject: bool | None,
    outcome: str,
    reason: str | None,
    facts: Facts | None,
    determination: Determination | None,
    now: datetime,
) -> Application:
    application = Application(
        id=uuid4().hex,
        received_at=now,
        subject_id=subject_id,
        name=name,
        presented=presented,
        same_subject=same_subject,
        outcome=outcome,
        reason=reason,
        facts=facts,
        determination=determination,
    )
    _applications.append(application)
    return application


def connect(subject_id: str, application_id: str, now: datetime) -> str:
    """Applying again replaces the connection: a new id, and the old one stops resolving
    (docs/design.md §6)."""
    old = _connections.get(subject_id)
    if old is not None:
        _by_connection_id.pop(old.connection_id, None)
    connection_id = uuid4().hex
    _connections[subject_id] = Connection(
        connected_at=now, application_id=application_id, connection_id=connection_id
    )
    _by_connection_id[connection_id] = subject_id
    return connection_id


def application_for_connection(connection_id: str) -> Application | None:
    subject_id = _by_connection_id.get(connection_id)
    if subject_id is None:
        return None
    connection = _connections.get(subject_id)
    if connection is None:
        return None
    return get_application(connection.application_id)


def get_application(application_id: str) -> Application | None:
    return next((a for a in _applications if a.id == application_id), None)


def all_applications() -> list[Application]:
    """Newest last, as recorded — callers group and reorder for display (docs/design.md §8)."""
    return list(_applications)


def reset_all() -> None:
    """Test-only: returns state to a fresh process's starting point."""
    _pending.clear()
    _applications.clear()
    _connections.clear()
    _by_connection_id.clear()
