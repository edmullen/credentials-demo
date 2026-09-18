# Benefit Programs and Eligibility

The five fictional programs the Benefits app offers, and how eligibility is determined.
Written for GitHub issue #7 and consumed by #20 (program pages), #6 (sample data) and #21
(credential model).

**These are not real programs and these figures are not policy.** They are plausible
inventions sized to make a demo legible. Values are fixed variables, stated "as of" below,
and would in reality change every year.

## Shared criteria

Every program requires both of:

1. **A valid identity credential** — the signature verifies against the issuing state's key.
   A tampered credential fails here, and a person holding no identity credential cannot apply
   at all (they have nothing to present).
2. **Proof of New Jersey residency** — the `state` claim on that identity credential is NJ.

The five programs then split into two shapes:

- **Pass/fail on an income threshold** — Food, Energy and Housing. Income above the threshold
  is a denial.
- **A calculated result on a sliding scale** — Health and Dividend. Income never denies
  eligibility; it sets how much. Health determines a discount on a plan anyone may buy into,
  Dividend a monthly payment. Both taper so that earning more never leaves someone worse off,
  deliberately contrasting with the cliffs above.

## Income

Income means **gross** pay, never net. Gross is what these tests are defined against, and both
figures appear on a paystub, so the payroll credential carries gross explicitly.

Two different figures are used, and which one applies depends on the program:

- **Annual income** — used by Health, Food, Energy and Housing, whose thresholds are published
  as annual figures:

  ```
  annual income = (sum of gross pay across all of the person's paystub credentials) × 12
  ```

  The two semi-monthly paystubs per employer together make one month, so the ×12 applies to
  that monthly total — not to each paystub. For people with two or three employers, all
  paystub credentials are summed before multiplying.

- **Monthly income** — used by Dividend: the same sum, one step earlier, with no ×12.

**Stated simplification:** annualizing a single month of pay ignores seasonality and the
variability of gig work — which is least accurate for exactly the multi-employer people the
sample data includes. Accepted for now to validate the rest of the demo.

## Variables

As of the initial definition (September 2026):

| Variable | Value | Used by |
|---|---|---|
| `federal_poverty_level` | $15,960 | Health (138% / 500%), Food (185%) |
| `state_median_income` | $50,000 | Energy (60%) |
| `county_ami` | see table | Housing (30%) |
| `health_plan_cost` | $750 / month | Health |
| `health_full_discount_ceiling` | 138% FPL | Health — 100% discount at or below |
| `health_zero_discount_floor` | 500% FPL | Health — full price at or above |
| `dividend_base` | $100 / month | Dividend |
| `dividend_max_bump` | $300 / month | Dividend |
| `dividend_phase_out` | $1,200 / month | Dividend |

Health's and Dividend's tapers are both derived from their bounds rather than hard-coded, so
moving a phase-out point is a one-variable change:
`health taper = health_plan_cost / (zero_discount_floor − full_discount_ceiling)`, and
`dividend taper = dividend_max_bump / dividend_phase_out`.

Household size is **not** modelled: every figure here is a single-person household. Real FPL
and AMI scale with household size.

## Health

Health provides access to the Public Option health care plan. **Anyone can buy into the plan**
— the program determines the *discount*, not whether someone may enroll. So, like Dividend and
unlike the other three, Health is not pass/fail: meeting the two shared criteria produces a
discount between 100% and 0%.

- Full price: **$750.00 / month**.
- **100% discount** (free) at or below **138% FPL** = $22,024.80 annual.
- **0% discount** (full price) at or above **500% FPL** = $79,800.00 annual.
- Between those, the discount tapers linearly:

```
discount = 1                                       if income <= 22,024.80
         = 0                                       if income >= 79,800.00
         = (79,800.00 - income) / 57,775.20        otherwise

monthly premium = 750.00 x (1 - discount)
```

| FPL % | Annual income | Discount | Premium / mo | Premium / yr |
|---|---|---|---|---|
| 138% | $22,024.80 | 100.0% | $0.00 | $0.00 |
| 150% | $23,940.00 | 96.7% | $24.86 | $298.34 |
| 175% | $27,930.00 | 89.8% | $76.66 | $919.89 |
| 200% | $31,920.00 | 82.9% | $128.45 | $1,541.44 |
| 250% | $39,900.00 | 69.1% | $232.04 | $2,784.53 |
| 300% | $47,880.00 | 55.2% | $335.64 | $4,027.62 |
| 350% | $55,860.00 | 41.4% | $439.23 | $5,270.72 |
| 400% | $63,840.00 | 27.6% | $542.82 | $6,513.81 |
| 450% | $71,820.00 | 13.8% | $646.41 | $7,756.91 |
| 500% and above | $79,800.00 | 0.0% | $750.00 | $9,000.00 |

The taper band spans $57,775.20, so the premium rises **$12.98 per $1,000 of annual income** —
about 15.6¢ of each additional dollar earned. The 50% discount point falls at $50,912.40
(319% FPL).

**Why it's a scale rather than a threshold.** Under a pass/fail rule at 138% FPL, earning one
dollar more costs $9,000 a year in lost coverage — a cliff nobody would rationally cross. The
taper replaces that with a 15.6% marginal rate, so money in hand still rises with every extra
dollar earned. This is the sharpest illustration of the cliff problem in the demo; Dividend
makes the same point at a smaller scale.

**Consequence for the demo:** income does not produce a Health *denial*. Everyone verified
and NJ-resident gets access at some price. Food, Energy and Housing remain the three pass/fail
programs where income can produce a "no".

### What the credential carries

Health's determination is a **discount**, and that is what the credential asserts. The dollar
premium is derived at display time. The credential's `credentialSubject`:

```json
{
  "program": "health",
  "discountPercent": 82.9,
  "planCost": { "type": "MonetaryAmount", "value": 750.00, "currency": "USD" }
}
```

- `discountPercent` — the entitlement Benefits determined.
- `planCost` — the monthly rate in force when it was decided. *When* is not a claim: it is the
  credential's standard `validFrom`.
- There is no `decision` claim. Holding a Health credential **means** eligible; a denial
  produces no credential at all (see Credential requirements).

Rendered by whatever displays it — the Wallet's credential detail, or the determination
result:

> Current rate is $750.00 per month. With your 82.9% discount, you'd pay **$128.45**.

Three rules this follows, which apply to the credential model generally (#21):

- **Assert the entitlement, derive the money.** A discount stays true if the plan's price
  changes; a stored premium silently doesn't. The premium is one multiplication away from two
  claims that are already present, so there is no `premium` claim.
- **Claims are facts as of the determination; UI text is never a claim.** The sentence above
  is composed by the display, not carried in the credential — signed prose can't be reworded,
  translated or corrected without re-issuing.
- **Carry the price snapshot for provenance.** `planCost`, read together with the credential's
  `validFrom`, records the conditions the decision was made under, so an older credential
  remains honest if the rate moves. Dividend needs no equivalent because its amount is a
  payment with no external price attached.

Rendering a derived number is **not** the Wallet re-deciding eligibility — it is multiplying
two claims. Benefits remains the only app that determines entitlement.

## Food Assistance

- Income threshold: **at or below 185% FPL** = **$29,526.00** annual.
- Eligible if both shared criteria are met and income is at or below the threshold.
- Ineligible if any of the three fails.

## Energy Assistance

- Income threshold: **at or below 60% of State Median Income** = **$30,000.00** annual.
- Eligible if both shared criteria are met and income is at or below the threshold.
- Ineligible if any of the three fails.

Note: Energy's threshold sits only $474 above Food's, so the two programs return the same
answer for almost every income. The sample data places one persona deliberately between them
(see Sample data requirements).

## Housing Assistance

- Income threshold: **at or below 30% of the applicant's county AMI** — between $19,349.70
  (Cumberland) and $41,835.90 (Hunterdon).
- Eligible if both shared criteria are met and income is at or below that county's threshold.
- Ineligible if any of the three fails.

Housing is the only program whose threshold depends on **where** the applicant lives, which
makes county an input to a real calculation rather than decoration. It is also the only
program where the same income produces different outcomes for different people.

| County | AMI | 30% threshold |
|---|---|---|
| Hunterdon | $139,453 | $41,835.90 |
| Somerset | $135,960 | $40,788.00 |
| Morris | $134,929 | $40,478.70 |
| Bergen | $123,715 | $37,114.50 |
| Monmouth | $122,727 | $36,818.10 |
| Sussex | $114,316 | $34,294.80 |
| Middlesex | $109,028 | $32,708.40 |
| Burlington | $105,271 | $31,581.30 |
| Gloucester | $102,807 | $30,842.10 |
| Union | $100,117 | $30,035.10 |
| Warren | $99,596 | $29,878.80 |
| Mercer | $96,333 | $28,899.90 |
| Hudson | $90,032 | $27,009.60 |
| Cape May | $88,046 | $26,413.80 |
| Passaic | $87,137 | $26,141.10 |
| Ocean | $86,411 | $25,923.30 |
| Camden | $86,384 | $25,915.20 |
| Salem | $78,412 | $23,523.60 |
| Atlantic | $76,819 | $23,045.70 |
| Essex | $76,712 | $23,013.60 |
| Cumberland | $64,499 | $19,349.70 |

## Dividend

An invention rather than an analogue of a real program — part cash assistance, part Alaska's
Permanent Fund Dividend. Like Health, and unlike the three pass/fail programs, income never
denies eligibility: it sets the amount. Unlike Health, the amount is money received rather
than a discount on money owed, so the credential needs no price snapshot.

Anyone meeting the two shared criteria receives a base payment. Below a phase-out point they
also receive a scaled bump that tapers as income rises:

```
taper = dividend_max_bump / dividend_phase_out          # 300 / 1200 = 0.25
monthly benefit = dividend_base + max(0, dividend_max_bump - taper × monthly gross)
                = 100 + max(0, 300 - 0.25 × monthly gross)
```

| Monthly gross | Benefit | In hand (earnings + benefit) |
|---|---|---|
| $0 | $400.00 | $400.00 |
| $200 | $350.00 | $550.00 |
| $400 | $300.00 | $700.00 |
| $600 | $250.00 | $850.00 |
| $800 | $200.00 | $1,000.00 |
| $1,000 | $150.00 | $1,150.00 |
| $1,200 | $100.00 | $1,300.00 |
| $2,400 | $100.00 | $2,500.00 |

**Why the taper exists.** In the phase-out range each additional dollar earned keeps 75¢ after
the bump is withdrawn; above $1,200 it keeps the full dollar. Total money in hand therefore
rises at every income level — there is no point on the curve where earning more leaves someone
worse off. That is deliberately the opposite of the other three pass/fail programs, which are
cliffs: one dollar over a threshold and the benefit goes from full to nothing. The demo shows
both designs.

**Arithmetic.** Compute in integer cents and round once at the end. A half-cent-per-cent
reduction produces fractional cents at odd income figures, and rounding mid-calculation makes
totals drift by a cent depending on evaluation order.

## Sample data requirements

For these rules to be visible, the personas in #6 have to be placed deliberately:

- **Two personas with identical income in different counties** — one high-AMI (Hunterdon,
  $41,835.90) and one low-AMI (Cumberland, $19,349.70) — so the same income yields different
  Housing decisions.
- **One persona between $29,526 and $30,000 annual**, where Energy says yes and Food says no.
- **Two or three part-time personas earning $500–$1,200 per month**, so the Dividend taper
  appears at all. Everyone earning above $1,200 a month lands on the $100 floor, and every
  full-time persona does.
- Plus the identity factors already specified in #6: 21 verified (18 NJ, 3 out-of-state),
  2 tampered, 2 with no credential.

Health's scale needs no special placement: personas earning roughly $20,000–$60,000 a year
span 125%–376% FPL, which lands most of them inside the taper with visibly different
discounts. Anyone at or above $79,800 would pay full price, and the part-time personas above
sit at or below the 138% ceiling, so they pay nothing.

## Credential requirements

Consequences for the credential model (#21):

- **Identity credential** must carry `state` (residency test) and `county` (selects the
  Housing threshold). Both are required claims.
- **Payroll credential** must carry **gross** pay for the period, the pay period dates and the
  employer, so income can be summed and annualized.
- **Benefit credential** is a single type — `["VerifiableCredential", "BenefitCredential"]` —
  whose `credentialSubject` carries the `program` plus **named claims** for whatever that
  program determined:

  | Program | `credentialSubject` claims |
  |---|---|
  | Food, Energy, Housing | `program` |
  | Dividend | `program`, `monthlyPayment` (MonetaryAmount) |
  | Health | `program`, `discountPercent`, `planCost` (MonetaryAmount) |

  Money values use schema.org's `MonetaryAmount` (value and currency) rather than a bare
  number. Claim names are camelCase, following the W3C VC Data Model's own convention.
- **A denial produces no credential.** A credential attests to an entitlement the holder may
  need to prove; a denial is not one. So there is no `decision` claim — holding a benefit
  credential means eligible for that program. The denial still appears on the determination
  result, in Benefits' admin record, and in the Wallet's Activity log.

Two rules the Health section establishes for the model as a whole: **assert the entitlement
and derive the money**, and **claims are facts as of the determination — UI text is never a
claim.**
