# CLAUDE.md

## What this is

Demo verifiable-credentials ecosystem: wallet (holds credentials), payroll (issues them), 
benefits (verifies, then issues). Credentials are signed JWTs shaped like W3C VCs, over simple 
REST. Demo only: no real PII, no passwords.

## How work is organized

Three documents drive the work and are worth reading before changing anything:

- [docs/decisions.md](docs/decisions.md): binding. If a change conflicts with it, raise it; don't silently diverge.
- `docs/intents/NNN-*.md`: problem and constraints for each loop.
- [docs/design.md](docs/design.md): the current loop's technical design.
- [docs/loop-log.md](docs/loop-log.md): a retro after each loop — what shipped, what went
  wrong, what to change. Worth checking before starting a new loop.

`docs/design/loop-N/` is the Claude Design handoff for that loop: a shared `cred.css` plus one
static HTML page per app, with a README documenting tokens, components and accessibility. It is
a **historical record** — the design files are never imported at runtime and are not edited to
match the apps.

## Branch 

Work on a branch; never commit to main.

## Architecture

Three independent FastAPI apps in one monorepo under `apps/<name>`. The defining constraint:

> **No app reads or imports anything outside its own directory.**

Each app is its own uv project (no root pyproject.toml; Render builds from each rootDir).

Each app owns its copy of cred.css; no shared stylesheet, template package, or sync script.

Theming is one attribute: `<html data-app="…">`, with all component CSS reading tokens only.

### Things that look like mistakes but are not

- **`href="/static/cred.css"` literally, never `url_for('static', …)`.** Starlette's `url_for`
  builds an absolute URL from the incoming request; behind Render's TLS proxy that arrives as
  `http://`, and browsers block the stylesheet as mixed content.
- **No JavaScript and no bundler, anywhere in these pages.** The mobile nav is a native
  `<details>` disclosure and the brand mark is a CSS-filled `<span>`. This is a design
  constraint, not an omission.
- **Copy, class names and ARIA attributes are verbatim from the mockups**, so `cred.css` applies
  without edits.
- **`apps/benefits`'s `cred.css` uses `data-app="benefits"`, not the handoff's `"benefit"`.**
  Deliberate rename to match the directory name, confined to that app's own copy. See
  `docs/design.md` §2 — don't "fix" it back to match the handoff.

## Commands

Everything runs from inside an app directory — there is no repo-root Python project.

```bash
cd apps/wallet && uv sync && uv run pytest
```

```bash
uv run pytest tests/test_app.py::test_health
```

Run one app locally with reload (ports: wallet 8001, payroll 8002, benefits 8003):

```bash
cd apps/wallet && uv run uvicorn app.main:app --reload --port 8001
```

## CI and deployment

`.github/workflows/ci.yml` runs on PRs to `main` **and** on pushes to `main` — the second
trigger matters, because Render's `autoDeployTrigger: checksPass` waits for checks on the merge
commit itself. Two rules follow from that and are easy to break:

- **No `paths:` filters on the workflow.** A required check whose workflow is skipped stays
  pending forever and blocks the PR. All three suites run in seconds. Path scoping belongs only
  to Render's `buildFilter`.
- **Never cancel in-progress runs on `main`** (`cancel-in-progress` is gated to
  `pull_request`). A cancelled check counts as "not passed", and Render would skip the deploy.

The `test` job is one matrix over `[wallet, payroll, benefits]` with `fail-fast: false`. A
separate `ci-passed` job aggregates it and is **the only required status check** in branch
protection — so adding or renaming an app never requires touching branch protection settings.

`render.yaml` at the repo root defines three free web services. `rootDir` is per app;
`buildFilter.paths` are relative to the **repo root**, not to `rootDir`. Editing one app's files
redeploys only that service; editing `docs/` redeploys none. `PYTHON_VERSION`
in `render.yaml` must be kept in step with each app's `.python-version`.

Live at `https://cred-demo-<app>.onrender.com` (`wallet` / `payroll` / `benefits`). Render's
free tier spins services down after ~15 min idle — the first request after that, including
right after a fresh Blueprint deploy, can take up to a minute or time out once before
succeeding. Don't treat that as a failure; retry before diagnosing.
