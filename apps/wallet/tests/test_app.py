from fastapi.testclient import TestClient

from app import peers
from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_static_css() -> None:
    response = client.get("/static/cred.css")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")


def test_footer_states_this_is_a_demo() -> None:
    body = client.get("/p/p01/credentials").text
    assert "<strong>This is a demo.</strong>" in body
    assert 'href="https://github.com/edmullen/credentials-demo"' in body
    assert "<script" not in body


def test_startup_with_no_peer_urls_still_serves_health(monkeypatch) -> None:
    for name in peers.PEER_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    with TestClient(app) as started:
        assert started.get("/health").json() == {"status": "ok"}
