from pathlib import Path

from fastapi import Body, Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import clock, connections
from app.activity import grouped_events
from app.display import issuer_phrase, when
from app.paystubs import all_employer_ids, employers_for, landing_groups, paystub_view
from app.people import all_people, get_person
from app.presentation import verify_presentation
from app.trust import trust_list

BASE_DIR = Path(__file__).parent

app = FastAPI()
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Everything that varies in the shared layout, for this app. Per-person and per-screen
# values are passed per request instead.
SITE = {
    "theme": "payroll",
    "title": "Meridian Payroll — verifiable employment credentials",
    "name": "Meridian Payroll",
    "fonts_url": (
        "https://fonts.googleapis.com/css2?"
        "family=Archivo:wght@500;600;700&family=Public+Sans:wght@400;600&display=swap"
    ),
    "nav": ["Product", "Issuance", "Documentation", "Support"],
}

# The portal's nav items, in order. The key is also the last path segment.
PORTAL_NAV = [("paystubs", "Paystubs"), ("connections", "Connections"), ("activity", "Activity")]

# DCQL-shaped, naming the credential type only — no claims list (docs/design.md §3, §13 item 1).
DCQL_QUERY = {
    "credentials": [
        {"id": "identity", "format": "vc+jwt", "meta": {"type_values": [["IdentityCredential"]]}}
    ]
}


def viewed_person(person_id: str) -> dict:
    person = get_person(person_id)
    if person is None:
        raise HTTPException(status_code=404)
    return person


def nav_for(person: dict) -> list[tuple[str, str, str]]:
    return [(key, label, f"/p/{person['id']}/{key}") for key, label in PORTAL_NAV]


def render(request: Request, template: str, person: dict, active: str, **context) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        template,
        {"site": SITE, "nav": nav_for(person), "person": person, "active": active, **context},
    )


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html", {"site": SITE})


@app.get("/p/{person_id}/")
async def person_root(person_id: str, person: dict = Depends(viewed_person)) -> RedirectResponse:
    return RedirectResponse(f"/p/{person_id}/paystubs", status_code=303)


@app.get("/p/{person_id}/paystubs", response_class=HTMLResponse)
async def paystubs(request: Request, person: dict = Depends(viewed_person)) -> HTMLResponse:
    groups = landing_groups(person["id"])
    return render(request, "paystubs.html", person, "paystubs", groups=groups)


@app.get("/p/{person_id}/paystubs/{paystub_id}", response_class=HTMLResponse)
async def paystub(
    request: Request, paystub_id: str, person: dict = Depends(viewed_person)
) -> HTMLResponse:
    # A paystub id that isn't this person's is a 404, not a redirect: the URL shape shouldn't
    # imply one employee can address another's record.
    view = paystub_view(person["id"], paystub_id)
    if view is None:
        raise HTTPException(status_code=404)
    # No nav item is current on the detail page, as in Loop 2's credential detail (design §5).
    return render(request, "paystub.html", person, "", stub=view)


@app.get("/p/{person_id}/connections", response_class=HTMLResponse)
async def connections_page(request: Request, person: dict = Depends(viewed_person)) -> HTMLResponse:
    connection = connections.get_connection(person["id"])
    context = None
    if connection is not None:
        context = {
            "issuer_phrase": issuer_phrase(connection.issuer_name),
            "when": when(connection.connected_at),
        }
    return render(request, "connections.html", person, "connections", connection=context)


@app.get("/p/{person_id}/activity", response_class=HTMLResponse)
async def activity_page(request: Request, person: dict = Depends(viewed_person)) -> HTMLResponse:
    groups = grouped_events(person["id"])
    return render(request, "activity.html", person, "activity", groups=groups)


@app.get("/p/{person_id}/switch", response_class=HTMLResponse)
async def switch(
    request: Request,
    person: dict = Depends(viewed_person),
    from_screen: str = Query("paystubs", alias="from"),
) -> HTMLResponse:
    # Each row's employer names come from that person's paystubs, not a stored field — the
    # same grouping the landing page uses, so the two can't disagree (design.md §4, §11).
    screen = from_screen if from_screen in dict(PORTAL_NAV) else "paystubs"
    rows = [
        {**p, "employer_names": [e["employer_name"] for e in employers_for(p["id"])]}
        for p in all_people()
    ]
    return render(request, "person-switcher.html", person, "", people=rows, screen=screen)


@app.post("/api/connections/requests")
async def create_connection_request(payload: dict = Body(...)) -> JSONResponse:
    employers = payload.get("employers")
    known = all_employer_ids()
    if not isinstance(employers, list) or not employers or any(e not in known for e in employers):
        return JSONResponse(status_code=400, content={"error": "invalid_request"})
    request_id = connections.create_request(employers, clock.now())
    return JSONResponse(
        status_code=201,
        content={
            "requestId": request_id,
            "dcql_query": DCQL_QUERY,
            "response_uri": f"/api/connections/requests/{request_id}/presentation",
        },
    )


@app.post("/api/connections/requests/{request_id}/presentation")
async def submit_presentation(request_id: str, vp: dict = Body(...)) -> JSONResponse:
    now = clock.now()
    pending = connections.pop_request(request_id, now)
    if pending is None:
        return JSONResponse(status_code=404, content={"error": "unknown_request"})
    outcome, extra = verify_presentation(vp, pending.employers, trust_list(), now)
    if outcome == "invalid_presentation":
        return JSONResponse(status_code=400, content={"error": "invalid_presentation"})
    if outcome == "connected":
        person = extra["person"]
        connections.connect(person["id"], extra["issuer_name"], now)
        connections.log(
            person["id"], "verified", "New connection from your wallet established", now
        )
        return JSONResponse(status_code=200, content={"outcome": "connected"})
    return JSONResponse(status_code=200, content={"outcome": "refused", "reason": outcome})


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
