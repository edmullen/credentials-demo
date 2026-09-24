"""Builds and signs Benefit Agency's benefit credentials (docs/design.md §5).

Unlike Payroll, which signs on demand because it stores nothing, Benefits signs each eligible
program's credential once, when the determination is made, and the application record keeps
the JWT — so call 3 returns the same id and signature every time (docs/design.md §6).
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

import jwt

from app import signing
from app.eligibility import ProgramResult
from app.programs import get_program


@dataclass(frozen=True)
class Issued:
    program: str
    credential_id: str
    jwt: str


def _floor_to_minute(dt: datetime) -> datetime:
    return dt.replace(second=0, microsecond=0)


def _plus_twelve_months(dt: datetime) -> datetime:
    try:
        return dt.replace(year=dt.year + 1)
    except ValueError:
        # 29 February becomes 28 February (docs/design.md §5).
        return dt.replace(year=dt.year + 1, month=2, day=28)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _amount(value) -> dict:
    return {"type": "MonetaryAmount", "value": float(value), "currency": "USD"}


def credential_payload(result: ProgramResult, subject_id: str, decided_at: datetime) -> dict:
    """The unsigned VC payload for one eligible program, exactly credential-model §3's shape."""
    valid_from = _floor_to_minute(decided_at)
    valid_until = _plus_twelve_months(valid_from)
    program = get_program(result.program)

    subject = {"id": subject_id, "program": result.program}
    if result.discount_percent is not None:
        subject["discountPercent"] = float(result.discount_percent)
        subject["planCost"] = _amount(result.plan_cost)
    if result.monthly_payment is not None:
        subject["monthlyPayment"] = _amount(result.monthly_payment)

    return {
        "@context": ["https://www.w3.org/ns/credentials/v2"],
        "id": f"urn:uuid:{uuid.uuid4()}",
        "type": ["VerifiableCredential", "BenefitCredential"],
        "issuer": {"id": signing.issuer_id(), "name": "Benefit Agency"},
        "validFrom": _iso(valid_from),
        "validUntil": _iso(valid_until),
        "credentialSubject": subject,
        "renderMethod": [
            {"type": "CredDemoCardColor", "color": f"oklch(0.46 0.11 {program['hue']})"}
        ],
    }


def sign(payload: dict) -> str:
    # The payload *is* the credential: no `vc` wrapper, no iss/sub/exp (credential-model §3-4).
    return jwt.encode(
        payload, signing.key(), algorithm="ES256", headers={"kid": signing.kid(), "typ": "vc+jwt"}
    )


def issue_eligible(programs: tuple[ProgramResult, ...], subject_id: str, decided_at: datetime) -> dict[str, Issued]:
    """One signed credential per eligible program, keyed by program code. Only call when
    signing.status().ok — a denial yields no credential, so an ineligible determination made
    without a valid key never surfaces the gap."""
    issued = {}
    for result in programs:
        if result.outcome != "eligible":
            continue
        payload = credential_payload(result, subject_id, decided_at)
        token = sign(payload)
        issued[result.program] = Issued(program=result.program, credential_id=payload["id"], jwt=token)
    return issued
