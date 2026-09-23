"""Verify a Verifiable Presentation for the connection protocol (docs/design.md §3, §7).

Payroll's own copy of the checks credential-model.md §2 defines (via app/verify.py), plus
check 5 ("one subject") and check 6 ("known subject", scoped to the named employers) — the
checks a *verifier* runs on an incoming presentation, distinct from app/verify.py's four checks
a holder's own wallet runs on a single credential it holds.
"""

from datetime import datetime

from app.paystubs import employer_ids_for
from app.people import find_by_subject
from app.verify import Outcome, verify

ENVELOPE_PREFIX = "data:application/vc+jwt,"
REQUESTED_TYPE = "IdentityCredential"


def _tokens_from(vp: dict) -> list[str] | None:
    """The JWTs inside a VP's enveloped credentials, or None if the shape is wrong."""
    if not isinstance(vp, dict) or "VerifiablePresentation" not in (vp.get("type") or []):
        return None
    creds = vp.get("verifiableCredential")
    if not isinstance(creds, list):
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


def known_subject(subject_id: str, employer_ids: list[str]) -> dict | None:
    """The employee this subject is, if they have paystubs at every named employer (check 6)."""
    person = find_by_subject(subject_id)
    if person is None or not set(employer_ids).issubset(employer_ids_for(person["id"])):
        return None
    return person


def verify_presentation(
    vp: dict, employer_ids: list[str], trust: dict, now: datetime
) -> tuple[str, dict | None]:
    """Returns (outcome, {"person", "issuer_name"} | None).

    Outcome is "connected", "credential_invalid", "not_an_employee", or
    "invalid_presentation" — a shape error the route turns into a 400, not a 200 refusal.
    """
    tokens = _tokens_from(vp)
    if tokens is None or len(tokens) != 1:  # check 5: exactly one credential
        return "invalid_presentation", None

    result = verify(tokens[0], trust, now)
    if REQUESTED_TYPE not in (result.claims or {}).get("type", []):
        return "invalid_presentation", None
    if result.outcome is not Outcome.VERIFIED:  # checks 1-4
        return "credential_invalid", None

    subject_id = result.claims["credentialSubject"]["id"]
    person = known_subject(subject_id, employer_ids)  # check 6
    if person is None:
        return "not_an_employee", None
    return "connected", {"person": person, "issuer_name": result.claims["issuer"]["name"]}
