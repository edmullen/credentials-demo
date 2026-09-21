# Handoff: Cred Demo — Loop 2, Wallet Stands Up

Design handoff for [Loop 2](../../intents/002-wallet-stands-up.md), answering
[brief.md](brief.md). Seven static pages plus a `cred.css` that is a strict superset of the
[Loop 0 handoff](../loop-0/README.md): every Loop 0 token, theme and component carries forward
unchanged, and everything new is appended in a marked section at the end of the stylesheet.

As with Loop 0, these are **design references written in HTML** — the shape the server-rendered
Jinja templates should take, not code to drop in. The handoff is a historical record: the app is
never edited to match it afterwards, so anything that must survive is written down here.

## Fidelity

**High.** Final colours, type, spacing, radii, states and copy. Open any page in a browser; there
is nothing to build. Copy, class names and ARIA attributes are production strings — take them
verbatim.

## Files

| File | Screen |
| --- | --- |
| `cred.css` | Loop 0 stylesheet verbatim + a Loop 2 additions section |
| `credentials.html` | Credentials home, one identity credential (Nadia Haddad, p08) |
| `credential-detail.html` | Credential detail, **Verified** |
| `credential-detail-tampered.html` | Credential detail, **Tampered** (Carmen Diaz, p23) |
| `credentials-empty.html` | Credentials home with no identity credential (Ray Miller, p24) |
| `connections.html` | Connections placeholder |
| `activity.html` | Activity placeholder |
| `person-switcher.html` | All 25 sample people |
| `photos/p08.jpg`, `photos/p23.jpg` | The two identity photos used, copied from `tools/sample_data/photos/` |
| `screenshots/` | Desktop capture of each page |

The brief asked for six screens; credential detail ships as two pages because the status badge
carries the loop's whole argument and both reachable outcomes needed designing.

## No JavaScript

The brief opened the door to script; the design does not walk through it. Every interaction here
is native HTML: the mobile nav and the technical disclosure are `<details>`, the credential stack
is server-positioned CSS, and the person switcher is a list of links. **Loop 2 needs no
JavaScript, and no bundler or framework.**

## Decisions the brief asked for

### 1. The status badge — five outcomes, four variants

[Credential model §5](../../credential-model.md#5-expiration-and-verification-failure) defines
five outcomes. Flattening the four failures onto `error` would say the wrong thing, so two
variants are added:

| Outcome | Variant | Glyph | Reachable in Loop 2 |
| --- | --- | --- | --- |
| Verified | `.badge--verified` | `✓` | Yes — 21 people |
| Tampered | `.badge--error` | `✕` | Yes — 2 people |
| Expired | `.badge--caution` **(new)** | `!` | No |
| Not yet valid | `.badge--caution` **(new)** | `!` | No |
| Unrecognized issuer | `.badge--unknown` **(new)** | `?` | No |

The reasoning: **Tampered is a forgery and keeps `error` to itself.** Expired and Not-yet-valid
are *timing* — the credential is genuine, it is simply being read outside its window — so they
share one caution variant. Unrecognized issuer is neither a pass nor a failure: the wallet is
declining to judge, which earns its own quieter, colder variant.

Two new tokens' worth of colour, chosen to sit beside the existing three at the same lightness
and contrast: caution is hue 85 (yellow, distinct from the wallet's amber accent at hue 52),
unknown is hue 255 (slate). Status colours still **do not retint per app**.

`.badge--neutral` is unchanged and still means "no state yet" — it is what the person switcher
uses for *No credential*, which is the absence of a credential rather than an outcome of
verifying one.

### 2. Label plus icon, never colour alone

Loop 0's badge drew a 7px dot in `currentColor`. That satisfies "never colour alone" only
weakly: four variants of the same dot are one shape. Each variant now carries a **distinct
glyph** in a `.badge__icon` span, so the four are told apart with colour removed entirely.

This is the one place a Loop 0 component is touched:

```css
.badge__icon { font-size: 0.75rem; line-height: 1; }
.badge:has(.badge__icon)::before { display: none; }   /* dot gives way to the glyph */
```

A badge with no `.badge__icon` child still renders exactly as it did in Loop 0. Glyphs are text
characters (`&#10003;`, `&#10005;`, `!`, `?`, `&ndash;`) — no icon font, no SVG.

### 3. Credential grouping and the stack

Credentials group by **category** (Identity, Income, Benefits), and the grouping is the same
markup at any length, so Loops 5 and 6 add a group rather than a layout:

```html
<section class="category" aria-labelledby="cat-income">
  <div class="category__head">
    <h2 class="category__title" id="cat-income">Income</h2>
    <span class="card__meta">6 credentials &middot; Meridian Payroll</span>
  </div>
  …one .cred card, or a .stack-cards stack…
</section>
```

**One credential in a category shows in full** (`.cred`). **Two or more stack**, Apple
Wallet-style: the oldest card sits at the back and highest, each newer card is shifted down and
layered over it, and the newest is fully visible at the bottom. Three treatments were explored;
the approved one is **five deep, then a page**:

- At most five cards are ever drawn. Each reveals a `--stack-peek` (68px) ledge carrying its
  employer and pay period — enough to know what the card is without opening it.
- If more than five exist, a `.stack-cards__more` ledge sits at the very back reading **"View all
  Income credentials (6)"** — the count is the category **total**, not the number hidden — and
  links to a category page holding a plain flat list.
- Nothing expands in place, which is why no script is needed.

The server positions the cards with two custom properties: `--i` on each card (0 = back/top) and
`--n` on the stack (number of cards, plus one when the "view all" ledge is present). The
stylesheet does the arithmetic.

```html
<div class="stack-cards" style="--n: 5">
  <a class="stack-cards__more" href="/credentials/income" style="--i: 0">View all Income credentials (6)</a>
  <a class="stack-cards__card" href="…" style="--i: 1">
    <span class="stack-cards__row">
      <span><strong>Ridgeline Home &amp; Hardware</strong></span>
      <span class="stack-cards__period">1&ndash;15 Sep 2026</span>
    </span>
    <span class="stack-cards__row stack-cards__row--bottom">
      <span class="stack-s">
        <span class="card__meta">Gross pay</span>
        <span class="stack-cards__amount">$320.00</span>
      </span>
      <span class="badge badge--verified"><span class="badge__icon" aria-hidden="true">&#10003;</span>Verified</span>
    </span>
  </a>
  …
</div>
```

Income credentials are the first non-white card: `--cred-income` (a warm sand at hue 75) with
`--cred-income-line` and a lighter `--cred-income-tint` for the "view all" ledge. **Identity
stays white**, per the brief. Benefits gets its own pair in Loop 6.

No Loop 2 page renders a stack — nobody holds two credentials yet. The CSS ships now so Loop 5
adds data, not layout.

### 4. Only identity carries a photo

`.cred__photo` is a 72×90 preview inside the card and `.cred__photo--lg` a 120×150 on the detail
screen, both 6px-radius rectangles — **never cropped to a circle**, because the photo is a claim
inside the credential, not a profile picture. Alt text is the person's name, supplied by the
Wallet. The header identity element stays `.initials`.

## Screens

Structure is Loop 0's: skip link → `.header` → `.main` → `.footer`, one `<h1>`, `.wrap` capped at
`30rem` under the wallet theme. **The 30rem cap holds on every screen, including the 25-person
switcher** — no exception was needed.

### Header

Nav is now **Credentials · Connections · Activity** ("Help" removed), with `aria-current="page"`
on the active item in both the inline nav and the disclosure panel. At the wallet's 30rem column
the viewport is usually below Loop 0's 40rem breakpoint, so what you normally see is the
`<details>` menu, not the inline nav — both are in the markup, exactly as Loop 0 specified.

The brand mark becomes a wallet: `.header__mark--wallet`, a 24×18 rounded rectangle with a white
side pocket and an accent clasp dot, both drawn as `::before`/`::after`. It is a **new modifier
alongside** `.header__mark`, not a redefinition, so the payroll and benefits copies of `cred.css`
are unaffected — each app owns its own copy and no sync is intended.

### Footer

Both footer strings changed. The demo disclaimer now reads, on the left three quarters:

> **This is a demo.** For more info, [view this repo.](https://github.com/edmullen/credentials-demo)

with the person link right-aligned in the remaining quarter (`.footer__note` at `flex: 3`,
`.footer__aside` at `flex: 1`). Loop 0's `.footer .wrap` rule is untouched. This satisfies #11 —
nothing implies a real government service — and the switcher link the brief asked the footer to
gain.

### Credentials home — `credentials.html`

Category heading, then the identity credential as a `.cred` card: issuer above the fold under an
`Issuer:` eyebrow (the issuer is a property of the credential, not of the person), status badge
opposite it, then photo beside name and address, then a hairline and a footer row carrying
`Valid until 15 Jan 2030` and a **Details** link. The whole card is the link; the "Details" text
is the affordance that says so.

An `Income` category follows in a waiting state (`.category--waiting`, `None yet`) with one line
of copy in `.category__waiting-note` — a dashed row deliberately quieter than `.empty`, which is
reserved for the demarcated slots that carry a button. It exists to show that the grouping is already there; drop it if Loop 5 lands soon
after.

### Credential detail — `credential-detail.html`, `credential-detail-tampered.html`

**One tall card** (`.panel`), not a column of cards: a full-width status band across the top
carrying the badge and its message, then divided sections — identity claims beside the photo,
address, validity dates, and the technical disclosure as the last row. Dividers, not gaps.

Plain-language labels throughout ("Date of birth", never `birthDate`). The machinery sits behind
`.disclosure`, whose summary reads **View credential details** in accent ink with a circled
caret that flips down/up on `[open]`, so it reads as interactive: credential id, issuer
identifier, `type`, `validFrom`/`validUntil`, and the raw JWT in a scrollable `.jwt` block.

Copy, revised from credential model §5:

| Badge | Message |
| --- | --- |
| Verified | Nothing in this credential has changed since {issuer} issued it. |
| Tampered | Something in this credential was changed after {issuer} issued it, so it can't be trusted or used. Ask {issuer} for a new one. |
| Expired | This credential expired on {date}. Ask {issuer} for a new one. |
| Not yet valid | This credential can't be used until {date}. |
| Unrecognized issuer | This wallet doesn't recognize {issuer}, so it can't check whether this credential is genuine. |

The tampered page shows the claims as received, with one `.panel__note` row saying so: *"The rest
of this credential is shown as it was received. Because the signature no longer matches, none of
it can be relied on."* The photo is held at 72% opacity — a quiet signal, never the only one.

### Empty state — `credentials-empty.html`

The identity category renders a **demarcated slot** (`.empty`, dashed border) where the credential
would sit, reading *"You have not yet added an Identity credential"* above a centred **real
`<button disabled>`** labelled **Add Identity**. Never a link with `aria-disabled` — a disabled
link still takes focus and still navigates.

### Connections — `connections.html`

Heading, one line of purpose, then the same `.empty` slot: *"You have no connections yet. Your
employer's payroll provider is the first one you'll add."* with a disabled **Find your employer**.
Loop 4 replaces the slot's contents with the employer, a live **Connect payroll** button and a
connected state; the surrounding screen does not change.

### Activity — `activity.html`

Both the nav item and the `<h1>` read **Activity** (#15's "Activities" gets corrected, not the
design). A chronological log: a mono day heading per group, then `.log` items of **time above
message**, each marked by a small 9px circle. The dot is a neutral marker in the accent
family — it carries no meaning yet. Before Loop 4 fills this screen, decide whether the marker
should take the status palette (accent for connections, green for credentials received, red for a
denial) or stay neutral; the design assumes neutral.

The five items shipped here are illustrative. **Loop 2 generates no real events** — the brief's
one sample item is the requirement; the rest are there to show the rhythm.

### Person switcher — `person-switcher.html`

Its own page, reached from the footer. A flat list of all 25 people, each row carrying initials,
name, town and state, and the **status badge that says what the person demonstrates** — Verified
(21), Tampered (2), No credential (2). The currently selected person is tinted
(`--accent-wash`) and carries `aria-current="page"`. Rows are 60px, links not buttons, so the URL
carries the person as every other screen does. Room is left for more metadata per row.

## New tokens

Added inside the wallet theme block, so the other two apps' copies are unaffected:

| Token | Value | Use |
| --- | --- | --- |
| `--surface-2` | `oklch(0.99 0.002 70)` | Inset rows, `.empty` fill |
| `--accent-wash` | `oklch(0.985 0.012 var(--hue))` | Selected switcher row |
| `--cred-income` | `oklch(0.93 0.03 75)` | Income credential card |
| `--cred-income-line` | `oklch(0.85 0.05 75)` | Its border |
| `--cred-income-tint` | `oklch(0.955 0.02 75)` | "View all" ledge |
| `--cred-card-h` | `132px` | Stacked card height |
| `--stack-peek` | `68px` | Visible ledge of a stacked card |

One theme rule changed: `html[data-app="wallet"] .main` now pads `28px` top / `64px` bottom
instead of Loop 0's `56px` / `72px`, so the top gap reads level with `.wrap`'s 24px sides.

## New components

`.back` · `.header__mark--wallet` · `.footer__note` / `.footer__aside` · `.category` ·
`.cred` · `.stack-cards` · `.panel` · `.claims` · `.disclosure` · `.empty` · `.category__waiting-note` · `.log` · `.people` ·
`.badge--caution` / `.badge--unknown` / `.badge__icon`

Every one reads tokens only and references no theme, so a fourth app remains one
`html[data-app="…"]` block.

## Accessibility

WCAG AA, as Loop 0:

- One `<h1>` per page, no skipped levels; `<header>`/`<main>`/`<footer>` landmarks;
  `<nav aria-label="Main">`; every section labelled by its heading, with the status band's
  heading visually hidden.
- `aria-current="page"` on the active nav item and on the selected switcher row.
- Every interactive element ≥ 44px in its smallest dimension; switcher rows are 60px.
- Status is never colour-only: label + distinct glyph, and the tampered photo's opacity is
  supplementary, never the signal.
- Disabled actions are real `<button disabled>`.
- Visible focus everywhere via Loop 0's global `:focus-visible`; skip link to `#main`.
- `.initials` keeps `role="img"` + `aria-label="Full Name"`; photos take the person's name as alt
  text; decorative marks, dots, chevrons and carets are all `aria-hidden`.
- Contrast: the two new badge variants were picked at the same lightness as the existing three
  and pass AA on their own fills; accent-ink links and `--ink-2` secondary text are unchanged
  from Loop 0.

## Known gaps left to implementation

1. **Hrefs are relative page links** (`credentials.html`, `person-switcher.html`) so the bundle is
   browsable. Wire them to real routes with the person in the URL; every page is server-rendered
   per person, no sign-in, no session.
2. **The stack has no page behind it.** "View all Income credentials (6)" points at a category
   page that Loop 5 needs to add — a flat `.cred` list under one `.category` heading.
3. **`:has()` is used once**, to hide the badge dot when a glyph is present. If the target
   browser set can't have it, drop the rule and remove `::before` from the badge variants that
   ship a glyph.
4. **The activity marker's colour semantics are undecided** (see Activity above).
5. **The photos in this bundle are two of 23.** The app takes its copies from
   `tools/sample_data/photos/`; these exist only so the pages render standalone.
