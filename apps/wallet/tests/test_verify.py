"""Verification, against the committed credentials and against throwaway keys."""

import base64
import json
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from jwt.algorithms import ECAlgorithm

from app.people import DATA_DIR
from app.verify import Outcome, verify

NOW = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)
COMMITTED = json.loads((DATA_DIR / "credentials.json").read_text())
TRUST = json.loads((DATA_DIR / "trust.json").read_text())
TAMPERED = {"p22", "p23"}
NO_CREDENTIAL = {"p24", "p25"}


def test_the_committed_data_is_25_people_with_23_credentials() -> None:
    assert len(COMMITTED) == 25
    assert {pid for pid, tokens in COMMITTED.items() if not tokens} == NO_CREDENTIAL
    assert all(len(tokens) == 1 for pid, tokens in COMMITTED.items() if pid not in NO_CREDENTIAL)


def _outcomes() -> dict[str, Outcome]:
    return {pid: verify(tokens[0], TRUST, NOW).outcome for pid, tokens in COMMITTED.items() if tokens}


def test_every_committed_credential_has_the_outcome_the_sample_data_implies() -> None:
    outcomes = _outcomes()
    assert len(outcomes) == 23
    assert {pid for pid, o in outcomes.items() if o is Outcome.TAMPERED} == TAMPERED
    assert [pid for pid, o in outcomes.items() if o is Outcome.VERIFIED] == [
        pid for pid in outcomes if pid not in TAMPERED
    ]


def test_p08_is_verified() -> None:
    assert verify(COMMITTED["p08"][0], TRUST, NOW).outcome is Outcome.VERIFIED


@pytest.mark.parametrize("person_id", sorted(TAMPERED))
def test_tampered_credentials_still_show_their_claims_as_received(person_id: str) -> None:
    result = verify(COMMITTED[person_id][0], TRUST, NOW)
    assert result.outcome is Outcome.TAMPERED
    assert result.claims["credentialSubject"]["givenName"]


def test_the_tampered_address_is_the_substituted_one() -> None:
    claims = verify(COMMITTED["p22"][0], TRUST, NOW).claims
    assert claims["issuer"]["name"] == "State of New York"
    assert claims["credentialSubject"]["address"]["addressLocality"] == "Elizabeth"


def test_credentials_have_the_documented_shape() -> None:
    for tokens in COMMITTED.values():
        for token in tokens:
            header = jwt.get_unverified_header(token)
            claims = jwt.decode(token, options={"verify_signature": False})
            assert set(header) == {"alg", "typ", "kid"}
            assert header["alg"] == "ES256" and header["typ"] == "vc+jwt"
            assert header["kid"] in {k["kid"] for i in TRUST.values() for k in i["keys"]}
            assert not {"vc", "iss", "sub", "exp"} & set(claims)
            assert claims["issuer"]["id"].startswith("did:example:")


def test_the_trust_list_is_four_states_and_payroll_with_public_keys_only() -> None:
    # The four states, trusted for IdentityCredential, plus Payroll, trusted for
    # PaystubCredential only (docs/design.md §3).
    assert len(TRUST) == 5
    payroll = TRUST["https://cred-demo-payroll.onrender.com"]
    assert payroll["trustedFor"] == ["PaystubCredential"]
    for issuer_id, issuer in TRUST.items():
        if issuer_id == "https://cred-demo-payroll.onrender.com":
            continue
        assert issuer["trustedFor"] == ["IdentityCredential"]
    for issuer in TRUST.values():
        (key,) = issuer["keys"]
        assert key["kty"] == "EC" and key["crv"] == "P-256"
        assert "d" not in key


def _flip_a_payload_character(token: str) -> str:
    header, payload, signature = token.split(".")
    i = len(payload) // 2
    swapped = "A" if payload[i] != "A" else "B"
    return ".".join([header, payload[:i] + swapped + payload[i + 1 :], signature])


@pytest.mark.parametrize("person_id", ["p01", "p08", "p20"])
def test_altering_one_payload_character_makes_a_credential_tampered(person_id: str) -> None:
    changed = _flip_a_payload_character(COMMITTED[person_id][0])
    assert verify(changed, TRUST, NOW).outcome is Outcome.TAMPERED


def test_a_string_that_is_not_a_jwt_is_tampered_with_no_claims() -> None:
    result = verify("not-a-jwt", TRUST, NOW)
    assert result.outcome is Outcome.TAMPERED and result.claims is None


# ---- Throwaway keys: the outcomes the committed data can't reach --------------------------------

ISSUER_ID = "did:example:test-issuer"


def _keypair(kid: str = "t-1") -> tuple[object, dict]:
    key = ec.generate_private_key(ec.SECP256R1())
    public = json.loads(ECAlgorithm.to_jwk(key.public_key()))
    public["kid"] = kid
    return key, public


def _trust(public: dict, trusted_for=("IdentityCredential",)) -> dict:
    return {ISSUER_ID: {"name": "Test Issuer", "trustedFor": list(trusted_for), "keys": [public]}}


def _credential(key, *, kid="t-1", issuer=ISSUER_ID, types=("VerifiableCredential", "IdentityCredential"),
                valid_from=NOW - timedelta(days=1), valid_until=NOW + timedelta(days=1)) -> str:
    payload = {
        "@context": ["https://www.w3.org/ns/credentials/v2"],
        "id": "urn:uuid:00000000-0000-5000-8000-000000000000",
        "type": list(types),
        "issuer": {"id": issuer, "name": "Test Issuer"},
        "validFrom": valid_from.isoformat().replace("+00:00", "Z"),
        "validUntil": valid_until.isoformat().replace("+00:00", "Z") if valid_until else None,
        "credentialSubject": {"id": "urn:uuid:11111111-1111-5111-8111-111111111111"},
    }
    if valid_until is None:
        del payload["validUntil"]
    return jwt.encode(payload, key, algorithm="ES256", headers={"kid": kid, "typ": "vc+jwt"})


def test_a_correctly_signed_credential_within_its_window_is_verified() -> None:
    key, public = _keypair()
    assert verify(_credential(key), _trust(public), NOW).outcome is Outcome.VERIFIED


def test_a_credential_with_no_validUntil_never_expires() -> None:
    key, public = _keypair()
    token = _credential(key, valid_until=None)
    assert verify(token, _trust(public), NOW + timedelta(days=36500)).outcome is Outcome.VERIFIED


def test_after_validUntil_is_expired() -> None:
    key, public = _keypair()
    token = _credential(key, valid_until=NOW - timedelta(seconds=1))
    assert verify(token, _trust(public), NOW).outcome is Outcome.EXPIRED


def test_before_validFrom_is_not_yet_valid() -> None:
    key, public = _keypair()
    token = _credential(key, valid_from=NOW + timedelta(days=1), valid_until=NOW + timedelta(days=9))
    assert verify(token, _trust(public), NOW).outcome is Outcome.NOT_YET_VALID


def test_an_issuer_not_in_the_trust_list_is_unrecognized() -> None:
    key, public = _keypair()
    token = _credential(key, issuer="did:example:somebody-else")
    assert verify(token, _trust(public), NOW).outcome is Outcome.UNRECOGNIZED_ISSUER


def test_an_issuer_not_trusted_for_the_credential_type_is_unrecognized() -> None:
    key, public = _keypair()
    token = _credential(key, types=("VerifiableCredential", "PaystubCredential"))
    assert verify(token, _trust(public), NOW).outcome is Outcome.UNRECOGNIZED_ISSUER


def test_a_signature_from_the_wrong_key_is_tampered() -> None:
    _, public = _keypair()
    other_key, _ = _keypair()
    assert verify(_credential(other_key), _trust(public), NOW).outcome is Outcome.TAMPERED


def test_a_kid_the_issuer_does_not_publish_is_tampered() -> None:
    key, public = _keypair()
    assert verify(_credential(key, kid="t-9"), _trust(public), NOW).outcome is Outcome.TAMPERED


def test_checks_run_in_order_an_unknown_issuer_is_reported_before_a_bad_signature() -> None:
    _, public = _keypair()
    other_key, _ = _keypair()
    token = _credential(other_key, issuer="did:example:somebody-else")
    assert verify(token, _trust(public), NOW).outcome is Outcome.UNRECOGNIZED_ISSUER


def test_a_bad_signature_is_reported_before_an_expired_window() -> None:
    _, public = _keypair()
    other_key, _ = _keypair()
    token = _credential(other_key, valid_until=NOW - timedelta(days=1))
    assert verify(token, _trust(public), NOW).outcome is Outcome.TAMPERED
