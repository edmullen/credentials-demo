# Project Decisions Log

## Product
- **Concept:** Demo verifiable-credentials ecosystem with 3 apps: **Wallet** (Public User holds and presents credentials), **Payroll Provider** (issues income credentials), **Benefit Provider** (requests data from the wallet, checks eligibility for five fictional programs, issues its own credentials).
- **Scope:** Demo only. No real PII, light security.
- **Identity photos are AI-generated faces of people who do not exist** — never photos of real people, even with consent. A face is personal (often biometric) data, and this repo is public and permanent. The current set was generated with **ChatGPT** (OpenAI) and each image is watermarked "Not real person". Ed confirmed on 2026-09-18 that OpenAI's terms permit this use. Any future photo tool needs the same confirmation before its output is committed.
- **Nothing impersonates a real government service.** The states, Meridian Payroll and the Benefits provider are fictional. Identifiers must not point at real agencies' domains — the states are `did:example:` issuers, the form the W3C specs reserve for illustration — and the apps present themselves as a demo throughout.
- **Realism:** Signed JWTs shaped like W3C Verifiable Credentials. Simple REST APIs stand in for OpenID4VCI/VP. Full standards could come in a later loop.
- **W3C alignment:** The target is the **VC Data Model 2.0**, secured as a JWT per the W3C **VC-JOSE-COSE** spec (not the superseded 1.1 approach, which nested the credential in a `vc` claim and used `issuanceDate`). Building a *subset* of the standard is expected; taking an approach *contrary* to it is not. Concretely: claims are named, camelCase `credentialSubject` properties rather than generic `{kind, value}` wrappers; a credential's class goes in its `type` array; structured values use an established vocabulary type (e.g. schema.org `MonetaryAmount`) rather than an invented one; and standard fields such as `validFrom` are used instead of custom equivalents.
- **Users:** No passwords. You pick from fake personas.
- **The credential model lives in [docs/credential-model.md](credential-model.md)** — the target flow, issuers and trust, claim schemas, W3C conformance, and validity and failure. Each section ends with the decisions made when it was reviewed.
- **Benefit programs and eligibility rules live in [docs/benefit-programs.md](benefit-programs.md)** — five programs, the FPL/SMI/county-AMI variables, and the Dividend calculation. Food, Energy and Housing are pass/fail on an annual income test; Health and Dividend calculate a result on a sliding scale — a discount on a $750/month plan and a monthly payment respectively — tapered so that earning more never leaves someone worse off.
- **The Benefits app holds no public-user accounts.** There is no applicant-facing portal; the user's own record of applying lives in the Wallet's Activity log, making the Wallet the system of record for the user. Benefits does retain a **determination record** for a future admin/caseworker view — the submitted data, the presented credentials kept **verbatim** so the decision can be re-verified later, the derived figures used, and the decision. That admin experience is deliberately unplanned.

## Delivery approach
- The SDLC stages follow the Claude Academy course: Plan → Design → Build → Test → Deploy → Maintain.
- **The roadmap lives in the GitHub Project "Credentials demo"**
  (`https://github.com/users/edmullen/projects/1`). Each loop is a repo milestone named
  `Loop N - <name>`, and issues carry GitHub blocked-by dependencies. The project is the
  source of truth for what is in a loop; this file records only the loop boundaries and why
  they fall where they do.
- **Loop 0 — Walking skeleton (shipped):** 3 placeholder apps (home page plus `/health`)
  deployed to production through CI/CD.
- **Loop 1 — Foundations:** definition and research only; ships no app code. The credential
  model and target end-to-end flow, the five benefit programs and their eligibility criteria,
  and the sample data set. A loop with no deployment is deliberate: these three artifacts
  otherwise get designed three separate times, once per consuming loop.
- **Loop 2 — Wallet stands up:** sample public users, hard-coded identity credentials with a
  Verified/Tampered signature badge, plus the Connections and Activity screens.
- **Loop 3 — Payroll stands up:** sample Payroll accounts and paystub display. Independent of
  Loop 2 — the two can run in either order.
- **Loop 4 — Wallet and Payroll connect:** employer lookup, Payroll's inbound connection and
  verification request, and the Wallet's consent screen. Payroll acts as a *verifier* here.
- **Loop 5 — Payroll issues credentials:** Payroll turns paystubs into credentials; the Wallet
  requests and displays them. Payroll acts as an *issuer* here.
- **Loop 6 — Benefits programs and eligibility:** Benefits publishes its five programs, then
  verifies credentials and makes an eligibility decision. **Only the program pages are defined
  so far, by choice.** Benefits introduces no role that Loops 4 and 5 don't already build
  (verifier, then issuer), so its detailed decisions can wait — provided Loop 1 records the
  claims an eligibility check will need.
- **Design stage uses Claude Design** for experience design (a shared design system plus
  screens, as plain HTML/CSS), handed off to Claude Code and versioned in `docs/design/loop-N/`.
  From Loop 2 on — the first loop with real screens — `/design-sync` imports the repo's real
  CSS back into Claude Design.

## Technical defaults
- Python 3.12 (installed with **uv**; leave macOS's built-in Python 3.9.6 alone) + FastAPI, with HTML templates so Ed's HTML/CSS skills carry over
- One public monorepo on GitHub (`credentials-demo`) with `apps/wallet`, `apps/payroll`, `apps/benefits`
- Wallet is a web app, not native mobile
- pytest for tests; GitHub Actions for CI; branch protection on `main`
- **Hosting:** Render via a `render.yaml` Blueprint (free plan, `rootDir` and `buildFilter` per app, `autoDeployTrigger: checksPass`). GCP Cloud Run still makes sense eventually, but there is **no move planned and no urgency** — revisit only if Render blocks something the demo needs.
- **Sample data:** one generated set (people, employers, paystubs), then copied per app — each app keeps only the slice it needs. No shared data store or package, per the monorepo constraint. Some duplication across apps is expected.
- **One-shot generators are allowed; sync scripts are not.** A script under `tools/` may generate files into several apps' directories — the sample data (#6), and the keys, trust lists and signed identity credentials (docs/credential-model.md §2) — provided it is run by hand, its output is committed, and nothing runs it at build or deploy time. What stays ruled out is a script that *keeps* copies aligned on an ongoing basis. (The "no sync script" rule originated in a proposal to sync `cred.css` across apps, which was rejected as unnecessary; each app still owns its own `cred.css`.)
