from datetime import UTC, datetime


def now() -> datetime:
    """The current time. A seam, so tests can fix the date instead of depending on today's."""
    return datetime.now(UTC)
