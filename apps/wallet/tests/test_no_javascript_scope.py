"""Only the two pending pages and the Credentials page (when connected) contain a <script>,
and no page loads one from a URL (docs/design.md §9, §15 item 10)."""

from fastapi.testclient import TestClient

from app import clock, state
from app.main import app

client = TestClient(app)

PLAIN_PAGES = [
    "/p/p01/credentials",  # not connected: no script
    "/p/p01/connections",
    "/p/p01/connections/employers",
    "/p/p01/activity",
    "/p/p01/switch",
]


def test_no_script_on_ordinary_pages() -> None:
    for page in PLAIN_PAGES:
        assert "<script" not in client.get(page).text, page


def test_credentials_page_has_a_script_once_connected() -> None:
    link = state.add_employer("p01", "meridian", "pinecrest")
    link.connected_at = clock.now()
    link.connection_id = "conn-1"
    body = client.get("/p/p01/credentials").text
    assert body.count("<script") == 1
    assert "<script src" not in body


def test_check_again_works_as_a_plain_get_without_javascript() -> None:
    client.post("/p/p01/connections/employers", data={"employer": "pinecrest"})
    client.post("/p/p01/connections/meridian/connect")
    # "Check again" is an ordinary GET to the page's own URL — the no-JS path.
    response = client.get("/p/p01/connections/meridian/asking")
    assert response.status_code == 200
    assert 'action="/p/p01/connections/meridian/asking"' in response.text


def test_asking_page_has_exactly_one_script_and_no_external_source() -> None:
    client.post("/p/p01/connections/employers", data={"employer": "pinecrest"})
    client.post("/p/p01/connections/meridian/connect")
    body = client.get("/p/p01/connections/meridian/asking").text
    assert body.count("<script") == 1
    assert "<script src" not in body


def test_only_the_two_pending_pages_have_a_script() -> None:
    from app import state

    person_id = "p01"
    link = state.add_employer(person_id, "meridian", "pinecrest")
    link.request = state.PendingRequest(token="t", phase="verifying")
    body = client.get(f"/p/{person_id}/connections/meridian/verifying").text
    assert body.count("<script") == 1
    assert "<script src" not in body
