# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Generate the Wallet's data from the sample data.

Run by hand from the repo root:

    uv run tools/generate_credentials.py

Reads   tools/sample_data/generated/people.json
Writes  apps/wallet/app/data/people.json

A one-shot generator with committed output, as docs/decisions.md allows: nothing runs it at
build or deploy time. Deterministic, so re-running with unchanged input changes nothing.

The Wallet's people.json carries only what a screen shows. It deliberately has no identity
status: the switcher's badge comes from verifying each person's credential (docs/design.md §2),
not from a field the app would have to trust.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_PEOPLE = ROOT / "tools" / "sample_data" / "generated" / "people.json"
WALLET_DATA = ROOT / "apps" / "wallet" / "app" / "data"


def wallet_person(person: dict) -> dict:
    return {
        "id": person["id"],
        "givenName": person["givenName"],
        "familyName": person["familyName"],
        "initials": person["givenName"][0] + person["familyName"][0],
        "locality": person["address"]["locality"],
        "region": person["address"]["region"],
    }


def write_json(name: str, data) -> None:
    WALLET_DATA.mkdir(parents=True, exist_ok=True)
    (WALLET_DATA / name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def main() -> None:
    people = json.loads(SAMPLE_PEOPLE.read_text())
    write_json("people.json", [wallet_person(p) for p in sorted(people, key=lambda p: p["id"])])
    print(f"Wrote {len(people)} people to {WALLET_DATA.relative_to(ROOT)}/people.json")


if __name__ == "__main__":
    main()
