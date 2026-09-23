"""Fetching income credentials from a connected provider (docs/design.md §9).

One function does the work for both moments call 3 can happen: right after connecting
(attempt.py) and whenever the Credentials page opens (PR 5). It uses the same stale-answer
guard as call 1 and call 2: a background task writes its result only if the check it started
with is still the current one for that person and provider.
"""

from app import clock, outbound, state
from app.credentials import trust_list
from app.providers import all_providers
from app.verify import Outcome, verify

RECEIVED_MESSAGE = "{count} income credential{plural} received from {provider}"
UNVERIFIED_MESSAGE = "{count} income credential{plural} from {provider} couldn't be verified"
UNREACHABLE_MESSAGE = "Couldn't reach {provider} to check for new credentials"


def _plural(count: int) -> str:
    return "" if count == 1 else "s"


def _still_current(person_id: str, provider_id: str, token: str) -> state.Check | None:
    check = state.get_check(person_id, provider_id)
    if check is None or check.token != token:
        return None
    return check


async def fetch(person_id: str, provider_id: str) -> None:
    link = state.get_link(person_id, provider_id)
    if link is None or link.connection_id is None:
        return
    provider = all_providers()[provider_id]
    previous = state.get_check(person_id, provider_id)
    previous_was_error = previous is not None and previous.result == "error"
    token = state.new_token()
    now = clock.now()
    state.set_check(person_id, provider_id, state.Check(state="checking", token=token))

    have = list(state.received_for(person_id).keys())
    try:
        response = await outbound.post_json(
            f"{provider['url']}/api/credentials",
            {"connectionId": link.connection_id, "have": have},
        )
        if response.status_code == 404:
            outcome = "lost"
        elif response.status_code != 200:
            raise ValueError(f"unexpected status {response.status_code}")
        else:
            outcome = "fetched"
            credentials = response.json()["credentials"]
    except Exception:
        outcome = "error"

    if not _still_current(person_id, provider_id, token):
        return

    if outcome == "lost":
        link.connected_at = None
        link.connection_id = None
        state.set_check(
            person_id, provider_id,
            state.Check(state="done", token=token, result="lost", finished_at=now),
        )
        return

    if outcome == "error":
        state.set_check(
            person_id, provider_id,
            state.Check(state="done", token=token, result="error", finished_at=now),
        )
        if not previous_was_error:
            state.log(
                person_id, "caution",
                UNREACHABLE_MESSAGE.format(provider=provider["name"]), now,
            )
        return

    trust = trust_list()
    verified_ids, tampered_count = [], 0
    for token_str in credentials:
        result = verify(token_str, trust, now)
        claims = result.claims or {}
        credential_id = claims.get("id", "")
        state.add_received(person_id, credential_id, token_str)
        if result.outcome is Outcome.VERIFIED:
            verified_ids.append(credential_id)
        else:
            tampered_count += 1

    count = len(credentials)
    state.set_check(
        person_id, provider_id,
        state.Check(
            state="done", token=token, result="new" if count else "none",
            count=count, finished_at=now,
        ),
    )
    if verified_ids:
        state.log(
            person_id, "verified",
            RECEIVED_MESSAGE.format(
                count=len(verified_ids), plural=_plural(len(verified_ids)),
                provider=provider["name"],
            ),
            now,
        )
    if tampered_count:
        state.log(
            person_id, "error",
            UNVERIFIED_MESSAGE.format(
                count=tampered_count, plural=_plural(tampered_count), provider=provider["name"],
            ),
            now,
        )
