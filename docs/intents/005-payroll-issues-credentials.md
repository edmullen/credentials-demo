# Intent 005: Payroll Issues Credentials (Loop 5)

## Problem
Loop 4 connected the Wallet to Payroll, but the connection does nothing yet. A person's income
exists only as paystubs on Payroll's screens, not as credentials they hold, so Benefits (Loop 6)
has nothing to verify. Payroll has only ever been a *verifier*. It has no signing key, and no
app trusts it as an issuer.

## Proposed outcome
Phase 3 of [credential-model.md §1](../credential-model.md#phase-3--receive-income-credentials),
tracked as #19:

1. **Payroll becomes an issuer.** It gets its own key pair from the generator
   ([§2](../credential-model.md#2-trust--issuers-keys-and-verification)), with the private key
   held in Render and a local `.env`, the startup self-check, and `/.well-known/jwks.json`. It
   issues one `PaystubCredential` per paystub
   ([§3](../credential-model.md#paystub-credential)). The paystub and its credential are **two
   separate but aligned artifacts** recording the same pay period. The credential has its own
   `urn:uuid:`, computed from the paystub's id so it comes out the same every time. Nothing
   is stored, and a restart can't produce a duplicate. `validFrom` is the **pay date**. Payroll
   signs whenever asked. The signature bytes differ each time, but the Wallet matches
   credentials by id, so it doesn't matter.
2. **The Wallet fetches** from each connected service right after a successful connection and
   again whenever the person's credentials page opens. It verifies what arrives, skips ids it
   already holds, and shows the rest under **Income**. The Activity log records the arrivals.
   Cold starts reuse Loop 4's pending pattern and **Check again**.
3. **Issuer branding is in scope** (the decision #19 asks for). Payroll signs a `renderMethod`
   display hint into each credential, and the Wallet renders income cards in Payroll's color
   (hue 255), not its own amber. The "Deferred (#19)" row in credential-model §4 changes.
4. **Payroll shows its side.** Each paystub page gets a credential panel with the credential id,
   and the signed claims next to the paystub they came from. There is no per-paystub delivery
   status. Payroll's Activity page logs each delivery instead.

A **medium Claude Design pass** comes before the build. It covers the Income category and card,
the income credential detail, the fetch/arrival states, and Payroll's credential panel.

Done means: for any connected person of the 25, every paystub arrives in the Wallet exactly once,
shows as **Verified** in Payroll's color, and is visible from the matching paystub in Payroll.

## Affected users/systems
- **Ed**: runs the Claude Design pass, and pastes Payroll's new private key into Render.
- **`apps/payroll`**: signing, the issuance endpoint, the startup self-check, JWKS, the paystub
  credential panel, and Activity.
- **`apps/wallet`**: fetch-on-connect and fetch-on-open, the Income category and card, branding,
  and trusting Payroll for `PaystubCredential`.
- **`apps/benefits`**: its trust list gains Payroll's key (generator output only; no code).
- **`tools/generate_credentials.py`**: re-keys every issuer and adds Payroll. Every committed
  identity credential is re-signed as a result.- **`render.yaml`**: Payroll's first secret (`sync: false`).

## Constraints
- **Plan before code** (Loop 4a retro): write the reconciliation and have the side-by-side setup
  running before the first build PR. A clean side-by-side table is a merge condition, alongside
  green CI.
- Write the first test from credential-model §3's paystub example (carried over from Loop 4).
- `trustedFor` must hold. Payroll's key is refused on identity credentials, and a state's key
  is refused on paystubs.
- Runtime state stays volatile and in memory (decisions.md). The stable ids mean a restart
  doesn't create duplicates in the Wallet.
- JavaScript is allowed only as progressive enhancement. Per-issue PRs, hands-off merges once
  CI is green.

## Open questions
- Which `renderMethod` shape to use: the W3C VC Render Method draft's, or a minimal subset?
  Record the choice as a §4 decision.
- Does the Wallet ask for "only what I haven't received" (sending held ids), or fetch
  everything and filter locally? Phase 3 implies the former.
