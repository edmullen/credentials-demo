# Design Brief: Loop 3 — Payroll Stands Up

Requirements for the Claude Design handoff that Loop 3 builds from. Written before design starts;
the handoff itself (`README.md`, `cred.css`, the pages) lands beside this file.

Context: [Intent 003](../../intents/003-payroll-stands-up.md) ·
[sample data](../../sample-data.md) · [Loop 0 handoff](../loop-0/README.md) ·
[Loop 2 handoff](../loop-2/README.md)

## 1. What this is

A demo of verifiable credentials across three fictional apps. This loop is **Meridian Payroll**
only: the payroll provider that pays all 25 sample people, and that will issue income
credentials in Loop 5. Loop 0 shipped its marketing home page. Nothing else in Payroll exists.

**The viewer is the employee.** Payroll becomes an employee self-service portal — you are the
person, and you see your own pay. A Meridian-side admin or employer view is deliberately
unplanned, as the Benefits caseworker view already is
([decisions.md](../../decisions.md)).

**Nothing is signed or verified this loop.** No credentials, no badges, no connection to the
Wallet — paystubs are display only. Loop 4 brings the Wallet's inbound connection and Loop 5
turns these paystubs into credentials. Both are near enough that the screens below should have
somewhere for them to go; neither is designed now.

## 2. This is a medium pass — please don't explore options

Loop 2's design pass was the most expensive part of that loop, because it explored alternatives.
This one shouldn't. The component vocabulary already exists and carries forward; there is exactly
one new component (§4), and it has a real-world convention to follow rather than a design space
to search. **One proposal per screen.** Where something genuinely can't be settled without a
choice, say so in the README and pick the one you'd ship.

## 3. What already exists — extend it, don't restart

`cred.css` and the Loop 0 pages are **authoritative and already in the repo**, and are handed to
Claude Design as files. So is the Loop 2 handoff, as the vocabulary to reuse.

- **Payroll's theme is fixed**: `data-app="payroll"`, hue 255 (corporate blue), `--bg: #F2F2F2`,
  radius 6px / 10px, Archivo display face, `.wrap` and header at **`max-width: 62rem`**. Payroll
  is a desktop-shaped app, unlike the Wallet's 30rem phone column — a paystub is a wide document
  and wants the room.
- **Payroll's `cred.css` is the Loop 0 baseline** (371 lines), not the Wallet's (731). Loop 2's
  additions live in the Wallet's own copy, and its new tokens sit *inside the wallet theme
  block*. What comes back here should be a superset of **Loop 0's** file, picking up only the
  Loop 2 components Payroll actually uses — `.back`, `.people`, `.panel`, `.empty`, `.log`,
  `.footer__note` / `.footer__aside` are the likely ones. Don't copy the Wallet's file across,
  and don't bring `--cred-*`, `--stack-peek` or anything else the credential cards need.
- Every component reads tokens only and references no theme. That rule holds: a fourth app should
  still be one `html[data-app="…"]` block.

## 4. The paystub — the one new component

**Follow real paystub conventions.** Layout, grouping and typography should read as a pay
statement to someone who has seen one: earnings and deductions as aligned figure columns, labels
left and amounts right on a tabular figure setting, totals set apart from the lines that make
them up. This is the piece to spend the effort on.

Every field in the committed data, and nothing invented:

| | |
|---|---|
| Employer | name, city |
| Job | title; `hourly` (rate × hours for the period) or `salary` (annual, paid in 24 equal installments) |
| Period | start and end date, pay date, frequency — **semimonthly for everyone** |
| Earnings | gross pay |
| Deductions | federal income tax, Social Security, Medicare, state income tax — four lines, always these four |
| | net pay |

Gross ranges from **$240.00 to $4,916.67** across the set, so the figure column has to look right
at both ends.

**No year-to-date figures**, and this is the constraint most likely to feel wrong while drawing
it, because a real stub has a YTD column beside every figure. They aren't in the data, and
deriving them from the two committed September stubs would print a two-period total labelled as a
year. Deferred to [#50](https://github.com/edmullen/credentials-demo/issues/50). **Design the
figure area so a second column can be added later without redrawing it** — that is what #50 will
need, and the only accommodation asked for.

**Withholding is an approximation, for display only** — 2025 single-filer federal and New Jersey
brackets applied to everyone regardless of where they live, no pre-tax deductions
([sample-data.md](../../sample-data.md#paystubs)). It shouldn't be presented as authoritative.
Propose how the page says so once, quietly, without annotating every line or undermining the
document's credibility as a specimen.

## 5. Screens

Four, all under the payroll theme.

### 5.1 Meridian Payroll home — stays at `/`
Loop 0's marketing page survives as the provider's public front page: a payroll company has one,
and Loop 4's employer lookup needs somewhere to land. **Change one thing only.**

- **The nav links stay exactly as they are** — "Product · Issuance · Documentation · Support".
  They belong to a marketing site and that is what this page is. Don't propose a replacement.
- **The header's identity element becomes a "Sign In" button.** Today it is a hard-coded "Rina
  Kapoor" in `.initials`; that goes. The button leads **straight to the account landing page** —
  `/p/p01/`, following the Wallet, which redirects `/` to `p01` and moves between people through
  the switcher.

**There is no sign-in experience**: no form, no credentials, no session, nothing stored. The
button is a door, not an authentication flow, and it should look like an ordinary product sign-in
rather than a demo control — the demo's honesty lives in the footer note, not in hedged button
copy. Use a real `<a>` styled as a button, since it navigates.

**There is no Sign out.** Nothing to sign out of, and the footer's switcher link already moves
between people. Don't design one.

### 5.1a The header, inside the portal

One header component, two states. Public (`/`) it carries the marketing nav and the Sign In
button; inside the portal it carries:

- **The selected person's `.initials`**, where Sign In sits on the public page, in the existing
  styling — `role="img"` with the person's full name as `aria-label`, as Loops 0 and 2 have it.
  Not their photo: that is a claim inside an identity credential, and two people have none (§6).
- **Three nav links — Paystubs · Connections · Activity** — replacing the marketing four.
  **Paystubs is the account landing page** (§5.2), and is the only one that goes anywhere this
  loop. `aria-current="page"` marks it, as in Loop 2.

This deliberately mirrors the Wallet's **Credentials · Connections · Activity**. The two apps are
different products with the same three-part shape, and Loop 4 gives Payroll a real Connections
screen when the Wallet connects to it.

**Connections and Activity are ordinary links to `#`**, styled exactly like Paystubs — not
disabled, not dimmed, not marked as coming later. This is what the Loop 0 pages already do for
every destination that doesn't exist yet, in the nav and in the marketing page's buttons, and
these two follow that convention until Loop 4 gives them somewhere to go. The same applies in the
mobile `<details>` nav panel, which repeats the items.

### 5.2 Employee account landing — the portal's home
The person's own pay, at `/p/<id>/`. **A section per employer**, headed with the employer name,
each listing that employer's paystubs by pay date, each row linking to the detail screen (#18).

Five people hold more than one employer — p06, p17 and p25 have two; **p07 and p08 have three** —
so this page has one, two or three sections. **Twenty of the twenty-five see a single section**,
and that has to look deliberate rather than like a page missing its other headings. Everyone has
exactly two paystubs per job, both from September 2026, so no list is long and none needs paging.

Whatever else an employee portal's landing page should carry — who you are, where you work, what
you're paid — propose it, knowing Loop 4 adds a connection to the Wallet and Loop 5 adds issued
credentials.

### 5.3 Paystub detail
One paystub in full, per §4, with a way back to the account landing page (`.back`).

### 5.4 Person switcher
Demo scaffolding, as in the Wallet: its own page, reached from the footer, listing all 25 people
so the demo can move between them. Reuse `.people`. **Rows carry the person's employer or
employers, and their town and state** — there is no verification status in Payroll, so the badge
the Wallet's rows carry has no equivalent here. Rows must hold three employer names without
breaking (p07, p08). The selected person is tinted and carries `aria-current="page"`.

## 6. Facts to design against

- **All 25 people have a Payroll account**, including Ray Miller and Megan Doyle, who hold no
  identity credential. Meridian employs and pays them; what they can't do is connect a wallet,
  which first matters in Loop 4. **There is no empty state in Payroll** — everyone has paystubs.
- **64 paystubs, two per job**, 1–15 and 16–30 September 2026, paid on the last day of the period
  or the Friday before if that falls on a weekend.
- **15 employers**, all fictional, all paying through Meridian, each with a city and industry.
- **No photos.** The person's photo is a claim inside their identity credential, not a profile
  picture, and two people have none. The header identity element stays `.initials`, as in Loops 0
  and 2. Longest name is 14 characters.
- Each employee record carries the person's `subjectId` (`urn:uuid:…`), which Loop 4 uses to
  match a Wallet connection to the right employee. It is plumbing — it does not need to appear on
  screen, but say so if you think it should.

## 7. Constraints

- **No JavaScript and no bundler.** Loop 2's handoff came back with none and the repo now treats
  that as a design constraint, not an omission — the mobile nav is a native `<details>`
  disclosure and the brand mark is a CSS-filled `<span>`. Keep it that way.
- Copy, class names and ARIA attributes are taken **verbatim** into the Jinja templates, so write
  them as production strings.
- WCAG AA as in Loops 0 and 2: 44px minimum targets, visible focus, one `<h1>`, landmarks, real
  `<button disabled>` rather than disabled links, `aria-current="page"` on the active nav item.
  A figure table needs real `<table>` semantics with scope'd headers, not a grid of `<div>`s.
- Every page is server-rendered per person, with the person in the URL. No sign-in, no session,
  nothing stored.
- Nothing may imply this is a real payroll provider or a real government service. The footer's
  demo note already says the people, employers, agencies and credentials are invented.

## 8. Deliverables

Into `docs/design/loop-3/`, matching the Loop 0 and Loop 2 handoffs' shape: an updated `cred.css`
(a superset of Payroll's Loop 0 file, per §3), one static HTML page per screen in §5, a
`README.md` documenting new tokens, components, states and accessibility decisions, and desktop
screenshots. The handoff is a **historical record** — the repo's apps are never edited to match it
afterwards, so anything that must survive belongs in the README.
