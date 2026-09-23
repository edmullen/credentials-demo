"""The Wallet's cred.css is the Loop 4a handoff's file, byte for byte, plus a short build block
(docs/design.md §2). The handoff lives outside this app, so its length and hash are pinned here
rather than read."""

import hashlib
from pathlib import Path

CSS = Path(__file__).resolve().parent.parent / "app" / "static" / "cred.css"

# docs/design/loop-4a/wallet/cred.css
HANDOFF_BYTES = 30902
HANDOFF_SHA256 = "4349e796ea6374d38902171a60df49633b4529426824ab98cb462e1ed1dc06d6"


def test_cred_css_starts_with_the_handoff_file() -> None:
    css = CSS.read_bytes()
    assert hashlib.sha256(css[:HANDOFF_BYTES]).hexdigest() == HANDOFF_SHA256


def test_only_the_build_block_follows_it() -> None:
    rest = CSS.read_bytes()[HANDOFF_BYTES:].decode()
    assert "Loop 4a build additions" in rest
    assert ".panel__status--plain .badge--caution" in rest
    assert ".panel__status--plain .badge--unknown" in rest
