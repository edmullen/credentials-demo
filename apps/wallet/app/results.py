"""The results screen's verdict, composed from a decided determination or a refusal
(docs/design.md §10.7)."""

from decimal import ROUND_HALF_UP, Decimal

from app.display import STATES, join_and, money

PROGRAM_NAMES = {
    "food": "Food Assistance", "energy": "Energy Assistance", "housing": "Housing Assistance",
    "health": "Health", "dividend": "Dividend",
}
PASS_FAIL = ("food", "energy", "housing")


def _entry(programs: list[dict], code: str) -> dict:
    return next(p for p in programs if p["program"] == code)


def _health_price(entry: dict) -> str:
    cost = Decimal(str(entry["planCost"]["value"]))
    discount = Decimal(str(entry["discountPercent"]))
    price = (cost * (100 - discount) / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return money({"value": price})


def _pct(value) -> str:
    text = f"{Decimal(str(value)):.1f}"
    return text[:-2] if text.endswith(".0") else text


def _pass_fail_phrase(eligible_codes: list[str]) -> str | None:
    if not eligible_codes:
        return None
    names = [PROGRAM_NAMES[c] for c in eligible_codes]
    shortened = [n.removesuffix(" Assistance") for n in names[:-1]] + [names[-1]]
    return join_and(shortened)


def _join_clauses(clauses: list[str]) -> str:
    if len(clauses) == 1:
        return clauses[0]
    return ", ".join(clauses[:-1]) + ", and " + clauses[-1]


def verdict(determination: dict, own_region: str | None) -> dict:
    """{"heading", "sentence", "status_text"} for a decided determination."""
    programs = determination["programs"]
    eligible = [p["program"] for p in programs if p["outcome"] == "eligible"]
    n = len(eligible)

    if n == 0:
        state = STATES.get(own_region or "", own_region or "")
        return {
            "heading": "You don’t qualify for any programs",
            "sentence": (
                f"Benefit Agency’s programs are for New Jersey residents, and your identity "
                f"credential gives your address in {state}."
            ),
            "status_text": "You don’t qualify for any programs.",
        }

    heading = "You qualify for all 5 programs" if n == 5 else (
        f"You qualify for {n} program{'' if n == 1 else 's'}"
    )
    status_text = heading + "." if n == 5 else f"{heading}. Not eligible for {5 - n}."

    pass_fail_eligible = [c for c in PASS_FAIL if c in eligible]
    dividend = _entry(programs, "dividend")
    dividend_clause = f"<strong>{money(dividend['monthlyPayment'])} a month</strong> from Dividend"
    health = _entry(programs, "health")

    clauses = []
    phrase = _pass_fail_phrase(pass_fail_eligible)
    if phrase:
        clauses.append(phrase)
    clauses.append(dividend_clause)

    extra_sentence = None
    discount = health["discountPercent"]
    if discount == 100:
        clauses.append("the Public Option health plan <strong>free</strong>")
    elif discount == 0:
        price = money(health["planCost"])
        extra_sentence = (
            f"Health gives no discount at your income: you may buy the Public Option plan at "
            f"its full price, <strong>{price} a month</strong>."
        )
    else:
        price = _health_price(health)
        clauses.append(
            f"<strong>{_pct(discount)}% off</strong> the Public Option health plan, so it "
            f"costs <strong>{price} a month</strong>"
        )

    sentence = _join_clauses(clauses) + "."
    if extra_sentence:
        sentence = f"{sentence} {extra_sentence}"

    return {"heading": heading, "sentence": sentence, "status_text": status_text}


def denials(determination: dict) -> dict:
    """{"heading", "lines": [(name, sentence)]} for the "you don't qualify for" section."""
    programs = determination["programs"]
    denied = [p for p in programs if p["outcome"] == "denied"]
    heading = "Each program" if len(denied) == 5 else "Programs you don’t qualify for"
    lines = []
    for p in denied:
        name = PROGRAM_NAMES[p["program"]]
        if p["reason"] == "not_nj_resident":
            lines.append((name, "this program is for New Jersey residents."))
        else:
            lines.append((name, "your income is above this program’s limit."))
    return {"heading": heading, "lines": lines}


def refusal_sentence(reason: str, own_checks_pass: bool, identity_failed: bool) -> str:
    """The Wallet composes this from its own verification of what it shared, per
    credential-model's wording (docs/design.md §10.7) — no protocol field is needed."""
    if reason == "subjects_differ":
        return "The credentials you shared aren’t all about the same person."
    if not own_checks_pass:
        if identity_failed:
            return "Your identity credential couldn’t be verified, so no program could be decided."
        return "One of your income credentials couldn’t be verified, so no program could be decided."
    return "One of the credentials you shared couldn’t be verified, so no program could be decided."
