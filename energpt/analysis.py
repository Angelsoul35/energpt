"""The deterministic analysis engine — the real value of EnerGPT.

Everything a reader will later act on is computed here, with plain arithmetic, so
it is reproducible and auditable. The LLM (in :mod:`energpt.advisor`) only *phrases*
these numbers; it never produces them.

Units and money. Consumption readings are integer **watt-hours** (Wh). Money is
integer **cents**, never a float: tariff rates are cents per kWh, and a cost is

    cost_cents(energy_wh, rate) = round_half_up(energy_wh * rate / 1000)

implemented as ``(energy_wh * rate + 500) // 1000`` — pure integer arithmetic.
Rounding to the cent is applied once per aggregated tariff bucket, not per hour,
so rounding error cannot compound.

What is computed:

* **Peak-usage hours** — the hours of day at which the home consumes most, from
  the average reading at each hour of day.
* **Base load** — the overnight minimum reading, i.e. the always-on floor.
* **Load factor** — average load divided by peak load; a flatness score in
  ``(0, 1]`` (low = spiky, expensive-to-serve; high = flat).
* **Cost under a time-of-use tariff** — energy split into peak and off-peak
  buckets and priced.
* **Savings opportunities** — quantified in kWh and cents: shifting part of the
  peak load to off-peak, and trimming standby/base-load draw.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import Settings, get_settings


def cost_cents(energy_wh: int, rate_cents_per_kwh: int) -> int:
    """Cost of ``energy_wh`` watt-hours at ``rate_cents_per_kwh``, rounded to the
    nearest cent (half up). Pure integer arithmetic; money is never a float."""
    return (energy_wh * rate_cents_per_kwh + 500) // 1000


@dataclass(frozen=True)
class Opportunity:
    """One quantified saving, computed from the analysis (not invented)."""

    key: str                    # machine key: "load_shift" | "standby"
    title: str                  # short human label
    energy_wh: int              # energy shifted or saved over the analysed period
    saving_cents: int           # money saved over the analysed period
    rationale: str              # the computed basis, in one sentence


@dataclass(frozen=True)
class Analysis:
    # Period
    hours: int
    days: int
    total_wh: int

    # Consumption profile
    average_wh: int
    peak_wh: int                 # the single highest hourly reading
    base_load_wh: int            # overnight minimum (always-on floor)
    load_factor: float           # average / peak, in (0, 1]
    peak_usage_hours: list[int]  # hours of day with the highest average usage
    peak_usage_avg_wh: int       # average reading at the top usage hour
    usage_peak_in_tariff_window: int  # how many peak-usage hours fall in the peak tariff window

    # Tariff
    peak_window: tuple[int, int]
    peak_rate_cents: int
    offpeak_rate_cents: int
    n_peak_hours: int
    n_offpeak_hours: int
    peak_energy_wh: int
    offpeak_energy_wh: int
    peak_cost_cents: int
    offpeak_cost_cents: int
    total_cost_cents: int
    avg_daily_cost_cents: int
    projected_monthly_cost_cents: int  # avg daily cost * 30

    # Savings
    opportunities: list[Opportunity] = field(default_factory=list)
    total_saving_cents: int = 0
    projected_monthly_saving_cents: int = 0

    @property
    def total_kwh(self) -> float:
        return round(self.total_wh / 1000, 3)


def _hour_of_day(index: int, start_hour: int) -> int:
    return (start_hour + index) % 24


def _average_by_hour(series: list[int], start_hour: int) -> dict[int, int]:
    """Mean reading at each hour of day, as an integer (floor)."""
    totals: dict[int, int] = {}
    counts: dict[int, int] = {}
    for i, value in enumerate(series):
        h = _hour_of_day(i, start_hour)
        totals[h] = totals.get(h, 0) + value
        counts[h] = counts.get(h, 0) + 1
    return {h: totals[h] // counts[h] for h in totals}


def _in_window(hour: int, start: int, end: int) -> bool:
    """True if ``hour`` is in ``[start, end)``, supporting windows that wrap midnight."""
    if start <= end:
        return start <= hour < end
    return hour >= start or hour < end


def analyse(
    series: list[int],
    settings: Settings | None = None,
    *,
    start_hour: int = 0,
) -> Analysis:
    """Analyse an hourly consumption series (watt-hours), starting at ``start_hour``.

    All results are a deterministic function of the series and the settings.
    """
    settings = settings or get_settings()
    if not series:
        raise ValueError("series is empty")
    if any(v < 0 for v in series):
        raise ValueError("consumption readings must be non-negative")

    hours = len(series)
    total_wh = sum(series)
    average_wh = total_wh // hours
    peak_wh = max(series)

    # Base load: the minimum reading inside the overnight window.
    overnight = [
        v
        for i, v in enumerate(series)
        if _in_window(
            _hour_of_day(i, start_hour),
            settings.overnight_start_hour,
            settings.overnight_end_hour,
        )
    ]
    base_load_wh = min(overnight) if overnight else min(series)

    # Load factor: how flat the demand is. A float ratio (not money), reported to
    # four decimals. 1.0 would be a perfectly flat load; spiky homes score low.
    load_factor = round(total_wh / hours / peak_wh, 4) if peak_wh else 0.0

    # Peak-usage hours: the hours of day with the highest average reading. Ties
    # are broken by the earlier hour so the result is deterministic.
    avg_by_hour = _average_by_hour(series, start_hour)
    ranked = sorted(avg_by_hour, key=lambda h: (-avg_by_hour[h], h))
    peak_usage_hours = ranked[: settings.top_usage_hours]
    peak_usage_avg_wh = avg_by_hour[peak_usage_hours[0]] if peak_usage_hours else 0
    usage_peak_in_tariff_window = sum(
        1
        for h in peak_usage_hours
        if _in_window(h, settings.peak_start_hour, settings.peak_end_hour)
    )

    # Tariff: split energy into peak and off-peak buckets and price each.
    peak_energy_wh = 0
    offpeak_energy_wh = 0
    n_peak_hours = 0
    n_offpeak_hours = 0
    for i, value in enumerate(series):
        if _in_window(
            _hour_of_day(i, start_hour), settings.peak_start_hour, settings.peak_end_hour
        ):
            peak_energy_wh += value
            n_peak_hours += 1
        else:
            offpeak_energy_wh += value
            n_offpeak_hours += 1

    peak_cost_cents = cost_cents(peak_energy_wh, settings.peak_rate_cents)
    offpeak_cost_cents = cost_cents(offpeak_energy_wh, settings.offpeak_rate_cents)
    total_cost_cents = peak_cost_cents + offpeak_cost_cents
    days = hours / 24 if hours >= 24 else 1
    avg_daily_cost_cents = int(total_cost_cents / days) if days else total_cost_cents
    projected_monthly_cost_cents = avg_daily_cost_cents * 30

    # Opportunity 1: shift part of the peak-hour energy to off-peak. You still use
    # the energy, just at the cheaper rate, so the saving is the rate difference
    # applied to the shifted energy.
    shift_wh = peak_energy_wh * settings.shiftable_pct // 100
    shift_saving_cents = cost_cents(shift_wh, settings.peak_rate_cents) - cost_cents(
        shift_wh, settings.offpeak_rate_cents
    )

    # Opportunity 2: trim the standby/base-load draw. The base load runs every
    # hour, so the avoided energy is priced hour-by-hour at each hour's own rate.
    reduce_per_hour_wh = base_load_wh * settings.standby_reduction_pct // 100
    standby_peak_wh = reduce_per_hour_wh * n_peak_hours
    standby_offpeak_wh = reduce_per_hour_wh * n_offpeak_hours
    standby_energy_wh = standby_peak_wh + standby_offpeak_wh
    standby_saving_cents = cost_cents(
        standby_peak_wh, settings.peak_rate_cents
    ) + cost_cents(standby_offpeak_wh, settings.offpeak_rate_cents)

    opportunities = [
        Opportunity(
            key="load_shift",
            title="Shift peak-hour load to off-peak",
            energy_wh=shift_wh,
            saving_cents=shift_saving_cents,
            rationale=(
                f"moving {settings.shiftable_pct}% of peak-window energy to off-peak "
                f"saves the {settings.peak_rate_cents - settings.offpeak_rate_cents}c/kWh "
                "rate difference on the shifted energy"
            ),
        ),
        Opportunity(
            key="standby",
            title="Cut always-on standby (base load)",
            energy_wh=standby_energy_wh,
            saving_cents=standby_saving_cents,
            rationale=(
                f"trimming {settings.standby_reduction_pct}% of the always-on base load "
                "removes draw from every hour, priced at each hour's own rate"
            ),
        ),
    ]
    total_saving_cents = sum(o.saving_cents for o in opportunities)
    projected_monthly_saving_cents = (
        int(total_saving_cents / days) * 30 if days else total_saving_cents
    )

    return Analysis(
        hours=hours,
        days=int(days) if float(days).is_integer() else round(days, 2),
        total_wh=total_wh,
        average_wh=average_wh,
        peak_wh=peak_wh,
        base_load_wh=base_load_wh,
        load_factor=load_factor,
        peak_usage_hours=peak_usage_hours,
        peak_usage_avg_wh=peak_usage_avg_wh,
        usage_peak_in_tariff_window=usage_peak_in_tariff_window,
        peak_window=(settings.peak_start_hour, settings.peak_end_hour),
        peak_rate_cents=settings.peak_rate_cents,
        offpeak_rate_cents=settings.offpeak_rate_cents,
        n_peak_hours=n_peak_hours,
        n_offpeak_hours=n_offpeak_hours,
        peak_energy_wh=peak_energy_wh,
        offpeak_energy_wh=offpeak_energy_wh,
        peak_cost_cents=peak_cost_cents,
        offpeak_cost_cents=offpeak_cost_cents,
        total_cost_cents=total_cost_cents,
        avg_daily_cost_cents=avg_daily_cost_cents,
        projected_monthly_cost_cents=projected_monthly_cost_cents,
        opportunities=opportunities,
        total_saving_cents=total_saving_cents,
        projected_monthly_saving_cents=projected_monthly_saving_cents,
    )
