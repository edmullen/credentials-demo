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
    """The payload without verifying the signature — for sorting by type and reading what was
    submitted even from a credential that turns out not to verify (docs/design.md §6, §8.2:
    the admin view shows submitted data "as presented" on a refusal too). {} if unreadable."""
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


def _facts(identity_claims: dict, income_tokens: list[str], claims_by_token: dict) -> Facts:
    address = (identity_claims.get("credentialSubject") or {}).get("address") or {}
    paystubs = []
    for token in income_tokens:
        subject = claims_by_token[token].get("credentialSubject") or {}
        gross = subject.get("grossPay") or {}
        paystubs.append(
            {
                "employer": (subject.get("employer") or {}).get("name"),
                "pay_date": subject.get("payDate"),
                "gross_pay": gross.get("value"),
            }
        )
    return Facts(region=address.get("addressRegion"), county=address.get("county"), paystubs=paystubs)


@dataclass(frozen=True)
class Refused:
    subject_id: str | None
    name: str | None
    presented: list[Presented]
    same_subject: bool
    facts: Facts


@dataclass(frozen=True)
class Decided:
    subject_id: str
    name: str
    presented: list[Presented]
    same_subject: bool
    facts: Facts
    determination: Determination


def decide_application(vp: dict, trust: dict, now: datetime):
    """Returns one of:

    - `("invalid_presentation", None)` — the wrong shape (400, nothing recorded).
    - `("credential_invalid", Refused)` — a credential failed checks 1-4.
    - `("subjects_differ", Refused)` — the subjects don't all agree.
    - `("decided", Decided)` — ready to record, connect and issue.

    `subject_id`/`name`/`facts` are read from the unverified claims, even on a refusal, so the
    admin view can still show who applied and what was submitted "as presented"
    (docs/design.md §6, §8.2).
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
    identity_claims = claims_by_token[identity_token]
    subject = identity_claims.get("credentialSubject") or {}
    subject_id = subject.get("id")
    name = None
    if subject.get("givenName") or subject.get("familyName"):
        name = f"{subject.get('givenName', '')} {subject.get('familyName', '')}".strip()
    facts = _facts(identity_claims, income_tokens, claims_by_token)

    ordered_tokens = [identity_token, *income_tokens]
    presented = [
        Presented(token=t, kind=_kind(claims_by_token[t]), outcome=verify(t, trust, now).outcome)
        for t in ordered_tokens
    ]

    # Computed from the unverified claims regardless of whether checks 1-4 passed: a signature
    # doesn't have to check out for two credentials to visibly name the same (or different)
    # subject (docs/design/loop-6/benefits/determination-refused.html shows "Same subject" even
    # on a credential_invalid refusal).
    subject_ids = {claims_by_token[t].get("credentialSubject", {}).get("id") for t in ordered_tokens}
    same_subject = len(subject_ids) == 1

    if any(p.outcome is not Outcome.VERIFIED for p in presented):
        return "credential_invalid", Refused(subject_id, name, presented, same_subject, facts)

    if not same_subject:
        return "subjects_differ", Refused(subject_id, name, presented, same_subject, facts)

    gross_pays = [Decimal(str(f["gross_pay"] or 0)) for f in facts.paystubs]
    determination = decide(facts.region, facts.county, gross_pays)
    return "decided", Decided(
        subject_id=subject_id, name=name, presented=presented, same_subject=same_subject,
        facts=facts, determination=determination,
    )
