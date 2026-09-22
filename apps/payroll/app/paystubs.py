"""Paystubs and employers, grouped per person.

Nothing here reads `jobs` — employment has one home in Payroll's data, the paystubs
themselves (design.md §2, §11 item 6).
"""

import json
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from app.display import employer_place, hours, installment, money, period_long, period_short, short_date

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


def find_paystub(person_id: str, paystub_id: str) -> dict | None:
    """None when the id isn't that person's — a mismatch is a 404, not a redirect."""
    full_id = f"urn:uuid:{paystub_id}"
    return next(
        (s for s in _paystubs() if s["personId"] == person_id and s["id"] == full_id), None
    )


def landing_groups(person_id: str) -> list[dict]:
    """employers_for(), formatted for the account landing page's .category sections."""
    return [
        {
            "employer_id": group["employer_id"],
            "employer_name": group["employer_name"],
            "sub": f"{group['title']} · {employer_place({'city': group['city']})}",
            "rows": [
                {
                    "id": stub["id"].removeprefix("urn:uuid:"),
                    "date": short_date(stub["payDate"]),
                    "period": period_short(stub["payPeriodStart"], stub["payPeriodEnd"]),
                }
                for stub in group["stubs"]
            ],
        }
        for group in employers_for(person_id)
    ]


def paystub_view(person_id: str, paystub_id: str) -> dict | None:
    """A single paystub, formatted for the detail page. None when the id isn't this person's."""
    stub = find_paystub(person_id, paystub_id)
    if stub is None:
        return None
    employer = _employers()[stub["employerId"]]
    deductions = stub["deductions"]
    total_deductions = sum(Decimal(v) for v in deductions.values())
    is_hourly = stub["payType"] == "hourly"
    return {
        "employer_name": employer["name"],
        "employer_place": employer_place(employer),
        "title": stub["title"],
        "period": period_long(stub["payPeriodStart"], stub["payPeriodEnd"]),
        "period_short": period_short(stub["payPeriodStart"], stub["payPeriodEnd"]),
        "pay_date": short_date(stub["payDate"]),
        "is_hourly": is_hourly,
        "earnings_label": "Regular" if is_hourly else "Salary",
        "rate": money(stub["hourlyRate"] if is_hourly else stub["annualSalary"]),
        "quantity": hours(stub["hours"]) if is_hourly else installment(stub),
        "gross": money(stub["grossPay"]),
        "deductions": [
            ("Federal income tax", money(deductions["federalIncomeTax"])),
            ("Social Security", money(deductions["socialSecurity"])),
            ("Medicare", money(deductions["medicare"])),
            ("State income tax", money(deductions["stateIncomeTax"])),
        ],
        "total_deductions": money(total_deductions),
        "net": money(stub["netPay"]),
    }
