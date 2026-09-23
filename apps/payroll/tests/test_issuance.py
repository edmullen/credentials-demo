import json
from decimal import Decimal

import jwt
from jwt.algorithms import ECAlgorithm

from app import signing
from app.issuance import credential_id, credential_payload, issue
from app.paystubs import paystubs_for

P01_FIRST = paystubs_for("p01")[0]  # newest pay date first (docs/design.md §4)


def test_matches_credential_models_paystub_example_key_by_key() -> None:
    """The first test, written from the spec (docs/design.md §11): compare structure, key by
    key, with credential-model.md §3's PaystubCredential example and envelope."""
    payload = credential_payload(P01_FIRST)

    # The common envelope (credential-model §3).
    assert set(payload) == {
        "@context", "id", "type", "issuer", "validFrom", "credentialSubject", "renderMethod",
    }
    assert payload["@context"] == ["https://www.w3.org/ns/credentials/v2"]
    assert payload["id"].startswith("urn:uuid:")
    assert payload["type"] == ["VerifiableCredential", "PaystubCredential"]
    assert set(payload["issuer"]) == {"id", "name"}
    assert "validUntil" not in payload  # a paystub never expires (§5)

    subject = payload["credentialSubject"]
    assert set(subject) == {
        "id", "employer", "payPeriodStart", "payPeriodEnd", "payDate", "payFrequency",
        "grossPay", "netPay",
    }
    assert subject["id"].startswith("urn:uuid:")
    assert set(subject["employer"]) == {"type", "name"}
    assert subject["employer"]["type"] == "Organization"
    for amount_key in ("grossPay", "netPay"):
        amount = subject[amount_key]
        assert set(amount) == {"type", "value", "currency"}
        assert amount["type"] == "MonetaryAmount"
        assert amount["currency"] == "USD"
        assert isinstance(amount["value"], float)
    assert "name" not in subject and "givenName" not in subject  # no employee name


def test_credential_id_is_stable_a_urn_uuid_and_not_the_paystubs_id() -> None:
    first = credential_id(P01_FIRST)
    second = credential_id(P01_FIRST)
    assert first == second
    assert first.startswith("urn:uuid:")
    assert first != P01_FIRST["id"]


def test_valid_from_is_the_pay_date_at_midnight_utc() -> None:
    payload = credential_payload(P01_FIRST)
    assert payload["validFrom"] == f"{P01_FIRST['payDate']}T00:00:00Z"


def test_claims_match_the_paystub() -> None:
    payload = credential_payload(P01_FIRST)
    subject = payload["credentialSubject"]
    assert subject["id"] == P01_FIRST["subjectId"]
    assert subject["employer"]["name"] == P01_FIRST["employerName"]
    assert subject["payPeriodStart"] == P01_FIRST["payPeriodStart"]
    assert subject["payPeriodEnd"] == P01_FIRST["payPeriodEnd"]
    assert subject["payDate"] == P01_FIRST["payDate"]
    assert subject["payFrequency"] == P01_FIRST["payFrequency"]
    assert Decimal(str(subject["grossPay"]["value"])) == Decimal(P01_FIRST["grossPay"])
    assert Decimal(str(subject["netPay"]["value"])) == Decimal(P01_FIRST["netPay"])


def test_render_method_carries_payrolls_issuer_color() -> None:
    payload = credential_payload(P01_FIRST)
    assert payload["renderMethod"] == [
        {"type": "CredDemoIssuerColor", "color": "oklch(0.46 0.11 255)"}
    ]


def test_header_is_es256_payroll_1_vc_jwt(payroll_key) -> None:
    token = issue(P01_FIRST)
    header = jwt.get_unverified_header(token)
    assert header == {"alg": "ES256", "typ": "vc+jwt", "kid": "payroll-1"}


def test_signature_verifies_against_issuer_json(payroll_key) -> None:
    token = issue(P01_FIRST)
    key = ECAlgorithm.from_jwk(json.dumps(payroll_key["public"]))
    claims = jwt.decode(token, key, algorithms=["ES256"])
    assert claims["id"] == credential_id(P01_FIRST)


def test_issuer_id_is_the_deployed_origin() -> None:
    payload = credential_payload(P01_FIRST)
    assert payload["issuer"]["id"] == signing.issuer_id() == "https://cred-demo-payroll.onrender.com"
