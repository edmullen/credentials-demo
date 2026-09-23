"""Per-person, in-memory, volatile runtime state (docs/design.md §2, §4).

Lost whenever this process restarts — no database, nothing on disk, by decision
(docs/decisions.md). One process serves every request, so every change here happens inside a
single event loop with no `await` between reading and writing a record; the one place work
spans an `await` is the outbound call to Payroll, guarded by `Request.token` rather than a lock
(docs/design.md §5).
"""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass
class PendingRequest:
    """An attempt toward one provider, in progress.

    `token` is fresh per attempt. A background task writes its result only if this still
    matches the token it was given — the invariant that makes a stale answer harmless.
    """

    token: str
    phase: str  # "asking" | "consent" | "missing" | "verifying"
    dcql_query: dict | None = None
    response_uri: str | None = None


@dataclass
class Link:
    """One connection to one payroll provider."""

    employers: list[str] = field(default_factory=list)
    connected_at: datetime | None = None
    outcome: str | None = None  # "credential_invalid" | "not_an_employee" | "no_response"
    shared_credential_id: str | None = None
    request: PendingRequest | None = None
    connection_id: str | None = None  # docs/design.md §2, §7
    arrived: int | None = None  # count the first fetch brought; shown once on Connections


@dataclass
class Check:
    """The latest background fetch for one person and provider (docs/design.md §7, §9)."""

    state: str  # "checking" | "done"
    token: str
    result: str | None = None  # "none" | "new" | "error" | "lost"
    count: int = 0
    finished_at: datetime | None = None


@dataclass
class Event:
    at: datetime
    dot: str  # "neutral" | "verified" | "caution" | "error"
    message: str


_links: dict[str, dict[str, Link]] = {}
# Per person: credential id -> JWT, in the order they arrived (docs/design.md §7).
_received: dict[str, dict[str, str]] = {}
# Per person: credential ids that have been rendered at least once (the New pill, §8).
_seen: dict[str, set[str]] = {}
# Per (person, provider): the latest background check.
_checks: dict[tuple[str, str], Check] = {}
_events: dict[str, list[Event]] = {}


def new_token() -> str:
    return uuid4().hex


def get_link(person_id: str, provider_id: str) -> Link | None:
    return _links.get(person_id, {}).get(provider_id)


def add_employer(person_id: str, provider_id: str, employer_id: str) -> Link:
    """Adds the employer, creating the link on first touch. A repeat add changes nothing."""
    link = _links.setdefault(person_id, {}).setdefault(provider_id, Link())
    if employer_id not in link.employers:
        link.employers.append(employer_id)
    return link


def remove_link(person_id: str, provider_id: str) -> Link | None:
    """Deletes the link and its check. Keeps received credentials — they're still valid and
    signed, and the person holds them (docs/design.md §7, §13 item 6). Returns what was
    removed, or None."""
    _checks.pop((person_id, provider_id), None)
    return _links.get(person_id, {}).pop(provider_id, None)


def received_for(person_id: str) -> dict[str, str]:
    return _received.get(person_id, {})


def add_received(person_id: str, credential_id: str, token: str) -> None:
    _received.setdefault(person_id, {})[credential_id] = token


def seen_for(person_id: str) -> set[str]:
    return _seen.get(person_id, set())


def mark_seen(person_id: str, credential_ids) -> None:
    _seen.setdefault(person_id, set()).update(credential_ids)


def get_check(person_id: str, provider_id: str) -> Check | None:
    return _checks.get((person_id, provider_id))


def set_check(person_id: str, provider_id: str, check: Check) -> None:
    _checks[(person_id, provider_id)] = check


def events_for(person_id: str) -> list[Event]:
    return _events.get(person_id, [])


def log(person_id: str, dot: str, message: str, at: datetime) -> None:
    _events.setdefault(person_id, []).append(Event(at=at, dot=dot, message=message))


def reset_all() -> None:
    """Test-only: returns every person's state to a fresh process's starting point."""
    _links.clear()
    _received.clear()
    _seen.clear()
    _checks.clear()
    _events.clear()
