# Intent 004: Wallet and Payroll Connect (Loop 4)

## Problem
Wallet and Payroll are still parallel and unlinked: Payroll displays paystub data (Loop 3) and
Wallet displays hard-coded identity credentials (Loop 2), but no wallet user has ever proven
their identity to Payroll or been recognized as an employee. Loop 5's income-credential issuance
depends on that link existing first. This is also the project's first loop that *stores*
anything at runtime rather than only displaying seed data — a real service-to-service call and
some server-held state, not just two apps rendering their own committed data.

## Proposed outcome
Three issues, matching [credential-model.md §1](../credential-model.md), Phase 1 (Find employer)
and Phase 2 (Connect to Payroll):

1. **Wallet — Employer lookup** (#13): pick an employer from the sample list, see it on the
   Connections screen with a **Connect payroll** button, remove it, Activity records both.
2. **Payroll — Receive connection request and verify identity credential** (#16): an inbound
   endpoint, signature and trust-list verification, linking to the existing employee record by
   subject identifier — refusing with a specific reason on each failure.
3. **Wallet — Consent screen for a verification request** (#22): a pending state while waiting
   on Payroll, the requested credential and every claim it contains, approve/deny (all-or-
   nothing), a missing-credential state, Activity and Connections updated on approval.

Failure paths are already specified (credential-model.md §1 Phase 2): tampered identity, no
identity credential (Ray Miller and Megan Doyle hit this the first time they connect — see
[003](003-payroll-stands-up.md)), and valid-but-not-an-employee.

Design comes before build: a *medium* Claude Design pass, reusing the switcher and existing
components; the lookup and consent-screen states are the new pieces.

Done means: for any of the 25 people, choosing an employer and approving the request either
connects them to Payroll (visible on Connections, logged in Activity) or shows the one correct
failure reason — and the two people without an identity credential hit the missing-credential
state cleanly.

## Affected users/systems
- **Ed**: reviews the design handoff; owns the persistence call below and can revisit it later;
  re-tests the Render-origin traffic question once #16's real endpoint exists.
- **`apps/wallet`**: employer lookup, consent screen, Connections and Activity updates.
- **`apps/payroll`**: inbound connection endpoint, verification, employee-record link, failure
  responses.
- **`apps/benefits`**: unaffected this loop.
- **`tools/`**: unaffected — no new or changed sample data.

## Constraints
- **State is volatile, by decision** (#27, 2026-09-22): connections live in memory/on-disk only,
  no database — consistent with "no shared data store" in
  [decisions.md](../decisions.md#technical-defaults). On-disk buys nothing over in-memory here,
  since Render's free tier has no persistent disk either. Accepted consequence: any of the three
  apps restarting (idle spin-down after ~15 min, or a redeploy) forgets what it stored. Because
  the three apps idle independently, one can outlive another's memory of the same connection —
  e.g. Wallet still shows "Connected" after Payroll has restarted and actually forgotten the
  link. Treat that as a named demo limitation, not something to engineer around. Revisit only if
  it becomes a real problem in practice — real persistence (Render's free Postgres) stays a later
  option, not this loop's.
- **Per-person demo reset** (#27's other half) is **out of scope** for Loop 4; it depends on the
  persistence answer above and belongs in its own later issue.
- **Verification badges don't depend on Payroll being awake.** Every app checks a signature
  against its own committed trust list ([credential-model.md §2](../credential-model.md#2-trust--issuers-keys-and-verification)),
  never a live call to the issuer. Nothing in this loop should make the Wallet fetch Payroll live
  just to render a badge.
- **Cold starts are expected, not failures.** A plain, non-browser `curl` against Payroll's live
  `/health` returned 200 in 22.5s cold, 0.14s warm on the immediate retry — no automated-traffic
  gate for that origin and pattern. The pending-state UI (Wallet waiting on Payroll) must
  tolerate a slow first response rather than treat it as an error.
- **Unresolved by that check:** it came from an external IP, not Render's own network, so it
  doesn't rule out the Render-to-Render gate Loop 3 found (#48). Re-test with the real endpoint
  once #16 exists, before calling the flow done. If it does gate, the pending state needs
  wording distinct from a verification failure.
- Per-item PRs to `main`, one branch per issue (#13, #16, #22) — settled in Loop 2, held since.
- No JavaScript, no bundler; `href="/static/cred.css"` literally; copy, class names and ARIA
  verbatim from the mockups ([CLAUDE.md](../../CLAUDE.md)).
- **The plan step is a reconciliation pass** (Loop 2's improvement, held through Loop 3): each
  mockup against the design text, each acceptance criterion against the mechanism that satisfies
  it, each new dependency against an Intel Mac with no Homebrew — before any code.
- **Link, don't restate.** Flow mechanics live in credential-model.md §1 Phases 1–2 and §2; this
  document says what changes and what's still undecided.

## Open questions
- Whether Render's own network traffic gates the connection request the way it gated peer-wake
  pings (#48) — not answered by the external `curl` check above; needs #16's real endpoint to
  test.
- Whether "never connected" and "connection lost to a restart" should look different to the
  wallet user, or whether it's acceptable for a lost connection to just read as "not connected
  yet," with no explanation for why it disappeared. A copy/UX question as much as a technical
  one — worth settling before design.
