"""Call 1 (docs/design.md §3, §5): outbound calls go through httpx.MockTransport, and
spawn() is replaced by a collector, so a test decides when a background call runs.
"""

import asyncio
import json

import httpx
import pytest

from app import outbound, state
from fastapi.testclient import TestClient

from app.main import app

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


def _dcql_response(request_id: str = "req-1") -> dict:
    return {
        "requestId": request_id,
        "dcql_query": {
            "credentials": [
                {"id": "identity", "format": "vc+jwt", "meta": {"type_values": [["IdentityCredential"]]}}
            ]
        },
        "response_uri": f"/api/connections/requests/{request_id}/presentation",
    }


def test_connect_gives_asking_immediately() -> None:
    client.post("/p/p01/connections/employers", data={"employer": "pinecrest"})
    response = client.post("/p/p01/connections/meridian/connect", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/p/p01/connections/meridian/asking"
    body = client.get("/p/p01/connections/meridian/asking").text
    assert 'data-poll="/p/p01/connections/meridian/status?page=asking"' in body
    assert '<h1 class="pagehead__name">Connecting to Meridian Payroll</h1>' in body
    assert '<p class="intro__title">Asking Meridian Payroll</p>' in body
    activity = client.get("/p/p01/activity").text
    assert "Connection to Meridian Payroll requested" in activity


def test_call_one_sends_every_employer_and_identifies_itself(monkeypatch, collector) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["ua"] = request.headers["user-agent"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(201, json=_dcql_response())

    _patch_transport(monkeypatch, handler)
    client.post("/p/p01/connections/employers", data={"employer": "pinecrest"})
    client.post("/p/p01/connections/meridian/connect")
    collector.run()
    assert seen["ua"] == "cred-demo-wallet"
    assert seen["body"] == {"employers": ["pinecrest"]}


def test_call_one_success_gives_consent_for_p01(monkeypatch, collector) -> None:
    _patch_transport(monkeypatch, lambda r: httpx.Response(201, json=_dcql_response()))
    client.post("/p/p01/connections/employers", data={"employer": "pinecrest"})
    client.post("/p/p01/connections/meridian/connect")
    collector.run()
    assert state.get_link("p01", "meridian").request.phase == "consent"
    body = client.get("/p/p01/connections/meridian/request").text
    assert '<h1 class="pagehead__name">Request from Meridian Payroll</h1>' in body
    assert '<p class="intro__title">Do you want to share 1 credential with Meridian Payroll?</p>' in body
    assert "Meridian Payroll runs payroll for " in body
    assert "1 of 1" in body
    assert "Approve and share" in body
    assert "Deny" in body


def test_call_one_success_gives_consent_with_tampered_band_for_p23(monkeypatch, collector) -> None:
    _patch_transport(monkeypatch, lambda r: httpx.Response(201, json=_dcql_response()))
    client.post("/p/p23/connections/employers", data={"employer": "shoreway"})
    client.post("/p/p23/connections/meridian/connect")
    collector.run()
    body = client.get("/p/p23/connections/meridian/request").text
    assert '<span class="badge badge--error">' in body
    assert "Tampered" in body
    assert "Approve and share" in body  # still offered


def test_call_one_success_gives_missing_for_p24(monkeypatch, collector) -> None:
    _patch_transport(monkeypatch, lambda r: httpx.Response(201, json=_dcql_response()))
    client.post("/p/p24/connections/employers", data={"employer": "ridgeline"})
    client.post("/p/p24/connections/meridian/connect")
    collector.run()
    assert state.get_link("p24", "meridian").request.phase == "missing"
    body = client.get("/p/p24/connections/meridian/request").text
    assert "Missing" in body
    assert "Close request" in body
    assert "Approve and share" not in body
    activity = client.get("/p/p24/activity").text
    assert "you don’t have an Identity credential to share" in activity


def test_call_one_5xx_gives_no_response(monkeypatch, collector) -> None:
    _patch_transport(monkeypatch, lambda r: httpx.Response(500))
    client.post("/p/p01/connections/employers", data={"employer": "pinecrest"})
    client.post("/p/p01/connections/meridian/connect")
    collector.run()
    link = state.get_link("p01", "meridian")
    assert link.outcome == "no_response"
    assert link.request is None
    activity = client.get("/p/p01/activity").text
    assert "Meridian Payroll didn’t respond" in activity


def test_call_one_bad_json_gives_no_response(monkeypatch, collector) -> None:
    _patch_transport(monkeypatch, lambda r: httpx.Response(201, content=b"not json"))
    client.post("/p/p01/connections/employers", data={"employer": "pinecrest"})
    client.post("/p/p01/connections/meridian/connect")
    collector.run()
    assert state.get_link("p01", "meridian").outcome == "no_response"


def test_call_one_timeout_gives_no_response(monkeypatch, collector) -> None:
    def handler(request: httpx.Request):
        raise httpx.TimeoutException("timed out", request=request)

    _patch_transport(monkeypatch, handler)
    client.post("/p/p01/connections/employers", data={"employer": "pinecrest"})
    client.post("/p/p01/connections/meridian/connect")
    collector.run()
    assert state.get_link("p01", "meridian").outcome == "no_response"


def test_call_one_off_origin_response_uri_gives_no_response(monkeypatch, collector) -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        body = _dcql_response()
        body["response_uri"] = "https://evil.example/steal"
        return httpx.Response(201, json=body)

    _patch_transport(monkeypatch, handler)
    client.post("/p/p01/connections/employers", data={"employer": "pinecrest"})
    client.post("/p/p01/connections/meridian/connect")
    collector.run()
    assert state.get_link("p01", "meridian").outcome == "no_response"
    assert len(calls) == 1  # only call 1 itself; nothing further was sent


def test_a_stale_answer_after_try_again_is_dropped(monkeypatch, collector) -> None:
    _patch_transport(monkeypatch, lambda r: httpx.Response(201, json=_dcql_response()))
    client.post("/p/p01/connections/employers", data={"employer": "pinecrest"})

    client.post("/p/p01/connections/meridian/connect")
    stale_task = collector.coros.pop(0)
    client.post("/p/p01/connections/meridian/connect")  # Try again: a fresh token
    fresh_task = collector.coros.pop(0)

    asyncio.run(stale_task)
    assert state.get_link("p01", "meridian").request.phase == "asking"  # untouched

    asyncio.run(fresh_task)
    assert state.get_link("p01", "meridian").request.phase == "consent"


def test_status_endpoint_reports_next_page(monkeypatch, collector) -> None:
    client.post("/p/p01/connections/employers", data={"employer": "pinecrest"})
    client.post("/p/p01/connections/meridian/connect")
    still_asking = client.get("/p/p01/connections/meridian/status?page=asking").json()
    assert still_asking == {"next": None}

    _patch_transport(monkeypatch, lambda r: httpx.Response(201, json=_dcql_response()))
    collector.run()
    moved_on = client.get("/p/p01/connections/meridian/status?page=asking").json()
    assert moved_on == {"next": "/p/p01/connections/meridian/request"}


def test_asking_page_redirects_once_the_attempt_has_moved_on(monkeypatch, collector) -> None:
    _patch_transport(monkeypatch, lambda r: httpx.Response(201, json=_dcql_response()))
    client.post("/p/p01/connections/employers", data={"employer": "pinecrest"})
    client.post("/p/p01/connections/meridian/connect")
    collector.run()
    response = client.get("/p/p01/connections/meridian/asking", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/p/p01/connections/meridian/request"


def test_request_page_redirects_while_still_asking() -> None:
    client.post("/p/p01/connections/employers", data={"employer": "pinecrest"})
    client.post("/p/p01/connections/meridian/connect")
    response = client.get("/p/p01/connections/meridian/request", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/p/p01/connections/meridian/asking"


def test_deny_returns_to_connections_unchanged_and_logs(monkeypatch, collector) -> None:
    _patch_transport(monkeypatch, lambda r: httpx.Response(201, json=_dcql_response()))
    client.post("/p/p01/connections/employers", data={"employer": "pinecrest"})
    client.post("/p/p01/connections/meridian/connect")
    collector.run()
    response = client.post(
        "/p/p01/connections/meridian/request", data={"decision": "deny"}, follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/p/p01/connections"
    assert state.get_link("p01", "meridian").request is None
    activity = client.get("/p/p01/activity").text
    assert "Request from Meridian Payroll denied. Nothing was shared." in activity


def test_close_is_silent(monkeypatch, collector) -> None:
    _patch_transport(monkeypatch, lambda r: httpx.Response(201, json=_dcql_response()))
    client.post("/p/p24/connections/employers", data={"employer": "ridgeline"})
    client.post("/p/p24/connections/meridian/connect")
    collector.run()
    before = client.get("/p/p24/activity").text
    client.post("/p/p24/connections/meridian/request", data={"decision": "close"})
    assert state.get_link("p24", "meridian").request is None
    after = client.get("/p/p24/activity").text
    assert before == after  # no new entry


def test_a_double_submitted_decision_changes_nothing(monkeypatch, collector) -> None:
    _patch_transport(monkeypatch, lambda r: httpx.Response(201, json=_dcql_response()))
    client.post("/p/p01/connections/employers", data={"employer": "pinecrest"})
    client.post("/p/p01/connections/meridian/connect")
    collector.run()
    client.post("/p/p01/connections/meridian/request", data={"decision": "deny"})
    before = client.get("/p/p01/activity").text
    client.post("/p/p01/connections/meridian/request", data={"decision": "deny"})
    after = client.get("/p/p01/activity").text
    assert before == after


def _consent_body(monkeypatch, collector, person_id: str, employer: str) -> str:
    _patch_transport(monkeypatch, lambda r: httpx.Response(201, json=_dcql_response()))
    client.post(f"/p/{person_id}/connections/employers", data={"employer": employer})
    client.post(f"/p/{person_id}/connections/meridian/connect")
    collector.run()
    return client.get(f"/p/{person_id}/connections/meridian/request").text


def test_consent_puts_the_decision_before_the_credential(monkeypatch, collector) -> None:
    body = _consent_body(monkeypatch, collector, "p01", "pinecrest")
    purpose = body.index('class="intro__purpose"')
    decision = body.index('value="approve"')
    request_list = body.index('<ol class="request">')
    assert purpose < decision < request_list


def test_consent_status_is_a_white_row_with_the_issuer_and_badge(monkeypatch, collector) -> None:
    body = _consent_body(monkeypatch, collector, "p01", "pinecrest")
    row = body[body.index('<div class="panel__top">'):body.index('class="panel__section panel__section--id"')]
    assert '<h3 class="visually-hidden" id="r1-status">Status</h3>' in row
    assert '<span class="cred__issuer-name">State of New Jersey</span>' in row
    assert 'class="badge badge--verified"' in row
    assert "Nothing in this credential has changed" in row
    assert "panel__status" not in body


def test_tampered_consent_row_keeps_its_red_badge(monkeypatch, collector) -> None:
    body = _consent_body(monkeypatch, collector, "p23", "shoreway")
    assert '<div class="panel__top">' in body
    assert 'class="badge badge--error"' in body


def test_missing_consent_keeps_close_request_below_the_list(monkeypatch, collector) -> None:
    body = _consent_body(monkeypatch, collector, "p24", "ridgeline")
    assert 'value="approve"' not in body
    assert body.index('<ol class="request">') < body.index('value="close"')
    assert '<p class="intro__title">Do you want to share 1 credential with Meridian Payroll?</p>' in body
