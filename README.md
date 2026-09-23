# credentials-demo

A demonstration of a verifiable-credentials ecosystem, built as three small web apps:

- **Wallet** — where a person holds their credentials and sees whether each can be trusted.
- **Payroll** — an employer's payroll provider, which issues income credentials.
- **Benefits** — an agency that asks for credentials, checks eligibility for five benefit programs,
  and issues its own credentials.

Credentials are signed JWTs shaped like [W3C Verifiable Credentials](https://www.w3.org/TR/vc-data-model-2.0/),
passed over simple REST APIs.

## This is a demo, and everything in it is fictional

- The people, employers, agencies, benefit programs and credentials are **invented**. Any
  resemblance to a real person or organization is coincidence.
- **Nothing here is a real government, payroll or benefits service.** Where a credential names a
  state, that is illustration only; the issuers are `did:example:` identifiers, the form the W3C
  reserves for examples.
- The identity photos are **AI-generated faces of people who do not exist**, each watermarked
  "Not real person". No photo of a real person is used.
- There is no real personal data, and no passwords or accounts. Do not enter any.

## Live apps

Hosted on Render's free tier, so the first request after a quiet spell can take up to a minute.
**Each app sleeps independently and does not wake the other two**, so if you're planning to try
the demo, visit all three URLs first — one at a time, waiting for each to load — before you
start.

- Wallet: <https://cred-demo-wallet.onrender.com>
- Payroll: <https://cred-demo-payroll.onrender.com>
- Benefits: <https://cred-demo-benefits.onrender.com>

## Running locally

Each app is its own [uv](https://docs.astral.sh/uv/) project; there is no repo-root Python
project. From inside an app's directory:

```bash
cd apps/wallet && uv sync && uv run uvicorn app.main:app --reload --port 8001
```

Ports: wallet 8001, payroll 8002, benefits 8003. To have a locally running Wallet reach a
locally running Payroll instead of the live one, set `MERIDIAN_PAYROLL_URL`:

```bash
MERIDIAN_PAYROLL_URL=http://localhost:8002 uv run uvicorn app.main:app --reload --port 8001
```

## More

Design decisions are recorded in [docs/decisions.md](docs/decisions.md).
