"""Call 2 of applying to Benefit Agency: approve, decided/refused/no-answer, Try again, and the
results screen (docs/design.md §10.4-10.7, #107).

Outbound calls go through httpx.MockTransport, and spawn() is replaced by a collector. One
handler serves every call for the whole test (monkeypatch doesn't compose two separate
httpx.AsyncClient.__init__ patches within a test — see test_attempt_call_two.py), reading the
current presentation response from a mutable box so a test can change it (Try again) without
re-patching.
"""

import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app import outbound, state
from app.main import app
from tests.apply_helpers import income_credential, payroll_trust

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


def _combined_handler(box: dict, seen: dict | None = None):
    """`box["response"]` is read at call time, so a test can swap it between actions (Try
    again) without re-patching httpx.AsyncClient within the same test."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/api/applications/requests"):
            return httpx.Response(201, json=_dcql_response())
        if request.url.path.endswith("/api/credentials"):
            # The post-decision fetch (docs/design.md §10.6) — empty by default, so
            # decided-outcome tests don't have to think about issued credentials.
            return httpx.Response(200, json={"credentials": []})
        if seen is not None:
            seen["body"] = json.loads(request.content)
            seen["url"] = str(request.url)
        return box["response"]

    return handler


def _reach_consent(
    monkeypatch, collector, payroll_trust, box: dict,
    *, person_id="p01", n=1, seen: dict | None = None,
) -> None:
    for i in range(1, n + 1):
        _, token = income_credential(payroll_trust, n=i, pay_date=f"2026-09-{10 + i:02d}")
        state.add_received(person_id, f"cred-{i}", token)
    _patch_transport(monkeypatch, _combined_handler(box, seen))
    client.get(f"/p/{person_id}/services/benefits/apply")
    collector.run()
    assert state.get_link(person_id, "benefits").request.phase == "consent"


def _decided_body(programs) -> dict:
    return {
        "outcome": "decided",
        "connectionId": "conn-1",
        "applicationId": "app-1",
        "decidedAt": "2026-09-21T12:00:00Z",
        "programs": programs,
    }


ALL_ELIGIBLE = [
    {"program": "food", "outcome": "eligible", "credentialId": "urn:uuid:cred-food"},
    {"program": "energy", "outcome": "eligible", "credentialId": "urn:uuid:cred-energy"},
    {"program": "housing", "outcome": "eligible", "credentialId": "urn:uuid:cred-housing"},
    {
        "program": "health", "outcome": "eligible", "credentialId": "urn:uuid:cred-health",
        "discountPercent": 92.4, "planCost": {"type": "MonetaryAmount", "value": 750.0, "currency": "USD"},
    },
    {
        "program": "dividend", "outcome": "eligible", "credentialId": "urn:uuid:cred-dividend",
        "monthlyPayment": {"type": "MonetaryAmount", "value": 100.0, "currency": "USD"},
    },
]

TWO_OF_FIVE = [
    {"program": "food", "outcome": "denied", "reason": "income_over_limit"},
    {"program": "energy", "outcome": "denied", "reason": "income_over_limit"},
    {"program": "housing", "outcome": "denied", "reason": "income_over_limit"},
    {
        "program": "health", "outcome": "eligible", "credentialId": "urn:uuid:cred-health",
        "discountPercent": 85.4, "planCost": {"type": "MonetaryAmount", "value": 750.0, "currency": "USD"},
    },
    {
        "program": "dividend", "outcome": "eligible", "credentialId": "urn:uuid:cred-dividend",
        "monthlyPayment": {"type": "MonetaryAmount", "value": 100.0, "currency": "USD"},
    },
]

ZERO_OF_FIVE = [
    {"program": p, "outcome": "denied", "reason": "not_nj_resident"}
    for p in ("food", "energy", "housing", "health", "dividend")
]


def test_approve_builds_vp_with_identity_then_income_in_order(monkeypatch, collector, payroll_trust) -> None:
    seen: dict = {}
    box = {"response": httpx.Response(200, json=_decided_body(ZERO_OF_FIVE))}
    _reach_consent(monkeypatch, collector, payroll_trust, box, n=2, seen=seen)
    client.post("/p/p01/services/benefits/request", data={"decision": "approve"})
    collector.run()
    creds = seen["body"]["verifiableCredential"]
    assert len(creds) == 3
    activity = client.get("/p/p01/activity").text
    assert "identity credential and 2 income credentials shared" in activity


def test_decided_stores_determination_and_connects(monkeypatch, collector, payroll_trust) -> None:
    box = {"response": httpx.Response(200, json=_decided_body(ALL_ELIGIBLE))}
    _reach_consent(monkeypatch, collector, payroll_trust, box)
    client.post("/p/p01/services/benefits/request", data={"decision": "approve"})
    collector.run()
    link = state.get_link("p01", "benefits")
    assert link.request is None
    assert link.determination is not None
    assert link.connection_id == "conn-1"
    assert link.presentation is None
    activity = client.get("/p/p01/activity").text
    assert "New connection to Benefit Agency established" in activity
    assert "Food Assistance: eligible" in activity
    assert "Dividend: eligible, $100.00 a month" in activity
    assert "Health: eligible, 92.4% off: $57.00 a month" in activity


def test_denied_program_logs_neutral_dot(monkeypatch, collector, payroll_trust) -> None:
    box = {"response": httpx.Response(200, json=_decided_body(TWO_OF_FIVE))}
    _reach_consent(monkeypatch, collector, payroll_trust, box)
    client.post("/p/p01/services/benefits/request", data={"decision": "approve"})
    collector.run()
    activity = client.get("/p/p01/activity").text
    assert "Food Assistance: not eligible. Your income is above this program’s limit." in activity


def test_refused_stores_refusal_and_logs_error(monkeypatch, collector, payroll_trust) -> None:
    box = {"response": httpx.Response(200, json={"outcome": "refused", "reason": "credential_invalid"})}
    _reach_consent(monkeypatch, collector, payroll_trust, box)
    client.post("/p/p01/services/benefits/request", data={"decision": "approve"})
    collector.run()
    link = state.get_link("p01", "benefits")
    assert link.refusal == "credential_invalid"
    assert link.determination is None
    assert link.presentation is None
    assert link.connection_id is None
    activity = client.get("/p/p01/activity").text
    assert "Your application couldn’t be decided: 1 credential couldn’t be verified" in activity


def test_no_response_keeps_presentation_and_shows_error(monkeypatch, collector, payroll_trust) -> None:
    box = {"response": httpx.Response(500)}
    _reach_consent(monkeypatch, collector, payroll_trust, box)
    client.post("/p/p01/services/benefits/request", data={"decision": "approve"})
    collector.run()
    link = state.get_link("p01", "benefits")
    assert link.request.phase == "error"
    assert link.presentation is not None
    redirect = client.get("/p/p01/services/benefits/applying", follow_redirects=False)
    assert redirect.status_code == 303
    assert redirect.headers["location"] == "/p/p01/services/benefits/error"


def test_try_again_resends_the_same_presentation(monkeypatch, collector, payroll_trust) -> None:
    box = {"response": httpx.Response(500)}
    seen: dict = {}
    _reach_consent(monkeypatch, collector, payroll_trust, box, seen=seen)
    client.post("/p/p01/services/benefits/request", data={"decision": "approve"})
    collector.run()
    kept_presentation = state.get_link("p01", "benefits").presentation

    box["response"] = httpx.Response(200, json=_decided_body(ALL_ELIGIBLE))
    client.post("/p/p01/services/benefits/request", data={"decision": "retry"})
    collector.run()
    assert seen["body"] == kept_presentation
    assert state.get_link("p01", "benefits").determination is not None


def test_try_again_falls_back_to_call_one_on_unknown_request(monkeypatch, collector, payroll_trust) -> None:
    box = {"response": httpx.Response(500)}
    _reach_consent(monkeypatch, collector, payroll_trust, box)
    client.post("/p/p01/services/benefits/request", data={"decision": "approve"})
    collector.run()

    box["response"] = httpx.Response(404, json={"error": "unknown_request"})
    client.post("/p/p01/services/benefits/request", data={"decision": "retry"})
    collector.run()  # the retried call 2, which (on 404) nested-spawns a fresh call 1
    collector.run()  # the fresh call 1 itself
    link = state.get_link("p01", "benefits")
    assert link.presentation is None
    assert link.request.phase == "consent"


def test_results_page_5_of_5(monkeypatch, collector, payroll_trust) -> None:
    box = {"response": httpx.Response(200, json=_decided_body(ALL_ELIGIBLE))}
    _reach_consent(monkeypatch, collector, payroll_trust, box)
    client.post("/p/p01/services/benefits/request", data={"decision": "approve"})
    collector.run()
    body = client.get("/p/p01/services/benefits/results").text
    assert "You qualify for all 5 programs" in body
    assert "Food, Energy and Housing Assistance" in body
    assert "<strong>$100.00 a month</strong> from Dividend" in body
    assert "<strong>92.4% off</strong>" in body
    assert 'role="status"' in body


def test_results_page_2_of_5_lists_denials(monkeypatch, collector, payroll_trust) -> None:
    box = {"response": httpx.Response(200, json=_decided_body(TWO_OF_FIVE))}
    _reach_consent(monkeypatch, collector, payroll_trust, box)
    client.post("/p/p01/services/benefits/request", data={"decision": "approve"})
    collector.run()
    body = client.get("/p/p01/services/benefits/results").text
    assert "You qualify for 2 programs" in body
    assert "Programs you don’t qualify for" in body
    assert "Food Assistance:</strong> your income is above this program’s limit." in body


def test_results_page_0_of_5_not_nj(monkeypatch, collector, payroll_trust) -> None:
    # p19 is out of state in the committed sample data.
    box = {"response": httpx.Response(200, json=_decided_body(ZERO_OF_FIVE))}
    _reach_consent(monkeypatch, collector, payroll_trust, box, person_id="p19")
    client.post("/p/p19/services/benefits/request", data={"decision": "approve"})
    collector.run()
    body = client.get("/p/p19/services/benefits/results").text
    assert "You don’t qualify for any programs" in body
    assert "Each program" in body
    assert "stays on your Credentials page" in body


def test_results_page_refused(monkeypatch, collector, payroll_trust) -> None:
    box = {"response": httpx.Response(200, json={"outcome": "refused", "reason": "subjects_differ"})}
    _reach_consent(monkeypatch, collector, payroll_trust, box)
    client.post("/p/p01/services/benefits/request", data={"decision": "approve"})
    collector.run()
    body = client.get("/p/p01/services/benefits/results").text
    assert "Your application couldn&rsquo;t be decided" in body
    assert "The credentials you shared aren’t all about the same person." in body


def test_results_redirects_with_no_determination() -> None:
    response = client.get("/p/p01/services/benefits/results", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/p/p01/credentials"
