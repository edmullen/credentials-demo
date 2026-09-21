# Design: Loop 2 — Wallet Stands Up

Technical design for [Intent 002](intents/002-wallet-stands-up.md), following
[decisions.md](decisions.md), the credential model in
[credential-model.md](credential-model.md), and the Claude Design handoff in
[design/loop-2/](design/loop-2/README.md).

Covers the loop's six issues, one PR each: #10 (populate the Wallet), #12 (identity
credentials, display and verification), #14 (Connections), #15 (Activity), #26 (apps wake each
other) and #11 (footer and README).

**Link, don't restate.** Claim schemas, verification order, validity windows and failure copy
are defined in `credential-model.md` and are referenced by section here, not repeated. Component
names, tokens and accessibility rules are defined in `design/loop-2/README.md`, likewise.

## 1. Overview

The Wallet becomes a per-person, server-rendered app over committed, signed data. Nothing is
stored at runtime and there is no session: the person being viewed is in the URL, so every page
is a pure function of the path plus the committed seed data.

Three things arrive together:

- **A one-shot generator** under `tools/` creates key pairs for the four states, signs an
  identity credential for each of the 23 people who has one, tampers two of them, and writes the
  Wallet's data directory. Output committed; private keys gitignored.
- **The Wallet gains five screens** — credentials home, credential detail, Connections, Activity
  and the person switcher — built from the handoff's mockups.
- **All three apps** gain the demo footer and a startup ping to their peers.

Loop 0's structure is unchanged: three independent uv projects, one matrix CI job, three Render
services, no app reading outside its own directory, no JavaScript and no bundler. The parts of
Loop 0's design that still govern this loop — monorepo layout, per-app `cred.css`, CI, and the
Blueprint — are unchanged except where §9 says otherwise. Loop 0's own design document is in git
archived beside its handoff at
[design/loop-0/design.md](design/loop-0/design.md).

## 2. What the Wallet owns (#10, #12)

Per the monorepo rule, the Wallet gets its own copy of the slice it needs. It is generated, not
hand-edited:

```
apps/wallet/app/data/
├── people.json        # the 25 people: the switcher's rows and each person's display identity
├── credentials.json   # personId → list of signed JWT strings (23 people, one each)
└── trust.json         # issuer id → name, trustedFor, public keys (JWK)
```

- **`people.json`** carries only what a screen shows: `id`, `givenName`, `familyName`,
  `initials`, and `locality` + `region` for the switcher's "Paterson, NJ". It does **not** carry
  an identity status. The switcher's badge is derived by verifying, exactly as the credential
  screens do (§4) — a `tampered` field the app trusted would be the thing #12 rules out.
- **`credentials.json`** maps a person to their credentials as opaque JWT strings. A person with
  no credential has an empty list; Ray Miller (p24) and Megan Doyle (p25) are the two.
- **`trust.json`** is the trust list shape from
  [credential-model §2](credential-model.md#2-trust--issuers-keys-and-verification): four state
  issuers, each `trustedFor: ["IdentityCredential"]`, each with its P-256 public key as a JWK
  with a `kid`. Payroll's and Benefits' entries arrive in Loops 5 and 6.

### Photos come out of the credential, not out of a file

The Wallet stores **no photo files**. The `image` claim is a `data:` URI inside the signed
payload ([credential-model §3](credential-model.md#3-claim-schemas)), so the template renders
`src="{{ claims.image }}"` directly and the alt text is the person's name, which the Wallet
supplies.

This is the one place where being faithful to the credential model is also the simplest build,
and it is what makes Carmen Diaz's tampered credential demonstrate anything: the face on screen
is the substituted one, and the signature fails because the signed value was something else. A
photo served from `/static/` would be a picture the signature never covered.

The mockups reference `photos/p08.jpg` because they are standalone files that have to render in
a browser with no server. Every other page-level link in the mockups is relative for the same
reason (§5).

## 3. The credential generator (#12)

`tools/generate_credentials.py`, a self-contained uv script run by hand from the repo root, like
`tools/generate_sample_data.py`:

```bash
uv run tools/generate_credentials.py
```

It reads `tools/sample_data/generated/people.json` and `tools/sample_data/photos/`, and writes
`keys/` plus the Wallet's three data files. Nothing runs it at build or deploy time, which is what
keeps it on the right side of the "one-shot generators yes, sync scripts no" rule
([decisions.md](decisions.md)).

### What it does

1. **Key pairs.** One ES256 (P-256) pair per state — New Jersey, Michigan, New York, Ohio —
   with `kid`s `nj-1`, `mi-1`, `ny-1`, `oh-1`. Private keys are written to `keys/` as JWK JSON,
   gitignored. Public keys go into `trust.json`.
2. **One identity credential per person with `identity != "none"`.** Payload per
   credential-model §3, built from the person's record: schema.org claim names
   (`givenName`, `familyName`, `birthDate`, `image`, `address`), where the sample data's
   `street` / `locality` / `region` / `postal_code` become `streetAddress` /
   `addressLocality` / `addressRegion` / `postalCode`, and `county` passes through as the one
   documented extension.
3. **Signs it** as a JWT with `alg: ES256`, `typ: vc+jwt` and the issuing state's `kid`. The
   payload *is* the credential — no `vc` wrapper, no `iss`/`sub`/`exp` (credential-model §4).
   The issuer is the person's own state: `did:example:state-of-new-york` for Victor Moreno, and
   so on.
4. **Tampers two credentials, after signing**, per the `tamper` block the sample data already
   carries — the generator reads it, it does not choose:
   - **p22 Victor Moreno (`kind: address`)** — signed with his real Staten Island, NY address,
     then the payload's `address` is replaced with the `claimed_address` (Elizabeth, Union
     County, NJ) and re-encoded with the original signature. The screen then shows an NJ address
     on a credential issued by the State of New York.
   - **p23 Carmen Diaz (`kind: photo`)** — signed over a placeholder image, then the payload's
     `image` is replaced with her real photo. The face shown is hers, and the signature no
     longer matches ([sample-data.md](sample-data.md)). The placeholder is a small base64 JPEG
     constant in the generator, so no extra file joins `tools/sample_data/photos/` and the
     sample-data generator's curated-placement checks are untouched.

   Both are payload substitutions with the header and signature left alone, so verification
   fails at check 3 for a genuine cryptographic reason.
5. **Dates.** `validFrom` is spread deterministically across the first half of 2026 from the
   person's id and `validUntil` is four years later, per credential-model §5. Fixed in committed
   data, so nothing expires mid-demo and no test depends on today's date.
6. **Credential ids** are `urn:uuid:` values derived with **uuid5** from the person id and
   credential type, the same technique the sample data uses for `subjectId`. Re-running the
   generator issues new keys and new signatures but the same ids, so detail-page URLs survive a
   regeneration.

### Keys are disposable, not precious

Re-running the script replaces every key and every signature. That is the documented posture
(credential-model §2, "Keys are disposable"): losing `keys/` costs one run and one commit. The
script prints nothing to paste into Render this loop — Payroll and Benefits do not sign anything
until Loops 5 and 6, so their keys, the `/health` self-check and `/.well-known/jwks.json` are
deliberately out of scope here. The script is written so those issuers are added as data.

## 4. Verification (#12)

A module inside the Wallet — `app/verify.py` — that takes a JWT string and the trust list and
returns an outcome plus the decoded claims. It implements
[credential-model §2](credential-model.md#2-trust--issuers-keys-and-verification)'s four checks
in order, stopping at the first failure:

| # | Check | Failure outcome |
| --- | --- | --- |
| 1 | `issuer.id` is in the trust list | Unrecognized issuer |
| 2 | that issuer's `trustedFor` includes the credential's type | Unrecognized issuer |
| 3 | the header's `kid` names one of that issuer's keys and the signature verifies | **Tampered** |
| 4 | now is within `validFrom` / `validUntil` | Expired, or Not yet valid |

All four pass → **Verified**. Checks 5 and 6 belong to presentations and have no caller yet.

Implementation notes:

- **PyJWT with the `crypto` extra** does ES256 and reads JWKs directly
  (`jwt.algorithms.ECAlgorithm.from_jwk`). It is the smallest dependency that covers signing in
  the generator and verifying in the app.
- The claims for checks 1, 2 and 4 are read from the payload **without** trusting it, then
  check 3 decides whether any of it can be believed. That ordering is what lets a tampered
  credential still be displayed as received, which the design requires.
- PyJWT's own `exp`/`nbf` handling is not used, because the credential carries `validFrom` and
  `validUntil` instead of registered claims (credential-model §4). Check 4 is ours.
- The outcome is an enum, not a string the template matches on, so adding an outcome is a
  mapping change.

### Outcome → badge → message

One table drives the badge variant, its glyph and its sentence. Variants and glyphs are the
handoff's ([design/loop-2/README.md](design/loop-2/README.md) §1–2); the copy is the handoff's
revision of credential-model §5.

| Outcome | Variant | Glyph | Status band | Message |
| --- | --- | --- | --- | --- |
| Verified | `badge--verified` | `&#10003;` | `panel__status--verified` | Nothing in this credential has changed since {issuer} issued it. |
| Tampered | `badge--error` | `&#10005;` | `panel__status--error` | Something in this credential was changed after {issuer} issued it, so it can't be trusted or used. Ask {issuer} for a new one. |
| Expired | `badge--caution` | `!` | `panel__status--caution` | This credential expired on {date}. Ask {issuer} for a new one. |
| Not yet valid | `badge--caution` | `!` | `panel__status--caution` | This credential can't be used until {date}. |
| Unrecognized issuer | `badge--unknown` | `?` | `panel__status--unknown` | This wallet doesn't recognize {issuer}, so it can't check whether this credential is genuine. |

`badge--neutral` with an en-dash glyph is not an outcome — it is the switcher's **No credential**
row, the absence of a credential rather than the result of checking one.

Only Verified and Tampered are reachable from committed data. The other three are covered by
tests that mint credentials with throwaway keys (§10), which is how CI exercises all five without
committing a credential that expires.

## 5. Routes and templates

The person is in the path, so no cookie and no server state, and a URL survives a Render
spin-down (Intent 002).

| Route | Screen | Mockup |
| --- | --- | --- |
| `GET /` | 303 redirect to `/p/p01/credentials` | — |
| `GET /p/{person_id}/credentials` | Credentials home, or the empty state | `credentials.html`, `credentials-empty.html` |
| `GET /p/{person_id}/credentials/{credential_id}` | Credential detail | `credential-detail.html`, `credential-detail-tampered.html` |
| `GET /p/{person_id}/connections` | Connections | `connections.html` |
| `GET /p/{person_id}/activity` | Activity | `activity.html` |
| `GET /p/{person_id}/switch` | Person switcher | `person-switcher.html` |
| `GET /health` | unchanged from Loop 0 | — |

- `{credential_id}` is the credential's UUID without the `urn:uuid:` prefix. Stable across
  regeneration (§3), and it scales to Loop 5's many paystubs without a route change.
- An unknown `person_id`, or a `credential_id` that isn't that person's, returns **404**. A
  credential id that belongs to someone else is a 404 rather than a redirect: there is no
  sign-in, but the URL shape should not imply one person's wallet can address another's.
- `/` redirecting to the first person means the landing experience is a populated wallet. The
  switcher is one click away in the footer, on every page.

### Templates

`base.html` is extended, not replaced. Changes:

- Nav becomes **Credentials · Connections · Activity**, "Help" removed (#14). Each item carries
  `aria-current="page"` when active, in both the inline nav and the `<details>` panel, so the
  nav needs the active screen and the person id in its context.
- The brand mark gains `header__mark--wallet`; the brand and every nav link point at real routes
  for the current person.
- `.initials` takes the viewed person's initials and `aria-label` — replacing Loop 0's
  hard-coded "Avery Mullen", who leaves the project here.
- The footer becomes the two-part note and aside (§7), with the aside linking to the switcher.
- The stylesheet link stays the literal `/static/cred.css`. The mockups' `href="cred.css"` and
  their relative page links (`credentials.html`, `photos/p08.jpg`) are artefacts of being
  browsable as files; every one becomes a real route or a data URI.

`SITE` stays for what is genuinely per-app (theme, brand, fonts). Per-person and per-screen
values are passed per request, not folded into it.

One new page-level component the templates rely on: `.back`, the "All credentials" link at the
top of the detail screen.

## 6. Screens

Copy, class names and ARIA attributes come **verbatim from the mockups**, so each app's
`cred.css` applies without edits — the same rule as Loop 0.

### Credentials home (#10, #12)

Eyebrow, `<h1>Your credentials</h1>`, then one `.category` section per category. Identity holds
the person's credential as a `.cred` card: `Issuer:` eyebrow with the issuer's display name from
the credential, the status badge opposite, then the photo beside name and address, a rule, and a
footer row with `Valid until {date}` and the **Details** affordance. The whole card is the link.

The **Income** category renders in its waiting state (`.category--waiting`, `None yet`, one line
of `.category__waiting-note` copy). Kept: Loop 5 is two loops away, and the row is what shows
the grouping already exists.

Where a person holds no credential, the Identity category renders the `.empty` slot with a real
`<button disabled>Add Identity</button>` — never a link with `aria-disabled`. Reachable at
`/p/p24/credentials` and `/p/p25/credentials`.

The `.stack-cards` component ships in `cred.css` but no Loop 2 page renders a stack; nobody holds
two credentials yet.

### Credential detail (#12)

One `.panel`: a full-width status band carrying the badge and its message, then `.panel__section`
rows — claims beside the photo, address, the validity pair — and `.disclosure` last, holding the
credential id, issuer identifier, `type`, the raw `validFrom`/`validUntil` and the JWT in a
scrollable `.jwt` block.

Labels are plain language ("Date of birth", "ZIP code"), and values are formatted for reading:
`birthDate` as "2 September 1991", the validity pair as "Valid from 15 January 2026", and the
state as its full name. That last one needs a USPS-code → name map in the Wallet — display text,
which the Wallet composes and no issuer signs.

A tampered credential shows the same sections with the claims **as received**, plus the
`.panel__note` row saying so, and a second note inside the disclosure naming the key the check
failed against.

### Connections (#14)

Heading, one line of purpose, and the `.empty` slot with a disabled **Find your employer**. Loop 4
replaces the slot's contents; the surrounding screen does not change.

### Activity (#15)

Heading, one line of purpose, one day group, **one** `.log` item: `2:14 PM` / "New connection to
Meridian Payroll established". The mockup's five items are illustrative; the issue's single item
is the requirement, and Loop 2 generates no events.

The day heading is hard-coded and will read as a fixed past date. That is accepted for a
placeholder Loop 4 replaces — a computed "today" would imply the log is live, which is a worse
lie than a stale date.

The marker dot stays neutral. Whether it should take the status palette is the handoff's open
question, and it belongs to Loop 4, when there are events to colour.

### Person switcher (#10)

`Demo control` eyebrow, `<h1>Switch person</h1>`, and a flat `.people` list of all 25 rows in
`p01`–`p25` order: small initials, name, "Locality, ST", and the badge that says what the person
demonstrates — Verified (21), Tampered (2), No credential (2). The viewed person's row is tinted
and carries `aria-current="page"`. Rows are links, so the selected person changes by URL like
everything else.

Each row's badge is the result of verifying that person's credential, not a field read from
`people.json` (§2). Twenty-five verifications per request is a few milliseconds of ES256 and
needs no caching at this size.

## 7. Footer and README (#11)

**Footer, all three apps.** The wallet mockup's footer is the two-part row: `.footer__note` at
`flex: 3` carrying the demo statement and the repo link, `.footer__aside` at `flex: 1` carrying
**Switch person**.

Payroll and Benefits get the same statement in their existing footer markup, without the aside —
neither has a person to switch, and `.footer__note` / `.footer__aside` exist only in the wallet's
`cred.css`. Porting the two classes into the other two copies is allowed (three independent
files, no sync) but buys nothing this loop.

**The copy is the mockup's, verbatim:** "**This is a demo.** For more info,
[view this repo.](https://github.com/edmullen/credentials-demo)" Decided 2026-09-21 — that is
enough detail for a footer, and the copy-verbatim rule holds.

It follows that the **README carries the full statement**, not an abridged one. The footer says
where to look; the README is what it points at, and it is the only place that spells out what is
fictional.

**README.** Replaced, per #11: what the project is, that it is a fictional demonstration whose
people, employers, agencies, programs and credentials are invented and whose identity photos are
AI-generated faces of people who do not exist, links to the three live apps, and a link to
`docs/decisions.md`. `docs/` changes redeploy nothing.

## 8. Waking the other two apps (#26)

Each app, on its own startup, fires a request at the other two apps' `/health` and does not wait
for the answer.

- **FastAPI `lifespan`**, one `asyncio.create_task` per peer, `httpx.AsyncClient` with a short
  timeout (about 5s). Every exception is swallowed: a peer being down must never stop an app
  starting, and Render's health check must not see a slow startup.
- **Configuration** is two environment variables per app, naming the other two origins —
  `PAYROLL_URL` and `BENEFITS_URL` in the Wallet, and so on. Set as plain values in
  `render.yaml` (they are public URLs, not secrets). Loop 4 needs the Wallet → Payroll one
  anyway.
- **Unset means no-op.** Locally and in CI no URLs are set, so nothing is pinged and no test
  touches the network. Tests that need the behaviour drive the lifespan explicitly with a stub.
- It cannot loop: an app pings only on its own startup, and waking an app that is already awake
  does not restart it.
- Server-side only, so the no-JavaScript rule is untouched; an HTTP call to another app is not
  reading outside the app's directory, so the monorepo rule is untouched too.

`httpx` moves from the dev group into runtime dependencies in all three apps.

## 9. Dependencies, configuration and deployment

| Change | Where | Why |
| --- | --- | --- |
| `pyjwt[crypto]` added | `apps/wallet` runtime | Verification (§4) |
| `cryptography<49` pinned | `apps/wallet` runtime, `tools/generate_credentials.py` | Versions 49 and later publish no Intel-Mac wheel (§12, item 4) |
| `httpx` moved dev → runtime | all three apps | Peer wake (§8) |
| `PAYROLL_URL`, `BENEFITS_URL`, `WALLET_URL` | `render.yaml`, two per service | Peer wake (§8) |
| `keys/` | root `.gitignore` | Private keys never in git |

Unchanged: `.python-version` and `PYTHON_VERSION`, the CI workflow (no `paths:` filters, no
cancellation on `main`, `ci-passed` the one required check), `rootDir` and `buildFilter` per app,
`autoDeployTrigger: checksPass`.

Deploy scope behaves as designed: generated data under `apps/wallet/app/data/` redeploys the
Wallet only; the footer change touches all three apps and redeploys all three; the README and this
document redeploy nothing.

## 10. Tests

Per app, from the app's own directory, as Loop 0 (`cd apps/wallet && uv run pytest`).

**Wallet — verification**, the part worth testing hardest, against committed data:

| Case | Assertion |
| --- | --- |
| Every one of the 23 credentials | decodes, and its outcome is exactly the one the sample data implies |
| p08 (and the other 20) | Verified |
| p22, p23 | Tampered — failing at check 3, not flagged |
| p24, p25 | no credentials at all |
| Synthetic, throwaway keys | Expired, Not yet valid, Unrecognized issuer, and issuer-not-trusted-for-type |
| Any credential with one payload byte altered | Tampered |

**Wallet — routes:** each of the five screens returns 200 HTML for a person who has a credential
and for one who does not; `/` redirects to `/p/p01/credentials`; an unknown person and a
mismatched credential id return 404; the switcher lists 25 rows with one `aria-current="page"`;
the detail page contains the badge label and the message for its outcome; every page links
`/static/cred.css` and contains no `<script>`.

**All three apps:** `/health` still returns `{"status": "ok"}`; the footer contains the demo
statement; startup with no peer URLs set performs no request.

No test uses a real private key, and no test depends on the current date.

## 11. Build order

Six PRs to `main`, one per issue, merged as each finishes. A closing keyword goes only in the PR
that finishes its issue.

1. **#11** — footer and README. Touches all three apps, depends on nothing, and gets the demo
   disclaimer live first.
2. **#26** — peer wake. Also all three apps, also independent.
3. **#10** — the generator's `people.json` output, the person-in-the-URL routes, `base.html`, the
   switcher, and Connections/Activity-shaped placeholders only insofar as the nav needs them.
4. **#12** — keys, signing, tampering, `trust.json`, verification, the credentials home, the
   empty state and the detail screens. The loop's substance, and the only PR that needs #10 first.
5. **#14** — Connections.
6. **#15** — Activity.

#14 and #15 are small and independent; they come last so the nav they join is already real.

## 12. Decisions and deviations

Nothing here is left open; each item records what was settled and why.

1. **Decided: the footer keeps the mockup's copy.** The question was whether "**This is a
   demo.** For more info, view this repo." is enough, given that #11 asks the footer to say the
   people, employers, agencies and credentials are invented and that the credentials naming real
   states make that load-bearing (`decisions.md`). Ed decided on 2026-09-21 that it is: the
   footer stays verbatim, and the weight moves to the README, which #11 also asks for and which
   is the only place that spells out what is fictional (§7).
2. **Decided: the tampered photo is not dimmed.** `design/loop-2/README.md` describes the
   tampered photo at 72% opacity as a supplementary signal, but the handoff's
   `credential-detail-tampered.html` and `cred.css` contain no such rule — the `<img>` carries
   the same classes as the verified page. Ed decided on 2026-09-21 to drop it: photo quality
   varies enough between people that a dimmed photo is not a reliable indicator of anything, and
   a signal a reader can't calibrate is worse than none. The badge, its message and the
   `.panel__note` row carry the meaning, which is what the handoff's own rule — opacity is never
   the signal — already required. Nothing needs building: the delivered files behave this way.
   The divergence is from the handoff README's prose only, and the handoff is a historical record
   that is never edited to match the apps.
3. **`:has()`** is used once, to hide the badge dot when a glyph is present. Kept — every target
   browser has supported it since 2023. The handoff documents the fallback if that changes.
4. **Deviation: `cryptography` is capped below 49.** `pyjwt[crypto]` pulls it in, and 49 and
   later publish no wheel for Intel Macs, so `uv sync` in `apps/wallet` and
   `uv run tools/generate_credentials.py` on Ed's machine fall back to a source build that needs
   OpenSSL and `pkg-config`. Both carry `cryptography<49` (48.0.1 resolves), with a comment saying
   why. Linux — CI and Render — is unaffected. Revisit when the machine changes or a newer
   release ships an Intel wheel.
5. **Deviation: the empty state shows Identity only.** §6 says the Identity category renders the
   `.empty` slot for a person with no credential but is silent on the Income row.
   `credentials-empty.html` has none, so `/p/p24/credentials` and `/p/p25/credentials` follow the
   mockup: no Income category. The waiting row appears only once a person holds a credential.
6. **Deviation: "the" before a state, not before Meridian Payroll.** §4's messages use `{issuer}`,
   but the mockups read "since the State of New Jersey issued it" while the issuer's name is
   "State of New Jersey". A small helper in `app/display.py` adds "the" to names beginning "State
   of", so the sentences match the mockups and Loop 5's "Meridian Payroll" reads correctly.
   Ed considered capitalizing it ("The") on 2026-09-21 and left it as is: every use is
   mid-sentence.
7. **Settled: how the switcher keeps the reader on the same kind of screen.** AC 9 asks for it and
   §5 doesn't say how, since `/p/{id}/switch` carries no origin. The footer's **Switch person**
   link is `/p/{id}/switch?from={screen}`, each row links to that screen for its person, and the
   switcher's own footer link reads "Back to {screen}". Only the three screen names are accepted;
   anything else falls back to Credentials, so the query string can't steer a link elsewhere. A
   query parameter rather than the `Referer` header, so it survives a copied URL.
8. **Settled: switcher badges landed with #12, not #10.** §11 puts the switcher in #10, but §2
   derives each badge from verification, which #12 builds. #10 shipped the rows, links and
   current-row marker; #12 added the badges.
9. **The Wallet took the Loop 2 handoff's `cred.css` in #11.** `.footer__note` and
   `.footer__aside` exist only there, and §7 assumes the Wallet's copy has them. It is a straight
   copy of `design/loop-2/cred.css`; Payroll and Benefits keep theirs.

## 13. Acceptance criteria

1. `uv run tools/generate_credentials.py` writes `keys/` (gitignored) and
   `apps/wallet/app/data/{people.json,credentials.json,trust.json}`, and nothing runs it at build
   or deploy time. Re-running it produces working credentials with the same credential ids and
   the same detail-page URLs.
2. The Wallet holds one signed identity credential for each of the 23 people whose sample-data
   `identity` is not `none`, issued by that person's own state as a `did:example:` issuer, with
   `alg: ES256`, `typ: vc+jwt`, a `kid` in the trust list, and the payload as the credential — no
   `vc` wrapper and no `iss`/`sub`/`exp`.
3. `trust.json` lists the four states, each `trustedFor: ["IdentityCredential"]` with its P-256
   public key. No private key is committed anywhere in the repo.
4. Verification runs credential-model §2's four checks in order and produces all five outcomes.
   Verified and Tampered come from committed data; the other three are proven by tests using
   throwaway keys. No code path reads a `tampered` field to decide a badge.
5. `/p/p08/credentials` shows Nadia Haddad's credential with a **Verified** badge, her issuer,
   photo, name, address and `Valid until` date, matching `design/loop-2/credentials.html`.
6. `/p/p22/…` and `/p/p23/…` show **Tampered**, with the claims as received, the `.panel__note`
   explanation, and the disclosure note naming the failed key. Victor Moreno's page shows the
   Elizabeth NJ address on a credential issued by the State of New York; Carmen Diaz's shows her
   own face. Editing any committed credential by hand flips its page to Tampered.
7. `/p/p24/credentials` and `/p/p25/credentials` show the empty state: the dashed `.empty` slot
   with a real `<button disabled>Add Identity</button>`.
8. Each credential's photo is rendered from the credential's own `image` claim, with the person's
   name as alt text. The Wallet serves no photo files.
9. `/p/{id}/switch` lists all 25 people in `p01`–`p25` order with initials, name, "Locality, ST"
   and a badge — 21 Verified, 2 Tampered, 2 No credential — the viewed person's row tinted and
   carrying `aria-current="page"`. Every row is a link, and following one keeps the reader on the
   same kind of screen for the new person.
10. The footer on every page of all three apps reads "**This is a demo.** For more info, view
    this repo." with the link live, and the Wallet's also carries **Switch person**. Because the
    footer is deliberately brief, the repo README carries the full statement: what the project
    is; that the people, employers, agencies, programs and credentials are invented; that nothing
    here is a real government or payroll service; that the identity photos are AI-generated faces
    of people who do not exist; and links to the three live apps and to `docs/decisions.md`.
11. The Wallet's nav reads **Credentials · Connections · Activity** with no "Help", and the
    active item carries `aria-current="page"` in both the inline nav and the `<details>` panel.
    `/p/{id}/connections` shows the Connections heading and its disabled **Find your employer**
    slot; `/p/{id}/activity` shows the **Activity** heading and one log item reading "New
    connection to Meridian Payroll established".
12. `GET /` redirects to `/p/p01/credentials`. An unknown person id, or a credential id that is
    not that person's, returns 404.
13. Each app pings the other two apps' `/health` on its own startup without waiting for a
    response, fails silently when a peer is down, and does nothing when the peer URLs are unset.
    `render.yaml` sets two peer URLs per service. Starting one app from cold leaves all three
    responding.
14. `GET /health` on each app still returns 200 `{"status": "ok"}`, and `GET /static/cred.css`
    still returns 200 `text/css` from that app's own copy.
15. `uv run pytest` passes in all three app directories; `ci-passed` is green; no test uses a real
    private key, reaches the network, or depends on the current date.
16. No app reads or imports anything outside its own directory, there is no shared stylesheet,
    template package or sync script, and no page contains JavaScript or uses a bundler.
17. Every screen matches its `design/loop-2/` mockup and screenshot at desktop width — copy,
    class names and ARIA attributes verbatim — and switches to the `<details>` menu at 40rem and
    below. Deviations are limited to those recorded in §2, §5 and §12.
18. A merge touching only `apps/wallet/**` redeploys only the Wallet; the README and this document
    redeploy nothing. All three live apps serve their pages fully styled over HTTPS with no
    mixed-content warning.
