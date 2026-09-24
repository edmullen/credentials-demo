"""Benefit Agency's own signing key (docs/design.md §3).

A copy of Payroll's shape (apps/payroll/app/signing.py): loaded once from BENEFITS_SIGNING_KEY
and checked against the committed public half in issuer.json, so a misconfigured key fails the
health check instead of silently signing with the wrong key. issuance.py signs with `key()`;
/health and JWKS read `status()` and `public_jwk()`.
"""

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import jwt
from jwt.algorithms import ECAlgorithm

DATA_DIR = Path(__file__).parent / "data"

ENV_VAR = "BENEFITS_SIGNING_KEY"


@lru_cache
def _issuer() -> dict:
    return json.loads((DATA_DIR / "issuer.json").read_text())


@dataclass(frozen=True)
class Status:
    ok: bool
    reason: str | None  # set when not ok


def status() -> Status:
    # Not cached, unlike _issuer(): tests set BENEFITS_SIGNING_KEY per case, and re-deriving the
    # public key from a small JWK is cheap enough to do on every /health call.
    raw = os.environ.get(ENV_VAR)
    if not raw:
        return Status(False, f"{ENV_VAR} is not set")
    try:
        private = json.loads(raw)
        public = json.loads(ECAlgorithm.to_jwk(ECAlgorithm.from_jwk(raw).public_key()))
    except (ValueError, TypeError, jwt.PyJWTError):
        return Status(False, f"{ENV_VAR} does not match the committed public key")
    public["kid"] = private.get("kid")
    if public != _issuer()["publicKey"]:
        return Status(False, f"{ENV_VAR} does not match the committed public key")
    return Status(True, None)


def key():
    """The private key, for signing. Only call when status().ok is True."""
    return ECAlgorithm.from_jwk(os.environ[ENV_VAR])


def kid() -> str:
    return _issuer()["kid"]


def issuer_id() -> str:
    return _issuer()["id"]


def issuer_name() -> str:
    return _issuer()["name"]


def public_jwk() -> dict:
    return _issuer()["publicKey"]
