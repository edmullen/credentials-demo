"""The Wallet's cred.css is the Loop 6 handoff's file, byte for byte (docs/design.md §11, §15).
The handoff lives outside this app, so its length and hash are pinned here rather than read."""

import hashlib
from pathlib import Path

CSS = Path(__file__).resolve().parent.parent / "app" / "static" / "cred.css"

# docs/design/loop-6/wallet/cred.css
HANDOFF_BYTES = 42195
HANDOFF_SHA256 = "e8f0c9fd599dff04b5be8e6dde37816da310422cb9ecfe7e7ee439a2ce8432fd"


def test_cred_css_is_the_handoff_file() -> None:
    css = CSS.read_bytes()
    assert len(css) == HANDOFF_BYTES
    assert hashlib.sha256(css).hexdigest() == HANDOFF_SHA256
