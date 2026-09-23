from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app import connections
from app.main import app

client = TestClient(app)


def test_connections_empty_state() -> None:
    body = client.get("/p/p01/connections").text
    assert '<h1 class="intro__title">Connections</h1>' in body
    assert "You have no connections yet." in body
    assert "connlist" not in body


def test_connections_shows_the_connected_wallet() -> None:
    connections.connect("p01", "State of New Jersey", datetime(2026, 9, 22, 18, 14, tzinfo=UTC))
    body = client.get("/p/p01/connections").text
    assert "Your wallet" in body
    assert "Identity verified with the State of New Jersey &middot; since 22 Sep 2026, 2:14 PM" in body
    assert '<span class="badge badge--verified">' in body


def test_activity_empty_state() -> None:
    body = client.get("/p/p01/activity").text
    assert "Nothing has happened on your account yet." in body
    assert 'class="log__item"' not in body


def test_activity_shows_a_logged_connection() -> None:
    connections.log("p01", "verified", "New connection from your wallet established", datetime(2026, 9, 22, 18, 14, tzinfo=UTC))
    body = client.get("/p/p01/activity").text
    assert '<span class="log__dot log__dot--verified"' in body
    assert "New connection from your wallet established" in body


def test_nav_marks_connections_and_activity_current() -> None:
    body = client.get("/p/p01/connections").text
    assert 'href="/p/p01/connections" aria-current="page">Connections</a>' in body
    body = client.get("/p/p01/activity").text
    assert 'href="/p/p01/activity" aria-current="page">Activity</a>' in body


def test_paystubs_page_has_no_wallet_card() -> None:
    body = client.get("/p/p01/paystubs").text
    assert "Send your pay to your wallet" not in body
    assert "Coming soon" not in body


def test_switcher_honours_from_for_all_three_screens() -> None:
    for screen in ("paystubs", "connections", "activity"):
        body = client.get(f"/p/p01/switch?from={screen}").text
        assert f"Back to {screen}" in body
        assert f'href="/p/p22/{screen}"' in body


def test_switcher_falls_back_to_paystubs_for_an_unknown_from() -> None:
    body = client.get("/p/p01/switch?from=nonsense").text
    assert "Back to paystubs" in body
