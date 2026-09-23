"""Employers and the payroll providers that pay them (docs/design.md §4).

`MERIDIAN_PAYROLL_URL` overrides Meridian's URL for a local run — read here, in the one place
that matters, so nothing else needs to know the env var's name.
"""

import json
import os
from functools import lru_cache

from app.people import DATA_DIR


@lru_cache
def all_employers() -> tuple[dict, ...]:
    """The 15 employers, `id`/`name`/`industry`/`city`, in file order."""
    return tuple(json.loads((DATA_DIR / "employers.json").read_text()))


def get_employer(employer_id: str) -> dict | None:
    return next((e for e in all_employers() if e["id"] == employer_id), None)


@lru_cache
def all_providers() -> dict[str, dict]:
    """Provider id -> `name`, `url`, `employers` (the ids it pays)."""
    providers = json.loads((DATA_DIR / "providers.json").read_text())
    override = os.environ.get("MERIDIAN_PAYROLL_URL")
    if override and "meridian" in providers:
        providers["meridian"]["url"] = override
    return providers


def get_provider(provider_id: str) -> dict | None:
    return all_providers().get(provider_id)


def provider_for_employer(employer_id: str) -> str | None:
    """Which provider pays this employer, or None if it's under none."""
    return next(
        (pid for pid, p in all_providers().items() if employer_id in p["employers"]),
        None,
    )
