"""Benefit credentials on the Credentials page: the category, ledge figures, hue, New, and the
detail page (docs/design.md §11, §13 table A)."""

import json
import uuid
from datetime import UTC, datetime

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from jwt.algorithms import ECAlgorithm

from app import clock, credentials, state
from app.main import app

client = TestClient(app)

ISSUER_ID = "https://cred-demo-benefits.onrender.com"
SUBJECT_ID = "urn:uuid:22222222-2222-5222-8222-222222222222"
HUES = {"food": "169", "energy": "24", "housing": "342", "health": "223", "dividend": "121"}


def _benefits_key() -> tuple[object, dict]:
    key = ec.generate_private_key(ec.SECP256R1())
    public = json.loads(ECAlgorithm.to_jwk(key.public_key()))
    public["kid"] = "benefits-1"
    return key, public


@pytest.fixture
def benefits_trust(monkeypatch):
    """Real committed identity credentials, plus a throwaway Benefits key trusted for
    BenefitCredential only — so benefit credentials in these tests genuinely verify."""
    key, public = _benefits_key()
    stored, _ = credentials._committed()
    trust = {ISSUER_ID: {"name": "Benefit Agency", "trustedFor": ["BenefitCredential"], "keys": [public]}}
    monkeypatch.setattr(credentials, "_committed", lambda: (stored, trust))
    return key


def _benefit(
    key, *, program="food", n=1, hue=None, discount_percent=None, plan_cost=750.0,
    monthly_payment=None, tamper=False, render_type="CredDemoCardColor",
) -> tuple[str, str]:
    """Returns (credential_id, jwt)."""
    credential_id = f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, f'test-benefit-{program}-{n}')}"
    if hue is None:
        hue = HUES[program]
    subject = {"id": SUBJECT_ID, "program": program}
    if discount_percent is not None:
        subject["discountPercent"] = discount_percent
        subject["planCost"] = {"type": "MonetaryAmount", "value": plan_cost, "currency": "USD"}
    if monthly_payment is not None:
        subject["monthlyPayment"] = {"type": "MonetaryAmount", "value": monthly_payment, "currency": "USD"}
    payload = {
        "@context": ["https://www.w3.org/ns/credentials/v2"],
        "id": credential_id,
        "type": ["VerifiableCredential", "BenefitCredential"],
        "issuer": {"id": ISSUER_ID, "name": "Benefit Agency"},
        "validFrom": "2026-10-01T00:00:00Z",
        "validUntil": "2027-10-01T00:00:00Z",
        "credentialSubject": subject,
    }
    if hue:
        payload["renderMethod"] = [{"type": render_type, "color": f"oklch(0.46 0.11 {hue})"}]
    token = jwt.encode(payload, key, algorithm="ES256", headers={"kid": "benefits-1", "typ": "vc+jwt"})
    if tamper:
        header, body, sig = token.split(".")
        claims = json.loads(jwt.utils.base64url_decode(body + "=" * (-len(body) % 4)))
        claims["credentialSubject"]["program"] = "housing"
        body = jwt.utils.base64url_encode(json.dumps(claims, separators=(",", ":")).encode()).decode()
        token = ".".join([header, body, sig])
    return credential_id, token


def _receive(person_id: str, *tokens: tuple[str, str]) -> None:
    for credential_id, token in tokens:
        state.add_received(person_id, credential_id, token)


def test_benefits_category_appears_between_identity_and_income(benefits_trust) -> None:
    _receive("p01", _benefit(benefits_trust, program="food"))
    body = client.get("/p/p01/credentials").text
    identity_pos = body.index('id="cat-identity"')
    benefits_pos = body.index('id="cat-benefits"')
    assert identity_pos < benefits_pos


def test_cards_render_in_program_order_dividend_at_front(benefits_trust) -> None:
    _receive(
        "p01",
        _benefit(benefits_trust, program="dividend", monthly_payment=100.0),
        _benefit(benefits_trust, program="food"),
        _benefit(benefits_trust, program="health", discount_percent=92.4),
    )
    body = client.get("/p/p01/credentials").text
    stack = body[body.index('id="benefits"'):body.index('id="income"')]
    food_i = stack.index("--i: 0")
    health_i = stack.index("--i: 1")
    dividend_i = stack.index("--i: 2")
    assert food_i < health_i < dividend_i  # program order in markup


def test_pass_fail_figure_is_eligible(benefits_trust) -> None:
    _receive("p01", _benefit(benefits_trust, program="housing"))
    body = client.get("/p/p01/credentials").text
    assert "Housing Assistance" in body
    assert 'class="stack-cards__figure">Eligible<' in body


def test_dividend_figure_is_payment_a_month(benefits_trust) -> None:
    _receive("p01", _benefit(benefits_trust, program="dividend", monthly_payment=125.0))
    body = client.get("/p/p01/credentials").text
    assert 'class="stack-cards__figure">$125.00 a month<' in body


def test_health_partial_discount_shows_figure_and_sub(benefits_trust) -> None:
    _receive("p01", _benefit(benefits_trust, program="health", discount_percent=92.4, plan_cost=750.0))
    body = client.get("/p/p01/credentials").text
    assert 'class="stack-cards__figure">92.4% off<' in body
    assert 'class="cred__figure-sub">$57.00 a month<' in body


def test_health_full_discount_drops_trailing_zero(benefits_trust) -> None:
    _receive("p01", _benefit(benefits_trust, program="health", discount_percent=100.0, plan_cost=750.0))
    body = client.get("/p/p01/credentials").text
    assert 'class="stack-cards__figure">100% off<' in body
    assert 'class="cred__figure-sub">$0.00 a month<' in body


def test_health_zero_discount_shows_full_price(benefits_trust) -> None:
    _receive("p01", _benefit(benefits_trust, program="health", discount_percent=0.0, plan_cost=750.0))
    body = client.get("/p/p01/credentials").text
    assert 'class="stack-cards__figure">Full price<' in body
    assert 'class="cred__figure-sub">0% off: $750.00 a month<' in body


@pytest.mark.parametrize("program,hue", list(HUES.items()))
def test_hue_per_program(benefits_trust, program, hue) -> None:
    kwargs = {}
    if program == "health":
        kwargs = {"discount_percent": 50.0}
    elif program == "dividend":
        kwargs = {"monthly_payment": 100.0}
    _receive("p01", _benefit(benefits_trust, program=program, **kwargs))
    body = client.get("/p/p01/credentials").text
    assert f"--issuer-hue: {hue}" in body


def test_new_pill_shows_once_then_is_gone(benefits_trust) -> None:
    _receive("p01", _benefit(benefits_trust, program="food"))
    first = client.get("/p/p01/credentials").text
    assert 'class="cred__new">New</span>' in first
    assert "1 credential · 1 new" in first.replace("&middot;", "·")
    second = client.get("/p/p01/credentials").text
    assert 'class="cred__new">New</span>' not in second


def test_old_render_hint_name_is_not_recognized(benefits_trust) -> None:
    _receive("p01", _benefit(benefits_trust, program="food", render_type="CredDemoIssuerColor"))
    body = client.get("/p/p01/credentials").text
    assert "cred--issuer" not in body


def test_no_benefits_category_when_no_benefit_credentials(benefits_trust) -> None:
    body = client.get("/p/p01/credentials").text
    assert 'id="cat-benefits"' not in body


def test_detail_page_health(benefits_trust) -> None:
    credential_id, token = _benefit(benefits_trust, program="health", discount_percent=92.4, plan_cost=750.0)
    _receive("p01", (credential_id, token))
    body = client.get(f"/p/p01/credentials/{credential_id.removeprefix('urn:uuid:')}").text
    assert 'class="panel__issuer-name">Health<' in body
    assert "92.4% off" in body
    assert "Public Option, $750.00 a month" in body
    assert "$57.00 a month" in body
    assert "Worked out by your wallet from the discount" in body


def test_detail_page_dividend(benefits_trust) -> None:
    credential_id, token = _benefit(benefits_trust, program="dividend", monthly_payment=100.0)
    _receive("p01", (credential_id, token))
    body = client.get(f"/p/p01/credentials/{credential_id.removeprefix('urn:uuid:')}").text
    assert "$100.00 a month" in body


def test_detail_page_pass_fail(benefits_trust) -> None:
    credential_id, token = _benefit(benefits_trust, program="food")
    _receive("p01", (credential_id, token))
    body = client.get(f"/p/p01/credentials/{credential_id.removeprefix('urn:uuid:')}").text
    assert "Eligible" in body
    assert "Food Assistance carries no amount. Holding this credential shows you qualify." in body


def test_detail_page_tampered(benefits_trust) -> None:
    credential_id, token = _benefit(benefits_trust, program="food", tamper=True)
    _receive("p01", (credential_id, token))
    body = client.get(f"/p/p01/credentials/{credential_id.removeprefix('urn:uuid:')}").text
    assert ">Tampered<" in body
    assert "Something in this credential was changed after Benefit Agency issued it" in body
    assert "can’t be trusted or used." in body
    assert "The rest of this credential is shown as it was received" in body
