"""Generate Payroll's data slice: people, employers and paystubs.

Run by hand from the repo root:

    uv run tools/generate_payroll_data.py

Reads   tools/sample_data/generated/{people,employers,paystubs}.json
Writes  apps/payroll/app/data/{people,employers,paystubs}.json

A one-shot generator with committed output, as docs/decisions.md allows: nothing runs it at
build or deploy time, and it regenerates nothing upstream — it never reads the hand-written
YAML and never writes tools/sample_data/generated/ or docs/sample-data.md, so
tools/generate_sample_data.py and its curated-placement self-checks are untouched.

What it builds is docs/design.md §2: employers.json and paystubs.json are copied verbatim,
because they already carry everything a stub renders. people.json is a projection, not a
copy — decisions.md requires each app to keep only the slice it needs, and Payroll's screens
show a person's name, initials, locality/region and subjectId, nothing else. birthDate,
street address, county, postal code, photo, identity status and jobs are deliberately
dropped; employment has one home in this app's data, the paystubs (design.md §11 item 6).
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DATA = ROOT / "tools" / "sample_data" / "generated"
PAYROLL_DATA = ROOT / "apps" / "payroll" / "app" / "data"


def payroll_person(person: dict) -> dict:
    """Only what a screen shows. No jobs, no identity status (design.md §2)."""
    return {
        "id": person["id"],
        "subjectId": person["subjectId"],
        "givenName": person["givenName"],
        "familyName": person["familyName"],
        "initials": person["givenName"][0] + person["familyName"][0],
        "locality": person["address"]["locality"],
        "region": person["address"]["region"],
    }


def write_json(name: str, data) -> None:
    PAYROLL_DATA.mkdir(parents=True, exist_ok=True)
    (PAYROLL_DATA / name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def main() -> None:
    people = json.loads((SAMPLE_DATA / "people.json").read_text())
    employers = json.loads((SAMPLE_DATA / "employers.json").read_text())
    paystubs = json.loads((SAMPLE_DATA / "paystubs.json").read_text())

    write_json("people.json", [payroll_person(p) for p in people])
    write_json("employers.json", employers)
    write_json("paystubs.json", paystubs)

    print(f"People:    {len(people)} (projected)")
    print(f"Employers: {len(employers)} (verbatim)")
    print(f"Paystubs:  {len(paystubs)} (verbatim)")


if __name__ == "__main__":
    main()
