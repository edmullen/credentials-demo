"""The eligibility engine (docs/design.md §4). Plain functions, no I/O: `rules()` reads
data/rules.json once and every other function is pure over Decimal input. This is the tested
core that presentation.py (call 2) and the program pages (§7) both build on, so the page a
person reads and the decision Benefits makes can't disagree.

Arithmetic mirrors tools/generate_sample_data.py exactly, because that script produced
docs/sample-data.md's oracle (tests/oracle.json is a copy of it): monthly = sum of gross pay,
annual = monthly × 12, and discountPercent is quantized to the cent half-up, then to one
decimal half-even — the same two steps generate_sample_data.py takes via `cents(...)` and
`:.1f` when it prints the oracle table.
"""

import json
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

# Program order, used everywhere a determination is decided, issued or displayed (call 2,
# credentials, the admin view).
PROGRAMS = ("food", "energy", "housing", "health", "dividend")

CENT = Decimal("0.01")
TENTH = Decimal("0.1")


def _cents(amount: Decimal) -> Decimal:
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


@lru_cache
def rules() -> dict:
    return json.loads((DATA_DIR / "rules.json").read_text())


@dataclass(frozen=True)
class ProgramResult:
    program: str
    outcome: str  # "eligible" | "denied"
    reason: str | None = None  # "income_over_limit" | "not_nj_resident", set when denied
    limit: Decimal | None = None  # food/energy/housing: the annual limit compared against
    discount_percent: Decimal | None = None  # health: one decimal place
    plan_cost: Decimal | None = None  # health
    monthly_payment: Decimal | None = None  # dividend


@dataclass(frozen=True)
class Determination:
    monthly: Decimal
    annual: Decimal
    programs: tuple[ProgramResult, ...]  # always five, in PROGRAMS order

    def program(self, code: str) -> ProgramResult:
        return next(p for p in self.programs if p.program == code)


def _not_nj_resident(monthly: Decimal, annual: Decimal) -> Determination:
    return Determination(
        monthly=monthly,
        annual=annual,
        programs=tuple(
            ProgramResult(program=code, outcome="denied", reason="not_nj_resident")
            for code in PROGRAMS
        ),
    )


def _pass_fail(code: str, annual: Decimal, limit: Decimal) -> ProgramResult:
    if annual <= limit:
        return ProgramResult(program=code, outcome="eligible", limit=limit)
    return ProgramResult(program=code, outcome="denied", reason="income_over_limit", limit=limit)


def _health(annual: Decimal, r: dict) -> ProgramResult:
    ceiling = Decimal(r["health"]["full_discount_ceiling_pct"]) * Decimal(r["federal_poverty_level"])
    floor = Decimal(r["health"]["zero_discount_floor_pct"]) * Decimal(r["federal_poverty_level"])
    if annual <= ceiling:
        discount = Decimal(1)
    elif annual >= floor:
        discount = Decimal(0)
    else:
        discount = (floor - annual) / (floor - ceiling)
    percent = _cents(discount * 100).quantize(TENTH, rounding=ROUND_HALF_EVEN)
    return ProgramResult(
        program="health",
        outcome="eligible",
        discount_percent=percent,
        plan_cost=Decimal(r["health"]["plan_cost"]),
    )


def _dividend(monthly: Decimal, r: dict) -> ProgramResult:
    base = Decimal(r["dividend"]["base"])
    max_bump = Decimal(r["dividend"]["max_bump"])
    phase_out = Decimal(r["dividend"]["phase_out"])
    taper = max_bump / phase_out
    payment = _cents(base + max(Decimal(0), max_bump - taper * monthly))
    return ProgramResult(program="dividend", outcome="eligible", monthly_payment=payment)


def decide(region: str, county: str, gross_pays: list[Decimal]) -> Determination:
    """`region` is the identity credential's address.addressRegion, `county` its address.county,
    and `gross_pays` every held paystub's grossPay.value (docs/design.md §4, §6)."""
    monthly = sum(gross_pays, Decimal(0))
    annual = monthly * 12
    if region != "NJ":
        return _not_nj_resident(monthly, annual)

    r = rules()
    fpl = Decimal(r["federal_poverty_level"])
    smi = Decimal(r["state_median_income"])
    food_limit = Decimal(r["food_limit_pct"]) * fpl
    energy_limit = Decimal(r["energy_limit_pct"]) * smi
    housing_limit = Decimal(r["county_ami"][county]) * Decimal(r["housing_share_pct"])

    programs = (
        _pass_fail("food", annual, food_limit),
        _pass_fail("energy", annual, energy_limit),
        _pass_fail("housing", annual, housing_limit),
        _health(annual, r),
        _dividend(monthly, r),
    )
    return Determination(monthly=monthly, annual=annual, programs=programs)
