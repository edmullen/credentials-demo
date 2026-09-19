# /// script
# requires-python = ">=3.12"
# dependencies = ["pyyaml>=6", "pillow>=10"]
# ///
"""Generate the demo's sample data from the hand-written files in tools/sample_data/.

Run by hand from the repo root:

    uv run tools/generate_sample_data.py

Reads   tools/sample_data/people.yaml, tools/sample_data/employers.yaml,
        tools/sample_data/photos/pNN.jpg
Writes  tools/sample_data/generated/{people,employers,paystubs}.json
        docs/sample-data.md  (expected outcomes, the Loop 6 test oracle, and the photos)

A one-shot generator with committed output, as docs/decisions.md allows: no app imports or
runs it. Output is deterministic — subject identifiers are name-based UUIDs and nothing
depends on today's date — so re-running with unchanged input changes nothing.

Money is handled in Decimal and written to JSON as strings ("1100.00") so no reader has to
trust floating point. Eligibility rules are docs/benefit-programs.md; if the two disagree,
the doc is right and this script is wrong.
"""

import json
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "tools" / "sample_data"
PHOTOS = SRC / "photos"
OUT = SRC / "generated"
DOC = ROOT / "docs" / "sample-data.md"

# Fixed so output never depends on the day the script runs.
AS_OF = date(2026, 9, 30)
PAY_PERIODS = [(date(2026, 9, 1), date(2026, 9, 15)), (date(2026, 9, 16), date(2026, 9, 30))]
MIN_HOURLY_RATE = Decimal("16.00")  # at or above NJ's 2026 minimum wage

# Identity photos arrive already processed (docs/credential-model.md §3): AI-generated,
# portrait, ID-photo style, metadata stripped. The generator checks them; it doesn't alter them.
PHOTO_SIZE = (200, 250)
PHOTO_MAX_BYTES = 25_000

# Stable namespace for name-based subject and paystub identifiers.
NAMESPACE = uuid.UUID("6f1c2a4e-2d7b-5c1e-9a3f-0b8d4e7c1a52")

CENT = Decimal("0.01")

# ---- Eligibility variables (docs/benefit-programs.md, as of September 2026) ----------------

FPL = Decimal("15960")
SMI = Decimal("50000")
COUNTY_AMI = {
    "Hunterdon": 139453, "Somerset": 135960, "Morris": 134929, "Bergen": 123715,
    "Monmouth": 122727, "Sussex": 114316, "Middlesex": 109028, "Burlington": 105271,
    "Gloucester": 102807, "Union": 100117, "Warren": 99596, "Mercer": 96333,
    "Hudson": 90032, "Cape May": 88046, "Passaic": 87137, "Ocean": 86411,
    "Camden": 86384, "Salem": 78412, "Atlantic": 76819, "Essex": 76712,
    "Cumberland": 64499,
}
HEALTH_PLAN_COST = Decimal("750")
HEALTH_FULL_DISCOUNT_CEILING = Decimal("1.38") * FPL  # 100% discount at or below
HEALTH_ZERO_DISCOUNT_FLOOR = Decimal("5.00") * FPL    # full price at or above
FOOD_LIMIT = Decimal("1.85") * FPL
ENERGY_LIMIT = Decimal("0.60") * SMI
HOUSING_SHARE = Decimal("0.30")
DIVIDEND_BASE = Decimal("100")
DIVIDEND_MAX_BUMP = Decimal("300")
DIVIDEND_PHASE_OUT = Decimal("1200")

# ---- Withholding approximations — display only; eligibility uses gross ---------------------
# 2025 single-filer federal brackets and standard deduction, and NJ's single brackets, applied
# to everyone regardless of where they live or work. No pre-tax deductions. Each employer
# withholds on its own paystub alone, as real employers do.

FEDERAL_STANDARD_DEDUCTION = Decimal("15750")
FEDERAL_BRACKETS = [(11925, "0.10"), (48475, "0.12"), (103350, "0.22"), (197300, "0.24"), (None, "0.32")]
NJ_EXEMPTION = Decimal("1000")
NJ_BRACKETS = [(20000, "0.014"), (35000, "0.0175"), (40000, "0.035"), (75000, "0.05525"), (None, "0.0637")]
SOCIAL_SECURITY_RATE = Decimal("0.062")
MEDICARE_RATE = Decimal("0.0145")


def cents(amount: Decimal) -> Decimal:
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def money(amount: Decimal) -> str:
    return f"{cents(amount):.2f}"


def progressive_tax(taxable: Decimal, brackets) -> Decimal:
    tax, lower = Decimal(0), Decimal(0)
    for upper, rate in brackets:
        top = taxable if upper is None else min(taxable, Decimal(upper))
        if top > lower:
            tax += (top - lower) * Decimal(rate)
        if upper is None or taxable <= upper:
            break
        lower = Decimal(upper)
    return tax


def withholding(gross: Decimal) -> dict[str, Decimal]:
    annualized = gross * 24
    federal = progressive_tax(max(Decimal(0), annualized - FEDERAL_STANDARD_DEDUCTION), FEDERAL_BRACKETS) / 24
    state = progressive_tax(max(Decimal(0), annualized - NJ_EXEMPTION), NJ_BRACKETS) / 24
    return {
        "federalIncomeTax": cents(federal),
        "socialSecurity": cents(gross * SOCIAL_SECURITY_RATE),
        "medicare": cents(gross * MEDICARE_RATE),
        "stateIncomeTax": cents(state),
    }


def pay_date(period_end: date) -> date:
    """Paid on the last day of the period, or the Friday before if that falls on a weekend."""
    while period_end.weekday() >= 5:
        period_end -= timedelta(days=1)
    return period_end


def age(birth: date) -> int:
    return AS_OF.year - birth.year - ((AS_OF.month, AS_OF.day) < (birth.month, birth.day))


def gross_per_period(pay: dict) -> Decimal:
    if pay["type"] == "hourly":
        return cents(Decimal(str(pay["rate"])) * Decimal(str(pay["hours"])))
    if pay["type"] == "salary":
        return cents(Decimal(str(pay["annual"])) / 24)
    raise ValueError(f"unknown pay type {pay['type']!r}")


# ---- Eligibility ---------------------------------------------------------------------------


@dataclass
class Outcome:
    """What Benefits should decide for one person. `gate` is set when nothing is evaluated."""

    gate: str | None
    monthly: Decimal
    annual: Decimal
    health_discount: Decimal | None = None
    food: bool | None = None
    energy: bool | None = None
    housing: bool | None = None
    dividend: Decimal | None = None


def evaluate(person: dict, monthly: Decimal) -> Outcome:
    annual = monthly * 12
    if person["identity"] == "none":
        return Outcome("credential_missing", monthly, annual)
    if person["identity"] == "tampered":
        return Outcome("credential_invalid", monthly, annual)
    if person["address"]["region"] != "NJ":
        return Outcome("not_nj_resident", monthly, annual)

    if annual <= HEALTH_FULL_DISCOUNT_CEILING:
        discount = Decimal(1)
    elif annual >= HEALTH_ZERO_DISCOUNT_FLOOR:
        discount = Decimal(0)
    else:
        discount = (HEALTH_ZERO_DISCOUNT_FLOOR - annual) / (HEALTH_ZERO_DISCOUNT_FLOOR - HEALTH_FULL_DISCOUNT_CEILING)

    housing_limit = Decimal(COUNTY_AMI[person["address"]["county"]]) * HOUSING_SHARE
    taper = DIVIDEND_MAX_BUMP / DIVIDEND_PHASE_OUT
    dividend = cents(DIVIDEND_BASE + max(Decimal(0), DIVIDEND_MAX_BUMP - taper * monthly))

    return Outcome(
        gate=None,
        monthly=monthly,
        annual=annual,
        health_discount=discount,
        food=annual <= FOOD_LIMIT,
        energy=annual <= ENERGY_LIMIT,
        housing=annual <= housing_limit,
        dividend=dividend,
    )


# ---- Build ---------------------------------------------------------------------------------


def load() -> tuple[list[dict], dict[str, dict]]:
    people = yaml.safe_load((SRC / "people.yaml").read_text())["people"]
    employers = {e["id"]: e for e in yaml.safe_load((SRC / "employers.yaml").read_text())["employers"]}
    return people, employers


def subject_id(person: dict) -> str:
    return f"urn:uuid:{uuid.uuid5(NAMESPACE, 'subject:' + person['id'])}"


def build_paystubs(person: dict, employers: dict[str, dict]) -> list[dict]:
    stubs = []
    for job in person["jobs"]:
        employer = employers[job["employer"]]
        gross = gross_per_period(job["pay"])
        for start, end in PAY_PERIODS:
            deductions = withholding(gross)
            key = f"paystub:{person['id']}:{employer['id']}:{start.isoformat()}"
            stubs.append({
                "id": f"urn:uuid:{uuid.uuid5(NAMESPACE, key)}",
                "personId": person["id"],
                "subjectId": subject_id(person),
                "employerId": employer["id"],
                "employerName": employer["name"],
                "title": job["title"],
                "payType": job["pay"]["type"],
                **({"hourlyRate": money(Decimal(str(job["pay"]["rate"]))), "hours": str(job["pay"]["hours"])}
                   if job["pay"]["type"] == "hourly" else
                   {"annualSalary": money(Decimal(str(job["pay"]["annual"])))}),
                "payPeriodStart": start.isoformat(),
                "payPeriodEnd": end.isoformat(),
                "payDate": pay_date(end).isoformat(),
                "payFrequency": "semimonthly",
                "grossPay": money(gross),
                "deductions": {k: money(v) for k, v in deductions.items()},
                "netPay": money(gross - sum(deductions.values())),
            })
    return stubs


def check_invariants(people: list[dict], employers: dict, outcomes: dict[str, Outcome]) -> None:
    """The curated placements #6 depends on. Fails loudly if an edit breaks one."""
    problems = []

    def need(condition: bool, message: str) -> None:
        if not condition:
            problems.append(message)

    status = Counter(p["identity"] for p in people)
    need(len(people) == 25, f"expected 25 people, found {len(people)}")
    need(status == Counter(verified=21, tampered=2, none=2), f"identity split is {dict(status)}")
    nj_verified = [p for p in people if p["identity"] == "verified" and p["address"]["region"] == "NJ"]
    need(len(nj_verified) == 18, f"expected 18 NJ-verified people, found {len(nj_verified)}")
    out_of_state = {(p["address"]["locality"], p["address"]["region"]) for p in people
                    if p["identity"] == "verified" and p["address"]["region"] != "NJ"}
    need(out_of_state == {("Livonia", "MI"), ("Astoria", "NY"), ("Cleveland", "OH")},
         f"out-of-state people are {out_of_state}")
    tamper_kinds = sorted(p["tamper"]["kind"] for p in people if p["identity"] == "tampered")
    need(tamper_kinds == ["address", "photo"], f"tamper kinds are {tamper_kinds}")
    need(len(employers) == 15, f"expected 15 employers, found {len(employers)}")
    used = {j["employer"] for p in people for j in p["jobs"]}
    need(used == set(employers), f"unused employers: {set(employers) - used}; unknown: {used - set(employers)}")
    jobs = Counter(len(p["jobs"]) for p in people)
    need(jobs[2] >= 2 and jobs[3] >= 2 and all(1 <= n <= 3 for n in jobs), f"jobs per person: {dict(jobs)}")
    for p in people:
        for j in p["jobs"]:
            if j["pay"]["type"] == "hourly":
                need(Decimal(str(j["pay"]["rate"])) >= MIN_HOURLY_RATE, f"{p['id']} is paid below ${MIN_HOURLY_RATE}")
        need(p["identity"] == "none" or bool(p.get("photo_brief")), f"{p['id']} holds a credential but has no photo brief")
        if p["address"]["region"] == "NJ":
            need(p["address"]["county"] in COUNTY_AMI, f"{p['id']} has unknown county {p['address']['county']!r}")

    needs_photo = {p["id"] for p in people if p["identity"] != "none"}
    supplied = {f.stem for f in PHOTOS.glob("*.jpg")}
    need(supplied == needs_photo,
         f"photos missing for {sorted(needs_photo - supplied)}; unexpected photos {sorted(supplied - needs_photo)}")
    for stem in sorted(supplied & needs_photo):
        path = PHOTOS / f"{stem}.jpg"
        with Image.open(path) as im:
            need(im.format == "JPEG", f"{path.name} is {im.format}, not JPEG")
            need(im.size == PHOTO_SIZE, f"{path.name} is {im.size[0]}x{im.size[1]}, not {PHOTO_SIZE[0]}x{PHOTO_SIZE[1]}")
            need(len(im.getexif()) == 0 and "xmp" not in im.info and "icc_profile" not in im.info,
                 f"{path.name} carries metadata; strip it before committing")
        need(path.stat().st_size <= PHOTO_MAX_BYTES, f"{path.name} is {path.stat().st_size} bytes, over {PHOTO_MAX_BYTES}")

    evaluated = {pid: o for pid, o in outcomes.items() if o.gate is None}
    # Same income, different Housing answer, in the highest- and lowest-AMI counties.
    by_county = {next(p for p in people if p["id"] == pid)["address"]["county"]: o for pid, o in evaluated.items()}
    hi, lo = by_county.get("Hunterdon"), by_county.get("Cumberland")
    need(hi is not None and lo is not None and hi.annual == lo.annual and hi.housing and not lo.housing,
         "the Hunterdon/Cumberland pair must share an income that Housing splits")
    need(any(o.energy and not o.food for o in evaluated.values()),
         "someone must fall between the Food and Energy limits")
    tapered = [o for o in evaluated.values() if o.dividend > DIVIDEND_BASE]
    need(2 <= len(tapered) <= 3, f"expected 2-3 people on the Dividend taper, found {len(tapered)}")
    need(any(o.health_discount == 1 for o in evaluated.values()), "someone must get Health free")
    need(any(o.health_discount == 0 for o in evaluated.values()), "someone must pay Health full price")
    need(any(0 < o.health_discount < 1 for o in evaluated.values()), "someone must be inside the Health taper")
    for flag in ("food", "energy", "housing"):
        need(any(getattr(o, flag) for o in evaluated.values()), f"nobody is eligible for {flag}")
        need(any(not getattr(o, flag) for o in evaluated.values()), f"nobody is denied {flag}")

    if problems:
        raise SystemExit("Sample data invariants failed:\n  - " + "\n  - ".join(problems))


# ---- Output --------------------------------------------------------------------------------


def write_json(name: str, data) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def yn(value: bool) -> str:
    return "✓" if value else "—"


GATE_TEXT = {
    "credential_missing": "No identity credential — cannot apply",
    "credential_invalid": "Identity credential fails verification — every program denied",
    "not_nj_resident": "Not an NJ resident — every program denied",
}


def write_doc(people: list[dict], employers: dict, outcomes: dict[str, Outcome], stubs: list[dict]) -> None:
    lines = [
        "# Sample Data",
        "",
        "<!-- Generated by tools/generate_sample_data.py from tools/sample_data/*.yaml. Do not edit by hand. -->",
        "",
        "The demo's 25 fictional people and 15 fictional employers (#6). Hand-written in",
        "[tools/sample_data/](../tools/sample_data/); everything below is derived by",
        "`uv run tools/generate_sample_data.py`, which also writes the JSON the apps copy from.",
        "",
        "Nothing here is copied into an app yet. The Wallet takes its slice in Loop 2 and Payroll",
        "in Loop 3 (docs/decisions.md: one-shot generators, per-app copies).",
        "",
        "## Expected outcomes",
        "",
        "What the Benefits app must decide for each person, by the rules in",
        "[docs/benefit-programs.md](benefit-programs.md). **This table is Loop 6's test oracle:**",
        "when Benefits is built, its answers must match it. Income is the sum of gross pay across",
        "the person's September paystubs; annual is that ×12.",
        "",
        "| Person | County | Monthly | Annual | Health discount | Food | Energy | Housing | Dividend |",
        "|---|---|---:|---:|---:|:-:|:-:|:-:|---:|",
    ]
    gated = []
    for p in people:
        o = outcomes[p["id"]]
        name = f"{p['given_name']} {p['family_name']}"
        if o.gate:
            gated.append((p, o))
            continue
        lines.append(
            f"| {name} | {p['address']['county']} | ${o.monthly:,.2f} | ${o.annual:,.2f} "
            f"| {cents(o.health_discount * 100):.1f}% | {yn(o.food)} | {yn(o.energy)} | {yn(o.housing)} "
            f"| ${o.dividend:,.2f} |"
        )
    lines += [
        "",
        "Not evaluated — stopped before any eligibility rule runs:",
        "",
        "| Person | Where | Outcome | Reason code |",
        "|---|---|---|---|",
    ]
    for p, o in gated:
        a = p["address"]
        lines.append(f"| {p['given_name']} {p['family_name']} | {a['locality']}, {a['region']} | {GATE_TEXT[o.gate]} | `{o.gate}` |")

    lines += [
        "",
        "## People",
        "",
        "| ID | Name | Age | Lives in | Identity | Jobs | Demonstrates |",
        "|---|---|---:|---|---|---|---|",
    ]
    for p in people:
        a = p["address"]
        identity = p["identity"] if p["identity"] != "tampered" else f"tampered ({p['tamper']['kind']})"
        job_list = "; ".join(f"{j['title']}, {employers[j['employer']]['name']}" for j in p["jobs"])
        demonstrates = " ".join(p["demonstrates"].split())
        lines.append(
            f"| {p['id']} | {p['given_name']} {p['family_name']} | {age(p['birth_date'])} "
            f"| {a['locality']}, {a['county']} County, {a['region']} | {identity} | {job_list} | {demonstrates} |"
        )

    lines += [
        "",
        "## Employers",
        "",
        "All fictional, all paid through Meridian Payroll.",
        "",
        "| ID | Name | Industry | City | Employees |",
        "|---|---|---|---|---:|",
    ]
    staff = Counter(j["employer"] for p in people for j in p["jobs"])
    for e in employers.values():
        lines.append(f"| {e['id']} | {e['name']} | {e['industry']} | {e['city']} | {staff[e['id']]} |")

    lines += [
        "",
        "## Paystubs",
        "",
        f"{len(stubs)} paystubs: two per job, for 1–15 and 16–30 September 2026, paid on the last",
        "day of each period (or the Friday before, if that falls on a weekend). Hourly pay is rate ×",
        "hours for the period; salaries are paid in 24 equal installments.",
        "",
        "**Withholding is an approximation, for display only** — eligibility uses gross pay and",
        "nothing else. It applies 2025 single-filer federal brackets and standard deduction, and New",
        "Jersey's single-filer brackets, to everyone regardless of where they live or work, with no",
        "pre-tax deductions. Each employer withholds on its own paystub alone, as real employers do.",
        "Year-to-date figures are not generated; Payroll can decide in Loop 3 whether it shows them.",
        "",
        "Full detail: [tools/sample_data/generated/paystubs.json](../tools/sample_data/generated/paystubs.json).",
        "",
        "## Photos",
        "",
        "Identity photos are **AI-generated faces of people who don't exist**, generated with",
        "ChatGPT (OpenAI), in ID-photo style —",
        "front-facing, plain light background, neutral expression, even lighting — each watermarked",
        f"\"Not real person\". Stored in [tools/sample_data/photos/](../tools/sample_data/photos/) as",
        f"{PHOTO_SIZE[0]}×{PHOTO_SIZE[1]} JPEGs of about 20 KB with no metadata; the generator checks",
        "each one but doesn't alter it. The identity credential embeds it as its `image` claim",
        f"(docs/credential-model.md §3). Ages are as of {AS_OF.isoformat()}. People with no identity",
        "credential have no photo.",
        "",
        "| ID | Name | Age | Photo | Brief |",
        "|---|---|---:|---|---|",
    ]
    for p in people:
        if p["identity"] == "none":
            continue
        note = " *(tampered: photo swapped — the credential is signed over a placeholder, then this photo is put in its place)*" if p.get("tamper", {}).get("kind") == "photo" else ""
        lines.append(f"| {p['id']} | {p['given_name']} {p['family_name']} | {age(p['birth_date'])} "
                     f"| [{p['id']}.jpg](../tools/sample_data/photos/{p['id']}.jpg) | {p['photo_brief']}{note} |")

    DOC.write_text("\n".join(lines) + "\n")


def main() -> None:
    people, employers = load()
    stubs, outcomes = [], {}
    for p in people:
        mine = build_paystubs(p, employers)
        stubs += mine
        outcomes[p["id"]] = evaluate(p, sum(Decimal(s["grossPay"]) for s in mine))

    check_invariants(people, employers, outcomes)

    write_json("employers.json", list(employers.values()))
    write_json("people.json", [
        {
            "id": p["id"],
            "subjectId": subject_id(p),
            "givenName": p["given_name"],
            "familyName": p["family_name"],
            "birthDate": p["birth_date"].isoformat(),
            "address": p["address"],
            "identity": p["identity"],
            **({"tamper": p["tamper"]} if "tamper" in p else {}),
            "photoBrief": p.get("photo_brief"),
            "photo": f"{p['id']}.jpg" if p["identity"] != "none" else None,
            "jobs": [{"employerId": j["employer"], "title": j["title"]} for j in p["jobs"]],
        }
        for p in people
    ])
    write_json("paystubs.json", stubs)
    write_doc(people, employers, outcomes, stubs)
    print(f"{len(people)} people, {len(employers)} employers, {len(stubs)} paystubs — invariants hold.")


if __name__ == "__main__":
    main()
