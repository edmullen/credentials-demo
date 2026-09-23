from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_index() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    body = response.text
    assert 'data-app="payroll"' in body
    assert "<h1" in body and "Meridian Payroll" in body
    assert "/static/cred.css" in body
    assert '<a class="btn" href="/p/p01/paystubs">Sign in</a>' in body
    assert 'class="initials"' not in body


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_static_css() -> None:
    response = client.get("/static/cred.css")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")


def test_footer_states_this_is_a_demo() -> None:
    body = client.get("/").text
    assert "<strong>This is a demo.</strong>" in body
    assert 'href="https://github.com/edmullen/credentials-demo"' in body
    assert "<script" not in body


def test_person_root_redirects_to_paystubs() -> None:
    response = client.get("/p/p01/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/p/p01/paystubs"


def test_unknown_person_is_404() -> None:
    assert client.get("/p/p99/").status_code == 404
    assert client.get("/p/p99/paystubs").status_code == 404
    assert client.get("/p/p99/switch").status_code == 404


def test_paystubs_page_shows_identity() -> None:
    response = client.get("/p/p01/paystubs")
    assert response.status_code == 200
    body = response.text
    assert 'data-app="payroll"' in body
    assert "Your pay" in body
    assert "<h1" in body and "Grace Okafor" in body
    assert "Flemington, NJ" in body
    assert "urn:uuid:031acde8-d4c0-5778-b6ab-84a4b612af70" in body
    assert "Send your pay to your wallet" not in body
    assert '<script' not in body


def test_paystubs_page_header_is_the_portal_state() -> None:
    body = client.get("/p/p01/paystubs").text
    assert 'class="initials" role="img" aria-label="Grace Okafor"' in body
    assert ">GO<" in body
    assert 'href="/p/p01/paystubs" aria-current="page">Paystubs</a>' in body
    assert 'href="/p/p01/connections">Connections</a>' in body
    assert 'href="/p/p01/activity">Activity</a>' in body
    assert '<a class="btn" href="/p/p01/paystubs">Sign in</a>' not in body


def test_switch_page_lists_all_25_with_one_current_row() -> None:
    response = client.get("/p/p01/switch")
    assert response.status_code == 200
    body = response.text
    assert body.count('class="people__row"') == 25
    assert body.count('aria-current="page"') == 1
    assert "Grace Okafor" in body  # p01, viewed person
    assert "Ray Miller" in body  # p24, no identity credential, still an employee here
    assert '<span class="footer__aside"><a href="/p/p01/paystubs">Back to paystubs</a></span>' in body


def test_switch_page_shows_multiple_employers_in_order() -> None:
    body = client.get("/p/p01/switch").text
    assert "Shoreway Supermarkets · Brightpath Early Learning · Ridgeline Home &amp; Hardware" in body


def test_switch_link_reachable_from_portal_footer() -> None:
    body = client.get("/p/p01/paystubs").text
    assert '<span class="footer__aside"><a href="/p/p01/switch?from=paystubs">Switch person</a></span>' in body
