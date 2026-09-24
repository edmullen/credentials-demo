"""fetch() wording for a service (Benefit Agency), and a lost service connection removing the
link outright (docs/design.md §10.8)."""

import asyncio
import json

import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from jwt.algorithms import ECAlgorithm

from app import clock, credentials, outbound, state
from app.issuance import fetch

ISSUER_ID = "https://cred-demo-benefits.onrender.com"
PERSON_ID = "p01"
PROVIDER_ID = "benefits"


class FakeResponse:
    def __init__(self, status_code: int, body: dict | None = None):
        self.status_code = status_code
        self._body = body

    def json(self):
        return self._body


def _benefits_key() -> tuple[object, dict]:
    key = ec.generate_private_key(ec.SECP256R1())
    public = json.loads(ECAlgorithm.to_jwk(key.public_key()))
    public["kid"] = "benefits-1"
    return key, public


def _benefits_trust(monkeypatch):
    key, public = _benefits_key()
    stored, _ = credentials._committed()
    trust = {ISSUER_ID: {"name": "Benefit Agency", "trustedFor": ["BenefitCredential"], "keys": [public]}}
    monkeypatch.setattr(credentials, "_committed", lambda: (stored, trust))
    return key


def _token(key, credential_id: str) -> str:
    payload = {
        "@context": ["https://www.w3.org/ns/credentials/v2"],
        "id": credential_id,
        "type": ["VerifiableCredential", "BenefitCredential"],
        "issuer": {"id": ISSUER_ID, "name": "Benefit Agency"},
        "validFrom": "2026-09-01T00:00:00Z",
        "validUntil": "2027-09-01T00:00:00Z",
        "credentialSubject": {"id": "urn:uuid:33333333-3333-5333-8333-333333333333", "program": "food"},
    }
    return jwt.encode(payload, key, algorithm="ES256", headers={"kid": "benefits-1", "typ": "vc+jwt"})


def _connected_link() -> state.Link:
    link = state.get_or_create_link(PERSON_ID, PROVIDER_ID)
    link.connected_at = clock.now()
    link.connection_id = "conn-1"
    return link


def test_received_message_says_benefit_not_income(monkeypatch) -> None:
    link = _connected_link()
    key = _benefits_trust(monkeypatch)
    token = _token(key, "urn:uuid:benefit-1")

    async def fake_post_json(url, payload):
        return FakeResponse(200, {"credentials": [token]})

    monkeypatch.setattr(outbound, "post_json", fake_post_json)
    asyncio.run(fetch(PERSON_ID, PROVIDER_ID))
    events = [e.message for e in state.events_for(PERSON_ID)]
    assert "1 benefit credential received from Benefit Agency" in events
    assert link.connection_id == "conn-1"  # unaffected


def test_announcement_says_new_benefit_credentials(monkeypatch) -> None:
    from app.issuance import check_status

    _connected_link()
    key = _benefits_trust(monkeypatch)
    token = _token(key, "urn:uuid:benefit-2")

    async def fake_post_json(url, payload):
        return FakeResponse(200, {"credentials": [token]})

    monkeypatch.setattr(outbound, "post_json", fake_post_json)
    asyncio.run(fetch(PERSON_ID, PROVIDER_ID))
    status = check_status(PERSON_ID)
    assert status["announce"] == "1 new benefit credential from Benefit Agency."


def test_lost_removes_the_link_but_keeps_held_credentials(monkeypatch) -> None:
    link = _connected_link()
    key = _benefits_trust(monkeypatch)
    state.add_received(PERSON_ID, "urn:uuid:already-held", _token(key, "urn:uuid:already-held"))

    async def fake_post_json(url, payload):
        return FakeResponse(404)

    monkeypatch.setattr(outbound, "post_json", fake_post_json)
    asyncio.run(fetch(PERSON_ID, PROVIDER_ID))
    assert state.get_link(PERSON_ID, PROVIDER_ID) is None
    assert "urn:uuid:already-held" in state.received_for(PERSON_ID)
