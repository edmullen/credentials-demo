"""Payroll's cred.css is the Loop 5 handoff's file, byte for byte (docs/design.md §6, §15). The
handoff lives outside this app, so its length and hash are pinned here rather than read."""

import hashlib
from pathlib import Path

CSS = Path(__file__).resolve().parent.parent / "app" / "static" / "cred.css"

# docs/design/loop-5/payroll/cred.css
HANDOFF_BYTES = 25989
HANDOFF_SHA256 = "6e2e0eb2379a161071cdaadba0bd0275cdd62593b4e234eda2bc31ebdbf511d4"


def test_cred_css_is_the_handoff_file() -> None:
    css = CSS.read_bytes()
    assert len(css) == HANDOFF_BYTES
    assert hashlib.sha256(css).hexdigest() == HANDOFF_SHA256
