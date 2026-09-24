import json
from datetime import UTC, datetime

import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from jwt.algorithms import ECAlgorithm

from app import applications, clock, signing

# An arbitrary fixed "today" — Benefits' own tests mint throwaway keys and credentials at test
# time (docs/design.md §6), so nothing here depends on real-world dates.
FIXED_NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: FIXED_NOW)
    return FIXED_NOW


@pytest.fixture(autouse=True)
def benefits_key(monkeypatch):
    """Tests never use the real key (docs/design.md §3): a throwaway pair, with issuer.json's
    public half patched in memory to match, so /health, JWKS and signing all agree."""
    key = ec.generate_private_key(ec.SECP256R1())
    private = json.loads(ECAlgorithm.to_jwk(key))
    public = json.loads(ECAlgorithm.to_jwk(key.public_key()))
    private["kid"] = public["kid"] = "benefits-1"
    monkeypatch.setenv(signing.ENV_VAR, json.dumps(private))
    real_issuer = signing._issuer()
    monkeypatch.setattr(signing, "_issuer", lambda: {**real_issuer, "publicKey": public})
    return {"private": private, "public": public}


@pytest.fixture(autouse=True)
def fresh_state():
    """Runtime state is in-memory and shared across requests (docs/design.md §6) — reset it
    between tests so one test's applications and connections can't leak into the next."""
    applications.reset_all()
    yield
    applications.reset_all()
