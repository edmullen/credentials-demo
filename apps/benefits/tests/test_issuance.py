"""The benefit credential (docs/design.md §5, §14, #106)."""

import json
from datetime import UTC, datetime
from decimal import Decimal

import jwt
from jwt.algorithms import ECAlgorithm

from app import signing
from app.eligibility import decide
from app.issuance import credential_payload, issue_eligible, sign
from app.programs import get_program

SUBJECT_ID = "urn:uuid:33333333-3333-5333-8333-333333333333"
DECIDED_AT = datetime(2026, 10, 1, 14, 3, 27, 654321, tzinfo=UTC)


def test_credential_shape_matches_credential_model_for_a_pass_fail_program(benefits_key) -> None:
    d = decide("NJ", "Hunterdon", [Decimal("2200.00")])
    result = d.program("food")
    payload = credential_payload(result, SUBJECT_ID, DECIDED_AT)
    assert payload["@context"] == ["https://www.w3.org/ns/credentials/v2"]
    assert payload["id"].startswith("urn:uuid:")
    assert payload["type"] == ["VerifiableCredential", "BenefitCredential"]
    assert payload["issuer"] == {"id": signing.issuer_id(), "name": "Benefit Agency"}
    assert payload["credentialSubject"] == {"id": SUBJECT_ID, "program": "food"}
    assert "discountPercent" not in payload["credentialSubject"]
    assert "monthlyPayment" not in payload["credentialSubject"]


def test_health_credential_carries_discount_and_plan_cost(benefits_key) -> None:
    d = decide("NJ", "Hunterdon", [Decimal("2200.00")])
    result = d.program("health")
    payload = credential_payload(result, SUBJECT_ID, DECIDED_AT)
    subject = payload["credentialSubject"]
    assert subject["program"] == "health"
    assert subject["discountPercent"] == 92.4
    assert subject["planCost"] == {"type": "MonetaryAmount", "value": 750.0, "currency": "USD"}


def test_dividend_credential_carries_monthly_payment(benefits_key) -> None:
    d = decide("NJ", "Hunterdon", [Decimal("2200.00")])
    result = d.program("dividend")
    payload = credential_payload(result, SUBJECT_ID, DECIDED_AT)
    subject = payload["credentialSubject"]
    assert subject["program"] == "dividend"
    assert subject["monthlyPayment"] == {"type": "MonetaryAmount", "value": 100.0, "currency": "USD"}


def test_valid_from_is_floored_to_the_whole_minute(benefits_key) -> None:
    d = decide("NJ", "Hunterdon", [Decimal("2200.00")])
    payload = credential_payload(d.program("food"), SUBJECT_ID, DECIDED_AT)
    assert payload["validFrom"] == "2026-10-01T14:03:00Z"


def test_valid_until_is_twelve_months_later() -> None:
    d = decide("NJ", "Hunterdon", [Decimal("2200.00")])
    payload = credential_payload(d.program("food"), SUBJECT_ID, DECIDED_AT)
    assert payload["validUntil"] == "2027-10-01T14:03:00Z"


def test_valid_until_handles_29_february() -> None:
    d = decide("NJ", "Hunterdon", [Decimal("2200.00")])
    leap_day = datetime(2028, 2, 29, 9, 0, tzinfo=UTC)
    payload = credential_payload(d.program("food"), SUBJECT_ID, leap_day)
    assert payload["validFrom"] == "2028-02-29T09:00:00Z"
    assert payload["validUntil"] == "2029-02-28T09:00:00Z"


def test_render_hint_carries_the_programs_hue() -> None:
    d = decide("NJ", "Hunterdon", [Decimal("2200.00")])
    for code in ("food", "energy", "housing", "health", "dividend"):
        payload = credential_payload(d.program(code), SUBJECT_ID, DECIDED_AT)
        hue = get_program(code)["hue"]
        assert payload["renderMethod"] == [{"type": "CredDemoCardColor", "color": f"oklch(0.46 0.11 {hue})"}]


def test_header_is_es256_benefits_1_vc_jwt(benefits_key) -> None:
    d = decide("NJ", "Hunterdon", [Decimal("2200.00")])
    payload = credential_payload(d.program("food"), SUBJECT_ID, DECIDED_AT)
    token = sign(payload)
    header = jwt.get_unverified_header(token)
    assert header["alg"] == "ES256"
    assert header["kid"] == "benefits-1"
    assert header["typ"] == "vc+jwt"


def test_signature_verifies_against_issuer_json(benefits_key) -> None:
    d = decide("NJ", "Hunterdon", [Decimal("2200.00")])
    payload = credential_payload(d.program("food"), SUBJECT_ID, DECIDED_AT)
    token = sign(payload)
    key = ECAlgorithm.from_jwk(json.dumps(benefits_key["public"]))
    claims = jwt.decode(token, key, algorithms=["ES256"])
    assert claims["id"] == payload["id"]


def test_envelope_matches_credential_model_key_by_key(benefits_key) -> None:
    # credential-model.md §3, "The common envelope": id, type, issuer, validFrom, validUntil,
    # credentialSubject — no vc wrapper, no iss/sub/exp.
    d = decide("NJ", "Hunterdon", [Decimal("2200.00")])
    payload = credential_payload(d.program("food"), SUBJECT_ID, DECIDED_AT)
    assert set(payload) == {
        "@context", "id", "type", "issuer", "validFrom", "validUntil", "credentialSubject",
        "renderMethod",
    }
    assert set(payload["issuer"]) == {"id", "name"}


def test_health_claims_match_credential_model_key_by_key() -> None:
    # credential-model.md §3, "Benefit credential" table: Health carries program,
    # discountPercent, planCost beyond id.
    d = decide("NJ", "Hunterdon", [Decimal("2200.00")])
    payload = credential_payload(d.program("health"), SUBJECT_ID, DECIDED_AT)
    assert set(payload["credentialSubject"]) == {"id", "program", "discountPercent", "planCost"}
    assert set(payload["credentialSubject"]["planCost"]) == {"type", "value", "currency"}


def test_dividend_claims_match_credential_model_key_by_key() -> None:
    d = decide("NJ", "Hunterdon", [Decimal("2200.00")])
    payload = credential_payload(d.program("dividend"), SUBJECT_ID, DECIDED_AT)
    assert set(payload["credentialSubject"]) == {"id", "program", "monthlyPayment"}


def test_pass_fail_claims_match_credential_model_key_by_key() -> None:
    d = decide("NJ", "Hunterdon", [Decimal("2200.00")])
    for code in ("food", "energy", "housing"):
        payload = credential_payload(d.program(code), SUBJECT_ID, DECIDED_AT)
        assert set(payload["credentialSubject"]) == {"id", "program"}


def test_a_denial_yields_no_credential() -> None:
    d = decide("MI", "Hunterdon", [Decimal("2200.00")])  # every program denied
    issued = issue_eligible(d.programs, SUBJECT_ID, DECIDED_AT)
    assert issued == {}


def test_issue_eligible_returns_one_entry_per_eligible_program_only() -> None:
    d = decide("NJ", "Essex", [Decimal("2536.00")])  # food/energy/housing denied, health/dividend eligible
    issued = issue_eligible(d.programs, SUBJECT_ID, DECIDED_AT)
    assert set(issued) == {"health", "dividend"}
    assert issued["health"].credential_id.startswith("urn:uuid:")
    assert issued["health"].jwt.count(".") == 2


def test_each_call_signs_a_fresh_jwt_but_the_credential_id_is_fixed_once_created() -> None:
    d = decide("NJ", "Hunterdon", [Decimal("2200.00")])
    result = d.program("food")
    payload = credential_payload(result, SUBJECT_ID, DECIDED_AT)
    token_1 = sign(payload)
    token_2 = sign(payload)
    claims_1 = jwt.decode(token_1, options={"verify_signature": False})
    claims_2 = jwt.decode(token_2, options={"verify_signature": False})
    assert claims_1["id"] == claims_2["id"] == payload["id"]
