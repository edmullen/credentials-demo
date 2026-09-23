"""The landing page, Sign in and Sign out (docs/design.md §4)."""

import re

import pytest
from fastapi.testclient import TestClient

from app.main import NAV, app

client = TestClient(app)


def test_root_is_the_landing_page_not_a_redirect() -> None:
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 200
    body = response.text
    assert "<title>Wallet</title>" in body
    assert '<h1 class="intro__title">Wallet: Collect and present your credentials in one place</h1>' in body
    assert "Wallet is a secure place to store your credentials, like your ID, proof of income, and benefits you receive from the government." in body
    assert "This website is not a real service. It&rsquo;s a demo." in body
    assert '<a href="https://github.com/edmullen/credentials-demo">Learn more here</a>' in body


def test_both_sign_in_buttons_open_the_default_persons_credentials() -> None:
    body = client.get("/").text
    assert body.count('<a class="btn" href="/p/p01/credentials">Sign in</a>') == 2
    assert client.get("/p/p01/credentials").status_code == 200


def test_the_landing_page_has_no_person_furniture() -> None:
    body = client.get("/").text
    assert 'class="initials' not in body
    assert "header__nav" not in body
    assert "nav-menu" not in body
    assert "Switch person" not in body
    assert "Sign out" not in body
    assert 'class="header__brand" href="/"' in body


@pytest.mark.parametrize("screen", [key for key, _ in NAV] + ["switch"])
def test_sign_out_is_the_last_item_in_the_menu(screen: str) -> None:
    body = client.get(f"/p/p08/{screen}").text
    menu = re.search(r'<nav class="nav-menu__panel" aria-label="Main">.*?</nav>', body, re.S).group(0)
    links = re.findall(r'<a href="([^"]+)"[^>]*>([^<]+)</a>', menu)
    assert len(links) == len(NAV) + 1
    assert links[-1] == ("/", "Sign out")
    # One nav at every width: the Menu (docs/design.md §4).
    assert "header__nav" not in body
    assert body.count("<nav") == 1


def test_signed_in_the_brand_still_opens_the_persons_credentials() -> None:
    body = client.get("/p/p08/activity").text
    assert 'class="header__brand" href="/p/p08/credentials"' in body
