"""A person's credentials, verified on every request.

Nothing is stored: the committed JWTs are read, checked against the trust list and turned into
what a screen shows. The claims are displayed as received, so a tampered credential shows what
it says, with a badge that says not to believe it.
"""

import json
from dataclasses import dataclass
from functools import lru_cache

from app import clock
from app.display import issuer_phrase, long_date, short_date, state_name
from app.outcomes import NO_CREDENTIAL, PRESENTATIONS, Presentation, message_for
from app.people import DATA_DIR
from app.verify import Outcome, verify

# Category comes from `type`, not from a claim (credential-model §3, decision 2).
CATEGORIES = {"IdentityCredential": "Identity", "PaystubCredential": "Income", "BenefitCredential": "Benefits"}
URN_PREFIX = "urn:uuid:"


@lru_cache
def _committed() -> tuple[dict[str, list[str]], dict]:
    credentials = json.loads((DATA_DIR / "credentials.json").read_text())
    trust = json.loads((DATA_DIR / "trust.json").read_text())
    return credentials, trust


@dataclass(frozen=True)
class CredentialView:
    id: str  # the credential's uuid without urn:uuid:, as used in URLs
    token: str
    outcome: Outcome
    claims: dict
    kid: str | None
    category: str

    @property
    def presentation(self) -> Presentation:
        return PRESENTATIONS[self.outcome]

    @property
    def subject(self) -> dict:
        return self.claims.get("credentialSubject") or {}

    @property
    def address(self) -> dict:
        return self.subject.get("address") or {}

    @property
    def issuer_name(self) -> str:
        return (self.claims.get("issuer") or {}).get("name", "")

    @property
    def issuer_id(self) -> str:
        return (self.claims.get("issuer") or {}).get("id", "")

    @property
    def issuer_phrase(self) -> str:
        return issuer_phrase(self.issuer_name)

    @property
    def types(self) -> str:
        return ", ".join(self.claims.get("type", []))

    @property
    def message(self) -> str:
        date = self.claims.get("validUntil") if self.outcome is Outcome.EXPIRED else self.claims.get("validFrom")
        return message_for(self.outcome, issuer_phrase(self.issuer_name), long_date(date))

    @property
    def city_line(self) -> str:
        a = self.address
        return f"{a.get('addressLocality', '')}, {a.get('addressRegion', '')} {a.get('postalCode', '')}".strip()

    @property
    def state_full(self) -> str:
        return state_name(self.address.get("addressRegion"))

    @property
    def birth_date(self) -> str:
        return long_date(self.subject.get("birthDate"))

    @property
    def valid_from(self) -> str:
        return long_date(self.claims.get("validFrom"))

    @property
    def valid_until(self) -> str:
        return long_date(self.claims.get("validUntil"))

    @property
    def valid_until_short(self) -> str:
        return short_date(self.claims.get("validUntil"))


def credentials_for(person_id: str) -> list[CredentialView]:
    stored, trust = _committed()
    now = clock.now()
    views = []
    for token in stored.get(person_id, []):
        result = verify(token, trust, now)
        claims = result.claims or {}
        types = [t for t in claims.get("type", []) if t in CATEGORIES]
        views.append(
            CredentialView(
                id=claims.get("id", "").removeprefix(URN_PREFIX),
                token=token,
                outcome=result.outcome,
                claims=claims,
                kid=result.kid,
                category=CATEGORIES[types[0]] if types else "Identity",
            )
        )
    return views


def find_credential(person_id: str, credential_id: str) -> CredentialView | None:
    return next((c for c in credentials_for(person_id) if c.id == credential_id), None)


def identity_status(person_id: str) -> Presentation:
    """The switcher's badge: the result of verifying the person's credential, or its absence."""
    views = credentials_for(person_id)
    return views[0].presentation if views else NO_CREDENTIAL
