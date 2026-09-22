"""Paystubs and employers, grouped per person.

Nothing here reads `jobs` — employment has one home in Payroll's data, the paystubs
themselves (design.md §2, §11 item 6).
"""

import json
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


@lru_cache
def _employers() -> dict[str, dict]:
    rows = json.loads((DATA_DIR / "employers.json").read_text())
    return {row["id"]: row for row in rows}


@lru_cache
def _paystubs() -> tuple[dict, ...]:
    return tuple(json.loads((DATA_DIR / "paystubs.json").read_text()))


def employers_for(person_id: str) -> list[dict]:
    """That person's employers, each with its paystubs.

    Grouped by employerId in the order the person's stubs first mention each employer (the
    source's jobs order), newest pay date first within a group. Drives both the landing
    page's sections and the switcher's employers line (design.md §4).
    """
    stubs = [s for s in _paystubs() if s["personId"] == person_id]
    order: list[str] = []
    for s in stubs:
        if s["employerId"] not in order:
            order.append(s["employerId"])

    groups = []
    for employer_id in order:
        employer_stubs = sorted(
            (s for s in stubs if s["employerId"] == employer_id),
            key=lambda s: s["payDate"],
            reverse=True,
        )
        employer = _employers()[employer_id]
        groups.append(
            {
                "employer_id": employer_id,
                "employer_name": employer["name"],
                "city": employer["city"],
                "title": employer_stubs[0]["title"],
                "stubs": employer_stubs,
            }
        )
    return groups
