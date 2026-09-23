"""End-to-end tests for the connection protocol's two calls (docs/design.md §3, §7).

Tests mint throwaway ES256 keys and a signed identity credential at test time; nothing here
reads the Wallet's committed files (docs/design.md §10).
"""

import base64
import json
from datetime import UTC, datetime, timedelta

import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from jwt.algorithms import ECAlgorithm

from app import connections
from app.main import app

client = TestClient(app)

ISSUER_ID = "did:example:test-state"
ISSUER_NAME = "State of Testland"
KID = "test-1"
GRACE_SUBJECT = "urn:uuid:031acde8-d4c0-5778-b6ab-84a4b612af70"  # p01, Pinecrest


def _key_and_trust() -> tuple[object, dict]:
    key = ec.generate_private_key(ec.SECP256R1())
    public = json.loads(ECAlgorithm.to_jwk(key.public_key()))
    public["kid"] = KID
    trust = {
        ISSUER_ID: {"name": ISSUER_NAME, "trustedFor": ["IdentityCredential"], "keys": [public]}
    }
    return key, trust


def _token(key, subject_id: str = GRACE_SUBJECT) -> str:
    payload = {
        "@context": ["https://www.w3.org/ns/credentials/v2"],
        "id": "urn:uuid:11111111-1111-1111-1111-111111111111",
        "type": ["VerifiableCredential", "IdentityCredential"],
        "issuer": {"id": ISSUER_ID, "name": ISSUER_NAME},
        "validFrom": "2026-01-01T00:00:00Z",
        "validUntil": "2030-01-01T00:00:00Z",
        "credentialSubject": {"id": subject_id},
    }
    return jwt.encode(payload, key, algorithm="ES256", headers={"kid": KID, "typ": "vc+jwt"})


def _vp(*tokens: str) -> dict:
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


def _patch_trust(monkeypatch, trust: dict) -> None:
    monkeypatch.setattr("app.main.trust_list", lambda: trust)


def test_call_one_returns_dcql_shaped_request() -> None:
    response = client.post("/api/connections/requests", json={"employers": ["pinecrest"]})
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"requestId", "dcql_query", "response_uri"}
    assert body["dcql_query"] == {
        "credentials": [
            {"id": "identity", "format": "vc+jwt", "meta": {"type_values": [["IdentityCredential"]]}}
        ]
    }
    assert "claims" not in json.dumps(body["dcql_query"])
    assert body["response_uri"] == f"/api/connections/requests/{body['requestId']}/presentation"
    assert body["response_uri"].startswith("/")  # path-only, never absolute


def test_call_one_rejects_missing_empty_or_unknown_employers() -> None:
    assert client.post("/api/connections/requests", json={}).status_code == 400
    assert client.post("/api/connections/requests", json={"employers": []}).status_code == 400
    r = client.post("/api/connections/requests", json={"employers": ["not-a-real-employer"]})
    assert r.status_code == 400
    assert r.json() == {"error": "invalid_request"}


def test_call_two_valid_at_the_right_employer_connects(monkeypatch) -> None:
    key, trust = _key_and_trust()
    _patch_trust(monkeypatch, trust)
    create = client.post("/api/connections/requests", json={"employers": ["pinecrest"]}).json()
    response = client.post(create["response_uri"], json=_vp(_token(key)))
    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "connected"
    connection = connections.get_connection("p01")
    assert connection is not None
    assert body["connectionId"] == connection.connection_id
    activity = client.get("/p/p01/activity").text
    assert "New connection from your wallet established" in activity
    conn_page = client.get("/p/p01/connections").text
    assert "Your wallet" in conn_page
    assert "Identity verified with" in conn_page


def test_call_two_tampered_is_refused_credential_invalid(monkeypatch) -> None:
    key, trust = _key_and_trust()
    _patch_trust(monkeypatch, trust)
    token = _token(key)
    header, payload, signature = token.split(".")

    def b64url_decode(t: str) -> bytes:
        return base64.urlsafe_b64decode(t + "=" * (-len(t) % 4))

    def b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    claims = json.loads(b64url_decode(payload))
    claims["credentialSubject"]["id"] = "urn:uuid:00000000-0000-0000-0000-000000000000"
    tampered = ".".join([header, b64url(json.dumps(claims, separators=(",", ":")).encode()), signature])

    create = client.post("/api/connections/requests", json={"employers": ["pinecrest"]}).json()
    response = client.post(create["response_uri"], json=_vp(tampered))
    assert response.status_code == 200
    assert response.json() == {"outcome": "refused", "reason": "credential_invalid"}
    assert connections.get_connection("p01") is None


def test_call_two_wrong_employer_is_refused_not_an_employee(monkeypatch) -> None:
    key, trust = _key_and_trust()
    _patch_trust(monkeypatch, trust)
    create = client.post("/api/connections/requests", json={"employers": ["harborline"]}).json()
    response = client.post(create["response_uri"], json=_vp(_token(key)))
    assert response.status_code == 200
    assert response.json() == {"outcome": "refused", "reason": "not_an_employee"}
    assert connections.get_connection("p01") is None
    assert client.get("/p/p01/activity").text.count('class="log__item"') == 0


def test_call_two_answered_twice_is_404_the_second_time(monkeypatch) -> None:
    key, trust = _key_and_trust()
    _patch_trust(monkeypatch, trust)
    create = client.post("/api/connections/requests", json={"employers": ["pinecrest"]}).json()
    first = client.post(create["response_uri"], json=_vp(_token(key)))
    assert first.status_code == 200
    second = client.post(create["response_uri"], json=_vp(_token(key)))
    assert second.status_code == 404
    assert second.json() == {"error": "unknown_request"}


def test_call_two_older_than_fifteen_minutes_is_404(monkeypatch) -> None:
    key, trust = _key_and_trust()
    _patch_trust(monkeypatch, trust)
    create = client.post("/api/connections/requests", json={"employers": ["pinecrest"]}).json()

    from app import clock

    later = datetime(2026, 9, 21, 12, 16, tzinfo=UTC)  # conftest's FIXED_NOW + 16 minutes
    monkeypatch.setattr(clock, "now", lambda: later)
    response = client.post(create["response_uri"], json=_vp(_token(key)))
    assert response.status_code == 404


def test_call_two_rejects_a_non_vp_body() -> None:
    create = client.post("/api/connections/requests", json={"employers": ["pinecrest"]}).json()
    response = client.post(create["response_uri"], json={"not": "a presentation"})
    assert response.status_code == 400
    assert response.json() == {"error": "invalid_presentation"}


def test_call_two_rejects_two_credentials(monkeypatch) -> None:
    key, trust = _key_and_trust()
    _patch_trust(monkeypatch, trust)
    create = client.post("/api/connections/requests", json={"employers": ["pinecrest"]}).json()
    token = _token(key)
    response = client.post(create["response_uri"], json=_vp(token, token))
    assert response.status_code == 400
    assert response.json() == {"error": "invalid_presentation"}
