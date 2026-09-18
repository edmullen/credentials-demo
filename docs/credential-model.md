# Credential Model

How credentials work across the three apps: who issues and verifies what, the flow the demo is
building towards, the claims each credential carries, and how closely it follows the W3C
standard. Written for GitHub issue #21.

Aligned with the **W3C VC Data Model 2.0**, secured as a JWT per **VC-JOSE-COSE** — a subset of
the standard, never contrary to it (see `docs/decisions.md`). Eligibility rules live in
[docs/benefit-programs.md](benefit-programs.md).

## 1. Target flow

This is the flow the demo is **eventually** meant to support, written before any of it is
built. Loops 2–6 each implement a slice of it; the loop column below says which. Where a loop
will build less than what is described, that is a deliberate subset, not a change of direction.

### Roles

| Party | App | Role in the flow |
|---|---|---|
| The public user | Wallet | **Holder** — receives, stores and presents credentials. The only party that ever holds all of a person's credentials. |
| A state (e.g. State of New Jersey) | none | **Issuer** of identity credentials. Not an app: identity credentials exist before the demo starts. |
| Meridian Payroll | Payroll | **Verifier** of identity, then **issuer** of income credentials. |
| The Benefits provider | Benefits | **Verifier** of identity and income, then **issuer** of benefit credentials. |

Every credential about a person carries the same **subject identifier** — the thread that ties
their identity, income and benefit credentials together, and the thing a verifier checks for
consistency across a set of credentials.

### Overview

| Phase | What happens | Built in |
|---|---|---|
| 0. Identity exists | The person already holds a state-issued identity credential | Loop 2 (#12) |
| 1. Find employer | The person records their employer in the Wallet | Loop 4 (#13) |
| 2. Connect to Payroll | Payroll verifies the person's identity and links them to their employee record | Loop 4 (#16, #22) |
| 3. Receive income credentials | Payroll issues one credential per paystub; the Wallet stores them | Loop 5 (#19) |
| 4. Apply for benefits | Benefits verifies identity and income, decides all five programs, issues credentials for the eligible ones | Loop 6 |

### Phase 0 — Identity exists

The person's state issued their identity credential before the demo begins. Nothing in the
demo performs this issuance: in Loop 2 the credentials are generated once and loaded into the
Wallet (#12).

Per the sample data (#6), 21 people hold a valid credential (18 NJ, 3 out-of-state), 2 hold a
**tampered** one, and 2 hold **none**. On receipt and on display, the Wallet verifies each
credential's signature against its issuer's public key and shows a Verified or Tampered badge.

> In a deployed system a wallet verifies a credential when it receives it and would reject a
> tampered one rather than keep it. Holding and badging a tampered credential is a demo device
> that makes an invisible cryptographic check visible on screen.

### Phase 1 — Find employer

1. The person chooses **Find your employer** in the Wallet and picks from the list of demo
   employers.
2. The Wallet records the employment relationship, including which payroll provider serves that
   employer (for every demo employer, Meridian Payroll) and where to reach it.
3. The employer appears on the Connections screen with a **Connect payroll** button. The
   Activity log records the new connection.

No credential moves in this phase. It establishes *where* the Wallet will send a request.

### Phase 2 — Connect to Payroll

Payroll needs to know that the person connecting is really one of its employees before it will
issue anything to them.

1. The person taps **Connect payroll**. The Wallet sends a connection request to Payroll.
2. Payroll replies with a **presentation request**: a list of the credentials it needs and,
   within each, the claims it needs. For Payroll the list has one entry — the identity
   credential — but it is a list, because later verifiers ask for several.
3. The Wallet shows the **consent screen** (#22): each requested credential, with the requested
   claims listed under it. Approval is **all-or-nothing** over the whole request.
   - **Deny** — nothing is shared, and the Wallet returns to its previous state.
   - **Approve** — the Wallet sends a **presentation** containing the requested credential.
4. Payroll **verifies** the presented credential: the signature checks out against the issuing
   state's public key, and the credential is within its validity period.
5. Payroll **matches** the verified identity to one of its employee records and links that
   record to the person's subject identifier. From now on Payroll knows which of its employees
   the Wallet's subject is.
6. Payroll confirms the connection. The Wallet marks Payroll as connected on the Connections
   screen and records it in the Activity log.

**When it fails:**

- **Tampered identity** — verification fails at step 4. Payroll refuses the connection, and the
  Wallet tells the person their identity credential could not be verified.
- **No identity credential** — the Wallet cannot satisfy the request at step 3. It shows that a
  required credential is missing rather than offering an Approve button that cannot work. These
  two personas are blocked here: without a connection they never receive income credentials.
- **No matching employee** — verification succeeds but step 5 finds no one. Payroll refuses:
  the person is who they say they are, but not an employee.

### Phase 3 — Receive income credentials

1. When the Wallet opens for a person, it asks each connected service for any credentials it
   has not yet received.
2. Payroll issues **one credential per paystub**, each naming the person's subject identifier
   as its subject.
3. The Wallet verifies each on receipt, stores it, and shows it under the **Income** category.
   The Activity log records what arrived.

Two paystubs per employer per month, so a person with three employers receives six income
credentials from the same issuer.

### Phase 4 — Apply for benefits

```mermaid
sequenceDiagram
    actor P as Person
    participant W as Wallet
    participant B as Benefits
    P->>B: Apply
    B->>W: Presentation request<br/>(identity + all income credentials)
    W->>P: Consent screen — every requested credential
    P->>W: Approve (all-or-nothing)
    W->>B: Presentation
    B->>B: Verify every credential<br/>Check they share one subject<br/>Evaluate all five programs
    B->>W: Outcome per program<br/>+ credentials for eligible ones
    W->>P: Results; credentials stored under Benefits
    Note over B: Determination record kept<br/>(credentials verbatim)
```

1. The person starts an application from the Benefits app.
2. Benefits sends a **presentation request** for the identity credential **and every income
   credential** — a list with several entries, which is why the request was a list from Phase 2.
3. The Wallet shows the consent screen. Approval is all-or-nothing.
4. The Wallet sends a presentation containing all the requested credentials.
5. Benefits **verifies** every credential against its issuer's key, and checks that they all
   name the **same subject** — an income credential about someone else must not count toward
   this person's income.
6. Benefits **evaluates all five programs** in one pass (docs/benefit-programs.md): residency
   from the identity credential's `state`, county from its `county`, and income summed from the
   gross pay on the income credentials.
7. Benefits returns an **outcome for every program** — eligible or denied, possibly with a
   reason — and a **benefit credential for each eligible one**. The per-program outcome is plain
   protocol data, not a credential.
8. The Wallet stores the benefit credentials under the **Benefits** category and records every
   outcome in the Activity log, **denials included** — a denial produces no credential, so the
   log is the only place the person sees it afterwards.
9. Benefits keeps a **determination record**: the presented credentials verbatim, the derived
   figures it used, the subject identifier and the outcomes. There is no applicant-facing view
   of it; it exists for a future admin view (see `docs/decisions.md`).

**When it fails:** a tampered identity credential fails verification at step 5 and every
program is denied. A person with no identity credential cannot satisfy the request at step 3.
Out-of-state identities verify successfully but fail the residency test at step 6.

### Deliberately out of the target flow

- **Presenting a benefit credential to someone else.** Proving eligibility to a third party is
  the reason benefit credentials exist, but no app in the demo asks for one.
- **Re-applying or renewing.** A second application would produce a second set of credentials;
  nothing reconciles them.
- **Revocation.** A credential, once issued, stays valid until it expires (see §5).

### Open questions in the flow

These need answers before the loops that build them, and some before this document is done:

1. **How does Payroll match a verified identity to an employee record (Phase 2, step 5)?**
   Realistically an employer matches on identity attributes such as name and date of birth.
   The alternative — a shared persona id baked into both apps' sample data — is simpler but
   means identity verification isn't really doing the matching. Leaning: match on identity
   claims, with the sample data guaranteeing uniqueness.
2. **What is the subject identifier?** VC 2.0 wants a URI in `credentialSubject.id`. A
   `urn:uuid:` per person is valid and simple; a DID is more realistic but brings key
   management with it. Leaning: `urn:uuid:`.
3. **Does the holder prove they control that identifier?** In a full implementation the
   presentation is signed by the holder's key ("holder binding"), so a stolen credential can't
   be presented by someone else. Leaning: leave presentations unsigned in the demo and record
   that as a known gap — a subset of the standard, not a contradiction of it.
4. **Does a person apply for all five programs at once, or choose?** Leaning: all five in one
   application — simpler, and it puts the pass/fail and sliding-scale programs side by side on
   one results screen.
5. **How does an application start and reach the Wallet?** In the real world, a QR code or deep
   link. In the demo, a button on the Benefits site that sends the person to the Wallet with the
   request, where the Wallet's currently selected persona responds.

## 2. Trust — issuers, keys and verification

*To be drafted.*

## 3. Claim schemas

*To be drafted.*

## 4. W3C conformance — what we adopt and what we fake

*To be drafted.*

## 5. Expiration and verification failure

*To be drafted.*
