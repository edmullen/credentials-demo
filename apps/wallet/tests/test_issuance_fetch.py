"""fetch() (docs/design.md §9): the have list, counts, logging, the stale-answer guard, a lost
connection, and repeated errors logging once."""

import asyncio
import json

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from jwt.algorithms import ECAlgorithm

from app import clock, credentials, outbound, state
from app.issuance import fetch

ISSUER_ID = "https://cred-demo-payroll.onrender.com"
PERSON_ID = "p01"
PROVIDER_ID = "meridian"


class FakeResponse:
    def __init__(self, status_code: int, body: dict | None = None, raw: bytes | None = None):
        self.status_code = status_code
        self._body = body
        self._raw = raw

    def json(self):
        if self._raw is not None:
            return json.loads(self._raw)
        return self._body


def _payroll_key() -> tuple[object, dict]:
    key = ec.generate_private_key(ec.SECP256R1())
    public = json.loads(ECAlgorithm.to_jwk(key.public_key()))
    public["kid"] = "payroll-1"
    return key, public


@pytest.fixture
def payroll_trust(monkeypatch):
    key, public = _payroll_key()
    stored, _ = credentials._committed()
    trust = {ISSUER_ID: {"name": "Meridian Payroll", "trustedFor": ["PaystubCredential"], "keys": [public]}}
    monkeypatch.setattr(credentials, "_committed", lambda: (stored, trust))
    return key


def _token(key, credential_id: str, *, kid="payroll-1", tamper=False) -> str:
    payload = {
        "@context": ["https://www.w3.org/ns/credentials/v2"],
        "id": credential_id,
        "type": ["VerifiableCredential", "PaystubCredential"],
        "issuer": {"id": ISSUER_ID, "name": "Meridian Payroll"},
        "validFrom": "2026-09-15T00:00:00Z",
        "credentialSubject": {
            "id": "urn:uuid:33333333-3333-5333-8333-333333333333",
            "employer": {"type": "Organization", "name": "Pinecrest Home Care"},
            "payPeriodStart": "2026-09-01", "payPeriodEnd": "2026-09-15", "payDate": "2026-09-15",
            "payFrequency": "semimonthly",
            "grossPay": {"type": "MonetaryAmount", "value": 1100.0, "currency": "USD"},
            "netPay": {"type": "MonetaryAmount", "value": 955.87, "currency": "USD"},
        },
    }
    token = jwt.encode(payload, key, algorithm="ES256", headers={"kid": kid, "typ": "vc+jwt"})
    if tamper:
        header, body, sig = token.split(".")
        claims = json.loads(jwt.utils.base64url_decode(body + "=" * (-len(body) % 4)))
        claims["credentialSubject"]["grossPay"]["value"] = 1.0
        body = jwt.utils.base64url_encode(json.dumps(claims, separators=(",", ":")).encode()).decode()
        token = ".".join([header, body, sig])
    return token


@pytest.fixture
def connected_link():
    link = state.add_employer(PERSON_ID, PROVIDER_ID, "pinecrest")
    link.connected_at = clock.now()
    link.connection_id = "conn-1"
    return link


def test_no_connection_id_does_nothing(monkeypatch) -> None:
    state.add_employer(PERSON_ID, PROVIDER_ID, "pinecrest")  # never connected

    async def unexpected(*a, **k):
        raise AssertionError("should not call out with no connection_id")

    monkeypatch.setattr(outbound, "post_json", unexpected)
    asyncio.run(fetch(PERSON_ID, PROVIDER_ID))
    assert state.get_check(PERSON_ID, PROVIDER_ID) is None


def test_sends_the_held_ids_as_have(connected_link, payroll_trust, monkeypatch) -> None:
    state.add_received(PERSON_ID, "urn:uuid:already-held", "some-jwt")
    seen = {}

    async def fake_post_json(url, payload):
        seen["url"], seen["payload"] = url, payload
        return FakeResponse(200, {"credentials": []})

    monkeypatch.setattr(outbound, "post_json", fake_post_json)
    asyncio.run(fetch(PERSON_ID, PROVIDER_ID))
    assert seen["payload"] == {"connectionId": "conn-1", "have": ["urn:uuid:already-held"]}
    assert seen["url"].endswith("/api/credentials")


def test_stores_new_credentials_and_counts_and_logs_verified(connected_link, payroll_trust, monkeypatch) -> None:
    tokens = [_token(payroll_trust, f"urn:uuid:income-{i}") for i in range(2)]

    async def fake_post_json(url, payload):
        return FakeResponse(200, {"credentials": tokens})

    monkeypatch.setattr(outbound, "post_json", fake_post_json)
    asyncio.run(fetch(PERSON_ID, PROVIDER_ID))

    received = state.received_for(PERSON_ID)
    assert set(received) == {"urn:uuid:income-0", "urn:uuid:income-1"}
    check = state.get_check(PERSON_ID, PROVIDER_ID)
    assert check.state == "done" and check.result == "new" and check.count == 2
    events = [e.message for e in state.events_for(PERSON_ID)]
    assert "2 income credentials received from Meridian Payroll" in events


def test_empty_response_finishes_as_none_and_logs_nothing(connected_link, payroll_trust, monkeypatch) -> None:
    async def fake_post_json(url, payload):
        return FakeResponse(200, {"credentials": []})

    monkeypatch.setattr(outbound, "post_json", fake_post_json)
    asyncio.run(fetch(PERSON_ID, PROVIDER_ID))
    check = state.get_check(PERSON_ID, PROVIDER_ID)
    assert check.result == "none" and check.count == 0
    assert state.events_for(PERSON_ID) == []


def test_a_tampered_credential_is_kept_and_logged_as_couldnt_be_verified(
    connected_link, payroll_trust, monkeypatch
) -> None:
    token = _token(payroll_trust, "urn:uuid:bad-1", tamper=True)

    async def fake_post_json(url, payload):
        return FakeResponse(200, {"credentials": [token]})

    monkeypatch.setattr(outbound, "post_json", fake_post_json)
    asyncio.run(fetch(PERSON_ID, PROVIDER_ID))
    assert "urn:uuid:bad-1" in state.received_for(PERSON_ID)  # kept, not dropped
    events = [e.message for e in state.events_for(PERSON_ID)]
    assert "1 income credential from Meridian Payroll couldn't be verified" in events
    assert not any("received from" in m for m in events)


def test_unknown_connection_clears_it_and_keeps_employers(connected_link, monkeypatch) -> None:
    async def fake_post_json(url, payload):
        return FakeResponse(404, {"error": "unknown_connection"})

    monkeypatch.setattr(outbound, "post_json", fake_post_json)
    asyncio.run(fetch(PERSON_ID, PROVIDER_ID))
    link = state.get_link(PERSON_ID, PROVIDER_ID)
    assert link.connected_at is None
    assert link.connection_id is None
    assert link.employers == ["pinecrest"]
    assert state.get_check(PERSON_ID, PROVIDER_ID).result == "lost"
    assert state.events_for(PERSON_ID) == []  # a lost connection logs nothing (§9)


def test_a_failure_logs_once_across_repeats(connected_link, monkeypatch) -> None:
    async def failing(url, payload):
        raise TimeoutError("no response")

    monkeypatch.setattr(outbound, "post_json", failing)
    asyncio.run(fetch(PERSON_ID, PROVIDER_ID))
    asyncio.run(fetch(PERSON_ID, PROVIDER_ID))
    events = [e.message for e in state.events_for(PERSON_ID)]
    assert events.count("Couldn't reach Meridian Payroll to check for new credentials") == 1
    assert state.get_check(PERSON_ID, PROVIDER_ID).result == "error"


def test_a_stale_answer_is_dropped(connected_link, monkeypatch) -> None:
    async def fake_post_json(url, payload):
        # Simulate a newer check starting and finishing while this one is still "in flight".
        state.set_check(PERSON_ID, PROVIDER_ID, state.Check(state="checking", token="superseding"))
        return FakeResponse(200, {"credentials": []})

    monkeypatch.setattr(outbound, "post_json", fake_post_json)
    asyncio.run(fetch(PERSON_ID, PROVIDER_ID))
    # The stale write didn't happen: the check is still the superseding one, still "checking".
    check = state.get_check(PERSON_ID, PROVIDER_ID)
    assert check.token == "superseding" and check.state == "checking"
