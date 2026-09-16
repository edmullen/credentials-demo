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


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_static_css() -> None:
    response = client.get("/static/cred.css")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")
