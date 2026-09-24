"""Benefit Agency on the Connections page: the panel, its wording, and Remove
(docs/design.md §10.9)."""

import jwt
from fastapi.testclient import TestClient

from app import clock, state
from app.main import app

client = TestClient(app)

PERSON_ID = "p01"


def _fake_benefit_token(program: str) -> str:
    # Claims just need to be readable, per verify()'s unverified peek — the signature never
    # checks out here, which is fine: these tests only care about the category count.
    payload = {
        "id": f"urn:uuid:fake-{program}",
        "type": ["VerifiableCredential", "BenefitCredential"],
        "issuer": {"id": "https://cred-demo-benefits.onrender.com", "name": "Benefit Agency"},
        "credentialSubject": {"id": "urn:uuid:33333333-3333-5333-8333-333333333333", "program": program},
    }
    return jwt.encode(payload, "not-the-real-key-but-long-enough-for-hs256", algorithm="HS256")


def _connected_link(held_benefits: int = 0) -> state.Link:
    link = state.get_or_create_link(PERSON_ID, "benefits")
    link.connected_at = clock.now()
    link.connection_id = "conn-1"
    for i in range(held_benefits):
        state.add_received(PERSON_ID, f"urn:uuid:benefit-{i}", _fake_benefit_token(f"food{i}"))
    return link


def test_panel_shows_government_service_label() -> None:
    _connected_link()
    body = client.get(f"/p/{PERSON_ID}/connections").text
    assert "Government service" in body
    assert "Benefit Agency" in body


def test_panel_sits_above_payroll_when_both_are_linked() -> None:
    state.add_employer(PERSON_ID, "meridian", "pinecrest")
    _connected_link()
    body = client.get(f"/p/{PERSON_ID}/connections").text
    assert body.index("Benefit Agency") < body.index("Meridian Payroll")


def test_connected_sentence_has_no_employer_clause() -> None:
    _connected_link()
    body = client.get(f"/p/{PERSON_ID}/connections").text
    assert "can send you credentials for every employer below" not in body


def test_credential_count_line_shown_when_held() -> None:
    _connected_link(held_benefits=2)
    body = client.get(f"/p/{PERSON_ID}/connections").text
    assert "Benefit Agency sent you 2 benefit credentials." in body


def test_credential_count_line_absent_at_zero() -> None:
    _connected_link(held_benefits=0)
    body = client.get(f"/p/{PERSON_ID}/connections").text
    assert "sent you" not in body


def test_no_connect_button_or_employer_list_for_a_service() -> None:
    _connected_link()
    body = client.get(f"/p/{PERSON_ID}/connections").text
    assert 'class="provider__emps"' not in body
    assert "Connect payroll" not in body


def test_remove_keeps_credentials_note_and_logs_removed(monkeypatch) -> None:
    _connected_link(held_benefits=1)
    body = client.get(f"/p/{PERSON_ID}/connections").text
    assert "Removing Benefit Agency keeps your benefit credentials." in body

    response = client.post(f"/p/{PERSON_ID}/connections/benefits/remove", follow_redirects=False)
    assert response.status_code == 303
    assert state.get_link(PERSON_ID, "benefits") is None
    assert "urn:uuid:benefit-0" in state.received_for(PERSON_ID)  # credentials kept
    activity = client.get(f"/p/{PERSON_ID}/activity").text
    assert "Benefit Agency removed" in activity
    assert "Disconnected from Benefit Agency" not in activity


def test_connect_route_rejects_a_service() -> None:
    _connected_link()
    response = client.post(f"/p/{PERSON_ID}/connections/benefits/connect")
    assert response.status_code == 404
