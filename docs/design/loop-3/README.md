# Handoff: Cred Demo — Loop 3, Payroll Stands Up

Design handoff for Loop 3, answering [brief.md](brief.md). Five static pages plus a `cred.css`
that is a strict superset of **Payroll's Loop 0 file** (371 lines): every Loop 0 token, theme and
component carries forward unchanged, and everything new is appended in a marked section at the
end. Nothing from the Wallet's 731-line copy is imported except the handful of Loop 2 components
Payroll actually uses, copied verbatim and marked as such in the stylesheet.

As with Loops 0 and 2, these are **design references written in HTML** — the shape the
server-rendered Jinja templates should take, not code to drop in. The handoff is a historical
record: the app is never edited to match it afterwards, so anything that must survive is written
down here.

## Fidelity

**High.** Final colours, type, spacing, radii, states and copy. Open any page in a browser; there
is nothing to build. Copy, class names and ARIA attributes are production strings — take them
verbatim. No JavaScript, no bundler: the mobile nav is still a native `<details>`, the brand mark
is still a CSS-filled `<span>`.

One proposal per screen, as the brief asked. Nothing below is an option to choose between.

## Files

| File | Screen |
| --- | --- |
| `cred.css` | Payroll's Loop 0 stylesheet verbatim + a Loop 3 additions section |
| `index.html` | Meridian Payroll home (`/`), one change: Sign in |
| `paystubs.html` | Employee account landing, **one employer** (Grace Okafor, p01) |
| `paystubs-p08.html` | The same screen with **three employers** (Nadia Haddad, p08) |
| `paystub.html` | Paystub detail, **hourly** (Grace Okafor, p01, 16–30 September 2026) |
| `paystub-salary.html` | Paystub detail, **salaried** (Daniel Walsh, p09, same period) |
| `person-switcher.html` | All 25 people, with their employers |
| `screenshots/` | Desktop capture of each page |

The brief asked for four screens; two of them ship as two pages each. The account landing is
drawn with one employer and with three, and the paystub is drawn hourly and salaried — in both
cases the same template with different data, and in both cases the pair is what makes the
figure area trustworthy.

## Decisions the brief asked for

### 1. The paystub

One `.panel`, read top to bottom as a pay statement:

1. **Parties** — Employer (name, city) and Employee (name, job title) side by side, each under a
   mono `.card__meta` label, names in Archivo at 1.25rem.
2. **Period** — Pay period, Pay date, Frequency as a three-up `<dl>`, values in tabular figures.
3. **Figures** — Earnings and Deductions as two real `<table>`s side by side in
   `.figures__pair`, each with `<caption>`, `scope="col"` headers, `scope="row"` line labels, and
   a `<tfoot>` total rule (2px `--line-2`) separating the total from the lines that make it up.
   Labels left, amounts right, `font-variant-numeric: tabular-nums` throughout. The column widths
   hold from $240.00 to $4,916.67 — `white-space: nowrap` on figure cells, `width: 1%` on the
   amount column, and the label column absorbs the slack.
4. **Net pay** — set apart on `--accent-wash`, label and one line of explanation left, the amount
   right in Archivo 2rem.
5. **The note** — one `.panel__note` row on `--surface-2`, once, at the foot of the document.

At the breakpoint the two tables wrap to a single column (`minmax(min(100%, 20rem), 1fr)`);
`align-items: start` keeps the one-line earnings table from stretching to the deductions table's
height.

### 2. Room for a year-to-date column (#50)

The amount column already carries a `<th scope="col">` reading **This period**. Adding YTD is
one more `<th scope="col">Year to date</th>` and one `<td class="figures__amount">` per row — no
CSS change, no relayout, because nothing in `.figures` is positioned or width-pinned. The header
row exists *only* for this; with a single figure column it would otherwise be redundant. That is
the whole accommodation, as asked.

### 3. Saying the withholding is approximate

Once, quietly, at the foot of the statement, in the same `.panel__note` treatment Loop 2 uses for
the tampered credential's caveat:

> Withholding on this statement is estimated for the demo, using 2025 single-filer federal and
> New Jersey rates. It is not a real tax calculation.

Outside the figure area, after the net pay, so it reads as a footnote on the document rather than
an annotation on any line. No asterisks, no per-line marks, no badge.

### 4. Sign in

`<a class="btn" href="/p/p01/">Sign in</a>` replaces the hard-coded `RK` `.initials` in the
header, same position, no other change to `/`. Sentence case "Sign in", matching the Loop 0
wallet page's button. It is a real `<a>` because it navigates. The marketing nav is untouched,
and the disclosure panel repeats Sign in as its last item so the door exists below 40rem.

### 5. The header, inside the portal

Same component, two states. Public: marketing nav + Sign in. Portal: **Paystubs · Connections ·
Activity** + the person's `.initials` (`role="img"`, full name as `aria-label`). Connections and
Activity are ordinary `<a href="#">` links, styled identically, in both the inline nav and the
`<details>` panel — no dimming, no "soon", per the Loop 0 convention.

`aria-current="page"` sits on Paystubs on the account landing page only. On the paystub detail
and the switcher no nav item is current, as in Loop 2.

### 6. What the landing page carries

- **Who you are**: eyebrow "Your pay", `<h1>` the person's name in Archivo, then `.ident` —
  town and state, and the `subjectId` below it in mono at 0.8125rem.
  **Recommendation: show it.** It is plumbing, but this is a demo whose subject is identifiers,
  the person is about to connect a wallet to this exact account in Loop 4, and one quiet mono line
  is what lets someone watching the demo match the two ends. If it ever reads as clutter, the
  line is removable without touching anything else.
- **A section per employer** using Loop 2's `.category` head: the employer name as `<h2>`, and
  under it a `.category__sub` line reading the job title and the employer's city and state in
  title case — "Home Health Aide · Trenton, NJ". It sits under the heading rather than opposite
  it, and in ordinary sentence type rather than the mono `.card__meta`, because it describes the
  job the statements below belong to and reads as part of the heading block.
  **No pay rate or salary** — that belongs on the statement, not on the index of statements.
- **The paystubs**, newest first, as `.paylist` rows: pay date in bold on the left, pay period in
  mono beside it, a hairline chevron at the right edge. Two rows per employer, always.
- **A held place for Loop 4**: a plain `.card` with a neutral *Coming soon* badge, "Send your pay
  to your wallet". Loop 4 replaces its contents with a real connection; the rest of the page does
  not move.

**One section looks deliberate** because the section head is a full-width `<h2>` with the job
title set opposite it — the same shape whether it appears once or three times — and because the
wallet card closes the page underneath it. Nothing is centred, nothing is half-width, so there is
no hole where a second heading would go.

### 7. Person switcher rows

`.people` reused. Each row: 32px `.initials--sm`, then a three-line meta column — name, the
employer names joined by `&middot;`, then town and state. The employers line wraps rather than
truncating, which is what holds p07's and p08's three names at narrow widths; rows are
`min-height: 60px` and grow. No badge: there is no verification status in Payroll, and an empty
badge column would imply one is coming. The selected person is tinted with `--accent-wash` and
carries `aria-current="page"`.

## New tokens

Added inside the payroll theme block, so the other apps' copies are unaffected:

| Token | Value | Use |
| --- | --- | --- |
| `--surface-2` | `oklch(0.99 0.002 70)` | `.panel__note` fill |
| `--accent-wash` | `oklch(0.985 0.012 var(--hue))` | Net pay band, selected switcher row |
| `--figure-gap` | `32px` | Gutter between the earnings and deductions tables |

The first two are the same values Loop 2 added to the wallet block.

## New components

Lifted verbatim from Loop 2: `.back` · `.footer__note` / `.footer__aside` · `.category` /
`.category__head` / `.category__title` · `.panel` / `.panel__section` / `.panel__note` ·
`.people` and its parts.

New in Loop 3: `.category__sub` · `.ident` · `.paylist` · `.stub__head` / `.stub__party` · `.stub__meta` ·
`.figures__pair` / `.figures` · `.stub__net` · `.people__employers`.

Every one reads tokens only and references no theme, so a fourth app remains one
`html[data-app="…"]` block.

**One Loop 2 rule is amended**: `.panel__section:first-child { border-top: 0 }`. In Loop 2 the
panel always opened with a status band, so the first section never needed it; the paystub opens
with a section. Harmless in the Wallet's copy, but it is a change, and Payroll's copy is the only
one that has it.

## Accessibility

WCAG AA, as Loops 0 and 2:

- One `<h1>` per page; `<header>`/`<main>`/`<footer>` landmarks; `<nav aria-label="Main">`; every
  employer section labelled by its `<h2>` via `aria-labelledby`.
- **The figure area is a real table.** `<caption>` names each table, `scope="col"` on the column
  heads, `scope="row"` on every line label, totals in `<tfoot>`. A screen reader reads
  "Medicare, this period, $15.95".
- `aria-current="page"` on the active nav item and the selected switcher row.
- Every interactive element ≥44px: `.paylist__row` and `.people__row` are 60px, the Sign in
  button and `.back` are 44px.
- Colour is never the only signal — the net pay band is also labelled, set apart and larger; the
  totals are separated by a rule, not just weight.
- Visible focus everywhere via Loop 0's global `:focus-visible`; skip link to `#main`.
- `.initials` keeps `role="img"` + `aria-label="Full Name"`; chevrons and the brand mark are
  `aria-hidden`.
- Contrast unchanged from Loop 0: `--ink` 13:1, `--ink-2` 5.7:1, white on `--accent` ~7:1.

## Known gaps left to implementation

1. **Hrefs are relative page links** (`paystubs.html`, `paystub.html`) so the bundle is browsable.
   Wire them to real routes with the person in the URL — `/p/p01/`, `/p/p01/paystubs/<id>/`.
   Sign in points at `/p/p01/`. Every switcher row except p08's points at `paystubs.html`.
2. **The two pay types differ only in the earnings line.** Hourly reads
   `Regular | $20.00 | 55.00 | $1,100.00` under **Rate / Hours**; salaried reads
   `Salary | $92,000.00 | 1 of 24 | $3,833.33` under **Rate / Installment** — the annual figure
   in the rate column, and which of the 24 equal installments this is in place of hours. Same
   table, same column count, one column heading changes. Deductions, totals and net pay are
   identical in structure.
3. **Printing is undesigned**, by decision. A browser print of `paystub.html` is legible but
   carries the header and footer. A print stylesheet is a small, self-contained addition whenever
   it is wanted.
4. **Connections and Activity have no destination** until Loop 4, and point at `#`.
5. **Employers carry no state in the data** — `employers.json` has a city only, and all fifteen
   are in New Jersey. The pages print ", NJ" as a literal. If a non-NJ employer is ever added,
   the field has to come from the data.
6. **No empty states exist in Payroll** — everyone has two paystubs per job — so none are drawn.
