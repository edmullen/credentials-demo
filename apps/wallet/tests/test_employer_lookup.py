from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app import state
from app.main import app

client = TestClient(app)


def test_lookup_lists_fifteen_employers_az_as_post_buttons() -> None:
    body = client.get("/p/p01/connections/employers").text
    assert body.count('class="employers__row"') == 15
    # Alphabetical: Beacon first, Shoreway last.
    assert body.index("Beacon Security Services") < body.index("Shoreway Supermarkets")
    assert 'value="pinecrest"' in body
    assert "Home health care &middot; Trenton, NJ" in body
    assert '<a class="back" href="/p/p01/connections">Connections</a>' in body


def test_an_already_added_employer_is_disabled() -> None:
    client.post("/p/p01/connections/employers", data={"employer": "pinecrest"})
    body = client.get("/p/p01/connections/employers").text
    assert 'value="pinecrest" disabled' in body
    assert '<span class="badge badge--neutral"><span class="badge__icon" aria-hidden="true">&ndash;</span>Added</span>' in body


def test_lookup_for_unknown_person_is_404() -> None:
    assert client.get("/p/p99/connections/employers").status_code == 404


def test_adding_an_employer_reaches_the_chosen_state() -> None:
    response = client.post(
        "/p/p01/connections/employers", data={"employer": "pinecrest"}, follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/p/p01/connections"
    body = client.get("/p/p01/connections").text
    assert "Pinecrest Home Care" in body
    assert '<button class="link-btn" type="submit" aria-describedby="prov-meridian">Remove</button>' in body
    assert '<button class="btn btn--block" type="button">Connect payroll</button>' in body
    assert "Find another employer" in body


def test_adding_an_employer_logs_one_activity_entry() -> None:
    client.post("/p/p01/connections/employers", data={"employer": "pinecrest"})
    body = client.get("/p/p01/activity").text
    assert "Pinecrest Home Care added, paid through Meridian Payroll" in body


def test_adding_the_same_employer_twice_leaves_one_activity_entry() -> None:
    client.post("/p/p01/connections/employers", data={"employer": "pinecrest"})
    client.post("/p/p01/connections/employers", data={"employer": "pinecrest"})
    body = client.get("/p/p01/activity").text
    assert body.count("Pinecrest Home Care added") == 1


def test_adding_an_unknown_employer_is_404() -> None:
    response = client.post("/p/p01/connections/employers", data={"employer": "no-such-employer"})
    assert response.status_code == 404


def test_employers_list_alphabetically_in_the_panel() -> None:
    client.post("/p/p08/connections/employers", data={"employer": "shoreway"})
    client.post("/p/p08/connections/employers", data={"employer": "brightpath"})
    body = client.get("/p/p08/connections").text
    assert body.index("Brightpath Early Learning") < body.index("Shoreway Supermarkets")


def test_remove_before_connecting_empties_the_page_and_logs() -> None:
    client.post("/p/p01/connections/employers", data={"employer": "harborline"})
    response = client.post("/p/p01/connections/meridian/remove", follow_redirects=False)
    assert response.status_code == 303
    body = client.get("/p/p01/connections").text
    assert 'class="empty"' in body
    activity = client.get("/p/p01/activity").text
    assert "Meridian Payroll removed, with Harborline Logistics" in activity


def test_disconnect_after_connecting_logs_disconnected() -> None:
    state.add_employer("p01", "meridian", "pinecrest")
    state.get_link("p01", "meridian").connected_at = datetime(2026, 9, 22, 18, 14, tzinfo=UTC)
    client.post("/p/p01/connections/meridian/remove")
    activity = client.get("/p/p01/activity").text
    assert "Disconnected from Meridian Payroll" in activity
    assert "removed, with" not in activity


def test_remove_unknown_provider_is_404() -> None:
    assert client.post("/p/p01/connections/no-such-provider/remove").status_code == 404
