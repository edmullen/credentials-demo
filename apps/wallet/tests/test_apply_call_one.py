"""Call 1 of applying to Benefit Agency, missing-credential pages, deny/close, status
(docs/design.md §10.1-10.3, #107)."""

import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app import outbound, state
from app.main import app
from tests.apply_helpers import benefit_credential, benefits_trust, income_credential, payroll_trust

client = TestClient(app)


class Collector:
    def __init__(self) -> None:
        self.coros: list = []

    def __call__(self, coro) -> None:
        self.coros.append(coro)

    def run(self) -> None:
        pending, self.coros = self.coros, []
        for coro in pending:
            asyncio.run(coro)


@pytest.fixture
def collector(monkeypatch):
    c = Collector()
    monkeypatch.setattr(outbound, "spawn", c)
    return c


def _patch_transport(monkeypatch, handler) -> None:
    transport = httpx.MockTransport(handler)
    real_init = httpx.AsyncClient.__init__

    def new_init(self, *args, **kwargs):
        kwargs["transport"] = transport
        real_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", new_init)


def _dcql_response(request_id: str = "areq-1") -> dict:
    return {
        "requestId": request_id,
        "dcql_query": {
            "credentials": [
                {"id": "identity", "format": "vc+jwt", "meta": {"type_values": [["IdentityCredential"]]}},
                {
                    "id": "income", "format": "vc+jwt", "multiple": True,
                    "meta": {"type_values": [["PaystubCredential"]]},
                },
            ]
        },
        "response_uri": f"/api/applications/requests/{request_id}/presentation",
    }


def test_services_page_lists_benefit_agency() -> None:
    body = client.get("/p/p01/services").text
    assert "Benefit Agency" in body
    assert 'href="/p/p01/services/benefits/apply"' in body


def test_apply_gives_asking_immediately() -> None:
    response = client.get("/p/p01/services/benefits/apply", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/p/p01/services/benefits/asking"
    body = client.get("/p/p01/services/benefits/asking").text
    assert 'data-poll="/p/p01/services/benefits/status?page=asking"' in body
    assert "Benefit Agency" in body


def test_call_one_success_gives_consent_when_both_are_held(monkeypatch, collector, payroll_trust) -> None:
    _, token = income_credential(payroll_trust)
    state.add_received("p01", "cred-1", token)
    _patch_transport(monkeypatch, lambda r: httpx.Response(201, json=_dcql_response()))
    client.get("/p/p01/services/benefits/apply")
    collector.run()
    assert state.get_link("p01", "benefits").request.phase == "consent"
    body = client.get("/p/p01/services/benefits/request").text
    assert "Do you want to share 2 credentials with Benefit Agency?" in body
    assert "Approve and share" in body
    assert "Deny" in body
    assert "1 of 2" in body


def test_call_one_sends_an_empty_body_and_identifies_itself(monkeypatch, collector, payroll_trust) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["ua"] = request.headers["user-agent"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(201, json=_dcql_response())

    _patch_transport(monkeypatch, handler)
    client.get("/p/p01/services/benefits/apply")
    collector.run()
    assert seen["ua"] == "cred-demo-wallet"
    assert seen["body"] == {}


def test_missing_income_shows_cant_apply_income_page(monkeypatch, collector) -> None:
    # p01 has an identity credential committed but no income credentials in this test.
    _patch_transport(monkeypatch, lambda r: httpx.Response(201, json=_dcql_response()))
    client.get("/p/p01/services/benefits/apply")
    collector.run()
    assert state.get_link("p01", "benefits").request.phase == "missing"
    assert state.get_link("p01", "benefits").request.missing == "income"
    body = client.get("/p/p01/services/benefits/request").text
    assert "Connect your payroll provider first" in body
    assert "Find your employer" in body
    activity = client.get("/p/p01/activity").text
    assert "you don’t have income credentials to share" in activity


def test_missing_identity_leads_over_missing_income_for_p24(monkeypatch, collector) -> None:
    # p24 has neither identity nor income; identity leads (docs/design.md §10.3).
    _patch_transport(monkeypatch, lambda r: httpx.Response(201, json=_dcql_response()))
    client.get("/p/p24/services/benefits/apply")
    collector.run()
    assert state.get_link("p24", "benefits").request.missing == "identity"
    body = client.get("/p/p24/services/benefits/request").text
    assert "You need an identity credential first" in body
    assert "Switch person" in body
    activity = client.get("/p/p24/activity").text
    assert "you don’t have an identity credential to share" in activity


def test_call_one_no_response_gives_error_page(monkeypatch, collector) -> None:
    _patch_transport(monkeypatch, lambda r: httpx.Response(500))
    client.get("/p/p01/services/benefits/apply")
    collector.run()
    link = state.get_link("p01", "benefits")
    assert link.request.phase == "error"
    body = client.get("/p/p01/services/benefits/error").text
    assert "Couldn&rsquo;t reach Benefit Agency" in body
    activity = client.get("/p/p01/activity").text
    assert "Couldn’t reach Benefit Agency to send your application" in activity


def test_deny_returns_and_logs(monkeypatch, collector, payroll_trust) -> None:
    _, token = income_credential(payroll_trust)
    state.add_received("p01", "cred-1", token)
    _patch_transport(monkeypatch, lambda r: httpx.Response(201, json=_dcql_response()))
    client.get("/p/p01/services/benefits/apply")
    collector.run()
    response = client.post(
        "/p/p01/services/benefits/request", data={"decision": "deny"}, follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/p/p01/services"
    assert state.get_link("p01", "benefits").request is None
    activity = client.get("/p/p01/activity").text
    assert "Request from Benefit Agency denied. Nothing was shared." in activity


def test_close_is_silent(monkeypatch, collector) -> None:
    _patch_transport(monkeypatch, lambda r: httpx.Response(201, json=_dcql_response()))
    client.get("/p/p24/services/benefits/apply")
    collector.run()
    before = client.get("/p/p24/activity").text
    client.post("/p/p24/services/benefits/request", data={"decision": "close"})
    assert state.get_link("p24", "benefits").request is None
    after = client.get("/p/p24/activity").text
    assert before == after


def test_status_endpoint_reports_next_page(monkeypatch, collector) -> None:
    client.get("/p/p01/services/benefits/apply")
    still_asking = client.get("/p/p01/services/benefits/status?page=asking").json()
    assert still_asking == {"next": None}

    _patch_transport(monkeypatch, lambda r: httpx.Response(201, json=_dcql_response()))
    collector.run()
    moved_on = client.get("/p/p01/services/benefits/status?page=asking").json()
    assert moved_on == {"next": "/p/p01/services/benefits/request"}


def test_asking_page_redirects_once_moved_on(monkeypatch, collector) -> None:
    _patch_transport(monkeypatch, lambda r: httpx.Response(201, json=_dcql_response()))
    client.get("/p/p01/services/benefits/apply")
    collector.run()
    response = client.get("/p/p01/services/benefits/asking", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/p/p01/services/benefits/request"


def test_request_page_redirects_while_still_asking() -> None:
    client.get("/p/p01/services/benefits/apply")
    response = client.get("/p/p01/services/benefits/request", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/p/p01/services/benefits/asking"


def test_repeat_apply_while_running_redirects_without_spawning_again(monkeypatch, collector, payroll_trust) -> None:
    _, token = income_credential(payroll_trust)
    state.add_received("p01", "cred-1", token)
    _patch_transport(monkeypatch, lambda r: httpx.Response(201, json=_dcql_response()))

    client.get("/p/p01/services/benefits/apply")
    assert len(collector.coros) == 1
    response = client.get("/p/p01/services/benefits/apply", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/p/p01/services/benefits/asking"
    assert len(collector.coros) == 1  # no second task spawned

    collector.run()
    assert state.get_link("p01", "benefits").request.phase == "consent"


def test_apply_redirects_to_already_when_a_credential_is_held(benefits_trust) -> None:
    _, token = benefit_credential(benefits_trust)
    state.add_received("p01", "cred-b1", token)
    response = client.get("/p/p01/services/benefits/apply", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/p/p01/services/benefits/already"
