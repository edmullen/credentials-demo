from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import state
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
from app.connections import add_employer, connections_title, provider_panels, remove_link
from app.credentials import credentials_for, find_credential, identity_status
from app.people import all_people, get_person
from app.providers import all_employers, get_provider
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
    identity = [c for c in credentials_for(person["id"]) if c.category == "Identity"]
    connected = any(p["connected"] for p in provider_panels(person["id"]))
    return render(
        request, "credentials.html", person, "credentials",
        identity=identity, connected=connected,
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
    return render(
        request, "credential.html", person, "credentials",
        c=found, tampered=found.outcome is Outcome.TAMPERED,
    )


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
    if get_provider(provider_id) is None or state.get_link(person["id"], provider_id) is None:
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


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
