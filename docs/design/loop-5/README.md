# Handoff: Cred Demo — Loop 5, Payroll issues credentials

> **No screenshots in this handoff.** Brief §8 asks for PNGs in `screenshots/`. Ed dropped that
> requirement on 2026-09-23, before the handoff was committed. `index.html` frames every page at
> its handoff widths instead, for capture later if needed.

Design handoff for Loop 5, answering [brief.md](brief.md). There are two stylesheets, 12 Wallet
pages and two Payroll pages:

- `wallet/cred.css` is a strict superset of `apps/wallet/app/static/cred.css`.
- `payroll/cred.css` is a strict superset of `apps/payroll/app/static/cred.css`.

Everything new sits in a marked **Loop 5 additions** section at the end of each file. There's one
documented exception: some of the Wallet's Loop 2 stack sizes are retuned (§1.3).

As in earlier loops, these are design references written in HTML. Copy, class names and ARIA are
production strings; take them verbatim. The handoff is a historical record, so anything that has to
survive is written here.

## Fidelity

**High.** Colours, type, spacing, states and copy are final. Ed chose both design problems from
three options each (2026-09-23):

- **Issuer colour: deep fill (option 1c).** The others were a tinted fill in place of the sand, and
  a white card with a coloured band.
- **Receiving: status inline in the Income heading (option 2a).** The others were a page-level
  strip, and a slot at the front of the stack.

Ed's review changes, all applied:

- The stack's padding and line-heights were retuned (§1.3).
- "View all" keeps Loop 2's sand (§1.2).
- The status reads "Checking issuers" (§2.1).
- **New** sits to the right of the pay period (§2.3).
- Payroll's panel heading is "Credential for this paystub" (§6).

Everything else is one proposal.

## Files

`index.html` shows every Wallet page at 375px and 480px (the 30rem cap), and every Payroll page at
375px and 992px (62rem).

### Wallet (`wallet/`)

| File | Page head | Person | State |
| --- | --- | --- | --- |
| `credentials-p01.html` | Credentials | p01 | Two income credentials; the check has finished with nothing new |
| `credentials-checking.html` | Credentials | p01 | Checking issuers |
| `credentials-new.html` | Credentials | p01 | 2 new credentials arrived |
| `credentials-error.html` | Credentials | p01 | Couldn't reach Meridian Payroll |
| `credentials-nojs.html` | Credentials | p01 | Without JavaScript |
| `credentials-waiting.html` | Credentials | p01 | Connected, nothing received yet (reworded note), checking |
| `credentials-p08.html` | Credentials | p08 | Six credentials: five drawn plus "View all Income credentials (6)" |
| `income-p08.html` | ‹ Credentials \| Income credentials | p08 | All six, newest first |
| `income-credential.html` | ‹ Credentials \| Income credential | p01 | Verified |
| `income-credential-tampered.html` | ‹ Credentials \| Income credential | p01 | Tampered (no sample person has one; shown on p01) |
| `connections-connected.html` | Connections | p01 | Right after connecting: "2 income credentials received" |
| `activity.html` | Activity | p01 | New received and couldn't-reach entries |

These are unchanged from Loop 4a and have no page here: the no-employer note, the employer-chosen
note, the p24 page, and the identity pages.

### Payroll (`payroll/`)

| File | Person | Change |
| --- | --- | --- |
| `paystub.html` | p01, 16–30 Sep 2026 | Credential panel beside the paystub from 60rem, below it when narrower |
| `activity.html` | p01 | "2 income credentials sent to your wallet" |

`photos/` holds p01, p08 and p23, copied from Loop 4a.

## Decisions

### 1. Income cards in the issuer's colour (brief §4.1)

#### 1.1 The treatment: deep fill

An income card with an issuer colour is filled with that colour at the Wallet's accent lightness
and chroma, with white text. The same treatment applies to a stacked card, a full card and the
detail page (§4).

```html
<a class="stack-cards__card cred--issuer" href="…" style="--i: 1; --issuer-hue: 255">…</a>
<a class="cred cred--income cred--issuer" href="…" style="--issuer-hue: 255">…</a>
<section class="panel cred--issuer" style="--issuer-hue: 255">…</section>
```

- **The Wallet takes only the hue.** The credential's display hint carries one colour. The Wallet
  converts it to an OKLCH hue and sets `--issuer-hue`. Lightness and chroma are fixed in
  `cred.css`:

  | Token | Value | Use |
  | --- | --- | --- |
  | `--issuer` | `oklch(0.46 0.11 h)` | Card fill, issuer bar |
  | `--issuer-edge` | `oklch(0.38 0.11 h)` | Card border |
  | `--issuer-rule` | `oklch(0.58 0.09 h)` | Rule inside a full card |
  | `--issuer-soft` | `oklch(0.93 0.03 h)` | Secondary text (meta labels, pay period) |

- **Contrast holds for any hue.** At L 0.46, white is about 7:1, and `--issuer-soft` about 5.5:1.
  Both stay above AA at any hue, because lightness, not hue, drives the ratio. This is the
  Wallet's own `--accent` recipe, which already passes for hues 52, 172 and 255. An issuer can't
  make a card illegible, because it can't choose the lightness.
- **The hue goes on the card, never on the stack or the category.** Cards from different issuers
  can then sit in one stack.
- **No hint, no class.** Without `cred--issuer`, an income card is Loop 2's sand
  (`--cred-income`). Identity cards never get the class, so they stay white.
- **Status never takes the issuer colour.** Badges keep their own pale fills and colours on the
  deep card, and the detail page's status band sits below the issuer bar, never inside it. The
  Unknown badge is hue 255 like Payroll, but it's pale (L 0.955) with dark text and a "?" glyph.
  Against a deep L 0.46 card it reads as a badge, not as part of the card.

#### 1.2 "View all" keeps Loop 2's sand

`.stack-cards__more` belongs to the category, not to an issuer, so it takes no issuer colour. It
keeps Loop 2's `--cred-income-tint` with the `--cred-income-line` border (Ed, 2026-09-23). The
stylesheet doesn't change here: the ledge just never gets `cred--issuer`.

#### 1.3 Stack retunes (Ed, 2026-09-23)

A two-line employer name ("Brightpath Early Learning", "Ridgeline Home & Hardware") pushed the
badge against the card's bottom edge, and its two lines sat too far apart.

| Rule | Loop 2 | Loop 5 |
| --- | --- | --- |
| `--cred-card-h` | 132px | **140px** |
| `.stack-cards__card`, `.stack-cards__more` padding | 14px 18px | **18px** all round |
| Employer name (`.stack-cards__employer`, new) | inherited 1.55 | **1.2** |
| `.stack-cards__amount` line-height | inherited 1.55 | **1.15** |

`--stack-peek` stays 68px. A two-line employer name still fits in the ledge (18 + 41px).

**Markup change:** the ledge's employer is now `<strong class="stack-cards__employer">`. It was
`<span><strong>…</strong></span>`.

### 2. Receiving credentials (brief §4.2)

#### 2.1 The status lives in the Income heading

The Credentials page renders what the person holds straight away. The meta slot beside "Income"
(`.card__meta.category__status`) carries the check:

| State | Meta text | Below the cards |
| --- | --- | --- |
| Checking | spinner + **Checking issuers** | nothing |
| New arrived | **2 credentials · 2 new** | nothing; new cards are tagged (§2.3) |
| Nothing new | **2 credentials** (as before the check) | nothing |
| Couldn't reach | **2 credentials** | `.category__waiting-note--action`: "Couldn't reach Meridian Payroll to check for new credentials." + **Check again** |

- "Checking issuers" is generic on purpose (Ed). There's one issuer today, but the Wallet may check
  several at once later.
- **Nothing new is silent:** the meta goes back to the count, and no note or log entry appears.
- `.spinner` is a 10px ring in `--accent`. With `prefers-reduced-motion` it stops and shows solid.

#### 2.2 JavaScript is progressive enhancement

**Without JavaScript** (`credentials-nojs.html`), the page shows what's held, the count in the
heading, and under the cards a `.category__check` form with a `.link-btn` **Check for new
credentials** (a GET). The server starts a fetch whenever the page is requested, so reloading does
the job.

**With JavaScript**, the inline script at the end of each Credentials page:

1. Hides `.category__check` and shows "Checking issuers" in the meta slot.
2. Polls the status URL in `data-check` every 2s. The URL is empty in these static pages, so the
   script does nothing here. The response is JSON: `{ "state": "checking" | "none" | "new" | "error", "announce": "…" }`.
3. On `none`, it restores the meta's original text and stops.
4. On `new` or `error`, it writes `announce` to the live region, then re-requests the page and
   swaps in the server's fresh `<section id="income">`. The server renders the finished state. No
   separate fragment endpoint is needed.

When the server renders a finished check (new or error), it leaves out `.category__check`.

**The announcement** goes to `<p class="visually-hidden" role="status" id="check-live">`, which is
always in the page. Focus doesn't move. The texts:

- "2 new income credentials from Meridian Payroll."
- "Couldn't reach Meridian Payroll to check for new credentials."

Nothing is announced on `none`.

**No delay copy:** nothing says the server is waking up (brief §4.2).

#### 2.3 New credentials are marked, once

A card shown for the first time carries `.cred__new`, a white mono pill reading **New**, to the
right of its pay period (Ed). The Wallet marks the ids as seen when it renders them, so the tag is
gone next time. After a Wallet restart everything comes back as new; that's accepted (brief §6).

#### 2.4 Connected, nothing received yet

`credentials-waiting.html`: the Loop 4 note is reworded, because it now lasts only until the first
fetch completes. It reads "You're connected to Meridian Payroll. Your pay will appear here as
credentials as soon as they arrive." The meta shows "Checking issuers".

The no-employer and employer-chosen notes are unchanged.

### 3. All income credentials (brief §5.2)

`income-p08.html`, reached from "View all Income credentials (6)":

- Page head: "‹ Credentials | Income credentials".
- Content: one `.category` with the Income heading, "6 credentials", and six full cards, newest
  first. Order within a pay date follows the sample data (Shoreway, Brightpath, Ridgeline).

The **full income card** (`.cred.cred--income`), the one-credential case, has:

- An "Employer:" label and the employer's name (`.cred__employer`, weight 600), with the badge on
  the right.
- "Gross pay" and the amount (`.cred__pay`, in `.stack-cards__amount` type).
- A rule, then the pay period and **Details**.

It uses the same deep fill. With no hint it's sand (`.cred--income`).

### 4. Income credential detail (brief §5.3)

This page has the same structure as the identity page:

1. **Page head:** "‹ Credentials | Income credential".
2. **Issuer bar** (`.panel__issuer`): a deep `--issuer` band reading "Issuer:" and "Meridian
   Payroll". It carries the issuer colour so the status band below keeps its green or red. The
   tampered page shows both together.
3. **Status band:** Loop 2's, unchanged.
   - Verified: "Nothing in this credential has changed since Meridian Payroll issued it."
   - Tampered: "Something in this credential was changed after Meridian Payroll issued it, so it
     can't be trusted or used. Ask Meridian Payroll for a new one." This is the identity wording
     with the issuer swapped.
4. **Claims:** Employer (strong) and Issued by.
5. **Tampered only:** the identity page's `.panel__note` ("The rest of this credential is shown as
   it was received…").
6. **Pay** (`.claims--grid`): Pay period, Pay date, Frequency, Gross pay (strong), Net pay. Dates are
   written out in full, as on the identity page. Frequency reads "Semimonthly", matching Payroll's
   paystub.
7. **Summary note** (`.panel__note`): "This is a signed summary of a paystub, not the paystub
   itself. Deductions and tax lines stay with Meridian Payroll."
8. **Validity:** "Valid from 15 September 2026" and **"Doesn't expire"** where identity says
   "Valid until".
9. **View credential details:**
   - Credential id
   - Issuer
   - Type (`VerifiableCredential, PaystubCredential`)
   - validFrom, noting "(no validUntil)"
   - Display ("Issuer colour, hue 255")
   - Signed JWT

   Nothing shows the subject identifier.

### 5. Connections right after connecting (brief §5.4)

Connections says what arrived. When the Loop 4 flow redirects to Connections after a successful
connection, and the first fetch returned credentials, the Connected band adds a second line: "2
income credentials received. <a>View credentials</a>". The link goes to Credentials.

- The first fetch can run during the pending-verify wait, so the count is known when Connections
  renders.
- The line shows only on that redirect, not on later visits.
- If the fetch hasn't finished or failed, the line is left out, and Credentials picks it up
  (§2.1).

### 6. Payroll: the credential panel (brief §5.6)

- **Position:** beside the paystub from 60rem (so at the 62rem wrap), below it when narrower.
- **Headings:** each record gets a `.record__head`:
  - "Paystub": "Meridian Payroll's full record of this pay period."
  - "Credential for this paystub" (Ed): "A separate record, signed by Meridian Payroll, holding only
    these claims from the paystub."
- **Rows line up:**
  - `.records` is a two-column grid (1.65fr / 1fr), and each `.record` spans six rows. Both panels
    use `grid-template-rows: subgrid`, so their five sections share row heights.
  - Paystub rows: parties, dates, figures, net pay, note. Credential rows: employer, dates, gross
    pay, net pay, disclosure.
  - Net pay sits level with net pay, with the same `--accent-wash` fill, and the dates sit level
    with the dates.
  - The credential's date row is a 2-column grid in the narrower column, so the paystub's date row
    gains some space. That's accepted.
- **It reads as a second record, not part of the paystub:**
  - It's a separate panel with an `--accent-line` border.
  - Its first row is a deep `--accent` band, echoing the Wallet's deep income card.
  - Each value carries its claim name in mono under it (`.claim__key`: `payPeriodStart, payPeriodEnd`,
    `payDate`, `payFrequency`, `grossPay`, `netPay`).
  - Values are formatted exactly as on the paystub, so the two visibly agree.
  - The gross row adds "Earnings lines, deductions and tax aren't in the credential."
- **The id:** `urn:uuid:…`, in mono in the deep band, and again in **View signed credential**.
- **No delivery status**, per the intent.
- **Payroll's copy gains** `.disclosure` and `.jwt`, lifted verbatim from the Wallet's (Loop 2),
  with Payroll's 24px side padding.

### 7. Activity (brief §5.5, §5.7)

| App | Entry | Marker |
| --- | --- | --- |
| Wallet | "2 income credentials received from Meridian Payroll" | `--verified` (they were verified on arrival) |
| Wallet | "Couldn't reach Meridian Payroll to check for new credentials" | `--caution` (not a trust failure) |
| Payroll | "2 income credentials sent to your wallet" | `--neutral` (routine delivery) |

- "Nothing new" is never logged.
- The count is the number received or sent in that fetch. A single credential reads "1 income
  credential".
- If a credential arrives but fails verification, it's logged separately, with `--error`: "1 income
  credential from Meridian Payroll couldn't be verified". No sample person produces one.

## New tokens

**Wallet:** `--issuer`, `--issuer-edge`, `--issuer-rule`, `--issuer-soft`, derived from
`--issuer-hue` (set per card by the server). `--cred-card-h` is retuned to 140px.

**Payroll:** none.

## New components

**Wallet:**

- `.cred--issuer`
- `.cred--income` / `.cred__employer` / `.cred__pay`
- `.stack-cards__employer` / `.stack-cards__when`
- `.cred__new`
- `.panel__issuer` / `.panel__issuer-name`
- `.category__status` / `.spinner`
- `.category__check`

**Payroll:**

- `.records` / `.record` / `.record__head` / `.record__title` / `.record__sub`
- `.panel--cred` / `.cred-panel__id` / `.cred-panel__urn`
- `.cred-panel__gross` / `.cred-panel__net` / `.cred-panel__amount` / `.cred-panel__omits`
- `.claimlist` / `.claim__key`
- `.disclosure` and `.jwt` (lifted from the Wallet)

## Accessibility

WCAG AA, as in Loops 0–4a:

- **Headings:** one `<h1>` per page, in the page head (Wallet) or the intro (Payroll). On the
  paystub, "Paystub" and "Credential for this paystub" are `<h2>`, and each record is a `<section>`
  labelled by its heading.
- **Landmarks and `aria-current`** are as in Loop 4a.
- **Targets:** at least 44px, including **Check again**, **Check for new credentials** (a
  `.link-btn`) and both disclosures.
- **Background check:** announced through an always-present `role="status"` region, without moving
  focus (§2.2).
- **Contrast:**
  - White on `--issuer` is about 7:1, and `--issuer-soft` on `--issuer` about 5.5:1, for any hue.
  - The New pill is ink on white.
  - Badges keep their tested pairs.
- **Colour is never the only signal:** issuer is also named in text ("Issuer: Meridian Payroll" on
  the detail page, Payroll by name in Connections and Activity). Status keeps its text and glyph.
- **Focus:** the standard ring shows outside the deep cards. `--accent-text` on the page `--bg`
  passes.

## Known gaps left to implementation

1. Hrefs are relative page links. Wire them to `/p/<id>/…`. `data-check` is empty in every static
   page.
2. The credential ids, the `did:example:meridian-payroll` issuer and the JWTs are illustrative
   samples. The credential model doesn't yet name Payroll's DID. Use what the generator produces.
3. The display hint's technical shape (`renderMethod`) is decided in the build (intent open
   question). The design assumes it yields one colour, from which the Wallet takes a hue.
4. Timestamps are fixed samples, as in Loop 4.
5. No screenshots (see the note at the top).
