"""Tests mint throwaway ES256 keys and a test trust list at test time (docs/design.md §10).
Nothing here reads the Wallet's committed files.
"""

import base64
import json
from datetime import UTC, datetime

import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from jwt.algorithms import ECAlgorithm

from app.presentation import verify_presentation

ISSUER_ID = "did:example:test-state"
ISSUER_NAME = "State of Testland"
KID = "test-1"
NOW = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)

# p01 (Grace Okafor)'s real subject id and employer, from apps/payroll/app/data.
GRACE_SUBJECT = "urn:uuid:031acde8-d4c0-5778-b6ab-84a4b612af70"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _trust_and_key() -> tuple[dict, object]:
    key = ec.generate_private_key(ec.SECP256R1())
    public = json.loads(ECAlgorithm.to_jwk(key.public_key()))
    public["kid"] = KID
    trust = {
        ISSUER_ID: {"name": ISSUER_NAME, "trustedFor": ["IdentityCredential"], "keys": [public]}
    }
    return trust, key


def _sign(payload: dict, key) -> str:
    return jwt.encode(payload, key, algorithm="ES256", headers={"kid": KID, "typ": "vc+jwt"})


def _payload(
    subject_id: str, valid_from: str = "2026-01-01T00:00:00Z", valid_until: str = "2030-01-01T00:00:00Z"
) -> dict:
    return {
        "@context": ["https://www.w3.org/ns/credentials/v2"],
        "id": "urn:uuid:11111111-1111-1111-1111-111111111111",
        "type": ["VerifiableCredential", "IdentityCredential"],
        "issuer": {"id": ISSUER_ID, "name": ISSUER_NAME},
        "validFrom": valid_from,
        "validUntil": valid_until,
        "credentialSubject": {"id": subject_id},
    }


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


def _tamper_subject(token: str, subject_id: str) -> str:
    header, payload, signature = token.split(".")
    claims = json.loads(_b64url_decode(payload))
    claims["credentialSubject"]["id"] = subject_id
    encoded = json.dumps(claims, separators=(",", ":")).encode()
    return ".".join([header, _b64url(encoded), signature])


def test_valid_at_the_right_employer_connects() -> None:
    trust, key = _trust_and_key()
    token = _sign(_payload(GRACE_SUBJECT), key)
    outcome, extra = verify_presentation(_vp(token), ["pinecrest"], trust, NOW)
    assert outcome == "connected"
    assert extra["person"]["id"] == "p01"
    assert extra["issuer_name"] == ISSUER_NAME


def test_tampered_is_credential_invalid() -> None:
    trust, key = _trust_and_key()
    token = _sign(_payload(GRACE_SUBJECT), key)
    tampered = _tamper_subject(token, "urn:uuid:00000000-0000-0000-0000-000000000000")
    outcome, extra = verify_presentation(_vp(tampered), ["pinecrest"], trust, NOW)
    assert outcome == "credential_invalid"
    assert extra is None


def test_unknown_issuer_is_credential_invalid() -> None:
    _, key = _trust_and_key()
    token = _sign(_payload(GRACE_SUBJECT), key)
    outcome, _ = verify_presentation(_vp(token), ["pinecrest"], {}, NOW)
    assert outcome == "credential_invalid"


def test_expired_is_credential_invalid() -> None:
    trust, key = _trust_and_key()
    token = _sign(
        _payload(GRACE_SUBJECT, valid_from="2020-01-01T00:00:00Z", valid_until="2021-01-01T00:00:00Z"),
        key,
    )
    outcome, _ = verify_presentation(_vp(token), ["pinecrest"], trust, NOW)
    assert outcome == "credential_invalid"


def test_not_yet_valid_is_credential_invalid() -> None:
    trust, key = _trust_and_key()
    token = _sign(
        _payload(GRACE_SUBJECT, valid_from="2030-01-01T00:00:00Z", valid_until="2035-01-01T00:00:00Z"),
        key,
    )
    outcome, _ = verify_presentation(_vp(token), ["pinecrest"], trust, NOW)
    assert outcome == "credential_invalid"


def test_verified_at_the_wrong_employer_is_not_an_employee() -> None:
    trust, key = _trust_and_key()
    token = _sign(_payload(GRACE_SUBJECT), key)
    outcome, extra = verify_presentation(_vp(token), ["harborline"], trust, NOW)
    assert outcome == "not_an_employee"
    assert extra is None


def test_right_plus_wrong_employer_is_not_an_employee() -> None:
    trust, key = _trust_and_key()
    token = _sign(_payload(GRACE_SUBJECT), key)
    outcome, _ = verify_presentation(_vp(token), ["pinecrest", "harborline"], trust, NOW)
    assert outcome == "not_an_employee"


def test_unknown_subject_is_not_an_employee() -> None:
    trust, key = _trust_and_key()
    token = _sign(_payload("urn:uuid:99999999-9999-9999-9999-999999999999"), key)
    outcome, _ = verify_presentation(_vp(token), ["pinecrest"], trust, NOW)
    assert outcome == "not_an_employee"


def test_not_a_vp_is_invalid_presentation() -> None:
    outcome, _ = verify_presentation({"type": "SomethingElse"}, ["pinecrest"], {}, NOW)
    assert outcome == "invalid_presentation"


def test_two_credentials_is_invalid_presentation() -> None:
    trust, key = _trust_and_key()
    token = _sign(_payload(GRACE_SUBJECT), key)
    outcome, _ = verify_presentation(_vp(token, token), ["pinecrest"], trust, NOW)
    assert outcome == "invalid_presentation"
