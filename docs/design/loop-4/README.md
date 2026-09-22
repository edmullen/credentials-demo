# Handoff: Cred Demo — Loop 4, Wallet and Payroll Connect

Design handoff for Loop 4, answering [brief.md](brief.md). Two stylesheets and 23 static pages:
`wallet/cred.css` is a strict superset of the Wallet's current file, and `payroll/cred.css` is a
strict superset of Payroll's. Every earlier token, theme and component carries forward
unchanged. Everything new is appended in a marked **Loop 4 additions** section at the end of each
file.

As in Loops 0–3, these are **design references written in HTML**: the shape the Jinja templates
should take, not code to drop in. The handoff is a historical record, so anything that has to
survive is written down here.

## Fidelity

**High.** Final colours, type, spacing, radii, states and copy. Copy, class names and ARIA are
production strings; take them verbatim. The consent screen and connected state went through one
round of options with Ed (2026-09-22). Everything else is one proposal.

## Files

### Wallet (`wallet/`, 30rem)

| File | Screen / state | Person |
| --- | --- | --- |
| `connections.html` | No employer chosen: the Loop 2 `.empty`, button now live | Grace Okafor, p01 |
| `employers.html` | Employer lookup: 15 employers, A–Z | p01 |
| `employers-p08.html` | Same, with one employer already added | Nadia Haddad, p08 |
| `connections-chosen.html` | Employer chosen, **Connect payroll** | p01 |
| `pending.html` | Waiting for Payroll's presentation request | p01 |
| `consent.html` | Consent screen | p01 |
| `consent-tampered.html` | Consent screen, credential already shows Tampered | Carmen Diaz, p23 |
| `consent-missing.html` | Consent screen, missing credential | Ray Miller, p24 |
| `pending-verify.html` | Waiting for Payroll to verify, after Approve | p01 |
| `connections-connected.html` | Connected | p01 |
| `connections-connected-p08.html` | Connected, three employers | p08 |
| `connections-tampered.html` | Outcome: `credential_invalid` | p23 |
| `connections-not-employee.html` | Outcome: `not_an_employee` | p01, chose Harborline |
| `activity.html` | Activity: every Wallet event type | p01 |
| `activity-p23.html` | Activity: tampered refusal | p23 |
| `activity-p24.html` | Activity: missing credential | p24 |
| `credentials.html` | Credentials home, connected but nothing issued yet | p01 |

### Payroll (`payroll/`, 62rem)

| File | Screen / state |
| --- | --- |
| `connections.html` | Not connected yet |
| `connections-connected.html` | Connected |
| `activity-empty.html` | No activity yet |
| `activity.html` | One successful connection |

All four show Grace Okafor (p01).

### Also

| File | Contents |
| --- | --- |
| `index.html` | Every page above in one browsable overview |
| `screenshots/` | Full-page capture of each page, `wallet-*.png` and `payroll-*.png`, at 924px wide. The Wallet sits at its 30rem cap. Payroll is 68px short of its 62rem wrap, so its `.wrap` fills the frame; nothing reflows at that width. |

## Decisions

### 1. One connection per provider, not per employer (Ed, 2026-09-22)

Payroll holds **one employee record per person**, covering all of that person's jobs. So the
Wallet connects to **Meridian Payroll** once, and the employers are listed *under* the provider
they are paid through. Nadia's three employers sit in one panel with one Connected status
(`connections-connected-p08.html`).

- **Disconnect and Remove live on the provider**, as a link-styled button (`.link-btn`) in the
  provider's head. The ✕ on each employer row from #13 is **dropped**. There is no per-employer
  remove. Before connecting, the action reads **Remove**, because the Wallet only forgets the
  provider and its employers. After connecting it reads **Disconnect**.
- **Disconnect makes no call to Payroll.** Per #13, the Wallet forgets locally, so Payroll's
  Connections page keeps showing the wallet as connected. This is a named demo limitation,
  like the restart case in §7.
- **Find another employer** sits below the provider, as a secondary button. An employer added
  after connecting joins the existing connection. Nothing is re-requested.
- Both link-buttons are `<button>`s inside `<form method="post">`, because they change state.
  `aria-describedby` points at the provider's `<h2>`, so a screen reader hears "Disconnect,
  Meridian Payroll".

### 2. The connected state (option 1f)

The same `.panel` as the credential detail screen, read top to bottom:

1. **Status band.** The Loop 2 `.panel__status`, with a badge and one sentence. Connected:
   `badge--verified` "✓ Connected" and *"Connected since 22 Sep 2026, 2:14 PM. Meridian Payroll can
   send you credentials for every employer below."*
2. **Provider head.** A mono "Payroll provider" label, the name as `<h2>`, and Disconnect or
   Remove opposite it.
3. **Employers.** A `.provider__emps` list, one 52px row per employer, with no actions.
4. **Connect payroll** as a block button, only while not connected.

The band is also where **every outcome lands** (§4), so the person always finds the result in
the same place.

**Payroll's side is one `.connlist` row** (option 1e): "Your wallet", a line reading *"Identity
verified with the State of New Jersey · since 22 Sep 2026, 2:14 PM"*, and the same Connected
badge. The page is always binary, never a list of several.

### 3. The consent screen (option 1b's copy, the Credentials home card)

- **Eyebrow** "Request from Meridian Payroll". **`<h1>`** "Meridian Payroll is asking for 1
  credential". **Purpose**: "It runs payroll for {employer}, and needs to check who you are
  before it links your wallet to your employee record." The count in the `<h1>` is the
  length of the request. With several employers under one provider, `{employer}` becomes the
  employer the person just added. This is the one wording case left for build.
- **A list, not a single item.** `<ol class="request">`, one `.request__item` per requested
  credential. Each item has a `.category__head` (type as `<h2>`, and "1 of 1" opposite), then:
  **the credential, drawn exactly as the credential detail screen draws it** (`credential.html`,
  Loop 2): status band, large photo with Name / Date of birth / Issued by, Address, validity,
  and the *View credential details* disclosure. For Carmen's Tampered credential it's the
  tampered variant, with its caveat note (Ed, 2026-09-22). Every claim is on screen, which
  meets brief §4. **Requested claims are not marked**; the item head names the credential
  type only. One adaptation, for heading order only: the band's hidden "Status" heading
  becomes an `<h3>`, a sibling of "Address", under the item's `<h2>`.
- **One decision for the whole request.** A single `<form class="decision">` after the list,
  holding both buttons (`name="decision"`, `value="approve|deny"`), under the line *"This
  applies to the whole request."* One form, outside every item, is what keeps the layout from
  reading as per-credential once Benefits asks for several.
- **Deny** returns to the previous Connections state **silently** (Ed, 2026-09-22). The
  Activity log records it (§5), and nothing appears on the Connections screen.
- **Tampered credentials are still offered.** The Wallet already knows Carmen's credential is
  Tampered, so its panel shows the Tampered band and caveat exactly as her detail screen does. Approve stays available, so the demo shows the verifier catching it.
- **Missing credential** (`consent-missing.html`). The item head reads "Missing". In place of the
  credential, a `.category__waiting-note` reads *"You don't have an Identity credential to share."*
  (credential-model §5, `credential_missing`). There is no Approve: the only action is **Close
  request**, a secondary button under *"Without it, this request can't be completed, and nothing
  is shared."*

### 4. Outcomes on Connections

Each outcome uses the provider panel's status band, with no new component. The copy comes from
credential-model §5, plus one sentence saying what to do next:

| Code | Band | Badge | Copy |
| --- | --- | --- | --- |
| connected | `--verified` | ✓ Connected | Connected since {when}. Meridian Payroll can send you credentials for every employer below. |
| `credential_invalid` | `--error` | ✕ Not connected | Meridian Payroll couldn't verify your identity credential. / It has been changed since it was issued. *View your credential* |
| `not_an_employee` | **`--caution`** (new) | ! Not connected | Meridian Payroll doesn't have an employee record that matches you. / Check that you chose the right employer. If not, remove Meridian Payroll and find your employer again. |

**Not-an-employee is amber, not red.** It's a wrong choice, not a trust failure, so it
shouldn't look scarier than a validation message. The new `.panel__status--caution` uses the
Loop 2 `badge--caution` colours. After either failure, the block button reads **Try again**
instead of Connect payroll.

**How not-an-employee is reached:** Payroll matches the presented subject against employee
records **at the employers the Wallet names in its connection request**. Grace choosing
Harborline Logistics, where she doesn't work, is the demo operator's way to trigger it.
Payroll has a record for every one of the 25 people, so without that employer check the
outcome could never happen. **This is a reconciliation item for the plan step.**

### 5. Activity: the marker takes the status palette (Ed, 2026-09-22)

Loop 2's open question, answered. Four modifiers are added, and the bare `.log__dot` still
renders as it did in Loop 2:

| Modifier | Used for |
| --- | --- |
| `--neutral` (grey) | Employer added, provider removed, disconnected, request made, credential shared, request denied |
| `--verified` (green) | New connection established |
| `--caution` (amber) | Refused as not an employee; no credential to share |
| `--error` (red) | Refused because the credential couldn't be verified |

The dot stays `aria-hidden`. **Every message states its outcome in words**, so colour is never
the only signal. Wallet entry wording:

- *{Employer} added, paid through Meridian Payroll*
- *Meridian Payroll removed, with {employers}* · *Disconnected from Meridian Payroll*
- *Connection to Meridian Payroll requested*
- *Identity credential shared with Meridian Payroll*
- *Request from Meridian Payroll denied. Nothing was shared.*
- *New connection to Meridian Payroll established* (Loop 2's wording, kept)
- *Connection to Meridian Payroll refused: {credential-model §5 message}*
- *Connection to Meridian Payroll not made: you don't have an Identity credential to share.*

**Payroll logs successful connections only** (brief §5.7): *New connection from your wallet
established*, with a green dot. Its empty state reads *"Nothing has happened on your account
yet. Connecting your wallet will be the first entry."*

### 6. Pending: a real page, plus one small script (Ed, 2026-09-22: **changes a rule**)

**Connect payroll** and **Approve and share** each POST, and the server 303-redirects to a
pending page (`pending.html`, `pending-verify.html`). The pending page is complete without
JavaScript. It holds:

- a `role="status"` box, with a decorative indeterminate `.progress` bar (`aria-hidden`), and the
  copy *"Waiting for Meridian Payroll to say what it needs from you."* or *"Meridian Payroll is
  checking the credential you shared."*, each followed by *"This can take up to half a
  minute."* The copy says the wait is normal up front, and never says why.
- a **Check again** button, an ordinary GET that returns either this page again or the next step.
  With JavaScript it's a fallback only: hidden on load, shown again after 45 seconds if Payroll
  still hasn't replied. Pressing it then does the same check the script does, by hand.

**The script** (inline at the foot of both pages, about 15 lines, no library) runs only when the
server sets `data-poll` on the status box to a status URL. It hides Check again, polls that URL
every 2 seconds for `{"next": "<url>"}`, and calls `location.replace(next)` when it arrives.
After 45 seconds it shows Check again once more, in case something really has stalled.

**Why not `<meta http-equiv="refresh">`:** every reload makes a screen reader start the page
over and resets focus. Timed refresh is also a documented WCAG failure (F41, under 2.2.1).
Holding the POST open for about 20 seconds leaves nothing on screen but the browser's spinner.
`role="status"` is announced once on arrival, not on every poll. The bar stops moving under
`prefers-reduced-motion`.

**Rule change to record.** CLAUDE.md says "No JavaScript and no bundler, anywhere in these
pages." Ed approved amending it on 2026-09-22: **JavaScript is allowed sparingly, only where a
no-JS option is insufficient, as progressive enhancement over a page that already works
without it. No framework and no bundler.** This pending page is the only use. Add it to
`docs/decisions.md` and update CLAUDE.md's "Things that look like mistakes" list.

If the Render-to-Render gate (#48) turns out to affect this call, the pending page needs a
distinct *"Meridian Payroll isn't responding"* state. That page isn't designed. It would reuse
the caution band.

### 7. A connection lost to a restart: no visible difference

Proposed answer to the open question in Intent 004 and brief §6. If either app forgets the
connection, the Wallet shows whatever it still holds. A Wallet restart reads as "no employer
chosen", and a Payroll restart still reads as connected on the Wallet. No explanation is shown.
A wallet user wouldn't be told why a real provider lost their link, and the demo has no
reliable way to tell a lost connection from one that never existed. Revisit alongside the
per-person reset (#27).

### 8. Employer lookup

`.employers` is the `.people` list, reshaped for POST buttons. Each row is a full-width
`<button class="employers__row">` inside its own `<form method="post">`, 60px tall. It shows the
name in bold, then *"{industry} · {city}, NJ"*, then a hairline chevron. An employer already
added shows a neutral **– Added** badge in place of the chevron, and its button is `disabled`.
The list is alphabetical, with no search or filter, per the brief.

### 9. Credentials home, Income category

Once connected, with nothing issued: *"You're connected to Meridian Payroll. Your pay will
appear here as credentials once it starts sending them."* It's still one
`.category__waiting-note`, and nothing else on the page changes. Before connecting, Loop 2's
wording stands.

### 10. Payroll Connections, not connected

The Wallet's `.empty` copied verbatim, with the copy told from Payroll's side: *"You have no
connections yet. Your credential wallet is the first one you'll add, from its Connections
page."* **No button.** The connection starts in the Wallet, so there is nothing to press here.
A disabled button would imply an action that will never exist.

## New tokens

None. Every colour added is a Loop 2 status colour reused, or a darker or lighter step of one:
the caution band, and the four dots.

## New components

**Wallet:** `.panel__status--caution` · `.link-btn` · `.provider__head` / `.provider__emps` /
`.provider__emp` · `.employers` / `.employers__row` / `.employers__go` · `.request` /
`.request__item` · `.decision` / `.decision__lead` · `.actions` · `.pending` /
`.pending__fallback` · `.progress` · `.log__dot--neutral|verified|caution|error`.

**Payroll:** `.badge__icon`, `.empty`, `.log` and its parts, all copied verbatim from the
Wallet · the four `.log__dot` modifiers · `.connlist` / `.connlist__row` / `.connlist__meta`
(new).

## Accessibility

WCAG AA, as in Loops 0–3:

- One `<h1>` per page; `<header>`/`<main>`/`<footer>` landmarks; skip link; `<nav aria-label="Main">`.
- `aria-current="page"` is on Connections for every Connections state, and on Activity and
  Credentials for their pages. The lookup, consent and pending pages are steps inside a flow,
  so no nav item is current on them (Loop 2's detail-page convention).
- Every state change is a real `<button>` in a POST form: employer rows, Connect payroll, Try
  again, Remove, Disconnect, Approve, Deny, Close request. There are no disabled links.
  Already-added employers use `<button disabled>`.
- Targets: every button is ≥44px, employer rows are 60px, and `.link-btn` has
  `min-height: var(--tap)`.
- Badges keep a text label and a glyph (✓ ✕ ! –). Status is never colour alone.
- The request is an `<ol>`, so a screen reader hears how many credentials are asked for.
- The pending page is covered in §6.

## Known gaps left to implementation

1. **Hrefs are relative page links** so the bundle is browsable. Wire them to `/p/<id>/…`
   routes.
2. **Which claims Payroll requests** is assumed to be **name and date of birth**. The credential
   model doesn't list Payroll's claim paths. Set it in the DCQL-shaped request. The consent
   screen doesn't currently mark requested claims (§3).
3. **The Payroll landing page's "Coming soon" wallet card** (Loop 3) is now out of date. It
   isn't redrawn here. The smallest fix is to link it to Connections, or remove it.
4. **Person switchers** aren't redrawn. The Loop 2 and Loop 3 switchers stand.
5. **The Render gate state** (§6) and the **per-employer wording** in the consent purpose line
   (§3) are open.
6. Timestamps are fixed samples (22 September 2026), as in Loop 2.
