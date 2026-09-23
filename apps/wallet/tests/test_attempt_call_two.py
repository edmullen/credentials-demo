"""Call 2 — Approve and share, the presentation, and every outcome (docs/design.md §3, §5).

Outbound calls go through httpx.MockTransport, and spawn() is replaced by a collector, as in
test_attempt_call_one.py. One handler serves both calls for the whole test (monkeypatch
doesn't compose two separate httpx.AsyncClient.__init__ patches within a test), so
`_reach_consent` takes the call-2 response up front.
"""

import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app import outbound, state
from app.credentials import credentials_for
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


def _two_stage_handler(presentation_response: httpx.Response, seen: dict | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/api/connections/requests"):
            return httpx.Response(201, json=_dcql_response())
        if request.url.path.endswith("/api/credentials"):
            # The post-connect fetch (docs/design.md §9) — empty by default, so existing
            # call-2 tests don't have to think about income credentials.
            return httpx.Response(200, json={"credentials": []})
        if seen is not None:
            seen["body"] = json.loads(request.content)
            seen["url"] = str(request.url)
        return presentation_response

    return handler


def _reach_consent(
    monkeypatch, collector, person_id: str, employer_id: str,
    presentation_response: httpx.Response, seen: dict | None = None,
) -> None:
    _patch_transport(monkeypatch, _two_stage_handler(presentation_response, seen))
    client.post(f"/p/{person_id}/connections/employers", data={"employer": employer_id})
    client.post(f"/p/{person_id}/connections/meridian/connect")
    collector.run()
    assert state.get_link(person_id, "meridian").request.phase == "consent"


def test_approve_sends_the_committed_jwt_exactly(monkeypatch, collector) -> None:
    seen: dict = {}
    _reach_consent(
        monkeypatch, collector, "p01", "pinecrest",
        httpx.Response(200, json={"outcome": "connected", "connectionId": "conn-1"}), seen,
    )
    response = client.post(
        "/p/p01/connections/meridian/request", data={"decision": "approve"}, follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/p/p01/connections/meridian/verifying"
    activity = client.get("/p/p01/activity").text
    assert "Identity credential shared with Meridian Payroll" in activity
    collector.run()

    committed = credentials_for("p01")[0].token
    sent = seen["body"]["verifiableCredential"][0]
    assert sent["type"] == "EnvelopedVerifiableCredential"
    assert sent["id"] == f"data:application/vc+jwt,{committed}"
    assert seen["url"].endswith("/api/connections/requests/req-1/presentation")


def test_connected_outcome(monkeypatch, collector) -> None:
    _reach_consent(
        monkeypatch, collector, "p01", "pinecrest", httpx.Response(200, json={"outcome": "connected", "connectionId": "conn-1"})
    )
    client.post("/p/p01/connections/meridian/request", data={"decision": "approve"})
    collector.run()
    link = state.get_link("p01", "meridian")
    assert link.connected_at is not None
    assert link.outcome is None
    assert link.request is None
    body = client.get("/p/p01/connections").text
    assert "Connected since" in body
    assert "Disconnect" in body
    activity = client.get("/p/p01/activity").text
    assert "New connection to Meridian Payroll established" in activity
    home = client.get("/p/p01/credentials").text
    assert "You&rsquo;re connected to Meridian Payroll." in home


def test_refused_credential_invalid(monkeypatch, collector) -> None:
    _reach_consent(
        monkeypatch, collector, "p23", "shoreway",  # p23: Tampered
        httpx.Response(200, json={"outcome": "refused", "reason": "credential_invalid"}),
    )
    client.post("/p/p23/connections/meridian/request", data={"decision": "approve"})
    collector.run()
    link = state.get_link("p23", "meridian")
    assert link.outcome == "credential_invalid"
    assert link.connected_at is None
    body = client.get("/p/p23/connections").text
    assert "Meridian Payroll couldn’t verify your identity credential." in body
    assert "It has been changed since it was issued." in body
    assert "View your credential" in body
    assert "Try again" in body
    activity = client.get("/p/p23/activity").text
    assert (
        "Connection to Meridian Payroll refused: Meridian Payroll couldn’t verify your "
        "identity credential." in activity
    )


def test_refused_not_an_employee(monkeypatch, collector) -> None:
    _reach_consent(
        monkeypatch, collector, "p01", "harborline",  # Grace doesn't work there
        httpx.Response(200, json={"outcome": "refused", "reason": "not_an_employee"}),
    )
    client.post("/p/p01/connections/meridian/request", data={"decision": "approve"})
    collector.run()
    link = state.get_link("p01", "meridian")
    assert link.outcome == "not_an_employee"
    body = client.get("/p/p01/connections").text
    assert "Meridian Payroll doesn’t have an employee record that matches you." in body


def test_call_two_404_gives_no_response(monkeypatch, collector) -> None:
    _reach_consent(
        monkeypatch, collector, "p01", "pinecrest",
        httpx.Response(404, json={"error": "unknown_request"}),
    )
    client.post("/p/p01/connections/meridian/request", data={"decision": "approve"})
    collector.run()
    link = state.get_link("p01", "meridian")
    assert link.outcome == "no_response"
    assert link.request is None


def test_call_two_5xx_gives_no_response(monkeypatch, collector) -> None:
    _reach_consent(monkeypatch, collector, "p01", "pinecrest", httpx.Response(500))
    client.post("/p/p01/connections/meridian/request", data={"decision": "approve"})
    collector.run()
    assert state.get_link("p01", "meridian").outcome == "no_response"


def test_call_two_bad_json_gives_no_response(monkeypatch, collector) -> None:
    _reach_consent(monkeypatch, collector, "p01", "pinecrest", httpx.Response(200, content=b"not json"))
    client.post("/p/p01/connections/meridian/request", data={"decision": "approve"})
    collector.run()
    assert state.get_link("p01", "meridian").outcome == "no_response"


def test_call_two_timeout_gives_no_response(monkeypatch, collector) -> None:
    def handler(request: httpx.Request):
        if request.url.path.endswith("/api/connections/requests"):
            return httpx.Response(201, json=_dcql_response())
        raise httpx.TimeoutException("timed out", request=request)

    _patch_transport(monkeypatch, handler)
    client.post("/p/p01/connections/employers", data={"employer": "pinecrest"})
    client.post("/p/p01/connections/meridian/connect")
    collector.run()
    client.post("/p/p01/connections/meridian/request", data={"decision": "approve"})
    collector.run()
    assert state.get_link("p01", "meridian").outcome == "no_response"


def test_a_stale_answer_after_remove_is_dropped(monkeypatch, collector) -> None:
    _reach_consent(
        monkeypatch, collector, "p01", "pinecrest", httpx.Response(200, json={"outcome": "connected", "connectionId": "conn-1"})
    )
    client.post("/p/p01/connections/meridian/request", data={"decision": "approve"})
    stale_task = collector.coros.pop(0)
    client.post("/p/p01/connections/meridian/remove")  # the person removes it mid-flight
    asyncio.run(stale_task)
    assert state.get_link("p01", "meridian") is None  # removal wasn't reopened by the answer


def test_a_double_submitted_approve_changes_nothing(monkeypatch, collector) -> None:
    _reach_consent(
        monkeypatch, collector, "p01", "pinecrest", httpx.Response(200, json={"outcome": "connected", "connectionId": "conn-1"})
    )
    client.post("/p/p01/connections/meridian/request", data={"decision": "approve"})
    before = client.get("/p/p01/activity").text
    client.post("/p/p01/connections/meridian/request", data={"decision": "approve"})
    after = client.get("/p/p01/activity").text
    assert before == after
    collector.run()


def test_verifying_page_redirects_once_answered(monkeypatch, collector) -> None:
    _reach_consent(
        monkeypatch, collector, "p01", "pinecrest", httpx.Response(200, json={"outcome": "connected", "connectionId": "conn-1"})
    )
    client.post("/p/p01/connections/meridian/request", data={"decision": "approve"})
    collector.run()
    response = client.get("/p/p01/connections/meridian/verifying", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/p/p01/connections"


def test_status_endpoint_during_verifying(monkeypatch, collector) -> None:
    _reach_consent(
        monkeypatch, collector, "p01", "pinecrest", httpx.Response(200, json={"outcome": "connected", "connectionId": "conn-1"})
    )
    client.post("/p/p01/connections/meridian/request", data={"decision": "approve"})
    still = client.get("/p/p01/connections/meridian/status?page=verifying").json()
    assert still == {"next": None}
    collector.run()
    moved = client.get("/p/p01/connections/meridian/status?page=verifying").json()
    assert moved == {"next": "/p/p01/connections"}


def test_verifying_page_head_and_step_title(monkeypatch, collector) -> None:
    _reach_consent(
        monkeypatch, collector, "p01", "pinecrest", httpx.Response(200, json={"outcome": "connected", "connectionId": "conn-1"})
    )
    client.post("/p/p01/connections/meridian/request", data={"decision": "approve"})
    body = client.get("/p/p01/connections/meridian/verifying").text
    assert '<h1 class="pagehead__title">Connecting to Meridian Payroll</h1>' in body
    assert '<h2 class="intro__title">Wait while Meridian Payroll checks your identity</h2>' in body
    assert "<title>Wait while Meridian Payroll checks your identity — Wallet</title>" in body
    collector.run()  # let the queued call two finish, so nothing is left un-awaited
