# Loop 6 handoff — Benefits programs and eligibility

Brief: [brief.md](brief.md). `index.html` frames every page at its widths: Benefits at 375 and 992, Wallet at 375 and 480.

---

## Part A — Benefit Agency (session 1)

Benefits' `cred.css` is a strict superset of `apps/benefits/app/static/cred.css`. Everything new
is in the marked **Loop 6 additions** section at the end; rules copied from another app are
labelled with their source (`.figures` from Payroll; `.disclosure`, `.jwt`, `.claims`, `.empty`
from the Wallet). Theme unchanged: `data-app="benefits"`, hue 172, Libre Franklin + Public Sans,
`62rem` wrap, 4px/6px radii.

### Program names

| Code | Display name | Landing phrase |
|---|---|---|
| `food` | Food Assistance | Help buying groceries each month. |
| `energy` | Energy Assistance | Help paying heating, cooling and electricity bills. |
| `housing` | Housing Assistance | Help with rent, with a limit set by your county. |
| `health` | Health | A discount on the Public Option health plan. |
| `dividend` | Dividend | A monthly payment of at least $100. |

Both apps use these names verbatim.

### Program color

- **One attribute:** `data-program="<code>"` on any element sets `--program-hue` and derives
  `--program-accent` (L 0.46, C 0.11), `--program-text` (0.42), `--program-tint` (0.955/0.022),
  `--program-line` (0.86/0.045) and `--program-on` (soft text on the accent). Same lightness
  and chroma as the app accent, so white on `--program-accent` passes AA for all five hues.
- **Treatment: band** (chosen over edge and tint). A landing card's name sits on a deep-fill
  band in the program's color (`.program-card__name`); the program page opens with a
  full-width band (`.program-band`) carrying the back link, eyebrow, `<h1>` and intro.
- **Agency teal stays on chrome only**: the brand mark, links, buttons and disclosures. No
  program element uses it, and every program element carries its name, so Food (169) next
  to the agency's teal (172) is always identified by its label, never by color alone.
- **Apply buttons are agency teal on every program page**, not the program color. Applying
  is an agency action and covers all five programs.
- **Denials never borrow red.** Energy (24) appears only as a program marker or band;
  outcome badges keep their own pale fills (`.badge--verified`, `.badge--neutral`).

### Outcome wording

| Outcome | Badge / text | Credential |
|---|---|---|
| Eligible | `.badge--verified` "Eligible" | Yes |
| `income_over_limit` | `.badge--neutral` "Not eligible" + "No credential issued · reason income_over_limit" | No |
| `not_nj_resident` | `.badge--neutral` "Not eligible" + reason code, all five | No |
| `credential_invalid` | "Refused: credential couldn't be verified" (error red, as it is a verification failure) | No |

Key figures: Health "92.4% off: $57.00 a month" (price derived from the signed percent), Dividend
"$100.00 a month". Admin summaries: "5 of 5 approved", "2 of 5 approved", "Not a New Jersey
resident", "Refused: credential couldn't be verified". Wallet wording for Part B should follow
the brief's §3.3 starting copy with these program names.

### Components added

- **Header:** `.header__nav a[aria-current="page"]` (underlined, ink); `.header__admin` (quiet
  bordered link, top right where the placeholder initials were; hidden ≤40rem, where it becomes
  `.nav-menu__admin`, the last menu item). The signed-in user is removed.
- **Landing:** `.programs` grid of `.program-card`.
- **Program page:** `.program-band`, `.program-body`, `.program-section`, `.criteria` (numbered
  qualification list; the `<ol>` carries the numbering, the visible numbers are `aria-hidden`),
  `.facts` (Health and Dividend's three figures), `.callout[data-program]` ("Earning more never
  leaves you worse off"), `.apply` with `.apply__option--wallet` first and the disabled
  "Apply here" second, each note tied to its button with `aria-describedby`.
- **Housing:** the 21 county limits sit in a closed `.disclosure--boxed` under the
  requirements, in a `.figures` table.
- **Admin list:** `.apps`, a compact table (Applicant, Received, Result, View). A person's name
  shows on their first row only (`.apps__start`); newest first within a person.
- **Determination:** `.meta` (received, application id, subject id), `.checks` (each credential
  row is a `.disclosure` holding its decoded header, claims and raw JWT; "Same person" is a plain
  row), `.submitted` (state/county + income `.figures` with monthly and × 12 totals), and
  `.decisions` of `.decision[data-program]` cards: Figure, Result, a decorative `.scale` bar
  (income dot against the program's qualifying zone; `aria-hidden`, since the text says the
  same), and a grey `.decision__foot` with the issued credential or the reason code.
  `.scale` reads `--zone-start`, `--zone-width` and `--dot` from an inline `style`, the one
  place a template writes computed values.
- **`--surface-muted`** (neutral grey) for the decision footers and the scale track, so they
  separate from the page's teal-white.

### Decisions that depart from the brief

- **Health and Dividend drop their tables** (§5.2). The three `.facts` and the "earning more"
  callout carry the scale. The full tables stay in `docs/benefit-programs.md`.
- **Housing's county table is behind a disclosure**, closed by default.
- **Admin list shows no per-program eligibility**, only the one-line result.
- **The admin view shows no photo**, though the identity credential carries one; the decoded
  claims show `image` truncated with "(photo, not shown)".
- **Admin link at 375px** lives inside the Menu disclosure; the header has no room beside it.
- **Program pages show no Rule line on determinations**; the Figure line names the limit.
- **Apply with Digital Wallet** points at the Wallet with Benefit Agency's request attached (Part B §10). In these static pages it links to `../wallet/landing-request.html`.
- **Dates** use 1 Oct 2026 (after the 30 Sep paystubs). Credential and application ids,
  signatures, and identity birth dates and street addresses are placeholders.

### Pages

| Page | Person | State |
|---|---|---|
| `benefits/landing.html` | — | Five program cards |
| `benefits/food.html` | — | Pass/fail limit |
| `benefits/energy.html` | — | Pass/fail limit |
| `benefits/housing.html` | — | County limit, table in disclosure |
| `benefits/health.html` | — | Sliding scale (discount) |
| `benefits/dividend.html` | — | Sliding scale (payment) |
| `benefits/admin.html` | p01, p07, p09, p19 ×2 | Applications |
| `benefits/admin-empty.html` | — | No applications yet |
| `benefits/determination-p01.html` | p01 Grace Okafor | 5 of 5 |
| `benefits/determination-p07.html` | p07 Luis Ferreira | 2 of 5, Energy $432.00 a year over |
| `benefits/determination-p19.html` | p19 Emily Carter | Not a NJ resident, programs not evaluated |
| `benefits/determination-refused.html` | p01 Grace Okafor | Refused, `credential_invalid` (tampered income credential) |

### Accessibility

WCAG AA as in Loops 0–5: 44px targets (including each admin "View" link, with a visually
hidden name and time), visible focus (white outline inside the program band), one `<h1>` per
page, header/nav/main/footer landmarks, `aria-current="page"` on the active nav item and on
Admin across admin pages. Outcomes are always stated in text ("Eligible", "Not eligible",
reason code); color is never the only signal.

---

## Part B — Wallet (session 2)

`wallet/cred.css` is a strict superset of `apps/wallet/app/static/cred.css`. Everything new is in
the marked **Loop 6 additions** section at the end; nothing earlier is redefined. Program names,
colors and outcome wording come from Part A.

### Fidelity

High. Ed approved Part B on 2026-09-24. He chose the results screen from three options:

- **Chosen: verdict band plus stack (1c).** The others were one flat deep card per benefit (1a),
  and a single statement panel listing all five programs (1b).
- **The verdict sits on the page background, with no box** (Ed, 2026-09-24). A sand band was tried after amber, which reads as caution. Both boxes felt inconsistent with the other pages.
- **Energy's near-miss is a plain denial.** The outcome carries only a reason code, so the Wallet
  can't say "$36 a month over" without Benefit Agency also sending the limit. The figure stays on
  the admin determination page.
- **Benefit card figure** (`.stack-cards__figure`) is 1.0625rem, close to the program name (Ed, 2026-09-24).
- **The Benefits category stacks like Income** on Credentials. On the results page the same cards are laid out flat (Ed, 2026-09-24).

Everything else is one proposal.

### 1. Program color in the Wallet

- **Loop 5's deep fill, unchanged.** A benefit card is `stack-cards__card cred--issuer` with
  `--issuer-hue` set to the program's hue (food 169, energy 24, housing 342, health 223,
  dividend 121). The detail page is `panel cred--issuer`. No new color tokens.
- **Contrast** is Loop 5's: white on `--issuer` about 7:1 and `--issuer-soft` about 5.5:1 for any hue.
- **Energy vs Tampered holds.** Badges keep their own pale fills on any card, and the status band
  sits below the program bar, never inside it. `benefit-energy-tampered.html` shows the deep red
  bar and the pale red Tampered band together: they differ in lightness, and Tampered always has
  its ✕ glyph and text.
- **Health (223) and Payroll (255)** sit close, as accepted. Every card names its program or employer.

### 2. Credentials page (§6.1, §6.7)

- **Find government services** (`.services-entry`) is a slim link row between Identity and Income:
  inset fill (`--surface-2`), `--line-2` border, no shadow, a title, one line ("Apply for programs
  with the credentials you already hold.") and a chevron. It isn't a category, so it has no heading.
- **Benefits** replaces it, in the same place, once any benefit credential is held. It's a
  `.category` with a stack, like Income, in program order (Food, Energy, Housing, Health,
  Dividend; Dividend at the front).
- **Each ledge shows the program name and its key figure** (`.stack-cards__program`,
  `.stack-cards__figure`): "Eligible", "92.4% off", "$100.00 a month", or "Full price" for a 0%
  Health credential. The front card adds Health's price line (`.cred__figure-sub`), "Valid until 1 Oct
  2027" and the Verified badge.
- **New** (Loop 5's pill) sits right after the program name. The heading meta reads "5
  credentials · 5 new". The results screen shows no New tags, so the tag first appears on
  Credentials, and it shows once.
- p19 keeps the entry after a 0 of 5 result.

### 3. Government services (§6.2)

Page head "‹ Credentials | Government services". It's a `.people` list of link rows (`.services` sets
72px rows), with one entry: **Benefit Agency**, "Five programs, applied for together: Food, Energy
and Housing Assistance, Health, and Dividend". The row leads to the request (consent, or a can't-apply page).

### 4. Consent with many credentials (§6.3)

- Page head "‹ Government services | Request from Benefit Agency". The heading: "Do you want to share N
  credentials with Benefit Agency?"
- **Approve and share / Deny come first**, as in Loop 4a: "This applies to the whole request: all N
  credentials." With more than three credentials they **repeat after the list** ("Approve shares
  all N credentials above. Deny shares nothing."), so they're never more than a screen away.
- **Identity** is Loop 4a's panel, unchanged, with "1 of N".
- **Income** is one panel for all income credentials ("2–N of N"). It has:
  - The Meridian Payroll issuer bar (`.panel__issuer`, hue 255).
  - A plain status area: "6 paystubs · September 2026", **All verified**, "Nothing in these 6
    credentials has changed since Meridian Payroll issued them. Open one to see every claim it
    shares."
  - A `.shares` list, with one `<details class="share">` per paystub. The summary shows employer,
    period and gross pay. Opening it shows every claim (Employer, Issued by, Pay period, Pay date,
    Frequency, Gross pay, Net pay) and the credential id.
- A person with income credentials from two issuers would get one panel per issuer.

### 5. Can't apply (§6.4)

Both pages use `.needs`: a panel listing what Benefit Agency asks for, against what's held.

- **No income** (p01 before connecting): "Connect your payroll provider first". Identity shows **In
  your wallet** (verified badge), Income shows **None yet** (neutral). The one step is **Find your
  employer**.
- **No identity** (p24): **identity leads**, because Payroll needs it too, so it comes first.
  "You need an identity credential first". Both rows show **None**. The demo can't issue one, so
  the page says so, and the one step is **Switch person**.

### 6. Waiting (§6.5)

- `checking.html`: page head "Applying to Benefit Agency", "Checking your eligibility…". It uses
  Loop 4's `.pending` and polling script (`data-poll`), with **Check again** as the no-JS
  fallback. Copy: "Benefit Agency is checking the credentials you shared and deciding all five
  programs. Your benefit credentials will follow straight away." Nothing about waking up.
- `checking-error.html`: "Couldn't reach Benefit Agency", with a caution band, badge **No answer**, and
  "Benefit Agency didn't answer, so your application wasn't decided and no credentials were issued.
  Try again in a moment." The actions are **Try again** (re-sends the approved request) and **Back to
  credentials**.

### 7. Results (§6.6)

Page head "Results from Benefit Agency". The order is fixed:

1. **Verdict** (`.verdict`, no box, on `--bg`): the `<h2>` and one sentence on what the person got.

   | Case | Heading | Sentence |
   |---|---|---|
   | 5 of 5 | You qualify for all 5 programs | Food, Energy and Housing Assistance, **$100.00 a month** from Dividend, and **92.4% off** the Public Option health plan, so it costs **$57.00 a month**. |
   | p04 | You qualify for all 5 programs | …, **$240.00 a month** from Dividend, and the Public Option health plan **free**. |
   | N of 5 | You qualify for N programs | Only the programs they got. |
   | p09 | You qualify for 2 programs | **$100.00 a month** from Dividend. Health gives no discount at your income: you may buy the Public Option plan at its full price, **$750.00 a month**. |
   | 0 of 5 | You don't qualify for any programs | Benefit Agency's programs are for New Jersey residents, and your identity credential gives your address in Michigan. |

2. **Added to your wallet**: the benefit cards laid out flat, in program order, each drawn in full like the front card of the Credentials stack (`.stack-cards--flat`), without New (Ed: stacked on Credentials only).
3. **Programs you don't qualify for**: `.outcomes`, one line each, with a grey marker and never error
   styling: "**Food Assistance:** your income is above this program's limit." or "…: this program
   is for New Jersey residents." For p19 the heading is "Each program", listing all five.
4. **Go to your credentials**, and "Benefit credentials are valid for 12 months, until 1 October
   2027." For p19: "Find government services stays on your Credentials page, so you can apply again."

More on specific cases:

- **0% Health** reads "Full price", with "0% off: $750.00 a month" on its card. It never says
  "discount", "save" or "qualify for help".
- **Still on the way** (`results-arriving.html`): the verdict shows, because the outcomes are known.
  The stack is replaced by "On the way to your wallet", with spinner meta **Collecting** and a
  waiting note. The cards follow on the next check, as income cards do.
- **Refused** (`credential_invalid`): a plain `<h2>` "Your application couldn't be decided",
  then an error band with badge **Refused** ✕. This is a verification failure, so red is right here.
  - The band's text: "One of your income credentials couldn't be verified, so no program could be
    decided."
  - A note: "Nothing was issued. On your Credentials page, the credential that failed shows as
    Tampered."
  - If the identity credential failed, use credential-model's wording: "Your identity credential
    couldn't be verified, so no program could be decided."
  - `subjects_differ` uses the same layout: "The credentials you shared aren't all about the same
    person."
- **Screen readers:** a visually hidden `role="status"` paragraph gives the verdict ("You qualify for
  2 programs. Not eligible for 3."). Focus stays at the top of the page, and the `<h2>` is the
  first content after the page head.
- **No motion.** The only animation is the Collecting spinner, which stops under
  `prefers-reduced-motion`.

### 8. Benefit credential detail (§6.8)

This page has the income detail's structure:

1. **Page head:** "‹ Credentials | Benefit credential".
2. **Program bar:** `.panel__issuer` reading "Program:" and the name.
3. **Status band.**
4. **Claims:** Program, Issued by Benefit Agency.
5. **Benefit:**
   - **Health:** Discount 92.4% off; Plan: Public Option, $750.00 a month; You pay $57.00 a month,
     with "Worked out by your wallet from the discount" (`.claims__note`).
   - **Pass/fail:** Result Eligible, and the note "Food Assistance carries no amount. Holding this
     credential shows you qualify."
6. **Validity:** "Valid from 1 October 2026" and "Valid until 1 October 2027".
7. **View credential details:**
   - Credential id
   - Issuer
   - Type
   - validFrom and validUntil
   - Program code, plus the signed figures for Health
   - Display ("Program colour, hue N")
   - Signed JWT

The Tampered text drops income's "Ask … for a new one", since there's no re-applying: "Something
in this credential was changed after Benefit Agency issued it, so it can't be trusted or used."
Loop 5's "The rest of this credential is shown as it was received…" note follows.

### 9. Connections and Activity (§6.9)

- **Connections:** a Benefit Agency panel above Meridian Payroll (newest first). It shows
  "Government service", **Connected** since the application, and "Benefit Agency sent you 2
  benefit credentials." **Remove** is a `.link-btn`. Under it, "Removing Benefit Agency keeps
  your benefit credentials.", tied to the button with `aria-describedby`. It's said, because a
  person would reasonably fear losing them.
- **Activity (p07)**, newest first:

  | Entry | Marker |
  |---|---|
  | 2 benefit credentials received from Benefit Agency | `--verified` |
  | Dividend: eligible, $100.00 a month | `--verified` |
  | Health: eligible, 85.4% off: $109.50 a month | `--verified` |
  | Food Assistance: not eligible. Your income is above this program's limit. | `--neutral` (a denial isn't a failure) |
  | New connection to Benefit Agency established | `--verified` |
  | Application sent to Benefit Agency: identity credential and 6 income credentials shared | `--neutral` |
  | Couldn't reach Benefit Agency to send your application | `--caution` |
  | Your application couldn't be decided: 1 credential couldn't be verified (not shown) | `--error` |

  Each program gets its own entry, so a denial can be found afterwards. For 0% Health: "Health:
  full price, 0% off: $750.00 a month" (`--neutral`).

### 10. Arriving from Benefit Agency (§6.10)

**Apply with Digital Wallet** opens the Wallet with the request attached. The URL shape is left to
the build: the Wallet's request route plus Benefit Agency's request reference.

- **Signed in** (`consent-arrived.html`): the consent page with page head "‹ Credentials |
  Request from Benefit Agency" and an `.arrival` row above the question: the person's photo,
  "Benefit Agency sent you here. You're applying as **Grace Okafor**.", and "Not you? Switch
  person".
- **Signed out** (`landing-request.html`): Loop 4a's landing with a sand `.notice` (`role="status"`)
  above the headline: "**Benefit Agency is asking for credentials.** Sign in, and your wallet will
  show you exactly what it wants before anything is shared." Sign in keeps the request and goes on
  to consent.
- **Already applied** (`already-applied.html`): "You've already applied", then "Benefit Agency
  decided your programs on 1 October 2026, and your benefit credentials are in your wallet." The one
  step is **View your benefit credentials** (`credentials-benefits.html#benefits`).
- **No income:** `cant-apply-income.html`. **No identity:** `cant-apply-identity.html`.

Nothing sends the person back to Benefit Agency.

### New components

`.services-entry`, `.services`, `.stack-cards__program`, `.stack-cards__figure`, `.cred__figure-sub`,
`.stack-cards--flat`, `.verdict`, `.outcomes`, `.results__next`, `.shares` / `.share`, `.arrival`, `.notice`, `.needs`,
`.claims__note`. **No new tokens.**

### Accessibility

WCAG AA, as in Loops 0–5:

- **Headings and landmarks:** one `<h1>` per page, in the page head. Landmarks and
  `aria-current` are as in Loop 4a.
- **Targets:** at least 44px, including every `.share` summary (64px) and the services entry (64px).
- **Outcomes are always in words:** "Eligible", "Full price", "not eligible", the reason. Program color
  is never the only signal, because every card and bar names its program.
- **Consent summaries** carry a visually hidden "Gross pay" before the amount.
- **The results verdict** is announced through a `role="status"` region, without moving focus.

### Pages

| Page | Person | State |
|---|---|---|
| `wallet/credentials-p01.html` | p01 | Before applying: Find government services |
| `wallet/credentials-p19.html` | p19 | After 0 of 5: the entry stays |
| `wallet/services.html` | p01 | Government services |
| `wallet/consent-p01.html` | p01 | 3 credentials |
| `wallet/consent-p08.html` | p08 | 7 credentials, actions repeated below |
| `wallet/cant-apply-income.html` | p01 | No income credentials |
| `wallet/cant-apply-identity.html` | p24 | No identity credential |
| `wallet/checking.html` | p01 | Checking your eligibility |
| `wallet/checking-error.html` | p01 | Couldn't reach Benefit Agency |
| `wallet/results-p01.html` | p01 | 5 of 5 |
| `wallet/results-p04.html` | p04 | 5 of 5, Health free, $240.00 Dividend |
| `wallet/results-p07.html` | p07 | 2 of 5 |
| `wallet/results-p09.html` | p09 | Health at full price, Dividend |
| `wallet/results-p19.html` | p19 | Not a New Jersey resident |
| `wallet/results-arriving.html` | p01 | Outcomes known, credentials on the way |
| `wallet/results-refused.html` | p01 | Refused, `credential_invalid` |
| `wallet/credentials-benefits.html` | p01 | Benefits category, 5 new |
| `wallet/credentials-p09.html` | p09 | Benefits category, 2 |
| `wallet/benefit-health.html` | p01 | Health, verified |
| `wallet/benefit-food.html` | p01 | Food Assistance, verified |
| `wallet/benefit-energy-tampered.html` | p01 | Energy Assistance, Tampered (not reachable) |
| `wallet/connections-p07.html` | p07 | Benefit Agency and Meridian Payroll |
| `wallet/activity-p07.html` | p07 | Application, five outcomes, credentials received, one failure |
| `wallet/consent-arrived.html` | p01 | From Benefit Agency, signed in |
| `wallet/landing-request.html` | — | From Benefit Agency, signed out |
| `wallet/already-applied.html` | p01 | From Benefit Agency, already applied |

`wallet/photos/` holds p01, p04, p07, p08, p09 and p19.

### Known gaps left to implementation

1. Hrefs are relative sample links. Wire them to `/p/<id>/…`. Pages for people other than p01 point
   the menu at p01's Credentials where no page of their own exists. `data-check` and
   `data-poll` are empty.
2. p08's net pay, the credential ids, `did:example:benefit-agency` and the JWTs are placeholders.
3. The Energy near-miss figure would need the outcome to carry the limit (a protocol change,
   declined).
