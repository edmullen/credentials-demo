# Project Decisions Log

## Product
- **Concept:** Demo verifiable-credentials ecosystem with 3 apps: **Wallet** (Public User holds and presents credentials), **Payroll Provider** (issues income credentials), **Benefit Provider** (requests data from the wallet, checks eligibility for five fictional programs, issues its own credentials).
- **Scope:** Demo only. No real PII, but the fake sample data is **treated as if it were PII** (Ed, 2026-10-03, amending "light security"): the security design is held to the standard a real deployment would face, apart from the deliberate gaps in **Security** below.
- **Identity photos are AI-generated faces of people who do not exist** — never photos of real people, even with consent. A face is personal (often biometric) data, and this repo is public and permanent. The current set was generated with **ChatGPT** (OpenAI) and each image is watermarked "Not real person". Ed confirmed on 2026-09-18 that OpenAI's terms permit this use. Any future photo tool needs the same confirmation before its output is committed.
- **Nothing impersonates a real government service.** The states, Meridian Payroll and the Benefits provider are fictional. Identifiers must not point at real agencies' domains — the states are `did:example:` issuers, the form the W3C specs reserve for illustration — and the apps present themselves as a demo throughout.
- **Realism:** Signed JWTs. Simple REST APIs stand in for OpenID4VCI/VP. Full standards could come in a later loop. *Amended 2026-10-03:* the demo **mirrors how deployed wallets work**, not the W3C Verifiable Credentials model. See **Security** below.
- **W3C alignment** *(superseded 2026-10-03 by "Mirror deployed wallets" under **Security**; it still describes the credentials until Loop 8 (#139) moves them to IETF SD-JWT VC, and the claim-naming rules below carry over)*: The target was the **VC Data Model 2.0**, secured as a JWT per the W3C **VC-JOSE-COSE** spec (not the superseded 1.1 approach, which nested the credential in a `vc` claim and used `issuanceDate`). Building a *subset* of the standard is expected; taking an approach *contrary* to it is not. Concretely: claims are named, camelCase `credentialSubject` properties rather than generic `{kind, value}` wrappers; a credential's class goes in its `type` array; structured values use an established vocabulary type (e.g. schema.org `MonetaryAmount`) rather than an invented one; and standard fields such as `validFrom` are used instead of custom equivalents.
- **Users:** No passwords. You pick from fake personas. This is the **kiosk premise** (see **Security**).
- **The credential model lives in [docs/credential-model.md](credential-model.md)** — the target flow, issuers and trust, claim schemas, W3C conformance, and validity and failure. Each section ends with the decisions made when it was reviewed.
- **Benefit programs and eligibility rules live in [docs/benefit-programs.md](benefit-programs.md)** — five programs, the FPL/SMI/county-AMI variables, and the Dividend calculation. Food, Energy and Housing are pass/fail on an annual income test; Health and Dividend calculate a result on a sliding scale — a discount on a $750/month plan and a monthly payment respectively — tapered so that earning more never leaves someone worse off.
- **The Benefits app holds no public-user accounts.** There is no applicant-facing portal; the user's own record of applying lives in the Wallet's Activity log, making the Wallet the system of record for the user. Benefits does retain a **determination record** — the submitted data, the presented credentials kept **verbatim** so the decision can be re-verified later (*amended 2026-10-04, Loop 7, #132:* only for a **decided** application, whose credentials all verified; a refused one keeps only the reason code and each credential's type, digest and verification result, never claims that didn't verify, and the number of records is capped), the derived figures used, and the decision — surfaced by an **admin view** (docs/design.md §8, Loop 6, #111): an applications list grouped by person, and a determination page showing every presented credential's own verification result (photo redacted), the submitted data, and the per-program figures and outcome. No sign-in, like the rest of the demo — it is a demo admin view, not a real caseworker tool, and its content is plainly labelled as such.

## Security

Decided 2026-10-03/04 while planning Loop 7, after a security assessment of the Loop 6 build
and an independent review of it. `docs/security.md` (#138) will hold the threat model; this
section holds the decisions it rests on.

- **The kiosk premise: no authentication, on purpose.** Anyone can act as any person in any
  app's screens, like a public terminal, so that anyone can explore the demo without signing in.
  The screens are therefore not the security boundary. What *is* held to a real standard:
  credentials work only for their holder (from Loop 8), presentations only for the verifier and
  request they were made for, verifiers keep only what they need, and nothing replayable leaks
  from public pages or APIs. Protections that only matter once a session carries authority
  (cross-site form posts, clickjacking) are not findings under this premise.
- **No one-click persona sign-in** (Ed asked, 2026-10-03). A switcher that submits stored
  credentials publishes the secret, so it authenticates no one, and an assessor would rate it as
  no authentication while it suggests protection that isn't there. Revisit only as realism
  inside OpenID4VCI's authorization-code flow (a Payroll sign-in labelled **simulated**, #142).
- **Mirror deployed wallets; OpenID4VC HAIP 1.0 is the yardstick** (Ed, 2026-10-03). The goal
  is whatever a security assessor would find most trustworthy, provided the user scenarios still
  work. The rule is **HAIP where we can, and every deviation written down with its reason**, in
  `docs/security.md`, the same discipline the W3C rule had. Concretely:
  - **IETF SD-JWT VC** (`dc+sd-jwt`) for all three credentials, identity included (Loop 8,
    #139). OpenID4VP 1.0 and HAIP carry it; neither carries W3C VCs secured with SD-JWT.
    Identity as SD-JWT VC rather than ISO mdoc is a **declared deviation from US mDL
    practice** (the EU defines both encodings): one format, one verification path, readable
    JSON on screen.
  - **Holder binding** with the holder's key in `cnf` and a **Key Binding JWT** carrying the
    verifier's nonce and audience (#25, rewritten), not `did:key` subject ids. Holder keys live
    in the hosted Wallet, derived per person from one `sync: false` secret. Binding does **not**
    stop anyone acting as a person through the screens (the kiosk). What it buys is that copied
    credentials and captured presentations become useless.
  - **Requests name the claims they need**, and the consent screen shows them (#28, rewritten).
    This will reverse Loop 4's "credential types only" rule (credential-model §3, decision 1).
- **Cut, and listed as declared deviations:** encrypted responses (`direct_post.jwt`), signed
  requests (JAR with `x509_hash`) and X.509 `x5c` issuer chains (Ed, 2026-10-04). The Wallet
  calls each verifier server to server over TLS, at an origin pinned in its registry, so these
  would add little beyond conformance. Also declared: a hosted web wallet with server-held keys
  (so no honest key or wallet attestation), no Digital Credentials API, a hand-kept trust list,
  and in-memory state.
- **Benefits receives the full identity** (Ed, 2026-10-03): name, address and date of birth,
  even though no eligibility rule uses them, because an application legitimately requires them.
  Minimisation is judged against a stated purpose, so each claim's purpose is written down in
  `docs/security.md`. **Open:** whether the portrait is part of that set.
- **Income completeness is not solved** (Ed, 2026-10-04). Someone calling the API directly could
  leave out an employer's paystubs, and no verifier can tell. In the real world the control is
  the applicant's **attestation** that what they submit is complete. Recorded as a residual risk,
  not built.
- **Also residual, not built:** correlation across verifiers (one subject id everywhere; the
  real fix is pairwise ids or batch issuance), visitors sharing each other's state (isolating
  them would mean a sandbox id through all three protocols), and rate limiting.

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
- **Loop 4a — UX improvements:** an unplanned loop between 4 and 5 (#69, Intent 004a): a
  Wallet landing page with sign in/out, compact page headers, step-naming titles, a reworked
  consent page, and Payroll's paystub table scrolling on mobile. Presentation only: no
  protocol, credential or state changes.
- **Loop 5 — Payroll issues credentials:** Payroll turns paystubs into credentials; the Wallet
  requests and displays them. Payroll acts as an *issuer* here.
- **Loop 6 — Benefits programs and eligibility:** Benefits publishes its five programs, then
  verifies credentials and makes an eligibility decision. **Only the program pages are defined
  so far, by choice.** Benefits introduces no role that Loops 4 and 5 don't already build
  (verifier, then issuer), so its detailed decisions can wait — provided Loop 1 records the
  claims an eligibility check will need.
- **Loop 7 — Security hardening** (milestone, #131–#138): close the exposure the assessment
  found without changing the credential format. No replayable credentials on public pages,
  Benefits keeps only verified data, API limits, checks on what the Wallet receives and on
  consent, browser and CI hardening, and `docs/security.md`. First because it's cheap and
  independent of the format change.
- **Loop 8 — Holder binding and selective disclosure** (milestone): SD-JWT VC (#139), binding
  identity credentials to their holder (#140, settled first in that loop's design), holder
  binding (#25) and claim-level requests with a new consent screen (#28).
- **Loop 9 — optional, not a milestone:** revocation through a status list (#141), then
  OpenID4VCI issuance (#142), both labelled `deferred`.
- **Design stage uses Claude Design** for experience design (a shared design system plus
  screens, as plain HTML/CSS), handed off to Claude Code and versioned in `docs/design/loop-N/`.
  **The handoff is file-based in both directions**: `cred.css` and the current pages are handed
  to Claude Design at the start of a loop, and what comes back is committed under
  `docs/design/loop-N/`. Claude Code's `/design-sync` does **not** apply here — it converts a
  built JavaScript component library (an npm package, its `dist/` bundled into React components
  with `.d.ts` prop contracts) into a claude.ai/design project, and this repo has no package,
  no build and no JavaScript. Checked on 2026-09-21; revisit only if that ever changes.
- **Each loop's technical design is archived when it is superseded.** `docs/design.md` is always
  the *current* loop's technical design; when the next loop's replaces it, the outgoing one moves
  to `docs/design/loop-N/design.md`, beside that loop's handoff. A loop's design record then sits
  in one directory — what Claude Design handed over, and what Claude Code built to — and
  `docs/design.md` stays a stable path that always means "the design in force". The move is
  otherwise verbatim — only the archived file's relative links are repointed, since it drops two
  directories down. Established 2026-09-21, when Loop 2's design replaced Loop 0's.

## Technical defaults
- Python 3.12 (installed with **uv**; leave macOS's built-in Python 3.9.6 alone) + FastAPI, with HTML templates so Ed's HTML/CSS skills carry over
- One public monorepo on GitHub (`credentials-demo`) with `apps/wallet`, `apps/payroll`, `apps/benefits`
- Wallet is a web app, not native mobile
- pytest for tests; GitHub Actions for CI; branch protection on `main`
- **Hosting:** Render via a `render.yaml` Blueprint (free plan, `rootDir` and `buildFilter` per app, `autoDeployTrigger: checksPass`). GCP Cloud Run still makes sense eventually, but there is **no move planned and no urgency** — revisit only if Render blocks something the demo needs.
- **Sample data:** one generated set (people, employers, paystubs), then copied per app — each app keeps only the slice it needs. No shared data store or package, per the monorepo constraint. Some duplication across apps is expected.
- **Runtime state is in memory, per app, and volatile** (#27, decided in Intent 004 on
  2026-09-22). There is no database and nothing written to disk: Render's free tier has no
  persistent disk, so a file would buy nothing. Each app runs a single worker, so one set of
  in-memory dictionaries serves every request. Any app restarting, whether from idle spin-down
  or a redeploy, forgets what it stored. Because the apps idle independently, one can remember a
  connection the other has lost; that is a named demo limitation, and nothing on screen
  explains it. Real persistence (Render's free Postgres) remains a later option, not a plan.
- **No per-person demo reset** (Ed, 2026-09-22, closing #27's other half). Restarts already are
  the reset. Within a session, removing a provider in the Wallet returns that person to the
  start, and reconnecting overwrites Payroll's record. Worth rechecking at Loop 6, where holding
  benefit credentials is the first state change with no in-app way back.
- **The Wallet remembers the last person viewed in one cookie,** `wallet_person` (Ed,
  2026-09-24, docs/design.md §12.1), so a browser arriving from Benefit Agency's **Apply with
  Digital Wallet** lands on that person's consent page. It is navigation, not authentication,
  exactly like **Sign in**: it holds a person id and nothing else, and **Sign out** (`/sign-out`)
  clears it. This amends Loop 4a's "signing out clears nothing" (design/loop-4a/design.md §3);
  runtime state is still never cleared by signing out.
- **JavaScript is allowed sparingly** (Ed, 2026-09-22, amending "no JavaScript"; extended
  2026-09-23 to the Credentials page): only where a no-JS option is insufficient, as
  progressive enhancement over a page that already works without it. No framework, no library,
  no bundler. It started on the Wallet's pending pages (docs/design/loop-4/README.md §6), where
  a `<meta refresh>` would fail WCAG (F41) and holding the POST open would show nothing but the
  browser's spinner. The Credentials page (docs/design.md §9) is the second use: polling for
  income credentials that arrive after the page loads, in place with no page reload, and
  announced through a live region rather than only redrawing silently.
- **Payroll's issuer id is its deployed origin,** `https://cred-demo-payroll.onrender.com`, not a
  `did:example:` placeholder like the four states (Ed, 2026-09-23, docs/design.md §3 and §13 item
  1). The states' `did:example:` ids stand for real government issuers that don't expose a
  service of their own; Payroll's fictional company does, so its issuer id names it directly, per
  credential-model §2's rule that an issuer id should resolve to something. The id is a constant
  in `apps/payroll/app/data/issuer.json`, not derived from the incoming request, so a local
  Payroll signs with the same issuer id a deployed one does.
- **A credential's display color is a demo-only render hint,** `CredDemoCardColor` (Ed,
  2026-09-23, docs/design.md §4 and §13 item 5; renamed from `CredDemoIssuerColor` in Loop 6
  §5, since one issuer — Benefit Agency — now signs five colors): one `oklch()` color on VC 2.0's
  standard `renderMethod` property. The Wallet reads only the hue; lightness and chroma stay
  fixed in its own `cred.css`, so a signed color hint can't make a card illegible.
- **One-shot generators are allowed; sync scripts are not.** A script under `tools/` may generate files into several apps' directories — the sample data (#6), and the keys, trust lists and signed identity credentials (docs/credential-model.md §2) — provided it is run by hand, its output is committed, and nothing runs it at build or deploy time. What stays ruled out is a script that *keeps* copies aligned on an ongoing basis. (The "no sync script" rule originated in a proposal to sync `cred.css` across apps, which was rejected as unnecessary; each app still owns its own `cred.css`.)
