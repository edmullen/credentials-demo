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

Four of the five programs then add an income test and return a pass/fail decision. The fifth,
Dividend, has no income test for *eligibility* — it calculates a payment amount instead.

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
| `federal_poverty_level` | $15,960 | Health (138%), Food (185%) |
| `state_median_income` | $50,000 | Energy (60%) |
| `county_ami` | see table | Housing (30%) |
| `dividend_base` | $100 / month | Dividend |
| `dividend_max_bump` | $300 / month | Dividend |
| `dividend_phase_out` | $1,200 / month | Dividend |

Household size is **not** modelled: every figure here is a single-person household. Real FPL
and AMI scale with household size.

## Health

- Income threshold: **at or below 138% FPL** = **$22,024.80** annual.
- Eligible if both shared criteria are met and income is at or below the threshold.
- Ineligible if any of the three fails.

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
Permanent Fund Dividend. It behaves differently from the other four in two ways: there is no
income test for eligibility, and the decision is an **amount**, not a yes or no.

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
worse off. That is deliberately the opposite of the other four programs, which are cliffs: one
dollar over a threshold and the benefit goes from full to nothing. The demo shows both designs.

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

## Credential requirements

Consequences for the credential model (#21):

- **Identity credential** must carry `state` (residency test) and `county` (selects the
  Housing threshold). Both are required claims.
- **Payroll credential** must carry **gross** pay for the period, the pay period dates and the
  employer, so income can be summed and annualized.
- **Benefit credential** is a single type carrying the `program`, the `decision`, and an
  `amount` that is present for Dividend and absent for the other four.
