from datetime import UTC, datetime

import pytest

from app import clock, connections

# An arbitrary fixed "today" — Payroll's own tests mint throwaway keys and credentials at test
# time (docs/design.md §10), so nothing here depends on the Wallet's committed validity windows.
FIXED_NOW = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: FIXED_NOW)
    return FIXED_NOW


@pytest.fixture(autouse=True)
def fresh_state():
    """Runtime state is in-memory and shared across requests (docs/design.md §7) — reset it
    between tests so one test's connections and Activity can't leak into the next."""
    connections.reset_all()
    yield
    connections.reset_all()
