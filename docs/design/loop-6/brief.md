# Design Brief: Loop 6 — Benefits Programs and Eligibility

These are the requirements for the Claude Design handoff that Loop 6 builds from. The brief is
written before design starts. The handoff itself (`README.md`, `index.html`, `benefits/`,
`wallet/`) lands beside this file.

Context: [Intent 006](../../intents/006-benefits-programs-and-eligibility.md) ·
[credential model §1, Phase 4](../../credential-model.md#phase-4--apply-for-benefits) ·
[benefit credential schema](../../credential-model.md#benefit-credential) ·
[benefit programs and rules](../../benefit-programs.md) ·
[expected outcomes](../../sample-data.md#expected-outcomes) ·
[Loop 5 handoff](../loop-5/README.md) · [Loop 4a handoff](../loop-4a/README.md) ·
[Loop 0 handoff](../loop-0/README.md) · issues
[#20](https://github.com/edmullen/credentials-demo/issues/20),
[#104–#111](https://github.com/edmullen/credentials-demo/milestone/7)

## How to run this brief: two sessions, Benefits first

This loop is large, so it runs as **two Claude Design sessions**, in order:

| Session | Read | Designs | Writes |
|---|---|---|---|
| **1, Benefits** | §1–§4 and **Part A** (§5) | Benefit Agency's landing and program pages, and the admin view | `benefits/`, `index.html`, `README.md` (Part A section) |
| **2, Wallet** | §1–§4, **Part B** (§6), and session 1's `README.md` | Applying from the Wallet, the results screen, benefit credentials | `wallet/`, extends `index.html` and `README.md` (Part B section) |

**Session 1: skip Part B.** Session 2 skips Part A, but takes session 1's decisions from its README
as settled: the program names, how program colors work, and the wording of each outcome. §7
(constraints) and §8 (deliverables) apply to both sessions.

## 1. What this is

This is a demo of verifiable credentials across three fictional apps. By now a person in the
**Wallet** holds a verified identity credential (Loop 2) and a month of signed income credentials
from **Meridian Payroll** (Loop 5). Nothing uses them yet. This loop gives them a purpose.
**Benefit Agency** publishes five programs. A person applies from their Wallet by sharing their
credentials. Benefit Agency verifies them, decides all five programs at once, and issues a
credential for each program the person qualifies for.

The story this loop has to tell on screen: *what used to take paperwork now takes one tap of
consent.* The person never fills in a form or uploads a pay stub. They see what is being shared,
approve it, and get their answer.

**The determination should feel like a payoff, not a receipt.** Ed set this as the loop's goal.
The results screen (§6.6) is the centerpiece of the loop and deserves the most design attention.

## 2. Pass depth: large

Nearly every screen is new. Three things are real design problems, and deserve options when
there's a real choice to make:

- **The results screen** (§6.6): making a determination feel like good news, while still being
  honest about denials.
- **Program colors next to app and status colors** (§3.2): five new colors, sitting on Benefit
  Agency's teal and next to the Wallet's badges.
- **The admin determination page** (§5.4): making a machine decision readable, one program at a
  time.

Everywhere else, make **one proposal, not options**.

## 3. Shared facts: both sessions

### 3.1 The five programs

Full rules are in [benefit-programs.md](../../benefit-programs.md). What each program gives, and
the figure that matters to the person:

| Code | Working name | Shape | What a credential says | Key figure |
|---|---|---|---|---|
| `food` | Food | Pass/fail: annual income ≤ 185% FPL ($29,526) | Eligible | none |
| `energy` | Energy | Pass/fail: annual income ≤ 60% of State Median Income ($30,000) | Eligible | none |
| `housing` | Housing | Pass/fail: annual income ≤ 30% of **county** AMI (21 limits) | Eligible | none |
| `health` | Health | Sliding scale: a discount on a $750/month plan anyone can buy | `discountPercent` (one decimal) and `planCost` | The discount and the monthly price, e.g. "92.4% off: $57.00 a month" |
| `dividend` | Dividend | Sliding scale: $100 base plus a bump that tapers to $0 at $1,200/month | `monthlyPayment` | e.g. "$240 a month" |

- **Names:** session 1 proposes each program's display name (credential-model's example uses
  "Food Assistance"). Both apps use the same names, so decide once, in Part A. They must not be
  real program names (SNAP, LIHEAP, Medicaid and so on) and must not imply a real agency.
- **Health's price is worked out from the signed percent:** $750 × (100 − discount) / 100. For
  Grace that's $57.00, not the formula's exact $56.80. Show the derived figure everywhere, so
  it's always the same number.
- **Health and Dividend never deny for income.** Every New Jersey resident with a verified
  identity gets both, even at a 0% Health discount (full price, $750). Design that case honestly
  (§6.6).

### 3.2 Program colors

Ed chose one color per program. Like every issuer color since Loop 5, a program's color reaches
the Wallet **as a hue only**, and the Wallet applies its own lightness and chroma.

| Program | Ed's color | Hue | Signed as |
|---|---|---|---|
| Energy | #CF4444 | 24 | `oklch(0.46 0.11 24)` |
| Food | #338067 | 169 | `oklch(0.46 0.11 169)` |
| Housing | #93537C | 342 | `oklch(0.46 0.11 342)` |
| Dividend | #7E9339 | 121 | `oklch(0.46 0.11 121)` |
| Health | #3B839B | 223 | `oklch(0.46 0.11 223)` |

- **In the Wallet**, benefit cards use the Loop 5 deep-fill treatment (`cred--issuer`,
  `--issuer-hue`; [Loop 5 README §1](../loop-5/README.md)) with the program's hue. Keep those
  class and token names: the stylesheet stays a strict superset. The credential's hint type is
  being renamed to `CredDemoCardColor`, but that's a data change, not a CSS one.
- **On Benefit Agency's own pages**, the program color comes from the same hue, set in Benefits'
  own `cred.css`. Session 1 proposes the treatment: an accent on a program card, a band on the
  program page, or similar.
- **Watch for three collisions:**
  - **Food (169) is almost Benefit Agency's own teal (172).** A Food accent must still read as
    "this program", not as the agency's chrome.
  - **Energy (24) is red, and Tampered is red.** In the Wallet, a deep red Energy card must
    never be confused with a Tampered status. Loop 5's rule (badges keep their own pale fills
    and never take the card's color) should cover this. Confirm it does.
  - **Health (223) sits near Payroll's blue (255).** Ed has accepted this. A Health card and an
    income card may sit close in color.
- Contrast holds at WCAG AA for all five, on both apps.

### 3.3 Every outcome, and what shows for each

Per the Loop 5 retro, every outcome is listed here, so each screen decides what to show for
each one explicitly.

**Per program** (Benefit Agency's decision, sent to the Wallet for all five programs):

| Outcome | Reason code | Credential? | Wallet wording (starting copy, refine it) |
|---|---|---|---|
| Eligible | none | Yes | Program name + key figure |
| Denied: income over the limit | `income_over_limit` | No | "{Program}: your income is above this program's limit." |
| Denied: not a New Jersey resident | `not_nj_resident` | No | "{Program}: this program is for New Jersey residents." |

Out-of-state people get `not_nj_resident` for **all five**. Nobody else is denied everything,
because Health and Dividend never deny for income.

**The application as a whole:**

| Outcome | Reason code | Reachable in the demo? |
|---|---|---|
| Decided | none | Yes: 21 people |
| Refused: a credential failed verification | `credential_invalid` | No. Tampered identities are stopped at Payroll, so they never hold income credentials. Design it anyway. |
| Refused: credentials about different people | `subjects_differ` | No, but the check exists. |
| Benefit Agency didn't answer | none (no response) | Yes, when it's cold. Reuse Loop 4's pattern. |
| Can't apply: no income credentials | Wallet-side | Yes: anyone who hasn't connected Payroll. |
| Can't apply: no identity credential | `credential_missing` | Yes: p24, p25 (who also have no income) |
| Already applied: holds benefit credentials | Wallet-side | Yes, arriving through the Benefits redirect (§6.10) |

**Credential badges** stay the five from Loops 2–5: Verified, Tampered, Expired, Not yet valid
and Unrecognized issuer. **A denial is not an error.** It must never borrow Tampered's red or
an error style.

### 3.4 People to design against

Figures are from the [expected outcomes](../../sample-data.md#expected-outcomes).

| Person | Income creds | Result | Health | Dividend | Use for |
|---|---|---|---|---|---|
| p01 Grace Okafor (Hunterdon) | 2 | **5 of 5** | 92.4% off, $57.00/mo | $100 | The main path, everywhere |
| p04 Aisha Rahman (Middlesex) | 2 | **5 of 5** | 100% off, $0.00/mo | $240 | The biggest payoff |
| p07 Luis Ferreira (Essex) | 6 | **2 of 5**: Health, Dividend | 85.4% off, $109.50/mo | $100 | Mixed result. $36 a month over the Energy limit, Ed's "cliff" persona |
| p08 Nadia Haddad (Passaic) | 6 | **5 of 5** | 94.5% off, $41.25/mo | $100 | Consent with seven credentials |
| p09 Daniel Walsh (Morris) | 2 | **2 of 5**: Health at **0%**, Dividend | 0% off, $750.00/mo | $100 | The honest "nothing off" Health credential |
| p17 Jun Park (Bergen) | 4 | **3 of 5**: Housing, Health, Dividend | 80.0% off, $150.00/mo | $100 | Housing yes, Food and Energy no |
| p19 Emily Carter (Livonia, MI) | 2 | **0 of 5**, `not_nj_resident` | — | — | Qualifies for nothing |
| p24 Ray Miller | 0 | Can't apply | — | — | No identity, no income |

### 3.5 What the flow does, as far as screens need to know

- **Benefit Agency asks for the identity credential and every income credential.** Consent is
  all-or-nothing over all of them, and every claim is shown, as on the Loop 4a consent page.
- **After Approve, two things happen behind one waiting page.** Benefit Agency returns all five
  outcomes, then the Wallet immediately collects the benefit credentials. The person sees one
  moment. If collecting fails, the outcomes are already known, and the credentials follow on the
  next check, as income credentials do.
- **Benefit Agency becomes a connection** in the Wallet, like Meridian Payroll. It gets no
  attention on the results screen. Removing it keeps the credentials.
- **Once a person holds any benefit credential, Find government services disappears for good.**
  There's no re-applying and no reset (Ed's call). People who were denied everything can apply
  again.
- **Benefit credentials are valid for 12 months** from the determination. They carry the program
  code and the figures in §3.1, never a name or address. The subject is an identifier, which is
  never shown.

## 4. What already exists: extend it, don't restart

These files are authoritative:

- **Benefit Agency today:** its [`cred.css`](../../../apps/benefits/app/static/cred.css) is
  still the Loop 0 system, and its only page is the placeholder
  [landing](../../../apps/benefits/app/templates/index.html). Theme, fixed:
  `data-app="benefits"` (plural, deliberately), hue 172 civic teal, Libre Franklin, a `62rem`
  wrap, 4px/6px radii, plainer and squarer than the other two apps
  ([Loop 0 README](../loop-0/README.md), `benefit.html`).
- **Components already designed elsewhere may be brought into Benefits' `cred.css`**, e.g.
  tables, `.claims`, `.log`, the badge set, the disclosure, `.panel`. Each app owns its copy, so
  bring in a rule by copying it into Benefits' file, never by linking another app's.
- **The Wallet today:** its [`cred.css`](../../../apps/wallet/app/static/cred.css) and the
  [Loop 5 handoff](../loop-5/README.md) pages, on top of Loop 4a's. Theme, fixed:
  `data-app="wallet"`, hue 52, Newsreader, a `30rem` cap, the Loop 4a compact page head and step
  titles.
  - The Credentials page has **Identity** then **Income** categories, with Income's inline check
    status (Loop 5 §2).
  - The **consent page** ([Loop 4a](../loop-4a/wallet/consent.html)) shows one requested
    credential with every claim, plus its missing variant.
  - The **pending pages** ([Loop 4](../loop-4/README.md)) are the pattern for waiting on a
    service: a small polling script, and **Check again** without JavaScript.
  - The **income stack** and the **deep fill in an issuer's hue** are settled
    ([Loop 5 §1](../loop-5/README.md)).
  - The **landing page** with sign in and sign out is from Loop 4a.
- **Activity (`.log`)** and its marker-dot palette are settled (Loop 4).

---

## 5. Part A — Benefit Agency (session 1)

Widths: **375px and 992px**.

### 5.1 Landing page (changed, #20)

Replaces the placeholder.
- **Five program cards.** Each has the program's name, a short phrase saying what it's for, and
  its color, and links to its page.
- **The navigation** links the five program pages, replacing "About the program / Who can apply
  / Contact us". **Remove the placeholder signed-in user** ("Jordan Diaz"): Benefit Agency has
  no public-user accounts.
- Say plainly, near the top, that you apply **with your digital wallet**. There's no form here.
- Propose where the admin view is reached from (§5.3). Something low-key, like a footer link, is
  fine: it's a demo tool, not a public feature.

### 5.2 Program pages (new, #20): all five

Each program page has:
- a couple of sentences about the program
- a **"Qualification requirements"** heading and the criteria list: a valid identity
  credential, New Jersey residency, and the program's income rule, as an **annual** figure with
  an **"as of September 2026"** note

The three shapes differ:
- **Food and Energy:** one "you qualify if your income is at or below X" limit.
- **Housing:** the limit depends on your county, so the page carries a **table of all 21 county
  thresholds** ([benefit-programs.md, Housing](../../benefit-programs.md)).
- **Health:** a sliding scale. Show the $750/month full price, free at or below 138% FPL, full
  price at or above 500% FPL, and a table of discounts across that range. Anyone may buy the
  plan.
- **Dividend:** the $100 base, the scaled bump, the $1,200/month phase-out, and its table. Its
  "earning more never leaves you worse off" point is worth making visible.

Every program page ends with **two options, side by side, each in its own box**:
- **Apply here**: disabled, with the note *"Applying without a digital wallet isn't available
  yet."*
- **Apply with Digital Wallet**: working. It sends the person to their Wallet (§6.10). Under it:
  *"Using your digital wallet uses info from your wallet to make applying fast and secure."*

Plain HTML: the note takes the place of a tooltip. The program's color carries through from its
card to its page (§3.2).

### 5.3 Admin — applications (new, #111)

A list of every application, **grouped by person** (the name from their identity credential),
each person's applications **newest first**. Each row shows the date and time and a summary
("5 of 5 approved", "Not a New Jersey resident", "Refused: credential couldn't be verified").
Each application links to its determination page (§5.4).

- **No sign-in**, like the rest of the demo. The page says it's a demo admin view.
- **Records are kept in memory and disappear when Benefit Agency restarts** (after about 15
  minutes idle). The empty state ("No applications yet") is a normal state, not an error.
  Explain that quietly on the page.
- Show it with p01, p07, p09 and p19, with **p19 appearing twice**: people who were denied
  everything can apply again. Also show the empty state.

### 5.4 Admin — determination (new, #111)

One page per application, laid out so a caseworker can follow the decision, **program by
program**:
- **Submitted data:** state and county from the identity credential, each paystub's employer,
  pay date and gross pay, then the monthly total and the annual (× 12) figure.
- **What the checks determined:** each presented credential's verification result, and whether
  they all name the same subject. Then, for each program: the rule, the person's figure against
  the limit or bounds, the outcome and reason. For eligible programs, the issued credential's id
  and figures.
- **The credentials used:** each one viewable, **decoded** (header and claims) and as the **raw
  JWT**. They're long, so show them behind a disclosure.
- Also: the subject id, the application's date and time, and the application id.

Variants: **p01** (all eligible), **p07** (mixed: show his Energy near-miss clearly), **p19**
(not a New Jersey resident: residency stops everything, so the programs aren't evaluated for
income), and **refused** (`credential_invalid`, shown on p01 with a failed income credential).
The last one isn't reachable in the demo, but the state exists.

---

## 6. Part B — The Wallet (session 2)

Widths: **375px and 480px**. Take program names, colors and outcome wording from session 1's
README.

### 6.1 Credentials page: Find government services (changed, #107)

- **Find government services** sits **between Identity and Income**. Propose its form: a card, a
  call to action, or a slim entry. It must invite, without competing with the credentials
  themselves.
- It's there until the person holds any benefit credential. After that, the **Benefits category
  takes its place**, in the same position (§6.7).
- Pages: p01 before applying, p01 after (§6.7), and p19 after being denied everything (the entry
  stays).

### 6.2 Government services (new, #107)

A directory with **one entry**, Benefit Agency, built as a list the way the employer list is,
since a fuller world would have many agencies. The entry says what it offers (five programs,
applied for together) and leads to its request. Page head: `‹ Credentials | <name>`, propose the
name.

### 6.3 Consent: many credentials (changed, #107)

The Loop 4a consent page, asked for **1 identity + N income credentials**. Every claim is shown,
all-or-nothing. It must stay readable and reachable with **seven credentials (p08)**, and the
buttons must never be buried. Propose how income credentials are grouped (for example, one
income section with each paystub collapsible, the claims still visible on demand). Also show
**p01** (three credentials).

### 6.4 Can't apply (new variants, #107)

- **No income credentials:** the person must connect their payroll provider first. Explain that
  and link to **Find your employer**. Show it for someone with an identity credential who hasn't
  connected yet (p01, before connecting).
- **No identity credential:** p24 has neither. Propose which message leads, and keep it to one
  clear next step.

### 6.5 Waiting (new, #107)

"Checking your eligibility…", on Loop 4's pending pattern, with **Check again** as the no-JS
fallback. No "server is waking up" copy. Show the "couldn't reach Benefit Agency" variant too.

### 6.6 Results (new, #107): the centerpiece

The payoff. **Lead with what the person got:** "You qualify for N programs" (propose the wording),
then each benefit **in its program color with its key figure**. Programs they didn't qualify for
come below, one plain line each with the reason. Then the way on, to their credentials.

- **p01:** five of five. The full payoff.
- **p04:** five of five, with Health free and a $240 Dividend. The biggest numbers.
- **p07:** two of five. Good news first, then three plain denials, including his near-miss on
  Energy. The page should still feel like getting something.
- **p09:** Health at **0% off ($750 a month)** plus Dividend. A 0% Health credential is an honest
  "you may buy the plan at full price", not a win. Propose how to say that without spin.
- **p19:** nothing, because she isn't a New Jersey resident. Clear and non-alarming, with no
  error styling. Find government services stays available.
- **Credentials still on the way:** p01's outcomes shown, with the cards not yet arrived.
- **Refused** (`credential_invalid`): not reachable, but design the state.

**Payoff through hierarchy, type and color, not animation.** Any motion respects
`prefers-reduced-motion`. No confetti. Announce the result to screen readers without moving focus
unexpectedly.

### 6.7 Credentials page: the Benefits category (changed, #109)

Once benefit credentials arrive, a **Benefits** category sits where Find government services
was, between Identity and Income. Each card is in its program's hue and shows the program name
and its key figure (Eligible, $100 a month, 92.4% off: $57.00 a month). There are at most five
cards, all from one issuer but in five colors. Propose whether they stack like income or show
flat. New cards get the Loop 5 **New** tag. Pages: p01 (five cards), p09 (two).

### 6.8 Benefit credential detail (new, #109)

Same structure as the income detail page ([Loop 5](../loop-5/wallet/income-credential.html)):
page head `‹ Credentials | <name>`, the program-colored panel, status band, claims, validity,
and **View credential details**.
- **Valid until** is 12 months out. It's the first credential in the demo whose expiry matters.
- Show **Health** (p01: discount, plan cost, and the derived price, marked as derived) and
  **Food** (p01: no figures, just the entitlement).
- **Tampered variant:** not reachable, but it must exist. Show it on Energy, so the red card and
  the Tampered status are seen together (§3.2).

### 6.9 Connections and Activity (changed, #107)

- **Connections:** Benefit Agency listed as a connected service, quietly. **Remove** keeps the
  credentials. Propose whether to say so.
- **Activity:** new entries for the application sent, each program's outcome (**denials
  included**, since Activity is the only place a denial is seen afterwards), the credentials
  received, and failures. Propose the wording and marker dots. Show p07.

### 6.10 Arriving from Benefit Agency (new, #108)

**Apply with Digital Wallet** on a program page opens the Wallet with Benefit Agency's request
attached.
- **Signed in:** straight to the consent page (§6.3), with the person it's for made obvious,
  since they didn't start in the Wallet.
- **Signed out:** the landing page with a notice that Benefit Agency is asking for credentials.
  Once the person signs in, they go on to consent with the request kept.
- **Already applied** (holds benefit credentials): a clear "you've already applied" page, with a
  link to their benefit credentials.
- **No income credentials:** the §6.4 page.

The results show in the Wallet, and nothing sends the person back to Benefit Agency.

---

## 7. Constraints: both sessions

- **JavaScript only sparingly**, as progressive enhancement over a page that already works
  without it (decisions.md). No framework, library or bundler.
- Copy, class names and ARIA attributes go **verbatim** into the Jinja templates, so write them
  as production strings.
- **Accessibility:** WCAG AA as in Loops 0–5: 44px minimum targets, visible focus, one `<h1>`
  per page, landmarks, `aria-current="page"` on the active nav item, and color never the only
  signal. That matters especially for outcomes: eligible or denied must be clear in text, not
  just color.
- **Every Wallet page is server-rendered per person, with the person in the URL.** Benefit
  Agency has no people; its admin pages are keyed by application.
- **Each app keeps its own `cred.css`.** Benefit Agency changes go in Benefits' copy, Wallet
  changes in the Wallet's.
- **Nothing may imply a real benefits agency, program or government service.** No real program
  names, seals or `.gov`-style language. Every app presents itself as a demo.
- **No photos or personal details on Benefit Agency's public pages.** The admin view may show
  the photo from the identity credential, since it received it (a selective-disclosure point,
  #28). Propose whether it should.

## 8. Deliverables

These go into `docs/design/loop-6/`:

- **`benefits/cred.css`** (session 1): a strict superset of
  [`apps/benefits/app/static/cred.css`](../../../apps/benefits/app/static/cred.css), with new
  rules in a marked **Loop 6 additions** section. Rules copied from another app's stylesheet go
  there too, noted as copied.
- **`wallet/cred.css`** (session 2): a strict superset of
  [`apps/wallet/app/static/cred.css`](../../../apps/wallet/app/static/cred.css), with a marked
  **Loop 6 additions** section.
- **One static HTML page per screen and variant** in Part A (`benefits/`) and Part B (`wallet/`).
  Photos the Wallet pages need go in `wallet/photos/`.
- **`index.html`**, framing every page at its widths (Benefits 375 and 992, Wallet 375 and 480).
  Session 1 creates it, and session 2 adds to it.
- **`README.md`**, documenting new tokens, components, states, copy and accessibility decisions,
  with a table listing every page, its person and its state. Session 1 writes **Part A**:
  program names, program color treatment, outcome wording. Session 2 adds **Part B**.
- **No screenshots.** `index.html` framing is enough.

The handoff is a **historical record**. The apps are never edited to match it afterwards, so
anything that must survive belongs in the README.
