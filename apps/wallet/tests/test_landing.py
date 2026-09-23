"""The landing page (docs/design.md §5)."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_is_the_landing_page_not_a_redirect() -> None:
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 200
    body = response.text
    assert "<title>Wallet: Collect and present your credentials in one place</title>" in body
    assert (
        '<h1 class="landing__title"><span class="landing__lead">Wallet:</span> '
        "Collect and present your credentials in one place</h1>"
    ) in body
    assert (
        '<p class="intro__purpose">Wallet is a secure place to store your credentials, like your ID, '
        "proof of income, and benefits you receive from the government.</p>"
    ) in body
    assert (
        '<p class="landing__demo">This website is not a real service. It&rsquo;s a demo. '
        '<a href="https://github.com/edmullen/credentials-demo">Learn more here</a></p>'
    ) in body
    assert body.count("<h1") == 1


def test_both_sign_in_buttons_open_the_default_persons_credentials() -> None:
    body = client.get("/").text
    assert '<a class="btn" href="/p/p01/credentials">Sign in</a>' in body  # header
    assert '<a class="btn btn--block" href="/p/p01/credentials">Sign in</a>' in body  # page
    assert client.get("/p/p01/credentials").status_code == 200


def test_signed_out_there_is_no_person_furniture() -> None:
    body = client.get("/").text
    assert 'class="initials' not in body
    assert "nav-menu" not in body
    assert "<nav" not in body
    assert "Sign out" not in body
    assert 'class="header__brand" href="/"' in body


def test_the_footer_keeps_switch_person_for_the_default_person() -> None:
    body = client.get("/").text
    assert '<span class="footer__aside"><a href="/p/p01/switch">Switch person</a></span>' in body
    assert client.get("/p/p01/switch").status_code == 200
