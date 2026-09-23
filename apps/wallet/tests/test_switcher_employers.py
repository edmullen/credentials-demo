"""Each person's employers in the switcher, a demo aid only (docs/design.md §7)."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.people import all_people

client = TestClient(app)
APP_DIR = Path(__file__).resolve().parent.parent / "app"


def _line(names: list[str]) -> str:
    label = "Employer" if len(names) == 1 else "Employers"
    listed = ", ".join(names).replace("&", "&amp;")  # autoescaped
    return f'<span class="people__employers">{label}: {listed}</span>'


def test_every_person_has_at_least_one_employer_name() -> None:
    assert all(p["employerNames"] for p in all_people())


def test_one_employer_is_singular() -> None:
    body = client.get("/p/p01/switch").text
    assert '<span class="people__employers">Employer: Pinecrest Home Care</span>' in body


def test_several_employers_are_listed_in_job_order() -> None:
    body = client.get("/p/p01/switch").text
    assert (
        '<span class="people__employers">Employers: Shoreway Supermarkets, '
        "Brightpath Early Learning, Ridgeline Home &amp; Hardware</span>"
    ) in body  # p08, as in the handoff


def test_every_row_shows_its_employers_under_the_place() -> None:
    body = client.get("/p/p01/switch").text
    for p in all_people():
        place = body.index(f'<span class="people__place">{p["place"]}</span>', body.index(f'aria-label="{p["name"]}"'))
        assert body.index(_line(p["employerNames"]), place) > place
    assert body.count('class="people__employers"') == len(all_people())


def test_employer_names_are_read_only_by_the_switcher() -> None:
    """Connect logic must never use them: Payroll decides who is an employee."""
    readers = sorted(
        str(path.relative_to(APP_DIR))
        for path in APP_DIR.rglob("*")
        if path.suffix in {".py", ".html"} and "employerNames" in path.read_text()
    )
    assert readers == ["people.py", "templates/switch.html"]
