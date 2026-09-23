import json

from fastapi.testclient import TestClient

from app import signing
from app.main import app

client = TestClient(app)


def test_health_ok_when_key_matches_issuer_json() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_503_when_key_is_missing(monkeypatch) -> None:
    monkeypatch.delenv(signing.ENV_VAR, raising=False)
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json() == {
        "status": "unhealthy",
        "reason": "PAYROLL_SIGNING_KEY is not set",
    }


def test_health_503_when_key_does_not_match_issuer_json(monkeypatch, payroll_key) -> None:
    other_key = json.loads(json.dumps(payroll_key["private"]))
    other_key["x"] = "AAAA"  # any value that no longer matches the public half in issuer.json
    monkeypatch.setenv(signing.ENV_VAR, json.dumps(other_key))
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json() == {
        "status": "unhealthy",
        "reason": "PAYROLL_SIGNING_KEY does not match the committed public key",
    }


def test_health_503_when_key_is_not_valid_json(monkeypatch) -> None:
    monkeypatch.setenv(signing.ENV_VAR, "not json")
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json()["reason"] == "PAYROLL_SIGNING_KEY does not match the committed public key"


def test_jwks_serves_the_public_key_from_issuer_json(payroll_key) -> None:
    response = client.get("/.well-known/jwks.json")
    assert response.status_code == 200
    assert response.json() == {"keys": [payroll_key["public"]]}
