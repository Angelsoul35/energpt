from __future__ import annotations

import pytest

from energpt.analysis import analyse, cost_cents
from energpt.config import Settings


def test_cost_cents_rounds_half_up():
    # 1 kWh at 32 c/kWh is exactly 32 cents.
    assert cost_cents(1000, 32) == 32
    # 1.5 kWh at 32 c/kWh = 48.0 cents.
    assert cost_cents(1500, 32) == 48
    # 0.5 cent rounds up; just under rounds down.
    assert cost_cents(500, 1) == 1  # 500 Wh * 1 c/kWh = 0.5 c -> 1
    assert cost_cents(499, 1) == 0


def test_hand_probe_exact_arithmetic(probe_series, settings):
    """Recompute every headline number by hand and assert the engine matches.

    Series: 2 days; hours 17-20 = 1000 Wh, all other hours = 100 Wh.
      peak hours per day = 4 (17,18,19,20); off-peak hours = 20.
      peak energy  = 2 days * 4 h * 1000 Wh = 8000 Wh
      off-peak e.  = 2 days * 20 h * 100 Wh = 4000 Wh ; total = 12000 Wh
      peak cost    = round(8000 * 30 / 1000) = 240 c
      off-peak cost= round(4000 * 12 / 1000) = 48 c ; total = 288 c
      base load    = 100 Wh (overnight min) ; peak reading = 1000 Wh
      average      = 12000 / 48 = 250 Wh ; load factor = 250/1000 = 0.25
      shift 30% of peak energy = 2400 Wh ; saving = 72 - 29 = 43 c
      standby 25% of 100 Wh base = 25 Wh/h ; peak 25*8=200, off-peak 25*40=1000
      standby saving = round(200*30/1000) + round(1000*12/1000) = 6 + 12 = 18 c
      total saving = 43 + 18 = 61 c
    """
    a = analyse(probe_series, settings)

    assert a.hours == 48
    assert a.days == 2
    assert a.total_wh == 12000
    assert a.average_wh == 250
    assert a.peak_wh == 1000
    assert a.base_load_wh == 100
    assert a.load_factor == 0.25

    # Peak-usage hours: the four evening hours tie; top 3 by earliest hour.
    assert a.peak_usage_hours == [17, 18, 19]
    assert a.peak_usage_avg_wh == 1000
    assert a.usage_peak_in_tariff_window == 3

    # Tariff split and cost.
    assert a.n_peak_hours == 8
    assert a.n_offpeak_hours == 40
    assert a.peak_energy_wh == 8000
    assert a.offpeak_energy_wh == 4000
    assert a.peak_cost_cents == 240
    assert a.offpeak_cost_cents == 48
    assert a.total_cost_cents == 288
    assert a.avg_daily_cost_cents == 144
    assert a.projected_monthly_cost_cents == 4320

    # Opportunities.
    shift = next(o for o in a.opportunities if o.key == "load_shift")
    standby = next(o for o in a.opportunities if o.key == "standby")
    assert shift.energy_wh == 2400
    assert shift.saving_cents == 43
    assert standby.energy_wh == 1200
    assert standby.saving_cents == 18
    assert a.total_saving_cents == 61
    assert a.projected_monthly_saving_cents == 900


def test_peak_detection_picks_the_busiest_hours(settings):
    # A single spike at 19:00 every day must be the top usage hour.
    series = []
    for _day in range(3):
        for hour in range(24):
            series.append(900 if hour == 19 else 100)
    a = analyse(series, settings)
    assert a.peak_usage_hours[0] == 19
    assert a.peak_wh == 900


def test_window_can_wrap_midnight():
    # A peak window of 22:00-02:00 wraps midnight: hours 22,23,0,1 are peak.
    s = Settings(peak_start_hour=22, peak_end_hour=2, overnight_start_hour=3, overnight_end_hour=6)
    series = [10] * 24
    a = analyse(series, s)
    assert a.n_peak_hours == 4
    assert a.n_offpeak_hours == 20


def test_empty_series_rejected(settings):
    with pytest.raises(ValueError):
        analyse([], settings)


def test_negative_reading_rejected(settings):
    with pytest.raises(ValueError):
        analyse([100, -5, 100], settings)
