"""Payroll's runtime state for the connection protocol (docs/design.md §7).

In-memory, per process, volatile — same decision as the Wallet's (docs/decisions.md). One
process serves every request (render.yaml, one worker), so no lock is needed here.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import uuid4

PENDING_TTL = timedelta(minutes=15)


@dataclass
class PendingRequest:
    employers: list[str]
    created_at: datetime


@dataclass
class Connection:
    connected_at: datetime
    issuer_name: str
    connection_id: str


@dataclass
class Event:
    at: datetime
    dot: str
    message: str


_pending: dict[str, PendingRequest] = {}
_connections: dict[str, Connection] = {}
_by_connection_id: dict[str, str] = {}  # connection id -> person id (docs/design.md §5)
_events: dict[str, list[Event]] = {}


def _prune_stale(now: datetime) -> None:
    stale = [rid for rid, r in _pending.items() if now - r.created_at > PENDING_TTL]
    for rid in stale:
        del _pending[rid]


def create_request(employers: list[str], now: datetime) -> str:
    """Records a pending request and returns its id. Bounds memory by pruning old ones."""
    _prune_stale(now)
    request_id = uuid4().hex
    _pending[request_id] = PendingRequest(employers=list(employers), created_at=now)
    return request_id


def pop_request(request_id: str, now: datetime) -> PendingRequest | None:
    """One-shot: answering it removes it. None if unknown, already answered, or expired."""
    request = _pending.pop(request_id, None)
    if request is None or now - request.created_at > PENDING_TTL:
        return None
    return request


def get_connection(person_id: str) -> Connection | None:
    return _connections.get(person_id)


def connect(person_id: str, issuer_name: str, now: datetime) -> str:
    """Connecting again overwrites the record and issues a fresh connection id; the old one
    stops resolving (docs/design.md §2, §5). Returns the new id."""
    old = _connections.get(person_id)
    if old is not None:
        _by_connection_id.pop(old.connection_id, None)
    connection_id = uuid4().hex
    _connections[person_id] = Connection(
        connected_at=now, issuer_name=issuer_name, connection_id=connection_id
    )
    _by_connection_id[connection_id] = person_id
    return connection_id


def person_for_connection(connection_id: str) -> str | None:
    return _by_connection_id.get(connection_id)


def events_for(person_id: str) -> list[Event]:
    return _events.get(person_id, [])


def log(person_id: str, dot: str, message: str, at: datetime) -> None:
    _events.setdefault(person_id, []).append(Event(at=at, dot=dot, message=message))


def reset_all() -> None:
    """Test-only: returns every person's state to a fresh process's starting point."""
    _pending.clear()
    _connections.clear()
    _by_connection_id.clear()
    _events.clear()
