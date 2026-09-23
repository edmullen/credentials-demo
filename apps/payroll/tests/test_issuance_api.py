"""POST /api/credentials (call 3, docs/design.md §2, §5) and the connection id it authenticates."""

import json

import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from jwt.algorithms import ECAlgorithm

from app import connections
from app.issuance import credential_id
from app.main import app
from app.paystubs import paystubs_for

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


def _connect(monkeypatch, employers: list[str] = None) -> str:
    """Runs the full call 1 + 2 flow for p01 and returns the connectionId."""
    key, trust = _key_and_trust()
    monkeypatch.setattr("app.main.trust_list", lambda: trust)
    create = client.post(
        "/api/connections/requests", json={"employers": employers or ["pinecrest"]}
    ).json()
    response = client.post(create["response_uri"], json=_vp(_token(key)))
    return response.json()["connectionId"]


def test_returns_credentials_not_in_have_newest_first(monkeypatch, payroll_key) -> None:
    connection_id = _connect(monkeypatch)
    response = client.post("/api/credentials", json={"connectionId": connection_id, "have": []})
    assert response.status_code == 200
    creds = response.json()["credentials"]
    expected_ids = [credential_id(s) for s in paystubs_for("p01")]
    assert len(creds) == len(expected_ids)
    got_ids = [jwt.decode(c, options={"verify_signature": False})["id"] for c in creds]
    assert got_ids == expected_ids  # newest pay date first (§4)


def test_omits_credentials_already_held(monkeypatch, payroll_key) -> None:
    connection_id = _connect(monkeypatch)
    all_ids = [credential_id(s) for s in paystubs_for("p01")]
    response = client.post(
        "/api/credentials", json={"connectionId": connection_id, "have": all_ids[:1]}
    )
    assert response.status_code == 200
    creds = response.json()["credentials"]
    got_ids = [jwt.decode(c, options={"verify_signature": False})["id"] for c in creds]
    assert got_ids == all_ids[1:]


def test_empty_when_everything_is_already_held(monkeypatch, payroll_key) -> None:
    connection_id = _connect(monkeypatch)
    all_ids = [credential_id(s) for s in paystubs_for("p01")]
    response = client.post(
        "/api/credentials", json={"connectionId": connection_id, "have": all_ids}
    )
    assert response.status_code == 200
    assert response.json() == {"credentials": []}


def test_unknown_connection_is_404(payroll_key) -> None:
    response = client.post(
        "/api/credentials", json={"connectionId": "not-a-real-id", "have": []}
    )
    assert response.status_code == 404
    assert response.json() == {"error": "unknown_connection"}


def test_reconnecting_replaces_the_connection_id(monkeypatch, payroll_key) -> None:
    first_id = _connect(monkeypatch)
    second_id = _connect(monkeypatch)
    assert first_id != second_id
    stale = client.post("/api/credentials", json={"connectionId": first_id, "have": []})
    assert stale.status_code == 404
    fresh = client.post("/api/credentials", json={"connectionId": second_id, "have": []})
    assert fresh.status_code == 200


def test_bad_body_shapes_are_400(payroll_key) -> None:
    for body in [
        {},
        {"connectionId": "x"},
        {"have": []},
        {"connectionId": 1, "have": []},
        {"connectionId": "x", "have": "not-a-list"},
        {"connectionId": "x", "have": [1, 2]},
    ]:
        response = client.post("/api/credentials", json=body)
        assert response.status_code == 400
        assert response.json() == {"error": "invalid_request"}


def test_activity_logs_a_send_with_singular_and_plural(monkeypatch, payroll_key) -> None:
    connection_id = _connect(monkeypatch)
    all_ids = [credential_id(s) for s in paystubs_for("p01")]
    # Send just one first, to see the singular form.
    client.post("/api/credentials", json={"connectionId": connection_id, "have": all_ids[1:]})
    activity = client.get("/p/p01/activity").text
    assert "1 income credential sent to your wallet" in activity
    assert "1 income credentials sent" not in activity

    client.post("/api/credentials", json={"connectionId": connection_id, "have": []})
    activity = client.get("/p/p01/activity").text
    assert f"{len(all_ids)} income credentials sent to your wallet" in activity


def test_activity_logs_nothing_for_an_empty_send(monkeypatch, payroll_key) -> None:
    connection_id = _connect(monkeypatch)
    all_ids = [credential_id(s) for s in paystubs_for("p01")]
    client.post("/api/credentials", json={"connectionId": connection_id, "have": all_ids})
    events = connections.events_for("p01")
    assert not any("sent to your wallet" in e.message for e in events)
