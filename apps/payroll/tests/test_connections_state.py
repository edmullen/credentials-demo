from datetime import UTC, datetime, timedelta

from app import connections

NOW = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)


def test_a_request_can_be_answered_once() -> None:
    request_id = connections.create_request(["pinecrest"], NOW)
    assert connections.pop_request(request_id, NOW) is not None
    assert connections.pop_request(request_id, NOW) is None


def test_a_request_older_than_fifteen_minutes_is_gone() -> None:
    request_id = connections.create_request(["pinecrest"], NOW)
    later = NOW + timedelta(minutes=15, seconds=1)
    assert connections.pop_request(request_id, later) is None


def test_an_unknown_request_id_is_none() -> None:
    assert connections.pop_request("no-such-id", NOW) is None


def test_connecting_again_overwrites_the_record() -> None:
    connections.connect("p01", "State of New Jersey", NOW)
    later = NOW + timedelta(days=1)
    connections.connect("p01", "State of New Jersey", later)
    assert connections.get_connection("p01").connected_at == later


def test_events_are_isolated_per_person() -> None:
    connections.log("p01", "verified", "connected", NOW)
    assert len(connections.events_for("p01")) == 1
    assert connections.events_for("p02") == []
