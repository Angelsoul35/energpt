"""Synthetic hourly electricity-consumption series for a home or small building.

A real smart meter emits one reading per hour (or per half hour). Here we
*synthesise* a plausible series so the analyser has something to work on without
needing a real meter feed. The shape is deliberately realistic:

* a constant **base load** (fridge, router, standby devices) that is always on;
* a **daily** pattern — a trough overnight, a morning bump, and a strong evening
  peak when people cook, heat and light the home;
* a **weekly** pattern — more daytime use at the weekend; and
* a little **noise**, so no two hours are identical.

Everything is deterministic given the seed: the same seed always yields the same
series, which is what makes the downstream analysis reproducible and testable.
Readings are integer **watt-hours** (Wh); money is handled later in integer cents.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Extra watt-hours above the base load, by hour of day (0-23), for a weekday.
# Index 0 is midnight. The evening (18:00-20:00) is the clear usage peak.
_HOURLY_SHAPE: list[int] = [
    20,
    10,
    5,
    5,
    5,
    10,  # 00-05  overnight trough
    60,
    180,
    320,
    220,
    160,
    150,  # 06-11  morning activity
    170,
    150,
    130,
    140,
    200,
    420,  # 12-17  afternoon rising into the evening
    620,
    680,
    520,
    300,
    140,
    60,  # 18-23  evening peak, then wind-down
]


@dataclass(frozen=True)
class SampleSpec:
    """The parameters of a named synthetic home/building."""

    name: str
    description: str
    base_wh: int  # always-on base load, watt-hours per hour
    peak_scale: float  # multiplier on the daily shape (bigger home -> higher peaks)
    weekend_daytime_wh: int  # extra daytime watt-hours at the weekend
    noise_wh: float  # standard deviation of the hourly noise
    seed: int


SAMPLES: dict[str, SampleSpec] = {
    "home": SampleSpec(
        name="home",
        description="A typical two-person household with an evening cooking-and-heating peak.",
        base_wh=160,
        peak_scale=1.0,
        weekend_daytime_wh=120,
        noise_wh=12.0,
        seed=7,
    ),
    "apartment": SampleSpec(
        name="apartment",
        description="A small flat: a lower base load and a gentler evening peak.",
        base_wh=90,
        peak_scale=0.6,
        weekend_daytime_wh=60,
        noise_wh=8.0,
        seed=19,
    ),
    "house": SampleSpec(
        name="house",
        description="A larger family house with electric heating and a pronounced evening peak.",
        base_wh=240,
        peak_scale=1.6,
        weekend_daytime_wh=220,
        noise_wh=18.0,
        seed=23,
    ),
}


def _is_weekend(day_index: int) -> bool:
    # Day 0 is a Monday; days 5 and 6 are Saturday and Sunday.
    return day_index % 7 in (5, 6)


def generate_series(spec: SampleSpec, days: int = 14) -> list[int]:
    """Return ``days * 24`` integer watt-hour readings, starting at midnight.

    The series is deterministic given ``spec.seed``. Each reading is the base
    load plus the hour-of-day shape (scaled), plus a weekend daytime bump, plus
    Gaussian noise, clamped to stay positive (consumption is never negative).
    """
    if days < 1:
        raise ValueError("days must be at least 1")
    rng = np.random.default_rng(spec.seed)
    series: list[int] = []
    for i in range(days * 24):
        hour = i % 24
        day = i // 24
        load = spec.base_wh + spec.peak_scale * _HOURLY_SHAPE[hour]
        if _is_weekend(day) and 9 <= hour <= 20:
            load += spec.weekend_daytime_wh
        load += rng.normal(0.0, spec.noise_wh)
        series.append(max(1, int(round(load))))
    return series


def build_sample(name: str = "home", days: int = 14) -> list[int]:
    """Build the named sample consumption series (see :data:`SAMPLES`)."""
    key = name.strip().lower()
    if key not in SAMPLES:
        raise ValueError(f"unknown sample {name!r} (known: {', '.join(SAMPLES)})")
    return generate_series(SAMPLES[key], days=days)


def sample_names() -> list[str]:
    return list(SAMPLES)
