import json
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


@lru_cache
def all_people() -> tuple[dict, ...]:
    """The 25 people in p01–p25 order, each with the display fields a screen needs.

    `employerNames` is for the person switcher only, a demo aid (docs/design.md §7). Connect
    logic must never read it: whether someone works for an employer is Payroll's call.
    """
    rows = json.loads((DATA_DIR / "people.json").read_text())
    return tuple(
        {
            **row,
            "name": f"{row['givenName']} {row['familyName']}",
            "place": f"{row['locality']}, {row['region']}",
        }
        for row in rows
    )


def get_person(person_id: str) -> dict | None:
    return next((p for p in all_people() if p["id"] == person_id), None)
