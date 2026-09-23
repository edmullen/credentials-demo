"""Employer sections on the landing page, and the paystub detail view (design.md §6, issue #18)."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

P01_16_30 = "b53638d6-8ff1-51a6-9e33-a6df833c8cba"  # Grace Okafor, hourly
P09_16_30 = "4c491125-916b-50a0-9510-9bfd982b7b59"  # Daniel Walsh, salaried


def test_single_employer_landing_page_has_one_section() -> None:
    body = client.get("/p/p01/paystubs").text
    assert body.count('class="category"') == 1
    assert body.count('class="paylist__row"') == 2
    assert "Pinecrest Home Care" in body
    assert "Home health aide · Trenton, NJ" in body


def test_three_employer_landing_page_has_sections_in_stub_order() -> None:
    body = client.get("/p/p08/paystubs").text
    assert body.count('class="category"') == 3
    assert body.count('class="paylist__row"') == 6
    shoreway = body.index("Shoreway Supermarkets")
    brightpath = body.index("Brightpath Early Learning")
    ridgeline = body.index("Ridgeline Home &amp; Hardware")
    assert shoreway < brightpath < ridgeline


def test_paylist_row_links_to_the_detail_route() -> None:
    body = client.get("/p/p01/paystubs").text
    assert f'href="/p/p01/paystubs/{P01_16_30}"' in body


def test_mismatched_paystub_id_is_404() -> None:
    # P09's paystub id, requested as p01 — not that person's.
    assert client.get(f"/p/p01/paystubs/{P09_16_30}").status_code == 404


def test_unknown_paystub_id_is_404() -> None:
    assert client.get("/p/p01/paystubs/00000000-0000-0000-0000-000000000000").status_code == 404


def test_hourly_detail_shows_the_figures() -> None:
    response = client.get(f"/p/p01/paystubs/{P01_16_30}")
    assert response.status_code == 200
    body = response.text
    assert "<h1" in body and "16–30 September 2026" in body
    assert "Pinecrest Home Care" in body
    assert "Trenton, NJ" in body
    assert "Grace Okafor" in body
    assert "Home health aide" in body
    assert "Semimonthly" in body
    assert '<th scope="col">Hours</th>' in body
    assert "$20.00" in body and "55.00" in body and "$1,100.00" in body
    assert "$44.38" in body  # federal income tax
    assert "$68.20" in body  # Social Security
    assert "$15.95" in body  # Medicare
    assert "$15.60" in body  # state income tax
    assert "$144.13" in body  # total deductions
    assert "$955.87" in body  # net pay
    assert body.count("Withholding on this statement is estimated") == 1


def test_deduction_lines_are_in_order() -> None:
    body = client.get(f"/p/p01/paystubs/{P01_16_30}").text
    order = ["Federal income tax", "Social Security", "Medicare", "State income tax"]
    positions = [body.index(label) for label in order]
    assert positions == sorted(positions)


def test_salaried_detail_shows_installment_not_hours() -> None:
    response = client.get(f"/p/p09/paystubs/{P09_16_30}")
    assert response.status_code == 200
    body = response.text
    assert '<th scope="col">Installment</th>' in body
    assert '<th scope="col">Hours</th>' not in body
    assert "Salary" in body
    assert "$92,000.00" in body
    assert "18 of 24" in body
    assert "$3,833.33" in body


def test_amount_column_keeps_the_this_period_head_for_number_50() -> None:
    body = client.get(f"/p/p01/paystubs/{P01_16_30}").text
    assert body.count('class="figures__amount">This period</th>') == 2  # earnings + deductions


def test_back_link_returns_to_the_landing_page() -> None:
    body = client.get(f"/p/p01/paystubs/{P01_16_30}").text
    assert '<a class="back" href="/p/p01/paystubs">All paystubs</a>' in body


def test_detail_page_has_no_current_nav_item() -> None:
    body = client.get(f"/p/p01/paystubs/{P01_16_30}").text
    assert "aria-current" not in body


def test_each_figures_table_scrolls_in_a_labelled_focusable_region() -> None:
    """Loop 4a (docs/design.md §8): a wide table scrolls sideways on a phone."""
    body = client.get(f"/p/p01/paystubs/{P01_16_30}").text
    for caption, fid in (("Earnings", "fig-earnings"), ("Deductions", "fig-deductions")):
        region = f'<div class="figures__scroll" role="region" aria-labelledby="{fid}" tabindex="0">'
        start = body.index(region)
        table = body.index('<table class="figures">', start)
        assert body.index(f'<caption id="{fid}">{caption}</caption>', table) < body.index("</table>", table)
        assert body.index("</table>", table) < body.index("</div>", table)
