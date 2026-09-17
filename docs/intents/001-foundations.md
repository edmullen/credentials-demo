# Intent 001: Foundations (Loop 1)

## Problem
Loop 0 proved the delivery path but nothing about credentials. Three separate later loops
now need the same three answers, and each would invent its own version if asked first:

- What is in a credential, and what is the flow we are building towards? (Loops 2, 4, 5, 6)
- What are the benefit programs and what makes someone eligible? (Loop 6, but it constrains
  the credential claims in Loops 2 and 5)
- Who are the sample people, employers and paystubs? (Loops 2, 3 and 4)

The expensive failure this loop prevents: Payroll issues credentials in Loop 5 whose claims
cannot answer an income question, so Loop 6 re-issues the credential model rather than
consuming it.

## Proposed outcome
Three documents and one data set. **No app code, no deployment.**

1. **Credential model** (GitHub issue #21) — a concept of operations covering:
   - the target end-to-end flow, written out before any of it is implemented
   - which parts of W3C Verifiable Credentials the demo adheres to, and which it fakes
   - the data points for each credential type: identity, payroll, and (sketched) benefit
   - expiration, and how verification failure is represented
2. **Benefit programs and eligibility** (#7) — the five programs (Food, Health, Housing,
   Energy, Dividend) and their criteria: NJ resident, identity verified via credential,
   income range. Decisions are y/n. Deliberately kept basic: no time windows.
3. **Sample data** (#6) — 25 people, 15 NJ employers, and two September 2026 paystubs per
   person per employer, covering one-, two- and three-employer scenarios.

Done means: the three artifacts exist in the repo, and the claim lists in #21 are specific
enough that Loop 2 can hard-code an identity credential and Loop 5 can issue a payroll
credential without reopening the model.

## Affected users/systems
- **Ed** (PM and solo developer): owns the definition work; Claude drafts and researches.
- **`docs/`**: gains the credential model and the benefit program definitions.
- **No app changes.** `apps/wallet`, `apps/payroll` and `apps/benefits` are untouched, so
  no Render service redeploys this loop.
- **End users**: none yet. The sample personas defined here are what Loop 2 picks from.

## Constraints
- Demo only, no real PII: names, addresses, employers and paystubs are invented, though
  the employers are real companies operating in NJ.
- The sample data is a one-time starting resource. Each app gets its own copy of the slice
  it needs — no shared data store, package or sync script.
- Eligibility criteria stay minimal (residency, verified identity, income range). Anything
  richer is a later decision, not this loop's.
- Credentials remain signed JWTs shaped like W3C VCs over simple REST, per
  `docs/decisions.md` — this loop documents that shape, it does not upgrade it.
- Loop 6's implementation decisions stay open. This loop records only what Benefits will
  *need to ask for*, so earlier loops don't foreclose it.

## Open questions
- What format does the sample data ship in — JSON fixtures committed per app, or a
  generator script whose output is committed? The per-app copy rule holds either way.
- Which income claims does an eligibility check actually need: gross per period, pay
  frequency, period start/end, YTD? This is the highest-value thing #21 has to settle.
- Does the identity credential carry a full address or only a state? Residency checks need
  the state; the sample data includes three out-of-state users so denials are demonstrable.
- Multi-employer users mean an income check spans several payroll credentials. Does the
  target flow present several credentials in one request, and if so, should Loop 4's consent
  screen be built around a list from the start?
- Does the benefit credential get sketched now or left entirely to Loop 6?
