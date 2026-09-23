from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app import state
from app.main import app

client = TestClient(app)


def test_events_group_by_day_newest_day_first_newest_first_within_day() -> None:
    state.log("p01", "neutral", "day one, earlier", datetime(2026, 9, 21, 18, 0, tzinfo=UTC))
    state.log("p01", "neutral", "day one, later", datetime(2026, 9, 21, 19, 0, tzinfo=UTC))
    state.log("p01", "verified", "day two", datetime(2026, 9, 22, 18, 0, tzinfo=UTC))
    body = client.get("/p/p01/activity").text
    assert body.index("Tuesday 22 September") < body.index("Monday 21 September")
    assert body.index("day two") < body.index("day one, later") < body.index("day one, earlier")


def test_dot_variants_render() -> None:
    at = datetime(2026, 9, 22, 18, 0, tzinfo=UTC)
    for dot in ("neutral", "verified", "caution", "error"):
        state.log("p01", dot, f"a {dot} event", at)
    body = client.get("/p/p01/activity").text
    for dot in ("neutral", "verified", "caution", "error"):
        assert f'class="log__dot log__dot--{dot}"' in body
