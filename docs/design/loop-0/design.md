# Design: Loop 0 — Walking Skeleton

Technical design for [Intent 000](../../intents/000-walking-skeleton.md), following the defaults in
[decisions.md](../../decisions.md) and the Claude Design handoff in [design/loop-0/](README.md).

## 1. Overview

Three independent FastAPI apps (**wallet**, **payroll**, **benefits**) share one monorepo but
nothing else. Each app serves its Loop 0 mockup as a server-rendered Jinja template at `/`, plus
a `/health` endpoint. GitHub Actions runs each app's pytest suite on every PR and on every push
to `main`. Branch protection makes a passing run a condition of merging. Render deploys each app
as its own free web service from a `render.yaml` Blueprint. A service redeploys only when its own
directory changes, and only after CI passes on that commit.

**Change from the intent.** Intent 000 describes `/` as a bare `<h1>` with no styling. The
mockups were finished before Build started, so `/` renders the real mockup page instead. Nothing
else in the intent's scope changes: no personas, no credential logic, no JavaScript.

## 2. Monorepo layout

```
credentials-demo/
├── .github/workflows/ci.yml
├── render.yaml
├── docs/                           # decisions, intents, design handoff, this file
└── apps/
    ├── wallet/                     # Render rootDir; self-contained uv project
    │   ├── .python-version         # 3.12
    │   ├── pyproject.toml          # deps: fastapi, jinja2, uvicorn[standard]
    │   │                           # dev group: pytest, httpx
    │   ├── uv.lock
    │   ├── app/
    │   │   ├── __init__.py
    │   │   ├── main.py             # FastAPI app: /static mount, templates, GET /, GET /health
    │   │   ├── templates/
    │   │   │   ├── base.html       # <html data-app>, head, skip link, header, footer
    │   │   │   └── index.html      # extends base.html; the <main> content from the mockup
    │   │   └── static/
    │   │       └── cred.css        # this app's own stylesheet
    │   └── tests/
    │       └── test_app.py
    ├── payroll/                    # same shape
    └── benefits/                   # same shape
```

### Rules

- **Each app is a standalone uv project with its own `uv.lock`.** There is no uv workspace and
  no root `pyproject.toml`, because Render builds each service from its `rootDir` and cannot see
  a lockfile at the repo root.
- **No app reads or imports anything outside its own directory.** No shared Python package, no
  shared templates, no shared static files.
- The package inside each app is named `app`, so the entry point is always `app.main:app`.
  Because the projects are separate, the matching names never clash.

### Mockup → template mapping

| App dir | Mockup | `data-app` | Google Fonts families |
| --- | --- | --- | --- |
| `apps/wallet` | `design/loop-0/wallet.html` | `wallet` | Newsreader 400/600, Public Sans 400/600 |
| `apps/payroll` | `design/loop-0/payroll.html` | `payroll` | Archivo 500/600/700, Public Sans 400/600 |
| `apps/benefits` | `design/loop-0/benefit.html` | `benefits` | Libre Franklin 500/600/700, Public Sans 400/600 |

**Deviation from the handoff.** The mockup and `docs/design/loop-0/cred.css` use the singular
`benefit` as the theme value, matching the mockup's filename. The app instead uses `benefits`,
matching its own directory name — the app's `app/static/cred.css` copy has its five
`html[data-app="benefit"]` selectors (and the introductory comment) renamed to `"benefits"`.
This is confined to that one file: `docs/design/loop-0/` is left untouched as the historical
record of what was handed off.

### `main.py` shape

- `app = FastAPI()`
- `app.mount("/static", StaticFiles(directory=<app dir>/static), name="static")`, with paths
  resolved relative to `main.py` (`Path(__file__).parent`) so the app runs the same from any
  working directory.
- `templates = Jinja2Templates(directory=<app dir>/templates)`
- A module-level `SITE` dict holds everything that varies in the layout:
  `theme`, `title`, `name` (brand), `fonts_url`, `nav` (list of labels), `user`
  (`name`, `initials`), `footer`.
- `GET /` renders `index.html` with `SITE` in the context and returns `text/html`.
- `GET /health` returns `{"status": "ok"}` with a 200. No dependencies, no I/O.

### Templates

- `base.html` holds the page skeleton, copied from the mockup: `<html lang="en" data-app="{{ site.theme }}">`,
  the head (charset, viewport, title, font `preconnect`s and link, stylesheet), the skip link,
  `<header class="header">` with brand, nav, initials (`role="img"` + `aria-label`) and the
  `<details class="nav-menu">` mobile menu, then `<main class="main" id="main">{% block main %}{% endblock %}</main>`
  and `<footer class="footer">`.
- `index.html` extends `base.html` and fills `main` with the mockup's eyebrow, `<h1>`, purpose
  paragraph, rule, and card, including the badge, disabled `<button>`s and payroll's secondary
  link.
- Copy is **verbatim from the mockups**. Class names, ARIA attributes and element choices are
  unchanged, so `cred.css` applies without edits.
- The stylesheet link is the literal path **`/static/cred.css`**, not `url_for('static', …)`.
  Starlette's `url_for` builds an absolute URL from the incoming request. Behind Render's TLS
  proxy that request arrives as `http://`, and browsers block the resulting stylesheet as mixed
  content.

### Out of scope for Loop 0 (noted, not done)

- Nav links stay `href="#"`, which is the known gap #1 in the design README. The brand link
  points to `/`.
- The two plain-language rewrites from the design README are not applied (known gap #2).
- Google Fonts are loaded from Google, not self-hosted.
- `design/loop-0/index.html` (the system reference page) is not served by any app.
- No JavaScript and no bundler, as the design requires.

## 3. CSS: where it lives and how each app gets it

**Each app owns its own stylesheet** at `apps/<app>/app/static/cred.css`. The app's
`StaticFiles` mount serves it at `/static/cred.css`. The file lives inside the app's `rootDir`,
so the Render service has it with no copy step, build step or symlink.

- **Seeding.** During Build, `docs/design/loop-0/cred.css` is copied verbatim into all three apps
  once. From then on the three files are **independent**. Nothing keeps them in sync and nothing
  checks for drift.
- **Divergence is allowed.** Each app may delete the other apps' `html[data-app="…"]` theme
  blocks, rename tokens, or restyle components without affecting the other two. Each
  `base.html` is independent in the same way.
- **Deploy scope.** Editing one app's CSS changes files under that app's directory only, so only
  that Render service rebuilds (see §6).
- **Design handoff.** `docs/design/loop-0/` stays as the historical record of what was handed
  off. From Loop 1 on, the stylesheet of whichever app is being designed — for example
  `apps/wallet/app/static/cred.css` — is handed to Claude Design as a file, and what comes back
  is committed under `docs/design/loop-N/`. Not `/design-sync`: it converts a built JavaScript
  component library, which this repo does not have ([decisions.md](../../decisions.md)).
- **Trade-off.** A change meant for all three apps, such as an accessibility fix to `.btn`, has to
  be made in three files. That is accepted: the apps are meant to look different, and
  independence avoids a sync mechanism.

## 4. Tests

Each app has its own suite, run from its own directory:

```bash
cd apps/wallet && uv sync && uv run pytest
```

`tests/test_app.py` uses FastAPI's `TestClient` (which needs `httpx`, in the dev group):

| Request | Assertions |
| --- | --- |
| `GET /` | 200; `content-type` starts with `text/html`; body contains `data-app="<theme>"`, the page's `<h1>` text, and `/static/cred.css` |
| `GET /health` | 200; JSON body equals `{"status": "ok"}` |
| `GET /static/cred.css` | 200; `content-type` starts with `text/css` |

To run an app locally with reload:

```bash
cd apps/wallet && uv run uvicorn app.main:app --reload --port 8001
```

Ports: wallet 8001, payroll 8002, benefits 8003.

Add `.venv/`, `__pycache__/` and `.pytest_cache/` to the root `.gitignore`.

## 5. GitHub Actions CI

File: `.github/workflows/ci.yml`

### Triggers

- `pull_request` targeting `main`. This check gates merges.
- `push` to `main`. Render's `checksPass` waits for checks **on the commit being deployed**,
  which is the merge commit on `main`. Without this trigger that commit has no checks to wait on.
- **No `paths:` filters.** A required check whose workflow is skipped stays pending, and the PR
  stays blocked. All three suites run in seconds, so every run tests all three apps.

### Concurrency

```yaml
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}
```

Superseded PR runs are cancelled. Runs on `main` are never cancelled, because a cancelled check
counts as "not passed" and Render would skip deploying that commit.

### Jobs

1. **`test`**, a matrix over the apps:
   - `strategy.matrix.app: [wallet, payroll, benefits]`, `fail-fast: false`, so one failing app
     doesn't hide results from the others.
   - `defaults.run.working-directory: apps/${{ matrix.app }}`
   - Steps:
     1. `actions/checkout`
     2. `astral-sh/setup-uv`, pinned to a major version, with `enable-cache: true` and
        `cache-dependency-glob: apps/${{ matrix.app }}/uv.lock`
     3. `uv sync --frozen`: installs Python 3.12 from `.python-version` and fails if `uv.lock`
        is stale
     4. `uv run pytest`
2. **`ci-passed`**, the single gate:
   - `needs: [test]`, `if: always()`
   - Fails unless `needs.test.result == 'success'`.
   - **This is the only required status check in branch protection.** Matrix legs show up as
     `test (wallet)` and so on. With one fixed aggregate name, adding or renaming an app never
     requires changing branch protection.

This answers the intent's open question: **one matrix job**, with no CI-side path scoping. Path
scoping belongs only to Render's `buildFilter`.

### Branch protection (manual, GitHub settings)

On `main`:
- Require a pull request before merging.
- Require status check **`ci-passed`**. It only appears in the picker after the workflow has run
  at least once, so push the workflow before configuring this.
- No lint gate in Loop 0, per the intent.

## 6. Render Blueprint

File: `render.yaml` at the repo root.

```yaml
services:
  - type: web
    name: cred-demo-wallet
    runtime: python
    plan: free
    branch: main
    rootDir: apps/wallet
    buildFilter:
      paths:
        - apps/wallet/**
    autoDeployTrigger: checksPass
    buildCommand: pip install uv && uv sync --frozen --no-dev
    startCommand: .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /health
    envVars:
      - key: PYTHON_VERSION
        value: "3.12.x"   # pin the exact 3.12 patch at Build time

  - type: web
    name: cred-demo-payroll
    runtime: python
    plan: free
    branch: main
    rootDir: apps/payroll
    buildFilter:
      paths:
        - apps/payroll/**
    autoDeployTrigger: checksPass
    buildCommand: pip install uv && uv sync --frozen --no-dev
    startCommand: .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /health
    envVars:
      - key: PYTHON_VERSION
        value: "3.12.x"

  - type: web
    name: cred-demo-benefits
    runtime: python
    plan: free
    branch: main
    rootDir: apps/benefits
    buildFilter:
      paths:
        - apps/benefits/**
    autoDeployTrigger: checksPass
    buildCommand: pip install uv && uv sync --frozen --no-dev
    startCommand: .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /health
    envVars:
      - key: PYTHON_VERSION
        value: "3.12.x"
```

### Notes

- **`rootDir`** sets the directory the build and start commands run in, and limits the service to
  that directory. That's why each app must be fully self-contained (§2, §3).
- **`buildFilter.paths`** are relative to the **repo root**, not to `rootDir`. They decide which
  commits trigger a build: changes under `docs/`, `.github/`, `render.yaml` or another app's
  directory don't rebuild this service.
- **`autoDeployTrigger: checksPass`** means Render deploys a new `main` commit only after every
  GitHub check on that commit passes. If a check fails, the previous deploy stays live.
- **`healthCheckPath: /health`** lets Render confirm a new instance responds before switching
  traffic to it.
- **Python version.** `PYTHON_VERSION` must be kept in step with each app's `.python-version`.
  Pin the exact patch release when writing the file.
- **Build risk to verify on first deploy.** The design assumes `uv sync` in Render's Python build
  environment creates `.venv/` inside `rootDir`, and that `.venv/` survives into runtime. If it
  doesn't, fall back to committing `uv export --frozen --no-dev -o requirements.txt` and using
  `pip install -r requirements.txt` with a plain `uvicorn …` start command.
- **URLs.** The default `https://<name>.onrender.com` subdomains are fine for Loop 0, which
  answers the intent's open question. Service names are chosen so the defaults read well. Render
  adds a suffix if a name is taken.
- **Free plan.** Instances spin down after about 15 minutes idle. The first request afterwards
  can take about a minute, so allow for that during manual verification.
- **One-time connection (manual).** Render dashboard → **New → Blueprint** → connect GitHub →
  select `edmullen/credentials-demo` → apply. After this, edits to `render.yaml` on `main` sync
  automatically.

## 7. Build order

1. Scaffold the three apps (§2), seed each `cred.css` (§3), and write tests (§4). Run each suite
   locally.
2. Add `ci.yml` (§5). Open a PR and confirm all matrix legs and `ci-passed` go green.
3. Merge, then turn on branch protection requiring `ci-passed`.
4. Add `render.yaml` (§6) through a PR, merge, and connect the Blueprint in Render.
5. Walk the acceptance criteria below.

## 8. Acceptance criteria

1. `apps/wallet`, `apps/payroll` and `apps/benefits` are each a standalone uv project
   (`pyproject.toml`, `uv.lock`, `.python-version` set to 3.12). None of them reads or imports
   files outside its own directory.
2. `GET /` on each app returns 200 HTML that matches its mockup in `docs/design/loop-0/`:
   `data-app` theme, header brand/nav/initials, eyebrow, `<h1>`, purpose, card copy, badge and
   button states. It looks like the matching screenshot in `docs/design/loop-0/screenshots/` at
   desktop width, and switches to the `<details>` menu at 40rem and below.
3. `GET /health` on each app returns 200 with body `{"status": "ok"}`.
4. `GET /static/cred.css` on each app returns 200 `text/css`, served from that app's own
   `app/static/cred.css`. The repo has no shared stylesheet, shared template or sync script.
5. `uv run pytest` passes in each of the three app directories.
6. `.github/workflows/ci.yml` runs on PRs to `main` and on pushes to `main`. `ci-passed` succeeds
   only when all three `test` matrix legs succeed.
7. `main` is protected: merges require a PR with `ci-passed` green, and direct pushes are
   rejected.
8. `render.yaml` syncs as a Blueprint and creates three free web services, each with its own
   `rootDir`, `buildFilter`, `autoDeployTrigger: checksPass` and `healthCheckPath: /health`.
9. A merged change only under `apps/payroll/**` (for example its `cred.css`) redeploys only the
   payroll service. A change only under `docs/` redeploys none of the services.
10. After a merge, Render starts the deploy only once CI has passed on the `main` commit. When a
    check fails on `main`, the previous deploy stays live.
11. Ed opens each app's live Render URL and gets a 200 from both `/` and `/health`. The page
    renders fully styled over HTTPS, with no mixed-content warnings and no 404 for `cred.css`.
12. The pages contain no client-side JavaScript and use no bundler. The only external requests
    are to Google Fonts.
