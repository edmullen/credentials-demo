# Design: Loop 5 — Payroll issues credentials

This is the technical design for [Intent 005](intents/005-payroll-issues-credentials.md). It
covers one issue, [#19](https://github.com/edmullen/credentials-demo/issues/19), and follows
[decisions.md](decisions.md), the [credential model](credential-model.md) and the Claude Design
handoff in [design/loop-5/](design/loop-5/README.md). Issue #9, which described the Wallet's
on-load check, was closed as superseded by #19 and is covered here as part of it.

Loop 4a's design is archived at [design/loop-4a/design.md](design/loop-4a/design.md).

## 1. Overview

Loop 4 connected the Wallet to Meridian Payroll. This loop makes the connection useful:

- **Payroll becomes an issuer.** It gets its own signing key, and signs one income credential
  (`PaystubCredential`) per paystub, whenever it's asked.
- **The Wallet receives them.** It asks right after connecting, and again whenever the
  Credentials page opens. It verifies each credential, keeps it, and shows it in Loop 2's stack,
  in Payroll's color.
- **Both apps show their side.** The Wallet gets an income detail page and an "all income
  credentials" page. Payroll's paystub page shows the credential for that paystub next to the
  paystub itself.

What changes, by app:

| Where | Changes |
| --- | --- |
| `tools/generate_credentials.py` | Adds Payroll's key pair and trust entry; re-keys everything (§3) |
| `apps/payroll` | Signing key and self-check, JWKS, credential builder, issuance endpoint, `connectionId`, paystub panel, Activity entry (§3–§6) |
| `apps/wallet` | Trusts Payroll for income, stores received credentials, fetch on connect and on open, income cards and pages, Activity entries (§7–§10) |
| `apps/benefits` | Nothing. It has no trust list yet; Loop 6's generator run adds Payroll to it (§13 item 9) |
| `render.yaml`, `.gitignore`, `.claude/launch.json` | Payroll's secret and its local `.env` (§3) |

## 2. The protocol

This is the stand-in for OpenID4VCI that credential-model §4 names: "give me the credentials I
haven't received." It adds one field to Loop 4's call 2, and one new call.

### Call 2 now returns a connection id

When Payroll answers a presentation with `connected`, the response gains an opaque id:

```json
{ "outcome": "connected", "connectionId": "3f9c…" }
```

- `connectionId` is a fresh `uuid4().hex`. Payroll keeps it on the person's `Connection` record,
  and in an index from id to person.
- The Wallet keeps it on its `Link` (§7). It's the only thing that identifies the person to
  Payroll from then on. The Wallet never sends a person id or subject id to fetch credentials.
- Connecting again (Loop 4's overwrite rule) issues a new id, and the old one stops working.

### Call 3: fetch credentials

```
POST {provider url}/api/credentials
{ "connectionId": "3f9c…", "have": ["urn:uuid:…", "urn:uuid:…"] }
```

- **200** `{ "credentials": ["<jwt>", …] }`: one signed credential for each of the person's
  paystubs whose credential id isn't in `have`, in the order of §4. An empty list means nothing
  new.
- **404** `{ "error": "unknown_connection" }`: Payroll doesn't know that `connectionId`. In
  practice this means Payroll restarted and forgot the connection (§9).
- **400** `{ "error": "invalid_request" }`: the body isn't that shape.

The Wallet sends the ids it holds (`have`) instead of fetching everything and filtering. This is
what Phase 3 describes, and it keeps the response small. It settles the intent's second open
question.

Payroll keeps no record of what it has sent. A restart on either side costs nothing: the Wallet's
`have` list says what it still holds, and the ids are stable (§4).

### Timing and failure

Call 3 uses the Wallet's existing `outbound.post_json`: one attempt, a 60-second timeout, no
automatic retry, and the honest `cred-demo-wallet` user agent. Loop 4's Render test found that a
cold Payroll refuses a server-to-server call in about 2 seconds. That lands as **Couldn't reach
Meridian Payroll**, and **Check again** works once Payroll is awake. Nothing is engineered around
it.

## 3. Payroll's key

### Generator

`tools/generate_credentials.py` gains Payroll as an issuer. It's still one run, by hand, with
committed output (decisions.md):

- **A new ES256 key pair**, `kid` `payroll-1`. The private JWK goes to `keys/payroll-1.jwk.json`
  (gitignored, like the states' keys), and to `apps/payroll/.env` as `PAYROLL_SIGNING_KEY=<jwk>`,
  on one line. The script prints the same line for pasting into Render.
- **`apps/payroll/app/data/issuer.json`** (committed): Payroll's issuer id, name, `kid` and public
  JWK. Payroll reads it for the self-check, for JWKS, and for the `issuer` it signs.
- **The Wallet's `trust.json`** gains Payroll's entry, trusted for `PaystubCredential` only.
- **Payroll's own `trust.json`** doesn't change shape: the four states, for `IdentityCredential`.
  Payroll never verifies its own credentials.
- **Everything is re-keyed,** as the credential model's "keys are disposable" rule says. The four
  states get new keys, so every committed identity credential is re-signed. The credential ids
  are name-based, so they survive, and the Wallet's detail-page URLs don't change.

**The issuer id is Payroll's deployed origin,** `https://cred-demo-payroll.onrender.com`, per
credential-model §2 ("Issuer identifiers"). The handoff's `did:example:meridian-payroll` is a
placeholder (#93). The id is a constant in `issuer.json`, not derived from the request, so a
local Payroll signs with the same issuer id and the same trust entry applies.

### Configuration

- **`render.yaml`:** Payroll's service gains `PAYROLL_SIGNING_KEY` with `sync: false`. Ed pastes
  the value in Render's dashboard. It's the demo's first secret in Render.
- **`.gitignore`** gains `.env`. A committed `apps/payroll/.env.example` names the variable.
- **Locally,** uvicorn loads it with `--env-file .env` (python-dotenv already comes with
  `uvicorn[standard]`). `.claude/launch.json`'s `payroll` entry and CLAUDE.md's local-run command
  gain the flag.
- **Tests** never use a real key. A fixture generates a throwaway key pair and patches
  `issuer.json`'s public key to match (credential-model §2, "Key custody").

### Self-check and JWKS: `app/signing.py`

- On startup, Payroll reads `PAYROLL_SIGNING_KEY`, derives its public key, and compares it with
  `issuer.json`.
- **`/health`** returns 200 `{"status": "ok"}` when they match. Otherwise it returns **503** with
  `{"status": "unhealthy", "reason": "…"}`, the reason being either "PAYROLL_SIGNING_KEY is not
  set" or "PAYROLL_SIGNING_KEY does not match the committed public key". Render's health check
  then refuses the deploy and keeps the previous version running, which is the safe outcome.
- **`GET /.well-known/jwks.json`** returns `{"keys": [<public JWK from issuer.json>]}`.
- Without a valid key, Payroll still serves its pages. The issuance endpoint returns 503, and the
  paystub panel leaves out the signed JWT (§6).

## 4. The income credential

`app/issuance.py` builds one credential per paystub, from `paystubs.json`, exactly as
credential-model §3 describes:

```json
{
  "@context": ["https://www.w3.org/ns/credentials/v2"],
  "id": "urn:uuid:<uuid5 of the paystub id>",
  "type": ["VerifiableCredential", "PaystubCredential"],
  "issuer": { "id": "https://cred-demo-payroll.onrender.com", "name": "Meridian Payroll" },
  "validFrom": "2026-09-15T00:00:00Z",
  "credentialSubject": {
    "id": "<the person's subjectId>",
    "employer": { "type": "Organization", "name": "Pinecrest Home Care" },
    "payPeriodStart": "2026-09-01",
    "payPeriodEnd": "2026-09-15",
    "payDate": "2026-09-15",
    "payFrequency": "semimonthly",
    "grossPay": { "type": "MonetaryAmount", "value": 1100.00, "currency": "USD" },
    "netPay":   { "type": "MonetaryAmount", "value": 955.87, "currency": "USD" }
  },
  "renderMethod": [{ "type": "CredDemoIssuerColor", "color": "oklch(0.46 0.11 255)" }]
}
```

- **`id`:** `uuid5(PAYSTUB_CREDENTIAL_NAMESPACE, <paystub id>)`, with a namespace constant of
  Payroll's own. It's different from the paystub's id, as Ed wanted (the two are separate
  records), but always the same for the same paystub. Nothing is stored, and a restart can't
  cause duplicates.
- **`validFrom`** is the pay date at midnight UTC. There's no `validUntil`: a paystub never
  expires (credential-model §5).
- **Money** is a JSON number, as in the credential model's example, converted from the paystub's
  decimal string.
- **No employee name**, per the credential model: the subject id says whose it is.
- **JWT header:** `alg: ES256`, `kid: payroll-1`, `typ: vc+jwt`.
- **Signing happens whenever a credential is asked for,** by call 3 or by the paystub page. ES256
  signatures differ each time, so the JWT bytes differ, but the id and every claim are the same.
  The Wallet matches by id, so that doesn't matter.
- **Order:** newest pay date first, and within a pay date, the order of `paystubs.json`. For p08
  that's Shoreway, Brightpath, Ridgeline. The Wallet keeps this order (§8).

### `renderMethod`: the issuer color

This settles the intent's first open question. The handoff's Wallet takes only a hue from the
hint (handoff §1.1), so the hint is one color:

- **Shape:** `renderMethod` is VC 2.0's reserved property for display hints. Its entries are typed
  objects. The W3C Render Method draft defines template types (SVG, HTML), not a single color, so
  the demo uses its own type, `CredDemoIssuerColor`, with one `color` in CSS `oklch()` syntax.
  This is a subset of the standard, not contrary to it: the property is standard, and new types
  are how it's meant to be extended. Like our other custom terms, it has no JSON-LD context of
  its own (credential-model §4, decision 1).
- **Payroll's value** is `oklch(0.46 0.11 255)`, its own `--accent` recipe at hue 255.
- **The Wallet** reads the first `CredDemoIssuerColor` entry and takes the hue, the third number
  in `oklch(L C H)`. It ignores L and C, which its own `cred.css` fixes, so an issuer can't make a
  card illegible. No entry, an unreadable color, or a tampered credential all mean no hue, and the
  card falls back to Loop 2's sand.
- **It's signed,** so the color can't be changed without breaking the signature.

credential-model §4's "Display rendering" row changes from "Deferred (#19)" to this, with a
decision entry (§12, PR 1).

## 5. Payroll's API and state

- **`POST /api/credentials`** (call 3, §2). It looks up the person by `connectionId`, builds the
  credentials for their paystubs not in `have`, and signs them. If there's at least one, Activity
  logs it (below).
- **`app/connections.py`:** `Connection` gains `connection_id`. There's a new index,
  `_by_connection_id: dict[str, str]` (id to person id). `connect()` creates the id, drops the
  person's old id from the index, and returns the new one. The call-2 route returns it.
- **Activity:** "2 income credentials sent to your wallet", with the `neutral` dot (handoff §7).
  It says "1 income credential" for one. A fetch that returns nothing new isn't logged.

## 6. Payroll's paystub page

The paystub page gains the credential panel from `payroll/paystub.html`, in the handoff's
`.records` grid. It sits beside the paystub from 60rem and below it when narrower:

- **"Paystub"** and **"Credential for this paystub"**, each an `<h2>` heading a `<section>`, with
  the handoff's `.record__sub` lines.
- **The panel shows the credential as signed.** The page builds the payload with §4's code, signs
  it, and renders the claims from that payload. So what's shown is exactly what a wallet would
  receive. Values are formatted with the paystub page's own `money()` and date helpers, so the
  two records visibly agree.
- **Claim names** in mono under each value (`.claim__key`), the id in the deep band, and **View
  signed credential** (`.disclosure` with `.jwt`) holding the JWT.
- **Every paystub shows it,** connected or not, with no delivery status (intent).
- Payroll's `cred.css` becomes the handoff's `payroll/cred.css`, byte for byte.

## 7. The Wallet's state

`app/state.py` gains:

- **On `Link`:** `connection_id: str | None` and `arrived: int | None`. `arrived` is the count the
  first fetch brought, shown once on Connections (§10).
- **`_received: dict[str, dict[str, str]]`**: per person, credential id to JWT, in the order they
  arrived. Only received credentials live here. The identity credentials are still read from the
  committed `credentials.json`.
- **`_seen: dict[str, set[str]]`**: per person, the credential ids that have been rendered. A
  received id not in it is **New** (handoff §2.3).
- **`_checks: dict[tuple[str, str], Check]`**: per person and provider, the latest check:
  `state` (`checking` or `done`), `result` (`none`, `new`, `error` or `lost`), `count`,
  `finished_at`, and `token`.

Removing an employer's last link (Loop 4's Remove) removes the link and its check. It keeps the
received credentials: they're signed and still valid, and the person holds them (§13 item 6).

Everything is in memory, per process, and lost on restart, as before (decisions.md).

## 8. The Wallet's credentials

`app/credentials.py`'s `credentials_for()` returns the committed identity credentials followed by
the received ones, each verified against `trust.json` on every render, as now. So a tampered
income credential shows as received, with a Tampered badge.

- **Trust:** Payroll's key verifies `PaystubCredential` only. A Payroll-signed
  `IdentityCredential`, or a state-signed `PaystubCredential`, fails check 2 (trusted for type)
  and shows as unrecognized.
- **`CredentialView`** gains the income claims: employer name, period, pay date, frequency, gross
  and net pay, and `issuer_hue` (§4, None when there's none or the credential isn't verified).
- **Order:** received credentials keep Payroll's order (§4), newest first.

### Income on the Credentials page

The Income category renders from what's held (handoff pages `credentials-*.html`):

- **None held:** the three Loop 4a notes, the "connected" one reworded to "You're connected to
  Meridian Payroll. Your pay will appear here as credentials as soon as they arrive."
  (handoff §2.4).
- **One held:** a full `.cred.cred--income` card (handoff §3). No sample person holds exactly one.
- **Two or more:** Loop 2's `.stack-cards`, with the handoff's retuned stylesheet:
  - The five newest are drawn, with the newest at the front. Each card gets `--i`, 0 at the back.
  - More than five adds the **"View all Income credentials (N)"** ledge at `--i: 0`, linking to
    `/p/{id}/credentials/income`. N is the total.
  - The stack gets `--n` equal to the highest `--i` (items drawn, minus one). This is what the
    handoff pages do and what the height formula needs. The CSS comment's "number of cards" is
    off by one; the pages are right.
- **Issuer color:** a card with a hue gets `cred--issuer` and `style="--issuer-hue: <h>"`. The
  ledge never does (handoff §1.2).
- **New:** a card whose id isn't in `_seen` gets the `.cred__new` pill. After rendering, the page
  adds every drawn id to `_seen`. The heading meta reads "2 credentials · 2 new" while any are
  new.

### Income pages

- **`/p/{id}/credentials/income`** (`income-p08.html`): page head "‹ Credentials | Income
  credentials", then every held income credential as a full card, newest first. It declares
  ahead of the detail route, so `income` isn't read as a credential id.
- **`/p/{id}/credentials/{credential_id}`** keeps its route. An income credential renders the new
  `income-credential.html` template (handoff §4): issuer bar, status band, claims, the summary
  note, "Valid from 15 September 2026" and "Doesn't expire", and **View credential details**
  (credential id, issuer, type, validFrom "(no validUntil)", display "Issuer colour, hue 255", and
  the JWT). The tampered variant adds the identity page's note, as the handoff shows. Identity
  credentials keep `credential.html`.

The Wallet's `cred.css` becomes the handoff's `wallet/cred.css`, byte for byte.

## 9. Fetching: `app/issuance.py`

One function does the work for both moments: `fetch(person_id, provider_id)`.

1. It reads the link. It stops if there's no `connection_id`.
2. It records a `Check` in state `checking` with a fresh token, and posts call 3 with the held
   income ids for that provider's issuer as `have`.
3. When the answer comes, it writes only if the check's token is still current, the same
   stale-answer rule as Loop 4's attempts. A Remove or a newer check makes the answer harmless.
4. Then, by answer:
   - **200:** verify each credential, add it to `_received`, and finish as `new` (count > 0) or
     `none`. Log "N income credentials received from Meridian Payroll" (`verified`) for those
     that verified, and "N income credential(s) from Meridian Payroll couldn't be verified"
     (`error`) for any that didn't (handoff §7). No sample person produces the second.
   - **404 `unknown_connection`:** Payroll has forgotten the connection. The Wallet clears
     `connected_at` and `connection_id` and keeps the employers, so the person is back at
     "Now connect your payroll". It finishes as `lost` and logs nothing: Loop 4 decided that a
     lost connection looks like no connection (Loop 4 design §13, item 11).
   - **Anything else** (timeout, refusal, 5xx, bad JSON): finish as `error`. Log "Couldn't reach
     Meridian Payroll to check for new credentials" (`caution`), unless the previous check for
     this provider also ended in `error`. Repeated page loads while Payroll is down then log once,
     not every time.

### Right after connecting

When call 2 returns `connected`, `run_call_two` stores the `connectionId`, then awaits `fetch()`
before it ends the attempt. The pending-verify page is still polling, so the person waits the
extra second or two there. Payroll is warm at that moment.

If the fetch brought credentials, `link.arrived` holds the count, and Connections adds the
handoff's line to the Connected band: "2 income credentials received. View credentials." The
Connections page clears `arrived` after rendering it once. If the fetch failed or brought
nothing, the line is left out, and the Credentials page picks it up (handoff §5).

### Whenever the Credentials page opens

A GET of the Credentials page, for a connected person:

- **Starts a check** by spawning `fetch()` (the existing `outbound.spawn` seam), unless one is
  already running for that provider or the last one finished less than 30 seconds ago. The
  30-second window matters because the handoff's script re-requests the page to redraw (below).
  Without it, every redraw would start another check. It also keeps reloads from hammering
  Payroll.
- **Never waits on it.** The page renders straight away from what's held.
- **Renders the check's state** in the Income heading and below the cards (handoff §2.1):

| The provider's check | Heading meta | Below the cards | `data-check` |
| --- | --- | --- | --- |
| Running | the count (the script shows "Checking issuers") | the no-JS form | the status URL |
| Finished, with cards not yet seen | "2 credentials · 2 new" | nothing | empty |
| Finished `none` or `lost` | the count | the no-JS form | empty |
| Finished `error`, most recent | the count | the error note with **Check again** | empty |

The no-JS form (`.category__check`) is a GET of the same page, so it starts a new check if the
30-second window has passed. The server renders it without `hidden`; the script hides it.

**`GET /p/{id}/credentials/check`** is the status endpoint the script polls. It returns
`{"state": "checking"}` while any check for the person is running. When they're all finished it
returns `none`, `new` or `error`, with `announce` set for `new` ("2 new income credentials from
Meridian Payroll.") and `error` (handoff §2.2). A `lost` result reports `new`, with no
announcement, so the script redraws the section into its not-connected state.

### The script

The handoff's inline script goes into `credentials.html` as delivered. It runs only when
`data-check` holds a URL, and the page works fully without it. This is the Wallet's second use of
JavaScript, under the same rule as the pending pages (decisions.md). decisions.md's "The first
and only use is the Wallet's pending pages" and CLAUDE.md's "The one script is inline on the
Wallet's two pending pages" are updated to name the Credentials page too (§12, PR 5). The test
that pins which pages may contain a `<script>` gains `credentials.html`.

## 10. The Wallet's other screens

- **Connections** (`connections-connected.html`): the one-time "N income credentials received.
  View credentials" line (§9). Nothing else changes.
- **Activity** (`activity.html`): the three new entry types from §9, grouped by day as now.
- **Credentials when the connection was lost:** the person still holds their income cards, and
  the Income note is Loop 4a's employer-chosen note with **Finish connecting**, shown below the
  cards in the same `.category__waiting-note--action` slot the error note uses. The handoff
  doesn't show this combination; it uses only existing components (§13 item 4).

## 11. Tests

**Write the first one from the credential model's example** (Loop 4's improvement, carried
forward): a Payroll test that builds p01's first credential and compares its structure, key by
key, with credential-model §3's paystub example and envelope.

**Payroll:**
- The credential: fields and types as §4; `id` stable across calls, a `urn:uuid:`, and not the
  paystub's id; `validFrom` is the pay date; no `validUntil`; the header's `alg`, `kid` and `typ`;
  the issuer id is the origin; `renderMethod` as §4.
- The signature verifies with `issuer.json`'s public key.
- Call 2 returns a `connectionId`; connecting again replaces it and the old one gets 404.
- Call 3: returns the credentials not in `have`, in §4's order; empty when all are held; 404 for
  an unknown id; 400 for a bad body.
- Activity logs a send with its count and singular form, and logs nothing for an empty send.
- `/health`: 200 with a matching key, 503 with each reason. JWKS serves the public key.
- The paystub page: the panel's `<h2>`, the credential id, each claim key, values that match the
  paystub's, the JWT in the disclosure, and no "sent" wording, for a connected and an unconnected
  person.

**Wallet:**
- Trust: a Payroll-signed paystub verifies; a Payroll-signed identity credential and a
  state-signed paystub don't.
- `fetch()`: stores new credentials and sends the held ids; counts and logs; drops a stale
  answer; `lost` clears the connection and logs nothing; `error` logs once across repeats; a
  tampered credential is kept and logged as `error`.
- Hue: read from a valid `CredDemoIssuerColor`; none for a missing or unreadable hint, or for a
  tampered credential.
- Credentials page: each row of §9's table; the stack's `--i` and `--n` for 2, 5 and 6
  credentials; the ledge's count and link; `cred--issuer` and the hue on cards but never on the
  ledge; the New pill once, then gone on the next render; the lost-connection note.
- The status endpoint's four answers, and the 30-second window.
- The income list and detail pages, including "Doesn't expire" and the tampered variant; `income`
  isn't treated as a credential id.
- Connections' one-time line; Activity's new entries.
- Script scope: exactly the two pending pages and the Credentials page contain a `<script>`, and
  no page loads one from a URL.

**Both apps:** `cred.css` is the handoff's file, pinned by length and SHA-256, as in Loop 4a.
Tests generate throwaway keys and never read `keys/` or `.env`.

## 12. Build order

Six PRs, one branch each, each saying "Refs #19" and the last closing it. Per the Loop 4a retro,
the reconciliation pass and the side-by-side setup are done before PR 1, and a UI PR merges only
with green CI **and** a clean side-by-side table. Hands-off merges apply as before.

1. **Keys and trust** (§3, §4's `renderMethod` decision). Generator, re-keyed committed output,
   `issuer.json`, `signing.py`, self-check, JWKS, `render.yaml`, `.gitignore`, `.env.example`,
   `launch.json`, CLAUDE.md's run command, and credential-model §2 and §4 updates. **Ed sets
   `PAYROLL_SIGNING_KEY` in Render before this merges.** It redeploys the Wallet (re-signed
   identity credentials) and Payroll.
2. **Payroll issues** (§4, §5). The credential builder, `connectionId`, call 3, and Activity. No
   screen changes.
3. **Payroll's paystub panel** (§6) and Payroll's `cred.css`.
4. **The Wallet receives on connect** (§7, §8, the first half of §9, §10's Connections line and
   Activity). Stores and shows income credentials: the stack, the issuer color, New, the income
   list and detail pages, and the Wallet's `cred.css`.
5. **The Wallet checks on open** (the rest of §9, §10's lost-connection note). The check, the
   status endpoint, the script, the no-JS form, the error and lost paths, and the decisions.md
   and CLAUDE.md updates for the script.
6. **Live pass on Render** (docs only). Connect a person on the deployed apps, check both sides,
   and record the result. As in earlier loops, Ed confirms from Render's events log that each PR
   redeployed only the services it should.

### Checking the build against the handoff

Loop 4a's side-by-side check carries over. The handoff pages are served on port 8010 from
`.claude/launch.json`, at `/loop-5/wallet/…` and `/loop-5/payroll/…`. For each built page and its
handoff counterpart, compare the rendered top and height of the page head, the Income category
and its first card (or the panel on detail pages) at **375px and 480px**. For the paystub, compare
both records at **375px and 992px**. Positions must agree within 1px, and the computed font size,
padding and gap must match. Each UI PR records the table. There are no screenshots (Ed,
2026-09-23).

## 13. Decisions and deviations

1. **The issuer id is Payroll's origin,** not the handoff's `did:example:meridian-payroll`
   (credential-model §2; #93).
2. **A connection id authenticates call 3** (§2). It's the stand-in for OpenID4VCI's access
   token, and it means one person's wallet can't ask for another's credentials by guessing a
   person id.
3. **The Wallet sends `have`** (§2), settling the intent's open question as Phase 3 describes.
4. **The lost-connection state** (§9, §10) is new. It follows Loop 4's rule that a lost connection
   looks like no connection, and it's built from existing components. It's reachable when
   Payroll restarts while the Wallet doesn't, for example a Payroll-only redeploy. **Confirmed
   (Ed, 2026-09-23).**
5. **`renderMethod` uses a demo type,** `CredDemoIssuerColor`, with one `oklch()` color, and the
   Wallet uses only its hue (§4). **Confirmed (Ed, 2026-09-23).**
6. **Removing an employer keeps received credentials** (§7). They're valid signed credentials the
   person holds, and the Wallet has no "delete credential" feature. A later reconnect sends their
   ids in `have`, so nothing duplicates.
7. **The 30-second window** between page-open checks (§9) isn't in the handoff. It stops the
   redraw from starting a second check, and limits reload traffic.
8. **The stack's `--n` follows the handoff pages, not the CSS comment** (§8).
9. **Benefits doesn't gain Payroll's key this loop,** though the intent listed it. Benefits has no
   trust list yet; the generator adds Payroll to it when Loop 6 creates one.
10. **The script and the JavaScript rule:** the Credentials page becomes the second page with a
    script (§9). The rule is unchanged; the two sentences that say "only the pending pages" are
    updated. **This amends decisions.md; confirmed (Ed, 2026-09-23).**

## 14. Acceptance criteria

1. Running `uv run tools/generate_credentials.py` writes Payroll's key pair, `issuer.json`, the
   Wallet's trust entry for Payroll (`PaystubCredential` only) and `apps/payroll/.env`, and
   re-signs every identity credential with the same ids. No private key is committed.
2. Payroll's `/health` returns 200 on Render with `PAYROLL_SIGNING_KEY` set, and 503 with a reason
   when the key is missing or doesn't match `issuer.json`.
3. `/.well-known/jwks.json` on Payroll serves the public key from `issuer.json`.
4. Every paystub's credential matches credential-model §3: `PaystubCredential`, the origin as
   issuer id, `validFrom` equal to the pay date, no `validUntil`, gross and net pay as
   `MonetaryAmount`, no employee name, and a `CredDemoIssuerColor` render hint. Its header is
   ES256, `payroll-1`, `vc+jwt`.
5. A paystub's credential id is a `urn:uuid:` that differs from the paystub's id and is the same
   on every request and after a restart.
6. A successful connection returns a `connectionId`. `POST /api/credentials` with it returns the
   person's credentials not listed in `have`, newest first, and returns 404 for an unknown id.
7. Payroll's Activity logs "N income credentials sent to your wallet" for each non-empty send, and
   nothing for an empty one.
8. Every paystub page shows "Credential for this paystub" beside the paystub from 60rem and below
   it when narrower, with the credential id, each claim and its claim name, values matching the
   paystub, the signed JWT, and no delivery status, whether or not the person is connected.
9. After connecting, a person reaches Connections with "N income credentials received. View
   credentials." once, and their income credentials are on the Credentials page, verified.
10. Two to five income credentials show as Loop 2's stack, newest at the front. More than five
    draw the five newest plus "View all Income credentials (N)", linking to a page listing all N
    as full cards, newest first. p08 shows six.
11. Each income card with a verified Payroll hint is filled in Payroll's color (hue 255); the
    "View all" ledge stays sand; identity cards stay white; badges keep their own colors.
12. A newly received card shows **New** and the heading reads "N credentials · N new" the first
    time; neither appears on the next visit.
13. Opening the Credentials page never waits on Payroll: held credentials render at once, and a
    check runs in the background at most once per 30 seconds per provider.
14. With JavaScript, the heading shows "Checking issuers" during a check; new arrivals redraw the
    Income section and are announced through the `role="status"` region without moving focus;
    nothing new restores the count silently.
15. Without JavaScript, the page shows what's held and a **Check for new credentials** button that
    re-checks by reloading.
16. When Payroll can't be reached, the Income section shows "Couldn't reach Meridian Payroll to
    check for new credentials." with **Check again**, and Activity logs it once, not on every
    repeat.
17. When Payroll no longer knows the connection, the Wallet shows the person as not connected,
    keeps their income cards, offers **Finish connecting**, and logs nothing.
18. The income detail page shows the issuer bar, status, claims, the summary note, the pay date as
    "Valid from", "Doesn't expire", and the technical details with the JWT. A tampered income
    credential shows the Tampered status and the note under the issuer color.
19. The Wallet's Activity logs "N income credentials received from Meridian Payroll" for each
    arrival, and a separate error entry for any that fail verification.
20. A Payroll-signed identity credential and a state-signed paystub credential are both refused by
    the Wallet's trust check.
21. Only the two pending pages and the Credentials page contain a `<script>`, and no page loads a
    script from a URL.
22. Each app's `cred.css` is its handoff file, byte for byte.
23. Every built page matches its handoff page within 1px at the §12 widths, recorded in a table in
    each UI PR.
24. All three apps' test suites pass in CI, and a live pass on Render connects a person, receives
    their credentials, and shows the matching credential on Payroll's paystub page.

## 15. Reconciliation (plan step)

This is the plan step's reconciliation pass (Loop 2's improvement, kept since — see Loop 4a's
retro, [loop-log.md](loop-log.md)). It checks each handoff page against this design, each
acceptance criterion against the mechanism that satisfies it, and each dependency against Ed's
machine. It was written before any PR, with the side-by-side setup (§16). No findings below
change what §1–14 already say; everything confirms this design as written, with one deviation
already on record (item 1 below) and one small addition to CLAUDE.md.

### Handoff pages against the design

Each page was diffed against the current committed template or stylesheet, whitespace ignored.

| Handoff page | PR | Diff from current | Design | Finding |
|---|---|---|---|---|
| `payroll/cred.css` | 3 | strict superset: 77 new lines (`.record`/`.records`, `.panel--cred`, `.claimlist`, `.disclosure`, `.jwt`) after the Loop 4a baseline | §6 | As designed. |
| `wallet/cred.css` | 4 | strict superset: 100 new lines (stack retunes, `.cred--issuer`, `.cred--income`, `.cred__new`, `.panel__issuer`, `.category__status`/`.spinner`) after the Loop 4a baseline | §4, §8, §9 | As designed. |
| `payroll/activity.html` | 2 | two new `log__item`s ("N income credentials sent…", `neutral` dot; "New connection…", `verified` dot, already built in Loop 4) | §5 | Only the send entry is new; the connection entry already exists. |
| `payroll/paystub.html` | 3 | adds the `.records` two-column grid, the `.record` wrapper around the existing paystub `<section>`, and the whole `.panel--cred` credential section with its `.disclosure` | §6 | As designed. The existing paystub markup is untouched, just wrapped. |
| `wallet/activity.html` | 4 | template-only diff (static page vs. Jinja loop); no new markup shapes beyond the three new entry types in §9's table | §9, §10 | As designed. |
| `connections-connected.html` | 4 | one new line in the Connected band: "N income credentials received. View credentials." | §10 | As designed. |
| `credentials-p01.html`, `credentials-waiting.html`, `credentials-nojs.html`, `credentials-new.html`, `credentials-checking.html`, `credentials-error.html`, `credentials-p08.html` | 4, 5 | new pages: none/one/stack states, the four `data-check` rows, the inline script | §8, §9 | As designed. Checked the stack math directly: p08's page has `--n: 5`, ledge at `--i: 0` ("View all Income credentials (6)"), five cards `--i: 1`..`--i: 5` — matches §8's "`--n` equal to the highest `--i`" exactly. |
| `income-p08.html` | 4 | new page: full `.cred.cred--income.cred--issuer` cards, newest first | §8 | As designed. |
| `income-credential.html`, `income-credential-tampered.html` | 4 | new page: issuer bar, status band, claims, "Valid from"/"Doesn't expire", disclosure | §8 | As designed. The disclosure's `Issuer` line reads the handoff's placeholder `did:example:meridian-payroll`; the built page renders the real issuer id per item 1 below — not a new finding, already decided. |

### Acceptance criteria against their mechanisms

| Criterion (§14) | Mechanism | Test | Check |
|---|---|---|---|
| 1 | generator's `ISSUERS`/`make_keys`/`trust_list` (§3) | new generator test, or a diff of committed output | — |
| 2, 3 | `app/signing.py`, `/health`, `/.well-known/jwks.json` (§3) | new `test_signing.py` | Render `/health` after PR 1 |
| 4, 5 | `app/issuance.py` payload builder (§4) | spec-example test (§11) + field tests | — |
| 6, 7 | `connections.py` connection id, `POST /api/credentials`, Activity (§5) | new `test_issuance_api.py` | — |
| 8 | `paystub.html`'s `.panel--cred` (§6) | new `test_paystub_credential.py` | paystub pair, 375/992px |
| 9 | `run_call_two` → `fetch()`, `link.arrived` (§9) | `test_attempt_call_two.py` additions | credentials-waiting, connections-connected pairs |
| 10, 11, 12 | `credentials.py`, Income section rendering (§8) | new `test_credentials_income.py` | credentials-p01/-p08/-new pairs |
| 13, 14, 15, 16 | `fetch()`, the 30s window, `/credentials/check`, the script (§9) | new `test_issuance_fetch.py`, `test_credentials_check.py` | credentials-checking/-error/-nojs pairs |
| 17 | the `unknown_connection` branch, lost-connection note (§9, §10) | `test_issuance_fetch.py` | — |
| 18 | `income-credential.html` template (§8) | `test_credentials_income.py` | income-credential(-tampered) pairs |
| 19 | Activity entries in `fetch()` (§9) | `test_activity_log.py` additions | activity pair |
| 20 | trust check in `credentials.py`/`verify.py` (§8) | `test_credentials.py`/`test_verify.py` additions | — |
| 21 | script scope (§9) | `test_no_javascript_scope.py` extended | — |
| 22 | adopted `cred.css` files (this section) | `test_stylesheet.py` in both apps | — |
| 23 | all of the above | — | the side-by-side table in each UI PR (§16) |
| 24 | everything | all three suites in CI | live pass on Render (PR 6) |

### Dependencies against Ed's machine

- **No new packages** in any app: Payroll already has `pyjwt[crypto]>=2.9` and
  `cryptography<49`; the generator's inline deps (same two) are unchanged.
- `uv 0.12.15` is on this machine; both apps pin Python 3.12, matching `render.yaml`'s
  `PYTHON_VERSION`.
- **New finding:** uvicorn's `--env-file .env` (§3, "Configuration") fails to start if the file
  doesn't exist. Locally, `apps/payroll/.env` is only written by the generator (§3), so
  CLAUDE.md's "Commands" section gains a line: run the generator once before starting Payroll
  locally for the first time, or after cloning fresh. `.claude/launch.json`'s `payroll` entry is
  unaffected — the file exists once the generator has run, same as `keys/`.
- **Side-by-side tooling only:** `python3 -m http.server` (already in `launch.json`'s `handoff`
  entry) and a browser measuring script (§16), nothing new.

## 16. Side-by-side setup

Set up once, reused by every UI PR (3, 4, 5), per Loop 4a's retro:

- `wallet` (:8001), `payroll` (:8002, pointed at `wallet`) and `handoff` (:8010) run together
  from `.claude/launch.json`.
- A measuring script (kept with the working files, not committed) reads, for a built page and
  its handoff counterpart: the page head's top and height, the Income category (or the
  `.records` panel) and its first card's top and height, and the computed font-size, padding and
  gap of each. Run at 375px and 480px for Wallet pages, 375px and 992px for the paystub, per
  §12. A dry run against the current `credentials.html`/`credentials-p01.html` pair (both
  showing 1 identity credential, no income yet) confirms the script reads matching numbers
  before any Loop 5 code exists.

## 17. Live pass on Render (PR 6, AC 24)

Run 2026-09-23, against both apps' production URLs, once PR 5 (#100) had merged and redeployed.

- **Payroll's health and JWKS.** `GET /health` → `200 {"status":"ok"}` — the deployed
  `PAYROLL_SIGNING_KEY` (rotated after the leak recorded in `no-secrets-in-pr-descriptions`,
  Ed's memory) matches the committed `issuer.json`. `GET /.well-known/jwks.json` serves that
  same rotated public key.
- **Connected p08 (Nadia Haddad) to Shoreway**, live, through the Wallet's UI: call 1, the
  consent screen, **Approve and share**, call 2, then the Wallet's own post-connect fetch — all
  server-to-server between the two Render services. Landed on Connections as connected; the
  Credentials page showed **"6 credentials · 5 new"**, the stack, the ledge ("View all Income
  credentials (6)"), and Payroll's hue on every verified card. Three of the six read "Not yet
  valid" — correctly: their `payDate` is 30 Sep 2026, after today's real date, so `validFrom` is
  in the future. This is a live-clock artifact the loop's own fixed-clock tests don't hit
  (design.md §11, "no sample person produces [an unverified credential] under the fixed test
  clock"), not a bug.
- **Matched one credential end to end.** Payroll's paystub page for Brightpath Early Learning,
  1–15 Sep 2026, showed its `.panel--cred` with id `urn:uuid:111e78a4-d2f7-5529-ac7a-ed39ac63b662`,
  gross `$330.00`, net `$300.71`. The Wallet's income detail page for the same card showed the
  identical id, gross, net, pay period and date, issuer id
  `https://cred-demo-payroll.onrender.com`, and a JWT that verified with the real deployed key —
  the same credential, independently rendered by both apps from the same signed JWT.
- **AC 24 is satisfied:** all three suites passed in CI on every PR (§12), and this pass connects
  a person, receives their credentials, and shows the matching credential on Payroll's paystub
  page, on the deployed services.

Ed confirms separately, from Render's events log, that each PR redeployed only the services
§12 says it should have (PR 1: Wallet and Payroll; PRs 2–3: Payroll only; PRs 4–5: Wallet only;
docs PRs: neither).
