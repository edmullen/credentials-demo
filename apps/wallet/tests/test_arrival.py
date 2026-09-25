"""Arriving from Benefit Agency (docs/design.md §12, #108): the remembered person, Sign out, the
arrival routes, consent when arrived, already applied, and the switcher carrying the request."""

import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient

from app import outbound, state
from app.main import app
from tests.apply_helpers import benefit_credential, benefits_trust, income_credential, payroll_trust

RID = "0123456789abcdef0123456789abcdef"
BENEFITS_URL = "https://cred-demo-benefits.onrender.com"


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


@pytest.fixture
def client():
    # A fresh client per test: TestClient keeps cookies, and the cookie is what's under test.
    return TestClient(app)


def _patch_transport(monkeypatch, handler) -> None:
    transport = httpx.MockTransport(handler)
    real_init = httpx.AsyncClient.__init__

    def new_init(self, *args, **kwargs):
        kwargs["transport"] = transport
        real_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", new_init)


def _request_body(request_id: str = RID) -> dict:
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


# The remembered person (§12.1)


def test_a_person_page_remembers_the_person(client) -> None:
    response = client.get("/p/p05/credentials")
    cookie = response.headers["set-cookie"]
    assert cookie.startswith("wallet_person=p05;")
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Path=/" in cookie
    assert "Secure" not in cookie


def test_the_cookie_is_secure_behind_an_https_proxy(client) -> None:
    response = client.get("/p/p05/activity", headers={"X-Forwarded-Proto": "https"})
    assert "Secure" in response.headers["set-cookie"]


def test_the_landing_page_sets_no_cookie(client) -> None:
    assert "set-cookie" not in client.get("/").headers


def test_sign_out_clears_the_cookie_and_goes_to_the_landing_page(client) -> None:
    client.get("/p/p05/credentials")
    response = client.get("/sign-out", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/"
    assert response.headers["set-cookie"].startswith('wallet_person="";')
    assert "Max-Age=0" in response.headers["set-cookie"]


# The arrival route (§12.2)


def test_arriving_with_a_remembered_person_goes_to_their_request(client) -> None:
    client.get("/p/p07/credentials")
    response = client.get(f"/requests/benefits/{RID}", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == f"/p/p07/requests/benefits/{RID}"


def test_arriving_signed_out_shows_the_landing_page_with_the_notice(client) -> None:
    response = client.get(f"/requests/benefits/{RID}")
    assert response.status_code == 200
    body = response.text
    assert "<title>Sign in to see Benefit Agency&rsquo;s request — Wallet</title>" in body
    assert '<div class="notice" role="status">' in body
    assert "<strong>Benefit Agency is asking for credentials.</strong>" in body
    assert "Sign in, and your wallet will show you exactly what it wants" in body
    assert f'href="/p/p01/requests/benefits/{RID}">Sign in</a>' in body
    assert f'href="/p/p01/switch?request=benefits:{RID}">Switch person</a>' in body
    # The notice sits above the headline, as in the handoff.
    assert body.index('class="notice"') < body.index('class="landing__title"')


def test_the_plain_landing_page_has_no_notice(client) -> None:
    assert 'class="notice"' not in client.get("/").text


def test_after_sign_out_arriving_is_signed_out_again(client) -> None:
    client.get("/p/p07/credentials")
    client.get("/sign-out")
    response = client.get(f"/requests/benefits/{RID}", follow_redirects=False)
    assert response.status_code == 200
    assert "is asking for credentials" in response.text


def test_an_unknown_remembered_person_counts_as_signed_out(client) -> None:
    client.cookies.set("wallet_person", "p99")
    response = client.get(f"/requests/benefits/{RID}", follow_redirects=False)
    assert response.status_code == 200
    assert "is asking for credentials" in response.text


@pytest.mark.parametrize("path", [
    f"/requests/meridian/{RID}",
    f"/requests/elsewhere/{RID}",
    "/requests/benefits/not-a-request-id",
    f"/requests/benefits/{RID.upper()}",
    f"/requests/benefits/{RID}0",
    f"/p/p01/requests/meridian/{RID}",
    "/p/p01/requests/benefits/short",
    f"/p/p99/requests/benefits/{RID}",
])
def test_a_bad_service_or_request_id_is_a_404(client, path) -> None:
    assert client.get(path, follow_redirects=False).status_code == 404


# The person's arrival route: call 1 by reference, then §10's flow


def test_the_arrival_fetches_the_request_by_reference_from_the_registry_url(
    monkeypatch, collector, client, payroll_trust
) -> None:
    _, token = income_credential(payroll_trust)
    state.add_received("p01", "cred-1", token)
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, str(request.url)))
        return httpx.Response(200, json=_request_body())

    _patch_transport(monkeypatch, handler)
    response = client.get(f"/p/p01/requests/benefits/{RID}", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/p/p01/services/benefits/asking"
    collector.run()
    assert seen == [("GET", f"{BENEFITS_URL}/api/applications/requests/{RID}")]
    request = state.get_link("p01", "benefits").request
    assert request.phase == "consent"
    assert request.arrived
    assert request.response_uri == f"{BENEFITS_URL}/api/applications/requests/{RID}/presentation"


def test_consent_when_arrived_shows_the_arrival_row(monkeypatch, collector, client, payroll_trust) -> None:
    _, token = income_credential(payroll_trust)
    state.add_received("p01", "cred-1", token)
    _patch_transport(monkeypatch, lambda r: httpx.Response(200, json=_request_body()))
    client.get(f"/p/p01/requests/benefits/{RID}")
    collector.run()
    body = client.get("/p/p01/services/benefits/request").text
    assert '<div class="arrival">' in body
    assert '<img class="arrival__photo" src="data:image/' in body
    assert "Benefit Agency sent you here. You&rsquo;re applying as <strong>Grace Okafor</strong>." in body
    assert f'<a href="/p/p01/switch?request=benefits:{RID}">Not you? Switch person</a>' in body
    # The page head goes back to Credentials, not Government services, and the arrival row sits
    # above the question.
    assert '<a class="back" href="/p/p01/credentials">Credentials</a>' in body
    assert body.index('class="arrival"') < body.index('class="intro__title"')
    assert "Do you want to share 2 credentials with Benefit Agency?" in body
    assert "uses your identity and your September pay to decide five programs" in body


def test_the_purpose_line_names_a_span_of_pay_months(monkeypatch, collector, client, payroll_trust) -> None:
    for n, pay_date in [(1, "2026-08-29"), (2, "2026-09-15")]:
        _, token = income_credential(payroll_trust, n=n, pay_date=pay_date)
        state.add_received("p01", f"cred-{n}", token)
    _patch_transport(monkeypatch, lambda r: httpx.Response(200, json=_request_body()))
    client.get(f"/p/p01/requests/benefits/{RID}")
    collector.run()
    body = client.get("/p/p01/services/benefits/request").text
    assert "uses your identity and your Aug–Sep pay to decide" in body


def test_consent_from_the_services_list_has_no_arrival_row(monkeypatch, collector, client, payroll_trust) -> None:
    _, token = income_credential(payroll_trust)
    state.add_received("p01", "cred-1", token)
    _patch_transport(monkeypatch, lambda r: httpx.Response(201, json=_request_body()))
    client.get("/p/p01/services/benefits/apply")
    collector.run()
    body = client.get("/p/p01/services/benefits/request").text
    assert 'class="arrival"' not in body
    assert '<a class="back" href="/p/p01/services">Government services</a>' in body


def test_arriving_without_income_gets_the_connect_payroll_page(monkeypatch, collector, client) -> None:
    _patch_transport(monkeypatch, lambda r: httpx.Response(200, json=_request_body()))
    client.get(f"/p/p01/requests/benefits/{RID}")
    collector.run()
    body = client.get("/p/p01/services/benefits/request").text
    assert "Connect your payroll provider first" in body


def test_reloading_the_arrival_returns_to_the_same_attempt(monkeypatch, collector, client, payroll_trust) -> None:
    _, token = income_credential(payroll_trust)
    state.add_received("p01", "cred-1", token)
    _patch_transport(monkeypatch, lambda r: httpx.Response(200, json=_request_body()))
    client.get(f"/p/p01/requests/benefits/{RID}")
    collector.run()
    first_token = state.get_link("p01", "benefits").request.token
    response = client.get(f"/p/p01/requests/benefits/{RID}", follow_redirects=False)
    assert response.headers["location"] == "/p/p01/services/benefits/request"
    assert collector.coros == []
    assert state.get_link("p01", "benefits").request.token == first_token


def test_a_different_request_starts_a_fresh_attempt(monkeypatch, collector, client) -> None:
    _patch_transport(monkeypatch, lambda r: httpx.Response(200, json=_request_body()))
    client.get(f"/p/p01/requests/benefits/{RID}")
    first_token = state.get_link("p01", "benefits").request.token
    other = "f" * 32
    client.get(f"/p/p01/requests/benefits/{other}", follow_redirects=False)
    request = state.get_link("p01", "benefits").request
    assert request.token != first_token
    assert request.request_id == other


def test_an_expired_request_ends_on_the_error_page_and_try_again_starts_fresh(
    monkeypatch, collector, client, payroll_trust
) -> None:
    _, token = income_credential(payroll_trust)
    state.add_received("p01", "cred-1", token)
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.method)
        if request.method == "GET":
            return httpx.Response(404, json={"error": "unknown_request"})
        return httpx.Response(201, json=_request_body("b" * 32))

    _patch_transport(monkeypatch, handler)
    client.get(f"/p/p01/requests/benefits/{RID}")
    collector.run()
    assert state.get_link("p01", "benefits").request.phase == "error"
    assert "Couldn&rsquo;t reach Benefit Agency" in client.get("/p/p01/services/benefits/error").text

    client.post("/p/p01/services/benefits/request", data={"decision": "retry"})
    collector.run()
    request = state.get_link("p01", "benefits").request
    assert seen == ["GET", "POST"]
    assert request.phase == "consent"
    assert not request.arrived
    assert 'class="arrival"' not in client.get("/p/p01/services/benefits/request").text


def test_a_person_holding_benefit_credentials_has_already_applied(
    monkeypatch, collector, client, benefits_trust
) -> None:
    _, token = benefit_credential(benefits_trust)
    state.add_received("p01", "ben-1", token)
    response = client.get(f"/p/p01/requests/benefits/{RID}", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/p/p01/services/benefits/already"
    assert collector.coros == []
    body = client.get(response.headers["location"]).text
    assert "You&rsquo;ve already applied" in body
    assert "<title>You’ve already applied — Wallet</title>" in body
    assert 'href="/p/p01/credentials#benefits">View your benefit credentials</a>' in body


# The switcher carries the request


def test_the_switcher_carries_the_request_to_every_row(client) -> None:
    body = client.get(f"/p/p01/switch?request=benefits:{RID}").text
    assert f'href="/p/p01/requests/benefits/{RID}"' in body
    assert f'href="/p/p19/requests/benefits/{RID}"' in body
    assert 'class="people__row" href="/p/p05/credentials"' not in body


@pytest.mark.parametrize("carried", [
    f"meridian:{RID}", f"elsewhere:{RID}", "benefits:nope", f"benefits{RID}", "",
])
def test_the_switcher_ignores_a_bad_carried_request(client, carried) -> None:
    body = client.get(f"/p/p01/switch?request={carried}").text
    assert 'class="people__row" href="/p/p05/credentials"' in body
    assert "/requests/" not in body


def test_the_arrival_pages_carry_no_script(client) -> None:
    assert "<script" not in client.get(f"/requests/benefits/{RID}").text
