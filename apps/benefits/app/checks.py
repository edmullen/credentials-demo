"""What a presented credential's verification outcome looks like in the admin view
(docs/design.md §8.2). A copy of the Wallet's badge vocabulary (app/outcomes.py), since the
same five outcomes get the same demo language wherever they're shown."""

from dataclasses import dataclass

from app.verify import Outcome


@dataclass(frozen=True)
class Badge:
    label: str
    variant: str  # badge--{variant}
    detail: str  # "signature {detail}" fills the check's detail line


BADGES = {
    Outcome.VERIFIED: Badge("Verified", "verified", "signature matches {issuer}’s key"),
    Outcome.TAMPERED: Badge("Tampered", "error", "signature doesn’t match {issuer}’s key"),
    Outcome.EXPIRED: Badge("Expired", "caution", "credential has expired"),
    Outcome.NOT_YET_VALID: Badge("Not yet valid", "caution", "credential isn’t valid yet"),
    Outcome.UNRECOGNIZED_ISSUER: Badge("Unrecognized issuer", "unknown", "issuer isn’t recognized"),
}
