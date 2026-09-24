"""A person's credentials, verified on every request.

Nothing is stored: the committed JWTs are read, checked against the trust list and turned into
what a screen shows. The claims are displayed as received, so a tampered credential shows what
it says, with a badge that says not to believe it.
"""

import json
import re
from dataclasses import dataclass
from functools import lru_cache

from app import clock, state
from app.display import (
    frequency_label,
    issuer_phrase,
    long_date,
    money,
    numeric_date,
    period_long,
    period_short,
    short_date,
    state_name,
)
from app.outcomes import NO_CREDENTIAL, PRESENTATIONS, Presentation, message_for
from app.people import DATA_DIR
from app.verify import Outcome, verify

# oklch(L C H) — only H (the third number) is read (docs/design.md §4).
_ISSUER_COLOR_RE = re.compile(r"oklch\(\s*[\d.]+\s+[\d.]+\s+([\d.]+)\s*\)")

# Category comes from `type`, not from a claim (credential-model §3, decision 2).
CATEGORIES = {"IdentityCredential": "Identity", "PaystubCredential": "Income", "BenefitCredential": "Benefits"}
URN_PREFIX = "urn:uuid:"


@lru_cache
def _committed() -> tuple[dict[str, list[str]], dict]:
    credentials = json.loads((DATA_DIR / "credentials.json").read_text())
    trust = json.loads((DATA_DIR / "trust.json").read_text())
    return credentials, trust


def trust_list() -> dict:
    return _committed()[1]


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
    def birth_date_numeric(self) -> str:
        return numeric_date(self.subject.get("birthDate"))

    @property
    def valid_from(self) -> str:
        return long_date(self.claims.get("validFrom"))

    @property
    def valid_until(self) -> str:
        return long_date(self.claims.get("validUntil"))

    @property
    def valid_until_short(self) -> str:
        return short_date(self.claims.get("validUntil"))

    # --- income claims (docs/design.md §8) ---------------------------------------------------

    @property
    def employer_name(self) -> str:
        return (self.subject.get("employer") or {}).get("name", "")

    @property
    def pay_period_short(self) -> str:
        return period_short(self.subject.get("payPeriodStart"), self.subject.get("payPeriodEnd"))

    @property
    def pay_period_long(self) -> str:
        return period_long(self.subject.get("payPeriodStart"), self.subject.get("payPeriodEnd"))

    @property
    def pay_date(self) -> str:
        return long_date(self.subject.get("payDate"))

    @property
    def frequency(self) -> str:
        return frequency_label(self.subject.get("payFrequency"))

    @property
    def gross(self) -> str:
        return money(self.subject.get("grossPay") or {"value": 0})

    @property
    def net(self) -> str:
        return money(self.subject.get("netPay") or {"value": 0})

    @property
    def _render_hue(self) -> str | None:
        for entry in self.claims.get("renderMethod") or []:
            if entry.get("type") == "CredDemoCardColor":
                match = _ISSUER_COLOR_RE.match(entry.get("color", ""))
                if match:
                    return match.group(1)
        return None

    @property
    def issuer_hue(self) -> str | None:
        """The issuer's render hue for a card, or None with no entry, an unreadable color, or a
        tampered credential (docs/design.md §4). The color is a signed claim, so what makes it
        untrustworthy is a broken signature (TAMPERED) or an issuer we can't check a signature
        against at all (UNRECOGNIZED_ISSUER) — not an expired or not-yet-valid window, which
        both still carry a signature that checked out."""
        if self.outcome in (Outcome.TAMPERED, Outcome.UNRECOGNIZED_ISSUER):
            return None
        return self._render_hue

    @property
    def detail_issuer_hue(self) -> str | None:
        """The detail page's issuer bar shows the color as received, tampered or not — the
        same "shown as received, badged as untrustworthy" rule the rest of the panel follows."""
        return self._render_hue


def _view(token: str, trust: dict, now) -> CredentialView:
    result = verify(token, trust, now)
    claims = result.claims or {}
    types = [t for t in claims.get("type", []) if t in CATEGORIES]
    return CredentialView(
        id=claims.get("id", "").removeprefix(URN_PREFIX),
        token=token,
        outcome=result.outcome,
        claims=claims,
        kid=result.kid,
        category=CATEGORIES[types[0]] if types else "Identity",
    )


def credentials_for(person_id: str) -> list[CredentialView]:
    stored, trust = _committed()
    now = clock.now()
    views = [_view(token, trust, now) for token in stored.get(person_id, [])]
    # Received credentials keep Payroll's order — newest first, as they arrived (§4, §8).
    views += [_view(token, trust, now) for token in state.received_for(person_id).values()]
    return views


def find_credential(person_id: str, credential_id: str) -> CredentialView | None:
    return next((c for c in credentials_for(person_id) if c.id == credential_id), None)


def identity_status(person_id: str) -> Presentation:
    """The switcher's badge: the result of verifying the person's credential, or its absence."""
    views = credentials_for(person_id)
    return views[0].presentation if views else NO_CREDENTIAL
