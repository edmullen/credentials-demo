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
2. **Benefit programs and eligibility** (#7) — **done**, in
   [docs/benefit-programs.md](../benefit-programs.md). The five programs and their criteria:
   valid identity credential, NJ residency, and an income test. Food, Energy and Housing are
   pass/fail; Health (a discount on a $750/month plan) and Dividend (a monthly payment) are
   calculated on sliding scales. Deliberately kept basic: no time windows, no household size.
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
  it needs — no shared data store or package. A one-shot generator under `tools/` whose output
  is committed is allowed (`docs/decisions.md`).
- Eligibility criteria stay minimal (residency, verified identity, income range). Anything
  richer is a later decision, not this loop's.
- Credentials remain signed JWTs shaped like W3C VCs over simple REST, per
  `docs/decisions.md` — this loop documents that shape, it does not upgrade it.
- Loop 6's implementation decisions stay open. This loop records only what Benefits will
  *need to ask for*, so earlier loops don't foreclose it.

## Open questions
- What format does the sample data ship in? A one-shot generator under `tools/` with
  committed output is now allowed (`docs/decisions.md`), so either that or hand-written JSON
  fixtures is open to #6. The per-app copy rule holds either way.
- Which income claims does an eligibility check actually need? Settled in
  [docs/benefit-programs.md](../benefit-programs.md): **gross** pay per period, the period
  dates and the employer, summed across all of a person's paystub credentials and annualized
  ×12 — monthly, un-annualized, for Dividend.
- Does the identity credential carry a full address, or only what eligibility needs? **State
  and county are both required claims** — state for the residency test, county to select the
  Housing threshold (30% of county AMI). Whether a street address is carried for realism is
  still open.
- Multi-employer users mean an income check spans several payroll credentials, so a request
  is a **list** of requested credentials — one element in Loop 4, several in Loop 6. Decided.
  What follows for the flow document:
  - Approval is **all-or-nothing** over the whole request, not per credential. Decided: it
    matches how real presentation requests work, and the list shape leaves per-credential
    approval open if it's ever wanted.
  - When the Wallet doesn't hold a requested credential, the consent screen says so and
    offers no Approve button. Decided — and reachable in **Loop 4**, not only later: the two
    people with no identity credential hit it when they connect to Payroll (#22).
- Credentials are grouped for the user by **category** — Identity, Income, Benefits — not by
  issuer, which is a developer's model rather than a user's. The Wallet derives the category
  from the credential's `type`, so Loop 6 adds a group as a data change, not a layout change —
  but the category is not itself a signed claim (docs/credential-model.md §3).
- The five benefit programs issue **one credential type with the program as a claim**, five
  times over — not five types. Decided: identical to the user (five cards under a Benefits
  heading), but one schema and one eligibility code path. Its `credentialSubject` carries
  `program` plus **named claims** for what that program determined — `monthlyPayment` for
  Dividend, `discountPercent` and `planCost` for Health. There is **no `decision` claim**: a
  denial produces no credential, so holding one means eligible.
- Credentials follow the **W3C VC Data Model 2.0**, secured per VC-JOSE-COSE — a subset,
  never contrary (`docs/decisions.md`). The flow, trust model and keys are in
  [docs/credential-model.md](../credential-model.md).
