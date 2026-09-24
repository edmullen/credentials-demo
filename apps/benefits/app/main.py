from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import signing

BASE_DIR = Path(__file__).parent

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
        "family=Libre+Franklin:wght@500;600;700&family=Public+Sans:wght@400;600&display=swap"
    ),
    "nav": ["About the program", "Who can apply", "Contact us"],
    "user": {"name": "Jordan Diaz", "initials": "JD"},
}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html", {"site": SITE})


@app.get("/health")
async def health() -> JSONResponse:
    result = signing.status()
    if not result.ok:
        return JSONResponse(status_code=503, content={"status": "unhealthy", "reason": result.reason})
    return JSONResponse(content={"status": "ok"})


@app.get("/.well-known/jwks.json")
async def jwks() -> dict:
    return {"keys": [signing.public_jwk()]}
