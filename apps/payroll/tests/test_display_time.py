from datetime import UTC, datetime

from app.display import day_heading, issuer_phrase, time_of_day, when

# 6:14 PM UTC on 22 Sep 2026 is 2:14 PM Eastern (EDT, UTC-4).
MOMENT = datetime(2026, 9, 22, 18, 14, tzinfo=UTC)


def test_time_of_day_has_no_leading_zero() -> None:
    assert time_of_day(MOMENT) == "2:14 PM"


def test_when() -> None:
    assert when(MOMENT) == "22 Sep 2026, 2:14 PM"


def test_day_heading() -> None:
    assert day_heading(MOMENT) == "Tuesday 22 September"


def test_issuer_phrase() -> None:
    assert issuer_phrase("State of New Jersey") == "the State of New Jersey"
    assert issuer_phrase("Meridian Payroll") == "Meridian Payroll"
