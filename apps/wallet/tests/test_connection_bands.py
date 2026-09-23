from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app import state
from app.main import app

client = TestClient(app)

CONNECTED_AT = datetime(2026, 9, 22, 18, 14, tzinfo=UTC)  # 2:14 PM Eastern


def test_connected_band() -> None:
    state.add_employer("p01", "meridian", "pinecrest")
    state.get_link("p01", "meridian").connected_at = CONNECTED_AT
    body = client.get("/p/p01/connections").text
    assert '<span class="badge badge--verified"><span class="badge__icon" aria-hidden="true">&#10003;</span>Connected</span>' in body
    assert "Connected since 22 Sep 2026, 2:14 PM. Meridian Payroll can send you credentials for every employer below." in body
    assert '<button class="link-btn" type="submit" aria-describedby="prov-meridian">Disconnect</button>' in body
    assert "Connect payroll" not in body


def test_arrived_line_shows_once_then_is_gone() -> None:
    link = state.add_employer("p01", "meridian", "pinecrest")
    link.connected_at = CONNECTED_AT
    link.arrived = 2
    first = client.get("/p/p01/connections").text
    assert "2 income credentials received. <a href=\"/p/p01/credentials\">View credentials</a>" in first
    second = client.get("/p/p01/connections").text
    assert "income credentials received" not in second


def test_no_arrival_line_when_nothing_arrived() -> None:
    state.add_employer("p01", "meridian", "pinecrest")
    state.get_link("p01", "meridian").connected_at = CONNECTED_AT
    assert "income credential" not in client.get("/p/p01/connections").text


def test_connected_lists_employers_az_p08_style() -> None:
    link = state.add_employer("p08", "meridian", "shoreway")
    state.add_employer("p08", "meridian", "ridgeline")
    state.add_employer("p08", "meridian", "brightpath")
    link.connected_at = CONNECTED_AT
    body = client.get("/p/p08/connections").text
    a = body.index("Brightpath Early Learning")
    b = body.index("Ridgeline Home &amp; Hardware")
    c = body.index("Shoreway Supermarkets")
    assert a < b < c


def test_credential_invalid_band_without_tampered_link() -> None:
    link = state.add_employer("p01", "meridian", "shoreway")
    link.outcome = "credential_invalid"
    body = client.get("/p/p01/connections").text
    assert '<span class="badge badge--error"><span class="badge__icon" aria-hidden="true">&#10005;</span>Not connected</span>' in body
    assert "Meridian Payroll couldn’t verify your identity credential." in body
    assert "View your credential" not in body
    assert '<button class="btn btn--block" type="submit">Try again</button>' in body
    assert '<button class="link-btn" type="submit" aria-describedby="prov-meridian">Remove</button>' in body


def test_credential_invalid_band_with_tampered_link() -> None:
    # p23 (Carmen Diaz) holds a Tampered identity credential (docs/design.md §6).
    from app.credentials import credentials_for

    cred = credentials_for("p23")[0]
    link = state.add_employer("p23", "meridian", "shoreway")
    link.outcome = "credential_invalid"
    link.shared_credential_id = cred.id
    body = client.get("/p/p23/connections").text
    assert (
        f'<p>It has been changed since it was issued. <a href="/p/p23/credentials/{cred.id}">'
        "View your credential</a></p>" in body
    )


def test_not_an_employee_band() -> None:
    link = state.add_employer("p01", "meridian", "harborline")
    link.outcome = "not_an_employee"
    body = client.get("/p/p01/connections").text
    assert '<span class="badge badge--caution"><span class="badge__icon" aria-hidden="true">!</span>Not connected</span>' in body
    assert "Meridian Payroll doesn’t have an employee record that matches you." in body
    assert (
        "Check that you chose the right employer. If not, remove Meridian Payroll and find "
        "your employer again." in body
    )


def test_no_response_band() -> None:
    link = state.add_employer("p01", "meridian", "pinecrest")
    link.outcome = "no_response"
    body = client.get("/p/p01/connections").text
    assert '<span class="badge badge--caution"><span class="badge__icon" aria-hidden="true">!</span>Not connected</span>' in body
    assert "Meridian Payroll didn’t respond." in body
    assert "Try again in a minute." in body


def test_credentials_home_income_note_reflects_connection() -> None:
    not_connected = client.get("/p/p01/credentials").text
    assert "Credentials from your employer&rsquo;s payroll provider will appear here once you connect." in not_connected

    link = state.add_employer("p01", "meridian", "pinecrest")
    link.connected_at = CONNECTED_AT
    connected = client.get("/p/p01/credentials").text
    assert (
        "You&rsquo;re connected to Meridian Payroll. Your pay will appear here as credentials "
        "as soon as they arrive." in connected
    )
