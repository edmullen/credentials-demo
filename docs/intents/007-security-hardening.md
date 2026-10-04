# Intent 007: Security Hardening (Loop 7)

## Problem
Loop 6 completed the demo's main flow, and a security assessment of it (3 October) found the
flow sound on its happy path but leaky underneath. Credentials are bearer tokens, and the demo
hands them out:

- **Payroll's paystub page** signs a fresh paystub credential every time anyone views it, and
  prints the JWT.
- **Benefits' admin page** prints every presented credential's JWT. Its photo redaction covers
  only the decoded claims, so the photo is still inside the printed JWT.
- **The repo** holds every person's identity JWT.

So anyone can copy two JWTs and apply to Benefits as someone else without touching the Wallet.
Beyond that:

- Benefits records refused applications using **claims that never verified**, so a forged
  presentation puts a made-up named applicant on the public admin page.
- The APIs accept bodies, presentations and pending requests of **any size and number**, on a
  single free-tier worker.
- The Wallet keeps whatever a provider sends without checking **who it's about or who sent it**,
  and tells each provider the ids of credentials **other** providers issued.
- **Approve** shares what the person holds when they press it, not what the consent screen
  showed.
- No app sends **security headers**, every page loads **Google's fonts**, and CI runs with the
  **default token permissions** and tag-pinned actions.
- Nothing written down says which gaps are deliberate. An assessor can't tell "no
  authentication, on purpose" from an oversight.

The fix for the bearer-token problem itself, holder binding, needs a new credential format and
is Loop 8's work. This loop closes everything that doesn't depend on it.

## Proposed outcome
The eight issues of the Loop 7 milestone, and the decisions recorded with this intent in
[decisions.md](../decisions.md) (**Security**):

1. **No replayable credentials on public pages** (#131). Payroll's paystub page shows the claims
   of the credential Payroll *would* issue, decoded and unsigned. Viewing a page never signs
   anything. Benefits' determination page shows decoded claims, header and verification result,
   not the JWT. The Wallet's own JWT panel stays: the Wallet is the holder, and Loop 8's binding
   makes the panel harmless.
2. **Benefits keeps only verified data** (#132). A refused application keeps when it arrived,
   the reason code, and for each credential its type, digest and result. Nothing from claims that
   didn't verify. Decided applications are unchanged. Records are capped.
3. **API limits** (#133): a body-size cap (413), a cap on credentials per presentation, a cap on
   pending requests. No rate limiting; that's recorded as a residual risk.
4. **Checks on everything received** (#134). The Wallet keeps a credential only if it's about
   this person and from the provider it asked. `have` lists only that provider's credentials.
   Every verifier checks `typ` and rejects a duplicated credential id.
5. **Approve shares exactly what was shown** (#135), on both consent screens. If what's held has
   changed, the consent screen shows again.
6. **Browser hardening** (#136): `nosniff`, `Referrer-Policy`, `no-store` on pages with a
   person's data, self-hosted fonts, and a Content-Security-Policy that admits the inline polling
   scripts by hash or moves them into `static/`.
7. **CI supply chain** (#137): least-privilege `permissions:`, actions pinned to commit SHAs,
   a dependency audit.
8. **`docs/security.md`** (#138), the first thing an assessor reads:
   - the **kiosk premise**
   - assets and parties
   - threats and controls, each marked in place, Loop 8 or accepted
   - residual risks
   - the **HAIP 1.0 conformance table**, every deviation with its reason
   - the purpose of each claim Benefits collects

A **small Claude Design pass** comes first. It covers Payroll's paystub credential panel, the
determination page (decided and refused), the admin list's refused rows, and what the consent
screen says when what the person holds has changed. The rest of the loop isn't visual. Fonts move
in-app with no visible change.

Done means:
- No public page or API returns a signed credential to anyone but the Wallet that fetched it.
- A forged presentation leaves no claimed name or data anywhere.
- Every cap answers as designed.
- The Wallet discards a credential about someone else.
- Approve never shares something the screen didn't show.
- Every response carries the headers.
- CI runs least-privilege with pinned actions and an audit.
- `docs/security.md` gives an assessor the whole picture, including what Loop 8 will close.

## Affected users/systems
- **Ed**:
  - runs the small Claude Design pass
  - turns on Dependabot alerts, and considers secret scanning's non-provider patterns (#137)
  - sets the board's Status column (the `gh` token can't)
  - no new secrets this loop
- **`apps/payroll`**: the paystub page stops signing (#131), API limits (#133), `typ` check
  (#134), headers and fonts (#136).
- **`apps/benefits`**: determination and admin pages (#131, #132), what a refused application
  keeps and the record cap (#132), API limits (#133), `typ` and duplicate checks (#134), headers
  and fonts (#136).
- **`apps/wallet`**: checks on receipt and a scoped `have` (#134), the consent digest (#135),
  headers, CSP and fonts (#136).
- **`.github/workflows/ci.yml`**: permissions, pinned actions, audit (#137).
- **Docs**:
  - `docs/security.md`, new (#138)
  - decisions.md: the **Security** section, the Scope, Realism, W3C alignment and Users entries,
    the determination-record entry, and Loops 7–9. These are already amended with this intent.
  - credential-model.md: a direction-change note, with #25 and #28 now planned for Loop 8. Its
    full rewrite is Loop 8's (#139).
  - CLAUDE.md, if the inline scripts move to `static/` (its "Things that look like mistakes"
    describes them as inline).

## Constraints
- **The kiosk premise holds.** No sign-in of any kind, including a one-click persona sign-in
  (decisions.md, **Security**).
- **Don't change the credential format.** Everything stays `vc+jwt` and W3C-shaped until Loop 8.
  Nothing this loop should make Loop 8's move harder: for example, `typ` checks go in one place
  per app.
- **The demo stays explorable.** Decoded claims replace the raw JWT panels on Payroll and the
  admin page, so the teaching value stays. Caps are set well above anything a real demo session
  reaches.
- **The plan step is a merged PR before PR 1** (Loop 6 retro). It lists:
  - which UI PR measures which handoff page, at which widths
  - the test that covers each row of each outcome table, including at least one real
    cross-feature sequence (for example: hold credentials → a new paystub arrives while consent
    is open → Approve → consent shows again)
  - the date each sample credential becomes valid, against the expected live-pass date

  UI PR descriptions carry their side-by-side table.
- **PR titles trace to the design:** `Loop 7 PR Y: …`.
- **No `paths:` filters, and never cancel CI runs on `main`** (CLAUDE.md). The new audit step
  must not make `ci-passed` flaky.
- **Secrets.** Never put a key's value in a PR, issue, commit or comment. Rotate if one leaks.
- **Per-app copies.** Fonts, headers middleware and limits are each app's own code, under the
  monorepo rule.
- **Out of scope**, recorded in decisions.md:
  - holder binding and selective disclosure (Loop 8)
  - encrypted responses, signed requests and X.509 (cut, declared deviations)
  - rate limiting
  - visitor isolation
  - income completeness (the applicant's attestation is the real-world control)
  - cross-site form posts and clickjacking as findings (the kiosk)

## Open questions
- **The caps.** Body size (about 512 KB?), credentials per presentation (50?), pending requests
  (500?), Benefits' records (200?). A real presentation is about 40 KB. Settle in the design.
- **The CSP and the inline scripts.** Hash them, or move them to a file in `static/`? Moving is
  simpler to keep right, but changes a documented convention.
- **HSTS.** Render serves HTTPS. Send `Strict-Transport-Security` now, or leave it to Render?
  A wrong HSTS header is hard to undo.
- **The dependency audit.** Should it fail the required check, or run as a separate,
  non-blocking job? A network blip shouldn't block a merge.
- **The refused admin row.** Date and reason only, as decided. Does the determination page for
  a refused application still show each credential's type and result? Settle in the design pass.
- **What the consent screen says when what's held changed.** Copy for the design pass.

## Looking ahead: Loops 8 and 9
Planned now so nothing is lost. Each gets its own intent when it starts, after the previous
loop's retro.

- **Loop 8: Holder binding and selective disclosure** (milestone).
  - **#139**: all credentials move to **IETF SD-JWT VC** (`dc+sd-jwt`). credential-model §3–§4
    are rewritten. The display color needs a new home.
  - **#140**: how identity credentials get bound to their holder. Today the generator signs them
    once with keys only on Ed's machine, and it re-keys every issuer on each run. Either it
    re-signs identities with the holder keys alone, or a small runtime state issuer appears.
    Settle this first in Loop 8's design.
  - **#25**: holder keys in the Wallet from one `sync: false` secret, `cnf` in every credential,
    and a Key Binding JWT over the verifier's nonce and audience.
  - **#28**: DCQL requests name claims, and the consent screen shows them (a Claude Design
    pass). Payroll asks for the minimum. Benefits asks for the full identity; the portrait is
    still open.
- **Loop 9: optional, `deferred` issues, no milestone.** A status list for revocation (#141),
  then OpenID4VCI issuance with a simulated Payroll sign-in (#142).
