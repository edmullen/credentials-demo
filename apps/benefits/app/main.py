import os
from decimal import Decimal
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import applications, clock, signing, trust
from app.admin import application_rows, determination_view
from app.display import money, money_whole
from app.eligibility import PROGRAMS, ProgramResult, rules
from app.issuance import issue_eligible
from app.presentation import decide_application
from app.programs import all_programs, get_program

# DCQL-shaped, naming credential types only — no claims list (docs/design.md §2, credential-model
# §3, decision 1). "multiple: true" is DCQL's own term for "every matching credential".
DCQL_QUERY = {
    "credentials": [
        {"id": "identity", "format": "vc+jwt", "meta": {"type_values": [["IdentityCredential"]]}},
        {
            "id": "income",
            "format": "vc+jwt",
            "multiple": True,
            "meta": {"type_values": [["PaystubCredential"]]},
        },
    ]
}

BASE_DIR = Path(__file__).parent

# Where Apply with Digital Wallet sends the browser (docs/design.md §3, §7.3). Local runs point
# it at a local Wallet, as the Wallet's MERIDIAN_PAYROLL_URL does for Payroll.
WALLET_URL = os.environ.get("WALLET_URL", "https://cred-demo-wallet.onrender.com").rstrip("/")

app = FastAPI()
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Everything that varies in the shared layout, for this app.
#
# Theme value is "benefits" (plural), matching this app's directory name —
# a deliberate deviation from the design handoff, which used the singular
# "benefit". See docs/design.md §2.
SITE = {
    "theme": "benefits",
    "title": "Benefit Agency",
    "name": "Benefit Agency",
    "fonts_url": (
        "https://fonts.googleapis.com/css2?"
        "family=Libre+Franklin:wght@600&family=Public+Sans:wght@400;600;700&display=swap"
    ),
}

INCOME_NOTE = (
    "Income means gross pay, before tax, from the income credentials in your wallet. "
    "Annual income is one month’s total × 12."
)
MONTHLY_INCOME_NOTE = (
    "Monthly income is one month of gross pay, before tax, from the income credentials "
    "in your wallet."
)


def render(request: Request, template: str, active: str | None, **context) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        template,
        {"site": SITE, "programs": all_programs(), "active": active, **context},
    )


def _pass_fail_context(limit_pct_label: str, r: dict, limit) -> dict:
    return {
        "rule_text": f"Your annual income is at or below {money(limit)}.",
        "rule_note": f"{limit_pct_label}, as of {r['as_of']}.",
        "income_note": INCOME_NOTE,
    }


@app.get("/", response_class=HTMLResponse)
async def landing(request: Request) -> HTMLResponse:
    return render(request, "landing.html", None)


@app.get("/programs/{code}", response_class=HTMLResponse)
async def program_page(request: Request, code: str) -> HTMLResponse:
    program = get_program(code)
    if program is None:
        raise HTTPException(status_code=404)
    r = rules()
    fpl = r["federal_poverty_level"]

    if code == "food":
        limit = Decimal(r["food_limit_pct"]) * Decimal(fpl)
        context = _pass_fail_context("185% of the federal poverty level", r, limit)
        context["intro_purpose"] = (
            "Food Assistance helps with the cost of groceries. It is decided on a single "
            "income limit."
        )
        return render(request, "program.html", code, program=program, **context)

    if code == "energy":
        limit = Decimal(r["energy_limit_pct"]) * Decimal(r["state_median_income"])
        context = _pass_fail_context("60% of the state median income", r, limit)
        context["intro_purpose"] = (
            "Energy Assistance helps with heating, cooling and electricity bills. It is "
            "decided on a single income limit."
        )
        return render(request, "program.html", code, program=program, **context)

    if code == "housing":
        county_limits = [
            {
                "county": county,
                "ami": money_whole(ami),
                "limit": money(Decimal(ami) * Decimal(r["housing_share_pct"])),
            }
            for county, ami in r["county_ami"].items()
        ]
        return render(
            request,
            "program_housing.html",
            code,
            program=program,
            rules=r,
            county_limits=county_limits,
            intro_purpose=(
                "Housing Assistance helps with the cost of rent. Housing costs differ across "
                "New Jersey, so the income limit depends on the county you live in."
            ),
            rule_text="Your annual income is at or below the limit for your county.",
            rule_note=f"30% of your county’s area median income, as of {r['as_of']}.",
            income_note=INCOME_NOTE,
        )

    if code == "health":
        ceiling = Decimal(r["health"]["full_discount_ceiling_pct"]) * Decimal(fpl)
        floor = Decimal(r["health"]["zero_discount_floor_pct"]) * Decimal(fpl)
        plan_cost = r["health"]["plan_cost"]
        per_1000 = Decimal(plan_cost) / (floor - ceiling) * 1000
        facts = {
            "full_price": money(plan_cost),
            "free_at_or_below": money(ceiling),
            "full_price_at_or_above": money(floor),
            "marginal_per_1000": money(per_1000),
        }
        return render(
            request,
            "program_health.html",
            code,
            program=program,
            facts=facts,
            intro_purpose=(
                f"Health gives you a discount on the Public Option health plan, which costs "
                f"{facts['full_price']} a month at full price. Anyone may buy the plan. Your "
                f"income sets how much of that price you pay."
            ),
            rule_text="Any income. Your annual income sets your discount.",
            rule_note=(
                f"Free at or below {facts['free_at_or_below']} a year, full price at or above "
                f"{facts['full_price_at_or_above']}, as of {r['as_of']}."
            ),
            income_note=INCOME_NOTE,
        )

    # dividend
    base = r["dividend"]["base"]
    max_bump = r["dividend"]["max_bump"]
    phase_out = r["dividend"]["phase_out"]
    facts = {
        "base": money_whole(base),
        "max_bump": money_whole(max_bump),
        "phase_out": money_whole(phase_out),
    }
    return render(
        request,
        "program_dividend.html",
        code,
        program=program,
        facts=facts,
        intro_purpose=(
            f"Dividend is a monthly payment to New Jersey residents who apply. Everyone "
            f"receives {facts['base']} a month, and people earning less receive more."
        ),
        rule_text="Any income. Your monthly income sets your payment.",
        rule_note=(
            f"{facts['base']} a month for everyone, plus up to {facts['max_bump']} more below "
            f"{facts['phase_out']} a month, as of {r['as_of']}."
        ),
        income_note=MONTHLY_INCOME_NOTE,
    )


@app.get("/apply")
async def apply() -> RedirectResponse:
    # A GET because the handoff's button is a link. Creating a request is harmless: it holds
    # nothing personal, expires in 15 minutes and is pruned. The browser carries only its id;
    # the Wallet fetches the request itself, by reference (docs/design.md §2, §7.3).
    request_id = applications.create_request(clock.now())
    return RedirectResponse(f"{WALLET_URL}/requests/benefits/{request_id}", status_code=303)


@app.get("/admin", response_class=HTMLResponse)
async def admin(request: Request) -> HTMLResponse:
    rows = application_rows(applications.all_applications())
    if not rows:
        return render(request, "admin_empty.html", "admin")
    return render(request, "admin.html", "admin", rows=rows)


@app.get("/admin/applications/{application_id}", response_class=HTMLResponse)
async def admin_determination(request: Request, application_id: str) -> HTMLResponse:
    application = applications.get_application(application_id)
    if application is None:
        raise HTTPException(status_code=404)
    return render(request, "determination.html", "admin", det=determination_view(application))


def _iso(dt) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _program_entry(result: ProgramResult, issued: dict) -> dict:
    entry = {"program": result.program, "outcome": result.outcome}
    if result.outcome == "denied":
        entry["reason"] = result.reason
        return entry
    if result.program in issued:
        entry["credentialId"] = issued[result.program].credential_id
    if result.discount_percent is not None:
        entry["discountPercent"] = float(result.discount_percent)
        entry["planCost"] = {
            "type": "MonetaryAmount", "value": float(result.plan_cost), "currency": "USD"
        }
    if result.monthly_payment is not None:
        entry["monthlyPayment"] = {
            "type": "MonetaryAmount", "value": float(result.monthly_payment), "currency": "USD"
        }
    return entry


@app.post("/api/applications/requests")
async def create_application_request() -> JSONResponse:
    request_id = applications.create_request(clock.now())
    return JSONResponse(
        status_code=201,
        content={
            "requestId": request_id,
            "dcql_query": DCQL_QUERY,
            "response_uri": f"/api/applications/requests/{request_id}/presentation",
        },
    )


@app.get("/api/applications/requests/{request_id}")
async def get_application_request(request_id: str) -> JSONResponse:
    # Fetchable any number of times until a presentation answers it (docs/design.md §2) — it
    # doesn't consume the pending request, unlike the presentation POST below.
    pending = applications.peek_request(request_id, clock.now())
    if pending is None:
        return JSONResponse(status_code=404, content={"error": "unknown_request"})
    return JSONResponse(
        status_code=200,
        content={
            "requestId": request_id,
            "dcql_query": DCQL_QUERY,
            "response_uri": f"/api/applications/requests/{request_id}/presentation",
        },
    )


@app.post("/api/applications/requests/{request_id}/presentation")
async def submit_application_presentation(request_id: str, vp: dict = Body(...)) -> JSONResponse:
    # Checked before consuming the pending request, so a key outage doesn't burn the one
    # presentation it answers (docs/design.md §3: call 2 needs a valid key to sign).
    if not signing.status().ok:
        return JSONResponse(status_code=503, content={"status": "unhealthy"})

    now = clock.now()
    pending = applications.pop_request(request_id, now)
    if pending is None:
        return JSONResponse(status_code=404, content={"error": "unknown_request"})

    outcome, extra = decide_application(vp, trust.trust_list(), now)
    if outcome == "invalid_presentation":
        return JSONResponse(status_code=400, content={"error": "invalid_presentation"})

    if outcome in ("credential_invalid", "subjects_differ"):
        refused = extra
        applications.record_application(
            subject_id=refused.subject_id,
            name=refused.name,
            presented=refused.presented,
            same_subject=refused.same_subject,
            outcome="refused",
            reason=outcome,
            facts=refused.facts,
            determination=None,
            now=now,
        )
        return JSONResponse(status_code=200, content={"outcome": "refused", "reason": outcome})

    decided = extra
    issued = issue_eligible(decided.determination.programs, decided.subject_id, now)
    application = applications.record_application(
        subject_id=decided.subject_id,
        name=decided.name,
        presented=decided.presented,
        same_subject=decided.same_subject,
        outcome="decided",
        reason=None,
        facts=decided.facts,
        determination=decided.determination,
        issued=issued,
        now=now,
    )
    # A connection either way — even an all-denied determination (docs/design.md §2).
    connection_id = applications.connect(decided.subject_id, application.id, now)
    return JSONResponse(
        status_code=200,
        content={
            "outcome": "decided",
            "connectionId": connection_id,
            "applicationId": application.id,
            "decidedAt": _iso(now),
            "programs": [_program_entry(r, issued) for r in decided.determination.programs],
        },
    )


@app.post("/api/credentials")
async def fetch_credentials(payload: dict = Body(...)) -> JSONResponse:
    connection_id = payload.get("connectionId")
    have = payload.get("have")
    if not isinstance(connection_id, str) or not isinstance(have, list) or not all(
        isinstance(h, str) for h in have
    ):
        return JSONResponse(status_code=400, content={"error": "invalid_request"})
    application = applications.application_for_connection(connection_id)
    if application is None:
        return JSONResponse(status_code=404, content={"error": "unknown_connection"})
    if not signing.status().ok:
        return JSONResponse(status_code=503, content={"status": "unhealthy"})
    have_set = set(have)
    credentials = [
        application.issued[code].jwt
        for code in PROGRAMS
        if code in application.issued and application.issued[code].credential_id not in have_set
    ]
    return JSONResponse(status_code=200, content={"credentials": credentials})


@app.get("/health")
async def health() -> JSONResponse:
    result = signing.status()
    if not result.ok:
        return JSONResponse(status_code=503, content={"status": "unhealthy", "reason": result.reason})
    return JSONResponse(content={"status": "ok"})


@app.get("/.well-known/jwks.json")
async def jwks() -> dict:
    return {"keys": [signing.public_jwk()]}
