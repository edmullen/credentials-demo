from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.paystubs import employers_for
from app.peers import wake_peers
from app.people import all_people, get_person

BASE_DIR = Path(__file__).parent


@asynccontextmanager
async def lifespan(_: FastAPI):
    tasks = wake_peers()
    yield
    for task in tasks:
        task.cancel()


app = FastAPI(lifespan=lifespan)
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

# The portal's nav items, in order. Connections and Activity have no route yet (Loop 4) and
# stay ordinary #-links, styled identically to Paystubs — Loop 0's convention.
PORTAL_NAV = [("paystubs", "Paystubs"), ("connections", "Connections"), ("activity", "Activity")]


def viewed_person(person_id: str) -> dict:
    person = get_person(person_id)
    if person is None:
        raise HTTPException(status_code=404)
    return person


def nav_for(person: dict) -> list[tuple[str, str, str]]:
    return [
        (key, label, f"/p/{person['id']}/paystubs" if key == "paystubs" else "#")
        for key, label in PORTAL_NAV
    ]


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
    # #18 adds the employer sections; this PR's landing page is identity plus the Wallet card.
    return render(request, "paystubs.html", person, "paystubs")


@app.get("/p/{person_id}/switch", response_class=HTMLResponse)
async def switch(request: Request, person: dict = Depends(viewed_person)) -> HTMLResponse:
    # Each row's employer names come from that person's paystubs, not a stored field — the
    # same grouping the landing page uses, so the two can't disagree (design.md §4, §11).
    rows = [
        {**p, "employer_names": [e["employer_name"] for e in employers_for(p["id"])]}
        for p in all_people()
    ]
    return render(request, "person-switcher.html", person, "", people=rows)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
