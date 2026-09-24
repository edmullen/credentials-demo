"""Display text the Wallet composes. None of it is signed by an issuer (docs/design.md §6)."""

from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

# Every employer and almost every credential is in New Jersey (docs/design.md §6).
EASTERN = ZoneInfo("America/New_York")

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
    "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon",
    "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia",
    "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def parse_date(value: str | None) -> date | None:
    """The calendar date of an ISO 8601 date or timestamp, or None if absent or unreadable."""
    try:
        return date.fromisoformat(value[:10]) if value else None
    except ValueError:
        return None


def long_date(value: str | None) -> str:
    """'2 September 1991'"""
    d = parse_date(value)
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}" if d else ""


def short_date(value: str | None) -> str:
    """'15 Jan 2030'"""
    d = parse_date(value)
    return f"{d.day} {MONTHS[d.month - 1][:3]} {d.year}" if d else ""


def numeric_date(value: str | None) -> str:
    """'03/11/82' (MM/DD/YY), the DOB line on a credentials card."""
    d = parse_date(value)
    return d.strftime("%m/%d/%y") if d else ""


def period_short(start: str, end: str) -> str:
    """'16–30 Sep 2026'. Collapses a single month with an en dash (docs/design.md §8)."""
    d1, d2 = parse_date(start), parse_date(end)
    if d1.year == d2.year and d1.month == d2.month:
        return f"{d1.day}–{d2.day} {MONTHS[d2.month - 1][:3]} {d2.year}"
    return f"{short_date(start)} – {short_date(end)}"


def period_long(start: str, end: str) -> str:
    """'1–15 September 2026'. Same collapsing rule as period_short, full month names."""
    d1, d2 = parse_date(start), parse_date(end)
    if d1.year == d2.year and d1.month == d2.month:
        return f"{d1.day}–{d2.day} {MONTHS[d2.month - 1]} {d2.year}"
    return f"{long_date(start)} – {long_date(end)}"


def month_span(dates: list[str]) -> str:
    """'September 2026' for one month held, 'Aug–Sep 2026' for a span (docs/design.md §10.4)."""
    parsed = sorted({d for d in (parse_date(v) for v in dates) if d})
    if not parsed:
        return ""
    first, last = parsed[0], parsed[-1]
    if (first.year, first.month) == (last.year, last.month):
        return f"{MONTHS[first.month - 1]} {first.year}"
    return f"{MONTHS[first.month - 1][:3]}–{MONTHS[last.month - 1][:3]} {last.year}"


def money(amount: dict) -> str:
    """A MonetaryAmount claim, '$1,100.00'. USD only, per credential-model §3 — the demo's."""
    return f"${Decimal(str(amount['value'])):,.2f}"


def frequency_label(value: str) -> str:
    """'semimonthly' -> 'Semimonthly'."""
    return value.capitalize() if value else ""


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


def join_and(items: list[str]) -> str:
    """'A', 'A and B', or 'A, B and C'."""
    if len(items) <= 1:
        return items[0] if items else ""
    return f"{', '.join(items[:-1])} and {items[-1]}"


def state_name(code: str | None) -> str:
    return STATES.get(code or "", code or "")


def issuer_phrase(name: str) -> str:
    """How a sentence refers to an issuer: 'the State of New Jersey', but 'Meridian Payroll'."""
    return f"the {name}" if name.startswith("State of ") else name
