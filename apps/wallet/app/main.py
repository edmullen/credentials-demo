from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.peers import wake_peers
from app.people import get_person

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


def render(request: Request, template: str, person: dict, active: str, **context) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        template,
        {"site": SITE, "nav": NAV, "person": person, "active": active, **context},
    )


@app.get("/")
async def index() -> RedirectResponse:
    return RedirectResponse(f"/p/{DEFAULT_PERSON}/credentials", status_code=303)


@app.get("/p/{person_id}/credentials", response_class=HTMLResponse)
async def credentials(request: Request, person: dict = Depends(viewed_person)) -> HTMLResponse:
    return render(request, "credentials.html", person, "credentials")


@app.get("/p/{person_id}/connections", response_class=HTMLResponse)
async def connections(request: Request, person: dict = Depends(viewed_person)) -> HTMLResponse:
    return render(request, "connections.html", person, "connections")


@app.get("/p/{person_id}/activity", response_class=HTMLResponse)
async def activity(request: Request, person: dict = Depends(viewed_person)) -> HTMLResponse:
    return render(request, "activity.html", person, "activity")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
