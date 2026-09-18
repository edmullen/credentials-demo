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
| A state (New Jersey, Michigan, New York, Ohio) | none | **Issuer** of identity credentials. Not an app: identity credentials exist before the demo starts. |
| Meridian Payroll | Payroll | **Verifier** of identity, then **issuer** of income credentials. |
| The Benefits provider | Benefits | **Verifier** of identity and income, then **issuer** of benefit credentials. |

Every credential about a person carries the same **subject identifier** — a `urn:uuid:` per
person. It is the thread that ties their identity, income and benefit credentials together, and
the thing a verifier checks for consistency across a set of credentials. It names the person;
it does not prove the presenter *is* that person (see holder binding, #25).

### Overview

| Phase | What happens | Built in |
|---|---|---|
| 0. Identity exists | The person already holds a state-issued identity credential | Loop 2 (#12) |
| 1. Find employer | The person records their employer in the Wallet | Loop 4 (#13) |
| 2. Connect to Payroll | Payroll verifies the person's identity and links them to their employee record | Loop 4 (#16, #22) |
| 3. Receive income credentials | Payroll issues one credential per paystub; the Wallet stores them | Loop 5 (#19) |
| 4. Apply for benefits | From the Wallet or the Benefits app: Benefits verifies identity and income, decides all five programs, issues credentials for the eligible ones | Loop 6 |
| 5. Present a benefit credential | The person opens a benefit credential in the Wallet and presents it to someone else | Not yet scheduled |

### Phase 0 — Identity exists

The person's state issued their identity credential before the demo begins. Nothing in the
demo performs this issuance: in Loop 2 the credentials are generated once and loaded into the
Wallet (#12).

Per the sample data (#6), 21 people hold a valid credential — 18 from New Jersey and one each
from Livonia (Wayne County, Michigan), Astoria (Queens County, New York) and Cleveland
(Cuyahoga County, Ohio) — 2 hold a **tampered** one, and 2 hold **none**. On receipt and on
display, the Wallet verifies each credential's signature against its issuer's public key and
shows a Verified or Tampered badge.

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

**Assumption:** when an employer signed up with Meridian Payroll, its employees' identities
were verified as part of that onboarding, so Payroll already knows each employee's subject
identifier. The demo does not show that onboarding; Payroll's sample employee records simply
carry each person's subject identifier.

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
5. Payroll **links** the connection to the employee record whose subject identifier matches the
   credential's subject. It does not create an account — the employee record already exists.
6. Payroll confirms the connection. The Wallet marks Payroll as connected on the Connections
   screen and records it in the Activity log.

Verification does real work at two points: the signature has to check out (step 4), **and** the
subject has to be someone Payroll already employs (step 5).

**When it fails:**

- **Tampered identity** — verification fails at step 4. Payroll refuses the connection, and the
  Wallet tells the person their identity credential could not be verified.
- **No identity credential** — the Wallet cannot satisfy the request at step 3. It shows that a
  required credential is missing rather than offering an Approve button that cannot work. This
  is reachable in **Loop 4**, not only later: the two people with no identity credential hit it
  the first time they connect. Without a connection they never receive income credentials.
- **Not an employee** — the credential verifies but no employee record carries its subject.
  Payroll refuses: the person is who they say they are, but not an employee.

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

There are **two ways in**, and they converge at the presentation request. From that point on
the flow is identical.

- **From the Wallet.** The Wallet has a **Find government services** button listing the
  services it knows about and where to reach them — a *services directory*, built as a list the
  way the employer list is. It has one entry today (Benefits); in a fuller world it would list
  many agencies, each offering its own programs. Choosing Benefits makes the Wallet ask
  Benefits for its presentation request directly. **The person never has to visit the Benefits
  app.**
- **From the Benefits app.** The Benefits app offers two options side by side:
  - **Apply here** — disabled, with the note *"Applying without a digital wallet isn't
    available yet."*
  - **Apply with Digital Wallet** — sends the person to the Wallet carrying Benefits'
    presentation request, where the Wallet's currently selected person responds. Under it:
    *"Using your digital wallet uses info from your wallet to make applying fast and
    secure."*

```mermaid
sequenceDiagram
    actor P as Person
    participant W as Wallet
    participant B as Benefits
    alt Starting from the Wallet
        P->>W: Find government services
        W->>B: Ask for a presentation request
        B->>W: Presentation request
    else Starting from the Benefits app
        P->>B: Apply with Digital Wallet
        B->>W: Redirect carrying the presentation request
    end
    Note over W: The request lists identity plus all income credentials
    W->>P: Consent screen, every requested credential
    P->>W: Approve (all-or-nothing)
    W->>B: Presentation
    B->>B: Verify every credential<br/>Check they share one subject<br/>Evaluate all five programs
    B->>W: Outcome per program<br/>plus credentials for eligible ones
    W->>P: Results, with credentials stored under Benefits
    Note over B: Determination record kept<br/>(credentials verbatim)
```

1. The person starts an application, from either entry point. **Every application covers all
   five programs** — there is no choosing among them.
2. Benefits' **presentation request** asks for the identity credential **and every income
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
9. Once the person holds benefit credentials, the Wallet **stops offering Find government
   services** and shows the credentials in its place. There is no re-applying.
10. Benefits keeps a **determination record**: the presented credentials verbatim, the derived
    figures it used, the subject identifier and the outcomes. There is no applicant-facing view
    of it; it exists for a future admin view (see `docs/decisions.md`).

**When it fails:** a tampered identity credential fails verification at step 5 and every
program is denied. A person with no identity credential cannot satisfy the request at step 3.
Out-of-state identities verify successfully but fail the residency test at step 6. In all three
cases the person holds no benefit credentials afterwards, so Find government services stays
available and they can apply again — getting the same answer. That is acceptable, and nothing
is built to prevent it.

### Phase 5 — Present a benefit credential

Not yet scheduled. The reason benefit credentials exist is so the person can prove eligibility
to someone else — a utility company applying an Energy discount, say. The Wallet will let the
person open a benefit credential and present it. No app in the demo asks for one yet, so the
verifier on the other side of this phase is undefined.

### Deliberately out of the target flow

- **Re-applying or renewing.** Once a person holds benefit credentials there is no path back to
  applying. People denied everything can apply again, but nothing reconciles repeated
  applications.
- **Revocation.** A credential, once issued, stays valid until it expires (see §5).
- **Holder binding.** Presentations are unsigned, so nothing proves the presenter is the
  credentials' subject. A subset of the standard, not a contradiction of it; deferred to #25.

### Decisions made in review

Settled on 2026-09-18, and reflected in the phases above:

1. **Payroll already knows each employee's subject identifier**, on the assumption that
   identities were verified when the employer joined Meridian Payroll. Payroll links to an
   existing employee record rather than creating an account.
2. **Subject identifiers are `urn:uuid:`.** A DID would only earn its keep with holder binding;
   #25 records switching to `did:key` if that is ever built.
3. **Holder binding is deferred** — #25, labelled `deferred`.
4. **Every application covers all five programs.**
5. **Two entry points to applying**, converging at the presentation request: Find government
   services in the Wallet, and Apply with Digital Wallet on the Benefits app.

## 2. Trust — issuers, keys and verification

A credential is trustworthy when three things hold: it was signed by the issuer it names, that
issuer is one the verifier trusts, and the issuer is trusted *for that kind of credential*.
This section says who the issuers are, where their keys live, and how an app checks all three.

### Issuers

| Issuer | Issues | Signs when | Private key lives |
|---|---|---|---|
| State of New Jersey | Identity credentials | Once, before any demo | Your machine, outside git |
| State of Michigan | Identity credentials | Once, before any demo | Your machine, outside git |
| State of New York | Identity credentials | Once, before any demo | Your machine, outside git |
| State of Ohio | Identity credentials | Once, before any demo | Your machine, outside git |
| Meridian Payroll | Income credentials | During the demo (Loop 5) | Render environment variable |
| Benefits | Benefit credentials | During the demo (Loop 6) | Render environment variable |

The states sign only when the identity credentials are generated; the signed credentials are
then committed and deployed like any other seed data. **No machine outside Render is involved
while a demo runs.**

Every key pair uses **ES256** (ECDSA on the P-256 curve) — the most widely supported algorithm
in the JOSE family that VC-JOSE-COSE builds on.

### Issuer identifiers

The VC's `issuer` is an object with an `id` (a URI) and a display `name`:

- **Payroll and Benefits** use their own deployed origins, e.g.
  `https://cred-demo-payroll.onrender.com`. They control those addresses, so the identifier is
  honest, and each can publish its public key there (see Keeping keys in step).
- **The states** have no app and no address the demo controls. They use
  `did:example:state-of-new-jersey` and so on. `did:example` is the method the W3C specs
  themselves reserve for illustration, so it is syntactically valid, self-evidently fictional,
  and never resolves anywhere. Using a real government domain such as `nj.gov` would
  misrepresent a real agency as the issuer.

### Trust lists

Each app that verifies credentials keeps **its own copy** of a trust list, per the monorepo
rule. An entry names the issuer, its public keys, and the **credential types it is trusted
for**:

```json
{
  "did:example:state-of-new-jersey": {
    "name": "State of New Jersey",
    "trustedFor": ["IdentityCredential"],
    "keys": [ { "kty": "EC", "crv": "P-256", "kid": "nj-1", "x": "…", "y": "…" } ]
  }
}
```

`trustedFor` matters: Payroll's key must not be accepted on an identity credential, and a
state's key must not be accepted on a paystub. A correctly signed credential from the wrong
kind of issuer is still rejected.

Who trusts whom:

| App | Trusts | Because it verifies |
|---|---|---|
| Wallet | All six issuers | Everything it receives and displays |
| Payroll | The four states | Identity, when a person connects (Phase 2) |
| Benefits | The four states and Payroll | Identity and income, when a person applies (Phase 4) |

Nothing needs to trust Benefits except the Wallet, until a Phase 5 verifier exists.

### Verification

Every verifying app runs the same checks, in this order, stopping at the first failure:

1. **Known issuer** — the credential's `issuer.id` is in the trust list.
2. **Trusted for this type** — the issuer's `trustedFor` includes the credential's type.
3. **Signature** — the JWT's `kid` names one of that issuer's keys, and the signature verifies
   against it.
4. **Validity window** — the current time is within `validFrom` and, if present,
   `validUntil`.

Verifiers receiving a *presentation* then add:

5. **One subject** — every credential in the presentation names the same subject identifier.
6. **Known subject** — Payroll only: the subject belongs to an existing employee record.

The order matters for what the person is told: an unknown issuer is not the same failure as a
broken signature, and an expired credential is not a forged one. What each failure looks like
on screen is §5.

### Key custody

| Where | Holds | In git? |
|---|---|---|
| Each app's trust list | Public keys | Yes — public keys are safe to publish |
| Committed seed data | Signed identity credentials, including the deliberately tampered ones | Yes — signatures are public by design |
| A local `keys/` folder on your machine | The four states' private keys | **No** — gitignored |
| Render environment variables | Payroll's and Benefits' private keys | **No** — set with `sync: false` in `render.yaml` |
| A local `.env` in `apps/payroll` and `apps/benefits` | The same keys, for running locally | **No** — gitignored; a committed `.env.example` shows the variable names |
| Tests | Throwaway keys generated at test time | Never real keys — CI has none and needs none |

The repository is public. Committing a private key would let anyone mint credentials that every
app in the demo would accept.

### Keys are disposable

Keys living only on one machine would be a liability if that machine were lost. Instead, **one
script regenerates everything**: new key pairs for all six issuers, freshly signed identity
credentials (tampered ones included), and every app's trust list. It prints the new Payroll and
Benefits private keys for pasting into Render. Losing the keys costs one run of the script and
a commit, not a reconstruction.

There is no key *rotation* beyond that: regenerating invalidates every credential signed with
the old keys. In a demo whose runtime state is reset whenever a service idles (#27), that is
acceptable.

### Keeping keys in step

A private key held in Render must match the public key committed in the other apps' trust
lists. If someone replaced Payroll's key in Render and forgot the trust lists, every credential
Payroll issued would show as **Tampered** — a configuration slip that looks like a
cryptography bug. Two guards:

- **Startup self-check.** Payroll and Benefits each commit their own public key alongside their
  code. On startup, each derives the public key from its private key and compares; on a
  mismatch, `/health` reports unhealthy with a message saying so, rather than the app quietly
  issuing credentials nothing will accept.
- **Published keys.** Each issuing app serves its public keys at `/.well-known/jwks.json`, the
  standard JOSE location, so a mismatch can be diagnosed by looking rather than guessing. It is
  also the first step towards verifiers looking keys up instead of hard-coding them.

### Decisions made in review

Settled on 2026-09-18:

1. **The regeneration script is allowed.** It is a one-shot generator under `tools/`, run by
   hand, with committed output, and nothing runs it at build or deploy time. That is distinct
   from the "no sync script" rule, which exists to rule out tooling that *keeps* copies aligned
   (it originated in a rejected proposal to sync `cred.css`). Recorded in `docs/decisions.md`;
   the same allowance covers the sample data generator (#6).
2. **The states are `did:example:` issuers.** Nothing in the demo may give the impression that
   any service in it is a real government service — now a product rule in `docs/decisions.md`.

## 3. Claim schemas

*To be drafted.*

## 4. W3C conformance — what we adopt and what we fake

*To be drafted.*

## 5. Expiration and verification failure

*To be drafted.*
