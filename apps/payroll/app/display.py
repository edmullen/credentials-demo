"""Display text Payroll composes for reading (design.md §4). None of it is signed or stored —
paystubs are display only this loop.

Money is parsed with Decimal, never float, because the committed figures are exact decimal
strings.
"""

from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

# employers.json carries a city and no region, and all fifteen employers are in New Jersey
# (design/loop-3/README.md, known gap 5). One constant means a non-NJ employer is a one-line
# change rather than a search through templates.
EMPLOYER_REGION = "NJ"

# Every employer is in New Jersey (docs/design.md §6).
EASTERN = ZoneInfo("America/New_York")

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def _parse(value: str) -> date:
    return date.fromisoformat(value[:10])


def short_date(value: str) -> str:
    """'30 Sep 2026'"""
    d = _parse(value)
    return f"{d.day} {MONTHS[d.month - 1][:3]} {d.year}"


def period_short(start: str, end: str) -> str:
    """'16–30 Sep 2026'. Collapses a single month with an en dash, as the mockups have it."""
    d1, d2 = _parse(start), _parse(end)
    if d1.year == d2.year and d1.month == d2.month:
        return f"{d1.day}–{d2.day} {MONTHS[d2.month - 1][:3]} {d2.year}"
    return f"{short_date(start)} – {short_date(end)}"


def period_long(start: str, end: str) -> str:
    """'16–30 September 2026'. Same collapsing rule as period_short, full month names."""
    d1, d2 = _parse(start), _parse(end)
    if d1.year == d2.year and d1.month == d2.month:
        return f"{d1.day}–{d2.day} {MONTHS[d2.month - 1]} {d2.year}"
    return (
        f"{d1.day} {MONTHS[d1.month - 1]} {d1.year} – "
        f"{d2.day} {MONTHS[d2.month - 1]} {d2.year}"
    )


def money(value: str) -> str:
    """'$1,100.00'"""
    return f"${Decimal(value):,.2f}"


def hours(value: str) -> str:
    """'55.00'"""
    return f"{Decimal(value):.2f}"


def frequency_label(value: str) -> str:
    """'semimonthly' -> 'Semimonthly'. Same word the paystub and its credential both show
    (docs/design.md §6), from `paystubs.json`'s payFrequency rather than hard-coded."""
    return value.capitalize()


def installment(stub: dict) -> str:
    """'18 of 24' — derived from the period start, not stored (design.md §4, §11 item 4).

    Semimonthly periods run 1st–15th and 16th–last-day, giving two installments a month over
    the year's 24. Not a running total: a calendar position, so it doesn't reintroduce the
    year-to-date figure #50 defers.
    """
    d = _parse(stub["payPeriodStart"])
    n = (d.month - 1) * 2 + (1 if d.day == 1 else 2)
    return f"{n} of 24"


def employer_place(employer: dict) -> str:
    """'Trenton, NJ'"""
    return f"{employer['city']}, {EMPLOYER_REGION}"


def time_of_day(moment: datetime) -> str:
    """'2:14 PM' in America/New_York, no leading zero on the hour."""
    d = moment.astimezone(EASTERN)
    hour = int(d.strftime("%I"))
    return f"{hour}:{d.strftime('%M %p')}"


def when(moment: datetime) -> str:
    """'22 Sep 2026, 2:14 PM' in America/New_York."""
    d = moment.astimezone(EASTERN)
    return f"{d.day} {MONTHS[d.month - 1][:3]} {d.year}, {time_of_day(moment)}"


def day_heading(moment: datetime) -> str:
    """'Tuesday 22 September' in America/New_York."""
    d = moment.astimezone(EASTERN)
    return f"{DAYS[d.weekday()]} {d.day} {MONTHS[d.month - 1]}"


def issuer_phrase(name: str) -> str:
    """How a sentence refers to an issuer: 'the State of New Jersey', but 'Meridian Payroll'."""
    return f"the {name}" if name.startswith("State of ") else name
