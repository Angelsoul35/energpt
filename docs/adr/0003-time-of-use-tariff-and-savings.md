# ADR 0003 — A two-rate time-of-use tariff and two grounded savings levers

## Status
Accepted.

## Context
Savings advice has to come from somewhere defensible. A flat per-kWh rate gives
nothing to optimise against: you can only use less. Real households increasingly
sit on **time-of-use** tariffs, where the same kWh costs more in a peak window,
and that price difference is what makes *when* you use energy matter. The advice
must follow from that structure, not from a guess.

## Decision
Model a **two-rate time-of-use tariff**: hours in `[EP_PEAK_START_HOUR,
EP_PEAK_END_HOUR)` are billed at the peak rate, every other hour at the off-peak
rate (the window may wrap midnight). From this, compute two savings levers, each
grounded in the energy split:

- **Load shift.** Moving `EP_SHIFTABLE_PCT` of the peak-window energy to off-peak
  saves the rate difference on the shifted energy. The total energy is unchanged;
  only its timing moves.
- **Standby / base-load reduction.** The base load (the overnight minimum) runs
  every hour, so trimming `EP_STANDBY_REDUCTION_PCT` of it is valued hour-by-hour
  at each hour's own rate — peak-hour draw at the peak rate, off-peak draw at the
  off-peak rate.

Both are configuration-driven assumptions, stated as such, applied with exact
arithmetic.

## Consequences
- The advice is a direct, checkable consequence of the tariff and the series: a
  home whose usage peak sits inside the expensive window has a large shift saving;
  a flat overnight-heavy load does not.
- The percentages are honest *assumptions*, not a measured audit, and are exposed
  as settings so an operator can tune them (or set them from real appliance-level
  data later).
- A single flat rate is a degenerate case (set both rates equal), where the shift
  saving correctly falls to zero.
- It is deliberately simpler than a real bill: no standing charge, no demand
  charge, no feed-in. Those are the first extensions a production model would add.
