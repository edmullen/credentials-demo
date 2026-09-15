# Handoff: Cred Demo — Design System + Three Home Pages

## Overview
A minimal shared design system and three placeholder home pages for a verifiable-credentials
demo. The three fictional apps share one stylesheet and identical component markup; each gets a
distinct tone through a theme attribute on the `<html>` element.

| App | Theme | Role |
| --- | --- | --- |
| Wallet | `data-app="wallet"` | A person's credential wallet. Warm, personal, mobile-first. |
| Meridian Payroll | `data-app="payroll"` | Corporate payroll provider that issues credentials. |
| Benefit Agency | `data-app="benefit"` | Fictional government program. Plain language, official. |

Each page carries the app name, a one-sentence purpose, and a "Coming soon" state.

## About the Design Files
The files in this bundle are **design references created in HTML** — prototypes showing intended
look and behavior, not production code to drop in as-is.

That said, this design was authored under an explicit constraint: **plain semantic HTML + CSS, no
React, no build step**, because the target app uses server-rendered HTML templates. So the markup
and the stylesheet are already in the shape the target needs. The implementation task is to port
them into the server-rendered template system (Jinja, ERB, Handlebars, Go templates, Blade,
whatever the codebase uses): lift `cred.css` in essentially verbatim, and split the page markup
into a base layout plus partials for the shared components. If the codebase already has a
stylesheet or token layer, reconcile `cred.css`'s custom properties with it rather than adding a
second parallel system.

Do not introduce a client-side framework or a bundler for these pages.

## Fidelity
**High fidelity.** Final colors, typography, spacing, radii, states and copy. The pages render
exactly as intended in a browser with no build step — open `index.html`. Recreate them
faithfully; where a value is expressed as a custom property, keep the custom property.

## Theming model
One stylesheet, `cred.css`. All theming flows from a single attribute on the root element:

```html
<html lang="en" data-app="wallet">   <!-- or "payroll" or "benefit" -->
```

Each theme block overrides `--hue`, `--bg`, `--radius`/`--radius-lg`, `--font-display`, and in one
case `--ink`. Component CSS never references a theme; it only reads tokens. Adding a fourth app
means adding one `html[data-app="…"]` block.

Accent tokens are derived from `--hue` inside `:root`. Because `var()` in a `:root` declaration
resolves against `:root`'s own `--hue`, overriding `--hue` on a descendant does **not** retint
that subtree. A `.theme` class re-declares the four accent tokens for exactly that case (used on
`index.html` to show three themed cards on one page). Keep this rule if you build any multi-theme
view; it is not optional sugar.

## Screens / Views

All three pages share one structure, top to bottom:

1. Skip link (visually hidden until focused)
2. `<header class="header">` — brand mark + name, inline nav, user initials, mobile disclosure menu
3. `<main class="main" id="main">` — eyebrow, `<h1>`, purpose paragraph, horizontal rule, one card
4. `<footer class="footer">` — app name, "Demo environment — no real credentials"

### 1. Wallet — `wallet.html`
- **Purpose**: A person lands here before the pilot opens. Reassurance, nothing to do yet.
- **Layout**: Single column, `max-width: 30rem` (both `.wrap` and `.header__inner` are narrowed by
  the wallet theme), centered, `0 24px` side padding. Main padding `56px` top, `72px` bottom.
  Vertical rhythm from `.stack` (24px gap) and `.stack-s` (8px gap).
- **Type**: `<h1>` in Newsreader 600, `clamp(2rem, 6vw, 3rem)`, letter-spacing `-0.02em`.
- **Copy**:
  - Eyebrow: "Wallet"
  - H1: "Your credentials"
  - Purpose: "Wallet holds the credentials you have been issued, so you can prove something about
    yourself without handing over your documents."
  - Card meta: "Status" · badge: "Coming soon" (neutral)
  - Card title: "Your credentials, in one place"
  - Card body: "Sign-in opens when the pilot begins. Nothing to do yet."
  - Button: "Sign in" — `disabled`, full width
- **Theme**: hue 52 (warm amber), `--bg: #F7F7F5`, radius 10px / 16px (roundest of the three).
- **Nav**: Credentials, Activity, Help. Initials "AM" (Avery Mullen).

### 2. Meridian Payroll — `payroll.html`
- **Purpose**: Employer-facing marketing/portal entry. Corporate, clean, slightly denser.
- **Layout**: Same structure, `max-width: 62rem`. Card actions sit in a wrapping `.row` (16px gap).
- **Type**: `<h1>` in Archivo 600 (neo-grotesque, corporate), same clamp and tracking.
- **Copy**:
  - Eyebrow: "Payroll provider"
  - H1: "Meridian Payroll"
  - Purpose: "Meridian Payroll issues signed employment and income credentials to your employees,
    so verification no longer requires a phone call or a PDF."
  - Card meta: "Employer portal" · badge: "Coming soon" (neutral)
  - Card title: "Issue employment and income credentials"
  - Card body: "Onboarding for pilot employers opens later this year."
  - Buttons: "Request access" (primary, `disabled`), "Read the integration notes" (secondary link)
- **Theme**: hue 255 (corporate blue), `--bg: #F2F2F2`, base radius 6px / 10px.
- **Nav**: Product, Issuance, Documentation, Support. Initials "RK" (Rina Kapoor).

### 3. Benefit Agency — `benefit.html`
- **Purpose**: Government program page. Plain language, high contrast, squarer and plainer.
- **Layout**: Same as payroll. Card uses `.card--flat` (no shadow) — the civic treatment.
- **Type**: `<h1>` in Libre Franklin 600 (Franklin Gothic lineage, common in public-sector type).
- **Copy**:
  - Eyebrow: "Benefit Agency"
  - H1: "Programs to support your needs"
  - Purpose: "Benefit Agency helps families with the cost of care, and lets you prove your income
    with a credential from your wallet instead of paperwork."
  - Card meta: "Program status" · badge: "Coming soon" (neutral)
  - Card title: "Apply without paper documents"
  - Card body: "You will be able to share a credential from your wallet instead of uploading pay
    stubs. Applications are not open yet."
  - Button: "Start an application" — `disabled`
- **Theme**: hue 172 (civic teal), `--bg: #F2F9FA`, radius 4px / 6px, `--ink: oklch(0.20 0.01 200)`
  (darker than the other themes). Badge and initials corners square off to 3px / 4px; the brand
  mark becomes a 2px-radius square instead of a circle.
- **Nav**: About the program, Who can apply, Contact us. Initials "JD" (Jordan Diaz).

### 4. `index.html` — system reference
Not a product screen. Links the three home pages and shows the component inventory: all three
badge states, primary/secondary/disabled buttons, both initials sizes, and one card per theme in
a `repeat(auto-fit, minmax(min(100%, 17rem), 1fr))` grid. Useful as a living reference; drop it or
keep it in a styleguide route.

## Components

Five shared components, all in `cred.css`. Markup is identical across apps — only tokens change.

### header — `.header`
```html
<header class="header">
  <div class="header__inner">
    <a class="header__brand" href="/">
      <span class="header__mark" aria-hidden="true"></span>
      App Name
    </a>
    <nav class="header__nav" aria-label="Main">
      <a href="#">Item</a>
    </nav>
    <span class="initials" role="img" aria-label="Avery Mullen">AM</span>
    <details class="nav-menu">
      <summary>Menu</summary>
      <div class="nav-menu__panel">
        <a href="#">Item</a>
      </div>
    </details>
  </div>
</header>
```
- White surface, 1px bottom border `--line`, `position: relative` (anchors the menu panel).
- `.header__inner`: flex, space-between, 16px gap, `min-height: 64px`, padding `8px 24px`,
  `max-width: 62rem` (wallet: `30rem`) centered.
- `.header__brand`: `--font-display` 600, 1.125rem, tracking `-0.01em`, `--ink`, no underline.
  `.header__mark` is a 22px accent-filled circle (2px-radius square under the benefit theme).
- `.header__nav a`: 0.9375rem, `--ink-2`, no underline, `min-height: 44px`; hover → `--ink` +
  underline. Hidden at `max-width: 40rem`.
- `.nav-menu`: native `<details>`/`<summary>`, no JavaScript. Summary is a 44px-min bordered
  button with a CSS chevron that flips on `[open]`. Panel is `position: absolute; top: 100%;
  left: 0; right: 0`, white, bottom-bordered, shadowed, `z-index: 20`, links stacked at 44px min
  with 1px dividers. Hidden at `min-width: 40.0625rem`.
- In a template system this is one partial taking brand name, nav items, and user initials.

### card — `.card`
- `--surface` background, 1px `--line` border, `--radius-lg` corners, 24px padding.
- Shadow: `0 1px 2px oklch(0.24 0.012 70 / 0.06), 0 4px 14px oklch(0.24 0.012 70 / 0.05)`.
- `.card--flat` removes the shadow (used by the benefit theme).
- Slots: `.card__meta` (mono, 0.75rem, uppercase, `0.04em` tracking, `--ink-2`),
  `.card__title` (1.0625rem/600), `.card__body` (`--ink-2`, margin 0).
- Labelled by its `<h2>` via `aria-labelledby`.

### primary button — `.btn`
- Inline-flex centered, `min-height: 44px`, padding `0 20px`, `--radius`, 1rem/600.
- Default: `--accent` fill, white text. Hover `oklch(0.38 0.11 var(--hue))`,
  active `oklch(0.33 0.10 var(--hue))`.
- `.btn--secondary`: `--surface` fill, 1px `--line-2` border, `--ink` text; hover fills `--bg`.
- `.btn--block`: full width.
- Disabled (`:disabled` or `[aria-disabled="true"]`): `--line` fill, `--line-2` border, `--ink-2`
  text, `not-allowed` cursor. **Use a real `<button disabled>`, never a link with
  `aria-disabled`** — a disabled link still takes focus and still navigates.

### user initials — `.initials`
- 44px circle, `--accent-tint` fill, 1px `--accent-line` border, `--accent-text` glyphs,
  0.875rem/600, `0.02em` tracking. `.initials--sm`: 32px / 0.75rem. 4px radius under benefit.
- Must carry `role="img"` plus `aria-label="Full Name"` — `aria-label` alone on a `<span>` is not
  reliably announced.

### status badge — `.badge`
Three states, each a text label plus a 7px dot in `currentColor` (never color alone):

| Variant | Background | Border | Text |
| --- | --- | --- | --- |
| `.badge--neutral` | `oklch(0.955 0.004 70)` | `oklch(0.86 0.006 70)` | `oklch(0.42 0.012 70)` |
| `.badge--verified` | `oklch(0.955 0.035 158)` | `oklch(0.84 0.07 158)` | `oklch(0.40 0.10 158)` |
| `.badge--error` | `oklch(0.965 0.025 25)` | `oklch(0.86 0.06 25)` | `oklch(0.45 0.16 25)` |

Pill (999px; 3px under the benefit theme), padding `2px 10px 2px 8px`, 0.8125rem/600. Status
colors are semantic and do **not** retint per app.

## Interactions & Behavior
- **Mobile nav**: `<details>` toggles on click/Enter/Space natively; panel overlays content below
  the header. No JS, no focus trap, Escape is not handled (native `<details>` behavior). If the
  codebase wants click-outside-to-close, that is the one place to add a few lines of JS.
- **Hover**: header links gain underline + darker ink; buttons darken; secondary button fills.
- **Focus**: global `:focus-visible` → `3px solid var(--accent-text)`, 2px offset, 2px radius.
- **Skip link**: `.skip` is off-canvas at `left: -9999px`, and on `:focus` becomes a bordered white
  chip at top-left, `z-index: 30`, targeting `#main`.
- **Transitions**: none. Deliberate — nothing on these pages animates.
- **Responsive**: single breakpoint at 40rem, for nav ↔ disclosure menu. Everything else is fluid;
  `.wrap` max-widths and `clamp()` type do the work. No fixed heights on text containers.
- **No JavaScript anywhere in this design.**

## State Management
None. These are static placeholder pages; every control is inert or disabled. The only stateful
element is the native `<details>` disclosure, whose state lives in the DOM.

When the pages go live, the pieces that will need real state: authenticated user (initials +
name for the header), credential list and per-credential status (drives badge variant), and the
enabled/disabled state of the primary action.

## Design Tokens

### Neutrals (shared)
| Token | Value | Notes |
| --- | --- | --- |
| `--bg` | `oklch(0.98 0.004 70)` | Per-theme override, see below |
| `--surface` | `oklch(1 0 0)` | Cards, header, footer |
| `--ink` | `oklch(0.24 0.012 70)` | Body text, 13:1 on `--bg` |
| `--ink-2` | `oklch(0.45 0.012 70)` | Secondary text, 5.7:1 on `--bg` |
| `--line` | `oklch(0.89 0.006 70)` | Hairlines, card borders |
| `--line-2` | `oklch(0.80 0.006 70)` | Stronger borders, disabled |

### Accents (derived from `--hue`)
| Token | Value | Use |
| --- | --- | --- |
| `--accent` | `oklch(0.46 0.11 var(--hue))` | Button fill, brand mark. ~7:1 with white text |
| `--accent-text` | `oklch(0.42 0.11 var(--hue))` | Links, initials glyphs, focus ring |
| `--accent-tint` | `oklch(0.955 0.022 var(--hue))` | Initials fill |
| `--accent-line` | `oklch(0.86 0.045 var(--hue))` | Initials border |

### Per-theme overrides
| Theme | `--hue` | `--bg` | `--radius` / `--radius-lg` | `--font-display` | Other |
| --- | --- | --- | --- | --- | --- |
| wallet | 52 | `#F7F7F5` | 10px / 16px | Newsreader | `.wrap`/header max-width `30rem` |
| payroll | 255 | `#F2F2F2` | 6px / 10px | Archivo | — |
| benefit | 172 | `#F2F9FA` | 4px / 6px | Libre Franklin | `--ink: oklch(0.20 0.01 200)` |

### Typography
- `--font-ui`: `"Public Sans", "Helvetica Neue", Helvetica, Arial, sans-serif` — all body/UI text.
- `--font-display`: per theme (above) — `<h1>` and header brand only.
- `--font-mono`: `ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace` — eyebrows, meta.
- Body: 17px / 1.55, `text-wrap: pretty`.
- Headings: 600, `line-height: 1.15`, `text-wrap: balance`.
- Scale in use: 3rem→2rem clamped (h1), 1.25rem→1.0625rem clamped (purpose), 1.0625rem (card
  title), 1rem (buttons, menu links), 0.9375rem (nav), 0.875rem (footer, initials), 0.8125rem
  (badge), 0.75rem (meta, eyebrow).
- Google Fonts are loaded per page with `preconnect` + one `css2` link. Self-host them in
  production; weights needed are 400/600 for Public Sans and Newsreader, 500/600/700 for Archivo
  and Libre Franklin (600 is the one actually used).

### Spacing & shape
- `--space: 8px`, used as multiples: 8 / 12 / 16 / 20 / 24 / 56 / 72.
- `--radius`, `--radius-lg` per theme; badges and initials use 999px pills except under benefit.
- `--measure: 34rem` caps the purpose paragraph. `--tap: 44px` is the minimum interactive size.
- `--shadow`: `0 1px 2px oklch(0.24 0.012 70 / 0.06), 0 4px 14px oklch(0.24 0.012 70 / 0.05)`.

## Accessibility
Built to WCAG AA and reviewed against it:
- Body text ≥ 13:1, secondary text 5.7:1, white-on-accent ~7:1, all three badge variants pass AA.
- Every interactive element is ≥ 44px in its smallest dimension.
- One `<h1>` per page, no skipped heading levels. `<header>`/`<main>`/`<footer>` landmarks,
  `<nav aria-label="Main">`, card sections labelled by their heading.
- Visible focus indicator on everything focusable; skip link to `#main`.
- Status is never color-only (label + dot). Disabled actions are real disabled buttons.
- `lang="en"` on `<html>`, `aria-hidden` on the decorative brand mark.

**Two known gaps, left as decisions for implementation:**
1. Every `href` is `"#"` — placeholder links that jump to the top of the page. Wire them to real
   routes; a nav item pointing at the current page should get `aria-current="page"`.
2. Plain-language pass not applied to two strings, by request: "signed employment and income
   credentials" ("signed" is cryptographic jargon) and "Onboarding for pilot employers opens
   later this year" (internal register). Suggested rewrites: drop "signed", and "Pilot employers
   can join later this year."

## Screenshots
`screenshots/` holds a capture of each page at desktop width:
`wallet.png`, `payroll.png`, `benefit.png`, `system-reference.png`. Reference only — the HTML
files are authoritative for every measurement.

## Assets
No images, no icon fonts, no SVG files. The brand mark is a CSS-filled `<span>`; the menu chevron
is a rotated CSS border. The only external dependency is Google Fonts (four families, listed
above) — self-host for production.

## Files
| File | Contents |
| --- | --- |
| `cred.css` | The entire design system: tokens, three theme blocks, all five components, skip link, disclosure menu. ~400 lines, no preprocessor. |
| `wallet.html` | Wallet home page (`data-app="wallet"`) |
| `payroll.html` | Meridian Payroll home page (`data-app="payroll"`) |
| `benefit.html` | Benefit Agency home page (`data-app="benefit"`) |
| `index.html` | System reference page; links the three and shows every component state |
| `screenshots/` | Desktop captures of all four pages |

Open `index.html` in any browser to see all of it. There is nothing to install and nothing to
build.
