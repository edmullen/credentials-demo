# Intent 003: Payroll Stands Up (Loop 3)

## Problem
Payroll is still Loop 0's placeholder: one styled page, no people, no data of its own. Loop 1
generated 15 fictional employers and 64 paystubs ([docs/sample-data.md](../sample-data.md))
and nothing consumes them. Loop 2 proved the pattern on the Wallet — a per-person,
server-rendered app over a committed slice of that data — and Payroll has yet to follow.

Loop 4 can't start until it does. Payroll's inbound connection and verification request assume
an employee record exists to attach a Wallet connection to, and that record has to carry the
person's `subjectId` before anything can match the two sides up.

## Proposed outcome
Payroll becomes Meridian Payroll: an employee self-service portal where each sample person can
see their own paystubs. Three issues, one PR each: #17, #18 and #48.

1. **Payroll is populated** (#17): its own copy of the people, employers and paystubs it needs,
   switchable from the footer as in the Wallet, the person in the URL path — no session. Each
   employee record carries the person's `subjectId` (`urn:uuid:`), which #16 uses in Loop 4.
2. **Paystubs display** (#18): the account landing page carries **a section per employer**,
   each listing that employer's paystubs by pay date, each item linking to a full paystub detail
   view, with navigation back.
3. **The peer-wake retry is finished** (#48), last: retest the 429 retry against Render with
   all three services idle, drop the temporary diagnostic logging in the Wallet's `app/peers.py`,
   and port the retry to Payroll's and Benefits' copies.

**Design comes before build.** A *medium* Claude Design pass: `cred.css` and the Loop 2 Wallet
pages go over as files, and what comes back is committed under `docs/design/loop-3/`. The
switcher and the existing components are reused, not redesigned. The paystub is the one new
component, and it is asked for **without options** — it should follow real paystub layout and
typographic conventions closely enough to read as one.

Done means: for any of the 25 people, Payroll lists their paystubs and opens each one in full.

## Affected users/systems
- **Ed**: reviews the design handoff, budgets the Claude Design session against the Loop 2
  overrun, runs the idle retest for #48 on Render.
- **`apps/payroll`**: the loop's substance — its data slice, templates, switcher and paystub
  views.
- **`apps/wallet`, `apps/benefits`**: #48 only — the Wallet loses its diagnostic logging, both
  gain the retry.
- **`tools/`**: unchanged. The sample data already exists; nothing is regenerated.

## Constraints
- **Payroll holds only the slice it needs**, per the monorepo rule — people, employers and
  paystubs, copied in, no shared package and no reading outside its own directory. In practice
  that slice is all 25 people, since every one of them has paystubs. **Ray Miller and Megan
  Doyle are included**, though neither has an identity credential: Meridian employs and pays
  them, and what they can't do is connect a wallet
  ([sample-data.md](../sample-data.md#people)). Excluding them would make the credential
  look like a condition of employment, and would take their Loop 4 and Loop 6 demonstrations
  with it.
- **Employee view now, admin later.** The viewer is the person whose record it is. A
  Meridian-side admin or employer view is deliberately unplanned, as the Benefits admin view
  already is in [decisions.md](../decisions.md).
- **Nothing is signed this loop.** Payroll's keys, `/.well-known/jwks.json` and credential
  issuance are Loop 5
  ([credential-model.md §2](../credential-model.md#2-trust--issuers-keys-and-verification));
  the connection and consent flow is Loop 4. Paystubs here are display only.
- **Five people hold more than one employer** — p06, p17 and p25 have two, p07 and p08 have
  three — so the landing page is **a section per employer**, not one list with the employer on
  each row. This narrows #18, which asks for a single "Paystubs" heading with employer name on
  each item; record the change on #18. The other twenty people see one section, which the design
  should not make look like a mistake.
- **No year-to-date figures.** They aren't generated, and deriving them from the two committed
  September stubs would show a two-period total labelled as a year. Recorded as
  [#50](https://github.com/edmullen/credentials-demo/issues/50), which lists what a real YTD
  would touch — the generator first, then the detail view, the list, and the Loop 5 and 6 claim
  and oracle.
- **Withholding is an approximation for display only** ([sample-data.md](../sample-data.md#paystubs));
  eligibility uses gross pay alone, in Loop 6. The detail view shouldn't imply otherwise.
- **Per-item PRs to `main`**, one branch per issue, closing keyword only in the PR that finishes
  that issue. Settled in Loop 2 and worked.
- No JavaScript and no bundler; `href="/static/cred.css"` literally; copy, class names and ARIA
  verbatim from the mockups ([CLAUDE.md](../../CLAUDE.md)).
- **The plan step is a reconciliation pass**, not just a breakdown — Loop 2's improvement. Each
  mockup against the design text, each acceptance criterion against the mechanism that satisfies
  it, and each new dependency against an Intel Mac with no Homebrew, before any code.
- **Link, don't restate.** This document and the issues say *what*; the reference docs say *how*.

## Open questions
- **No empty state is reachable in Payroll this loop**, since all 25 people have paystubs. Ray
  Miller and Megan Doyle — the Wallet's empty state — appear here like everyone else; what they
  lack first matters when connecting in Loop 4.
- **#48 is to be solved, not timeboxed.** The retest needs all three services genuinely idle and
  Render answers a wake-up with `429` only some of the time, so reproducing the gate may take
  several attempts across separate sittings. If it still can't be reproduced, the next step is
  more instrumentation, not closing the issue on the local test.
