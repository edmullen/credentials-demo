import json

import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from jwt.algorithms import ECAlgorithm

from app import signing


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
