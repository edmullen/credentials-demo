# Handoff: Cred Demo — Loop 4a, UX improvements

Design handoff for Loop 4a, answering [brief.md](brief.md). There are two stylesheets, 24 Wallet
pages and one Payroll page:

- `wallet/cred.css` is a strict superset of `apps/wallet/app/static/cred.css`.
- `payroll/cred.css` is a strict superset of `apps/payroll/app/static/cred.css`.

Everything new sits in a marked **Loop 4a additions** section at the end of each file. There's
one documented exception: two Wallet sizes are retuned (§8). No protocol, credential or state
changes.

As in earlier loops, these are design references written in HTML. Copy, class names and ARIA are
production strings; take them verbatim. The handoff is a historical record, so anything that has to
survive is written here.

## Fidelity

**High.** Colours, type, spacing, states and copy are all final. Ed chose the landing page and the
compact page head from three options each (2026-09-23): landing option A with its illustration
slot removed and more space before the blurb, and page head option A. Everything else is one
proposal.

## Files

`index.html` shows every page at 375px and 480px (the Wallet's 30rem cap), and the paystub at
375px and 992px (62rem).

### Wallet (`wallet/`)

| File | Page head | Intro title | Person |
| --- | --- | --- | --- |
| `landing.html` | *(landing, no page head)* | `<h1>` headline | signed out |
| `credentials-start.html` | Credentials | *none* | p01, no employer yet |
| `credentials-chosen.html` | Credentials | *none* | p01, employer chosen |
| `credentials.html` | Credentials | *none* | p01, connected |
| `credentials-empty.html` | Credentials | *none* | p24 |
| `credential-detail.html` | ‹ Credentials \| Identity credential | *none* | p08 |
| `credential-detail-tampered.html` | ‹ Credentials \| Identity credential | *none* | p23 |
| `connections.html` | Connections | You have 0 connections | p01 |
| `employers.html`, `employers-p08.html` | ‹ Connections \| Find your employer | Select your employer | p01, p08 |
| `connections-chosen.html` | Connections | Now connect your payroll | p01 |
| `pending.html` | Connecting to Meridian Payroll | Wait while Meridian Payroll prepares its request | p01 |
| `consent.html` | ‹ Connections \| Request from Meridian Payroll | Do you want to share 1 credential with Meridian Payroll? | p01 |
| `consent-tampered.html` | same | same | p23 |
| `consent-missing.html` | same | You do not have the credential Meridian Payroll is requesting. | p24 |
| `pending-verify.html` | Connecting to Meridian Payroll | Wait while Meridian Payroll checks your identity | p01 |
| `connections-connected.html`, `-p08.html` | Connections | You have 1 connection | p01, p08 |
| `connections-tampered.html`, `connections-not-employee.html` | Connections | Now connect your payroll | p23, p01 |
| `activity.html`, `activity-p23.html`, `activity-p24.html` | Activity | *none* | p01, p23, p24 |
| `person-switcher.html` | Switch person | Choose who to demo as | p08 current |

### Payroll (`payroll/`)

| File | Change |
| --- | --- |
| `paystub.html` | Earnings and Deductions tables each sit in a scroll region |

## Decisions

### 1. Landing page (brief §4.1)

`/` becomes `landing.html`. The page has:

- **Headline**, the page's `<h1>` (`.landing__title`, Newsreader 2.5rem). "Wallet:" sits on its own
  line in `--accent-text`. That's a visual split only: the heading text reads as the brief's
  sentence.
- **Blurb**: `.intro__purpose`, 36px below the headline (Ed asked for more space there).
- **Sign in**: a block `.btn` pointing to `/p/p01/` (Grace Okafor's credentials). Beneath it,
  `.landing__demo` (0.875rem, `--ink-2`) reads "This website is not a real service. It's a demo.
  Learn more here", and "Learn more here" links to the repo.
- **Header**: only the brand and the **Sign in** `.btn`, the Payroll pattern. There's no nav, no
  initials and no Menu, because with no nav there's nothing to disclose, and the button fits at
  320px. The brand links to the landing page.
- **Footer**: unchanged. It has the usual demo note, plus **Switch person** as a demo aid.

### 2. Sign out: one Menu at every width (brief §4.2, Ed 2026-09-23)

The Wallet drops its inline nav. The `<details class="nav-menu">` Menu, which used to appear
only at 40rem and narrower, is now shown **at every width**, so there is one place for navigation
and Sign out.

- **Sign out** is the last item in the Menu panel, as `<a class="nav-menu__signout">`. A
  `--line-2` rule and 8px of space set it apart from the nav items. It links to `/`.
- **The panel is the landmark:** `.nav-menu__panel` becomes `<nav aria-label="Main">` (it was a
  `<div>`), and the hidden `.header__nav` markup is removed from Wallet pages.
  `aria-current="page"` sits on the panel's links.
- **On wide screens**, the panel still spans the header, but its links are padded in so they line
  up with the 30rem column.
- **The initials** stay a static `role="img"` label, as in Loop 4.
- **The brand** still links to the person's credentials while signed in.

The change is confined to the Wallet's copy (`html[data-app="wallet"]`). Payroll keeps its inline
nav.

### 3. Compact page head (brief §4.3), used on every signed-in page

```html
<div class="pagehead">
  <a class="back" href="…">Connections</a>
  <span class="pagehead__sep" aria-hidden="true"></span>
  <h1 class="pagehead__title">Request from Meridian Payroll</h1>
</div>
```

- **The page name carries the page's `<h1>`.** It's in the page head on every page, including
  Credentials and Activity, which have no intro title. The step title is now an
  `<h2 class="intro__title">`, a sibling of the page's other `<h2>`s. The `<title>` element uses
  the step title where there is one, and the page name otherwise.
- **Without a back link**, only the `<h1>` is present.
- **Type:** mono, 0.75rem, weight 700, 0.08em tracking, uppercase, `--ink`. This is the old eyebrow,
  set bold and black.
- **Layout:** one flex row, 44px minimum height, 12px gaps. The divider is a 1px × 20px
  `--line-2` rule. The back link and divider are `flex: none`, and the title is `min-width: 0`.
  At 375px, "Request from Meridian Payroll" wraps inside its own column beside the back link.
  The back link never wraps or moves to its own line.
- **The back link** is the Loop 2 `.back`, unchanged. Its label names the destination page, as in
  the brief's example. The detail page's "All credentials" becomes "Credentials".
- **Removed from the Wallet pages:** the standalone `.back` line, and the `.intro__eyebrow` +
  `<h1 class="intro__title">` pair. `.intro__eyebrow` stays in the stylesheet, because Activity
  still uses it for its day headings.

### 4. Step titles for pages the brief didn't name (brief §4.4)

| Page | Proposal | Why |
| --- | --- | --- |
| Credential detail | Page head "‹ Credentials \| Identity credential", **no intro title** | The panel already leads with the status and the name. Dropping the old name-as-title saves the most height on the longest page. |
| Pending (request) | "Connecting to Meridian Payroll" / "Wait while Meridian Payroll prepares its request" | Tells the person what to do, which is to wait. No back link: the page is a step inside a flow. |
| Pending (verify) | same head / "Wait while Meridian Payroll checks your identity" | as above |
| Person switcher | "Switch person", no back link / "Choose who to demo as" | It's a demo control, not part of Credentials. The footer's "Back to credentials" stays, unchanged. |
| Connections after a failed attempt | "Now connect your payroll" | The person still has an employer chosen and a Try again button. |

The consent page's missing variant uses "You do not have the credential Meridian Payroll is
requesting." (Ed, 2026-09-23).

### 5. Consent page (brief §4.5)

- The page head and title follow the brief. The purpose line now starts "Meridian Payroll runs
  payroll for…", and the rest is unchanged.
- **The decision moves up.** The Loop 4 `<form class="decision">` ("This applies to the whole
  request.", **Approve and share**, **Deny**) now sits between the purpose line and
  `<ol class="request">`. It keeps its markup; only its position changes.
- **Status area: `.panel__status--plain`.** A white band with a `--line` bottom border. Inside, a
  `.cred__top` row puts "Issuer:" and "State of New Jersey" on the left, and the badge on the
  right. The status sentence follows in `--ink-2`. The badge keeps its own green or red tint.
  (The Loop 2 rule that whitens a badge inside a status band is overridden for this variant.) The
  hidden `<h3>Status</h3>` stays. The credential detail page keeps its tinted band.
- **Missing variant: Close request stays after the list.** The list is only one short note, so the
  button is still near the top of the page. Its lead line, "Without it, this request can't be
  completed…", only makes sense once the note above it has said what's missing.

### 6. Credentials page (brief §4.6)

- **Date of birth.** A `.cred__dob` line under the name reads "DOB: 03/11/82" (MM/DD/YY). It's
  0.9375rem, `--ink-2`, with tabular figures.
- **Before any connection** (`credentials-start.html`): Loop 2's note stands. A secondary
  **Find your employer** button inside it (`.category__waiting-note--action`) goes straight to
  the lookup. It's secondary so the note stays quiet next to the identity card.
- **Employer chosen, not yet connected** (`credentials-chosen.html`): **the button doesn't
  stay**, because finding an employer is done. The note reads "You've added Pinecrest Home
  Care. Connect to Meridian Payroll, and your pay will appear here as credentials." Its button is
  **Finish connecting**, a GET link to Connections, where the Connect payroll POST lives. With
  several employers under one provider, name the most recently added one.
- **Connected:** Loop 4's note stands, with no button.

### 7. Person switcher (brief §4.7)

Each row gains a `.people__employers` line under the city and state, reading
"Employer: {name}" or "Employers: {a}, {b}, {c}". The class is lifted from Payroll's copy
(Loop 3), with the same size and colour. The employers are listed in sample-data order. The row
grows to about 80px for three employers.

### 8. Final sizes (brief §4.9)

| Rule | Loop 4 | Loop 4a |
| --- | --- | --- |
| `html[data-app="wallet"] .main` top padding | 28px | **14px** (`--space × 1.75`) |
| `.intro__title` (Wallet) | `clamp(2rem, 6vw, 3rem)` | **2rem** |
| Page head | eyebrow + back line + title stack, about 150px | **one 44px line** |

The top of a page now reads header → 14px → 44px page head → 24px (`.stack` gap) → 2rem step
title. At 375px, the consent page's buttons sit about 330px from the top, against about 520px in
Loop 4.

### 9. Payroll paystub (brief §4.8)

`.panel`'s `overflow: hidden` clipped the `nowrap` figure tables. Each table is now wrapped:

```html
<div class="figures__scroll" role="region" aria-labelledby="fig-earnings" tabindex="0">
  <table class="figures"><caption id="fig-earnings">Earnings</caption>…</table>
</div>
```

- **Touch:** the region scrolls sideways (`overflow-x: auto`).
- **Keyboard:** `tabindex="0"` makes the region focusable, so arrow keys scroll it, and it shows
  the standard focus ring. The region is named by its caption, so a screen reader hears
  "Earnings, region".
- **Scroll cue:** a soft shadow shows on whichever edge has more content. It's CSS-only, using
  `background-attachment: local`. It disappears at each end, and the table looks exactly as
  before when it fits.
- The description column keeps a minimum width of 8.5rem, so it stays readable instead of being
  crushed.

Payroll's headers and every other page stay as they are.

## New tokens

None.

## New components

**Wallet:** `.pagehead` / `.pagehead__sep` / `.pagehead__title` · `.nav-menu__signout` · Wallet-scoped `.nav-menu` at every width · `.landing` / `.landing__title` /
`.landing__lead` / `.landing__demo` · `.cred__dob` · `.category__waiting-note--action` ·
`.panel__status--plain` · `.people__employers` (from Payroll).

**Payroll:** `.figures__scroll`.

## Accessibility

WCAG AA, as in Loops 0–4:

- **Headings:** one `<h1>` per page, the page head title, or the headline on the landing page.
  Step titles are `<h2>`.
- **Landmarks:** header, main and footer landmarks, and the skip link, are all unchanged.
  `aria-current="page"` is where Loop 4 put it.
- **Targets:** every target is at least 44px. That includes the back link, Sign in, Menu, Sign out
  and the scroll regions.
- **The Menu** is a native `<details>`, reachable by keyboard, and its panel is the Main nav landmark.
- **Status** always has a text label and a glyph, and colour is never the only signal.

## Known gaps left to implementation

1. Hrefs are relative page links. Wire them to `/` and `/p/<id>/…`.
2. The Credentials "Finish connecting" wording is a proposal.
3. Timestamps are fixed samples, as in Loop 4.
4. Screenshots: see `index.html`. Each page is framed at the handoff widths, for capture.
