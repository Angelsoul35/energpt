# ADR 0002 — Money in integer cents, with one explicit rounding rule

## Status
Accepted.

## Context
Costs and savings must add up exactly. IEEE-754 floating point cannot represent
most decimal fractions (`0.1 + 0.2 == 0.30000000000000004`), so money built on
floats drifts, and a split that should reconcile does not. Consumption, meanwhile,
is naturally fractional in kWh, so some rounding to the cent is unavoidable — the
question is where it happens.

## Decision
Represent all money as an `int` number of **cents** and all energy as an `int`
number of **watt-hours**. Tariff rates are cents per kWh. A cost is:

```
cost_cents(energy_wh, rate_cents_per_kwh) = (energy_wh * rate + 500) // 1000
```

which is round-half-up in pure integer arithmetic. Rounding to the cent is
applied **once per aggregated tariff bucket** (total peak energy, total off-peak
energy, the shifted energy, the avoided standby energy), never per hour, so
rounding error cannot compound across hundreds of readings.

## Consequences
- Addition is exact; the peak and off-peak costs sum to the total with no drift.
- The arithmetic is recomputable by hand, which the tests rely on to assert exact
  values rather than approximate ones.
- Load factor is a ratio, not money, so it is a `float` rounded to four decimals
  for display; it never feeds a monetary calculation.
- Sub-cent precision and multi-part tariffs (standing charges, demand charges) are
  out of scope; a production system would extend the rate model, keeping the
  integer-cents discipline.
