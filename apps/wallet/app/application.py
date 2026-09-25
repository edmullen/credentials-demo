"""The Wallet's side of applying to a government service (docs/design.md §10). A copy of Loop
4's attempt machinery (attempt.py) — phases, a fresh token per attempt, the stale-answer guard,
outbound.spawn — adapted for Benefit Agency's shape: one identity credential plus every income
credential, and a determination instead of a connection outcome.
"""

from decimal import ROUND_HALF_UP, Decimal

from app import clock, outbound, state
from app.credentials import credentials_for
from app.display import month_span
from app.issuance import fetch
from app.providers import all_providers
from app.verify import Outcome

SERVICE_ID = "benefits"

MISSING_INCOME_MESSAGE = (
    "Application to Benefit Agency not made: you don’t have income credentials to share."
)
MISSING_IDENTITY_MESSAGE = (
    "Application to Benefit Agency not made: you don’t have an identity credential to share."
)
NO_RESPONSE_MESSAGE = "Couldn’t reach Benefit Agency to send your application"


def _service():
    return all_providers()[SERVICE_ID]


def held_identity(person_id: str):
    return next((c for c in credentials_for(person_id) if c.category == "Identity"), None)


def held_income(person_id: str) -> list:
    return [c for c in credentials_for(person_id) if c.category == "Income"]


def income_groups(income: list) -> list[dict]:
    """One panel per issuer, in first-encountered order (docs/design.md §10.4)."""
    groups: dict[str, dict] = {}
    for c in income:
        groups.setdefault(
            c.issuer_id,
            {
                "issuer_name": c.issuer_name,
                "hue": c.issuer_hue,
                "credentials": [],
                "pay_dates": [],
            },
        )
        groups[c.issuer_id]["credentials"].append(c)
        groups[c.issuer_id]["pay_dates"].append(c.subject.get("payDate"))
    result = []
    for group in groups.values():
        group["all_verified"] = all(c.outcome is Outcome.VERIFIED for c in group["credentials"])
        group["period_label"] = month_span(group["pay_dates"])
        del group["pay_dates"]
        result.append(group)
    return result


def pay_months(income: list) -> str:
    """The purpose line's "September" (handoff consent-p01.html): the income panels' month or
    span, without the year."""
    return month_span([c.subject.get("payDate") for c in income]).rsplit(" ", 1)[0]


def holds_benefit_credential(person_id: str) -> bool:
    """"Holds" counts every received BenefitCredential, whatever its verification outcome
    (docs/design.md §10.1)."""
    return any(c.category == "Benefits" for c in credentials_for(person_id))


def arrival_in_progress(person_id: str, request_id: str) -> bool:
    """True if this person's attempt is already answering this very request, so a reload of the
    arrival URL returns to it instead of starting over (docs/design.md §16 item 8)."""
    link = state.get_link(person_id, SERVICE_ID)
    return link is not None and link.request is not None and link.request.request_id == request_id


def where_is_the_attempt(person_id: str) -> str:
    link = state.get_link(person_id, SERVICE_ID)
    if link is None or link.request is None:
        return f"/p/{person_id}/services"
    phase = link.request.phase
    if phase in ("consent", "missing"):
        return f"/p/{person_id}/services/{SERVICE_ID}/request"
    return f"/p/{person_id}/services/{SERVICE_ID}/{phase}"


def _still_current(person_id: str, token: str) -> state.Link | None:
    link = state.get_link(person_id, SERVICE_ID)
    if link is None or link.request is None or link.request.token != token:
        return None
    return link


def start_apply(person_id: str, request_id: str | None = None) -> None:
    """GET …/apply: a fresh token, phase asking, call 1 spawned. With `request_id` — an arrival
    from Benefit Agency (docs/design.md §12) — call 1 fetches that request by reference."""
    link = state.get_or_create_link(person_id, SERVICE_ID)
    token = state.new_token()
    link.request = state.PendingRequest(
        token=token, phase="asking", request_id=request_id, arrived=request_id is not None
    )
    outbound.spawn(run_call_one(person_id, token))


async def run_call_one(person_id: str, token: str) -> None:
    service = _service()
    link = _still_current(person_id, token)
    if link is None:
        return
    request_id = link.request.request_id
    try:
        # Always the registry's URL: the arrival URL supplies only a validated id, so nothing a
        # browser carries can steer this call elsewhere (docs/design.md §12.2).
        if request_id is None:
            response = await outbound.post_json(f"{service['url']}/api/applications/requests", {})
            expected = 201
        else:
            response = await outbound.get_json(
                f"{service['url']}/api/applications/requests/{request_id}"
            )
            expected = 200
        if response.status_code != expected:
            raise ValueError(f"unexpected status {response.status_code}")
        body = response.json()
        dcql_query = body["dcql_query"]
        resolved_uri = outbound.resolve(service["url"], body["response_uri"])
        if resolved_uri is None:
            raise ValueError("response_uri resolved off the service's origin")
    except Exception:
        _end_call_one_as_no_response(person_id, token)
        return

    link = _still_current(person_id, token)
    if link is None:
        return
    link.request.dcql_query = dcql_query
    link.request.response_uri = resolved_uri
    _advance_from_asking(person_id, link)


def _advance_from_asking(person_id: str, link: state.Link) -> None:
    """Identity leads: with neither held, the identity page shows, not the income one
    (docs/design.md §10.3, handoff Part B §5)."""
    if held_identity(person_id) is None:
        link.request.phase = "missing"
        link.request.missing = "identity"
        state.log(person_id, "caution", MISSING_IDENTITY_MESSAGE, clock.now())
    elif not held_income(person_id):
        link.request.phase = "missing"
        link.request.missing = "income"
        state.log(person_id, "caution", MISSING_INCOME_MESSAGE, clock.now())
    else:
        link.request.phase = "consent"


def _end_call_one_as_no_response(person_id: str, token: str) -> None:
    link = _still_current(person_id, token)
    if link is None:
        return
    link.request.phase = "error"
    state.log(person_id, "caution", NO_RESPONSE_MESSAGE, clock.now())


def deny(person_id: str) -> None:
    link = state.get_link(person_id, SERVICE_ID)
    if link is None or link.request is None or link.request.phase != "consent":
        return
    link.request = None
    state.log(person_id, "neutral", "Request from Benefit Agency denied. Nothing was shared.", clock.now())


def close(person_id: str) -> None:
    """Closing a can't-apply page is silent (docs/design.md §10.3)."""
    link = state.get_link(person_id, SERVICE_ID)
    if link is None or link.request is None or link.request.phase != "missing":
        return
    link.request = None


def _build_presentation(identity_token: str, income_tokens: list[str]) -> dict:
    tokens = [identity_token, *income_tokens]
    return {
        "@context": ["https://www.w3.org/ns/credentials/v2"],
        "type": ["VerifiablePresentation"],
        "verifiableCredential": [
            {
                "@context": "https://www.w3.org/ns/credentials/v2",
                "type": "EnvelopedVerifiableCredential",
                "id": f"data:application/vc+jwt,{token}",
            }
            for token in tokens
        ],
    }


def approve(person_id: str) -> None:
    """Approve and share: builds the VP (identity, then income in held order), phase applying,
    logged, call 2 spawned (docs/design.md §10.4)."""
    link = state.get_link(person_id, SERVICE_ID)
    if link is None or link.request is None or link.request.phase != "consent":
        return
    identity = held_identity(person_id)
    income = held_income(person_id)
    presentation = _build_presentation(identity.token, [c.token for c in income])
    link.presentation = presentation
    link.request.phase = "applying"
    n = len(income)
    state.log(
        person_id, "neutral",
        f"Application sent to Benefit Agency: identity credential and {n} income credential{'' if n == 1 else 's'} shared",
        clock.now(),
    )
    outbound.spawn(run_call_two(person_id, link.request.token))


def _program_outcome_message(entry: dict) -> tuple[str, str]:
    """(dot, message) for one program's Activity entry (docs/design.md §10.9)."""
    name = _PROGRAM_NAMES.get(entry["program"], entry["program"])
    if entry["outcome"] == "denied":
        if entry["reason"] == "not_nj_resident":
            return "neutral", f"{name}: not eligible. This program is for New Jersey residents."
        return "neutral", f"{name}: not eligible. Your income is above this program’s limit."
    if entry["program"] == "dividend":
        payment = _money(entry["monthlyPayment"])
        return "verified", f"{name}: eligible, {payment} a month"
    if entry["program"] == "health":
        discount = entry["discountPercent"]
        if discount == 0:
            price = _money(entry["planCost"])
            return "neutral", f"{name}: full price, 0% off: {price} a month"
        price = _health_price(entry)
        return "verified", f"{name}: eligible, {_pct(discount)}% off: {price} a month"
    return "verified", f"{name}: eligible"


_PROGRAM_NAMES = {
    "food": "Food Assistance", "energy": "Energy Assistance", "housing": "Housing Assistance",
    "health": "Health", "dividend": "Dividend",
}


def _pct(value) -> str:
    text = f"{Decimal(str(value)):.1f}"
    return text[:-2] if text.endswith(".0") else text


def _money(amount: dict) -> str:
    return f"${Decimal(str(amount['value'])):,.2f}"


def _health_price(entry: dict) -> str:
    cost = Decimal(str(entry["planCost"]["value"]))
    discount = Decimal(str(entry["discountPercent"]))
    price = (cost * (100 - discount) / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return _money({"value": price})


async def run_call_two(person_id: str, token: str) -> None:
    link = _still_current(person_id, token)
    if link is None:
        return
    try:
        response = await outbound.post_json(link.request.response_uri, link.presentation)
        status = response.status_code
        if status == 404:
            outcome = "unknown_request"
        elif status != 200:
            raise ValueError(f"unexpected status {status}")
        else:
            body = response.json()
            outcome = body["outcome"]
            if outcome == "refused" and body["reason"] not in ("credential_invalid", "subjects_differ"):
                raise ValueError(f"unknown reason {body['reason']!r}")
            if outcome not in ("decided", "refused"):
                raise ValueError(f"unknown outcome {outcome!r}")
    except Exception:
        outcome, body = "no_response", None

    link = _still_current(person_id, token)
    if link is None:
        return

    if outcome == "unknown_request":
        # Benefits no longer knows the request (restarted, or 15 minutes passed) — start over,
        # so the person consents again (docs/design.md §10.6).
        link.presentation = None
        start_apply(person_id)
        return

    if outcome == "no_response":
        link.request.phase = "error"
        state.log(person_id, "caution", NO_RESPONSE_MESSAGE, clock.now())
        return

    link.request = None
    link.presentation = None
    now = clock.now()
    if outcome == "decided":
        link.determination = body
        link.refusal = None
        link.connected_at = now
        link.connection_id = body["connectionId"]
        state.log(person_id, "verified", "New connection to Benefit Agency established", now)
        for entry in body["programs"]:
            dot, message = _program_outcome_message(entry)
            state.log(person_id, dot, message, now)
        # The applying page is still polling, so credentials are usually in hand by the time
        # results renders (docs/design.md §10.6, following Payroll's connect, Loop 5 design §9).
        await fetch(person_id, SERVICE_ID)
    else:
        reason = body["reason"]
        link.refusal = reason
        if reason == "credential_invalid":
            sentence = "1 credential couldn’t be verified"
        else:
            sentence = "the credentials you shared aren’t all about the same person"
        state.log(
            person_id, "error", f"Your application couldn’t be decided: {sentence}", now
        )


def retry(person_id: str) -> None:
    """Try again: re-sends the kept presentation if there is one, else starts over at call 1
    (docs/design.md §10.6)."""
    link = state.get_link(person_id, SERVICE_ID)
    if link is None or link.request is None or link.request.phase != "error":
        return
    if link.presentation is not None:
        link.request.phase = "applying"
        outbound.spawn(run_call_two(person_id, link.request.token))
    else:
        start_apply(person_id)
