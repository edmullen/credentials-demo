# Intent 000: Walking Skeleton (Loop 0)

## Problem
We have decisions (`docs/decisions.md`) but no running system. Before building any
credential logic, we need proof that the full path — code on `main` → CI → deploy →
public URL — actually works for all three apps. Without this, later loops would be
debugging deployment and app logic at the same time.

## Proposed outcome
Three placeholder FastAPI apps (`wallet`, `payroll`, `benefits`), each monorepo-scoped
under `apps/<name>`, each with:
- `/` returning the app's name (e.g. an `<h1>Wallet</h1>`) — no styling or description yet
- `/health` returning a 200

All three are deployed to production on Render via a `render.yaml` Blueprint, connected
to this GitHub repo, with `autoDeployTrigger: checksPass`. A pytest suite (one test per
app, hitting `/` and `/health` with FastAPI's TestClient) runs in GitHub Actions on every
PR, and passing tests gate merge to `main` via branch protection.

Done means: PR merges trigger a Render deploy automatically, and Ed manually visits each
app's `/` and `/health` on its live Render URL and confirms a 200.

## Affected users/systems
- **Ed** (solo developer): sets up the repo structure, CI workflow, and Render Blueprint.
- **GitHub repo** `edmullen/credentials-demo`: gets `apps/wallet`, `apps/payroll`,
  `apps/benefits`, a GitHub Actions workflow, and branch protection rules on `main`.
- **Render**: account exists but is not yet connected to this repo — that connection is
  in scope for this loop, done through the `render.yaml` Blueprint.
- No end users yet — no persona picker, no credential logic. That starts in Loop 1.

## Constraints
- Python 3.12 via `uv`; FastAPI; pytest — per `docs/decisions.md`.
- Free Render plan; `rootDir`/`buildFilter` per app so each service only rebuilds on
  changes to its own directory.
- Branch protection requires only the pytest job to pass (no lint gate yet, to keep
  Loop 0 minimal — lint can be added in a later loop if it becomes useful).
- No real PII, light security — consistent with the demo-only scope.

## Open questions
- Render Blueprint connection (linking the existing Render account to this GitHub repo)
  hasn't been done yet — first concrete step of this loop.
- Do the three Render services need distinct/memorable subdomains now, or is the
  Render-generated default URL fine until a later loop?
- Should the GitHub Actions workflow be one job matrix-ed over the three apps, or three
  separate jobs? (Affects how `buildFilter`-style path-scoping is mirrored in CI.)
