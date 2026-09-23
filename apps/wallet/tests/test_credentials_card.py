"""The credentials page: DOB on the card and the Income note's three states
(docs/design.md §6)."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app import state
from app.credentials import credentials_for
from app.main import app

client = TestClient(app)


def _note(body: str) -> str:
    start = body.index('class="category__waiting-note')
    return body[start:body.index("</section>", start)]


def test_the_card_shows_dob_under_the_name() -> None:
    body = client.get("/p/p01/credentials").text
    name = body.index('<span class="cred__name">Grace Okafor</span>')
    dob = body.index('<span class="cred__dob">DOB: 03/11/82</span>')
    assert name < dob < body.index('class="cred__address"')


def test_a_tampered_card_shows_its_dob_as_received() -> None:
    cred = credentials_for("p23")[0]
    assert f'<span class="cred__dob">DOB: {cred.birth_date_numeric}</span>' in client.get("/p/p23/credentials").text


def test_with_no_employer_the_note_offers_find_your_employer() -> None:
    note = _note(client.get("/p/p01/credentials").text)
    assert note.startswith('class="category__waiting-note category__waiting-note--action"')
    assert "Credentials from your employer&rsquo;s payroll provider will appear here once you connect." in note
    assert '<a class="btn btn--secondary" href="/p/p01/connections/employers">Find your employer</a>' in note


def test_with_an_employer_chosen_the_note_offers_finish_connecting() -> None:
    client.post("/p/p07/connections/employers", data={"employer": "beacon"})
    client.post("/p/p07/connections/employers", data={"employer": "pinecrest"})
    note = _note(client.get("/p/p07/credentials").text)
    # names the most recently added employer
    assert (
        "<p>You&rsquo;ve added Pinecrest Home Care. Connect to Meridian Payroll, and your pay will "
        "appear here as credentials.</p>"
    ) in note
    assert '<a class="btn btn--secondary" href="/p/p07/connections">Finish connecting</a>' in note
    assert "Find your employer" not in note


def test_after_a_failed_attempt_the_note_still_says_finish_connecting() -> None:
    client.post("/p/p23/connections/employers", data={"employer": "shoreway"})
    state.get_link("p23", "meridian").outcome = "credential_invalid"
    assert "Finish connecting" in _note(client.get("/p/p23/credentials").text)


def test_once_connected_the_note_has_no_button() -> None:
    client.post("/p/p01/connections/employers", data={"employer": "pinecrest"})
    state.get_link("p01", "meridian").connected_at = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)
    note = _note(client.get("/p/p01/credentials").text)
    assert note.startswith('class="category__waiting-note">You&rsquo;re connected to Meridian Payroll.')
    assert "btn" not in note


def test_no_identity_means_no_income_note() -> None:
    body = client.get("/p/p24/credentials").text
    assert "category__waiting-note" not in body
