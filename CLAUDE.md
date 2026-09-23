# CLAUDE.md

## What this is

Demo verifiable-credentials ecosystem: wallet (holds credentials), payroll (issues them), 
benefits (verifies, then issues). Credentials are signed JWTs shaped like W3C VCs, over simple 
REST. Demo only: no real PII, no passwords.

## How work is organized

Three documents drive the work and are worth reading before changing anything:

- [docs/decisions.md](docs/decisions.md): binding. If a change conflicts with it, raise it; don't silently diverge.
- `docs/intents/NNN-*.md`: problem and constraints for each loop.
- [docs/design.md](docs/design.md): the current loop's technical design. When the next loop's
  design replaces it, the outgoing one is archived to `docs/design/loop-N/design.md`.
- [docs/loop-log.md](docs/loop-log.md): a retro after each loop — what shipped, what went
  wrong, what to change. Worth checking before starting a new loop.

Three reference documents from Loop 1 define what the apps build *towards*. Read the relevant one
before touching credentials, eligibility or sample data:

- [docs/credential-model.md](docs/credential-model.md): the target flow, issuers and keys,
  claim schemas, W3C conformance, validity and failure messages.
- [docs/benefit-programs.md](docs/benefit-programs.md): the five programs and their eligibility
  rules.
- [docs/sample-data.md](docs/sample-data.md): the 25 sample people, and the expected eligibility
  outcome for each — the test oracle for the Benefits app. Generated; don't edit by hand.

`docs/design/loop-N/` holds both halves of a loop's design record. The **Claude Design
handoff** — a shared `cred.css` plus one static HTML page per app, with a README documenting
tokens, components and accessibility — and, once a later loop supersedes it, that loop's
**`design.md`**, the technical design Claude Code worked to. Both are a **historical record**:
the design files are never imported at runtime and are not edited to match the apps.

## Branch 

Work on a branch; never commit to main.

## Architecture

Three independent FastAPI apps in one monorepo under `apps/<name>`. The defining constraint:

> **No app reads or imports anything outside its own directory.**

Each app is its own uv project (no root pyproject.toml; Render builds from each rootDir).

Each app owns its copy of cred.css; no shared stylesheet, template package, or sync script.
A hand-run, one-shot generator under `tools/` that writes committed files into several apps is
allowed — see `docs/decisions.md`. Apps never import or run it.

Theming is one attribute: `<html data-app="…">`, with all component CSS reading tokens only.

### Things that look like mistakes but are not

- **`href="/static/cred.css"` literally, never `url_for('static', …)`.** Starlette's `url_for`
  builds an absolute URL from the incoming request; behind Render's TLS proxy that arrives as
  `http://`, and browsers block the stylesheet as mixed content.
- **Almost no JavaScript, and no framework or bundler.** JavaScript is allowed sparingly, only
  where a no-JS option is insufficient, as progressive enhancement over a page that already
  works without it (`docs/decisions.md`). The mobile nav is a native `<details>` disclosure and
  the brand mark is a CSS-filled `<span>`. The one script is inline on the Wallet's two pending
  pages, polling a status URL; without it, **Check again** does the same job by hand.
- **One uvicorn worker per app, with no `--workers`.** Runtime state (connections, requests,
  activity) lives in each app's memory. More than one worker would split it and break the
  connection flow.
- **The Wallet sends Payroll's `response_uri` only to the origin it already holds.** Payroll
  returns that URI as a path, not an absolute URL, for the same TLS-proxy reason as the
  `cred.css` href above.
- **Copy, class names and ARIA attributes are verbatim from the mockups**, so `cred.css` applies
  without edits.
- **`apps/benefits`'s `cred.css` uses `data-app="benefits"`, not the handoff's `"benefit"`.**
  Deliberate rename to match the directory name, confined to that app's own copy. See
  `docs/design/loop-0/design.md` §2 — don't "fix" it back to match the handoff.

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

Payroll signs with a key that isn't committed (docs/design.md §3), so it needs
`--env-file .env` and won't start locally until that file exists — run
`uv run tools/generate_credentials.py` from the repo root first (once, or again after a fresh
clone):

```bash
cd apps/payroll && uv run uvicorn app.main:app --reload --port 8002 --env-file .env
```

`.claude/launch.json` starts the same three apps for the desktop app's preview pane, with the
Wallet pointed at the local Payroll. It also has a `handoff` server that serves `docs/design/` on
port 8010, so a loop's handoff pages (`http://localhost:8010/loop-N/…`) can be compared side by
side with the running apps (Loop 4a's design, §10).

The one exception to "run from inside an app": the sample-data generator is a self-contained
uv script, run from the repo root. It regenerates `tools/sample_data/generated/` and
`docs/sample-data.md` from the hand-written YAML, and refuses to write anything if an edit
breaks one of the curated placements (docs/sample-data.md):

```bash
uv run tools/generate_sample_data.py
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
redeploys only that service; editing `docs/` or `tools/` redeploys none. `PYTHON_VERSION`
in `render.yaml` must be kept in step with each app's `.python-version`.

Live at `https://cred-demo-<app>.onrender.com` (`wallet` / `payroll` / `benefits`). Render's
free tier spins services down after ~15 min idle — the first request after that, including
right after a fresh Blueprint deploy, can take up to a minute or time out once before
succeeding. Don't treat that as a failure; retry before diagnosing.
