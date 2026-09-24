"""Call 3: fetch credentials (docs/design.md §2, #106) — exactly Payroll's shape."""

import jwt
import pytest
from fastapi.testclient import TestClient

from app import signing, trust
from app.main import app
from tests.helpers import PAYROLL_ISSUER, STATE_ISSUER, identity_token, keypair, paystub_token, vp

client = TestClient(app)


@pytest.fixture
def keys():
    return {"state": keypair("nj-test-1"), "payroll": keypair("payroll-test-1")}


@pytest.fixture(autouse=True)
def patched_trust(monkeypatch, keys):
    trust_list = {
        STATE_ISSUER: {
            "name": "State of New Jersey",
            "trustedFor": ["IdentityCredential"],
            "keys": [keys["state"][1]],
        },
        PAYROLL_ISSUER: {
            "name": "Meridian Payroll",
            "trustedFor": ["PaystubCredential"],
            "keys": [keys["payroll"][1]],
        },
    }
    monkeypatch.setattr(trust, "trust_list", lambda: trust_list)
    return trust_list


def _decide(keys, *, gross=2200.0, **identity_kwargs) -> dict:
    request_id = client.post("/api/applications/requests").json()["requestId"]
    identity = identity_token(keys["state"][0], "nj-test-1", **identity_kwargs)
    income = paystub_token(keys["payroll"][0], "payroll-test-1", gross=gross)
    response = client.post(f"/api/applications/requests/{request_id}/presentation", json=vp(identity, income))
    return response.json()


def test_returns_credentials_not_in_have_in_program_order(keys) -> None:
    decided = _decide(keys)
    connection_id = decided["connectionId"]
    response = client.post("/api/credentials", json={"connectionId": connection_id, "have": []})
    assert response.status_code == 200
    credentials = response.json()["credentials"]
    assert len(credentials) == 5  # every program eligible at $2,200/month in Hunterdon
    codes = [jwt.decode(c, options={"verify_signature": False})["credentialSubject"]["program"] for c in credentials]
    assert codes == ["food", "energy", "housing", "health", "dividend"]


def test_have_excludes_already_held_credentials(keys) -> None:
    decided = _decide(keys)
    connection_id = decided["connectionId"]
    held_id = decided["programs"][0]["credentialId"]
    response = client.post("/api/credentials", json={"connectionId": connection_id, "have": [held_id]})
    credentials = response.json()["credentials"]
    assert len(credentials) == 4


def test_same_id_and_jwt_every_time(keys) -> None:
    decided = _decide(keys)
    connection_id = decided["connectionId"]
    first = client.post("/api/credentials", json={"connectionId": connection_id, "have": []}).json()
    second = client.post("/api/credentials", json={"connectionId": connection_id, "have": []}).json()
    assert first == second


def test_denied_programs_yield_no_credential(keys) -> None:
    # Luis Ferreira's figures (docs/sample-data.md): $2,536/month in Essex denies food/energy/housing.
    decided = _decide(keys, county="Essex", gross=2536.0)
    connection_id = decided["connectionId"]
    response = client.post("/api/credentials", json={"connectionId": connection_id, "have": []})
    credentials = response.json()["credentials"]
    assert len(credentials) == 2  # health, dividend


def test_404_for_unknown_connection() -> None:
    response = client.post("/api/credentials", json={"connectionId": "nonexistent", "have": []})
    assert response.status_code == 404
    assert response.json() == {"error": "unknown_connection"}


def test_400_for_invalid_request(keys) -> None:
    decided = _decide(keys)
    connection_id = decided["connectionId"]
    assert client.post("/api/credentials", json={"have": []}).status_code == 400
    assert client.post("/api/credentials", json={"connectionId": connection_id}).status_code == 400
    assert client.post(
        "/api/credentials", json={"connectionId": connection_id, "have": "not-a-list"}
    ).status_code == 400
    assert client.post(
        "/api/credentials", json={"connectionId": connection_id, "have": [1, 2]}
    ).status_code == 400


def test_503_without_a_valid_key(keys, monkeypatch) -> None:
    decided = _decide(keys)
    connection_id = decided["connectionId"]
    monkeypatch.delenv(signing.ENV_VAR, raising=False)
    response = client.post("/api/credentials", json={"connectionId": connection_id, "have": []})
    assert response.status_code == 503


def test_reapplying_makes_the_old_connection_id_404(keys) -> None:
    first = _decide(keys)
    second = _decide(keys)
    response = client.post("/api/credentials", json={"connectionId": first["connectionId"], "have": []})
    assert response.status_code == 404
    response = client.post("/api/credentials", json={"connectionId": second["connectionId"], "have": []})
    assert response.status_code == 200
