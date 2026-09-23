# Design: Loop 4a — UX improvements

This is the technical design for [Intent 004a](intents/004a-ux-improvements.md). It covers one
issue, [#69](https://github.com/edmullen/credentials-demo/issues/69), and follows
[decisions.md](decisions.md) and the Claude Design handoff in
[design/loop-4a/](design/loop-4a/README.md). It replaces the pre-handoff design merged in #72.

**Link, don't restate.** Markup, class names, copy, sizes and accessibility decisions are in the
handoff's pages and README, cited below as "handoff §N". This document says where each piece
lands in the apps, what the handoff leaves to implementation, and how the build is checked
against it.

## 1. Overview

This loop changes presentation only. Nothing changes in the protocol, the credentials, runtime
state or verification. Every one of the 25 people reaches the same outcome as at the end of
Loop 4.

| Area | Handoff | Where | PR |
|---|---|---|---|
| Stylesheet, Menu and Sign out, page heads, step titles | §2, §3, §4, §8 | Wallet `cred.css`, `base.html`, every template | 1 |
| Landing page | §1 | Wallet `main.py`, `base.html`, new `landing.html` | 2 |
| Consent page, credentials page | §5, §6 | `request.html`, `_credential_panel.html`, `credentials.html`, `connections.py`, `display.py` | 3 |
| Switcher employers | §7 | `tools/generate_credentials.py`, Wallet data, `switch.html` | 4 |
| Paystub scroll | §9 | Payroll `cred.css`, `paystub.html` | 5 |

## 2. Stylesheets: adopt the handoff's files

Each handoff `cred.css` is a strict superset of its app's copy: the new rules are in a marked
"Loop 4a additions" section at the end, and no existing line changed. So the build doesn't
hand-transcribe rules:

- **Wallet:** `apps/wallet/app/static/cred.css` becomes `docs/design/loop-4a/wallet/cred.css`,
  byte for byte. That lands in PR 1, together with the markup the Menu rules need (§3).
- **Payroll:** `apps/payroll/app/static/cred.css` becomes `docs/design/loop-4a/payroll/cred.css`,
  in PR 5.
- **One build addition, Wallet only.** `.panel__status--plain` puts back the tints for the
  verified and error badges (a `.panel__status` rule paints badges white), but not for caution
  or unknown. An expired, not-yet-valid or unrecognized-issuer credential can reach the consent
  page, so a short "Loop 4a build additions" block after the handoff's section restores
  `.badge--caution` and `.badge--unknown` the same way, using the values from their own rules (§9
  item 3).

A test asserts that each app's `cred.css` starts with the handoff file's exact contents, so
later drift is visible.

## 3. Menu and Sign out (handoff §2)

In `base.html`, when a person is signed in:

- **Remove the inline nav:** delete the `<nav class="header__nav">` block.
- **Make the Menu panel the landmark:** `<div class="nav-menu__panel">` becomes
  `<nav class="nav-menu__panel" aria-label="Main">`. It keeps the three links and their
  `aria-current`.
- **Add Sign out:** `<a class="nav-menu__signout" href="/">Sign out</a>` becomes the panel's last
  link.

The CSS shows the Menu at every width. Signing out clears nothing, because runtime state is per
person, not per visit. The brand still links to the person's credentials.

## 4. Page heads and step titles (handoff §3, §4)

Every signed-in template replaces its `.back` line and its `.intro__eyebrow` + `<h1
class="intro__title">` pair with the handoff's markup:

```html
<div class="pagehead">
  <a class="back" href="/p/{id}/connections">Connections</a>
  <span class="pagehead__sep" aria-hidden="true"></span>
  <h1 class="pagehead__title">Find your employer</h1>
</div>
<h2 class="intro__title">Select your employer</h2>
```

There's no back link or separator when a page has none, and no `<h2>` when a page has no step
title. Both sit directly in the page's `.stack`, as in the handoff. **`<title>` is the step
title when there is one, otherwise the page name**, followed by " — Wallet".

| Template | Back link | `<h1>` page name | `<h2>` step title |
|---|---|---|---|
| `credentials.html` | — | Credentials | — |
| `credential.html` | Credentials → `/p/{id}/credentials` | Identity credential | — |
| `connections.html` | — | Connections | `connections_title(panels)` |
| `employers.html` | Connections | Find your employer | Select your employer |
| `asking.html` | — | Connecting to {provider} | Wait while {provider} prepares its request |
| `request.html` | Connections | Request from {provider} | see below |
| `verifying.html` | — | Connecting to {provider} | Wait while {provider} checks your identity |
| `activity.html` | — | Activity | — |
| `switch.html` | — | Switch person | Choose who to demo as |

**Step titles that depend on state:**

- **`connections_title(panels)`** is a new helper in `app/connections.py`. It returns "Now connect
  your payroll" if any panel isn't connected; that covers an employer just chosen and a failed
  attempt, as in handoff §4. Otherwise it returns "You have {n} connection" or "You have {n}
  connections", counting connected panels.
- **Consent:** "Do you want to share {n} credential(s) with {provider}?", or, in the missing
  phase, "You do not have the credential {provider} is requesting."
- **Purpose line:** `purpose_line()` in `app/attempt.py` starts with the provider's name, "Meridian
  Payroll runs payroll for …", instead of "It".

The credential detail page loses its name-as-title; the panel already shows the name.

## 5. Landing page (handoff §1)

- **Route:** `GET /` renders `landing.html` instead of redirecting to p01. `render()` accepts
  `person=None`.
- **Markup:** `landing.html` is the handoff's `<main>` content, verbatim.
- **Links:** both **Sign in** buttons go to `/p/p01/credentials` (§9 item 1).
- **`<title>`:** the headline alone, with no " — Wallet" suffix, as in the handoff. `base.html`
  wraps its title in a `{% block title %}`, and the landing page overrides it.
- **`base.html` without a person:** the brand links to `/`. There are no initials and no Menu, and
  a **Sign in** `.btn` sits in their place. The footer keeps **Switch person**, which links to
  `/p/p01/switch` (§9 item 2).

## 6. Consent page and credentials page (handoff §5, §6)

**Consent (`request.html`):**

- **Decision placement:** outside the missing phase, the `<form class="decision">` for Approve
  and Deny moves between the purpose line and `<ol class="request">`, with its markup unchanged.
  The missing phase's Close request form stays after the list.
- **Status area:** `_credential_panel.html` gains a `status_style` variable. When the consent page
  sets it to `"plain"`, the status block renders as `panel__status panel__status--plain`, with
  the handoff's `.cred__top` row (issuer on the left, badge on the right) above the status
  sentence. The credential detail page sets nothing and keeps its tinted band.

**Credentials (`credentials.html`):**

- **DOB:** a `<span class="cred__dob">DOB: {MM/DD/YY}</span>` goes after `.cred__name`. The date
  comes from a new `numeric_date()` in `app/display.py`, exposed as
  `Credential.birth_date_numeric`. A tampered card shows its DOB as received, as it already does
  for the address.
- **Income note:** the note has three states, chosen by a new `income_note(person_id)` in
  `app/connections.py`:

  | State | Markup | Copy |
  |---|---|---|
  | No link | `div.category__waiting-note.category__waiting-note--action` with a `.btn--secondary` link to `/p/{id}/connections/employers` | Loop 2's sentence; button **Find your employer** |
  | Employer chosen, not connected (including after a failure) | the same `div`, with a link to `/p/{id}/connections` | "You've added {employer}. Connect to {provider}, and your pay will appear here as credentials."; button **Finish connecting** |
  | Connected | `p.category__waiting-note` | Loop 4's sentence, no button |

  {employer} is the most recently added employer, the last entry in `Link.employers`, which
  appends in the order employers are added.

## 7. Switcher employers (handoff §7)

- **Generator:** `tools/generate_credentials.py`'s `wallet_person()` adds an `employerNames` list,
  resolved through `tools/sample_data/generated/employers.json` in sample-data (job) order.
- **Re-key churn is accepted** (Intent 004a). The re-run replaces every key, so it rewrites the
  Wallet's `credentials.json` and both apps' `trust.json`, which **redeploys Payroll as well**. Both
  suites run after it.
- **Template:** `switch.html` adds `<span class="people__employers">Employer: {name}</span>`, or
  "Employers: {a}, {b}" for more than one, after `.people__place`.
- **Demo aid only.** `app/people.py` notes that connect logic must never read `employerNames`, and a
  test asserts that only `people.py` and `switch.html` mention it under `app/`.

## 8. Payroll paystub (handoff §9)

`paystub.html` wraps each figures table exactly as the handoff does:

```html
<div class="figures__scroll" role="region" aria-labelledby="fig-earnings" tabindex="0">
```

It uses `fig-deductions` for the second table, and each `<caption>` gets the matching `id`. The
stylesheet comes from §2.

## 9. Decisions and deviations

These are things the handoff leaves open, or gets slightly wrong.

1. **Sign in goes to `/p/p01/credentials`.** The handoff README gives `/p/p01/`, which is a route
   Payroll has but the Wallet doesn't.
2. **The landing footer's Switch person links to `/p/p01/switch`.** The switcher needs a person in
   its URL, and p01 is the default person Sign in opens.
3. **Caution and unknown badges keep their tints on the consent page** (§2), a build addition.
   The handoff restored only verified and error.
4. **"Finish connecting" and its note** are the handoff's proposal (handoff gaps §2). They're built
   as written unless Ed changes them.
5. **Code comments that cite `docs/design.md §N`** point at whichever loop's design was current
   when they were written. That's pre-existing drift, and this loop doesn't fix it.

## 10. Checking the build against the handoff

Tests confirm structure and copy. They can't confirm that sizes and spacing match, so every
Wallet PR also gets a **side-by-side check**:

- **Serve the handoff pages locally**, alongside the Wallet and Payroll, from
  `.claude/launch.json`.
- **Compare pairs:** for each built page and its handoff counterpart, at **375px** and **480px**
  (and the paystub at 375px and 992px), compare the rendered positions of the page head, the step
  title, and the first block of content below it (`getBoundingClientRect().top` and `height`).
- **Tolerance:** the pair should agree to within 1px. The computed `font-size`, `padding` and
  `gap` of the page head and title must match exactly.
- **Record the results:** a table in each PR's description lists the pages compared and any
  difference, with its reason. Differences in sample content, like names, dates or which
  employer, are expected. Differences in layout are not.

After the last merge, one live pass on Render covers every Wallet page and a paystub at 375px.

**Handoff screenshots are skipped this loop** (Ed, 2026-09-23). Headless Chrome hung in this
environment, and `index.html` already shows every handoff page at its widths.

## 11. Tests

- **Stylesheets:** each app's `cred.css` begins with its handoff file's exact contents.
- **Menu:** the single `<nav>` on each page is the Menu panel, and Sign out is its last link, going
  to `/`.
- **Page heads:** every template's back link, `<h1>`, `<h2>` and `<title>` match §4's table, with
  exactly one `<h1>` per page.
- **`connections_title()`:** zero connections, one connected, a panel pending, and a panel failed.
- **Landing:** the copy, both Sign in links, no initials or Menu, and the footer's switcher link.
- **Consent:** the decision comes before the list; the plain status shows the issuer and a badge
  with its tint class (verified and tampered); the missing phase shows its title, with Close
  request after the list.
- **Credentials:** `numeric_date()`, DOB placement, and each of the three Income note states.
- **Switcher:** employer lines, singular and plural, and the `employerNames` confinement check.
- **Payroll:** each table sits in a labelled, focusable region.
- **Existing tests:** copy assertions are updated in place. Each new string matches the apostrophe
  encoding of its nearest neighbor.

## 12. Build order

There are five PRs, one branch each. Each says "Refs #69", except the last, which closes the
issue. Each is merged without waiting once `ci-passed` is green and the side-by-side check (§10)
is clean.

1. **Wallet stylesheet, Menu, page heads and step titles** (§2, §3, §4). The whole stylesheet
   lands here, so the Menu markup has to land with it.
2. **Landing page** (§5).
3. **Consent page and credentials page** (§6).
4. **Switcher employers** (§7). This one redeploys Payroll too.
5. **Payroll paystub** (§8).

## 13. Acceptance criteria

- [ ] Every Wallet page matches its handoff counterpart at 375px and 480px, per §10.
- [ ] `/` is the landing page, and both Sign in buttons open p01's credentials.
- [ ] Sign out is the last Menu item at every width, and goes to `/`.
- [ ] Page heads, step titles and `<title>`s match §4.
- [ ] Consent: the decision comes before the credential, the status is white with a tinted badge,
      and the detail page is unchanged.
- [ ] Credentials: DOB appears, and the Income note follows its three states.
- [ ] Switcher: each person's employers are listed.
- [ ] Payroll: the paystub's tables scroll sideways at 375px, by touch and by keyboard.
- [ ] All three suites pass, and all 25 people still reach their Loop 4 outcomes.
- [ ] ~~Handoff screenshots are committed under `docs/design/loop-4a/screenshots/`.~~ Skipped
      this loop (Ed, 2026-09-23; see §10).

## 14. Reconciliation (plan step)

This is the plan step's reconciliation pass (Loop 2's improvement, kept since). It checks each
handoff page against this design, each acceptance criterion against the mechanism that satisfies
it, and each dependency against Ed's machine. It was written after PR 1 (#82) was built and
checked, and before PRs 2–5. Findings marked **new** change what gets built. Everything else
confirms this design as written.

### Handoff pages against the design

Each page was compared with its Loop 4 version, or with the current template, with whitespace
ignored. The diffs contain only the changes listed here.

| Handoff page | PR | Changes in the handoff | Design | Finding |
|---|---|---|---|---|
| `connections*.html`, `employers*.html`, `pending*.html`, `activity*.html`, `credential-detail*.html` | 1 | page head and step title only | §4 | Built in #82; the side-by-side check is identical. |
| `landing.html` | 2 | new page: `.wrap.landing`, `.landing__title` with a `.landing__lead` span, `.btn--block` Sign in, `.landing__demo`; header shows only the brand and a `.btn`; footer unchanged | §5 | As designed. `<main>` holds `.wrap landing`, not `.wrap stack`, so the 24px top padding comes from `.landing`. The side-by-side check covers it. |
| `consent.html`, `consent-tampered.html` | 3 | decision moved above the list; `panel__status panel__status--plain` with no variant class; `.cred__top` row; status sentence unchanged | §6 | As designed. The tampered panel's `.panel__note` and disclosure note are unchanged, so `_credential_panel.html` changes only its status block. |
| `consent-missing.html` | 1, 3 | step title (#82); Close request stays after the list | §4, §6 | Nothing left to build in PR 3: the form is already after the list. |
| `credentials-start.html`, `credentials-chosen.html`, `credentials.html`, `credentials-empty.html` | 3 | `.cred__dob`; the Income note's three states | §6 | As designed. The handoff has no page for a failed attempt; §6 puts it in the "chosen" state. |
| `credential-detail*.html` | 1 | page head; status band unchanged | §4 | Built. The detail page keeps its tinted band, so `status_style` defaults to the band. |
| `person-switcher.html` | 4 | `.people__employers` line | §7 | As designed. The handoff's order for p06, p07 and p08 matches the generated `jobs` order exactly, so "sample-data order" means job order. |
| `payroll/paystub.html` | 5 | two `.figures__scroll` wrappers, and caption `id`s `fig-earnings` and `fig-deductions` | §8 | As designed. |
| `payroll/cred.css` | 5 | Loop 4a additions only (strict superset) | §2 | **New:** PR 5 adds a pinned-hash test to Payroll too, matching the Wallet's `test_stylesheet.py`. §11 already asks for "each app", and PR 1 wrote only the Wallet's. |

### Acceptance criteria against their mechanisms

| Criterion (§13) | Mechanism | Test | Check |
|---|---|---|---|
| Pages match the handoff at 375px and 480px | adopted `cred.css` (§2) and the handoff's markup | `test_stylesheet.py` | side-by-side table in each PR (§10) |
| `/` is the landing page; Sign in opens p01's credentials | `landing()` route, `render(person=None)`, `{% block title %}` | new `test_landing.py` | landing pair at both widths |
| Sign out is the last Menu item and goes to `/` | `base.html` Menu (§3) | `test_pagehead.py` (#82) | Menu pair (#82) |
| Page heads, step titles, `<title>`s | templates (§4), `connections_title()` | `test_pagehead.py`, attempt tests (#82) | #82's table |
| Consent: decision first, white status, detail page unchanged | `request.html` order; `status_style="plain"` | consent tests in `test_attempt_call_one.py`; the existing detail-page include test | consent and consent-tampered pairs |
| Credentials: DOB and the three Income note states | `numeric_date()`, `birth_date_numeric`, `income_note()` | new `test_credentials_card.py`, `test_display.py` | credentials-start, credentials-chosen and credentials pairs |
| Switcher lists employers | generator `employerNames`, `switch.html` | new `test_switcher_employers.py`, including confinement | switcher pair |
| Paystub tables scroll by touch and keyboard | wrappers and adopted Payroll `cred.css` | new tests in `test_paystub_display.py`, including the pinned hash | paystub pair at 375px and 992px, plus a keyboard scroll check |
| All suites pass; 25 outcomes unchanged | no protocol or state change; re-keyed trust lists stay byte-identical | all three suites; `cmp` of the two `trust.json` files | a live connect on Render after PR 4 |
| Handoff screenshots committed | skipped this loop (§10) | — | — |

### Dependencies against Ed's machine

- **No new packages** in any app.
- `tools/generate_credentials.py` runs through `uv run` with its existing inline dependencies,
  including the `cryptography<49` cap that keeps Intel Mac wheels available. It ran cleanly on
  this machine in the rolled-back build.
- **Local tooling only:** the side-by-side check serves the handoff with `python3 -m http.server`
  (macOS's built-in Python 3.9, standard library only), launched from the untracked
  `.claude/launch.json`. Nothing about it reaches the apps, CI or Render.

### Limits of the side-by-side check

- **Pending pages:** the **Check again** fallback is hidden by the pages' own script, as designed,
  but the handoff's copy doesn't hide it. The pair is compared above that form.
- **Pages that need a pending state:** reaching them locally takes a stand-in on Payroll's port
  that holds requests. That's how #82 measured the asking page.
- **Sample content:** names, dates, employers and log entries differ between the two sides, so the
  check compares structure and spacing, not every block's height.
