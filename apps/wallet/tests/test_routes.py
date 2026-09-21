import re

import pytest
from fastapi.testclient import TestClient

from app.main import NAV, app
from app.people import all_people

client = TestClient(app)


def test_root_redirects_to_the_first_person() -> None:
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/p/p01/credentials"


@pytest.mark.parametrize("screen", [key for key, _ in NAV])
@pytest.mark.parametrize("person_id", ["p08", "p24"])
def test_each_screen_renders_for_a_person(screen: str, person_id: str) -> None:
    response = client.get(f"/p/{person_id}/{screen}")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert 'href="/static/cred.css"' in response.text
    assert "<script" not in response.text


@pytest.mark.parametrize("screen", [key for key, _ in NAV])
def test_unknown_person_is_404(screen: str) -> None:
    assert client.get(f"/p/p99/{screen}").status_code == 404


def test_there_are_25_people_in_order() -> None:
    ids = [p["id"] for p in all_people()]
    assert ids == [f"p{n:02d}" for n in range(1, 26)]


def test_header_shows_the_viewed_person() -> None:
    body = client.get("/p/p08/credentials").text
    assert 'aria-label="Nadia Haddad">NH</span>' in body
    assert "Avery Mullen" not in body


def test_nav_is_the_three_screens_with_no_help() -> None:
    body = client.get("/p/p08/connections").text
    assert "Help" not in body
    for key, label in NAV:
        assert f'href="/p/p08/{key}"' in body and f">{label}</a>" in body


@pytest.mark.parametrize("screen", [key for key, _ in NAV])
def test_active_item_is_marked_in_both_navs(screen: str) -> None:
    body = client.get(f"/p/p08/{screen}").text
    current = re.findall(r'<a href="/p/p08/(\w+)" aria-current="page"', body)
    assert current == [screen, screen]  # inline nav and <details> panel


def test_footer_links_to_the_switcher_from_the_current_screen() -> None:
    body = client.get("/p/p08/activity").text
    assert 'href="/p/p08/switch?from=activity">Switch person</a>' in body


def test_switcher_lists_25_people_with_the_viewed_one_current() -> None:
    body = client.get("/p/p08/switch").text
    rows = re.findall(r'<a class="people__row" href="/p/(p\d\d)/credentials"( aria-current="page")?>', body)
    assert [r[0] for r in rows] == [f"p{n:02d}" for n in range(1, 26)]
    assert [r[0] for r in rows if r[1]] == ["p08"]
    assert "Paterson, NJ" in body
    assert 'aria-label="Nadia Haddad">NH</span>' in body


def test_switcher_rows_keep_the_reader_on_the_same_screen() -> None:
    body = client.get("/p/p08/switch?from=activity").text
    assert 'href="/p/p22/activity"' in body
    assert "Back to activity" in body


def test_switcher_ignores_an_unknown_from_value() -> None:
    body = client.get("/p/p08/switch?from=https://evil.example").text
    assert 'href="/p/p22/credentials"' in body
    assert "evil.example" not in body


def test_switcher_for_an_unknown_person_is_404() -> None:
    assert client.get("/p/p99/switch").status_code == 404


@pytest.mark.parametrize("person_id", ["p08", "p24"])
def test_connections_shows_the_heading_and_a_disabled_find_your_employer(person_id: str) -> None:
    body = client.get(f"/p/{person_id}/connections").text
    assert '<h1 class="intro__title">Connections</h1>' in body
    assert "Connections are the services allowed to send credentials" in body
    assert '<button class="btn" type="button" disabled>Find your employer</button>' in body
    assert 'class="empty"' in body


@pytest.mark.parametrize("person_id", ["p08", "p24"])
def test_activity_shows_one_sample_log_item(person_id: str) -> None:
    body = client.get(f"/p/{person_id}/activity").text
    assert '<h1 class="intro__title">Activity</h1>' in body
    assert body.count('class="log__item"') == 1
    assert "New connection to Meridian Payroll established" in body
    assert '<span class="log__time">2:14 PM</span>' in body
