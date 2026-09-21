# Intent 002: Wallet Stands Up (Loop 2)

## Problem
The Wallet is a styled placeholder: one page, one hard-coded name in the header, no
credentials and no people. Loop 1 defined what a credential is
([docs/credential-model.md](../credential-model.md)) and who the 25 people are
([docs/sample-data.md](../sample-data.md)), but nothing consumes either, and no credential
in this project has ever been signed or verified.

Until it is, the central claim of the demo — that a signature makes tampering visible — is
only written down. Loop 4 also can't start: Payroll verifies an identity credential the
Wallet presents, so the credential has to exist, and the Wallet has to hold it, first.

## Proposed outcome
The Wallet holds real, signed credentials for real sample people, and shows whether each
one can be trusted. Closes #10, #12, #14, #15, #26 and #11.

1. **Signed identity credentials exist.** A one-shot generator under `tools/` creates key
   pairs for the four states, signs an identity credential for each of the 23 people who
   has one, tampers the two that `identity_status` marks tampered, and writes the Wallet's
   trust list. Output committed; private keys gitignored
   ([credential-model.md §2](../credential-model.md#2-trust--issuers-keys-and-verification)).
2. **The Wallet is populated** (#10): all 25 people, switchable from the footer, with the
   selected person in the URL path — no server-side session this loop.
3. **Credentials display and verify** (#12): previews on the landing page including the
   person's photo, a detail view, and a badge from real verification —
   **Verified** or **Tampered**, per
   [§5](../credential-model.md#5-expiration-and-verification-failure). Ray Miller and Megan
   Doyle hold nothing, so the empty state is reachable.
4. **Connections and Activity screens** (#14, #15) exist as navigable placeholders.
5. **Each app wakes the other two** on startup (#26), and the footer and README say plainly
   that this is a fictional demonstration (#11).

**Design comes before build.** Most of these screens have no Loop 0 mockup. Ed and Claude
write a design brief, Claude Design produces `docs/design/loop-2/`, and `/design-sync`
imports the repo's real `cred.css` back first (`docs/decisions.md`).

Done means: for any of the 25 people, the Wallet shows their credentials and the right
badge; altering a committed credential by hand flips it to Tampered.

## Affected users/systems
- **Ed**: writes the design brief, reviews the design handoff, runs the generator, sets no
  Render secrets this loop.
- **`apps/wallet`**: the loop's substance — templates, verification, its copy of the sample
  data and photos, its trust list.
- **`apps/payroll`, `apps/benefits`**: #26 only, so all three services redeploy.
- **`tools/`**: gains the key and credential generator. **`keys/`**: new, gitignored.
- **End users**: the 25 sample people become selectable for the first time.

## Constraints
- **Per-item PRs to `main`**, one branch per issue, merged as each finishes — not a loop
  branch. Settled at the start of this loop from the Loop 1 retro: closing keywords fire,
  CI needs no change, and Render deploys item by item so breakage surfaces immediately.
- Each app copies the slice of sample data it needs; the Wallet takes all 25 people. No
  shared package, no app reading outside its own directory.
- **JavaScript is not ruled out.** The Loop 0 pages have none because the design handoff
  specified none (`docs/design/loop-0/README.md`), not because the project decided against it —
  `docs/decisions.md` is silent on it. The Loop 2 design brief settles whether these screens use
  any, and treats "no client-side framework or bundler" as a separate question from "no script
  at all".
- The persona switcher is **its own page**, not a footer dropdown: room for the metadata that
  screen will likely want later.
- ES256, VC Data Model 2.0 over VC-JOSE-COSE, `did:example:` state issuers — a subset of
  the standard, never contrary to it.
- The tampered badge comes from a signature that genuinely fails, never from a flag.
- **Link, don't restate.** This document and the issues say *what* to build; the reference
  docs say *how*. Loop 1's improvement.

## Open questions
- **The key generator covers the four states only.** Decided: Payroll's and Benefits' keys,
  the Render env vars, the `/health` self-check and `/.well-known/jwks.json`
  ([§2](../credential-model.md#2-trust--issuers-keys-and-verification)) arrive in Loops 5
  and 6, when those apps first sign something. The script is written to be extended.
- **#12's demo-only tamper link is dropped.** Decided: Victor Moreno and Carmen Diaz already
  hold genuinely tampered credentials, so switching persona demonstrates it without a
  demo-only mutation path in the verification code. Record the change on #12.
- **Persona selection lives in the URL** (`/p/p01/…`). Decided: no cookie and no server
  state, so it survives a Render spin-down and #27 stays wholly Loop 4's.
- **Nothing is stored this loop.** Decided: the Wallet re-reads the committed credentials on
  every request. There is nothing yet to write.
- **Out-of-state people display like everyone else.** Decided: Emily Carter, Nikos Pappas and
  Jamal Wright get no special treatment. The Wallet is not an NJ app — the NJ majority is a
  property of the demo data, and any valid state credential displays the same way. Residency
  first matters at eligibility, in Loop 6.
- **The Activity screen shows nothing real.** Decided: #15's single sample item, establishing
  styling and navigation only. Nothing in Loop 2 generates an event.
