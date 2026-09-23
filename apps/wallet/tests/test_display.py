from datetime import UTC, datetime

from app.display import day_heading, time_of_day, when

# 6:14 PM UTC on 22 Sep 2026 is 2:14 PM Eastern (EDT, UTC-4).
MOMENT = datetime(2026, 9, 22, 18, 14, tzinfo=UTC)


def test_time_of_day_has_no_leading_zero() -> None:
    assert time_of_day(MOMENT) == "2:14 PM"
    morning = datetime(2026, 9, 22, 13, 5, tzinfo=UTC)  # 9:05 AM Eastern
    assert time_of_day(morning) == "9:05 AM"


def test_when() -> None:
    assert when(MOMENT) == "22 Sep 2026, 2:14 PM"


def test_day_heading() -> None:
    assert day_heading(MOMENT) == "Tuesday 22 September"


def test_numeric_date_is_zero_padded_mm_dd_yy() -> None:
    from app.display import numeric_date

    assert numeric_date("1982-03-11") == "03/11/82"
    assert numeric_date("2001-12-05T00:00:00Z") == "12/05/01"
    assert numeric_date(None) == ""
