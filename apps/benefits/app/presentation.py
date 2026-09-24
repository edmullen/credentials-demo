"""Verify a Verifiable Presentation for the application protocol (docs/design.md §2, §6).

A copy of Payroll's shape (app/presentation.py: `_tokens_from`, the envelope prefix), with
Benefits' own app/verify.py, plus the two checks a verifier runs that a single-credential holder
check doesn't need: check 5 ("one subject") here is that *every* presented credential's subject
agrees, not just two.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

import jwt

from app.applications import Facts, Presented
from app.eligibility import Determination, decide
from app.verify import Outcome, verify

ENVELOPE_PREFIX = "data:application/vc+jwt,"
IDENTITY_TYPE = "IdentityCredential"
INCOME_TYPE = "PaystubCredential"


def _tokens_from(vp: dict) -> list[str] | None:
    """The JWTs inside a VP's enveloped credentials, or None if the shape is wrong."""
    if not isinstance(vp, dict) or "VerifiablePresentation" not in (vp.get("type") or []):
        return None
    creds = vp.get("verifiableCredential")
    if not isinstance(creds, list) or not creds:
        return None
    tokens = []
    for c in creds:
        if not isinstance(c, dict) or c.get("type") != "EnvelopedVerifiableCredential":
            return None
        cid = c.get("id")
        if not isinstance(cid, str) or not cid.startswith(ENVELOPE_PREFIX):
            return None
        tokens.append(cid[len(ENVELOPE_PREFIX):])
    return tokens


def _peek(token: str) -> dict:
    """The payload without verifying the signature — for sorting by type and reading a name
    even from a credential that turns out not to verify (docs/design.md §6). {} if unreadable."""
    try:
        return jwt.decode(token, options={"verify_signature": False})
    except jwt.PyJWTError:
        return {}


def _kind(claims: dict) -> str:
    types = set(claims.get("type") or [])
    if IDENTITY_TYPE in types:
        return "identity"
    if INCOME_TYPE in types:
        return "income"
    return "other"


@dataclass(frozen=True)
class Decided:
    subject_id: str
    name: str
    presented: list[Presented]
    facts: Facts
    determination: Determination


def decide_application(vp: dict, trust: dict, now: datetime):
    """Returns one of:

    - `("invalid_presentation", None)` — the wrong shape (400, nothing recorded).
    - `("credential_invalid", (subject_id, name, presented))` — a credential failed checks 1-4.
    - `("subjects_differ", (subject_id, name, presented))` — the subjects don't all agree.
    - `("decided", Decided)` — ready to record, connect and (from #106) issue.

    `subject_id`/`name` are read from the identity credential's unverified claims when present,
    even on a refusal, so the admin view can still list who applied (docs/design.md §6).
    """
    tokens = _tokens_from(vp)
    if tokens is None:
        return "invalid_presentation", None

    claims_by_token = {token: _peek(token) for token in tokens}
    identity_tokens = [t for t in tokens if _kind(claims_by_token[t]) == "identity"]
    income_tokens = [t for t in tokens if _kind(claims_by_token[t]) == "income"]
    if len(identity_tokens) != 1 or not income_tokens:
        return "invalid_presentation", None
    if len(identity_tokens) + len(income_tokens) != len(tokens):
        return "invalid_presentation", None  # a credential of some other type was included

    identity_token = identity_tokens[0]
    subject = claims_by_token[identity_token].get("credentialSubject") or {}
    subject_id = subject.get("id")
    name = None
    if subject.get("givenName") or subject.get("familyName"):
        name = f"{subject.get('givenName', '')} {subject.get('familyName', '')}".strip()

    ordered_tokens = [identity_token, *income_tokens]
    presented = [
        Presented(token=t, kind=_kind(claims_by_token[t]), outcome=verify(t, trust, now).outcome)
        for t in ordered_tokens
    ]

    if any(p.outcome is not Outcome.VERIFIED for p in presented):
        return "credential_invalid", (subject_id, name, presented)

    subject_ids = {claims_by_token[t].get("credentialSubject", {}).get("id") for t in ordered_tokens}
    if len(subject_ids) != 1:
        return "subjects_differ", (subject_id, name, presented)

    address = subject.get("address") or {}
    region = address.get("addressRegion")
    county = address.get("county")

    paystub_facts = []
    gross_pays = []
    for token in income_tokens:
        income_subject = claims_by_token[token].get("credentialSubject") or {}
        gross = income_subject.get("grossPay") or {}
        gross_pays.append(Decimal(str(gross.get("value", 0))))
        paystub_facts.append(
            {
                "employer": (income_subject.get("employer") or {}).get("name"),
                "pay_date": income_subject.get("payDate"),
                "gross_pay": gross.get("value"),
            }
        )

    determination = decide(region, county, gross_pays)
    facts = Facts(region=region, county=county, paystubs=paystub_facts)
    return "decided", Decided(
        subject_id=subject_id, name=name, presented=presented, facts=facts, determination=determination
    )
