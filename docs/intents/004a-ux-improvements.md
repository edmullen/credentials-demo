# Intent 004a: UX improvements (Loop 4a)

## Problem
With Loop 4 shipped, a demo now runs from employer lookup through consent to a live connection.
Walking through that flow shows friction that has nothing to do with credentials. The Wallet has
no front door: `/` redirects straight into p01's credentials. There's no way to "sign out".
Headers, eyebrows and back links use too much vertical space, and the page titles name the page
instead of telling the user what to do. The consent page puts its decision below a long credential
review. The switcher doesn't say where anyone works. On Payroll, the paystub earnings table is cut
off on mobile and can't be scrolled.

## Proposed outcome
One issue, [#69](https://github.com/edmullen/credentials-demo/issues/69), the source of truth for
every copy and layout detail. In summary:

- **Wallet** (#69 items 1–10): a landing page at `/` with **Sign in** in place of the initials
  (like Payroll's), and **Sign out** at the end of the nav. A **Find your employer** button in the
  Credentials empty state. Employers listed in the switcher. Two CSS size reductions. A compact
  line for the page name and back link on every page. Page titles that name the step, not the page.
  A reworked consent page. Date of birth on the identity card.
- **Payroll** (#69, final item): the paystub earnings table scrolls horizontally on mobile.

**No Claude Design pass** (Ed, 2026-09-23). The issue is already written at mockup precision.
Only the landing page and the compact header line are new patterns, and both are small. Claude
Code builds straight from #69, and Ed reviews the running app and the PRs.

Done means: every item in #69 is visible on the live Wallet and Payroll. The Wallet's and Payroll's
existing suites still pass with updated copy assertions, and every one of the 25 people still
reaches the outcome Loop 4 designed for them.

## Affected users/systems
- **Ed**: reviews each PR on the running app in place of a design handoff.
- **`apps/wallet`**: nearly everything. Its templates, its own `cred.css`, a new `/` landing route,
  and a person-to-employers field on its people data.
- **`apps/payroll`**: the paystub table's mobile overflow only. Its headers stay as they are.
- **`tools/generate_credentials.py`**: adds employer names to the Wallet's `people.json`.
- **`apps/benefits`**: unaffected.

## Constraints
- **Record the design skip in [decisions.md](../decisions.md)** as a one-off exception to "Design
  stage uses Claude Design", not a change to the rule. With no handoff, `docs/design/loop-4a/` holds
  only the archived technical design when Loop 5 supersedes it.
- **Switcher employers are a demo aid, nothing more.** They come from the generator (one-shot,
  output committed, per decisions.md). The Wallet's lookup, connect and consent logic must never
  read them. Whether someone works for an employer is still Payroll's call.
- **The consent page's status panel changes on the consent page only** (Ed, 2026-09-23). The
  credential detail page keeps its tinted panel, so the shared `_credential_panel.html` needs a
  consent-only variant rather than a global edit.
- **The compact header line is Wallet-only** (Ed, 2026-09-23). Payroll could follow in a later loop.
- **Sign in/out is navigation, not authentication.** **Sign in** goes to p01's credentials and
  **Sign out** goes to `/`. There are still no passwords and no session.
- CLAUDE.md's rules still hold: `href="/static/cred.css"` literally, no new JavaScript, and each app
  edits only its own `cred.css`. Loop 4's retro applies to copy: match the apostrophe encoding of the
  nearest existing string.
- Per-item PRs to `main`, merged hands-off once `ci-passed` is green. The likely split: CSS and
  headers; landing page and sign in/out; consent page; switcher data; the Payroll table.

## Open questions
None remain. Settled by Ed on 2026-09-23:
- **Re-keying is accepted.** `generate_credentials.py` makes new keys on every run, so adding the
  employer field re-signs every identity credential and rewrites both apps' `trust.json`. Accept
  the churn, and don't change the script to reuse keys.
- **The Connections count uses plain pluralization**: "You have 0 connections", "You have 1
  connection".
- **When signed in, the brand mark still leads to the person's credentials**, as it does today.
  Only **Sign out** goes to `/`.
