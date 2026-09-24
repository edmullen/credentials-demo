"""The admin view (docs/design.md §8, #111)."""

import pytest
from fastapi.testclient import TestClient

from app import trust
from app.main import app
from tests.helpers import PAYROLL_ISSUER, STATE_ISSUER, identity_token, keypair, paystub_token, vp

client = TestClient(app)


@pytest.fixture
def keys():
    return {"state": keypair("nj-test-1"), "payroll": keypair("payroll-test-1")}


@pytest.fixture(autouse=True)
def patched_trust(monkeypatch, keys):
    trust_list = {
        STATE_ISSUER: {
            "name": "State of New Jersey",
            "trustedFor": ["IdentityCredential"],
            "keys": [keys["state"][1]],
        },
        PAYROLL_ISSUER: {
            "name": "Meridian Payroll",
            "trustedFor": ["PaystubCredential"],
            "keys": [keys["payroll"][1]],
        },
    }
    monkeypatch.setattr(trust, "trust_list", lambda: trust_list)
    return trust_list


def _apply(
    keys, subject_id=None, region="NJ", county="Hunterdon", gross=1100.0, tamper=False,
    given_name="Grace", family_name="Okafor",
) -> dict:
    request_id = client.post("/api/applications/requests").json()["requestId"]
    identity_kwargs = {"region": region, "county": county, "given_name": given_name, "family_name": family_name}
    income_kwargs = {}
    if subject_id:
        identity_kwargs["subject_id"] = subject_id
        income_kwargs["subject_id"] = subject_id
    identity = identity_token(keys["state"][0], "nj-test-1", **identity_kwargs)
    income = paystub_token(keys["payroll"][0], "payroll-test-1", gross=gross, tamper=tamper, **income_kwargs)
    response = client.post(f"/api/applications/requests/{request_id}/presentation", json=vp(identity, income))
    return response.json()


def test_empty_state_when_no_applications() -> None:
    body = client.get("/admin").text
    assert "No applications yet" in body
    assert 'class="apps"' not in body


def test_404_for_unknown_application() -> None:
    assert client.get("/admin/applications/nonexistent").status_code == 404


def test_admin_link_has_aria_current_on_admin_pages() -> None:
    for path in ("/admin",):
        body = client.get(path).text
        assert 'href="/admin" aria-current="page"' in body


def test_list_groups_by_person_newest_first(keys) -> None:
    grace = "urn:uuid:11111111-1111-5111-8111-111111111111"
    luis = "urn:uuid:22222222-2222-5222-8222-222222222222"
    _apply(keys, subject_id=grace, county="Hunterdon", gross=2200.0, given_name="Grace", family_name="Okafor")
    _apply(keys, subject_id=luis, county="Essex", gross=2536.0, given_name="Luis", family_name="Ferreira")
    _apply(keys, subject_id=grace, county="Hunterdon", gross=2200.0, given_name="Grace", family_name="Okafor")

    body = client.get("/admin").text
    # Grace's group (most recent application) comes first; her second row has no repeated name.
    grace_pos = body.index("Grace")
    luis_pos = body.index("Luis")
    assert grace_pos < luis_pos
    assert body.count('<th scope="row">Grace Okafor</th>') == 1  # shown once, first row of her group only
    assert body.count('class="apps__start"') == 2  # one per group


def test_decided_row_shows_n_of_5_approved(keys) -> None:
    _apply(keys, county="Hunterdon", gross=2200.0)
    body = client.get("/admin").text
    assert "5 of 5 approved" in body


def test_not_nj_row_shows_the_wording(keys) -> None:
    _apply(keys, region="MI", county="Wayne")
    body = client.get("/admin").text
    assert "Not a New Jersey resident" in body


def test_refused_rows_show_the_wording(keys) -> None:
    _apply(keys, county="Hunterdon", gross=2200.0, tamper=True)
    body = client.get("/admin").text
    assert "Refused: credential couldn’t be verified" in body


def test_subjects_differ_row(keys) -> None:
    request_id = client.post("/api/applications/requests").json()["requestId"]
    identity = identity_token(keys["state"][0], "nj-test-1")
    other = "urn:uuid:99999999-9999-5999-8999-999999999999"
    income = paystub_token(keys["payroll"][0], "payroll-test-1", subject_id=other)
    client.post(f"/api/applications/requests/{request_id}/presentation", json=vp(identity, income))
    body = client.get("/admin").text
    assert "Refused: credentials aren’t about one person" in body


def test_determination_decided_page(keys) -> None:
    result = _apply(keys, county="Hunterdon", gross=2200.0)
    body = client.get(f"/admin/applications/{result['applicationId']}").text
    assert "5 of 5 approved" in body
    assert "Food Assistance" in body
    assert "Eligible" in body
    assert "Same subject" in body
    assert result["programs"][0]["credentialId"] in body
    assert "Issued credential" in body
    assert 'data-program="food"' in body
    assert "<table" not in body or "figures" in body  # only the paystub figures table


def test_determination_denied_program_shows_scale_and_reason(keys) -> None:
    # Luis Ferreira's figures: $2,536/month in Essex denies food/energy/housing.
    result = _apply(keys, county="Essex", gross=2536.0)
    body = client.get(f"/admin/applications/{result['applicationId']}").text
    assert "income_over_limit" in body
    assert "over the limit" in body
    assert 'data-program="food"' in body


def test_determination_not_nj_page_has_no_scale_and_a_callout(keys) -> None:
    result = _apply(keys, region="MI", county="Wayne")
    body = client.get(f"/admin/applications/{result['applicationId']}").text
    assert "Residency stopped the application" in body
    assert "not_nj_resident" in body
    assert 'class="scale"' not in body
    assert "may apply again" in body


def _latest_application_id() -> str:
    import re

    match = re.search(r"/admin/applications/([a-f0-9]+)", client.get("/admin").text)
    return match.group(1)


def test_determination_refused_page_has_no_decisions(keys) -> None:
    _apply(keys, county="Hunterdon", gross=2200.0, tamper=True)
    body = client.get(f"/admin/applications/{_latest_application_id()}").text
    assert "Refused before any program was evaluated" in body
    assert "credential_invalid" in body
    assert 'class="decisions"' not in body
    assert "Tampered" in body


def test_image_is_truncated_not_shown(keys) -> None:
    result = _apply(keys, county="Hunterdon", gross=2200.0)
    body = client.get(f"/admin/applications/{result['applicationId']}").text
    assert "(photo, not shown)" in body
    assert body.count("base64") <= 1  # truncated, not the full data URI twice over


def test_no_script_tag_on_any_admin_page(keys) -> None:
    result = _apply(keys, county="Hunterdon", gross=2200.0)
    assert "<script" not in client.get("/admin").text
    assert "<script" not in client.get(f"/admin/applications/{result['applicationId']}").text
