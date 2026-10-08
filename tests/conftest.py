from __future__ import annotations

import pytest

from energpt.config import Settings


@pytest.fixture
def settings() -> Settings:
    # Explicit defaults, independent of any .env or environment variables.
    return Settings(
        peak_start_hour=17,
        peak_end_hour=21,
        peak_rate_cents=30,
        offpeak_rate_cents=12,
        overnight_start_hour=0,
        overnight_end_hour=6,
        shiftable_pct=30,
        standby_reduction_pct=25,
        top_usage_hours=3,
    )


@pytest.fixture
def probe_series() -> list[int]:
    """A hand-built 2-day series with an obvious evening peak.

    Each day: hours 17-20 (the peak tariff window) draw 1000 Wh; every other
    hour draws 100 Wh. The numbers are chosen so the analysis can be recomputed
    by hand (see test_analysis).
    """
    series: list[int] = []
    for _day in range(2):
        for hour in range(24):
            series.append(1000 if 17 <= hour <= 20 else 100)
    return series
