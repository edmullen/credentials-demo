"""Benefits' cred.css is the Loop 6 handoff's file, byte for byte (docs/design.md §7, §15). The
handoff lives outside this app, so its length and hash are pinned here rather than read."""

import hashlib
from pathlib import Path

CSS = Path(__file__).resolve().parent.parent / "app" / "static" / "cred.css"

# docs/design/loop-6/benefits/cred.css
HANDOFF_BYTES = 27878
HANDOFF_SHA256 = "70f00c1ce60d4b187747181aa33167ab510fbbc68c4eb1cb8b8de83c6c6c8de1"


def test_cred_css_is_the_handoff_file() -> None:
    css = CSS.read_bytes()
    assert len(css) == HANDOFF_BYTES
    assert hashlib.sha256(css).hexdigest() == HANDOFF_SHA256
