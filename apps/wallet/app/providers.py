"""Employers, payroll providers and government services (docs/design.md §4, §9.1).

`MERIDIAN_PAYROLL_URL` and `BENEFIT_AGENCY_URL` override those providers' URLs for a local
run — read here, in the one place that matters, so nothing else needs to know the env var names.
"""

import json
import os
from functools import lru_cache

from app.people import DATA_DIR

URL_OVERRIDES = {"meridian": "MERIDIAN_PAYROLL_URL", "benefits": "BENEFIT_AGENCY_URL"}


@lru_cache
def all_employers() -> tuple[dict, ...]:
    """The 15 employers, `id`/`name`/`industry`/`city`, in file order."""
    return tuple(json.loads((DATA_DIR / "employers.json").read_text()))


def get_employer(employer_id: str) -> dict | None:
    return next((e for e in all_employers() if e["id"] == employer_id), None)


@lru_cache
def all_providers() -> dict[str, dict]:
    """Provider id -> `kind` ("payroll" | "service"), `name`, `url`, `employers` (the ids it
    pays — empty for a service)."""
    providers = json.loads((DATA_DIR / "providers.json").read_text())
    for provider_id, env_var in URL_OVERRIDES.items():
        override = os.environ.get(env_var)
        if override and provider_id in providers:
            providers[provider_id]["url"] = override
    return providers


def get_provider(provider_id: str) -> dict | None:
    return all_providers().get(provider_id)


def provider_for_employer(employer_id: str) -> str | None:
    """Which provider pays this employer, or None if it's under none."""
    return next(
        (
            pid for pid, p in all_providers().items()
            if p["kind"] == "payroll" and employer_id in p["employers"]
        ),
        None,
    )


def all_services() -> list[tuple[str, dict]]:
    """(id, provider) for every government service, in file order."""
    return [(pid, p) for pid, p in all_providers().items() if p["kind"] == "service"]
