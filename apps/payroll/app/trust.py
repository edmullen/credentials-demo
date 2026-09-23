"""Payroll's own trust list (docs/design.md §7): the four states, trusted for IdentityCredential."""

import json
from functools import lru_cache

from app.people import DATA_DIR


@lru_cache
def trust_list() -> dict:
    return json.loads((DATA_DIR / "trust.json").read_text())
