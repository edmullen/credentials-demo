"""What each verification outcome looks like on screen.

One table drives the badge variant, its glyph, the status band and the sentence
(docs/design.md §4). Variants and glyphs are the Loop 2 handoff's; the copy is the handoff's
revision of docs/credential-model.md §5. The Wallet composes every message — none comes from a
credential.
"""

from dataclasses import dataclass

from app.verify import Outcome


@dataclass(frozen=True)
class Presentation:
    label: str
    variant: str  # badge--{variant} and panel__status--{variant}
    glyph: str  # an HTML entity, rendered with |safe
    message: str  # {issuer} and {date} are filled in by message_for


PRESENTATIONS = {
    Outcome.VERIFIED: Presentation(
        "Verified", "verified", "&#10003;",
        "Nothing in this credential has changed since {issuer} issued it.",
    ),
    Outcome.TAMPERED: Presentation(
        "Tampered", "error", "&#10005;",
        "Something in this credential was changed after {issuer} issued it, so it can’t be "
        "trusted or used. Ask {issuer} for a new one.",
    ),
    Outcome.EXPIRED: Presentation(
        "Expired", "caution", "!",
        "This credential expired on {date}. Ask {issuer} for a new one.",
    ),
    Outcome.NOT_YET_VALID: Presentation(
        "Not yet valid", "caution", "!",
        "This credential can’t be used until {date}.",
    ),
    Outcome.UNRECOGNIZED_ISSUER: Presentation(
        "Unrecognized issuer", "unknown", "?",
        "This wallet doesn’t recognize {issuer}, so it can’t check whether this "
        "credential is genuine.",
    ),
}

# Not an outcome: the switcher's row for a person who holds nothing — the absence of a
# credential, not the result of checking one.
NO_CREDENTIAL = Presentation("No credential", "neutral", "&ndash;", "")


def message_for(outcome: Outcome, issuer: str, date: str = "") -> str:
    return PRESENTATIONS[outcome].message.format(issuer=issuer, date=date)
