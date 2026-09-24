"""Program display data (docs/design.md §9.1): code, name and order. Kept separate from
Benefits' own copy by the monorepo rule — the two are pinned to agree by a test in each app."""

import json
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


@lru_cache
def all_programs() -> tuple[dict, ...]:
    """The five programs, in program order (food, energy, housing, health, dividend)."""
    rows = json.loads((DATA_DIR / "programs.json").read_text())
    return tuple(sorted(rows, key=lambda r: r["order"]))


def get_program(code: str) -> dict | None:
    return next((p for p in all_programs() if p["code"] == code), None)
