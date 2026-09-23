"""The credentials page: DOB on the card and Find your employer in the Income note
(docs/design.md §6)."""

from fastapi.testclient import TestClient

from app.credentials import credentials_for
from app.main import app

client = TestClient(app)

FIND = '<a class="btn" href="/p/p01/connections/employers">Find your employer</a>'


def test_the_card_shows_dob_under_the_name() -> None:
    body = client.get("/p/p01/credentials").text
    name = body.index('<span class="cred__name">Grace Okafor</span>')
    dob = body.index('<span class="cred__dob">DOB: 03/11/82</span>')
    address = body.index('class="cred__address"')
    assert name < dob < address


def test_a_tampered_card_shows_its_dob_as_received() -> None:
    cred = credentials_for("p23")[0]
    body = client.get("/p/p23/credentials").text
    assert f'<span class="cred__dob">DOB: {cred.birth_date_numeric}</span>' in body


def test_find_your_employer_shows_in_the_income_note_until_an_employer_is_added() -> None:
    body = client.get("/p/p01/credentials").text
    note = body[body.index('<div class="category__waiting-note">'):]
    assert FIND in note[:note.index("</div>")]
    client.post("/p/p01/connections/employers", data={"employer": "pinecrest"})
    assert FIND not in client.get("/p/p01/credentials").text


def test_no_identity_means_no_income_note_and_no_button() -> None:
    body = client.get("/p/p24/credentials").text
    assert "category__waiting-note" not in body
    assert "Find your employer" not in body
