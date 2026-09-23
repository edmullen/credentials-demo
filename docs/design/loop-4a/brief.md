# Design Brief: Loop 4a — UX improvements

These are the requirements for the Claude Design handoff that Loop 4a builds from. The brief is
written before design starts, and the handoff itself (`README.md`, `cred.css`, the pages) lands
beside this file.

Context: [Intent 004a](../../intents/004a-ux-improvements.md) ·
[issue #69](https://github.com/edmullen/credentials-demo/issues/69) ·
[Loop 4 handoff](../loop-4/README.md) · [Loop 3 handoff](../loop-3/README.md) ·
[Loop 2 handoff](../loop-2/README.md)

## 1. What this is

This is a demo of verifiable credentials across three fictional apps. After Loop 4, a demo runs
from employer lookup through consent to a live connection between the **Wallet** and **Meridian
Payroll**. This loop changes no behavior: no protocol, credentials or state. It improves how the
demo *reads and moves*:

- The Wallet gets a front door, plus a way to sign in and out.
- Page headers take less vertical space.
- Page titles tell the person what to do rather than naming the page.
- The consent page puts its decision where the person meets it.
- The person switcher says where everyone works.
- Payroll's paystub stays usable on a phone.

## 2. Pass depth: light, one proposal

Most of the loop adjusts components that already exist. Two pieces are new and deserve real
thought:

- the **Wallet landing page** (§4.1);
- the **compact page head**, which puts the back link and page name on one line (§4.3).

Everywhere else, make **one proposal, not options**. Reuse what's there, and keep every
component's existing structure unless a requirement below changes it.

## 3. What already exists: extend it, don't restart

The handoff pages and `cred.css` files below are authoritative. Ed hands them over as files.

- **The Wallet's current `cred.css`** (`apps/wallet/app/static/cred.css`), and its pages as the
  [Loop 4 handoff](../loop-4/README.md) left them: `wallet/*.html` in that folder, and
  [`person-switcher.html`](../loop-2/person-switcher.html) from Loop 2.
- **Payroll's current `cred.css`** (`apps/payroll/app/static/cred.css`), and its paystub page as
  the [Loop 3 handoff](../loop-3/paystub.html) left it.
- **The Wallet theme is fixed.** It uses `data-app="wallet"` and hue 52 (warm amber), with the
  Newsreader display face. `.wrap` and the header are capped at **`30rem`**, so the Wallet is a
  phone-shaped app on any display. That cap holds on every screen here, the landing page
  included.
- **Payroll's theme is fixed too.** It uses hue 255 and Archivo, with a `62rem` wrap. Its only
  change this loop is the paystub table (§4.8).
- **Payroll already has the sign-in pattern the Wallet needs.** Signed out, its header shows a
  **Sign in** button (`.btn`) where a signed-in person's initials would be. The Wallet copies
  that pattern (§4.1).

## 4. Screens and changes

Copy in quotes is final. It comes from #69 and goes into the templates verbatim. Item numbers
refer to #69.

### 4.1 Wallet landing page (item 1): new
This becomes the default screen when someone first comes to the Wallet. Today `/` goes straight
to the first person's credentials.

- **Headline:** "Wallet: Collect and present your credentials in one place"
- **Marketing blurb:** "Wallet is a secure place to store your credentials, like your ID, proof of
  income, and benefits you receive from the government."
- **Primary call to action:** a **Sign in** button that opens the default person's credentials.
- **Secondary message, subtle:** "This website is not a real service. It's a demo. Learn more
  here", with "Learn more here" linking to `https://github.com/edmullen/credentials-demo`.
- **Header:** a **Sign in** button replaces the initials, as on Payroll (§3). It also opens the
  default person's credentials.

Nobody is signed in on this page, so it has no nav, initials or Switch person link. Propose what
the header and footer show instead.

### 4.2 Sign out (item 2)
Add a **Sign out** link at the bottom of the navigation menu list. It returns the person to the
landing page. Sign out must be reachable at every width. Today the Wallet shows its nav inline in
the 30rem header, beside the initials, on wider screens, and behind the Menu disclosure on
narrow ones. Propose where Sign out sits at each width.

While signed in, the brand mark still leads to the person's credentials, not to the landing page.

### 4.3 The compact page head (item 7): new, used on every Wallet page
Across the Wallet, the page header, eyebrow and back link take up too much vertical space.
Replace them with one compact line:

- **The page name** is set small, like the current eyebrow, but **bold and black**.
- **A back link**, when the page has one, sits on the same line as the page name.

The effect should be like this:

> [‹ Connections](#)  |  **FIND YOUR EMPLOYER**

Design it once, for every Wallet page, with and without a back link. It must hold up at phone
width when the page name is long, as in "Request from Meridian Payroll" beside a back link. Keep
one `<h1>` per page, and say in the README which element carries it.

### 4.4 Step titles (item 8)
Intro titles stop simply naming the page. They tell the person **what step to take on that
page**, and the page's name moves into the page head (§4.3).

| Page | Page head | Intro title |
|---|---|---|
| Credentials | Credentials | *none* |
| Connections: no connections yet, or after connections are made | Connections | "You have [count] connections" |
| Connections: after selecting an employer | Connections | "Now connect your payroll" |
| Find your employer | ‹ Connections \| Find your employer | "Select your employer" |
| Activity | Activity | *none* |
| Consent (§4.5) | ‹ Connections \| Request from Meridian Payroll | "Do you want to share 1 credential with Meridian Payroll?" |

- **Count wording:** use plain pluralization, as in "You have 0 connections" and "You have 1
  connection".
- **Other pages:** #69 doesn't name every Wallet page. Apply the page head to all of them and
  propose each one's page name and intro title: the credential detail page, the two pending
  pages and the person switcher.
- **Find your employer:** the page head follows item 7's example (back to Connections, page name
  "Find your employer").

### 4.5 Consent page (item 9)
- **Page head:** "Request from Meridian Payroll" moves into the page head (§4.3).
- **Intro title:** "Meridian Payroll is asking for 1 credential" becomes "Do you want to share 1
  credential with Meridian Payroll?"
- **Purpose line:** "It runs payroll for Crossroads Diner Group…" becomes "Meridian Payroll runs
  payroll for Crossroads Diner Group…". The rest of the sentence is unchanged.
- **Status area:** the credential's status area uses the same format as `cred__top` on the
  Credentials page, with the issuer on one side and the badge on the other. There's **no green
  tint**: the area is white, with the green Verified badge. A tampered credential keeps its red
  badge the same way. **This applies to the consent page only.** The credential detail page keeps
  its tinted status band.
- **Decision placement:** the Approve and Deny buttons move up, between the purpose line and the
  credential review. Propose where the missing-credential variant's **Close request** goes. Ray
  Miller and Megan Doyle have no identity credential and always reach that variant.

### 4.6 Credentials page (items 3, 10)
- **Find your employer (item 3).** The Income category's dotted note is shown before any
  connection to Payroll exists. Inside it, add a **Find your employer** button that goes straight
  to the Find your employer screen. Propose whether it stays once an employer has been chosen but
  not yet connected.
- **Date of birth (item 10).** In the identity card, add "DOB: [MM/DD/YY]" under the name, for
  example "DOB: 03/11/82".

### 4.7 Person switcher (item 4)
Under each person's city and state, add "Employers: [list all employers]". Five people have more
than one employer: p06, p17 and p25 have two, and p07 and p08 have three. Use "Employer:" when
there's only one. This line is a demo aid for choosing whom to demo as. Nothing else in the
Wallet uses it.

### 4.8 Payroll paystub (Payroll item)
On the paystub page, the earnings table gets cut off on mobile and can't be scrolled
horizontally. The page needs to work at phone width. Propose the treatment, and make sure it
works for keyboard users as well as touch.

### 4.9 Wallet stylesheet sizes (items 5, 6)
- `html[data-app="wallet"] .main`: reduce the top padding by half.
- `.intro__title`: reduce the font size to `2rem`.

These are starting values from #69. Tune them together with the page head (§4.3) so the whole
top of each page reads as one intended rhythm, and record the final values in the README.

## 5. Constraints

- **JavaScript only sparingly**, as progressive enhancement over a page that already works
  without it (decisions.md, "JavaScript is allowed sparingly"). The one existing use is the
  Wallet's pending-page poll. Nothing in this loop should need more.
- Copy, class names and ARIA attributes go **verbatim** into the Jinja templates, so write them
  as production strings.
- **Accessibility:** WCAG AA, as in Loops 0–4. That means 44px minimum targets, visible focus,
  one `<h1>` per page, landmarks, and `aria-current="page"` on the active nav item.
- **Every page is server-rendered per person, with the person in the URL.** There are no
  passwords and no sessions: Sign in and Sign out are navigation, not authentication.
- **Each app keeps its own `cred.css`.** Wallet changes go in the Wallet's copy only. Payroll's
  only change is the paystub table, and Payroll's headers stay as they are.
- **Nothing may imply a real service.** The landing page's secondary message and the footer's
  demo note both carry this.

## 6. Deliverables

These go into `docs/design/loop-4a/`, in the same shape as earlier handoffs:

- **Two updated `cred.css` files**, one per app, each a superset of that app's current file.
- **One static HTML page per changed screen and state** in §4. That includes the landing page,
  each step-title state, the consent page (verified, tampered and missing) and the paystub.
- **A `README.md`** documenting new tokens, components, final sizes and accessibility decisions.
- **Screenshots of every page at 375px.** Also include the Wallet at its `30rem` width, and
  Payroll's paystub at `62rem`.

The handoff is a **historical record**. The apps are never edited to match it afterwards, so
anything that must survive belongs in the README.
