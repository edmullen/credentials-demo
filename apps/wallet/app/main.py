from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import application, results, state
from app.activity import grouped_events
from app.attempt import (
    approve,
    close,
    deny,
    matching_credential,
    phase_url,
    purpose_line,
    request_label,
    request_type,
    start_connect,
    where_is_the_attempt,
)
from app.connections import (
    add_employer, connections_title, income_check_view, income_note, provider_panels, remove_link,
)
from app.credentials import credentials_for, find_credential, identity_status
from app.display import long_date
from app.issuance import check_status, maybe_start_check
from app.people import all_people, get_person
from app.programs import all_programs
from app.providers import all_employers, all_providers, all_services, get_provider
from app.verify import Outcome

BASE_DIR = Path(__file__).parent

app = FastAPI()
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Everything that varies in the shared layout, for this app. Per-person and per-screen values
# are passed per request instead.
SITE = {
    "theme": "wallet",
    "name": "Wallet",
    "fonts_url": (
        "https://fonts.googleapis.com/css2?"
        "family=Newsreader:wght@400;600&family=Public+Sans:wght@400;600&display=swap"
    ),
}

# The screens a person can be on, in nav order. The key is also the last path segment.
NAV = [("credentials", "Credentials"), ("connections", "Connections"), ("activity", "Activity")]
DEFAULT_PERSON = "p01"


def viewed_person(person_id: str) -> dict:
    person = get_person(person_id)
    if person is None:
        raise HTTPException(status_code=404)
    return person


def render(
    request: Request, template: str, person: dict | None, active: str, **context
) -> HTMLResponse:
    """`person` is None only on the landing page, where no one is signed in."""
    return templates.TemplateResponse(
        request,
        template,
        {"site": SITE, "nav": NAV, "person": person, "active": active, **context},
    )


@app.get("/", response_class=HTMLResponse)
async def landing(request: Request) -> HTMLResponse:
    # Sign in is navigation, not authentication: it opens the default person's wallet
    # (docs/design.md §5, §9 items 1-2).
    return render(
        request, "landing.html", None, "",
        sign_in=f"/p/{DEFAULT_PERSON}/credentials",
        switcher=f"/p/{DEFAULT_PERSON}/switch",
    )


@app.get("/p/{person_id}/credentials", response_class=HTMLResponse)
async def credentials(request: Request, person: dict = Depends(viewed_person)) -> HTMLResponse:
    for provider_id in all_providers():
        maybe_start_check(person["id"], provider_id)
    all_credentials = credentials_for(person["id"])
    identity = [c for c in all_credentials if c.category == "Identity"]
    income = [c for c in all_credentials if c.category == "Income"]
    order = {p["code"]: p["order"] for p in all_programs()}
    benefits = sorted(
        (c for c in all_credentials if c.category == "Benefits"),
        key=lambda c: order.get(c.program, 99),
    )
    seen = state.seen_for(person["id"])
    over = len(income) > 5
    drawn = income[:5]
    new_count = sum(1 for c in drawn if c.id not in seen)
    benefits_new_count = sum(1 for c in benefits if c.id not in seen)
    response = render(
        request, "credentials.html", person, "credentials",
        identity=identity, note=income_note(person["id"]),
        income_total=len(income), drawn=drawn, over=over,
        stack_n=len(drawn) + (1 if over else 0) - 1, new_count=new_count, seen=seen,
        check=income_check_view(person["id"]),
        benefits=benefits, benefits_new_count=benefits_new_count,
        holds_benefit_credential=bool(benefits),
    )
    state.mark_seen(person["id"], (c.id for c in drawn))
    state.mark_seen(person["id"], (c.id for c in benefits))
    return response


@app.get("/p/{person_id}/credentials/check")
async def credentials_check(person: dict = Depends(viewed_person)) -> dict:
    return check_status(person["id"])


@app.get("/p/{person_id}/credentials/income", response_class=HTMLResponse)
async def income_credentials(request: Request, person: dict = Depends(viewed_person)) -> HTMLResponse:
    # Declared ahead of the detail route below, so "income" isn't read as a credential id.
    income = [c for c in credentials_for(person["id"]) if c.category == "Income"]
    return render(
        request, "income.html", person, "credentials",
        income=income, seen=state.seen_for(person["id"]),
    )


@app.get("/p/{person_id}/credentials/{credential_id}", response_class=HTMLResponse)
async def credential(
    request: Request, credential_id: str, person: dict = Depends(viewed_person)
) -> HTMLResponse:
    # Someone else's credential id is a 404, not a redirect: the URL shape shouldn't imply that
    # one person's wallet can address another's.
    found = find_credential(person["id"], credential_id)
    if found is None:
        raise HTTPException(status_code=404)
    tampered = found.outcome is Outcome.TAMPERED
    if found.category == "Income":
        return render(
            request, "income-credential.html", person, "credentials", c=found, tampered=tampered
        )
    if found.category == "Benefits":
        return render(
            request, "benefit-credential.html", person, "credentials", c=found, tampered=tampered
        )
    return render(request, "credential.html", person, "credentials", c=found, tampered=tampered)


@app.get("/p/{person_id}/connections", response_class=HTMLResponse)
async def connections(request: Request, person: dict = Depends(viewed_person)) -> HTMLResponse:
    panels = provider_panels(person["id"])
    return render(
        request, "connections.html", person, "connections",
        panels=panels, title=connections_title(panels),
    )


@app.get("/p/{person_id}/connections/employers", response_class=HTMLResponse)
async def employers(request: Request, person: dict = Depends(viewed_person)) -> HTMLResponse:
    added = {e for panel in provider_panels(person["id"]) for e in panel["employers"]}
    rows = sorted(
        ({**e, "added": e["name"] in added} for e in all_employers()),
        key=lambda e: e["name"],
    )
    return render(request, "employers.html", person, "", employers=rows)


@app.post("/p/{person_id}/connections/employers")
async def add_employer_route(
    person: dict = Depends(viewed_person), employer: str = Form(...)
) -> RedirectResponse:
    if add_employer(person["id"], employer) is None:
        raise HTTPException(status_code=404)
    return RedirectResponse(f"/p/{person['id']}/connections", status_code=303)


@app.post("/p/{person_id}/connections/{provider_id}/remove")
async def remove_link_route(
    provider_id: str, person: dict = Depends(viewed_person)
) -> RedirectResponse:
    if get_provider(provider_id) is None:
        raise HTTPException(status_code=404)
    remove_link(person["id"], provider_id)
    return RedirectResponse(f"/p/{person['id']}/connections", status_code=303)


@app.post("/p/{person_id}/connections/{provider_id}/connect")
async def connect_route(
    provider_id: str, person: dict = Depends(viewed_person)
) -> RedirectResponse:
    provider = get_provider(provider_id)
    if (
        provider is None or provider["kind"] != "payroll"
        or state.get_link(person["id"], provider_id) is None
    ):
        raise HTTPException(status_code=404)
    start_connect(person["id"], provider_id)
    return RedirectResponse(
        f"/p/{person['id']}/connections/{provider_id}/asking", status_code=303
    )


@app.get("/p/{person_id}/connections/{provider_id}/asking", response_class=HTMLResponse)
async def asking_page(
    request: Request, provider_id: str, person: dict = Depends(viewed_person)
) -> HTMLResponse:
    provider = get_provider(provider_id)
    if provider is None:
        raise HTTPException(status_code=404)
    link = state.get_link(person["id"], provider_id)
    if link is None or link.request is None or link.request.phase != "asking":
        return RedirectResponse(where_is_the_attempt(person["id"], provider_id), status_code=303)
    return render(
        request, "asking.html", person, "",
        provider={"id": provider_id, "name": provider["name"]},
    )


@app.get("/p/{person_id}/connections/{provider_id}/request", response_class=HTMLResponse)
async def request_page(
    request: Request, provider_id: str, person: dict = Depends(viewed_person)
) -> HTMLResponse:
    provider = get_provider(provider_id)
    if provider is None:
        raise HTTPException(status_code=404)
    link = state.get_link(person["id"], provider_id)
    if link is None or link.request is None or link.request.phase not in ("consent", "missing"):
        return RedirectResponse(where_is_the_attempt(person["id"], provider_id), status_code=303)
    entries = []
    for entry in link.request.dcql_query.get("credentials", []):
        credential_type = request_type(entry)
        credential = matching_credential(person["id"], credential_type)
        entries.append({
            "label": request_label(credential_type),
            "credential": credential,
            "tampered": credential is not None and credential.outcome is Outcome.TAMPERED,
        })
    return render(
        request, "request.html", person, "",
        provider={"id": provider_id, "name": provider["name"]},
        entries=entries,
        phase=link.request.phase,
        purpose=purpose_line(provider["name"], link.employers),
    )


@app.post("/p/{person_id}/connections/{provider_id}/request")
async def decide_request(
    provider_id: str, person: dict = Depends(viewed_person), decision: str = Form(...)
) -> RedirectResponse:
    if get_provider(provider_id) is None:
        raise HTTPException(status_code=404)
    if decision == "approve":
        approve(person["id"], provider_id)
    elif decision == "deny":
        deny(person["id"], provider_id)
    elif decision == "close":
        close(person["id"], provider_id)
    return RedirectResponse(where_is_the_attempt(person["id"], provider_id), status_code=303)


@app.get("/p/{person_id}/connections/{provider_id}/verifying", response_class=HTMLResponse)
async def verifying_page(
    request: Request, provider_id: str, person: dict = Depends(viewed_person)
) -> HTMLResponse:
    provider = get_provider(provider_id)
    if provider is None:
        raise HTTPException(status_code=404)
    link = state.get_link(person["id"], provider_id)
    if link is None or link.request is None or link.request.phase != "verifying":
        return RedirectResponse(where_is_the_attempt(person["id"], provider_id), status_code=303)
    return render(
        request, "verifying.html", person, "",
        provider={"id": provider_id, "name": provider["name"]},
    )


@app.get("/p/{person_id}/connections/{provider_id}/status")
async def connection_status(
    provider_id: str, person: dict = Depends(viewed_person), page: str = Query(...)
) -> dict:
    if get_provider(provider_id) is None:
        raise HTTPException(status_code=404)
    link = state.get_link(person["id"], provider_id)
    if link is None or link.request is None:
        return {"next": f"/p/{person['id']}/connections"}
    if link.request.phase == page:
        return {"next": None}
    return {"next": phase_url(person["id"], provider_id, link.request.phase)}


@app.get("/p/{person_id}/activity", response_class=HTMLResponse)
async def activity(request: Request, person: dict = Depends(viewed_person)) -> HTMLResponse:
    groups = grouped_events(person["id"])
    return render(request, "activity.html", person, "activity", groups=groups)


@app.get("/p/{person_id}/switch", response_class=HTMLResponse)
async def switch(
    request: Request,
    person: dict = Depends(viewed_person),
    from_screen: str = Query("credentials", alias="from"),
) -> HTMLResponse:
    # Rows keep the reader on the kind of screen they came from. Only a known screen name is
    # accepted, so the query string can't steer a link anywhere else.
    screen = from_screen if from_screen in dict(NAV) else "credentials"
    # Each badge is the result of verifying that person's credential, not a stored field.
    rows = [{**p, "status": identity_status(p["id"])} for p in all_people()]
    return render(request, "switch.html", person, "", people=rows, screen=screen)


@app.get("/p/{person_id}/services", response_class=HTMLResponse)
async def services_page(request: Request, person: dict = Depends(viewed_person)) -> HTMLResponse:
    services = [
        {"id": service_id, "name": provider["name"], "blurb": provider.get("blurb", "")}
        for service_id, provider in all_services()
    ]
    return render(request, "services.html", person, "credentials", services=services)


def _require_service(service_id: str) -> None:
    if service_id != application.SERVICE_ID:
        raise HTTPException(status_code=404)


@app.get("/p/{person_id}/services/{service_id}/apply")
async def services_apply(
    service_id: str, person: dict = Depends(viewed_person)
) -> RedirectResponse:
    _require_service(service_id)
    person_id = person["id"]
    if application.holds_benefit_credential(person_id):
        return RedirectResponse(f"/p/{person_id}/services/{service_id}/already", status_code=303)
    link = state.get_link(person_id, service_id)
    if link is not None and link.request is not None:
        return RedirectResponse(application.where_is_the_attempt(person_id), status_code=303)
    application.start_apply(person_id)
    return RedirectResponse(f"/p/{person_id}/services/{service_id}/asking", status_code=303)


@app.get("/p/{person_id}/services/{service_id}/asking", response_class=HTMLResponse)
async def services_asking(
    request: Request, service_id: str, person: dict = Depends(viewed_person)
) -> HTMLResponse:
    _require_service(service_id)
    person_id = person["id"]
    provider = get_provider(service_id)
    link = state.get_link(person_id, service_id)
    if link is None or link.request is None or link.request.phase != "asking":
        return RedirectResponse(application.where_is_the_attempt(person_id), status_code=303)
    return render(
        request, "asking.html", person, "credentials",
        provider={"id": service_id, "name": provider["name"]},
        poll_url=f"/p/{person_id}/services/{service_id}/status?page=asking",
        fallback_action=f"/p/{person_id}/services/{service_id}/asking",
    )


@app.get("/p/{person_id}/services/{service_id}/request", response_class=HTMLResponse)
async def services_request(
    request: Request, service_id: str, person: dict = Depends(viewed_person)
) -> HTMLResponse:
    _require_service(service_id)
    person_id = person["id"]
    link = state.get_link(person_id, service_id)
    if link is None or link.request is None or link.request.phase not in ("consent", "missing"):
        return RedirectResponse(application.where_is_the_attempt(person_id), status_code=303)
    if link.request.phase == "missing":
        template = (
            "cant-apply-identity.html" if link.request.missing == "identity" else "cant-apply-income.html"
        )
        return render(request, template, person, "credentials", service_id=service_id)
    identity = application.held_identity(person_id)
    income = application.held_income(person_id)
    groups = application.income_groups(income)
    total = 1 + len(income)
    return render(
        request, "services-consent.html", person, "credentials",
        service_id=service_id, identity=identity,
        identity_tampered=identity.outcome is Outcome.TAMPERED,
        income_groups=groups, total=total,
    )


@app.post("/p/{person_id}/services/{service_id}/request")
async def services_decide(
    service_id: str, person: dict = Depends(viewed_person), decision: str = Form(...)
) -> RedirectResponse:
    _require_service(service_id)
    person_id = person["id"]
    if decision == "approve":
        application.approve(person_id)
    elif decision == "deny":
        application.deny(person_id)
    elif decision == "close":
        application.close(person_id)
    elif decision == "retry":
        application.retry(person_id)
    return RedirectResponse(application.where_is_the_attempt(person_id), status_code=303)


@app.get("/p/{person_id}/services/{service_id}/applying", response_class=HTMLResponse)
async def services_applying(
    request: Request, service_id: str, person: dict = Depends(viewed_person)
) -> HTMLResponse:
    _require_service(service_id)
    person_id = person["id"]
    link = state.get_link(person_id, service_id)
    if link is None or link.request is None or link.request.phase != "applying":
        return RedirectResponse(application.where_is_the_attempt(person_id), status_code=303)
    return render(request, "checking.html", person, "credentials", service_id=service_id)


@app.get("/p/{person_id}/services/{service_id}/error", response_class=HTMLResponse)
async def services_error(
    request: Request, service_id: str, person: dict = Depends(viewed_person)
) -> HTMLResponse:
    _require_service(service_id)
    person_id = person["id"]
    link = state.get_link(person_id, service_id)
    if link is None or link.request is None or link.request.phase != "error":
        return RedirectResponse(application.where_is_the_attempt(person_id), status_code=303)
    return render(request, "checking-error.html", person, "credentials", service_id=service_id)


@app.get("/p/{person_id}/services/{service_id}/status")
async def services_status(
    service_id: str, person: dict = Depends(viewed_person), page: str = Query(...)
) -> dict:
    _require_service(service_id)
    person_id = person["id"]
    link = state.get_link(person_id, service_id)
    if link is None or link.request is None:
        return {"next": f"/p/{person_id}/services/{service_id}/results"}
    phase = link.request.phase
    if phase == page:
        return {"next": None}
    if phase in ("consent", "missing"):
        return {"next": f"/p/{person_id}/services/{service_id}/request"}
    return {"next": f"/p/{person_id}/services/{service_id}/{phase}"}


@app.get("/p/{person_id}/services/{service_id}/already", response_class=HTMLResponse)
async def services_already(
    request: Request, service_id: str, person: dict = Depends(viewed_person)
) -> HTMLResponse:
    _require_service(service_id)
    link = state.get_link(person["id"], service_id)
    decided_date = None
    if link is not None and link.determination is not None:
        decided_date = long_date(link.determination["decidedAt"])
    return render(request, "already-applied.html", person, "credentials", decided_date=decided_date)


@app.get("/p/{person_id}/services/{service_id}/results", response_class=HTMLResponse)
async def services_results(
    request: Request, service_id: str, person: dict = Depends(viewed_person)
) -> HTMLResponse:
    _require_service(service_id)
    person_id = person["id"]
    link = state.get_link(person_id, service_id)
    if link is None or (link.determination is None and link.refusal is None):
        return RedirectResponse(f"/p/{person_id}/credentials", status_code=303)

    if link.refusal:
        identity = application.held_identity(person_id)
        income = application.held_income(person_id)
        identity_ok = identity is not None and identity.outcome is Outcome.VERIFIED
        income_ok = bool(income) and all(c.outcome is Outcome.VERIFIED for c in income)
        sentence = results.refusal_sentence(link.refusal, identity_ok and income_ok, not identity_ok)
        return render(
            request, "results.html", person, "credentials",
            variant="refused", refusal_sentence=sentence,
        )

    determination = link.determination
    own_identity = application.held_identity(person_id)
    own_region = own_identity.address.get("addressRegion") if own_identity else None
    verdict = results.verdict(determination, own_region)
    eligible_entries = [p for p in determination["programs"] if p["outcome"] == "eligible"]
    held_ids = set(state.received_for(person_id).keys())
    all_held = all(e["credentialId"] in held_ids for e in eligible_entries)

    order = {p["code"]: p["order"] for p in all_programs()}
    eligible_cards = []
    for entry in eligible_entries:
        card = find_credential(person_id, entry["credentialId"].removeprefix("urn:uuid:"))
        if card is not None:
            eligible_cards.append(card)
    eligible_cards.sort(key=lambda c: order.get(c.program, 99))

    variant = "decided"
    if eligible_entries and not all_held:
        variant = "arriving"
    denials = None
    if any(p["outcome"] == "denied" for p in determination["programs"]):
        denials = results.denials(determination)

    return render(
        request, "results.html", person, "credentials",
        variant=variant, verdict=verdict, eligible_cards=eligible_cards, denials=denials,
        zero_of_five=not eligible_entries,
        valid_until=eligible_cards[0].valid_until if eligible_cards else "",
    )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
