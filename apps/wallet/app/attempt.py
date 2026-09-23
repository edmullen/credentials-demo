"""The Wallet's side of a connection attempt (docs/design.md §5): call 1 here, call 2 in the
next PR. An attempt moves through phases, each with its own page. A token makes a stale
answer harmless — a task writes its result only if the link's request still has that token, so
an answer arriving after Try again, Remove or Disconnect is dropped.
"""

from app import clock, outbound, state
from app.credentials import CATEGORIES, credentials_for
from app.display import join_and
from app.providers import all_providers, get_employer

MISSING_MESSAGE = "Connection to Meridian Payroll not made: you don’t have an Identity credential to share."
NO_RESPONSE_MESSAGE = "Connection to Meridian Payroll not made: Meridian Payroll didn’t respond."

# Where each phase's own page lives. "consent" and "missing" share one page (docs/design.md §5).
PHASE_PATH = {
    "asking": "asking",
    "consent": "request",
    "missing": "request",
    "verifying": "verifying",
}


def request_type(entry: dict) -> str | None:
    """The one credential type a DCQL-shaped entry names, or None if it names none."""
    values = (entry.get("meta") or {}).get("type_values") or []
    return values[0][0] if values and values[0] else None


def request_label(credential_type: str) -> str:
    """'Identity credential' from 'IdentityCredential'."""
    return f"{CATEGORIES.get(credential_type, credential_type)} credential"


def matching_credential(person_id: str, credential_type: str):
    """A held credential of this type, offered whatever its own badge says (docs/design.md §5)."""
    return next(
        (c for c in credentials_for(person_id) if credential_type in c.claims.get("type", [])),
        None,
    )


def phase_url(person_id: str, provider_id: str, phase: str) -> str:
    return f"/p/{person_id}/connections/{provider_id}/{PHASE_PATH[phase]}"


def where_is_the_attempt(person_id: str, provider_id: str) -> str:
    """Wherever this attempt actually is right now, for a page or the status endpoint to
    redirect to."""
    link = state.get_link(person_id, provider_id)
    if link is None or link.request is None:
        return f"/p/{person_id}/connections"
    return phase_url(person_id, provider_id, link.request.phase)


def purpose_line(provider_name: str, employer_ids: list[str]) -> str:
    names = sorted(get_employer(e)["name"] for e in employer_ids)
    return (
        f"It runs payroll for {join_and(names)}, and needs to check who you are before it "
        "links your wallet to your employee record."
    )


def start_connect(person_id: str, provider_id: str) -> None:
    """Connect payroll / Try again: a fresh token, phase asking, logged, call spawned."""
    link = state.get_link(person_id, provider_id)
    provider = all_providers()[provider_id]
    token = state.new_token()
    link.request = state.PendingRequest(token=token, phase="asking")
    link.outcome = None
    state.log(person_id, "neutral", f"Connection to {provider['name']} requested", clock.now())
    outbound.spawn(run_call_one(person_id, provider_id, token))


def _still_current(person_id: str, provider_id: str, token: str) -> state.Link | None:
    link = state.get_link(person_id, provider_id)
    if link is None or link.request is None or link.request.token != token:
        return None
    return link


def _end_as_no_response(person_id: str, provider_id: str, token: str) -> None:
    link = _still_current(person_id, provider_id, token)
    if link is None:
        return
    link.request = None
    link.outcome = "no_response"
    state.log(person_id, "caution", NO_RESPONSE_MESSAGE, clock.now())


async def run_call_one(person_id: str, provider_id: str, token: str) -> None:
    provider = all_providers()[provider_id]
    link = _still_current(person_id, provider_id, token)
    if link is None:
        return
    try:
        response = await outbound.post_json(
            f"{provider['url']}/api/connections/requests", {"employers": link.employers}
        )
        if response.status_code != 201:
            raise ValueError(f"unexpected status {response.status_code}")
        body = response.json()
        dcql_query = body["dcql_query"]
        resolved_uri = outbound.resolve(provider["url"], body["response_uri"])
        if resolved_uri is None:
            raise ValueError("response_uri resolved off the provider's origin")
    except Exception:
        _end_as_no_response(person_id, provider_id, token)
        return

    link = _still_current(person_id, provider_id, token)
    if link is None:
        return
    link.request.dcql_query = dcql_query
    link.request.response_uri = resolved_uri
    entries = dcql_query.get("credentials", [])
    missing = any(matching_credential(person_id, request_type(e)) is None for e in entries)
    if missing:
        link.request.phase = "missing"
        state.log(person_id, "caution", MISSING_MESSAGE, clock.now())
    else:
        link.request.phase = "consent"


def deny(person_id: str, provider_id: str) -> None:
    link = state.get_link(person_id, provider_id)
    if link is None or link.request is None or link.request.phase != "consent":
        return
    provider = all_providers()[provider_id]
    link.request = None
    state.log(
        person_id, "neutral", f"Request from {provider['name']} denied. Nothing was shared.", clock.now()
    )


def close(person_id: str, provider_id: str) -> None:
    """Closing a missing-credential request is silent (docs/design.md §5)."""
    link = state.get_link(person_id, provider_id)
    if link is None or link.request is None or link.request.phase != "missing":
        return
    link.request = None
