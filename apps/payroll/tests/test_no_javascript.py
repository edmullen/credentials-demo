from fastapi.testclient import TestClient

from app import connections
from app.main import app

client = TestClient(app)

PAGES = [
    "/",
    "/p/p01/paystubs",
    "/p/p01/paystubs/76281fa6-3de4-5e89-be7e-462a46baaa11",
    "/p/p01/connections",
    "/p/p01/activity",
    "/p/p01/switch",
]


def test_no_script_anywhere_in_payroll() -> None:
    for page in PAGES:
        body = client.get(page).text
        assert "<script" not in body, page


def test_no_script_on_the_connected_state_either() -> None:
    from datetime import UTC, datetime

    connections.connect("p01", "State of New Jersey", datetime(2026, 9, 22, tzinfo=UTC))
    connections.log("p01", "verified", "New connection from your wallet established", datetime(2026, 9, 22, tzinfo=UTC))
    assert "<script" not in client.get("/p/p01/connections").text
    assert "<script" not in client.get("/p/p01/activity").text
