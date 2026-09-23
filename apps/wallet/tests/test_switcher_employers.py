"""Each person's employers in the switcher, a demo aid only (docs/design.md §7)."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.people import all_people

client = TestClient(app)
APP_DIR = Path(__file__).resolve().parent.parent / "app"


def test_every_person_has_at_least_one_employer_name() -> None:
    assert all(p["employerNames"] for p in all_people())


def test_one_employer_is_singular() -> None:
    body = client.get("/p/p01/switch").text
    assert '<span class="people__place">Employer: Pinecrest Home Care</span>' in body


def test_several_employers_are_listed_in_job_order() -> None:
    body = client.get("/p/p01/switch").text
    p06 = next(p for p in all_people() if p["id"] == "p06")
    assert len(p06["employerNames"]) == 2
    listed = ", ".join(p06["employerNames"]).replace("&", "&amp;")  # autoescaped
    assert f'<span class="people__place">Employers: {listed}</span>' in body


def test_every_row_shows_its_employers() -> None:
    body = client.get("/p/p01/switch").text
    assert body.count("<span class=\"people__place\">Employer") == len(all_people())


def test_employer_names_are_read_only_by_the_switcher() -> None:
    """Connect logic must never use them: Payroll decides who is an employee."""
    readers = sorted(
        str(path.relative_to(APP_DIR))
        for path in APP_DIR.rglob("*")
        if path.suffix in {".py", ".html"} and "employerNames" in path.read_text()
    )
    assert readers == ["people.py", "templates/switch.html"]
