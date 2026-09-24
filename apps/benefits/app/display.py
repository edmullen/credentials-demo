from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

# Every state and employer in the sample data is in the Eastern time zone (Payroll's
# app/display.py §6 makes the same choice for its own admin-facing dates).
EASTERN = ZoneInfo("America/New_York")

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def money(value) -> str:
    """'$1,234.56'."""
    return f"${Decimal(value):,.2f}"


def money_whole(value) -> str:
    """'$1,200' — for Dividend's round-dollar variables, which the handoff shows with no
    cents (docs/design/loop-6/benefits/dividend.html)."""
    return f"${Decimal(value):,.0f}"


def short_date(value: str) -> str:
    """'15 Sep 2026' from an ISO date or datetime string."""
    d = date.fromisoformat(value[:10])
    return f"{d.day} {MONTHS[d.month - 1][:3]} {d.year}"


def _time_of_day(moment: datetime, *, seconds: bool) -> str:
    d = moment.astimezone(EASTERN)
    hour = int(d.strftime("%I"))
    clock = d.strftime("%M:%S %p") if seconds else d.strftime("%M %p")
    return f"{hour}:{clock}"


def when(moment: datetime) -> str:
    """'1 Oct 2026, 2:03 PM' in America/New_York (docs/design.md §8.1)."""
    d = moment.astimezone(EASTERN)
    return f"{d.day} {MONTHS[d.month - 1][:3]} {d.year}, {_time_of_day(moment, seconds=False)}"


def when_seconds(moment: datetime) -> str:
    """'1 Oct 2026, 9:48:12 AM' — the determination page's more precise timestamp
    (docs/design/loop-6/benefits/determination-p01.html)."""
    d = moment.astimezone(EASTERN)
    return f"{d.day} {MONTHS[d.month - 1][:3]} {d.year}, {_time_of_day(moment, seconds=True)}"
