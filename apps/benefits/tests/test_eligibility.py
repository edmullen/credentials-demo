"""The eligibility engine against the sample-data oracle (docs/design.md §4, §14)."""

import json
from decimal import Decimal
from pathlib import Path

import pytest

from app.eligibility import decide

ORACLE = json.loads((Path(__file__).parent / "oracle.json").read_text())


@pytest.mark.parametrize("row", ORACLE["rows"], ids=[r["person"] for r in ORACLE["rows"]])
def test_oracle_row(row: dict) -> None:
    d = decide("NJ", row["county"], [Decimal(row["monthly"])])
    assert d.monthly == Decimal(row["monthly"])
    assert d.annual == Decimal(row["annual"])
    assert d.program("health").discount_percent == Decimal(row["health_discount"])
    assert (d.program("food").outcome == "eligible") == row["food"]
    assert (d.program("energy").outcome == "eligible") == row["energy"]
    assert (d.program("housing").outcome == "eligible") == row["housing"]
    assert d.program("dividend").monthly_payment == Decimal(row["dividend"])
    for code in ("food", "energy", "housing"):
        result = d.program(code)
        if result.outcome == "denied":
            assert result.reason == "income_over_limit"


@pytest.mark.parametrize("region", ["MI", "NY", "OH"])
def test_out_of_state_denies_all_five_with_not_nj_resident(region: str) -> None:
    # Region alone gates the decision (docs/benefit-programs.md, "shared criteria"); the county
    # and income are irrelevant once residency fails (docs/design.md §4).
    d = decide(region, "Hunterdon", [Decimal("5000.00")])
    assert len(d.programs) == 5
    for result in d.programs:
        assert result.outcome == "denied"
        assert result.reason == "not_nj_resident"
        assert result.limit is None
        assert result.discount_percent is None
        assert result.monthly_payment is None


def test_program_order_is_always_food_energy_housing_health_dividend() -> None:
    d = decide("NJ", "Hunterdon", [Decimal("2200.00")])
    assert [p.program for p in d.programs] == ["food", "energy", "housing", "health", "dividend"]
    d = decide("MI", "Hunterdon", [Decimal("2200.00")])
    assert [p.program for p in d.programs] == ["food", "energy", "housing", "health", "dividend"]


def _at_and_over(limit: Decimal) -> tuple[Decimal, Decimal]:
    """Monthly figures that annualize to exactly `limit` and to one cent over it. The engine
    takes monthly gross, not annual, so "one cent over" is expressed as the monthly figure
    whose ×12 lands exactly one annual cent past the limit (docs/design.md §4, §14)."""
    return limit / 12, (limit + Decimal("0.01")) / 12


def test_food_limit_is_inclusive_and_denied_one_cent_over() -> None:
    # Food: 185% of FPL 15,960 = 29,526.00 annual.
    limit = Decimal("29526.00")
    at_monthly, over_monthly = _at_and_over(limit)
    at_limit = decide("NJ", "Hunterdon", [at_monthly])
    assert at_limit.annual == limit
    assert at_limit.program("food").outcome == "eligible"

    over_limit = decide("NJ", "Hunterdon", [over_monthly])
    assert over_limit.annual == limit + Decimal("0.01")
    assert over_limit.program("food").outcome == "denied"
    assert over_limit.program("food").reason == "income_over_limit"


def test_energy_limit_is_inclusive_and_denied_one_cent_over() -> None:
    # Energy: 60% of SMI 50,000 = 30,000.00 annual.
    limit = Decimal("30000.00")
    at_monthly, over_monthly = _at_and_over(limit)
    at_limit = decide("NJ", "Hunterdon", [at_monthly])
    assert at_limit.annual == limit
    assert at_limit.program("energy").outcome == "eligible"

    over_limit = decide("NJ", "Hunterdon", [over_monthly])
    assert over_limit.annual == limit + Decimal("0.01")
    assert over_limit.program("energy").outcome == "denied"
    assert over_limit.program("energy").reason == "income_over_limit"


def test_housing_limit_is_inclusive_and_denied_one_cent_over_for_its_county() -> None:
    # Cumberland: 30% of AMI 64,499 = 19,349.70 annual.
    limit = Decimal("19349.70")
    at_monthly, over_monthly = _at_and_over(limit)
    at_limit = decide("NJ", "Cumberland", [at_monthly])
    assert at_limit.annual == limit
    assert at_limit.program("housing").outcome == "eligible"

    over_limit = decide("NJ", "Cumberland", [over_monthly])
    assert over_limit.annual == limit + Decimal("0.01")
    assert over_limit.program("housing").outcome == "denied"
    assert over_limit.program("housing").reason == "income_over_limit"


def test_health_discount_rounds_half_tenth_boundary_half_even() -> None:
    # Health's discount percent is quantized to the cent half-up, then to one decimal
    # half-even (docs/design.md §4), matching tools/generate_sample_data.py's oracle output.
    d = decide("NJ", "Hunterdon", [Decimal("2200.00")])
    assert d.program("health").discount_percent == Decimal("92.4")


def test_health_full_discount_at_or_below_138_percent_fpl() -> None:
    # 138% of FPL 15,960 = 22,024.80 annual.
    at_ceiling = decide("NJ", "Hunterdon", [Decimal("22024.80") / 12])
    assert at_ceiling.program("health").discount_percent == Decimal("100.0")
    below = decide("NJ", "Hunterdon", [Decimal("0")])
    assert below.program("health").discount_percent == Decimal("100.0")


def test_health_zero_discount_at_or_above_500_percent_fpl() -> None:
    # 500% of FPL 15,960 = 79,800.00 annual.
    at_floor = decide("NJ", "Hunterdon", [Decimal("79800.00") / 12])
    assert at_floor.program("health").discount_percent == Decimal("0.0")
    above = decide("NJ", "Hunterdon", [Decimal("100000.00") / 12])
    assert above.program("health").discount_percent == Decimal("0.0")


def test_health_is_never_denied() -> None:
    for monthly in ("0", "1000000.00"):
        d = decide("NJ", "Hunterdon", [Decimal(monthly)])
        assert d.program("health").outcome == "eligible"


@pytest.mark.parametrize(
    "monthly, expected",
    [("0", "400.00"), ("200", "350.00"), ("400", "300.00"), ("600", "250.00"),
     ("800", "200.00"), ("1000", "150.00"), ("1200", "100.00"), ("2400", "100.00")],
)
def test_dividend_taper_matches_benefit_programs_table(monthly: str, expected: str) -> None:
    d = decide("NJ", "Hunterdon", [Decimal(monthly)])
    assert d.program("dividend").monthly_payment == Decimal(expected)


def test_dividend_is_never_denied() -> None:
    for monthly in ("0", "1000000.00"):
        d = decide("NJ", "Hunterdon", [Decimal(monthly)])
        assert d.program("dividend").outcome == "eligible"


def test_multiple_paystubs_are_summed_before_annualizing() -> None:
    two_employers = decide("NJ", "Hunterdon", [Decimal("1100.00"), Decimal("1100.00")])
    one_employer = decide("NJ", "Hunterdon", [Decimal("2200.00")])
    assert two_employers.monthly == one_employer.monthly == Decimal("2200.00")
    assert two_employers.annual == one_employer.annual
