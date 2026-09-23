"""Page heads, step titles and <title>s (docs/design.md §4), and the Menu (§3)."""

import re

import pytest
from fastapi.testclient import TestClient

from app.connections import connections_title
from app.credentials import credentials_for
from app.main import NAV, app

client = TestClient(app)


def _head(body: str) -> tuple[tuple[str, str] | None, str]:
    """The page head's back link as (href, label), or None, and its <h1> text."""
    head = re.search(r'<div class="pagehead">(.*?)</div>', body, re.S).group(1)
    back = re.search(r'<a class="back" href="([^"]+)">([^<]+)</a>', head)
    name = re.search(r'<h1 class="pagehead__title">([^<]+)</h1>', head).group(1)
    if back:
        assert '<span class="pagehead__sep" aria-hidden="true"></span>' in head
    else:
        assert "pagehead__sep" not in head
    return (back.groups() if back else None), name


def _steps(body: str) -> list[str]:
    return re.findall(r'<h2 class="intro__title">([^<]+)</h2>', body)


@pytest.mark.parametrize("path, back, name, step", [
    ("/p/p01/credentials", None, "Credentials", None),
    ("/p/p01/connections", None, "Connections", "You have 0 connections"),
    ("/p/p01/connections/employers", ("/p/p01/connections", "Connections"), "Find your employer", "Select your employer"),
    ("/p/p01/activity", None, "Activity", None),
    ("/p/p01/switch", None, "Switch person", "Choose who to demo as"),
])
def test_each_page_opens_with_its_page_head(path, back, name, step) -> None:
    body = client.get(path).text
    assert _head(body) == (back, name)
    assert _steps(body) == ([step] if step else [])
    assert f"<title>{step or name} — Wallet</title>" in body
    assert body.count("<h1") == 1
    assert "intro__eyebrow\">Wallet<" not in body


def test_the_credential_detail_page_has_no_step_title() -> None:
    cred = credentials_for("p01")[0]
    body = client.get(f"/p/p01/credentials/{cred.id}").text
    assert _head(body) == (("/p/p01/credentials", "Credentials"), "Identity credential")
    assert _steps(body) == []
    assert "<title>Identity credential — Wallet</title>" in body


def test_connections_asks_for_the_next_step_once_an_employer_is_added() -> None:
    client.post("/p/p01/connections/employers", data={"employer": "pinecrest"})
    body = client.get("/p/p01/connections").text
    assert _steps(body) == ["Now connect your payroll"]
    assert "<title>Now connect your payroll — Wallet</title>" in body


@pytest.mark.parametrize("panels, title", [
    ([], "You have 0 connections"),
    ([{"connected": True}], "You have 1 connection"),
    ([{"connected": True}, {"connected": True}], "You have 2 connections"),
    ([{"connected": False}], "Now connect your payroll"),
    ([{"connected": True}, {"connected": False}], "Now connect your payroll"),
])
def test_connections_title(panels, title) -> None:
    assert connections_title(panels) == title


@pytest.mark.parametrize("screen", [key for key, _ in NAV] + ["switch"])
def test_the_menu_is_the_only_nav_and_ends_with_sign_out(screen: str) -> None:
    body = client.get(f"/p/p08/{screen}").text
    assert body.count("<nav") == 1
    assert "header__nav" not in body
    menu = re.search(r'<nav class="nav-menu__panel" aria-label="Main">(.*?)</nav>', body, re.S).group(1)
    links = re.findall(r'<a (?:class="([^"]+)" )?href="([^"]+)"[^>]*>([^<]+)</a>', menu)
    assert [label for _, _, label in links] == [label for _, label in NAV] + ["Sign out"]
    assert links[-1] == ("nav-menu__signout", "/", "Sign out")


def test_signed_in_the_brand_still_opens_the_persons_credentials() -> None:
    assert 'class="header__brand" href="/p/p08/credentials"' in client.get("/p/p08/activity").text
