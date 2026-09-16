from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).parent

app = FastAPI()
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Everything that varies in the shared layout, for this app.
SITE = {
    "theme": "payroll",
    "title": "Meridian Payroll — verifiable employment credentials",
    "name": "Meridian Payroll",
    "fonts_url": (
        "https://fonts.googleapis.com/css2?"
        "family=Archivo:wght@500;600;700&family=Public+Sans:wght@400;600&display=swap"
    ),
    "nav": ["Product", "Issuance", "Documentation", "Support"],
    "user": {"name": "Rina Kapoor", "initials": "RK"},
    "footer": "Meridian Payroll, Inc.",
}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html", {"site": SITE})


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
