"""Benefits' own trust list (docs/design.md §3, §6): the four states (IdentityCredential) and
Payroll (PaystubCredential) — everything a presentation to Benefits can carry."""

import json
from functools import lru_cache

from app.signing import DATA_DIR


@lru_cache
def trust_list() -> dict:
    return json.loads((DATA_DIR / "trust.json").read_text())
