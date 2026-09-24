"""Shared test credential builders (docs/design.md §14): throwaway-signed identity and paystub
tokens, trusted the way the real trust.json trusts the state and Payroll, so presentations in
API-level tests genuinely verify."""

import json
import uuid

import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from jwt.algorithms import ECAlgorithm

STATE_ISSUER = "did:example:state-of-new-jersey"
PAYROLL_ISSUER = "https://cred-demo-payroll.onrender.com"
SUBJECT_ID = "urn:uuid:11111111-1111-5111-8111-111111111111"


def keypair(kid: str):
    key = ec.generate_private_key(ec.SECP256R1())
    public = json.loads(ECAlgorithm.to_jwk(key.public_key()))
    public["kid"] = kid
    return key, public


def identity_token(key, kid, *, subject_id=SUBJECT_ID, region="NJ", county="Hunterdon", tamper=False):
    payload = {
        "@context": ["https://www.w3.org/ns/credentials/v2"],
        "id": f"urn:uuid:{uuid.uuid4()}",
        "type": ["VerifiableCredential", "IdentityCredential"],
        "issuer": {"id": STATE_ISSUER, "name": "State of New Jersey"},
        "validFrom": "2026-01-01T00:00:00Z",
        "validUntil": "2030-01-01T00:00:00Z",
        "credentialSubject": {
            "id": subject_id,
            "givenName": "Grace",
            "familyName": "Okafor",
            "birthDate": "1990-01-01",
            "address": {
                "type": "PostalAddress",
                "streetAddress": "1 Main St",
                "addressLocality": "Flemington",
                "county": county,
                "addressRegion": region,
                "postalCode": "08822",
            },
        },
    }
    token = jwt.encode(payload, key, algorithm="ES256", headers={"kid": kid, "typ": "vc+jwt"})
    if tamper:
        token = flip(token)
    return token


def paystub_token(key, kid, *, subject_id=SUBJECT_ID, gross=1100.0, employer="Pinecrest Home Care", tamper=False):
    payload = {
        "@context": ["https://www.w3.org/ns/credentials/v2"],
        "id": f"urn:uuid:{uuid.uuid4()}",
        "type": ["VerifiableCredential", "PaystubCredential"],
        "issuer": {"id": PAYROLL_ISSUER, "name": "Meridian Payroll"},
        "validFrom": "2026-09-15T00:00:00Z",
        "credentialSubject": {
            "id": subject_id,
            "employer": {"type": "Organization", "name": employer},
            "payPeriodStart": "2026-09-01",
            "payPeriodEnd": "2026-09-15",
            "payDate": "2026-09-15",
            "payFrequency": "semimonthly",
            "grossPay": {"type": "MonetaryAmount", "value": gross, "currency": "USD"},
            "netPay": {"type": "MonetaryAmount", "value": gross * 0.85, "currency": "USD"},
        },
    }
    token = jwt.encode(payload, key, algorithm="ES256", headers={"kid": kid, "typ": "vc+jwt"})
    if tamper:
        token = flip(token)
    return token


def flip(token: str) -> str:
    header, payload, signature = token.split(".")
    claims = json.loads(jwt.utils.base64url_decode(payload + "=" * (-len(payload) % 4)))
    claims["credentialSubject"]["grossPay"] = {"type": "MonetaryAmount", "value": 999999.0, "currency": "USD"}
    body = jwt.utils.base64url_encode(json.dumps(claims, separators=(",", ":")).encode()).decode()
    return ".".join([header, body, signature])


def vp(*tokens: str) -> dict:
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
