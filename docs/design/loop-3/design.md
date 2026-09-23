# Design: Loop 3 — Payroll Stands Up

Technical design for [Intent 003](../../intents/003-payroll-stands-up.md), following
[decisions.md](../../decisions.md), the sample data in [sample-data.md](../../sample-data.md), and the Claude
Design handoff in [design/loop-3/](README.md).

Covers the loop's three issues, one PR each: #17 (populate Payroll), #18 (display paystubs) and
#48 (retest the peer-wake retry, then remove it).

**Link, don't restate.** The people, employers and paystubs are defined in `sample-data.md`;
component names, tokens, copy and accessibility rules are defined in
`design/loop-3/README.md`; the 429 trace is in
[design/loop-2/design.md §12 item 10](../loop-2/design.md#12-decisions-and-deviations). Each
is referenced by section here, not repeated.

Loop 2's design document moves to `design/loop-2/design.md` as this one replaces it, per
[decisions.md](../../decisions.md).

## 1. Overview

Payroll becomes **Meridian Payroll**, an employee self-service portal, built the way the Wallet
was: a per-person, server-rendered app over a committed slice of the Loop 1 sample data, with the
person in the URL and no session. Every page is a pure function of the path plus committed data.

Three things arrive:

- **Payroll's own data slice** — 25 people, 15 employers, 64 paystubs — written by a one-shot
  script and committed. Each employee record carries the person's `subjectId`, which #16 needs in
  Loop 4.
- **Four screens**: the marketing home with one change, the account landing page, the paystub
  detail view, and the person switcher.
- **#48 finishes**: a Render retest shows the retry-on-429 never actually wakes a sleeping
  peer, so the whole peer-wake feature comes out of all three apps rather than being extended.

**Nothing is signed, verified or connected this loop.** Payroll's keys, `/.well-known/jwks.json`
and credential issuance are Loop 5; the Wallet connection and consent flow are Loop 4. Paystubs
here are display only, and Payroll's `cred.css` gains no badge or status vocabulary
([credential-model.md §2](../../credential-model.md#2-trust--issuers-keys-and-verification)).

Loop 0's structure is unchanged: three independent uv projects, one matrix CI job, three Render
services, no app reading outside its own directory, no JavaScript and no bundler.

## 2. Payroll's data slice (#17)

Per the monorepo rule, Payroll gets its own copy of the slice it needs, under
`apps/payroll/app/data/`:

```
apps/payroll/app/data/
├── people.json      # the 25 people: display identity and subjectId
├── employers.json   # the 15 employers, verbatim
└── paystubs.json    # the 64 paystubs, verbatim
```

**`people.json` is a projection.** Each record carries `id`, `subjectId`, `givenName`,
`familyName`, `initials`, `locality` and `region` — what the header, the landing page's `.ident`
block and the switcher's rows render, plus the identifier #17 requires. `initials` is computed
the same way the Wallet's generator computes it (first letter of each name).

It deliberately does **not** carry `birthDate`, `address.street`, `county`, `postal_code`,
`photo`, `photoBrief`, `identity` or `jobs`:

- The first five are personal detail a payroll portal has no screen for, and decisions.md says
  each app keeps only the slice it needs.
- `identity` has no expression in Payroll — there is no verification here and the switcher has no
  badge column (§11, item 7).
- `jobs` is left out so employment has **one** home in this app's data: the paystubs. Every job
  in the sample set has two stubs, so nothing is lost, and the landing page and the switcher
  can't disagree with each other (§11, item 6).

**`employers.json` and `paystubs.json` are byte-for-byte copies** of
`tools/sample_data/generated/`. A verbatim copy is the cheapest thing to trust: checking it is
one `diff`. `paystubs.json` already carries everything a stub renders — `employerName`, `title`,
`payType`, the rate/hours or annual salary, the period, `grossPay`, the four `deductions` and
`netPay` — and `employers.json` supplies the city the employer's name is shown with.

## 3. The data generator (#17)

`tools/generate_payroll_data.py`, a self-contained uv script run by hand from the repo root, like
`tools/generate_sample_data.py` and `tools/generate_credentials.py`:

```bash
uv run tools/generate_payroll_data.py
```

It reads `tools/sample_data/generated/{people,employers,paystubs}.json` and writes the three
files in §2 — two copied, one projected. It is stdlib only (`json`, `pathlib`): no PEP 723
dependency block, nothing to install, nothing to compile.

It **regenerates nothing upstream**: it never reads the hand-written YAML and never writes
`tools/sample_data/generated/` or `docs/sample-data.md`, so `uv run tools/generate_sample_data.py`
and its curated-placement self-checks are untouched. Nothing runs it at build or deploy time,
which keeps it on the right side of the "one-shot generators yes, sync scripts no" rule
([decisions.md](../../decisions.md)). Adding it is a divergence from Intent 003, recorded in §11 item 1.

## 4. Display helpers and derived values (#18)

`apps/payroll/app/display.py` — Payroll's own; the Wallet's copy is not importable and is not
meant to be. Everything here is text Payroll composes for reading. Money is parsed with
`decimal.Decimal`, never a float, because the committed figures are exact decimal strings.

| Helper | Example | Used by |
| --- | --- | --- |
| `short_date("2026-09-30")` | `30 Sep 2026` | pay date, `.paylist__date` |
| `period_short(start, end)` | `16–30 Sep 2026` | `.paylist__period`, the Pay period row |
| `period_long(start, end)` | `16–30 September 2026` | the detail page's `<h1>` and `<title>` |
| `money("1100.00")` | `$1,100.00` | every figure cell |
| `hours("55")` | `55.00` | the hourly earnings row |
| `installment(stub)` | `18 of 24` | the salaried earnings row |
| `employer_place(employer)` | `Trenton, NJ` | `.category__sub`, the Employer party block |

- **`period_short` collapses a single month** — `16–30 Sep 2026`, not `16 Sep – 30 Sep 2026` —
  with an en dash, as the mockups have it. Every committed period sits inside September 2026; a
  period spanning two months falls back to naming both.
- **`installment` is derived from the period start**, not stored: `(month − 1) × 2 + 1` for a
  period beginning on the 1st, `+ 2` otherwise, over the 24 semimonthly installments of the year.
  September's two periods are therefore the 17th and 18th. This is a position in the calendar,
  not a running total, so it does not reintroduce the year-to-date figure #50 defers (§11,
  item 4).
- **`employer_place` appends a literal `NJ`** from a single module constant with a comment.
  `employers.json` carries a city and no region, and all fifteen are in New Jersey
  ([design/loop-3/README.md](README.md), known gap 5); one constant means a
  non-NJ employer is a one-line change rather than a search through templates.

`apps/payroll/app/people.py` and `apps/payroll/app/paystubs.py` load and index the data with
`functools.lru_cache`, as the Wallet's `people.py` does:

- `all_people()` — the 25 records in `p01`–`p25` order, each with `name` and `place` composed.
- `get_person(person_id)`.
- `employers_for(person_id)` — the person's employers, each with its paystubs, grouped by
  `employerId` **in the order that person's stubs first mention each employer** (the source's
  jobs order), stubs within a group newest pay date first. This drives both the landing page's
  sections and the switcher's employers line.
- `find_paystub(person_id, paystub_id)` — `None` when the id is not that person's.

## 5. Routes and templates (#17, #18)

| Route | Screen | Mockup |
| --- | --- | --- |
| `GET /` | Meridian Payroll marketing home | `index.html` |
| `GET /p/{person_id}/` | 303 redirect to `/p/{person_id}/paystubs` | — |
| `GET /p/{person_id}/paystubs` | Account landing | `paystubs.html`, `paystubs-p08.html` |
| `GET /p/{person_id}/paystubs/{paystub_id}` | Paystub detail | `paystub.html`, `paystub-salary.html` |
| `GET /p/{person_id}/switch` | Person switcher | `person-switcher.html` |
| `GET /health` | unchanged from Loop 0 | — |

- **`/` stays the public marketing page** and is not a redirect. Payroll has a front door the
  Wallet doesn't: a payroll company has a marketing site, and Loop 4's employer lookup needs
  somewhere to land (brief §5.1).
- **`{paystub_id}` is the stub's UUID without the `urn:uuid:` prefix**, the same convention Loop 2
  used for credential ids. Stable in committed data.
- An unknown `person_id`, or a `paystub_id` that is not that person's, returns **404** — not a
  redirect, for the reason Loop 2 gives: there is no sign-in, but the URL shape should not imply
  one employee can address another's record.
- `/p/{person_id}/` redirects rather than 404s, so every URL the handoff names
  ([design/loop-3/README.md](README.md), known gap 1) resolves. The route shape
  itself is a deviation from that gap's wording, recorded in §11 item 2.

### Templates

`base.html` is extended, not replaced. It becomes **one header component with two states**, as
the handoff asks (§5):

| | Public (`/`) | Portal (`/p/…`) |
| --- | --- | --- |
| Brand link | `/` | `/p/{id}/paystubs` |
| Nav | Product · Issuance · Documentation · Support, each `href="#"` | Paystubs · Connections · Activity |
| Identity element | `<a class="btn" href="/p/p01/paystubs">Sign in</a>` | `.initials`, `role="img"`, full name as `aria-label` |
| `<details>` panel | the four nav items, then Sign in | the three nav items |
| Footer aside | none | **Switch person** |

The template switches on whether a `person` is in the context. Nav items carry a key, a label and
an href; **Connections' and Activity's href is the literal `#`** until Loop 4 gives them routes,
styled identically to Paystubs — the Loop 0 convention, settled on this loop's mockups in
`7274c80`. `aria-current="page"` marks Paystubs on the account landing page only, in both the
inline nav and the `<details>` panel; no nav item is current on the detail page or the switcher.

Other changes to `base.html`:

- `<title>` comes from a `page_title` block carrying the whole string, because the marketing
  page's title (`Meridian Payroll — verifiable employment credentials`) does not follow the
  `X — Meridian Payroll` pattern the other three do.
- The footer becomes the handoff's two-part row: `.footer__note` always, and a `footer_aside`
  block that renders **Switch person** on portal pages, is overridden to **Back to paystubs** on
  the switcher, and renders nothing on `/`.
- The stylesheet link stays the literal `/static/cred.css`. The mockups' `href="cred.css"` and
  their relative page links (`paystubs.html`, `paystub.html`) are artefacts of being browsable as
  files; every one becomes a real route.

`SITE` keeps what is genuinely per-app — theme, brand name, fonts, the marketing nav. It **loses
`user`**: Rina Kapoor leaves the project here, as Avery Mullen did in Loop 2.

### Stylesheet

`apps/payroll/app/static/cred.css` is replaced wholesale by `design/loop-3/cred.css`. That file's
first 371 lines are byte-identical to the current one — verified, not assumed — so it is a strict
superset and no existing page can change. The Wallet's and Benefits' copies are untouched: three
independent files, no shared stylesheet, no sync script.

## 6. Screens (#17, #18)

Copy, class names and ARIA attributes come **verbatim from the mockups**, so Payroll's `cred.css`
applies without edits.

### Marketing home (#17) — `index.html`

**One change.** The hard-coded `RK` `.initials` becomes `<a class="btn" href="/p/p01/paystubs">Sign
in</a>`, in the same position, repeated as the last item of the `<details>` panel so the door
exists below 40rem. The marketing nav, the heading, the purpose line and the Employer portal card
are untouched. The footer gains the `.footer__note` markup, with no aside.

There is no sign-in form, no session and no **Sign out**: the button is a door, and the footer's
switcher link is how the demo moves between people.

### Account landing (#18) — `paystubs.html`, `paystubs-p08.html`

Eyebrow **Your pay**, `<h1>` the person's name, then `.ident` — "Flemington, NJ" and the
`subjectId` in mono beneath it. The identifier is shown: the person is about to connect a wallet
to this exact account in Loop 4, and one quiet mono line is what lets someone watching the demo
match the two ends (handoff §6).

Then `<hr class="rule">` and **one `.category` section per employer** (§4), each:

- `<h2 class="category__title" id="e-{employerId}">` with the employer's name, the section
  labelled by it via `aria-labelledby`;
- a `.category__sub` line reading `{job title} · {employer city}, NJ` — the job title in the
  data's own sentence case (§11, item 3);
- a `.paylist` of that employer's stubs, newest pay date first: pay date in bold, pay period in
  mono, a hairline chevron, the whole row a link to the detail view.

Twenty of the twenty-five people see one section, and that is what the handoff's full-width
section head is shaped for; nothing needs a different layout for the single-employer case.

The page closes with the static Wallet card — `Coming soon` badge, "Send your pay to your wallet"
— the held place Loop 4 replaces.

### Paystub detail (#18) — `paystub.html`, `paystub-salary.html`

`.back` reading **All paystubs**, eyebrow **Pay statement**, `<h1>` the pay period in long form.
Then one `.panel` read top to bottom, exactly as the handoff's §1 sets it out: the two parties,
the three-up period `<dl>`, the earnings and deductions tables in `.figures__pair`, the net pay
band, and the withholding note once at the foot.

**The figure area is a real table**: `<caption>` per table, `scope="col"` on the column heads,
`scope="row"` on every line label, totals in `<tfoot>`. The amount column already carries a
`This period` head, which exists only so #50 can add `Year to date` beside it without a
relayout.

**Hourly and salaried differ in one column and one row**, same template:

| | Hourly | Salaried |
| --- | --- | --- |
| 3rd column head | `Hours` | `Installment` |
| Row | `Regular` · `$20.00` · `55.00` · `$1,100.00` | `Salary` · `$92,000.00` · `18 of 24` · `$3,833.33` |

Deductions, totals and net pay are identical in structure. The installment value is derived
(§4, §11 item 4).

The `<h1>` is the pay period, so a person with several employers has two stubs per period that
share it. Kept verbatim: the employer is named in the panel's first line directly below, and the
`.back` link says which list you came from. The `<title>` gains the employer name to keep browser
history and tabs distinguishable (§11, item 5).

### Person switcher (#17) — `person-switcher.html`

Eyebrow **Demo control**, `<h1>Switch person</h1>`, and a flat `.people` list of all 25 rows in
`p01`–`p25` order. Each row: `.initials--sm`, then name, the person's employer names joined by
`&middot;`, and "Locality, ST". The employers line wraps rather than truncating, which is what
holds p07's and p08's three names at narrow widths.

**No badge**: there is no verification status in Payroll, and an empty badge column would imply
one is coming. Ray Miller (p24) and Megan Doyle (p25) appear as ordinary employees — Meridian
employs and pays them; what they lack first matters in Loop 4 (Intent 003).

The viewed person's row is tinted and carries `aria-current="page"`. Every row links to that
person's landing page, and the footer aside reads **Back to paystubs**. Loop 2's `?from=` machinery
is not ported (§11, item 9).

## 7. The peer-wake retest, and a correction to Loop 2's finding (#48)

**The retest ran on 2026-09-22 and disproved the premise it was meant to confirm.** All three
services idle, Wallet visited directly. The Wallet's `[peer-wake]` log showed attempts 21–24
against Benefits, five seconds apart (01:49:08–01:49:23 PM), every one a `429
hibernate-rate-limited` — consistent with what design/loop-2/design.md §12 item 10 predicted,
*if* retrying just needed a longer runway. It didn't: that attempt sequence started around
01:47:53 PM, so its 120-second budget expired around 01:49:53 PM with no 200 ever received.
Benefits' own log confirms it: no sign of life (`Waiting for application startup`) until
**01:50:23 PM** — thirty seconds after the Wallet's retry had already given up — and the request
that woke it, visible four seconds later, was a browser `GET /` from Ed's own IP, not a peer
ping. Across the whole idle-to-wake window, not one of the Wallet's automated attempts got
through.

**Loop 2's design.md §12 item 10 called the 429 "documented, expected behavior of the
platform... not a bug," citing Render's docs and community reports.** That claim doesn't hold
up: neither Render's own documentation nor independent write-ups describe a
`hibernate-rate-limited` gate on `/health`-style pings, and the retry built to work around it
(§7 originally, this section before this rewrite) was designed on the assumption that retrying
for longer would eventually get through — which this retest shows is false, not merely
untested. The historical record at `design/loop-2/design.md` is left as written, per
`decisions.md`'s rule that an archived design isn't edited to match what was learned later; this
section is where the correction belongs, since it surfaced during this loop's own build.

**The better-supported explanation is that Render's free tier declines to wake a sleeping
service for requests that look like automated inter-service polling, specifically because
that pattern is how people defeat the spin-down that funds the free tier** — a `robots.txt`
request to a sleeping Render service gets an automatic disallow-all with no wake at all, which
is at least precedent for the platform special-casing bot-shaped traffic at the edge. A genuine
browser visit, by contrast, reliably wakes it (CLAUDE.md's own "retry before diagnosing" note,
and every successful wake observed so far). Whether the signal is the source (another
Render service's network), the client (`httpx`'s default headers, no browser `Accept`/`User-Agent`),
or the frequency, no combination tried during this loop got a ping through — and deliberately
disguising one as a browser to get past the gate would be evading a free-tier anti-abuse
mechanism on purpose, not fixing a bug, so it isn't attempted here.

**#48 closes by removing the feature, not by fixing it.** A mechanism that never once woke a
peer across a full idle-to-wake window isn't a courtesy worth the code it costs to carry — every
app has a background task, two env vars and a test file whose only job is a ping that doesn't
ping anything awake. Removing it is simpler than keeping a known-inert code path around and
explaining why it's there. Concretely:

1. **`app/peers.py` and `tests/test_peers.py` are deleted in all three apps.** `wake_peers()`,
   `_ping()`, the retry loop and its constants, `PEER_ENV_VARS` — gone, not deprecated in place.
2. **Each app's `lifespan` hook goes with it.** `FastAPI(lifespan=lifespan)` reverts to plain
   `FastAPI()`; there is nothing left to run at startup or cancel at shutdown.
3. **`WALLET_URL`, `PAYROLL_URL` and `BENEFITS_URL` come out of `render.yaml`.** Only
   `PYTHON_VERSION` remains per service. Nothing reads these env vars anymore, so leaving them
   configured would be a stale hint that the feature still exists.
4. **`httpx` moves back to each app's dev dependency group.** It was promoted to runtime in
   Loop 2 solely for the peer-wake ping (§8); nothing at runtime uses it now.
   `fastapi.testclient.TestClient` still needs it for `uv run pytest`, so it stays, just in
   `dependency-groups.dev` where Loop 0 originally had it.
5. **Each app's `test_startup_with_no_peer_urls_still_serves_health` test is removed**, along
   with its `from app import peers` import — there's no peer-URL behavior left to assert.
6. **The documented workaround is a person visiting each app directly**, which the README's
   "Live apps" section now says plainly: visit all three before starting a demo, since no app
   can wake the others for you anymore.

## 8. Dependencies, configuration and deployment

**No app gains a dependency this loop; #48 removes one from each app's runtime instead**, per
§7 — `httpx` moves back to `dependency-groups.dev` in all three `pyproject.toml`, where Loop 0
originally had it, now that nothing at runtime calls it. #17 and #18 add nothing. Reconciled
against CLAUDE.md's Intel Mac with no Homebrew — the check Loop 2's retro asked the plan step to
make — there is nothing to install and nothing that could fall back to a source build. Loop 2's
`cryptography<49` problem has no analogue here.

| Change | Where | Why |
| --- | --- | --- |
| `httpx` moves dev ← runtime | `pyproject.toml`, all three apps | Loop 2 promoted it for the peer-wake ping (§8 then); #48 removes that ping (§7) |
| `WALLET_URL`, `PAYROLL_URL`, `BENEFITS_URL` removed | `render.yaml`, two per service | Nothing reads them once `app/peers.py` is gone |

| Unchanged | Why it is worth saying |
| --- | --- |
| `.python-version`, `PYTHON_VERSION` in `render.yaml` | still in step |
| `.github/workflows/ci.yml` | no `paths:` filters, no cancellation on `main`, `ci-passed` the one required check |
| `tools/generate_sample_data.py` and its output | §3 |

Deploy scope behaves as designed: #17 and #18 touch `apps/payroll/**` only, so Payroll redeploys
alone; #48 touches all three apps' `app/main.py` and `pyproject.toml` (plus `render.yaml`, which
Render reads on every deploy but which doesn't itself gate `buildFilter`), so all three
redeploy; `docs/` and `tools/` redeploy none.

## 9. Tests

Per app, from the app's own directory (`cd apps/payroll && uv run pytest`). No test reaches the
network, and none depends on the current date.

**Payroll — the data slice:**

| Case | Assertion |
| --- | --- |
| `people.json` | 25 records, `p01`–`p25`, each with `id`, `subjectId`, `initials`, `locality`, `region` |
| every `subjectId` | matches `urn:uuid:` followed by a UUID |
| the projection | no record carries `birthDate`, `street`, `county`, `postal_code`, `photo`, `identity` or `jobs` |
| `paystubs.json`, `employers.json` | 64 and 15 records; every stub's `employerId` is in `employers.json` and its `personId` is one of the 25 |
| every person | has at least one paystub — Payroll has no reachable empty state |

**Payroll — routes and screens:**

- `/` returns 200, carries **Sign in** pointing at `/p/p01/paystubs`, and no `.initials`.
- `/p/p01/` returns 303 to `/p/p01/paystubs`.
- `/p/p01/paystubs` has exactly one `.category` section with two `.paylist` rows;
  `/p/p08/paystubs` has three, headed Shoreway Supermarkets, Brightpath Early Learning and
  Ridgeline Home & Hardware in that order, two rows each; both show the person's `subjectId`.
- `/p/p01/paystubs/{16–30 Sep id}` shows `$20.00`, `55.00`, `$1,100.00`, the four deduction lines,
  `$144.13`, `$955.87`, an `Hours` column head, and the withholding note exactly once.
- `/p/p09/paystubs/{16–30 Sep id}` shows `Salary`, `$92,000.00`, `18 of 24`, `$3,833.33` and an
  `Installment` column head.
- `/p/{id}/switch` lists 25 rows with exactly one `aria-current="page"`, p08's row naming three
  employers, and every row linking to that person's landing page.
- An unknown person id, and a paystub id belonging to a different person, both return 404.
- Every page links the literal `/static/cred.css` and contains no `<script>`; every portal page's
  footer carries the demo note, and the aside where the mockup has one.

**All three apps:** `/health` still returns `{"status": "ok"}`; `/static/cred.css` returns 200
`text/css` from that app's own copy; the footer carries the demo statement. No test imports
`app.peers` — that module no longer exists in any of the three apps (§7).

## 10. Build order

Three PRs to `main`, one branch per issue, merged as each finishes. A closing keyword goes only
in the PR that finishes its issue.

1. **#17 — Payroll is populated.** The generator and the data slice, the Loop 3 `cred.css`,
   `base.html`'s two header states, the Sign in button, the person-in-the-URL routes, the landing
   page's identity block and Wallet card, the switcher, and the footer. The landing page exists
   and is reachable; it has no paystub sections yet.
2. **#18 — Paystubs display.** The employer sections and `.paylist` on the landing page, and the
   paystub detail view with its figure tables.
3. **#48 — the peer-wake retest**, last, per §7 — confirmed the retry doesn't wake a sleeping
   peer, and the PR that closes it removes the whole feature from all three apps rather than
   extending it further.

#17 before #18 because #18's sections render #17's data through #17's routes. #48 is independent
of both and goes last because the retest wants the deployed services idle, which is easiest once
Payroll's own deploys have finished.

## 11. Decisions and deviations

The reconciliation pass Intent 003 asks for — each mockup against the design text, each acceptance
criterion against its mechanism, each new dependency against Ed's machine. Nothing here is left
open.

1. **Divergence from Intent 003: one new script in `tools/`.** The intent lists `tools/` as
   unchanged. The slice still has to be produced, and decisions.md requires each app to keep only
   what it needs, so `people.json` has to be *projected*, not copied — by hand for 25 records, or
   by a script. §3 chooses the script, because it makes the projection reviewable and repeatable
   and mirrors exactly what `generate_credentials.py` did for the Wallet. It regenerates nothing:
   the intent's substance — "the sample data already exists; nothing is regenerated" — holds.
   Raised rather than assumed; Ed agreed on 2026-09-22, so the intent's `tools/` line is
   superseded for this loop and the script is the design.
2. **Route shape: `/p/{id}/paystubs`, not `/p/{id}/`.** Intent 003 and the handoff's known gap 1
   both write `/p/p01/`. Mirroring the Wallet instead means the nav item "Paystubs" points at the
   screen it names and carries `aria-current="page"` there, the detail view nests under it, and
   Loop 4's Connections and Activity drop in beside it without a route change. `/p/{id}/`
   303-redirects, so every URL the handoff names still resolves and nothing written down is wrong.
   Agreed with Ed on 2026-09-22.
3. **Job titles keep the data's sentence case.** The handoff's `.category__sub` reads "Home Health
   Aide"; the committed title is "Home health aide", and the same handoff's `.stub__party-sub`
   uses the data's case two screens away. Title-casing would need either `str.title()`, which
   turns "QA engineer" into "Qa Engineer", or a hand-maintained map of 26 titles. Sentence case
   everywhere, taking the data verbatim. Ed decided on 2026-09-22 that deviating from the mockup
   on this point is fine; the paystub's own `.stub__party-sub` is the precedent to follow. This
   changes one rendered string in two mockups and nothing else.
4. **The salaried earnings row shows the installment this actually is.** The mockup reads
   `1 of 24` on a 16–30 September statement; the data carries no installment number at all, and
   those two periods are the 17th and 18th of 2026. Derived from the period start (§4), so the
   page states a calendar position rather than inventing a figure — and a position is not a
   running total, so #50's year-to-date deferral is untouched. The column heading
   **Installment** is unchanged. Agreed with Ed on 2026-09-22.
5. **The paystub's `<h1>` stays the pay period; the `<title>` gains the employer.** For p07, p08
   and the three others with more than one job, two statements per period share the heading. The
   heading is kept verbatim — the employer is the first thing in the panel below it — but the
   document title becomes "Pay statement, Pinecrest Home Care, 16–30 September 2026 — Meridian
   Payroll" so history and tabs distinguish them. A deviation from the mockups' `<title>` only;
   nothing visible changes.
6. **`jobs` is not carried into Payroll's data.** Employment has one home in this app: the
   paystubs. Sections group by `employerId` in the order the person's stubs first mention each
   one, which is the source's jobs order and matches both landing mockups and the switcher's rows
   (Shoreway · Brightpath · Ridgeline for p08) — verified against the committed data for all five
   multi-employer people.
7. **No verification status anywhere in Payroll.** `identity` is not carried, the switcher has no
   badge column (handoff §7), and nothing in the Loop 3 `cred.css` adds one. Payroll first
   distinguishes people by credential in Loop 4.
8. **", NJ" is a literal, in one place.** `employers.json` has a city and no region, and all
   fifteen employers are in New Jersey (handoff, known gap 5). One constant in `display.py` with
   a comment saying why, so the day a non-NJ employer appears it is a one-line change.
9. **Loop 2's `?from=` switcher machinery is not ported.** Its point was keeping the reader on the
   same kind of screen across a switch; Payroll has one real screen this loop, so rows link to the
   landing page and the switcher's aside reads "Back to paystubs", verbatim from the mockup. Loop
   4 adds the parameter when it adds a second destination.
10. **`.panel__section:first-child { border-top: 0 }` lands in Payroll's copy only.** The handoff
    amends this Loop 2 rule because the paystub panel opens with a section rather than a status
    band. Payroll takes the handoff's `cred.css` whole; the Wallet's and Benefits' copies are not
    touched, and the Wallet is not "fixed" to match.
11. **Rina Kapoor leaves the project**, as Avery Mullen did in Loop 2. `SITE["user"]` goes, and
    the header's identity element is the Sign in button on `/` and the viewed person's initials
    inside the portal.
12. **No new dependency, in any app or in the generator** (§8). This is the Intel-Mac check Loop
    2's retro asked the plan step to make, and this loop passes it trivially.
13. **Connections and Activity link to `#`**, styled identically to Paystubs — not dimmed, not
    disabled, not badged. Loop 0's convention, settled on this loop's mockups in `7274c80`.
14. **Printing is undesigned**, by decision (handoff, known gap 3). A browser print of the detail
    page is legible and carries the header and footer. Not built, not tested; a print stylesheet
    is a small self-contained addition whenever it is wanted.
15. **No empty state is built**, because none is reachable: every one of the 25 people has at
    least one job and two stubs per job. A test asserts that, so the day the data changes, the
    missing state fails loudly rather than rendering a blank section.
16. **Corrected: the peer-wake retry does not reliably wake a sleeping peer, and the whole
    feature is removed rather than extended.** `design/loop-2/design.md` §12 item 10 treated the
    `429 hibernate-rate-limited` response as a queueing delay a retry could wait out; this loop's
    retest (§7) showed the retry exhausting its full budget with every attempt gated, and the
    peer waking thirty seconds later from a direct browser visit instead. The archived Loop 2
    record is left as written — it reflects what was believed and built at the time — and the
    correction lives here, where it surfaced. Per §7: `app/peers.py`, its tests, each app's
    `lifespan` hook, and the peer URL env vars in `render.yaml` are all removed, and `httpx`
    moves back to a dev dependency in all three apps. The README now tells a person to visit each
    app directly before a demo, which is the only wake mechanism this loop found that reliably
    works.

## 12. Acceptance criteria

1. `uv run tools/generate_payroll_data.py` writes
   `apps/payroll/app/data/{people.json,employers.json,paystubs.json}` and nothing else; it does
   not modify `tools/sample_data/` or `docs/sample-data.md`, and nothing runs it at build or
   deploy time. `employers.json` and `paystubs.json` are byte-identical to their
   `tools/sample_data/generated/` originals.
2. Payroll's `people.json` holds 25 records, `p01`–`p25`, each carrying the person's `subjectId`
   as a `urn:uuid:` value, and none carrying `birthDate`, street address, county, postal code,
   photo, identity status or `jobs`. No app reads or imports anything outside its own directory.
3. `GET /` returns the Loop 0 marketing page with exactly one change: the identity element is
   `<a class="btn" href="/p/p01/paystubs">Sign in</a>`, repeated as the last item of the
   `<details>` panel. The marketing nav, heading, purpose line and Employer portal card are
   unchanged, and there is no sign-in form, session or Sign out anywhere in the app.
4. `GET /p/{id}/` redirects (303) to `GET /p/{id}/paystubs` for all 25 people.
5. `/p/{id}/paystubs` shows the eyebrow **Your pay**, the person's name as the one `<h1>`, their
   "Locality, ST", and their `subjectId` in mono.
6. The landing page carries **one `.category` section per employer**, headed by the employer's
   name with the section `aria-labelledby` it, a `.category__sub` reading
   `{job title} · {city}, NJ` in the data's sentence case, and that employer's paystubs as
   `.paylist` rows newest pay date first, each row a link. `/p/p01/paystubs` shows one section;
   `/p/p08/paystubs` shows three, in the order Shoreway Supermarkets · Brightpath Early Learning ·
   Ridgeline Home & Hardware; all 25 people render without an empty section.
7. The landing page ends with the static Wallet card — `Coming soon` badge and "Send your pay to
   your wallet" — which Loop 4 replaces without moving the rest of the page.
8. `/p/{id}/paystubs/{paystub_id}` renders one statement in full: employer (name, city) and
   employee (name, job title) as the two parties; pay period, pay date and **Semimonthly** as the
   period row; earnings and deductions as two real `<table>`s with `<caption>`, `scope="col"`
   heads, `scope="row"` line labels and `<tfoot>` totals; the four deduction lines federal income
   tax, Social Security, Medicare and state income tax, always in that order; and the net pay band.
9. The earnings table reads `Regular · $20.00 · 55.00 · $1,100.00` under a **Hours** head for an
   hourly stub, and `Salary · $92,000.00 · 18 of 24 · $3,833.33` under an **Installment** head for
   a salaried one, with the installment derived from the pay period and not stored. Figures match
   the committed data exactly, from $240.00 to $4,916.67.
10. The amount column carries a `This period` `<th scope="col">`, so #50 can add a
    `Year to date` head and one cell per row with no CSS change and no relayout. No year-to-date
    figure appears anywhere this loop.
11. The withholding note appears **once**, at the foot of the statement, reading "Withholding on
    this statement is estimated for the demo, using 2025 single-filer federal and New Jersey
    rates. It is not a real tax calculation." No per-line marks, asterisks or badges.
12. The detail page carries a `.back` link reading **All paystubs** that returns to that person's
    landing page, and its `<h1>` is the pay period in long form.
13. `/p/{id}/switch` lists all 25 people in `p01`–`p25` order with small initials, name, their
    employer names joined by `&middot;`, and "Locality, ST" — no badge column. p07's and p08's
    three employers wrap without truncating. The viewed person's row is tinted and carries
    `aria-current="page"`, every row links to that person's landing page, and the switcher's footer
    aside reads **Back to paystubs**. It is reached from **Switch person** in the footer of every
    portal page.
14. Inside the portal the header reads **Paystubs · Connections · Activity** with the viewed
    person's `.initials` (`role="img"`, full name as `aria-label`); Connections and Activity are
    ordinary links to `#`, styled identically; `aria-current="page"` is on Paystubs on the account
    landing page only, in both the inline nav and the `<details>` panel.
15. An unknown person id, and a paystub id that is not that person's, both return 404.
16. **No app pings its peers on startup.** `app/peers.py` and `tests/test_peers.py` are gone from
    all three apps; each `main.py` constructs `FastAPI()` with no `lifespan`; `render.yaml`
    carries no `WALLET_URL`/`PAYROLL_URL`/`BENEFITS_URL`; `httpx` is a dev dependency only, in
    all three `pyproject.toml`. This loop's Render retest showed the retry never woke a sleeping
    peer within its budget (§7) — a platform limitation, not a bug the retry could be tuned
    past. The README's "Live apps" section tells a person to visit each app directly before a
    demo, which is the only wake mechanism this loop found that reliably works.
17. `GET /health` on each app returns 200 `{"status": "ok"}`; `GET /static/cred.css` returns 200
    `text/css` from that app's own copy; `uv run pytest` passes in all three app directories and
    `ci-passed` is green. No test reaches the network or depends on the current date, and no app
    gained a dependency this loop.
18. Every screen matches its `design/loop-3/` mockup and screenshot at desktop width — copy, class
    names and ARIA attributes verbatim — and switches to the `<details>` menu at 40rem and below.
    No page contains JavaScript and nothing uses a bundler. Deviations are limited to those
    recorded in §11.
19. A merge touching only `apps/payroll/**` redeploys only Payroll; #48 redeploys all three; `docs/`
    and `tools/` redeploy none. All three live apps serve their pages fully styled over HTTPS with
    no mixed-content warning.
