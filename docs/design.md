# Design: Loop 6 — Benefits programs and eligibility

This is the technical design for [Intent 006](intents/006-benefits-programs-and-eligibility.md).
It covers the nine issues in the Loop 6 milestone:
[#20](https://github.com/edmullen/credentials-demo/issues/20) and
[#104](https://github.com/edmullen/credentials-demo/issues/104)–[#111](https://github.com/edmullen/credentials-demo/issues/111).
It follows [decisions.md](decisions.md), the [credential model](credential-model.md),
[benefit-programs.md](benefit-programs.md), the oracle in
[sample-data.md](sample-data.md#expected-outcomes), and the Claude Design handoff in
[design/loop-6/](design/loop-6/README.md).

Loop 5's design is archived at [design/loop-5/design.md](design/loop-5/design.md).

## 1. Overview

Benefit Agency goes from Loop 0's placeholder to a verifier and an issuer, and the Wallet gets a
reason to hold everything it has collected:

- **Benefit Agency publishes five programs** (#20): a landing page and one page per program.
- **It decides** (#104, #105). It asks for the identity credential and every income credential,
  verifies them, decides all five programs in one pass, and keeps a determination record.
- **It issues** (#106) one `BenefitCredential` per eligible program, through the same call 3
  that Payroll answers.
- **The Wallet applies** (#107) from **Find government services**, and shows a results screen
  that leads with what the person got.
- **The Wallet shows benefit credentials** (#109), each in its program's color.
- **There's a second way in** (#108): **Apply with Digital Wallet** on a program page.
- **An admin view** (#111) lays out every application and how it was decided.
- **The render hint is renamed** (#110), from `CredDemoIssuerColor` to `CredDemoCardColor`.

What changes, by app:

| Where | Changes | Issues |
|---|---|---|
| `tools/generate_credentials.py` | Adds Benefits' key, `issuer.json` and `.env`; Benefits' trust list; the Wallet trusts Benefits; everything re-keyed (§3) | #105 |
| `apps/benefits` | Everything: key and self-check, JWKS, engine, request/presentation/credentials API, state, program pages, `/apply`, admin (§3–§8) | #20, #104–#106, #108, #111 |
| `apps/wallet` | A service in its registry, the apply flow, multi-credential consent, results, benefit cards and detail, arrival from Benefits, a remembered person, the renamed hint (§9–§12) | #107–#110 |
| `apps/payroll` | The renamed hint only, plus its re-keyed key (§5) | #110 |
| `render.yaml`, `.claude/launch.json`, `CLAUDE.md` | `BENEFITS_SIGNING_KEY`; local URLs and `--env-file` for Benefits (§3) | #105 |
| Docs | decisions.md, credential-model.md §1, §3, §4 (§16) | several |

## 2. The protocol

The same REST stand-ins as Loops 4 and 5 (credential-model §4): a DCQL-shaped request, an
enveloped-VC presentation, and "give me the credentials I haven't received". Benefit Agency adds
two things Payroll doesn't have: a request that can be fetched **by reference**, and a reply that
carries **five outcomes**.

### Call 1: ask for the request

```
POST {benefits}/api/applications/requests
{}
```

**201:**

```json
{
  "requestId": "9b2e…",
  "dcql_query": {
    "credentials": [
      { "id": "identity", "format": "vc+jwt",
        "meta": { "type_values": [["IdentityCredential"]] } },
      { "id": "income", "format": "vc+jwt", "multiple": true,
        "meta": { "type_values": [["PaystubCredential"]] } }
    ]
  },
  "response_uri": "/api/applications/requests/9b2e…/presentation"
}
```

- **Credential types only**, no claims list, as Payroll's request (credential-model §3,
  decision 1).
- **`multiple: true`** is DCQL's own flag for "every matching credential, not one". This settles
  the intent's open question with the real OpenID4VP term, so a later move to OpenID4VP stays a
  translation.
- **`response_uri` is a path**, which the Wallet resolves onto the origin it already holds, as
  for Payroll (CLAUDE.md, "Things that look like mistakes").
- A pending request lives 15 minutes and answers **one** presentation, as Payroll's does.

### Request by reference (the redirect entry)

```
GET {benefits}/api/applications/requests/{requestId}
```

- **200:** the same body as call 1. **404** `{"error": "unknown_request"}`: expired, already
  answered, or never made.
- It's OpenID4VP's `request_uri` pattern. The browser carries only a request id to the Wallet,
  never the request itself or anything personal (§12).
- It can be fetched any number of times until a presentation answers the request. So "Not you?
  Switch person" (§12) can reuse it.

### Call 2: the presentation

```
POST {benefits}/api/applications/requests/{requestId}/presentation
<a VerifiablePresentation: the identity credential, then every income credential, each an
 EnvelopedVerifiableCredential — credential-model §4>
```

**200, decided:**

```json
{
  "outcome": "decided",
  "connectionId": "c41f…",
  "applicationId": "a7d0…",
  "decidedAt": "2026-10-01T14:03:00Z",
  "programs": [
    { "program": "food",     "outcome": "eligible", "credentialId": "urn:uuid:…" },
    { "program": "energy",   "outcome": "denied", "reason": "income_over_limit" },
    { "program": "housing",  "outcome": "denied", "reason": "income_over_limit" },
    { "program": "health",   "outcome": "eligible", "credentialId": "urn:uuid:…",
      "discountPercent": 85.4, "planCost": { "type": "MonetaryAmount", "value": 750.0, "currency": "USD" } },
    { "program": "dividend", "outcome": "eligible", "credentialId": "urn:uuid:…",
      "monthlyPayment": { "type": "MonetaryAmount", "value": 100.0, "currency": "USD" } }
  ]
}
```

- **Always five entries**, in program order: food, energy, housing, health, dividend.
- **`reason`** is `income_over_limit` or `not_nj_resident` (credential-model §5). An
  out-of-state person gets five `not_nj_resident` denials.
- **An eligible entry repeats its credential's figures and id.** The results screen can then say
  what the person got before the credentials themselves arrive, and knows which ones are still
  on the way (§10.7). The figures are protocol data, as the intent says. The credential is what
  the person holds.
- **`connectionId`** is issued on every decided application, including all-denied ones: Benefit
  Agency is a connection either way (§6).

**200, refused:** `{"outcome": "refused", "reason": "credential_invalid" | "subjects_differ"}`.
No connection is made and nothing is decided.

**400** `{"error": "invalid_presentation"}`: the wrong shape. That means not a VP, or not exactly
one `IdentityCredential` plus at least one `PaystubCredential`. **404** `{"error":
"unknown_request"}`.

### Call 3: fetch credentials

Exactly Payroll's (Loop 5 design §2):
`POST {benefits}/api/credentials {"connectionId", "have"}`. **200**
`{"credentials": [<jwt>, …]}` returns that connection's benefit credentials not in `have`, in
program order. **404** `unknown_connection`, **400** `invalid_request`, **503** without a valid
key. So the Wallet's `fetch()` works for Benefit Agency with no protocol change.

### Timing

The Wallet's `outbound.post_json` (one attempt, 60 seconds, no retry, honest user agent) serves
every call, with a `get_json` beside it for the request by reference. A cold Benefit Agency
refuses in about 2 seconds (Loop 4's Render finding). That lands as "Couldn't reach Benefit
Agency" (§10.6), and **Try again** works once it's awake. **Benefit Agency makes no outbound
calls at all.** The redirect is the browser's job.

## 3. Keys, trust and configuration

### Generator

`tools/generate_credentials.py` gains Benefit Agency, following the pattern Payroll set in Loop 5:

- **A new ES256 key pair**, `kid` `benefits-1`. It goes to `keys/benefits-1.jwk.json`
  (gitignored), and to `apps/benefits/.env` as `BENEFITS_SIGNING_KEY=<jwk>` on one line.
- **`apps/benefits/app/data/issuer.json`** (committed): id `https://cred-demo-benefits.onrender.com`,
  name **Benefit Agency**, `kid`, public JWK. The id is Benefits' origin (credential-model §2),
  not the handoff's placeholder `did:example:benefit-agency` (§16 item 1).
- **`apps/benefits/app/data/trust.json`** (new): the four states for `IdentityCredential`, and
  Meridian Payroll for `PaystubCredential`.
- **The Wallet's `trust.json`** gains Benefit Agency, for `BenefitCredential` only.
- **Everything is re-keyed.** Each run replaces every key, so Payroll's key changes too, and every
  identity credential is re-signed (with the same ids).
- **It no longer prints private keys.** Loop 5's run printed `PAYROLL_SIGNING_KEY=…` to the
  terminal for pasting. After PR 1's leak (loop-log.md, Loop 5), the script instead prints where
  each `.env` was written. Ed copies the values from those gitignored files, and Claude hands
  them over in chat if asked, never on GitHub.

### Benefits' signing: `app/signing.py`

A copy of Payroll's (Loop 5 design §3) with `BENEFITS_SIGNING_KEY`. It does the startup
self-check against `issuer.json`. `/health` returns 200, or 503 with "BENEFITS_SIGNING_KEY is not
set" / "…does not match the committed public key". `/.well-known/jwks.json` serves the public
key. Without a valid key, pages still render, and call 2 and call 3 return 503.

### Configuration

| Where | What |
|---|---|
| `render.yaml` | `cred-demo-benefits` gains `BENEFITS_SIGNING_KEY` (`sync: false`). **Ed sets it, and Payroll's new key, before PR 2 merges.** |
| `apps/benefits/.env.example` | Names `BENEFITS_SIGNING_KEY`. `.env` is already gitignored. |
| Benefits `WALLET_URL` | Where **Apply with Digital Wallet** sends the browser (§7.3). Default `https://cred-demo-wallet.onrender.com`, read in one place, like the Wallet's `MERIDIAN_PAYROLL_URL`. |
| Wallet `BENEFIT_AGENCY_URL` | Overrides Benefit Agency's URL in the Wallet's registry (§9.1) for local runs. |
| `.claude/launch.json` | `wallet` gains `BENEFIT_AGENCY_URL=http://localhost:8003`. `benefits` gains `WALLET_URL=http://localhost:8001` and `--env-file .env`. |
| `CLAUDE.md` | Benefits' local-run command gains `--env-file .env`, with the same "run the generator first" note as Payroll. |

Tests never use a real key. A fixture makes a throwaway pair and patches `issuer.json`, as in
Payroll.

**New Benefits dependencies:** `pyjwt[crypto]>=2.9`, `cryptography<49` (Intel-Mac wheel cap) and
`tzdata`, all of which Payroll already uses. Benefits has no forms, so no `python-multipart`.

## 4. The eligibility engine (#104)

`app/eligibility.py`: plain functions, no I/O. This is the tested core that §6 and §8 build on.

- **Input:** `region`, `county`, and the list of gross pay amounts (`Decimal`). **Output:** a
  `Determination` with `monthly`, `annual`, and one `ProgramResult` per program. Each result
  holds `outcome`, `reason`, and the figures used: the limit or bounds compared against, and the
  discount or payment.
- **Rules and variables** are those of benefit-programs.md, held as data in
  `app/data/rules.json`: FPL 15,960; SMI 50,000; the 21 county AMIs; Health 750, 138%, 500%;
  Dividend 100, 300, 1,200; and "as of September 2026". The program pages (§7) render their
  limits from the same file, so page and decision can't disagree.
- **Arithmetic is `Decimal`,** mirroring `tools/generate_sample_data.py` exactly, because that's
  what produced the oracle:
  - `monthly` = sum of gross pay; `annual` = `monthly` × 12.
  - **Not NJ** (`region != "NJ"`): every program is `denied`, `not_nj_resident`, and nothing is
    evaluated for income.
  - **Food** eligible if `annual` ≤ 1.85 × FPL. **Energy** if `annual` ≤ 0.60 × SMI. **Housing**
    if `annual` ≤ 0.30 × county AMI. Otherwise `denied`, `income_over_limit`. All three are
    "at or below".
  - **Health** is always eligible. Its discount is 1 at or below 138% FPL, 0 at or above 500%, and
    linear between. **`discountPercent`** = `discount × 100` quantized to 0.01 half-up, then to 0.1
    **half-even**. That's exactly what the generator does when it prints the oracle
    (`cents(…)` then `:.1f`), so the engine can't land a tenth off (Intent 006).
  - **Dividend** is always eligible: `100 + max(0, 300 − 0.25 × monthly)`, quantized to cents
    half-up once, at the end.
- **The oracle is copied into the tests** (`tests/oracle.json`, since tests can't read `docs/`).
  All 18 decided rows and the 3 out-of-state rows must match: monthly, annual, Health percent,
  Food, Energy, Housing and Dividend.

## 5. The benefit credential (#106) and the renamed hint (#110)

`app/issuance.py` builds one credential per eligible program, when the determination is made
(§6):

```json
{
  "@context": ["https://www.w3.org/ns/credentials/v2"],
  "id": "urn:uuid:<uuid4>",
  "type": ["VerifiableCredential", "BenefitCredential"],
  "issuer": { "id": "https://cred-demo-benefits.onrender.com", "name": "Benefit Agency" },
  "validFrom": "2026-10-01T14:03:00Z",
  "validUntil": "2027-10-01T14:03:00Z",
  "credentialSubject": {
    "id": "<the subject id from the presented identity credential>",
    "program": "health",
    "discountPercent": 92.4,
    "planCost": { "type": "MonetaryAmount", "value": 750.0, "currency": "USD" }
  },
  "renderMethod": [{ "type": "CredDemoCardColor", "color": "oklch(0.46 0.11 223)" }]
}
```

- **Claims** follow credential-model §3. Food, Energy and Housing carry `program` alone. Dividend
  adds `monthlyPayment`, and Health adds `discountPercent` (one decimal, a JSON number) and
  `planCost`. There's no `decision` claim, no name and no address.
- **`id`** is a random `urn:uuid:`, created once with the determination and stored with it. So
  call 3 returns the same id every time, and `have` works.
- **`validFrom`** is the determination time, **floored to the whole minute**.
  **`validUntil`** is 12 months later (29 February becomes 28 February). Flooring gives up to a
  minute of margin against the Wallet's clock being a little behind Benefits'. Otherwise a
  credential seconds old could show as "Not yet valid", which is Loop 5's hue-bug lesson about
  moving clocks (§16 item 3).
- **Signing:** the credential is signed once, when the determination is made, and the JWT is
  stored. Payroll re-signs on every request because it stores nothing. Benefits keeps the record
  anyway, and a stable JWT is what the admin view shows as issued. Header: `ES256`, `benefits-1`,
  `vc+jwt`.
- **Program hues:** food 169, energy 24, housing 342, health 223, dividend 121, signed on the
  Wallet's recipe `oklch(0.46 0.11 H)`. They're held in Benefits' `app/data/programs.json` with
  each program's code, name, landing phrase and order.

### The rename (#110)

`CredDemoIssuerColor` becomes **`CredDemoCardColor`**, since one issuer now signs five colors.

- **Payroll** signs the new type with its unchanged color, `oklch(0.46 0.11 255)`.
- **The Wallet** reads only `CredDemoCardColor`. There's no fallback to the old name: Payroll
  signs on demand, and the Wallet's state resets on every redeploy, so no credential with the old
  name survives.
- **The CSS keeps its names** (`cred--issuer`, `--issuer-hue`), as the handoff does (README
  Part B §1). The rename is a data change, not a stylesheet change.
- decisions.md's render-hint entry and credential-model §4's "Display rendering" row are
  updated. Archived design records keep the old name.

## 6. Benefits' state and verification (#105)

### State: `app/applications.py`

In memory, per process, volatile (decisions.md). Everything is lost when Benefits restarts,
which the intent accepts.

- **`_pending: dict[request_id, PendingRequest]`** holds `created_at`, with a 15-minute TTL and
  pruning, as Payroll's.
- **`_applications: list[Application]`**, newest last. Each `Application` holds:
  - `id` (`uuid4().hex`) and `received_at`
  - `subject_id` and `name`: "Given Family" from the identity credential, read even if it failed
    verification, so the admin view can list it
  - `presented`: a list of `(token, kind, outcome)`, **the JWTs verbatim**, each with its own
    verification result
  - `same_subject`: a bool, or None if not reached
  - `outcome`: `decided` or `refused`
  - `reason`: for a refusal
  - `facts`: region, county, and each paystub's employer, pay date and gross pay
  - `determination`: §4's, for a decided application
  - `issued`: program code → `(credential id, JWT)`
- **`_connections: dict[subject_id, Connection]`** and `_by_connection_id: dict[str, subject_id]`,
  as Payroll's. A `Connection` points at its application. **Applying again replaces the
  connection:** a new id, and the old one returns 404. Only all-denied people can re-apply in
  practice (§10.1).

### Verifying a presentation: `app/presentation.py`

A copy of Payroll's shape (`_tokens_from`, the envelope prefix), with Benefits' own `verify.py`,
a copy of the four checks. Then:

1. **Shape:** exactly one `IdentityCredential` and at least one `PaystubCredential`, judged by
   each token's unverified `type`. Anything else is `invalid_presentation` (400), with nothing
   recorded.
2. **Checks 1–4** on every credential against Benefits' trust list. Any failure means
   **refused, `credential_invalid`**. The record keeps every credential's own result, so the
   admin view shows which one failed.
3. **Check 5, one subject:** every `credentialSubject.id` equal. Otherwise **refused,
   `subjects_differ`**.
4. **Decide:** §4's engine, from the identity credential's `address.addressRegion` and
   `address.county`, and every paystub's `grossPay.value`.
5. **Issue:** §5, for each eligible program. Record the application, make the connection, and
   reply (§2).

A refused application is recorded too, so the admin view can show it, but it gets no connection.

## 7. Benefit Agency's pages (#20)

Benefits' `cred.css` becomes the handoff's `benefits/cred.css`, byte for byte, pinned by length
and SHA-256 as the other apps' are. `base.html` takes the handoff's header, footer and fonts URL
(Libre Franklin 600; Public Sans 400/600/700):

- The five programs' links replace the placeholder nav, with `aria-current="page"` on the current
  program.
- `.header__admin` sits top right, and becomes the menu's last item (`.nav-menu__admin`) at 40rem
  and below. It carries `aria-current` on admin pages.
- The placeholder signed-in user ("Jordan Diaz") is removed.

### 7.1 Routes

| Route | Page | Handoff |
|---|---|---|
| `GET /` | Landing: five `.program-card`s in program order, each `data-program` | `landing.html` |
| `GET /programs/{code}` | A program page; 404 for an unknown code | `food.html`, `energy.html`, `housing.html`, `health.html`, `dividend.html` |
| `GET /apply` | Starts the redirect (§7.3) | — |
| `GET /admin`, `GET /admin/applications/{id}` | The admin view (§8) | `admin*.html`, `determination-*.html` |

### 7.2 Program pages

One template, `program.html`, with a partial per shape. The copy is the handoff's, verbatim.
Every figure is rendered from `rules.json` (§4), never typed into the template:

- **Food, Energy:** one annual limit, $29,526 and $30,000.
- **Housing:** "30% of your county's AMI", with the 21 county limits in the closed
  `.disclosure--boxed` table, in the handoff's order.
- **Health, Dividend:** the three `.facts` and the `.callout`. There are no tables (Ed,
  2026-09-24; #20 amended).
- **Every page:** the "as of September 2026" note, and the two `.apply` options. **Apply with
  Digital Wallet** is an `<a class="btn">` to `/apply`. **Apply here** is disabled, with its note
  tied by `aria-describedby`.

### 7.3 `GET /apply`

It creates a pending request, exactly as call 1 does, and answers **303** to
`{WALLET_URL}/requests/benefits/{requestId}`.

- It's a GET because the handoff's button is a link. A GET that creates a request is harmless:
  it holds nothing personal, expires in 15 minutes, and is pruned.
- Until PR 10 (§15), `/apply` redirects to the Wallet's landing page, so the button is never a
  dead link on the deployed site.

## 8. The admin view (#111)

No sign-in, like the rest of the demo. `<title>` and the heading say it's a demo admin view.

### 8.1 Applications list: `GET /admin`

The handoff's `.apps` table. People are grouped by `subject_id` and ordered by their newest
application, newest first. Within a person, applications are newest first too, and the name
shows on the first row only (`.apps__start`).

| Column | Content |
|---|---|
| Applicant | The name (first row of a group) |
| Received | `when()`: "1 Oct 2026, 2:03 PM", America/New_York, as Payroll's display |
| Result | "5 of 5 approved" · "2 of 5 approved" · "Not a New Jersey resident" · "Refused: credential couldn't be verified" · "Refused: credentials aren't about one person" |
| View | A 44px link with a visually hidden name and time |

With no applications: `admin-empty.html`'s `.empty` state, which explains quietly that records
are lost when Benefit Agency restarts.

### 8.2 Determination page: `GET /admin/applications/{id}`

The handoff's layout, rendered from the `Application` (§6). 404 for an unknown id.

- **`.meta`:** received, application id, subject id.
- **`.checks`:** a row per presented credential, with its type, issuer, verification result and a
  `.disclosure` holding the decoded header, the claims and the raw JWT. **`image` is truncated to
  "(photo, not shown)"** (handoff decision). Then the plain "Same person" row.
- **`.submitted`:** state and county, then the paystubs' `.figures` table with the monthly and
  × 12 totals.
- **`.decisions`:** a `.decision[data-program]` per program, with:
  - the **Figure** line, naming the limit
  - the **Result**
  - the decorative **`.scale`**, with `--zone-start`, `--zone-width` and `--dot` computed by the
    view model as percentages of a fixed axis. It's `aria-hidden`, since the text says the same.
  - **`.decision__foot`**, with the issued credential's id, or the reason code
- **Variants:**
  - **Not NJ:** the decisions say "Not evaluated: not a New Jersey resident" (`determination-p19.html`).
  - **Refused:** `.checks` shows the failing credential. There are no decisions, and a note says
    so (`determination-refused.html`).

## 9. The Wallet: registry and state

### 9.1 A service in the registry

`providers.json` gains Benefit Agency, and every entry gains a `kind`:

```json
"benefits": { "kind": "service", "name": "Benefit Agency",
              "url": "https://cred-demo-benefits.onrender.com", "employers": [] }
```

- Meridian becomes `"kind": "payroll"`. `all_providers()` still returns both, so `fetch()`,
  `maybe_start_check()` and `check_status()` already loop over Benefit Agency once it's connected.
- Employer lookup filters on `kind == "payroll"`, and the services directory on
  `kind == "service"`.
- `BENEFIT_AGENCY_URL` overrides the URL, beside `MERIDIAN_PAYROLL_URL`.

**Program display data** lives in the Wallet's own `programs.json`:

| Code | Name |
|---|---|
| `food` | Food Assistance |
| `energy` | Energy Assistance |
| `housing` | Housing Assistance |
| `health` | Health |
| `dividend` | Dividend |

Each entry also holds the program's order. The Wallet's copy is kept separate from Benefits' by
the monorepo rule, and a test in each app pins the names.

### 9.2 State

`app/state.py` gains:

- **On `Link`:**
  - `determination: Determination | None`: the call 2 reply (application id, `decidedAt`, the five
    program outcomes), kept for the results and already-applied pages
  - `refusal: str | None`
  - `presentation: dict | None`: the approved VP, kept only until call 2 answers, for **Try
    again** (§10.6)
- **`PendingRequest.phase`** gains `"applying"` (Benefits' verifying) and `"arrived"` (fetched by
  reference, §12). `PendingRequest` gains `missing: str | None` (`"identity"` or `"income"`) and
  `arrived: bool`.

There's no server state for "who is signed in": the remembered person is a cookie (§12.1).

A Benefit Agency `Link` has no employers. It exists from the first **Apply** until Remove, or
until a `lost` fetch (§10.8).

## 10. The Wallet applies (#107)

### 10.1 Find government services

On the Credentials page, between Identity and Income:

- **The `.services-entry`** link to `/p/{id}/services`, when the person **holds no benefit
  credential**. "Holds" counts every received `BenefitCredential`, whatever its verification
  outcome (§13, table A). A tampered one is still held, and re-applying is not a way to replace
  it.
- **The Benefits category** (§11.1) otherwise, in the same place.
- The entry gets **`id="benefits"`**, the same id as the category. The handoff's script redraws
  `#income` only. The built script redraws **both** `#income` and `#benefits`, so benefit
  credentials that arrive in a background check replace the entry in place (§16 item 6).

### 10.2 Government services: `GET /p/{id}/services`

`services.html`: page head "‹ Credentials | Government services", with one `.people` row per
service. The row links to `/p/{id}/services/benefits/apply`.

### 10.3 The apply attempt

It's Loop 4's attempt machinery (`attempt.py`): phases, a fresh token per attempt, the stale-answer
guard, `outbound.spawn`, and the polling pages. The routes live under
`/p/{id}/services/{service_id}/`, and `app/application.py` holds what's specific to Benefits.

| Route | Does |
|---|---|
| `GET …/apply` | If the person holds a benefit credential, redirect to `…/already`. If an attempt is running, redirect to where it is. Otherwise start one (phase `asking`) and redirect to `…/asking`. A GET, because the handoff's row is a link; the guard makes a repeat GET harmless, like the Credentials page's check. |
| `GET …/asking` | Loop 4a's `asking.html` with Benefit Agency's name, while call 1 runs. The handoff has no page for this; it reuses the existing component (§16 item 7). |
| `GET …/request` | Consent (phase `consent`) or can't-apply (phase `missing`) |
| `POST …/request` | `decision` = `approve`, `deny`, `close` or `retry` |
| `GET …/applying` | "Checking your eligibility…" while call 2 and the fetch run |
| `GET …/error` | Couldn't reach Benefit Agency |
| `GET …/results` | The results screen |
| `GET …/already` | Already applied |
| `GET …/status?page=` | The poller's endpoint, as Loop 4's |

**Call 1** (`asking`): `POST /api/applications/requests`. Then:

- `response_uri` is resolved onto Benefits' origin, or the attempt ends as `no_response`.
- A credential is **missing** when a DCQL entry has no held credential of its type: none for a
  single entry, zero for a `multiple` one.
- **Identity leads:** p24 has neither, and gets the identity page (handoff Part B §5).
- Missing → phase `missing`, `missing` set, and Activity logs it (§10.9). Otherwise → `consent`.

**Deny** ends the attempt and logs "Request from Benefit Agency denied. Nothing was shared." as
Loop 4 does. **Close** on a can't-apply page ends it silently.

### 10.4 Consent: `request.html` for a service

The handoff's `consent-p01.html` / `consent-p08.html`:

- Page head "‹ Government services | Request from Benefit Agency" ("‹ Credentials" when
  arrived, §12). The heading: "Do you want to share N credentials with Benefit Agency?"
- **Approve and share / Deny** come first. With more than three credentials, they're repeated
  after the list, with the handoff's lines.
- **Identity:** Loop 4a's panel, unchanged, marked "1 of N".
- **Income:** one panel **per issuer**, marked "2–N of N". It has:
  - the issuer bar, in that issuer's hue
  - the status area ("6 paystubs · September 2026", **All verified** or the worst badge present)
  - `.shares`, one `<details class="share">` per credential, newest first, holding every claim and
    the credential id

  "September 2026" is the month (or "Aug–Sep 2026" span) of the held pay dates. A tampered
  paystub is still offered, whatever its badge, as Loop 4 decided. Benefit Agency then refuses.
- **Approve** builds the VP (identity, then income in held order), keeps it on the link, logs
  "Application sent to Benefit Agency: identity credential and N income credentials shared", sets
  phase `applying` and spawns call 2.

### 10.5 Can't apply

`cant-apply-income.html` and `cant-apply-identity.html`, rendered by `GET …/request` in phase
`missing`:

- **Income:** "Connect your payroll provider first". **Find your employer** goes to
  `/p/{id}/connections/employers`.
- **Identity:** "You need an identity credential first". **Switch person** goes to the switcher.
- The `.needs` rows come from what's held: **In your wallet** with its badge, or **None yet** /
  **None**.

### 10.6 Applying and its failures

- **`applying.html`** (`checking.html`): Loop 4's `.pending` with its polling script and **Check
  again**. The script is the same code as `verifying.html`'s.
- **Call 2** posts the VP to the resolved `response_uri`. Then, by answer:
  - **`decided`:** store `determination`, set `connected_at` and `connection_id`, clear
    `presentation`, and log it (§10.9). Then **await `fetch()`** before ending the attempt, as
    Payroll's connect does (Loop 5 design §9). The applying page is still polling, so the
    credentials are usually in hand when the results page renders.
  - **`refused`:** store `refusal`, clear `presentation`, and log it. No connection.
  - **Anything else** (timeout, refusal to connect, 5xx, bad JSON, 404 `unknown_request`): end as
    `no_response`, **keeping `presentation`**, and log "Couldn't reach Benefit Agency to send your
    application" (`caution`).
- **`error.html`** (`checking-error.html`): "Couldn't reach Benefit Agency", with **Try again**
  (`decision=retry`) and **Back to credentials**. What **Try again** does:
  - With a kept `presentation` and the request not yet answered, it re-posts the same approved
    VP (phase `applying`). The person approved exactly this.
  - If that answer is 404 `unknown_request` (Benefits restarted, or 15 minutes passed), or if
    nothing was approved yet (call 1 failed), it starts over at call 1, and the person consents
    again.

  A call 1 failure lands on the same page, since nothing was shared either way.

### 10.7 Results: `GET …/results`

Rendered from `link.determination` (or `link.refusal`) and the benefit credentials held. With
neither, it redirects to the Credentials page. The order is the handoff's (README Part B §7):

1. **The verdict** (`.verdict`) is an `<h2>` plus one sentence, composed by the Wallet from the
   outcomes:

   | Case | Heading | Sentence |
   |---|---|---|
   | 5 of 5 | "You qualify for all 5 programs" | Pass/fail names, the Dividend payment, and Health's discount and price. For 100%: "free". |
   | 1–4 of 5 | "You qualify for N programs" (1: "1 program") | Only what they got |
   | Health 0% | as above | Health's sentence becomes "Health gives no discount at your income: you may buy the Public Option plan at its full price, $750.00 a month." |
   | 0 of 5 (`not_nj_resident`) | "You don't qualify for any programs" | "Benefit Agency's programs are for New Jersey residents, and your identity credential gives your address in {state}." `{state}` is from the Wallet's own identity credential. |

2. **Added to your wallet:** the eligible programs' cards in program order, full and flat
   (`.stack-cards--flat`), without **New**. A card is drawn when its `credentialId` is held. If
   any eligible id isn't held yet, the whole block is replaced by the handoff's **On the way to
   your wallet** state (spinner meta **Collecting**), and the Credentials page's background check
   brings them.
3. **Programs you don't qualify for:** `.outcomes`, one line per denial, with a grey marker. The
   heading is "Each program" when all five are denied. The line is "**{Name}:** your income is
   above this program's limit." or "…: this program is for New Jersey residents."
4. **Go to your credentials**, with "Benefit credentials are valid for 12 months, until {date}."
   On a 0-of-5 page it says instead: "Find government services stays on your Credentials page, so
   you can apply again."

**Refused:** "Your application couldn't be decided" and the error band (**Refused** ✕).

- **Which sentence:** the Wallet works out which kind failed from **its own** verification of what
  it shared. That's "One of your income credentials…" or "Your identity credential…"
  (credential-model §5), or "One of the credentials you shared couldn't be verified" when all of
  its own checks pass (a clock edge at Benefits). No protocol field is added.
- **`subjects_differ`** uses its credential-model sentence.

The visually hidden `role="status"` paragraph gives the verdict ("You qualify for 2 programs. Not
eligible for 3."). Focus stays at the top.

### 10.8 Fetching from Benefit Agency

`fetch()` is unchanged in protocol. Its wording is chosen by the provider's `kind`:

| | Payroll (as now) | Benefit Agency |
|---|---|---|
| Received | "N income credentials received from Meridian Payroll" | "N benefit credentials received from Benefit Agency" |
| Unverified | "N income credential(s) from … couldn't be verified" | "N benefit credential(s) from Benefit Agency couldn't be verified" |
| Unreachable | "Couldn't reach … to check for new credentials" | same |
| Announcement | "N new income credentials from …" | "N new benefit credentials from Benefit Agency." |

**`lost`** (Benefits restarted and forgot the connection) removes the Benefit Agency link
silently, keeping any credentials held. There's nothing to reconnect to: a person holding
credentials can't re-apply, and a person holding none gets Find government services back. If
Benefits restarted before the credentials were collected, they're lost with it. That's the
volatile-state limitation, accepted.

### 10.9 Connections and Activity

**Connections** (`connections-p07.html`):

- A Benefit Agency panel sits above Meridian Payroll (links newest first). It shows "Government
  service", **Connected** since the decision, and "Benefit Agency sent you N benefit credentials."
  (count of held benefit credentials; the line is left out at 0).
- **Remove** is a `.link-btn`, with "Removing Benefit Agency keeps your benefit credentials." tied
  by `aria-describedby`. It posts to the existing remove route, which logs "Benefit Agency
  removed" (`neutral`). Payroll's "…removed, with {employers}" needs employers, and a service has
  none.

**Activity:** each program gets its own entry, so a denial can be found afterwards
(`activity-p07.html`). Newest first:

| Event | Message | Dot |
|---|---|---|
| Can't apply (identity) | "Application to Benefit Agency not made: you don't have an identity credential to share." | `caution` |
| Can't apply (income) | "Application to Benefit Agency not made: you don't have income credentials to share." | `caution` |
| Denied consent | "Request from Benefit Agency denied. Nothing was shared." | `neutral` |
| Approved | "Application sent to Benefit Agency: identity credential and N income credentials shared" | `neutral` |
| Decided | "New connection to Benefit Agency established" | `verified` |
| Each eligible program | "{Name}: eligible" · "Dividend: eligible, $100.00 a month" · "Health: eligible, 85.4% off: $109.50 a month" | `verified` |
| Health at 0% | "Health: full price, 0% off: $750.00 a month" | `neutral` |
| Each denial | "{Name}: not eligible. Your income is above this program's limit." / "…This program is for New Jersey residents." | `neutral` |
| Credentials arrive | §10.8 | `verified` |
| Refused | "Your application couldn't be decided: N credential(s) couldn't be verified" / "…the credentials you shared aren't all about the same person" | `error` |
| No answer | "Couldn't reach Benefit Agency to send your application" | `caution` |

The two "Can't apply" messages aren't in the handoff. They follow Loop 4's missing-credential
entry.

## 11. Benefit credentials in the Wallet (#109)

### 11.1 The Benefits category

`credentials-benefits.html` / `credentials-p09.html`: a `.category` with `id="benefits"` and a
stack, as Income, between Identity and Income:

- **Order:** program order (food, energy, housing, health, dividend), with the last drawn at the
  front. At most five exist, so there's no "View all" ledge.
- **Each ledge:** `.stack-cards__program` (the name, from `programs.json`) and
  `.stack-cards__figure`:

  | Program | Figure | Front card also shows |
  |---|---|---|
  | Food, Energy, Housing | "Eligible" | — |
  | Health, 0 < d | "{d}% off" | `.cred__figure-sub` "{price} a month" |
  | Health, d = 100 | "100% off" | "$0.00 a month" |
  | Health, d = 0 | "Full price" | "0% off: $750.00 a month" |
  | Dividend | "{payment} a month" | — |

  - **Percent formatting** drops a trailing ".0" ("80% off", "94.5% off").
  - **Money** is Loop 5's `money()`.
  - **The price** is `planCost × (100 − d) / 100`, quantized to cents half-up. The Wallet derives
    it from the signed percent (§16 item 4).
- **The front card** adds "Valid until {date}" and the badge.
- **New:** Loop 5's pill after the program name, and "N credentials · N new" in the heading meta.
- **Hue:** `cred--issuer` and `--issuer-hue` per card, by §13 table A.

### 11.2 The detail page

`benefit-credential.html`, for a `BenefitCredential` at `/p/{id}/credentials/{credential_id}`
(`benefit-health.html`, `benefit-food.html`, `benefit-energy-tampered.html`). From top to bottom:

- **Page head:** "‹ Credentials | Benefit credential".
- **Program bar:** "Program: {Name}", in the hue as received (as income's
  `detail_issuer_hue`).
- **Status band.**
- **Claims:** Program, Issued by.
- **Benefit:**
  - Health: Discount, Plan, and You pay, with "Worked out by your wallet from the discount".
  - Pass/fail: Result "Eligible", with "{Name} carries no amount. Holding this credential shows you
    qualify."
  - Dividend: Payment.
- **Validity:** "Valid from {date}" and "Valid until {date}".
- **View credential details:** id, issuer, type, `validFrom`/`validUntil`, the program code and
  signed figures, "Program colour, hue N", and the JWT.

The tampered text is the handoff's: "Something in this credential was changed after Benefit
Agency issued it, so it can't be trusted or used."

`CredentialView` gains `program`, `program_name`, `discount_percent`, `plan_cost`,
`monthly_price` (derived), `monthly_payment`, and `figure` / `figure_sub` for the ledge. The route
picks the template by category, as income does now.

The Wallet's `cred.css` becomes the handoff's `wallet/cred.css`, byte for byte.

## 12. Arriving from Benefit Agency (#108)

### 12.1 The remembered person

The Wallet has no sign-in: a person is "signed in" by being in the URL (Loop 4a). To answer "who
is signed in?" when a browser arrives from Benefits, the Wallet **remembers the last person
viewed in a cookie**:

- Every `/p/{id}/…` page response sets `wallet_person={id}`: `HttpOnly`, `SameSite=Lax`, `Path=/`,
  and `Secure` when the request came over HTTPS (Render's proxy says so in `X-Forwarded-Proto`).
- **Sign out** changes from a link to `/` into a link to `GET /sign-out`, which clears the cookie
  and redirects to `/`.

It's navigation, not authentication, exactly like **Sign in**. It amends decisions.md's "Signing
out clears nothing" (Loop 4a design §3). **Confirmed (Ed, 2026-09-24).**

### 12.2 Routes

| Route | Does |
|---|---|
| `GET /requests/{service_id}/{request_id}` | Validates the service id against the registry, and the request id as 32 hex characters (404 otherwise). **Cookie holds a known person:** 303 to that person's route below. **No cookie:** the landing page's `landing-request.html` variant, whose **Sign in** goes to `/p/p01/requests/benefits/{request_id}`. |
| `GET /p/{id}/requests/{service_id}/{request_id}` | Holds a benefit credential: `…/already`. Otherwise start an attempt whose call 1 is **the request by reference** (`GET …/api/applications/requests/{rid}`), with `arrived` set, then `…/asking`. From there it's §10's flow. |

- **The Wallet only ever fetches from the registry's URL for that service id.** Nothing in the
  query string or path can steer an outbound call elsewhere.
- **Consent when arrived** (`consent-arrived.html`) adds the `.arrival` row: the photo, "Benefit
  Agency sent you here. You're applying as {name}.", and **Not you? Switch person**.
- **Switch person** carries the request: the switcher accepts `request={service_id}:{request_id}`,
  validated as above. Each row then links to that person's `/p/{id}/requests/…` route. A
  by-reference request can be fetched any number of times until answered (§2).
- **Already applied** (`already-applied.html`) says "You've already applied", "Benefit Agency
  decided your programs on {date}…" (from `link.determination`, or "earlier" if the link is gone),
  and **View your benefit credentials** (`/p/{id}/credentials#benefits`).
- **An expired or unknown request** (404 by reference) ends as the `error` page. There, **Try
  again** starts a fresh call 1, so the person can still apply.
- **Nothing sends the person back to Benefit Agency.**

## 13. Outcome tables (Loop 5 retro)

Every display rule below names each value it can receive, instead of "the happy path and
everything else".

**A. A held `BenefitCredential`, by verification outcome**

| Outcome | Card hue | Badge | Counts as "holds" (hides Find government services) | Shown on results |
|---|---|---|---|---|
| Verified | program hue | Verified | yes | yes |
| Not yet valid | program hue | Not yet valid | yes | yes |
| Expired | program hue | Expired | yes | yes |
| Tampered | none (sand) | Tampered | yes | yes, badged |
| Unrecognized issuer | none (sand) | Unrecognized issuer | yes | yes, badged |

**B. A program outcome**

| Outcome | Credential | Results | Activity dot | Admin |
|---|---|---|---|---|
| eligible (pass/fail) | yes | card, "Eligible" | `verified` | Result "Eligible", credential id |
| eligible, Health 0 < d ≤ 100 | yes | card, "{d}% off" / "100% off" | `verified` | discount and price |
| eligible, Health d = 0 | yes | card, "Full price" | `neutral` | "0% off" |
| eligible, Dividend | yes | card, payment | `verified` | payment |
| denied, `income_over_limit` | no | `.outcomes` line | `neutral` | figure against limit, reason |
| denied, `not_nj_resident` | no | `.outcomes` line (all five) | `neutral` | "Not evaluated" |

**C. How an application attempt ends, in the Wallet**

| End | Page | Activity | Connection | Find government services afterwards |
|---|---|---|---|---|
| Missing identity | can't apply (identity) | `caution` | none | stays |
| Missing income | can't apply (income) | `caution` | none | stays |
| Denied consent | back to the services page | `neutral` | none | stays |
| No answer (call 1 or 2) | error | `caution` | none | stays |
| Refused (`credential_invalid`, `subjects_differ`) | results, refused | `error` | none | stays |
| Decided, 0 eligible | results, "don't qualify" | per program | yes | stays |
| Decided, ≥ 1 eligible | results | per program + received | yes | replaced by Benefits once any credential is held |

**D. Benefit Agency's view of a presentation**

| Case | HTTP | Recorded | Connection |
|---|---|---|---|
| Bad shape | 400 | no | no |
| Unknown or expired request | 404 | no | no |
| A credential fails checks 1–4 | 200 refused `credential_invalid` | yes | no |
| Subjects differ | 200 refused `subjects_differ` | yes | no |
| Decided | 200 decided | yes | yes, replacing any earlier one for that subject |

## 14. Tests

**First, from the documents** (Loop 4's improvement, carried forward):

- The engine against **every row of the oracle** (§4).
- A benefit credential compared key by key with credential-model §3's envelope and the Health
  claims.

**Benefits:**
- **Engine:** the oracle rows; each limit at exactly the limit (eligible) and one cent over
  (denied); Health's rounding at a half-tenth boundary; Dividend at 0, 1,200 and above.
- **Credential:** fields, types, `validFrom` floored to the minute, `validUntil` +12 months
  (29 February too), header, issuer id, `CredDemoCardColor` hue per program, and that the
  signature verifies with `issuer.json`.
- **API:**
  - Call 1 shape, including `multiple`; the by-reference GET, repeatable, then 404 once answered
    or expired.
  - Call 2: decided (five entries, in order, with ids and figures), refused for each reason, 400
    for each bad shape, 404.
  - Re-applying replaces the connection. Call 3 as Payroll's tests.
- **`/health` and JWKS**, as Payroll's.
- **Pages:** landing cards and order; each program page's figures from `rules.json`; Housing's 21
  rows; no Health or Dividend table; the Apply options and `aria-describedby`; `/apply` 303s to
  the Wallet with a live request id.
- **Admin:** grouping and order, each Result wording, empty state, each determination variant,
  image truncated, 404.
- `cred.css` pinned; no `<script>` on any Benefits page.

**Wallet:**
- **Registry:** kinds, the URL override, employer lookup unchanged.
- **Trust:** a Benefits-signed `BenefitCredential` verifies; a Benefits-signed paystub and a
  Payroll-signed benefit credential don't.
- **Hue:** read from `CredDemoCardColor` only; §13 table A row by row.
- **Credentials page:** the entry, or the category, per table A. The ledge figure rows of §11.1;
  New once; `id="benefits"` on both; the script redraws both sections.
- **Attempt:**
  - Missing identity leads over missing income. Consent with 1 + 2 and 1 + 6, repeated actions
    above three, per-issuer panels.
  - Approve builds the VP in order. Each call 2 answer and the resulting phase; fetch awaited on
    decided.
  - Try again re-sends, and falls back to call 1 on 404. Stale answers are dropped.
- **Results:** every row of the verdict table; flat cards; "on the way" when an id isn't held;
  denials; the refused sentence chosen by the Wallet's own verification; redirect with no
  determination.
- **Fetch:** kind-specific wording, and `lost` removing a Benefits link silently.
- **Connections and Activity:** each row of §10.9.
- **Detail page:** each program, including the derived price and tampered.
- **Arrival:**
  - Cookie set on `/p/…` pages and cleared by `/sign-out`.
  - With a cookie → redirect; without → the landing variant. Bad service or request ids → 404.
  - Already applied; the switcher carrying the request; the outbound URL always the registry's.
- **Script scope:** the pending pages, the applying page and the Credentials page contain a
  `<script>`, and no page loads one from a URL.
- `cred.css` pinned.

**Payroll:** the renamed hint type; the Wallet reads only the new name.

Tests use throwaway keys and never read `keys/` or `.env`.

## 15. Build order

Ten build PRs and a live pass. There's one branch each, and each says "Refs #N" or "Closes #N".
Per the Loop 4a retro, **the plan step comes before PR 1**: a reconciliation pass (each handoff
page against this design, each acceptance criterion against its mechanism, and each dependency
against Ed's machine), and the side-by-side setup, dry-run. A UI PR merges only with green CI
**and** a clean side-by-side table. Hands-off merges apply.

| PR | Issue | Scope | Redeploys |
|---|---|---|---|
| 1 | #110 | The rename (§5): Payroll signs, the Wallet reads, docs | Wallet, Payroll |
| 2 | #105 (part) | Keys and trust (§3): generator, re-keyed output, Benefits' `signing.py`, `/health`, JWKS, trust lists, `render.yaml`, `.env.example`, `launch.json`, CLAUDE.md. **Ed sets `BENEFITS_SIGNING_KEY` and the new `PAYROLL_SIGNING_KEY` in Render before it merges.** | all three |
| 3 | #104 | The engine and `rules.json` (§4) | Benefits |
| 4 | #20 | Benefits' `cred.css`, `base.html`, landing and program pages; `/apply` to the Wallet's landing for now (§7) | Benefits |
| 5 | #105 | Call 1, by reference, call 2, verification, the application record, connections (§2, §6); credential-model §1 updates | Benefits |
| 6 | #106 | The benefit credential and call 3 (§5) | Benefits |
| 7 | #111 | The admin view (§8); decisions.md's admin amendment | Benefits |
| 8 | #109 | The Wallet's `cred.css`, `programs.json`, `CredentialView`, the Benefits category and the detail page (§11), tested with fixture-signed credentials | Wallet |
| 9 | #107 | The registry entry, services, the apply attempt, consent, can't apply, applying, error, results, fetch wording, Connections, Activity, the script change (§9, §10); decisions.md and CLAUDE.md script sentences | Wallet |
| 10 | #108 | `/apply` by reference (Benefits); arrival, the cookie, `/sign-out`, the landing variant, consent-arrived, already applied, the switcher carry (Wallet) (§12); decisions.md (cookie) | Wallet, Benefits |
| 11 | — | Live pass on Render (docs only) | none |

### Checking the build against the handoff

The `handoff` server (port 8010) serves `/loop-6/benefits/…` and `/loop-6/wallet/…`. For each
built page and its handoff counterpart, compare the rendered top and height of the page head
(Benefits: `.intro` or `.program-band`), the main section and its first card or panel. Benefits
pages are compared at **375px and 992px**, and Wallet pages at **375px and 480px**. Positions agree
within 1px, and computed font size, padding and gap match. Each UI PR (4, 7, 8, 9, 10) records the
table. There are no screenshots.

## 16. Decisions and deviations

1. **Benefits' issuer id is its origin**, `https://cred-demo-benefits.onrender.com`, not the
   handoff's `did:example:benefit-agency` (credential-model §2; Payroll's precedent).
2. **`multiple: true`** asks for every income credential (§2). It's DCQL's own term, and settles
   the intent's question.
3. **`validFrom` is floored to the minute** (§5): a small margin for clock skew between services.
   Credential-model §5's "the moment of issue" still holds to the minute.
4. **Health's price is derived by the Wallet** from the signed one-decimal percent, rounded to
   the cent half-up (Intent 006; Grace $57.00).
5. **The Wallet remembers the last person in a cookie** (§12.1), so an arrival from Benefits knows
   who is signed in. It amends "Signing out clears nothing". **Confirmed (Ed, 2026-09-24).** Without it, every
   arrival lands on the signed-out variant and **Sign in** opens p01.
6. **The Credentials script redraws `#benefits` as well as `#income`**, and the services entry
   carries `id="benefits"` (§10.1). It's a two-line change to the handoff's script, and an added id.
7. **The apply attempt reuses Loop 4a's asking page** while call 1 runs (§10.3). The handoff
   doesn't show that moment.
8. **Starting an attempt is a GET** (`…/apply`, `/apply` on Benefits), because the handoff's
   controls are links. Both are guarded so a repeat is harmless.
9. **Try again re-sends the approved presentation**, falling back to a fresh request and fresh
   consent when Benefits no longer knows the request (§10.6).
10. **The refused sentence comes from the Wallet's own verification** of what it shared, so the
    refusal reply needs no new field (§10.7).
11. **A `lost` Benefits connection removes the link** instead of offering "Finish connecting"
    (§10.8), since there's nothing to reconnect to.
12. **Benefit credentials are signed once and stored** (§5), unlike Payroll's sign-on-demand,
    because Benefits keeps the record anyway.
13. **The generator stops printing private keys** (§3), after Loop 5's leak.
14. **Docs changed this loop:**
    - decisions.md: the admin view, the render hint's name, the script and pending-page
      sentences, and the cookie
    - credential-model.md: §1 Phase 4 steps 7 and 9, and "When it fails" (a tampered identity
      is stopped at Payroll); §3's Health claim precision; §4's `renderMethod` row and the DCQL
      `multiple` note
    - CLAUDE.md: the scripts sentence, Benefits' local run, and the Sign out link

## 17. Acceptance criteria

1. Running `uv run tools/generate_credentials.py` writes Benefits' key pair, `issuer.json`
   (origin id, Benefit Agency, `benefits-1`), Benefits' trust list (the four states for identity,
   Payroll for paystubs), the Wallet's trust entry for Benefits (`BenefitCredential` only), and
   both apps' `.env`. It re-signs every identity credential with the same ids, and prints no
   private key. No private key is committed.
2. Benefits' `/health` returns 200 on Render with `BENEFITS_SIGNING_KEY` set, and 503 with a reason
   when it's missing or doesn't match. `/.well-known/jwks.json` serves the public key. Payroll's
   `/health` returns 200 with its new key.
3. The eligibility engine reproduces every row of sample-data.md's expected outcomes: monthly,
   annual, Health discount to one decimal, Food, Energy, Housing and Dividend. Out-of-state people
   get `not_nj_resident` for all five programs.
4. Each limit is inclusive: income exactly at a limit is eligible, and one cent over is denied
   with `income_over_limit`.
5. Benefit Agency's landing page shows five program cards in program order, each named and
   colored, linking to its page. The nav links the five programs and Admin, and no placeholder
   user remains.
6. Each program page shows its requirements with annual figures rendered from the rules data and
   an "as of September 2026" note. Housing lists all 21 county limits in a disclosure. Health and
   Dividend show their three figures and the "earning more" callout, with no table.
7. Every program page offers a disabled **Apply here** with its note, and **Apply with Digital
   Wallet**, which sends the browser to the Wallet carrying only a request id.
8. Call 1 and the request by reference return a DCQL query naming `IdentityCredential` and
   `PaystubCredential` with `multiple: true`, and a `response_uri` path. The by-reference request
   can be fetched until it's answered, then returns 404.
9. Call 2 with a valid presentation returns `decided`, a `connectionId`, and five program outcomes
   in order. Eligible ones carry their credential id and figures, and denied ones their reason
   code.
10. Call 2 refuses with `credential_invalid` when any credential fails checks 1–4, and
    `subjects_differ` when the subjects differ. It returns 400 for a presentation without exactly
    one identity credential and at least one income credential.
11. Each eligible program yields one `BenefitCredential` matching credential-model §3. It carries
    a random `urn:uuid:` id, `validFrom` at the determination time floored to the minute,
    `validUntil` 12 months later, and one-decimal `discountPercent` for Health. It has no name or
    address, a `CredDemoCardColor` hint with its program's hue, and an ES256 `benefits-1`
    `vc+jwt` header. A denial yields no credential.
12. Call 3 returns a connection's benefit credentials not in `have`, with the same id and JWT
    every time. It returns 404 for an unknown connection. Applying again replaces the connection.
13. Payroll signs `CredDemoCardColor`, and the Wallet reads only `CredDemoCardColor`.
14. The admin list shows every application grouped by person, newest first, with the time and a
    one-line result. It shows the empty state when there are none.
15. Each determination page shows the received time and ids, and each presented credential's
    result with its decoded claims (photo not shown) and raw JWT. It shows the same-person check,
    the submitted state, county and paystubs with monthly and annual totals, and per program the
    figure against its limit, the result and the issued credential or reason. Not-NJ and refused
    applications show their variants.
16. A person holding no benefit credential sees **Find government services** between Identity and
    Income. It leads to a services list with Benefit Agency, and on to its request.
17. A person with no identity credential gets the "identity credential first" page, and one with
    identity but no income gets "Connect your payroll provider first" with **Find your employer**.
    Each is logged in Activity.
18. The consent page lists every requested credential, with the income credentials grouped by
    issuer, each openable to every claim. It is all-or-nothing, and repeats the actions below the
    list when there are more than three credentials. Deny shares nothing and is logged.
19. After **Approve and share**, the person waits on "Checking your eligibility…" (polling, with
    **Check again** without JavaScript), then lands on the results screen.
20. The results screen leads with the verdict sentence for the person's case (p01, p04, p07, p09,
    p19 as in the handoff). It shows the benefit cards in program order, then each denial as a
    plain line, then **Go to your credentials**. The verdict is announced without moving focus.
21. If the outcomes are known but credentials haven't arrived, the results screen says they're on
    the way, and the Credentials page's check brings them.
22. If Benefit Agency can't be reached, the person sees "Couldn't reach Benefit Agency", which is
    logged once. **Try again** re-sends the approved application, or starts over when Benefits no
    longer knows the request.
23. A refused application shows "Your application couldn't be decided" with the right sentence for
    what failed, is logged as an error, and makes no connection.
24. Once any benefit credential is held, the Benefits category replaces **Find government
    services**. Each card is in its program's hue (by §13 table A), shows its name and figure
    (Eligible, "92.4% off" with "$57.00 a month", "Full price", "$100.00 a month"), and shows
    **New** once.
25. The benefit detail page shows the program bar, status, claims, the benefit's figures (Health's
    price marked as worked out by the wallet), valid from and until, and the technical details
    with the JWT. A tampered one shows the Tampered status and its note.
26. Connections shows Benefit Agency as a connected government service with its credential count,
    and **Remove** keeps the benefit credentials. Activity logs the application, each program's
    outcome, the credentials received, and failures, with §10.9's dots.
27. Arriving from Benefit Agency with a remembered person opens that person's consent page, with
    "You're applying as {name}" and **Not you? Switch person** (which keeps the request). Without
    one, it opens the landing page with the request notice, and **Sign in** continues to consent.
    A person who already holds benefit credentials gets "You've already applied".
28. The Wallet only ever calls Benefit Agency at its registry URL, whatever the arrival URL says.
29. Only the Wallet's pending pages, applying page and Credentials page contain a `<script>`, and
    no page in any app loads a script from a URL.
30. Each app's `cred.css` is its handoff file, byte for byte. Every built page matches its handoff
    page within 1px at the §15 widths, recorded in each UI PR.
31. All three suites pass in CI. A live pass on Render applies for p01 from the Wallet and p07
    from a program page, and matches one credential's id, claims and signature between Benefits'
    admin page and the Wallet's detail page. Ed confirms from Render's events log that each PR
    redeployed only the services §15 lists.
