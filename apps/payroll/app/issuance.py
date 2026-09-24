"""Builds and signs Payroll's income credentials (docs/design.md §4-5).

One credential per paystub, built fresh whenever it's asked for — by call 3 (POST
/api/credentials) or by the paystub page's panel. Nothing is stored: the credential id is
name-based, so a restart can't cause duplicates, and ES256 signatures differ each call even
though the id and every claim stay the same.
"""

import uuid
from decimal import Decimal

import jwt

from app import signing

# A namespace constant of Payroll's own, distinct from the generator's (tools/generate_
# credentials.py) — no app imports across the monorepo boundary. Different from the paystub's
# own id, as Ed wanted: the two are separate records, but always the same for the same paystub.
PAYSTUB_CREDENTIAL_NAMESPACE = uuid.UUID("e7a1c2d4-9f3b-5a67-8c12-4d9e6f2b8a71")

ISSUER_COLOR = "oklch(0.46 0.11 255)"  # Payroll's own --accent recipe at hue 255 (§4)


def credential_id(stub: dict) -> str:
    return f"urn:uuid:{uuid.uuid5(PAYSTUB_CREDENTIAL_NAMESPACE, stub['id'])}"


def _amount(value: str) -> dict:
    return {"type": "MonetaryAmount", "value": float(Decimal(value)), "currency": "USD"}


def credential_payload(stub: dict) -> dict:
    """The unsigned VC payload for one paystub, exactly credential-model §3's shape."""
    return {
        "@context": ["https://www.w3.org/ns/credentials/v2"],
        "id": credential_id(stub),
        "type": ["VerifiableCredential", "PaystubCredential"],
        "issuer": {"id": signing.issuer_id(), "name": "Meridian Payroll"},
        "validFrom": f"{stub['payDate']}T00:00:00Z",
        "credentialSubject": {
            "id": stub["subjectId"],
            "employer": {"type": "Organization", "name": stub["employerName"]},
            "payPeriodStart": stub["payPeriodStart"],
            "payPeriodEnd": stub["payPeriodEnd"],
            "payDate": stub["payDate"],
            "payFrequency": stub["payFrequency"],
            "grossPay": _amount(stub["grossPay"]),
            "netPay": _amount(stub["netPay"]),
        },
        "renderMethod": [{"type": "CredDemoCardColor", "color": ISSUER_COLOR}],
    }


def sign(payload: dict) -> str:
    # The payload *is* the credential: no `vc` wrapper, no iss/sub/exp (credential-model §3-4).
    return jwt.encode(payload, signing.key(), algorithm="ES256", headers={"kid": signing.kid(), "typ": "vc+jwt"})


def issue(stub: dict) -> str:
    return sign(credential_payload(stub))


def credential_view(stub: dict, view: dict) -> dict:
    """The signed credential, formatted for the paystub page's panel (docs/design.md §6).

    `view` is that same paystub's own `paystub_view()` output: reusing its already-formatted
    `period_short`, `pay_date`, `frequency`, `gross` and `net` is what makes the two records
    visibly agree, since both panels then show output from the very same helper calls.
    """
    payload = credential_payload(stub)
    # Without a valid key the panel still shows every claim; only the signed JWT is left out
    # (docs/design.md §3).
    token = sign(payload) if signing.status().ok else None
    subject = payload["credentialSubject"]
    return {
        "id": payload["id"],
        "employer_name": subject["employer"]["name"],
        "period_short": view["period_short"],
        "pay_date": view["pay_date"],
        "frequency": view["frequency"],
        "gross": view["gross"],
        "net": view["net"],
        "issuer_id": payload["issuer"]["id"],
        "type_line": ", ".join(payload["type"]),
        "valid_from": payload["validFrom"],
        "jwt": token,
    }
