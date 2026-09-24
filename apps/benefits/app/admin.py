"""The admin view's models (docs/design.md §8, #111): grouping and summarizing applications for
the list, and the full determination page for one of them. No sign-in, like the rest of the
demo — this module only formats what applications.py already recorded.
"""

import json
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

import jwt

from app.applications import Application
from app.checks import BADGES
from app.display import money, short_date, when, when_seconds
from app.eligibility import rules
from app.programs import get_program

STATE_NAMES = {"NJ": "New Jersey", "MI": "Michigan", "NY": "New York", "OH": "Ohio"}

# Health's decorative scale spans a fixed axis wide enough to place the taper band and any
# realistic income on it (docs/design.md §8.2 — decorative, aria-hidden, since the text beside
# it says the same thing).
HEALTH_AXIS = Decimal(90000)


def _cents(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _summary(application: Application) -> str:
    if application.outcome == "refused":
        return {
            "credential_invalid": "Refused: credential couldn’t be verified",
            "subjects_differ": "Refused: credentials aren’t about one person",
        }[application.reason]
    if application.facts and application.facts.region != "NJ":
        return "Not a New Jersey resident"
    n = sum(1 for p in application.determination.programs if p.outcome == "eligible")
    return f"{n} of 5 approved"


def application_rows(applications: list[Application]) -> list[dict]:
    """Grouped by person, newest application first within a group; groups ordered by their own
    newest application, newest first (docs/design.md §8.1)."""
    groups: dict[str, list[Application]] = defaultdict(list)
    for a in applications:
        groups[a.subject_id or a.id].append(a)
    ordered = sorted(groups.values(), key=lambda g: max(a.received_at for a in g), reverse=True)

    rows = []
    for group in ordered:
        group_sorted = sorted(group, key=lambda a: a.received_at, reverse=True)
        for i, a in enumerate(group_sorted):
            rows.append(
                {
                    "id": a.id,
                    "name": a.name if i == 0 else None,
                    "start": i == 0,
                    "when": when(a.received_at),
                    "summary": _summary(a),
                }
            )
    return rows


def _short_subject(subject_id: str | None) -> str:
    if not subject_id:
        return "unknown"
    tail = subject_id.removeprefix("urn:uuid:")
    return tail.split("-")[0]


def _redacted_claims(claims: dict) -> dict:
    """A copy with the identity credential's photo truncated, as the admin view never shows a
    photo (docs/design.md §8.2, handoff decision)."""
    copy = json.loads(json.dumps(claims))
    subject = copy.get("credentialSubject")
    if isinstance(subject, dict) and isinstance(subject.get("image"), str):
        subject["image"] = subject["image"][:42] + "… (photo, not shown)"
    return copy


def _check_view(presented, claims: dict) -> dict:
    badge = BADGES[presented.outcome]
    if presented.kind == "identity":
        issuer_name = (claims.get("issuer") or {}).get("name", "")
        label = "Identity credential"
        detail = f"{issuer_name} · {badge.detail.format(issuer=issuer_name)}"
    else:
        subject = claims.get("credentialSubject") or {}
        employer = (subject.get("employer") or {}).get("name", "")
        pay_date = subject.get("payDate")
        paid = f"paid {short_date(pay_date)}" if pay_date else "paid —"
        label = "Income credential"
        detail = f"{employer} · {paid} · {badge.detail.format(issuer='Meridian Payroll')}"
    try:
        header = jwt.get_unverified_header(presented.token)
    except jwt.PyJWTError:
        header = {}
    return {
        "label": label,
        "detail": detail,
        "badge_label": badge.label,
        "badge_variant": badge.variant,
        "header_json": json.dumps(header, indent=2),
        "claims_json": json.dumps(_redacted_claims(claims), indent=2),
        "jwt": presented.token,
    }


def _submitted_view(application: Application) -> dict | None:
    facts = application.facts
    if facts is None:
        return None
    note = None
    if application.outcome == "refused":
        note = "Recorded as presented. Not used: the application was refused at the credential checks."
    elif facts.region != "NJ":
        note = "Recorded as presented. Income was not used: residency is checked first."
    monthly = sum((Decimal(str(p["gross_pay"] or 0)) for p in facts.paystubs), Decimal(0))
    return {
        "note": note,
        "state_name": STATE_NAMES.get(facts.region, facts.region or "—"),
        "region": facts.region,
        "county": facts.county or "—",
        "paystubs": [
            {
                "employer": p["employer"] or "—",
                "pay_date": short_date(p["pay_date"]) if p["pay_date"] else "—",
                "gross": money(p["gross_pay"] or 0),
            }
            for p in facts.paystubs
        ],
        "monthly": money(monthly),
        "annual": money(monthly * 12),
    }


def _linear_scale(value: Decimal, threshold: Decimal) -> dict:
    """A fixed-80%-zone axis that scales to whichever of value/threshold is larger, so the zone
    fills 80% when the value is inside it, and the value's dot pins at 80% once it's over
    (docs/design.md §8.2). See the PR's write-up for the worked examples."""
    divisor = max(value, threshold, Decimal("0.01"))
    zone_width = threshold / divisor * 80
    dot = value / divisor * 80
    return {"zone_start": Decimal(0), "zone_width": zone_width, "dot": dot}


def _health_scale(annual: Decimal, ceiling: Decimal, floor: Decimal) -> dict:
    zone_start = ceiling / HEALTH_AXIS * 100
    zone_width = (floor - ceiling) / HEALTH_AXIS * 100
    dot = min(annual, HEALTH_AXIS) / HEALTH_AXIS * 100
    return {"zone_start": zone_start, "zone_width": zone_width, "dot": dot}


def _decision_view(result, application: Application, r: dict) -> dict:
    program = get_program(result.program)
    facts = application.facts
    annual = Decimal(str(application.determination.annual))
    monthly = Decimal(str(application.determination.monthly))

    view = {
        "code": result.program,
        "name": program["name"],
        "outcome": result.outcome,
        "badge_label": "Eligible" if result.outcome == "eligible" else "Not eligible",
        "badge_variant": "verified" if result.outcome == "eligible" else "neutral",
    }

    if result.program in ("food", "energy", "housing"):
        limit = Decimal(str(result.limit))
        scale = _linear_scale(annual, limit)
        if result.outcome == "eligible":
            result_text = f"{money(limit - annual)} under the limit"
        else:
            monthly_over = _cents((annual - limit) / 12)
            result_text = f"{money(annual - limit)} over the limit ({money(monthly_over)} a month)"
        view.update(
            figure=f"Annual income {money(annual)}, limit {money(limit)}",
            result=result_text,
            scale=scale,
            legend_left=f"Qualifies up to {money(limit)}",
            legend_right=f"● {money(annual)}",
        )
    elif result.program == "health":
        ceiling = Decimal(r["health"]["full_discount_ceiling_pct"]) * Decimal(r["federal_poverty_level"])
        floor = Decimal(r["health"]["zero_discount_floor_pct"]) * Decimal(r["federal_poverty_level"])
        discount = Decimal(str(result.discount_percent))
        plan_cost = Decimal(str(result.plan_cost))
        price = _cents(plan_cost * (100 - discount) / 100)
        view.update(
            figure=f"Annual income {money(annual)}",
            result=f"{discount}% off: {money(price)} a month",
            scale=_health_scale(annual, ceiling, floor),
            legend_left=f"Scale {money(ceiling)}–{money(floor)}",
            legend_right=f"● {money(annual)}",
        )
    else:  # dividend
        phase_out = Decimal(r["dividend"]["phase_out"])
        payment = Decimal(str(result.monthly_payment))
        if monthly >= phase_out:
            result_text = f"{money(payment)} a month (base only, above {money(phase_out)})"
        else:
            result_text = f"{money(payment)} a month"
        view.update(
            figure=f"Monthly income {money(monthly)}",
            result=result_text,
            scale=_linear_scale(monthly, phase_out),
            legend_left=f"Extra paid up to {money(phase_out)}",
            legend_right=f"● {money(monthly)}",
        )

    if result.outcome == "eligible" and result.program in application.issued:
        issued = application.issued[result.program]
        claims = jwt.decode(issued.jwt, options={"verify_signature": False})
        view["foot_label"] = f"Issued credential · valid until {short_date(claims['validUntil'])}"
        view["credential_id"] = issued.credential_id
        if result.program == "health":
            view["mono"] = f"discountPercent: {result.discount_percent} · planCost: {money(result.plan_cost)} USD"
        elif result.program == "dividend":
            view["mono"] = f"monthlyPayment: {money(result.monthly_payment)} USD"
        else:
            view["mono"] = f'program: "{result.program}"'
    else:
        view["reason"] = result.reason
    return view


def determination_view(application: Application) -> dict:
    checks = [_check_view(p, jwt.decode(p.token, options={"verify_signature": False}))
              for p in application.presented]
    subject_short = _short_subject(application.subject_id)
    same_subject_check = {
        "detail": f"All {len(application.presented)} credentials name subject {subject_short}…"
        if application.same_subject
        else "Not every presented credential names the same subject",
        "badge_label": "Same subject" if application.same_subject else "Subjects differ",
        "badge_variant": "verified" if application.same_subject else "error",
    }

    variant = "refused"
    decisions = None
    callout = None
    if application.outcome == "decided":
        r = rules()
        if application.facts and application.facts.region != "NJ":
            variant = "not_nj"
            decisions = [
                {
                    "code": p.program,
                    "name": get_program(p.program)["name"],
                    "badge_label": "Not eligible",
                    "badge_variant": "neutral",
                    "reason": p.reason,
                }
                for p in application.determination.programs
            ]
            callout = (
                "Residency stopped the application",
                f"The identity credential gives {STATE_NAMES.get(application.facts.region, application.facts.region)} "
                f"({application.facts.region}). Every program requires New Jersey residency, so all five were "
                "denied without checking income. This person may apply again.",
            )
        else:
            variant = "decided"
            decisions = [_decision_view(p, application, r) for p in application.determination.programs]
    else:
        reason_text = {
            "credential_invalid": (
                "One income credential failed verification, so none of the submitted data can be "
                "relied on. No program was decided and no credential was issued. "
                "Reason: credential_invalid."
            ),
            "subjects_differ": (
                "The presented credentials don’t all name the same subject, so none of the "
                "submitted data can be relied on. No program was decided and no credential was "
                "issued. Reason: subjects_differ."
            ),
        }
        callout = ("Refused before any program was evaluated", reason_text[application.reason])

    return {
        "name": application.name or "—",
        "summary": _summary(application),
        "summary_error": application.outcome == "refused",
        "received": when_seconds(application.received_at),
        "application_id": application.id,
        "subject_id": application.subject_id or "—",
        "checks": checks,
        "same_subject_check": same_subject_check,
        "submitted": _submitted_view(application),
        "variant": variant,
        "decisions": decisions,
        "callout": callout,
    }
