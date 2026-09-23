"""Verify a credential JWT against a trust list.

The four checks of docs/credential-model.md §2, in order, stopping at the first failure. The
claims for checks 1, 2 and 4 are read from the payload *without* trusting it; check 3 decides
whether any of it can be believed. That ordering is what lets a tampered credential still be
shown as received.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

import jwt
from jwt.algorithms import ECAlgorithm


class Outcome(Enum):
    VERIFIED = "verified"
    TAMPERED = "tampered"
    EXPIRED = "expired"
    NOT_YET_VALID = "not_yet_valid"
    UNRECOGNIZED_ISSUER = "unrecognized_issuer"


@dataclass(frozen=True)
class Result:
    outcome: Outcome
    claims: dict | None  # the payload as received; None if it could not be read at all
    kid: str | None  # the key the header names


def _read_unverified(token: str) -> tuple[dict, dict] | None:
    try:
        header = jwt.get_unverified_header(token)
        claims = jwt.decode(token, options={"verify_signature": False})
    except jwt.PyJWTError:
        return None
    return header, claims


def _signature_verifies(token: str, header: dict, issuer: dict) -> bool:
    key_data = next((k for k in issuer.get("keys", []) if k.get("kid") == header.get("kid")), None)
    if key_data is None:
        return False
    key = ECAlgorithm.from_jwk(json.dumps(key_data))
    try:
        # PyJWT's own exp/nbf handling is off: the credential carries validFrom/validUntil
        # instead of registered claims (credential-model §4), and check 4 is ours.
        jwt.decode(token, key, algorithms=["ES256"], options={"verify_exp": False, "verify_nbf": False})
    except jwt.PyJWTError:
        return False
    return True


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value)


def verify(token: str, trust: dict, now: datetime) -> Result:
    read = _read_unverified(token)
    if read is None:
        # Not a readable JWT at all, so nothing to show and nothing to trust.
        return Result(Outcome.TAMPERED, None, None)
    header, claims = read
    kid = header.get("kid")

    def result(outcome: Outcome) -> Result:
        return Result(outcome, claims, kid)

    issuer_id = (claims.get("issuer") or {}).get("id")
    issuer = trust.get(issuer_id)
    if issuer is None:  # 1. known issuer
        return result(Outcome.UNRECOGNIZED_ISSUER)

    types = [t for t in claims.get("type", []) if t != "VerifiableCredential"]
    if not types or any(t not in issuer.get("trustedFor", []) for t in types):  # 2. trusted for type
        return result(Outcome.UNRECOGNIZED_ISSUER)

    if not _signature_verifies(token, header, issuer):  # 3. signature
        return result(Outcome.TAMPERED)

    valid_from, valid_until = claims.get("validFrom"), claims.get("validUntil")  # 4. validity window
    if valid_from and now < _timestamp(valid_from):
        return result(Outcome.NOT_YET_VALID)
    if valid_until and now > _timestamp(valid_until):
        return result(Outcome.EXPIRED)
    return result(Outcome.VERIFIED)
