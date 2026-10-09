"""Functional tests for the real London smart-meter benchmark.

EnerGPT's engine is deterministic, so these do not check an accuracy number; they
prove the engine runs correctly on *real* homes (every invariant holds on all 10
vendored London homes) and that the reported metrics genuinely respond to the input
(a home whose load sits in the peak tariff window is costed and advised differently
from one whose identical energy sits off-peak). A metric that ignored the data would
fail these.
"""

from __future__ import annotations

import numpy as np
import pytest

from energpt.config import Settings
from energpt.real_benchmark import analyse_home, format_report, run_benchmark
from energpt.real_data import load_london

SETTINGS = Settings()


@pytest.fixture(scope="module")
def homes():
    return load_london()


@pytest.fixture(scope="module")
def report(homes):
    return run_benchmark(homes)


def test_loads_ten_real_homes(homes):
    assert len(homes) == 10
    for home_id, series in homes:
        assert isinstance(home_id, str) and home_id
        assert len(series) == 336  # 14 days of hourly readings
        assert all(isinstance(x, int) and x >= 0 for x in series)
        assert sum(series) > 0  # a real home draws power


def test_engine_invariants_hold_on_every_real_home(homes):
    for home_id, series in homes:
        a = analyse_home(series, SETTINGS)
        assert a.total_wh == sum(series), home_id  # accounting identity
        assert a.total_kwh == pytest.approx(sum(series) / 1000)
        assert a.hours == 336
        assert a.peak_wh == max(series), home_id
        assert 0 < a.load_factor <= 1.0, home_id  # average/peak, bounded
        assert all(0 <= h <= 23 for h in a.peak_usage_hours), home_id
        assert 0 <= a.peak_window[0] < 24 and 0 < a.peak_window[1] <= 24
        # Costs and savings are non-negative and the saving never exceeds the bill.
        assert a.total_cost_cents >= 0 and a.total_saving_cents >= 0, home_id
        assert a.total_saving_cents <= a.total_cost_cents, home_id
        assert a.projected_monthly_saving_cents >= 0, home_id


def test_peak_window_placement_changes_cost_and_advice():
    """Identical energy costs more, and is advised to shift, when it sits in the peak
    window — proof the engine reads the hour-of-day structure, not just the totals."""
    peak_mid = (SETTINGS.peak_start_hour + SETTINGS.peak_end_hour) // 2
    offpeak_hour = (SETTINGS.peak_start_hour + 12) % 24  # far from the peak window

    def spike_at(hour: int) -> list[int]:
        # 14 days; 2000 Wh at the chosen hour each day, a small 50 Wh floor elsewhere.
        return [2000 if i % 24 == hour else 50 for i in range(336)]

    in_window = analyse_home(spike_at(peak_mid), SETTINGS)
    off_window = analyse_home(spike_at(offpeak_hour), SETTINGS)

    assert in_window.total_wh == off_window.total_wh  # same energy
    assert in_window.total_cost_cents > off_window.total_cost_cents  # but costs more
    assert in_window.usage_peak_in_tariff_window > 0
    assert off_window.usage_peak_in_tariff_window == 0
    shift = {o.key: o for o in in_window.opportunities}.get("load_shift")
    assert shift is not None and shift.saving_cents > 0  # advised to shift the peak
    # The off-peak home's only peak-window energy is the small floor, so its
    # load-shift saving is far smaller (the spike itself is nothing to shift).
    off_shift = {o.key: o for o in off_window.opportunities}.get("load_shift")
    off_saving = off_shift.saving_cents if off_shift is not None else 0
    assert shift.saving_cents > 3 * max(off_saving, 1)


def test_flat_load_has_high_load_factor_but_a_spiky_one_is_low():
    flat = analyse_home([500] * 336, SETTINGS)
    spiky = analyse_home([50 if i % 24 else 5000 for i in range(336)], SETTINGS)
    assert flat.load_factor > 0.95  # average ~= peak
    assert spiky.load_factor < 0.3  # one tall spike drags the average down
    assert flat.peak_wh == 500 and spiky.peak_wh == 5000


def test_report_summarises_all_homes_with_a_real_advisory(report):
    assert report.n_homes == 10
    assert len(report.results) == 10
    assert report.mean_total_kwh > 0
    assert report.mean_monthly_cost_cents > 0
    assert report.mean_monthly_saving_cents > 0
    assert 0 < report.median_saving_fraction < 1
    # Residential usage peaks in the evening: the modal peak hour is in 17:00-22:00.
    modal_hour = max(report.peak_hour_distribution, key=report.peak_hour_distribution.get)
    assert 17 <= modal_hour <= 22, report.peak_hour_distribution
    # The sample advisory is the real offline template, with real figures in it.
    assert report.sample_home_id == report.results[0].home_id
    assert "save" in report.sample_headline.lower()
    assert "kWh" in report.sample_advisory and "peak window" in report.sample_advisory


def test_format_report_renders_the_homes_and_sample(report):
    text = format_report(report)
    assert "Low Carbon London" in text
    assert f"{report.n_homes}" in text
    assert "sample advisory" in text
    assert report.sample_home_id in text


def test_run_benchmark_defaults_to_the_vendored_homes():
    # No argument -> loads datasets/london_real.npz itself.
    report = run_benchmark()
    assert report.n_homes == 10


def test_main_prints_the_report(capsys):
    from energpt.real_benchmark import main

    main()
    assert "real-data report" in capsys.readouterr().out


def test_loader_rejects_a_missing_dataset(monkeypatch, tmp_path):
    import energpt.real_data as rd

    monkeypatch.setattr(rd, "_DATASET_PATH", tmp_path / "missing.npz")
    with pytest.raises(FileNotFoundError):
        rd.load_london()


def test_fetch_aggregates_and_rejects_bad_rows(tmp_path, monkeypatch):
    import json

    # A page with three rows: an all-zero home (no draw), a home with a negative
    # reading (corrupt), and one good home. Only the good one should be written.
    page = {
        "rows": [
            {"row": {"target": [0.0] * 48, "item_id": "ZERO"}},
            {"row": {"target": [-1.0] + [0.1] * 47, "item_id": "BAD"}},
            {"row": {"target": [0.1] * 48, "item_id": "MAC000001"}},
        ]
    }

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps(page).encode()

    monkeypatch.setattr("urllib.request.urlopen", lambda url, timeout=0: _Resp())
    from energpt.real_data import fetch_london

    dest = tmp_path / "london.npz"
    n = fetch_london(n_homes=1, days=1, dest=dest)
    assert n == 1  # the zero and negative rows were filtered out
    data = np.load(dest, allow_pickle=True)
    hourly = data["readings"][0]
    assert len(hourly) == 24
    # Two 0.1 kWh half-hours -> 0.2 kWh -> 200 Wh each hour.
    assert all(x == 200 for x in hourly)
    assert str(data["item_ids"][0]) == "MAC000001"
