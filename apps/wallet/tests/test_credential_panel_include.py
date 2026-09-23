"""The detail page's rendered HTML must not change when the panel moves into an include
shared with the consent screen (docs/design.md §6, §13 item 14)."""

from fastapi.testclient import TestClient

from app.credentials import credentials_for
from app.main import app

client = TestClient(app)


def test_detail_page_output_is_unchanged_verified() -> None:
    cred = credentials_for("p01")[0]
    body = client.get(f"/p/p01/credentials/{cred.id}").text
    assert '<section class="panel" aria-labelledby="status">' in body
    assert '<h2 class="visually-hidden" id="status">Status</h2>' in body
    assert body.count('<h2 class="visually-hidden"') == 1
    assert "\n\n\n" not in body  # no stray blank lines from the {% set %} tags


def test_detail_page_output_is_unchanged_tampered() -> None:
    cred = credentials_for("p23")[0]
    body = client.get(f"/p/p23/credentials/{cred.id}").text
    assert '<h2 class="visually-hidden" id="status">Status</h2>' in body
    assert "The signature check failed against" in body


def test_detail_page_keeps_its_tinted_band() -> None:
    cred = credentials_for("p01")[0]
    body = client.get(f"/p/p01/credentials/{cred.id}").text
    assert '<div class="panel__status panel__status--verified">' in body
    assert "panel__status--plain" not in body
