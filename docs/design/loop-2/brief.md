# Design Brief: Loop 2 — Wallet Stands Up

Requirements for the Claude Design handoff that Loop 2 builds from. Written before design starts; the handoff itself (`README.md`, `cred.css`, the pages) lands beside this file.

Context: [Intent 002](../../intents/002-wallet-stands-up.md) ·
[credential model](../../credential-model.md) · [sample data](../../sample-data.md) ·
[Loop 0 handoff](../loop-0/README.md)

## 1. What this is

A demo of verifiable credentials across three fictional apps. This loop is the **Wallet**
only: the app where a member of the public holds credentials and sees whether each one can
be trusted. Loop 0 shipped its placeholder home page. Nothing else in the Wallet exists yet.

The story this loop has to tell on screen: *a credential is signed, and a signature makes
tampering visible.* Two of the 25 sample people hold a credential that has been altered
after signing, and the Wallet must show that plainly without the person needing to know what
a signature is.

## 2. What already exists — extend it, don't restart

`cred.css` and the three Loop 0 pages are **authoritative and already in the repo**, imported
back into Claude Design with `/design-sync` before this work starts. Tokens, the five
components, the theming model and the accessibility rules all carry forward unchanged. Adding
a component is expected; redefining an existing one is not.

The Wallet theme is fixed: `data-app="wallet"`, hue 52, `--bg: #F7F7F5`, radius 10/16px,
Newsreader display face, **`.wrap` and header capped at `30rem`**.

**That 30rem cap holds on every new screen**, including the 25-person switcher. The Wallet is
a phone-shaped app on any display, because that is what a real wallet is. If a screen genuinely
cannot work in a single 30rem column, say so and propose the narrowest exception that solves it
— don't widen the theme.

## 3. Screens

Six, all under the wallet theme. Header nav becomes **Credentials · Connections · Activity**
("Help" is removed). The footer gains a link to the person switcher.

### 3.1 Credentials — the home screen
Replaces the Loop 0 "Coming soon" page. Lists the credentials the selected person holds, as
preview cards showing what the credential is, who issued it, and its status badge. Opening one
goes to the detail screen.

**Only the Identity credential carries a photo.** Income and benefit credentials have no `image`
claim at all ([credential model §3](../../credential-model.md#3-claim-schemas)), so the photo is
what distinguishes identity from the other two types — not a property every credential card has.

Credentials group by **category** — Identity, Income, Benefits. Only Identity exists this loop; design the grouping so Loops 5 and 6 add a group without a new layout. A person may eventually hold six or more income credentials from one issuer, so the grouping has to survive a long list. Consider stacked, overlapping cards with some affordance that implies the ability to open for full details.

The Identity credential should have a base color of white. Future credentials will have color schemes that vary from the Identity credential.

### 3.2 Credential detail
One credential in full. **Written for the person holding it, with the machinery behind a
disclosure.** Plain-language labels by default — "Date of birth", not `birthDate` — and a
`<details>` reveal holding the technical envelope: credential id, issuer identifier, `type`,
`validFrom`/`validUntil`, and the raw JWT. A wallet first; a demo of how VCs work second.

Claims to display, per [credential model §3](../../credential-model.md#3-claim-schemas):
given and family name, date of birth, photo, and a postal address of street, locality,
county, state and postal code.

The **status badge** is the centrepiece — see §4.

### 3.3 Empty state
The person holds no credentials at all. Ray Miller and Megan Doyle are in this state, and it is reachable from the first moment of the demo, not an edge case. The lack of an identity credential would defeat the purpose of the Wallet app. Adding an identity credential would be the first action of a user in a real world situation, but for now, we will not build Add Identity credential functionality. The UI should have a demarcated space where the identity credential would be placed, and in that space, include a message such as, "You have not yet added an Identity credential" with an "Add Identity" button, which is deactivated. 

### 3.4 Connections (#14)
A placeholder this loop: heading, and whatever an empty Connections screen should say. Loop 4 fills it with an employer, a **Connect payroll** button, and a connected state — design the empty screen knowing that is what arrives.

### 3.5 Activity (#15)
Also a placeholder: heading, plus **one sample item** to establish the pattern — a circle icon, a timestamp, and a message ("New connection to Meridian Payroll established"). This will be an activity log page, so the display should read as a chronological listing of events that happen. Nothing in Loop 2 generates a real event.
Both the nav item and the page heading read **Activity** — #15's body still says "Activities",
and the issue gets corrected rather than the design.

### 3.6 Person switcher
**Its own page**, reached from the footer, listing all 25 sample people so the demo can move
between them. Demo scaffolding, not part of the product story — but it should feel of a piece
with the app, and it may grow metadata about each person later, so leave it room.

## 4. The status badge

The badge carries the loop's whole argument, and `cred.css` has three variants today
(`neutral`, `verified`, `error`). [Credential model §5](../../credential-model.md#5-expiration-and-verification-failure)
defines **five** verification outcomes:

| Outcome | Reachable in Loop 2 |
|---|---|
| Verified | Yes — 21 people |
| Tampered | Yes — 2 people |
| Expired | No |
| Not yet valid | No |
| Unrecognized issuer | No |

**Please propose the mapping**, including whether a fourth variant is needed. Expired and
Not-yet-valid are not failures of the same kind as Tampered — one is a forgery, the others are
timing — and flattening all four onto `error` would say the wrong thing. Loop 2 renders only
two, but the badge shouldn't need redesigning when the rest arrive.

Each outcome has a message to the person, already drafted in §5 of the credential model. Treat
that copy as a starting point and improve it; it hasn't had a plain-language pass.

Rules that carry over: **label plus icon, never color alone**, and status colors do not retint
per app.

## 5. Facts to design against

- **25 people, 23 photos.** The two with no photo are exactly the two with no identity
  credential, so a missing photo never appears where one is expected. Photos are
  **200×250 portrait JPEGs, ~18 KB**, ID-style: front-facing, plain background, each watermarked "Not real person". They are claims
  inside the credential, not profile pictures — design them as part of the credential, and don't
  crop to a circle.
- **The header identity element stays initials**, not the photo: two people have no photo, and
  the `.initials` component already handles it. Longest name is 14 characters.
- **21 of 25 people are in New Jersey**, the rest in Michigan, New York and Ohio. The Wallet is
  not an NJ app — an out-of-state credential displays exactly like any other.
- **Four issuers this loop**, all states: "State of New Jersey", Michigan, New York, Ohio.
- The person switcher needs to convey at a glance which people demonstrate which state
  (verified, tampered, none) — that is what the demo operator is choosing between.

## 6. Constraints

- **JavaScript is open this loop.** The Loop 0 pages have none because that handoff specified
  none; it was never a project-wide decision. Plain semantic HTML and CSS remain the default and
  server-rendered Jinja templates are the target, so reach for script only where it genuinely
  earns its place — and **no client-side framework and no bundler**, which is a separate rule
  and still holds.
- Copy, class names and ARIA attributes are taken **verbatim** into the templates, so write them
  as production strings.
- WCAG AA as in Loop 0: 44px minimum targets, visible focus, one `<h1>`, landmarks, real
  `<button disabled>` rather than disabled links, `aria-current="page"` on the active nav item.
- Every page is server-rendered per person, with the person in the URL. No sign-in, no session.
- Nothing may imply this is a real government service. The footer says plainly that the people,
  employers, agencies and credentials are invented (#11).

## 7. Deliverables

Into `docs/design/loop-2/`, matching the Loop 0 handoff's shape: an updated `cred.css` (a
superset of the current one), one static HTML page per screen above, a `README.md` documenting
new tokens, components, states and accessibility decisions, and desktop screenshots. The
handoff is a historical record — the repo's apps are never edited to match it afterwards, so
anything that must survive belongs in the README.
