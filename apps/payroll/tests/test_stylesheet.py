"""Payroll's cred.css is the Loop 4a handoff's file, byte for byte (docs/design.md §2, §14). The
handoff lives outside this app, so its length and hash are pinned here rather than read."""

import hashlib
from pathlib import Path

CSS = Path(__file__).resolve().parent.parent / "app" / "static" / "cred.css"

# docs/design/loop-4a/payroll/cred.css
HANDOFF_BYTES = 21686
HANDOFF_SHA256 = "f05fe18226af4241a4103403ea3fde9843ec7288b082e47835f2548e1a1c70a7"


def test_cred_css_is_the_handoff_file() -> None:
    css = CSS.read_bytes()
    assert len(css) == HANDOFF_BYTES
    assert hashlib.sha256(css).hexdigest() == HANDOFF_SHA256
