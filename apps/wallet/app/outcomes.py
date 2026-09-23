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


@dataclass(frozen=True)
class ConnectionState:
    """A connection outcome's status band (docs/design.md §6): variant, glyph, label, the
    sentence(s) always shown, and the Activity dot a transition to this outcome logs with.
    `{provider}` and `{when}` are filled in by `connection_message`.
    """

    variant: str  # panel__status--{variant}
    glyph: str
    label: str
    sentences: tuple[str, ...]
    dot: str  # log__dot--{variant}


CONNECTION_STATES = {
    "connected": ConnectionState(
        "verified", "&#10003;", "Connected",
        (
            "Connected since {when}. {provider} can send you credentials for every "
            "employer below.",
        ),
        "verified",
    ),
    "credential_invalid": ConnectionState(
        "error", "&#10005;", "Not connected",
        ("{provider} couldn’t verify your identity credential.",),
        "error",
    ),
    "not_an_employee": ConnectionState(
        "caution", "!", "Not connected",
        (
            "{provider} doesn’t have an employee record that matches you.",
            "Check that you chose the right employer. If not, remove {provider} and find "
            "your employer again.",
        ),
        "caution",
    ),
    "no_response": ConnectionState(
        "caution", "!", "Not connected",
        ("{provider} didn’t respond.", "Try again in a minute."),
        "caution",
    ),
}


def connection_sentences(code: str, provider: str, when: str = "") -> list[str]:
    return [s.format(provider=provider, when=when) for s in CONNECTION_STATES[code].sentences]
