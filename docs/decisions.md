# Project Decisions Log

## Product
- **Concept:** Demo verifiable-credentials ecosystem with 3 apps: **Wallet** (Public User holds and presents credentials), **Payroll Provider** (issues income credentials), **Benefit Provider** (requests data from the wallet, checks eligibility for a fictional program, issues its own credential).
- **Scope:** Demo only. No real PII, light security.
- **Realism:** Signed JWTs shaped like W3C Verifiable Credentials. Simple REST APIs stand in for OpenID4VCI/VP. Full standards could come in a later loop.
- **Users:** No passwords. You pick from fake personas.

## Delivery approach
- The SDLC stages follow the Claude Academy course: Plan → Design → Build → Test → Deploy → Maintain.
- **Loop 0 (walking skeleton):** 3 placeholder apps (home page plus /health) deployed to production through CI/CD.
- **Loop 1:** The Wallet displays a hard-coded signed credential with a Verified or Tampered badge.
- **Loop 2 (planned):** Payroll issues a credential and the Wallet receives it.
- **Loop 3 (planned):** Benefits requests data from the Wallet and issues its own credential.
- **Loop 4 (planned):** Move hosting to GCP Cloud Run.
- Guidance lives in `playbook.md`.
- **Design stage uses Claude Design** for experience design (a shared design system plus screens, as plain HTML/CSS), handed off to Claude Code and versioned in `docs/design/loop-N/`. From Loop 1 on, `/design-sync` imports the repo's real CSS back into Claude Design.

## Technical defaults
- Python 3.12 (installed with **uv**; leave macOS's built-in Python 3.9.6 alone) + FastAPI, with HTML templates so Ed's HTML/CSS skills carry over
- One public monorepo on GitHub (`credentials-demo`) with `apps/wallet`, `apps/payroll`, `apps/benefits`
- Wallet is a web app, not native mobile
- pytest for tests; GitHub Actions for CI; branch protection on `main`
- **Hosting:** Render via a `render.yaml` Blueprint (free plan, `rootDir` and `buildFilter` per app, `autoDeployTrigger: checksPass`). Move to GCP Cloud Run later.
