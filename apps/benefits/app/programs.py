"""Program display data (docs/design.md §5, §7): code, name, landing phrase, order and hue,
shared by the landing page, the nav, the program pages, and (from #106) credential issuance."""

import json
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


@lru_cache
def all_programs() -> tuple[dict, ...]:
    """The five programs, in program order (docs/design.md §2: food, energy, housing, health,
    dividend)."""
    rows = json.loads((DATA_DIR / "programs.json").read_text())
    return tuple(sorted(rows, key=lambda r: r["order"]))


def get_program(code: str) -> dict | None:
    return next((p for p in all_programs() if p["code"] == code), None)
