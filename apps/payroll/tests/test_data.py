"""The committed data slice under apps/payroll/app/data/ (design.md §2, §3)."""

import json
import re
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "app" / "data"
SUBJECT_ID_RE = re.compile(r"^urn:uuid:[0-9a-f-]{36}$")

PROJECTED_FIELDS = {"id", "subjectId", "givenName", "familyName", "initials", "locality", "region"}


def _people() -> list[dict]:
    return json.loads((DATA_DIR / "people.json").read_text())


def _employers() -> list[dict]:
    return json.loads((DATA_DIR / "employers.json").read_text())


def _paystubs() -> list[dict]:
    return json.loads((DATA_DIR / "paystubs.json").read_text())


def test_people_has_25_records_in_order() -> None:
    people = _people()
    assert len(people) == 25
    assert [p["id"] for p in people] == [f"p{i:02d}" for i in range(1, 26)]


def test_people_is_the_projection_only() -> None:
    # Exact equality means birthDate, address, photo, photoBrief, identity and jobs are all
    # necessarily absent (design.md §2) — no separate check needed for what's excluded.
    for person in _people():
        assert set(person.keys()) == PROJECTED_FIELDS


def test_every_subject_id_is_a_urn_uuid() -> None:
    for person in _people():
        assert SUBJECT_ID_RE.match(person["subjectId"]), person


def test_employers_and_paystubs_counts() -> None:
    assert len(_employers()) == 15
    assert len(_paystubs()) == 64


def test_every_paystub_references_a_valid_person_and_employer() -> None:
    person_ids = {p["id"] for p in _people()}
    employer_ids = {e["id"] for e in _employers()}
    for stub in _paystubs():
        assert stub["personId"] in person_ids
        assert stub["employerId"] in employer_ids


def test_every_person_has_at_least_one_paystub() -> None:
    # Payroll has no reachable empty state this loop (design.md §11 item 15) — this guard
    # means the day that stops being true, a test fails loudly instead of a blank section.
    covered = {s["personId"] for s in _paystubs()}
    assert covered == {p["id"] for p in _people()}


def test_employers_and_paystubs_are_verbatim_copies() -> None:
    sample_dir = DATA_DIR.parent.parent.parent.parent / "tools" / "sample_data" / "generated"
    assert (DATA_DIR / "employers.json").read_text() == (sample_dir / "employers.json").read_text()
    assert (DATA_DIR / "paystubs.json").read_text() == (sample_dir / "paystubs.json").read_text()
