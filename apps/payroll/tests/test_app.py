from fastapi.testclient import TestClient

from app import peers
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


def test_startup_with_no_peer_urls_still_serves_health(monkeypatch) -> None:
    for name in peers.PEER_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    with TestClient(app) as started:
        assert started.get("/health").json() == {"status": "ok"}
