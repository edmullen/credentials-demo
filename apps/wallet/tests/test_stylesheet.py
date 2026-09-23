"""The Wallet's cred.css is the Loop 5 handoff's file, byte for byte (docs/design.md §8, §15).
The handoff lives outside this app, so its length and hash are pinned here rather than read."""

import hashlib
from pathlib import Path

CSS = Path(__file__).resolve().parent.parent / "app" / "static" / "cred.css"

# docs/design/loop-5/wallet/cred.css
HANDOFF_BYTES = 35699
HANDOFF_SHA256 = "f69cd78a10c01908a79de9866e616e187c965afda3dab129b8568b11c6ced060"


def test_cred_css_is_the_handoff_file() -> None:
    css = CSS.read_bytes()
    assert len(css) == HANDOFF_BYTES
    assert hashlib.sha256(css).hexdigest() == HANDOFF_SHA256
