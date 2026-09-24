"""Program display data (docs/design.md §9.1). Pinned against the same fixed list the Wallet's
own copy is pinned against — no cross-app read, per the monorepo rule."""

from app.programs import all_programs, get_program

EXPECTED = [
    ("food", "Food Assistance"),
    ("energy", "Energy Assistance"),
    ("housing", "Housing Assistance"),
    ("health", "Health"),
    ("dividend", "Dividend"),
]


def test_programs_match_the_five_in_order() -> None:
    assert [(p["code"], p["name"]) for p in all_programs()] == EXPECTED


def test_get_program_looks_up_by_code() -> None:
    assert get_program("health")["name"] == "Health"
    assert get_program("nonexistent") is None
