# Design Brief: Loop 5 — Payroll Issues Credentials

These are the requirements for the Claude Design handoff that Loop 5 builds from. The brief is
written before design starts, and the handoff itself (`README.md`, `cred.css`, the pages,
`screenshots/`) lands beside this file.

Context: [Intent 005](../../intents/005-payroll-issues-credentials.md) ·
[issue #19](https://github.com/edmullen/credentials-demo/issues/19) ·
[credential model §1, Phase 3](../../credential-model.md#phase-3--receive-income-credentials) ·
[paystub credential schema](../../credential-model.md#paystub-credential) ·
[Loop 4a handoff](../loop-4a/README.md) · [Loop 4 handoff](../loop-4/README.md) ·
[Loop 2 handoff](../loop-2/README.md)

## 1. What this is

This is a demo of verifiable credentials across three fictional apps. Loop 4 connected the
**Wallet** to **Meridian Payroll**, but the connection doesn't do anything yet. This loop gives
it a purpose: Payroll becomes an **issuer**. It turns each paystub into a signed income
credential, and the Wallet receives, verifies and shows them.

The story this loop has to tell on screen: *the paystub and the credential are two separate
records of the same pay period.* The paystub is Payroll's full document, with deductions and
tax lines. The credential is a small signed claim about it, carrying what a verifier needs
(employer, dates, gross and net pay) and nothing else. The person holds the credential, and
Benefits will verify it in Loop 6.

**Both apps change.** The Wallet gets income credentials: cards, a detail page, and the moment
they arrive. Payroll's paystub page shows the credential it issues for that paystub, next to the
paystub itself.

## 2. Pass depth: medium, with two real design problems

Most of this loop is already designed. **Loop 2's handoff designed the income credential cards
and how several of them stack** (§3), and that CSS is already in the Wallet's `cred.css`, waiting
for data. This loop fills it in. Two things deserve real thought:

- **Recoloring the income cards in the issuer's color** (§4.1). This is the first credential from
  an issuer other than the four states, and the first time a card's color comes from its issuer
  instead of from the Wallet. It's a change to the existing income card, not a new card.
- **Receiving credentials without making the person wait** (§4.2). The Wallet asks Payroll for
  new credentials whenever the Credentials page opens, and Payroll can take up to ~20 seconds to
  answer from cold.

Everywhere else, make **one proposal, not options**.

## 3. What already exists: extend it, don't restart

The pages and `cred.css` files below are authoritative. Ed hands them over as files.

- **The Wallet's current `cred.css`** (`apps/wallet/app/static/cred.css`) and its pages as the
  [Loop 4a handoff](../loop-4a/README.md) left them (`wallet/*.html` there).
- **Payroll's current `cred.css`** (`apps/payroll/app/static/cred.css`) and its paystub page as
  the [Loop 4a handoff](../loop-4a/payroll/paystub.html) left it. Its Activity page follows the
  [Loop 4 handoff](../loop-4/README.md) (`payroll/activity.html` there).
- **The Wallet theme is fixed:** `data-app="wallet"`, hue 52 (warm amber), Newsreader, and a
  **`30rem`** cap on `.wrap` and the header. Every new screen keeps the Loop 4a compact page
  head and step titles.
- **Payroll's theme is fixed:** hue 255, Archivo, and a `62rem` wrap.
- **The income cards and the stack are already designed**, in the
  [Loop 2 handoff](../loop-2/README.md) §3 ("Credential grouping and the stack"). The rules
  (`.stack-cards` and the `--cred-income` tokens) are already in the Wallet's `cred.css`. Take
  them as settled:
  - **One credential in a category shows in full** (`.cred`). **Two or more stack**, Apple
    Wallet-style, oldest at the back and newest fully visible at the front.
  - **Five deep, then a page.** At most five cards are drawn. Each shows a ledge with its
    employer and pay period. The front card also shows gross pay and the badge. With more than
    five, a **"View all Income credentials (6)"** ledge sits at the back and links to a category
    page.
  - **Income cards are warm sand** (`--cred-income`, hue 75); identity cards stay white.
  - **Still to design, as Loop 2's README noted:** the category page behind "View all", a flat
    list of income cards under one heading (§5.2).
- **The identity detail page's panel is the pattern for the income detail page.** It has a
  status band, claims (`.claims`), a validity row and a **View credential details** disclosure
  showing the technical envelope. An income credential should read as the same kind of object,
  holding different claims.
- **The Credentials page's Income category is a waiting note today** (`.category--waiting`),
  with three states: no employer yet, employer chosen, and connected but nothing received.
  This loop fills the category with real cards. The first two notes stay; the third changes
  (§5.1).
- **The Loop 4 pending pages** (`pending.html`, `pending-verify.html`) are the existing pattern
  for waiting on Payroll: a real page, a small inline script that polls, and **Check again**
  as the no-JavaScript fallback.
- **Activity (`.log`)** exists in both apps, with the marker-dot palette settled in Loop 4.

## 4. The two new design problems

### 4.1 The income cards, in Payroll's color

Payroll signs a display hint into each credential, and the Wallet uses it to show the card in
**Payroll's color (hue 255)** instead of Loop 2's warm sand. The technical shape of the hint is
decided later. For the design, assume the credential carries **one issuer color**, and nothing
else.

- **Start from Loop 2's income card and stack.** Their layout and content stay. The question is
  what the issuer color replaces: the `--cred-income` fill, border and "View all" tint, or
  something smaller. Keep it to one clear treatment, applied the same way to a stacked card, a
  full card, the "View all" ledge and the detail page.
- **It must stay generic.** The Wallet applies whatever color an issuer supplies. Payroll is the
  only issuer that supplies one this loop. With no hint, an income card falls back to Loop 2's
  sand. The four states supply none, so **identity cards stay white**.
- **The issuer color must never be confused with a status.** Verified, Tampered and the other
  badges keep their own colors, whatever the issuer's color is. Note: the Wallet's **unknown**
  badge already uses hue 255, the same as Payroll's brand. Make sure the two can't be mistaken
  for each other.
- **Contrast holds.** Text on or next to the issuer color meets WCAG AA. Say in the README how
  the treatment would stay legible for a different issuer hue.

### 4.2 Receiving credentials

The Wallet asks Payroll for new credentials at two moments:

1. **Right after connecting.** The Loop 4 flow ends on Connections, showing Connected. The
   first income credentials are fetched at this point.
2. **Whenever the Credentials page opens**, for anyone connected.

Requirements:

- **The Credentials page never waits on Payroll.** It shows what the person already holds
  straight away. Checking for new credentials happens alongside it. Propose how the page shows
  **checking**, **new credentials arrived** (with a count), **nothing new**, and **couldn't
  reach Meridian Payroll** (with **Check again**). Keep the "nothing new" case quiet: it's the
  most common one.
- **JavaScript is allowed only as progressive enhancement**, as on the pending pages. Without
  it, the page still works: it shows what's held, and **Check again** fetches by hand.
- **Don't explain the delay.** No "server is waking up" copy, as in Loop 4.
- **Right after connecting**, propose whether Connections says what arrived (for example,
  "2 income credentials received") and links to them, or leaves that to the Credentials page.
- **Newly arrived credentials:** propose whether they're marked as new on the Credentials page
  the first time they're shown.

## 5. Screens

### 5.1 Wallet — Credentials page (changed)
The Income category holds real cards, using Loop 2's stack in Payroll's color (§4.1). Design
these states:
- **Connected, with credentials**: p01, a stack of two from one employer, shown below the white
  identity card so both treatments are seen on one page.
- **More than five**: p08 (Nadia) has **six** income credentials from three employers, so her
  stack draws five cards and the **"View all Income credentials (6)"** ledge.
- **Connected, nothing received yet**: the existing "connected" waiting note, reworded, since
  it now lasts only until the first fetch completes.
- **The fetch states** from §4.2.
- **Not connected**: the existing no-employer and employer-chosen notes stay as they are.

No sample person holds exactly one income credential, so the single full-card case needs no
page. Its colors still follow §4.1.

### 5.2 Wallet — All income credentials (new)
The page behind **"View all Income credentials (6)"**, which Loop 2 left undesigned: a flat
list of full income cards under one Income heading, newest first. Page head
`‹ Credentials | <name>`, propose the name. Shown for p08.

### 5.3 Wallet — Income credential detail (new)
Reached from an income card. Same structure as the identity detail page: page head
(`‹ Credentials | <name>`, propose the name), status band, claims, validity and **View
credential details**. The claims come from the
[paystub credential schema](../../credential-model.md#paystub-credential): employer, pay period
start and end, pay date, pay frequency, gross pay and net pay. There's no photo, name or
address: the credential names its subject only by an identifier, which is never shown.
- **Validity:** valid from the pay date, and it **never expires**. Propose how to say that where
  the identity page says "Valid until".
- Add a short line that the credential is **a signed summary of a paystub, not the paystub
  itself**. Deductions and tax lines stay in Payroll.
- **Tampered variant.** No sample person has a tampered income credential, but the Wallet
  verifies every credential it receives, so the state has to exist. Reuse the identity page's
  tampered treatment. Show it with Payroll's color, so the issuer color and the error status
  are seen together.

### 5.4 Wallet — Connections (small change)
Only if §4.2's right-after-connecting proposal adds something here.

### 5.5 Wallet — Activity (extended)
New entry types: credentials received (with a count), and a failed check. Propose the wording
and marker dots, using the Loop 4 palette. Don't log "nothing new": opening the Credentials page
would otherwise add an entry every time.

### 5.6 Payroll — Paystub page (changed)
Add a **credential panel** to each paystub page, showing the income credential Payroll issues
for it:
- The credential's **id** (`urn:uuid:…`) and its **signed claims**, laid out so they line up with
  the paystub figures they come from: gross pay, net pay and the dates.
- **Every paystub has a credential**, whether or not the person has connected a wallet. So the
  panel is always there, with **no delivery status** ("sent", "not sent"). Ed decided this in
  the intent.
- Make the separate-but-aligned relationship visible: the panel should read as a second record
  next to the paystub, not as part of it.
- Propose where it sits on the page (below the paystub, or beside it at `62rem`) and what the
  heading says.

### 5.7 Payroll — Activity (extended)
One new entry type: credentials sent to the person's wallet, with a count. Reuse the existing
`.log` format. Propose the wording from Payroll's side.

## 6. Facts to design against

- **64 paystubs: two per job**, for 1–15 and 16–30 September 2026. Most people have two. p06,
  p17 and p25 have four; p07 and p08 have six, from three employers each.
- **Three people never receive income credentials.** Carmen Diaz (p23) has a tampered identity
  credential, so Payroll refuses to connect her. Ray Miller (p24) and Megan Doyle (p25) have no
  identity credential. Their Credentials pages keep the not-connected notes. Payroll still shows
  a credential on each of their paystubs.
- **Pay amounts come from the sample data.** Format them as the paystub page does, e.g.
  `$1,250.00`, so the two records visibly agree.
- **Runtime state is volatile.** If the Wallet restarts, it forgets what it held, and the next
  fetch brings everything back as new. That's accepted; no special screen is needed.

## 7. Constraints

- **JavaScript only sparingly**, as progressive enhancement over a page that already works
  without it (decisions.md). No framework, library or bundler.
- Copy, class names and ARIA attributes go **verbatim** into the Jinja templates, so write them
  as production strings.
- **Accessibility:** WCAG AA as in Loops 0–4a. That means 44px minimum targets, visible focus,
  one `<h1>` per page, landmarks, and `aria-current="page"` on the active nav item. A status
  change from the background check is announced to screen readers without moving focus.
- **Every page is server-rendered per person, with the person in the URL.**
- **Each app keeps its own `cred.css`**. Wallet changes go in the Wallet's copy, and Payroll's in
  Payroll's.
- **Nothing may imply a real payroll provider or government service.**

## 8. Deliverables

These go into `docs/design/loop-5/`, in the same shape as the Loop 4 and 4a handoffs:

- **Two updated `cred.css` files**, `wallet/cred.css` and `payroll/cred.css`, each a strict
  superset of that app's current file, with new rules in a marked **Loop 5 additions** section.
- **One static HTML page per screen and state** in §4 and §5, in `wallet/` and `payroll/`.
- **An `index.html`** framing every page at its widths, as in Loop 4a.
- **A `README.md`** documenting new tokens, components, states, copy and accessibility
  decisions, with a table listing every page, its person and its screenshots.
- **Screenshots, as PNG files.** This is a required deliverable, not an extra. Loop 4a's handoff
  came without them, and they couldn't be made afterwards. Framing in `index.html` does **not**
  replace them.
  - Put them in `screenshots/`, **one PNG per page per width**.
  - Widths: **every Wallet page at 375px and 480px** (the `30rem` cap). **Every Payroll page at
    375px and 992px** (the `62rem` wrap).
  - **Full page**, top to bottom, not just the visible window.
  - Name them `<app>-<page>-<width>.png`, matching the HTML file, e.g.
    `wallet-credentials-p08-375.png` for `wallet/credentials-p08.html`.
  - Each captures the page as delivered, with fonts loaded and no browser chrome.
  - If PNG export isn't possible, say so at the top of the README, so the gap is seen before
    the handoff is committed.

The handoff is a **historical record**. The apps are never edited to match it afterwards, so
anything that must survive belongs in the README.

**For Ed, before committing the handoff:** check that `screenshots/` holds a PNG for every page at
both widths, and that the README's table lists them.
