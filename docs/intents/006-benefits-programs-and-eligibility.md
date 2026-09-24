# Intent 006: Benefits Programs and Eligibility (Loop 6)

## Problem
By the end of Loop 5 a person can hold a verified identity and a month of signed income. Nothing
uses it. The Benefits app is still Loop 0's placeholder page. The Wallet has a Benefits category
with nothing in it, and Phase 4, the point of the whole demo, is unbuilt. Benefits has never
verified a credential or signed one. It holds no key, and nothing trusts it.

## Proposed outcome
Phase 4 of [credential-model.md §1](../credential-model.md#phase-4--apply-for-benefits), in the
nine issues of the Loop 6 milestone:

1. **Benefits publishes its programs** (#20). A landing page with five program cards, and a page
   for each program with its qualification requirements, drawn from
   [benefit-programs.md](../benefit-programs.md). Each page offers **Apply with Digital Wallet**
   next to a disabled **Apply here**. There is no application form on the Benefits app.
2. **Benefits decides** (#104, #105). An eligibility engine covers all five programs and is
   tested against the oracle in [sample-data.md](../sample-data.md#expected-outcomes). Benefits
   gets its own key, trust list, self-check and JWKS, following Payroll's Loop 5 pattern. It
   answers with a presentation request for identity **and every income credential**, verifies
   what it receives (checks 1–5), decides every program, and keeps a determination record.
3. **The protocol follows Loops 4 and 5.** The reply to the presentation carries a **connection
   id and all five outcomes**, denials included, each with a reason code. The **credentials**
   come afterwards, through the same call 3 fetch the Wallet already uses for Payroll (#106).
   Benefits becomes a **connection** in the Wallet, which makes re-enrollment possible later.
   This amends Phase 4 step 7, which had outcomes and credentials arrive in a single response.
4. **The Wallet applies** (#107). **Find government services** sits on the Credentials page
   between Identity and Income, until the person holds a benefit credential. It opens a services
   directory with one entry. Choosing it leads to consent over every credential, a pending page,
   then a **results screen**. A person with no income credentials can't apply. The Wallet tells
   them to connect their payroll provider through **Find your employer**.
5. **The determination should feel like a payoff, not a receipt.** Behind the pending page the
   Wallet sends the presentation and immediately fetches the credentials. So the person sees one
   moment, which leads with what they got: "You qualify for N programs", each benefit in its
   program color with the figure that matters. Denials come below, one plain line each, and are
   logged in Activity. The connection itself gets no emphasis. If the fetch fails, the outcomes
   still show, with the credentials "on the way".
6. **The second way in** (#108). Apply with Digital Wallet sends the person to the Wallet with
   Benefits' request attached. If nobody is signed in, the Wallet asks them to sign in, then
   carries on to consent. Results show in the Wallet. There's no redirect back.
7. **Benefit credentials** (#106, #109). One `BenefitCredential` per eligible program. Claims
   follow [§3](../credential-model.md#benefit-credential), with `discountPercent` to one
   decimal, matching the oracle (Grace: 92.4). The Wallet derives Health's monthly price from
   that signed percent ($750 × 7.6% = $57.00), not from the unrounded formula ($56.80): the
   credential asserts the entitlement, and the money is derived from it
   ([benefit-programs.md](../benefit-programs.md)). The `id` is random, validity is 12 months, and each credential is signed with its
   program's hue. The Wallet shows a Benefits section with a card and a detail page for each.
8. **Program colors on the hue-only rule.** Energy 24 (#CF4444), Food 169 (#338067), Housing 342
   (#93537C), Dividend 121 (#7E9339), Health 223 (#3B839B). The signed value is the Wallet's
   recipe, `oklch(0.46 0.11 H)`, as Payroll's is. The hint's type is renamed from
   `CredDemoIssuerColor` to `CredDemoCardColor` (#110), since one issuer now signs five colors.
9. **A lightweight admin view** (#111). A list of applications grouped by person. It opens onto
   a determination page that lays out, program by program, the submitted data, what the checks
   decided, and the credentials used (decoded and raw).

A **large Claude Design pass** comes before the build, because nearly every screen this loop is
new: Benefits' landing, program pages and admin views, and the Wallet's services entry,
multi-credential consent, results screen, benefit cards and detail. The results screen is the
loop's centerpiece and deserves the most design attention.

Done means: for each of the 18 NJ residents with a verified identity, applying from either entry
point gives the oracle's outcome for every program, shown on the results screen. It also puts one
credential per eligible program in the Wallet in its program color, and the whole determination
in Benefits' admin view. The three out-of-state people get `not_nj_resident` for everything. The
four with a tampered identity or none can't reach Benefits.

## Affected users/systems
- **Ed**: runs the Claude Design pass. Pastes new keys into Render: Benefits' first key, **and
  Payroll's again**, because the generator re-keys every issuer. The values come in chat, never
  on GitHub.
- **`apps/benefits`**: everything above, from the placeholder to a verifier, issuer and admin
  view. Its first runtime state, secret, trust list and outbound configuration (the Wallet's
  URL).
- **`apps/wallet`**: the services directory, Find government services, the no-income gate,
  multi-credential consent, the results screen, the redirect entry, Benefits as a connection,
  benefit cards and detail, trusting Benefits for `BenefitCredential`, and the rename.
- **`apps/payroll`**: the rename only, plus the re-keyed signing key.
- **`tools/generate_credentials.py`**: adds Benefits (`benefits-1`, its `.env`, `issuer.json`,
  and trust entries in the Wallet and Benefits). Every identity credential is re-signed as a
  result.
- **`render.yaml`**: `BENEFITS_SIGNING_KEY` (`sync: false`).
- **`.claude/launch.json`**: the Wallet also pointed at the local Benefits, and Benefits at the
  local Wallet.
- **Docs**: decisions.md, which amends "admin experience deliberately unplanned", the Loop 6
  boundary text and the renderMethod name. credential-model.md §1 Phase 4 steps 7 and 9, plus
  its "When it fails" paragraph (a tampered identity is now stopped at Payroll, so it never
  reaches Benefits), and §4's renderMethod row.

## Constraints
- **Plan before code** (Loop 4a retro, held in Loop 5). The reconciliation and side-by-side setup
  are finished before the first build PR. A clean side-by-side table is a merge condition,
  alongside green CI.
- **Write out every outcome table before keying a display rule on it** (Loop 5 retro). This loop
  has verification outcomes (five), refusal codes, and per-program eligibility outcomes. For each
  card, badge, hue and message, decide every value explicitly, not "the happy path and
  everything else".
- **Test against a moving clock, not only a fixed one** (Loop 5's hue bug). Benefit credentials
  are valid from the moment of determination, so check `validFrom` at "now" live before calling
  the loop done.
- **The oracle is the spec.** Tests copy sample-data.md's expected outcomes into the Benefits
  app (tests can't read `docs/`). The Health discount the engine returns, the credential signs and
  the admin view shows is one number, rounded the way the oracle's generator rounds it (to the
  cent half-up, then to one decimal), so an x.x5 value can't land a tenth off.
- **`trustedFor` holds.** Benefits trusts the states for identity and Payroll for paystubs only.
  The Wallet trusts Benefits for `BenefitCredential` only.
- **Runtime state stays volatile.** Connections and determination records are lost when Benefits
  idles, and that's accepted. There is no reset: holding a benefit credential removes Find
  government services for good, and removing the Benefits connection keeps the credentials.
- **Secrets.** Never put a key's value in a PR, issue, commit or comment (CLAUDE.md). Rotate if
  one leaks.
- **Deferred, still:** holder binding (#25), selective disclosure (#28), partial income from
  unconnected payers (only matters once there's more than one payroll or 1099 issuer),
  re-enrollment, revocation, and Phase 5.
- JavaScript only as progressive enhancement. Per-issue PRs, and hands-off merges once CI is
  green.

## Open questions
- **How does the request ask for "every income credential"?** DCQL's per-query `multiple` flag
  is the natural fit. Settle it in the design and record it against credential-model §4.
- **How does the redirect carry the request?** By reference (a request id Benefits can resolve),
  or inline in the URL? My lean is by reference: short URLs, and nothing personal in a query
  string.
- **Program display names.** The Wallet and Benefits each hold their own list (monorepo rule).
  The design settles the names ("Food Assistance", …) once for both.
- **Is the large design pass one session or two?** Given the usage window, splitting it into
  Benefits (program pages, admin) and Wallet (apply flow, results, cards) may be kinder, with one
  shared `cred.css` carried between them.
