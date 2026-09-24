"""Shared fixtures for the apply-to-Benefits tests (docs/design.md §10): a throwaway Payroll
key trusted for PaystubCredential, so income credentials genuinely verify, and a builder for one
income credential."""

import json
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from jwt.algorithms import ECAlgorithm

from app import credentials

PAYROLL_ISSUER_ID = "https://cred-demo-payroll.onrender.com"
BENEFITS_ISSUER_ID = "https://cred-demo-benefits.onrender.com"
SUBJECT_ID = "urn:uuid:22222222-2222-5222-8222-222222222222"


def _keypair(kid: str) -> tuple[object, dict]:
    key = ec.generate_private_key(ec.SECP256R1())
    public = json.loads(ECAlgorithm.to_jwk(key.public_key()))
    public["kid"] = kid
    return key, public


def _payroll_key() -> tuple[object, dict]:
    return _keypair("payroll-1")


@pytest.fixture
def payroll_trust(monkeypatch):
    key, public = _payroll_key()
    stored, _ = credentials._committed()
    trust = {
        PAYROLL_ISSUER_ID: {"name": "Meridian Payroll", "trustedFor": ["PaystubCredential"], "keys": [public]},
    }
    monkeypatch.setattr(credentials, "_committed", lambda: (stored, trust))
    return key


@pytest.fixture
def benefits_trust(monkeypatch):
    key, public = _keypair("benefits-1")
    stored, _ = credentials._committed()
    trust = {
        BENEFITS_ISSUER_ID: {"name": "Benefit Agency", "trustedFor": ["BenefitCredential"], "keys": [public]},
    }
    monkeypatch.setattr(credentials, "_committed", lambda: (stored, trust))
    return key


def benefit_credential(
    key, *, program="food", n=1, hue="169", discount_percent=None, plan_cost=750.0,
    monthly_payment=None, subject_id=SUBJECT_ID,
) -> tuple[str, str]:
    credential_id = f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, f'apply-test-benefit-{program}-{n}')}"
    subject = {"id": subject_id, "program": program}
    if discount_percent is not None:
        subject["discountPercent"] = discount_percent
        subject["planCost"] = {"type": "MonetaryAmount", "value": plan_cost, "currency": "USD"}
    if monthly_payment is not None:
        subject["monthlyPayment"] = {"type": "MonetaryAmount", "value": monthly_payment, "currency": "USD"}
    payload = {
        "@context": ["https://www.w3.org/ns/credentials/v2"],
        "id": credential_id,
        "type": ["VerifiableCredential", "BenefitCredential"],
        "issuer": {"id": BENEFITS_ISSUER_ID, "name": "Benefit Agency"},
        "validFrom": "2026-09-01T00:00:00Z",
        "validUntil": "2027-09-01T00:00:00Z",
        "credentialSubject": subject,
        "renderMethod": [{"type": "CredDemoCardColor", "color": f"oklch(0.46 0.11 {hue})"}],
    }
    token = jwt.encode(payload, key, algorithm="ES256", headers={"kid": "benefits-1", "typ": "vc+jwt"})
    return credential_id, token


def income_credential(
    key, *, n=1, employer="Pinecrest Home Care", gross=1100.0, net=955.87,
    pay_date="2026-09-15", pay_period_start="2026-09-01", pay_period_end="2026-09-15",
    subject_id=SUBJECT_ID, tamper=False,
) -> tuple[str, str]:
    credential_id = f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, f'apply-test-paystub-{n}')}"
    payload = {
        "@context": ["https://www.w3.org/ns/credentials/v2"],
        "id": credential_id,
        "type": ["VerifiableCredential", "PaystubCredential"],
        "issuer": {"id": PAYROLL_ISSUER_ID, "name": "Meridian Payroll"},
        "validFrom": f"{pay_date}T00:00:00Z",
        "credentialSubject": {
            "id": subject_id,
            "employer": {"type": "Organization", "name": employer},
            "payPeriodStart": pay_period_start,
            "payPeriodEnd": pay_period_end,
            "payDate": pay_date,
            "payFrequency": "semimonthly",
            "grossPay": {"type": "MonetaryAmount", "value": gross, "currency": "USD"},
            "netPay": {"type": "MonetaryAmount", "value": net, "currency": "USD"},
        },
        "renderMethod": [{"type": "CredDemoCardColor", "color": "oklch(0.46 0.11 255)"}],
    }
    token = jwt.encode(payload, key, algorithm="ES256", headers={"kid": "payroll-1", "typ": "vc+jwt"})
    if tamper:
        header, body, sig = token.split(".")
        claims = json.loads(jwt.utils.base64url_decode(body + "=" * (-len(body) % 4)))
        claims["credentialSubject"]["grossPay"]["value"] = 99999.0
        body = jwt.utils.base64url_encode(json.dumps(claims, separators=(",", ":")).encode()).decode()
        token = ".".join([header, body, sig])
    return credential_id, token
