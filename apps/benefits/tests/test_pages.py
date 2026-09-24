"""Landing and program pages (docs/design.md §7, #20)."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

PROGRAM_CODES = ["food", "energy", "housing", "health", "dividend"]


def test_landing_shows_five_program_cards_in_order_each_linked() -> None:
    body = client.get("/").text
    positions = [body.index(f'data-program="{code}"') for code in PROGRAM_CODES]
    assert positions == sorted(positions)
    for code in PROGRAM_CODES:
        assert f'href="/programs/{code}"' in body


def test_landing_nav_has_no_aria_current() -> None:
    body = client.get("/").text
    assert "aria-current" not in body


def test_landing_has_no_placeholder_signed_in_user() -> None:
    body = client.get("/").text
    assert "Jordan Diaz" not in body


def test_each_program_page_marks_itself_current_in_nav() -> None:
    for code in PROGRAM_CODES:
        body = client.get(f"/programs/{code}").text
        assert f'href="/programs/{code}" aria-current="page"' in body


def test_unknown_program_code_is_404() -> None:
    response = client.get("/programs/nonexistent")
    assert response.status_code == 404


def test_food_and_energy_have_no_table() -> None:
    for code in ("food", "energy"):
        body = client.get(f"/programs/{code}").text
        assert "<table" not in body


def test_food_limit_rendered_from_rules() -> None:
    body = client.get("/programs/food").text
    assert "$29,526.00" in body


def test_energy_limit_rendered_from_rules() -> None:
    body = client.get("/programs/energy").text
    assert "$30,000.00" in body


def test_housing_lists_all_21_counties_in_a_closed_disclosure() -> None:
    body = client.get("/programs/housing").text
    assert '<details class="disclosure disclosure--boxed">' in body
    assert "Hunterdon" in body and "$41,835.90" in body
    assert "Cumberland" in body and "$19,349.70" in body
    assert body.count("figures__strong") == 21


def test_health_and_dividend_have_no_table_only_facts_and_callout() -> None:
    for code in ("health", "dividend"):
        body = client.get(f"/programs/{code}").text
        assert "<table" not in body
        assert 'class="facts"' in body
        assert "Earning more never leaves you worse off" in body


def test_health_discount_figures_from_rules() -> None:
    body = client.get("/programs/health").text
    assert "$750.00" in body
    assert "$22,024.80" in body
    assert "$79,800.00" in body


def test_dividend_figures_from_rules() -> None:
    body = client.get("/programs/dividend").text
    assert "$100" in body
    assert "$300" in body
    assert "$1,200" in body


def test_every_program_page_has_the_as_of_note() -> None:
    for code in PROGRAM_CODES:
        body = client.get(f"/programs/{code}").text
        assert "September 2026" in body


def test_every_program_page_offers_apply_options_with_aria_describedby() -> None:
    for code in PROGRAM_CODES:
        body = client.get(f"/programs/{code}").text
        assert 'href="/apply" aria-describedby="apply-wallet-note"' in body
        assert 'id="apply-wallet-note"' in body
        assert 'disabled aria-describedby="apply-here-note"' in body
        assert 'id="apply-here-note"' in body


def test_apply_redirects_to_the_wallet_with_a_303() -> None:
    response = client.get("/apply", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "https://cred-demo-wallet.onrender.com"


def test_no_script_tag_on_any_benefits_page() -> None:
    for path in ["/", "/programs/food", "/programs/energy", "/programs/housing",
                 "/programs/health", "/programs/dividend"]:
        assert "<script" not in client.get(path).text
