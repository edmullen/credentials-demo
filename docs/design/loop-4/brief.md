# Design Brief: Loop 4 — Wallet and Payroll Connect

Requirements for the Claude Design handoff that Loop 4 builds from. Written before design starts;
the handoff itself (`README.md`, `cred.css`, the pages) lands beside this file.

Context: [Intent 004](../../intents/004-wallet-and-payroll-connect.md) ·
[credential model §1](../../credential-model.md), Phases 1–2 · [sample data](../../sample-data.md) ·
[Loop 2 handoff](../loop-2/README.md) · [Loop 3 handoff](../loop-3/README.md)

## 1. What this is

A demo of verifiable credentials across three fictional apps. This loop makes the **Wallet**
and **Meridian Payroll** talk to each other for the first time: a person finds their employer,
asks to connect, and Payroll checks their identity credential before linking the connection to
an existing employee record. Payroll is a **verifier** here, not yet an issuer — it doesn't hand
back a credential until Loop 5.

The story this loop has to tell on screen: *sharing a credential is a request you can see through
before you agree to it.* The consent screen — approving a request that names exactly what's being
handed over — is the piece neither app has needed until now.

**Both apps get real screens this loop.** The connection is a real service call — Wallet asks,
Payroll verifies and links — and the outcome shows on both sides: the Wallet's Connections page
gets its connected-provider state, and **Payroll's own Connections and Activity pages, inert
since Loop 3, become real too** — an employee can see that their wallet is connected, and when.
This is the [Loop 3 brief](../loop-3/brief.md) §5.1a's own expectation, holding as written: "these
two follow that convention until Loop 4 gives them somewhere to go." This is **not** the
Meridian-side admin/employer view named as deliberately unplanned in
[decisions.md](../../decisions.md) — it's the same employee, viewing their own account, the way
they already view their own paystubs.

## 2. Pass depth — medium, with one real design problem

Most of this loop extends components that already exist. Two things are the exception and
deserve real thought, the way the paystub did in Loop 3: the **consent screen** (a genuinely new
interaction — a request the person did not initiate, that they can approve, deny, or find they
can't satisfy) and the **connected-service state**, shared by both apps and designed once.
Everywhere else, **one proposal, not options** — reuse what's there, including the Wallet's
existing empty-state and activity-log patterns for Payroll's new screens (§3).

## 3. What already exists — extend it, don't restart

`cred.css` and the Loop 2 and Loop 3 Wallet pages are **authoritative and already in the repo**,
handed to Claude Design as files.

- **The Wallet theme is fixed**: `data-app="wallet"`, hue 52 (warm amber), `--bg: oklch(0.98
  0.004 70)`, radius 10/16px, Newsreader display face, `.wrap` and header capped at **`30rem`**.
  That cap holds on every new screen here too, including the employer list and the consent
  screen — the Wallet is a phone-shaped app on any display.
- **Connections already exists, as a placeholder** (`connections.html`): a heading, one line of
  purpose, and an `.empty` slot holding a disabled "Find your employer" button. This loop
  replaces the slot's contents and adds everything downstream of it — the button becomes real,
  and the screen gains states for an employer with no connection yet, a pending request, a
  connected provider, and each failure. The surrounding screen (heading, purpose line) doesn't
  change.
- **Activity already exists, as a placeholder** (`activity.html`): one hard-coded day, one
  `.log` item ("New connection to Meridian Payroll established"), neutral marker dot. Loop 2's
  own design record flagged the dot's color as **this loop's open question** — now that there
  are real outcomes to distinguish (connected vs. each failure reason), propose whether the
  marker takes the status palette or stays neutral for all activity regardless of outcome.
- **The credential card (`.cred`) already exists** (`credentials.html`, `credential.html`) —
  issuer, photo, name, address, a `<details>` reveal for the technical envelope. The consent
  screen's "every claim this credential contains" requirement (§5) is the same information this
  card already knows how to show; reuse it rather than inventing a second claims layout.
- **Payroll has neither component yet.** Loop 3's `cred.css` is a superset of Loop 0's baseline
  only — no `.empty`, no `.log` — and its Connections/Activity nav links are still plain `href="#"`
  (`base.html`), with no templates behind them. This loop copies `.empty` and `.log` into
  Payroll's own `cred.css` the same way Loop 3 brought over `.back`, `.people` and `.panel`: same
  component, same rules, Payroll's own copy per the monorepo constraint. **Reuse the patterns
  outright** — the Wallet's "no connections yet" empty state and its activity-log list format are
  proven; Payroll's versions should differ only in copy (an employee's wallet, not a payroll
  provider, is what's being connected to), not in structure.
- **The Credentials home's Income category needs a small update.** Today it reads "Credentials
  from your employer's payroll provider will appear here once you connect" — true only for
  someone not yet connected. Once a person *is* connected but Payroll hasn't issued anything yet
  (true for everyone this loop — issuance is Loop 5), that copy is wrong. Propose the connected-
  but-nothing-issued-yet wording; it's one `<section class="category--waiting">` note, not a
  layout change.

## 4. The consent screen — the one new component

Per [credential model §1, Phase 2](../../credential-model.md#phase-2--connect-to-payroll),
Payroll replies to a connection request with a **presentation request**: a list of credential
types it needs, and within each, the claims it needs. This loop's list always has one entry
(the identity credential), but the screen is a list because Benefits will ask for several in a
later loop — **design the list, not a single-item special case**.

Requirements, all from the credential model and issue #22:
- **Every claim the credential contains is shown**, not just the ones Payroll asked for — mark
  the ones the requester needs, but don't hide the rest. A signed credential is shared whole, so
  the screen should show everything that's actually about to be handed over.
- **Approve and deny apply to the whole request**, not per credential. There's nothing to
  partially approve this loop, but the layout shouldn't suggest otherwise once there's more than
  one requested type.
- **A pending state while waiting on Payroll's reply**, both for the initial connection request
  and for the verification round-trip after Approve. Payroll's Render service can take **up to
  ~20 seconds to respond from cold** — the pending state has to read as normal progress that
  length of time, not stall or look broken partway through. Don't surface *why* it's slow (no
  "server is waking up" copy) — that's an implementation detail, not something a wallet user
  would be told by a real payroll provider.
- **A missing-credential variant.** If the Wallet doesn't hold a requested credential, say so and
  don't offer an Approve button that can't work. Reachable immediately: Ray Miller and Megan
  Doyle have no identity credential and hit this the first time they try to connect (§5).
- **Three outcomes after Approve**, each with its own message back on the Connections screen —
  wording is drafted in
  [credential model §5, "What the person is told"](../../credential-model.md#what-the-person-is-told)
  as a starting point, not final copy:
  - **Connected** — the happy path.
  - **Tampered identity** — the signature doesn't verify. Same kind of failure the Credentials
    home already shows as a badge; the consent flow's version doesn't need a new visual language
    for it, just the right words.
  - **Not an employee** — the credential verifies, but no Payroll employee record carries that
    subject. This is a real, reachable outcome for the demo operator to choose, not a system
    error — it shouldn't look scarier than a validation message.

## 5. Screens

### 5.1 Employer lookup (#13)
Reached from the now-live "Find your employer" button. **A plain list, not a search field** —
15 employers total, which is short enough that a filter would be solving a problem the demo
doesn't have. No JavaScript (§7), so this is its own page, not a modal. Selecting an employer
returns to Connections with that employer now shown and a **Connect payroll** button beneath it.
An employer can also be removed (an icon `X`, per #13) — the Wallet forgets the relationship, no
Payroll call happens.

### 5.2 Connections (#13, #16, #22)
The existing placeholder, extended with states: no employer chosen yet (today's `.empty`, kept
for anyone who hasn't looked up an employer), an employer chosen with an inert **Connect
payroll** button, a pending state once tapped, and a connected state after Payroll confirms.
Each of the three failure outcomes (§4) needs to land back here with the right message — this is
where the person ends up whether the request succeeds or not.

### 5.3 Consent screen (#22)
Per §4. Appears after **Connect payroll** is tapped, once Payroll's presentation request comes
back.

### 5.4 Activity (existing, extended)
Real events replace the single hard-coded placeholder: at minimum, an employer added, an
employer removed, a connection attempted, and each of the three outcomes. Propose the marker-dot
question from §3 here.

### 5.5 Credentials home (existing, small update)
Per §3's Income category note.

### 5.6 Payroll — Connections
New. Under Payroll's own theme (hue 255, Archivo, `.wrap` at `62rem`), reached from the
now-live Connections nav item (`base.html` currently links it to `#`). Per §3, this is a direct
reuse of the Wallet's Connections pattern, not a redesign: a **not-yet-connected** state matching
the Wallet's existing `.empty` copy in shape (adapted so it reads from Payroll's side — a
payroll provider waiting for an employee's wallet, not a wallet waiting for a provider), and a
new **connected** state once the Wallet's request succeeds. The connected state is genuinely new
for both apps (§1) — propose it once and let the same shape inform both, adjusted per theme.
Because each employee record is exactly one person, this page never lists multiple connections
the way the Wallet's might (§6) — it's binary, connected or not.

### 5.7 Payroll — Activity
New, same treatment as 5.6: reuse the Wallet's `.log` list format verbatim, real content
instead of a placeholder. **Only successful connections are logged here**, not failed attempts —
unlike verification failures at the signature step, Payroll doesn't yet know which employee an
unverified credential was even claiming to be, so there's no employee page to attach a failed
attempt to. (The Wallet's own Activity page is where every outcome, success or failure, belongs —
it's the person's own device and their own history.) Propose the entry's wording; something in
the shape of the Wallet's own placeholder ("New connection to Meridian Payroll established") but
told from Payroll's side.

## 6. Facts to design against

- **15 employers**, all fictional, all routed through Meridian Payroll. Five people hold more
  than one — p06, p17 and p25 have two; p07 and p08 have three — so a person's Connections
  screen may need to show more than one employer/connection pair at once. Twenty of the
  twenty-five have exactly one.
- **Ray Miller and Megan Doyle have no identity credential.** They can still look up and choose
  an employer (Phase 1 moves no credential), but hit the missing-credential state the moment
  they try to connect — reachable in this loop, not deferred, as noted in
  [Intent 003](../../intents/003-payroll-stands-up.md).
- **The person's `subjectId` is what actually links the two sides** — it never appears on
  screen; it's how Payroll matches the presented credential to an employee record.
- **State doesn't persist across a service restart** (decided in
  [Intent 004](../../intents/004-wallet-and-payroll-connect.md)). A connection made earlier in a
  demo session can quietly disappear if Payroll (or the Wallet) has been idle and restarts.
  **Open question, not yet settled either way:** should a connection that's gone missing this
  way look any different from an employer that was never connected? Propose a treatment, but
  it's fine to say the honest answer is "no visible difference" — the technical side hasn't
  decided this needs solving yet either.
- **Four states already trusted for identity** (New Jersey, Michigan, New York, Ohio) — nothing
  new here, but the tampered-credential failure can happen to any of them, not just one.

## 7. Constraints

- **No JavaScript and no bundler.** Held since Loop 2's handoff came back with none; still the
  rule. The pending state (§4) needs to work as a real page — most naturally, the Connect/Approve
  action lands on an interstitial page that then continues, rather than anything that needs a
  client-side timer or poll.
- Copy, class names and ARIA attributes are taken **verbatim** into the Jinja templates — write
  them as production strings.
- WCAG AA as in Loops 0–3: 44px minimum targets, visible focus, one `<h1>`, landmarks, real
  `<button disabled>` rather than disabled links, `aria-current="page"` on the active nav item.
- Every page is server-rendered per person, with the person in the URL. No sign-in, no session.
- **Payroll's new screens use Payroll's own theme**, not the Wallet's — hue 255, Archivo, `62rem`
  wrap, per [Loop 3's brief](../loop-3/brief.md) §3. Because `.empty` and `.log` already read
  tokens only and reference no theme, copying them into Payroll's `cred.css` should need no new
  rules, just the class definitions — the existing theme block retints them automatically.
- Nothing may imply this is a real payroll provider or government service. The footer's existing
  demo note carries this; no new claim should undercut it.

## 8. Deliverables

Into `docs/design/loop-4/`, matching the Loop 2 and Loop 3 handoffs' shape: **two** updated
`cred.css` files, one per app (each a superset of that app's current file), one static HTML page
per screen in §5 plus each state called for in §4, a `README.md` documenting new tokens,
components, states and accessibility decisions, and screenshots — the Wallet's at its `30rem`
width, Payroll's at its `62rem`. The handoff is a **historical record** — the repo's apps are
never edited to match it afterwards, so anything that must survive belongs in the README.
