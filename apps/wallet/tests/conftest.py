from datetime import UTC, datetime

import pytest

from app import clock, state

# A fixed "today" inside every committed credential's validity window, so no test depends on
# the date it runs.
FIXED_NOW = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: FIXED_NOW)
    return FIXED_NOW


@pytest.fixture(autouse=True)
def fresh_state():
    """Runtime state is in-memory and shared across requests (docs/design.md §2) — reset it
    between tests so one test's connections and Activity can't leak into the next."""
    state.reset_all()
    yield
    state.reset_all()
