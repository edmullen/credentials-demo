"""Call 1, the request by reference, and call 2 (docs/design.md §2, §6, #105)."""

import pytest
from fastapi.testclient import TestClient

from app import trust
from app.main import app
from tests.helpers import PAYROLL_ISSUER, STATE_ISSUER, SUBJECT_ID, keypair
from tests.helpers import identity_token as _identity_token
from tests.helpers import paystub_token as _paystub_token
from tests.helpers import vp as _vp

client = TestClient(app)


@pytest.fixture
def keys():
    return {"state": keypair("nj-test-1"), "payroll": keypair("payroll-test-1")}


@pytest.fixture(autouse=True)
def patched_trust(monkeypatch, keys):
    """Throwaway keys, trusted the way the real trust.json trusts the state and Payroll, so
    presentations in these tests genuinely verify (docs/design.md §3)."""
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


def _new_request() -> str:
    return client.post("/api/applications/requests").json()["requestId"]


# ---- Call 1 -------------------------------------------------------------------------------


def test_call_one_returns_dcql_query_with_multiple_for_income() -> None:
    response = client.post("/api/applications/requests")
    assert response.status_code == 201
    body = response.json()
    assert "requestId" in body
    credentials = body["dcql_query"]["credentials"]
    identity = next(c for c in credentials if c["id"] == "identity")
    income = next(c for c in credentials if c["id"] == "income")
    assert identity["meta"]["type_values"] == [["IdentityCredential"]]
    assert income["meta"]["type_values"] == [["PaystubCredential"]]
    assert income["multiple"] is True
    assert "multiple" not in identity
    assert body["response_uri"] == f"/api/applications/requests/{body['requestId']}/presentation"


# ---- Request by reference -------------------------------------------------------------------


def test_by_reference_is_fetchable_repeatedly_until_answered() -> None:
    request_id = _new_request()
    first = client.get(f"/api/applications/requests/{request_id}")
    second = client.get(f"/api/applications/requests/{request_id}")
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()


def test_by_reference_404_once_answered(keys) -> None:
    request_id = _new_request()
    identity = _identity_token(keys["state"][0], "nj-test-1")
    income = _paystub_token(keys["payroll"][0], "payroll-test-1")
    client.post(f"/api/applications/requests/{request_id}/presentation", json=_vp(identity, income))
    response = client.get(f"/api/applications/requests/{request_id}")
    assert response.status_code == 404
    assert response.json() == {"error": "unknown_request"}


def test_by_reference_404_for_unknown_request() -> None:
    response = client.get("/api/applications/requests/nonexistent")
    assert response.status_code == 404
    assert response.json() == {"error": "unknown_request"}


# ---- Call 2: decided ------------------------------------------------------------------------


def test_call_two_decided_returns_five_programs_in_order_with_figures(keys) -> None:
    request_id = _new_request()
    identity = _identity_token(keys["state"][0], "nj-test-1", county="Hunterdon")
    income = _paystub_token(keys["payroll"][0], "payroll-test-1", gross=2200.0)
    response = client.post(f"/api/applications/requests/{request_id}/presentation", json=_vp(identity, income))
    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "decided"
    assert "connectionId" in body and "applicationId" in body and "decidedAt" in body
    programs = body["programs"]
    assert [p["program"] for p in programs] == ["food", "energy", "housing", "health", "dividend"]
    food, energy, housing, health, dividend = programs
    assert food["outcome"] == "eligible"
    assert energy["outcome"] == "eligible"
    assert housing["outcome"] == "eligible"
    assert health["outcome"] == "eligible"
    for entry in programs:
        assert entry["credentialId"].startswith("urn:uuid:")
    assert health["discountPercent"] == 92.4
    assert health["planCost"] == {"type": "MonetaryAmount", "value": 750.0, "currency": "USD"}
    assert dividend["outcome"] == "eligible"
    assert dividend["monthlyPayment"] == {"type": "MonetaryAmount", "value": 100.0, "currency": "USD"}


def test_call_two_denied_programs_carry_a_reason_and_no_figures(keys) -> None:
    request_id = _new_request()
    identity = _identity_token(keys["state"][0], "nj-test-1", county="Essex")
    income = _paystub_token(keys["payroll"][0], "payroll-test-1", gross=2536.0)
    body = client.post(
        f"/api/applications/requests/{request_id}/presentation", json=_vp(identity, income)
    ).json()
    for code in ("food", "energy", "housing"):
        entry = next(p for p in body["programs"] if p["program"] == code)
        assert entry["outcome"] == "denied"
        assert entry["reason"] == "income_over_limit"
        assert "discountPercent" not in entry and "monthlyPayment" not in entry


def test_call_two_out_of_state_denies_all_five_with_not_nj_resident(keys) -> None:
    request_id = _new_request()
    identity = _identity_token(keys["state"][0], "nj-test-1", region="MI", county="Wayne")
    income = _paystub_token(keys["payroll"][0], "payroll-test-1")
    body = client.post(
        f"/api/applications/requests/{request_id}/presentation", json=_vp(identity, income)
    ).json()
    assert body["outcome"] == "decided"
    assert "connectionId" in body  # a connection either way
    for entry in body["programs"]:
        assert entry["outcome"] == "denied"
        assert entry["reason"] == "not_nj_resident"


def test_multiple_income_credentials_are_summed(keys) -> None:
    request_id = _new_request()
    identity = _identity_token(keys["state"][0], "nj-test-1")
    income_1 = _paystub_token(keys["payroll"][0], "payroll-test-1", gross=1100.0)
    income_2 = _paystub_token(keys["payroll"][0], "payroll-test-1", gross=1100.0)
    body = client.post(
        f"/api/applications/requests/{request_id}/presentation", json=_vp(identity, income_1, income_2)
    ).json()
    dividend = next(p for p in body["programs"] if p["program"] == "dividend")
    assert dividend["monthlyPayment"] == {"type": "MonetaryAmount", "value": 100.0, "currency": "USD"}


# ---- Call 2: refused -------------------------------------------------------------------------


def test_call_two_refused_credential_invalid_when_a_credential_is_tampered(keys) -> None:
    request_id = _new_request()
    identity = _identity_token(keys["state"][0], "nj-test-1")
    income = _paystub_token(keys["payroll"][0], "payroll-test-1", tamper=True)
    response = client.post(f"/api/applications/requests/{request_id}/presentation", json=_vp(identity, income))
    assert response.status_code == 200
    assert response.json() == {"outcome": "refused", "reason": "credential_invalid"}


def test_call_two_refused_credential_invalid_for_an_unrecognized_issuer(keys) -> None:
    request_id = _new_request()
    other_key, _ = keypair("someone-else-1")
    identity = _identity_token(other_key, "someone-else-1")
    income = _paystub_token(keys["payroll"][0], "payroll-test-1")
    response = client.post(f"/api/applications/requests/{request_id}/presentation", json=_vp(identity, income))
    assert response.json() == {"outcome": "refused", "reason": "credential_invalid"}


def test_call_two_refused_subjects_differ(keys) -> None:
    request_id = _new_request()
    other_subject = "urn:uuid:22222222-2222-5222-8222-222222222222"
    identity = _identity_token(keys["state"][0], "nj-test-1")
    income = _paystub_token(keys["payroll"][0], "payroll-test-1", subject_id=other_subject)
    response = client.post(f"/api/applications/requests/{request_id}/presentation", json=_vp(identity, income))
    assert response.status_code == 200
    assert response.json() == {"outcome": "refused", "reason": "subjects_differ"}


def test_nothing_is_connected_on_a_refusal(keys) -> None:
    request_id = _new_request()
    identity = _identity_token(keys["state"][0], "nj-test-1")
    income = _paystub_token(keys["payroll"][0], "payroll-test-1", tamper=True)
    client.post(f"/api/applications/requests/{request_id}/presentation", json=_vp(identity, income))
    from app import applications

    assert applications.all_applications()[0].outcome == "refused"
    assert applications._connections == {}


def test_facts_are_recorded_as_presented_on_a_refusal(keys) -> None:
    # The admin view shows submitted data even on a refusal, "as presented" (docs/design.md §8.2).
    request_id = _new_request()
    identity = _identity_token(keys["state"][0], "nj-test-1", county="Hunterdon")
    income = _paystub_token(keys["payroll"][0], "payroll-test-1", tamper=True)
    client.post(f"/api/applications/requests/{request_id}/presentation", json=_vp(identity, income))
    from app import applications

    application = applications.all_applications()[0]
    assert application.facts.region == "NJ"
    assert application.facts.county == "Hunterdon"
    assert len(application.facts.paystubs) == 1
    assert application.subject_id == SUBJECT_ID


# ---- Call 2: bad shapes (400) ------------------------------------------------------------------


def test_400_when_not_a_verifiable_presentation() -> None:
    request_id = _new_request()
    response = client.post(f"/api/applications/requests/{request_id}/presentation", json={"foo": "bar"})
    assert response.status_code == 400
    assert response.json() == {"error": "invalid_presentation"}


def test_400_with_no_identity_credential(keys) -> None:
    request_id = _new_request()
    income = _paystub_token(keys["payroll"][0], "payroll-test-1")
    response = client.post(f"/api/applications/requests/{request_id}/presentation", json=_vp(income))
    assert response.status_code == 400


def test_400_with_no_income_credentials(keys) -> None:
    request_id = _new_request()
    identity = _identity_token(keys["state"][0], "nj-test-1")
    response = client.post(f"/api/applications/requests/{request_id}/presentation", json=_vp(identity))
    assert response.status_code == 400


def test_400_with_two_identity_credentials(keys) -> None:
    request_id = _new_request()
    identity_1 = _identity_token(keys["state"][0], "nj-test-1")
    identity_2 = _identity_token(keys["state"][0], "nj-test-1")
    income = _paystub_token(keys["payroll"][0], "payroll-test-1")
    response = client.post(
        f"/api/applications/requests/{request_id}/presentation", json=_vp(identity_1, identity_2, income)
    )
    assert response.status_code == 400


def test_400_nothing_is_recorded() -> None:
    request_id = _new_request()
    client.post(f"/api/applications/requests/{request_id}/presentation", json={"foo": "bar"})
    from app import applications

    assert applications.all_applications() == []


# ---- Call 2: 404 -------------------------------------------------------------------------------


def test_404_unknown_request(keys) -> None:
    identity = _identity_token(keys["state"][0], "nj-test-1")
    income = _paystub_token(keys["payroll"][0], "payroll-test-1")
    response = client.post(
        "/api/applications/requests/nonexistent/presentation", json=_vp(identity, income)
    )
    assert response.status_code == 404
    assert response.json() == {"error": "unknown_request"}


def test_404_when_request_already_answered(keys) -> None:
    request_id = _new_request()
    identity = _identity_token(keys["state"][0], "nj-test-1")
    income = _paystub_token(keys["payroll"][0], "payroll-test-1")
    client.post(f"/api/applications/requests/{request_id}/presentation", json=_vp(identity, income))
    response = client.post(f"/api/applications/requests/{request_id}/presentation", json=_vp(identity, income))
    assert response.status_code == 404


# ---- Call 2: without a valid key ----------------------------------------------------------------


def test_503_without_a_valid_key_and_the_request_stays_pending(keys, monkeypatch) -> None:
    import os

    from app import signing

    request_id = _new_request()
    identity = _identity_token(keys["state"][0], "nj-test-1")
    income = _paystub_token(keys["payroll"][0], "payroll-test-1")
    real_key = os.environ[signing.ENV_VAR]
    monkeypatch.delenv(signing.ENV_VAR, raising=False)
    response = client.post(f"/api/applications/requests/{request_id}/presentation", json=_vp(identity, income))
    assert response.status_code == 503

    monkeypatch.setenv(signing.ENV_VAR, real_key)  # restore the throwaway key
    retry = client.post(f"/api/applications/requests/{request_id}/presentation", json=_vp(identity, income))
    assert retry.status_code == 200


# ---- Re-applying -----------------------------------------------------------------------------


def test_reapplying_replaces_the_connection(keys) -> None:
    from app import applications

    request_1 = _new_request()
    identity = _identity_token(keys["state"][0], "nj-test-1")
    income = _paystub_token(keys["payroll"][0], "payroll-test-1")
    first = client.post(f"/api/applications/requests/{request_1}/presentation", json=_vp(identity, income)).json()

    request_2 = _new_request()
    second = client.post(f"/api/applications/requests/{request_2}/presentation", json=_vp(identity, income)).json()

    assert first["connectionId"] != second["connectionId"]
    assert applications.application_for_connection(first["connectionId"]) is None
    assert applications.application_for_connection(second["connectionId"]).id == second["applicationId"]
