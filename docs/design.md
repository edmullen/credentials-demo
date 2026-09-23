# Design: Loop 4a — UX improvements

This is the technical design for [Intent 004a](intents/004a-ux-improvements.md). It covers one
issue, [#69](https://github.com/edmullen/credentials-demo/issues/69), and follows
[decisions.md](decisions.md).

**There is no Claude Design handoff this loop.** See the Loop 4a exception in
[decisions.md](decisions.md#delivery-approach). #69 holds every copy and layout instruction and is
cited below as "#69 item N". This document says where each change lands. It also fills the gaps
the issue leaves, and §9 lists those choices for Ed to confirm.

Loop 4's design moves to `design/loop-4/design.md` as this one replaces it, per
[decisions.md](decisions.md).

## 1. Overview

This loop changes presentation only. Nothing changes in the protocol, the credentials, runtime
state or verification. Every one of the 25 people reaches the same outcome as at the end of Loop 4.

| #69 item | What | Where | PR |
|---|---|---|---|
| 5, 6 | Top padding halved; `.intro__title` set to 2rem | Wallet `cred.css` | 1 |
| 7, 8, 9.1–9.3 | Compact page-head line; titles that name the step | Wallet templates, `cred.css`, `attempt.py`, `connections.py` | 1 |
| 1, 2 | Landing page; Sign in and Sign out | Wallet `main.py`, `base.html`, new `landing.html` | 2 |
| 9.4, 9.5 | Consent page: white status row; decision moved up | `request.html`, `_credential_panel.html`, `cred.css` | 3 |
| 3, 10 | Credentials page: Find your employer button; DOB on the card | `credentials.html`, `credentials.py`, `display.py` | 3 |
| 4 | Employers listed in the switcher | `tools/generate_credentials.py`, Wallet data, `switch.html` | 4 |
| Payroll | The paystub tables scroll sideways on mobile | Payroll `paystub.html`, `cred.css` | 5 |

## 2. Wallet stylesheet sizes (#69 items 5, 6)

- `html[data-app="wallet"] .main` top padding goes from `calc(var(--space) * 3.5)` to
  `calc(var(--space) * 1.75)`. The bottom padding stays as it is.
- `.intro__title` changes from `font-size: clamp(2rem, 6vw, 3rem)` to `font-size: 2rem`. This edits
  the Wallet's own copy of `cred.css` only, so Payroll and Benefits keep the clamp.

## 3. The page head (#69 items 7, 8, 9.1)

### Component

A new `.pagehead` replaces the separate `.back` link and `.intro__eyebrow` at the top of every
Wallet page:

```html
<div class="pagehead">
  <a class="back" href="/p/p01/connections">Connections</a>
  <span class="pagehead__sep" aria-hidden="true">|</span>
  <h1 class="pagehead__name">Find your employer</h1>
</div>
<p class="intro__title">Select your employer</p>
```

- **The page name is the `<h1>` on every page.** Credentials and Activity lose their intro title,
  so the page name is the only heading that can be the `<h1>` there. Making it the `<h1>` on every
  page means the `<h1>` always names the page and `<title>` can match it (§9 item 2). When a page
  has a step line, it becomes a `<p class="intro__title">`, which looks the same as before.
- **CSS:** `.pagehead` is a single flex row, with items centered and a gap of `var(--space)`. The
  back link doesn't shrink. A long page name wraps within its own column, so the separator is never
  left stranded at a line end.
  `.pagehead__name` uses the eyebrow's type (mono, 0.75rem, 0.08em tracking, uppercase), but with
  `font-weight: 600`, `color: var(--ink)` and `margin: 0`. `.pagehead .back` drops to 0.875rem and
  keeps its `min-height: var(--tap)` touch target. `.pagehead__sep` uses `var(--line-2)`.
- When there's no back link, the separator is left out as well.
- `.intro__eyebrow` stays, because Activity's day headings still use it. `.back` also stays, and
  appears only inside `.pagehead` from now on.
- The page head and the step line sit together in a `.stack-s`, so they read as one block.

### Page by page

For pages #69 doesn't name, one rule applies: the old eyebrow becomes the page name and the title
is unchanged. Where the old eyebrow just said "Wallet", the nav label becomes the page name.

| Page | Back link | Page name (`<h1>`, `<title>`) | Step line |
|---|---|---|---|
| Credentials | — | Credentials | none (#69 8.1) |
| Credential detail | All credentials | Identity credential | {person's name} |
| Connections | — | Connections | see below (#69 8.2, 8.4) |
| Find your employer | Connections | Find your employer | Select your employer (#69 8.3) |
| Asking | — | Connecting to Meridian Payroll | Asking Meridian Payroll |
| Consent | Connections | Request from Meridian Payroll (#69 9.1) | Do you want to share 1 credential with Meridian Payroll? (#69 9.2) |
| Checking | — | Connecting to Meridian Payroll | Checking your identity |
| Activity | — | Activity | none (#69 8.5) |
| Switch person | — | Demo control | Switch person |

### Step lines that depend on state

- **Connections** (#69 8.2, 8.4): shows "Now connect your payroll" if any provider panel is not
  connected. That covers a panel just added and a panel showing a failure band. Otherwise it shows
  "You have {n} connection" or "You have {n} connections", with plain pluralization, counting
  connected panels. With no panels, it shows "You have 0 connections". This is a new
  `connections_title(panels)` helper in `app/connections.py`, so it can be unit-tested.
- **Consent** (#69 9.2): "Do you want to share {n} credential(s) with {provider}?" The same line
  appears in the missing-credential phase (§9 item 8).
- **Purpose line** (#69 9.3): `purpose_line()` in `app/attempt.py` starts with the provider's name
  instead of "It": "Meridian Payroll runs payroll for Crossroads Diner Group, and needs …".

## 4. Landing page and sign in/out (#69 items 1, 2)

- **`GET /`** now renders `landing.html` instead of redirecting to p01's credentials. The page
  follows #69 item 1's copy, in order:
  1. The headline, as the `<h1 class="intro__title">`. The landing page has no page head.
  2. The blurb, as `.intro__purpose`.
  3. **Sign in**, as a `.btn` link to `/p/p01/credentials`, reusing `DEFAULT_PERSON`.
  4. The demo notice, as a new `.landing__note`: 0.875rem in `var(--ink-2)`, with the repo link.

  `<title>` is "Wallet".
- **`base.html` without a person.** `render()` accepts `person=None`, the same pattern Payroll's
  `base.html` already uses. Without a person:
  - the brand links to `/`;
  - there are no nav links and no Menu, since every nav link needs a person;
  - a `.btn` **Sign in** link takes the initials' place (#69 item 1.5);
  - the footer leaves out Switch person.

  Payroll's landing page shows placeholder nav links, but the Wallet's shows none (§9 item 5).
- **Sign out** is a plain link to `/`, and the last item in the Menu panel (#69 item 2). **The
  Wallet shows the Menu at every width** (§9 item 4). The desktop header's inline links are gone,
  and the panel becomes the page's one `<nav aria-label="Main">`. Its links line up with the 30rem
  column. Signing out clears nothing: runtime state is per person, not per visit. The brand still
  links to the signed-in person's credentials (Intent 004a).
- **Tests:** `/` returns 200 with the headline and a Sign in link to `/p/p01/credentials`, and has
  no initials. Every person page has a Sign out link to `/`. Any test that expected `/` to redirect
  is updated.

## 5. Consent page (#69 items 9.4, 9.5)

- **Decision placement.** The Approve and Deny form, with its lead line, moves between the purpose
  line and the `<ol class="request">`. In the missing-credential phase, the Close request form stays
  below the list, because its lead line ("Without it …") refers to the missing item above it
  (§9 item 8).
- **Status row.** `_credential_panel.html` gains a `status_layout` variable, set to `"band"` by
  default or `"top"`. The consent page passes `"top"`. The credential detail page passes nothing and
  keeps its tinted band, as Ed decided in Intent 004a. `"top"` renders:

  ```html
  <div class="panel__top">
    <h3 class="visually-hidden" id="r1-status">Status</h3>
    <div class="cred__top">  <!-- Issuer: {issuer name} on the left, the badge on the right -->
    <p>{{ c.message }}</p>
  </div>
  ```

  The HTML comment stands in for the issuer and badge markup, which is exactly the markup
  `credentials.html` uses today.

  `.panel__top` copies the band's padding and gap, sits on the panel's white surface with
  `border-bottom: 1px solid var(--line)`, and sets its `<p>` in `var(--ink-2)`. It's deliberately
  not a `.panel__status`: that class's badge rule paints badges white, and here the badge keeps its
  own color. So a tampered credential gets a white row with a red badge. The message sentence
  stays below the row (§9 item 9).

## 6. Credentials page (#69 items 3, 10)

- **Find your employer** (#69 item 3). The dashed Income note becomes a `<div>` holding the
  existing `<p>` and a `.btn` link to `/p/{id}/connections/employers`. It's the same button the
  Connections empty state has. The button shows only while the person has **no provider panel at
  all** (§9 item 10). The route passes `has_link` next to `connected`. Add
  `.category__waiting-note` flex-column rules, and `margin: 0` on its `<p>`. p24 and p25 never see
  the button, because they have no Identity credential and so no Income category.
- **DOB** (#69 item 10). A new `.cred__dob` line under `.cred__name` reads `DOB: 09/02/91`. That's
  MM/DD/YY, zero-padded, from a new `numeric_date()` in `app/display.py` exposed as
  `Credential.birth_date_numeric`. It's styled like `.cred__address`. A tampered card shows its DOB
  as received, just as it already shows the address.

## 7. Switcher employers (#69 item 4)

- `tools/generate_credentials.py`: `wallet_person()` adds an `employerNames` list, resolved from
  each person's `jobs` through `tools/sample_data/generated/employers.json`, in job order. Every
  person has at least one job, and p07 and p08 have three.
- **Re-key churn is accepted** (Intent 004a). A re-run makes new keys. That rewrites the Wallet's
  `people.json`, `credentials.json` and `trust.json`, and **Payroll's `trust.json`**, so this PR
  redeploys Payroll as well as the Wallet. Both suites are run after the regeneration.
- `switch.html` adds a second `.people__place` line: "Employer: X" for one employer, or
  "Employers: X, Y" for more (§9 item 11).
- **This is a demo aid only.** `app/people.py` notes that `employerNames` is for the switcher
  display and that connect logic must never read it, since Payroll decides employment. A test
  asserts that `employerNames` appears nowhere under `app/` except `people.py` and the switcher
  template.

## 8. Payroll: paystub tables on mobile (#69, Payroll item)

**Cause:** `.figures` cells are `white-space: nowrap`, and `.panel` has `overflow: hidden`. On a
narrow screen, the four-column Earnings table grows wider than its panel and gets clipped.

**Fix:** wrap each `.figures` table in
`<div class="figures__scroll" role="region" aria-label="Earnings" tabindex="0">`, using
"Deductions" as the label for the second table. It gets `overflow-x: auto`. `tabindex` lets
keyboard users scroll the region (WCAG 2.1.1), and the global `:focus-visible` style shows focus.
Both tables are wrapped, even though only Earnings overflows today (§9 item 12). This edits
Payroll's own `cred.css` only.

## 9. Decisions and deviations

Choices this design makes where #69 is silent or ambiguous, for Ed to confirm or overturn.

1. **Find your employer's page name follows #69 item 7's example**, `< Connections | FIND YOUR
   EMPLOYER`. Item 8.3 reads as if the page name were "Connections", which would repeat the back
   link.
2. **The page name is the `<h1>`, and `<title>` matches it.** Two titles change as a result:
   Credentials' `<title>` is no longer "Your credentials", and the consent page's `<title>` is no
   longer its "is asking for" sentence.
3. **Pages #69 doesn't list** (credential detail, Asking, Checking, Switch person) follow the rule
   in §3: the old eyebrow moves up to the page name, and the title stays.
4. **The Wallet uses the Menu at every width** (Ed, 2026-09-23, during build). The plan was to add
   Sign out to the desktop header nav as well, but it doesn't fit. The Wallet's header is 30rem
   wide, which leaves about 269px for nav links, and the four links measure 278px with no gaps. So
   the desktop header drops its inline links, and Sign out sits at the bottom of the Menu at every
   width, as #69 item 2 describes.
5. **The landing page has no nav, no Menu and no Switch person link.** It shows just the brand and
   Sign in.
6. **Blurb typo:** #69 item 1.2 says "like you ID". The page reads "like your ID".
7. **The Connections step line** says "Now connect your payroll" whenever any panel isn't
   connected, including after a failure.
8. **Consent, missing-credential phase:** it keeps the "Do you want to share" step line, and its
   Close request form stays below the list.
9. **The consent status row keeps its message sentence** under the issuer and badge. That sentence
   is what explains a tampered result.
10. **Find your employer on Credentials shows only until an employer is added.** After that, the
    next step is Connect payroll, on the Connections page, so the button would lead to the wrong
    step.
11. **Switcher label:** "Employer:" for one employer and "Employers:" for more, following the
    plain-pluralization answer given for the connections count.
12. **Both paystub tables are wrapped** in the scroll region, not only Earnings.
13. **Pre-existing drift, not fixed here:** comments in the app code cite `docs/design.md §N`,
    meaning whichever loop's design was current when they were written. After this move they point
    at the wrong document. Fixing them would redeploy every app for comment-only changes, so it's
    left for a loop that touches those files anyway.

## 10. Tests

Copy assertions are updated in place: the two `<h1 class="intro__title">` checks in
`test_routes.py`, and "is asking for" in `test_attempt_call_one.py`. Following Loop 4's retro, each
new string matches the apostrophe encoding of its nearest neighbor. New tests:

- `connections_title()` for zero connections, one connected, a panel pending, and a panel failed;
- the page head on each page: the `<h1>` text, and a back link where the table says there is one;
- the landing page, Sign in and Sign out (§4);
- consent: the decision form comes before the request list, and the `"top"` status layout appears
  on consent but not on the detail page;
- `numeric_date()`, and the DOB on the credentials card;
- Find your employer shown with no link and hidden once an employer is added;
- the switcher's employer lines, and the `employerNames` confinement check;
- Payroll: each `.figures` table sits inside a focusable `role="region"`.

## 11. Build order

Five PRs, one branch each. Each PR says "Refs #69", except the last, which closes it. Each is
merged hands-off once `ci-passed` is green.

1. **Wallet page heads and sizes** (§2, §3). This is the widest template change, so it goes first
   and later PRs build on the new markup.
2. **Landing page and sign in/out** (§4).
3. **Consent page and credentials card** (§5, §6).
4. **Switcher employers** (§7). The generator re-run redeploys Payroll too.
5. **Payroll paystub tables** (§8). Independent of the others; it could go at any point.

Each PR is checked on a locally running Wallet at phone width (375px) and at desktop width before
it's merged. After the last merge, one live pass on Render covers every Wallet page, plus a paystub
at phone width.

## 12. Acceptance criteria

- [ ] `/` shows the landing page, and both Sign in buttons go to p01's credentials.
- [ ] Sign out, the last Menu item at every width, returns to `/`.
- [ ] Every Wallet page opens with the compact page head, following §3's table.
- [ ] Step lines match #69 item 8 and §3, including the Connections count.
- [ ] Consent: the new title and purpose line, Approve and Deny above the credential, and a white
      status row. The credential detail page is unchanged.
- [ ] Credentials: Find your employer appears in the Income note until an employer is added, and
      the card shows DOB in MM/DD/YY.
- [ ] Switcher: each person's employers appear under their city and state.
- [ ] Payroll: a paystub's Earnings table scrolls sideways at 375px, by touch and by keyboard.
- [ ] All three suites pass, and all 25 people still reach their Loop 4 outcomes.
