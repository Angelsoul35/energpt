"""Run the EnerGPT engine on real London smart-meter homes.

EnerGPT's analysis is **deterministic** — tariff arithmetic and load-shift maths, not
a trained model — so there is nothing to over/underfit and no accuracy to report. The
real-data question for a deterministic engine is different: *does it produce correct,
sensible advisories on real consumption, not just on the synthetic generator?* This
module answers that by running :func:`energpt.analysis.analyse` and the offline
:class:`energpt.advisor.Advisor` over every real home in ``datasets/london_real.npz``
(a 10-home, 14-day slice of the Low Carbon London trial) and summarising the results:
total energy, projected monthly cost and saving, and where each home's usage peaks.

Run it with ``python -m energpt.real_benchmark``.
"""

from __future__ import annotations

import statistics
from collections import Counter
from dataclasses import dataclass

from .advisor import Advisor
from .analysis import Analysis, analyse
from .config import Settings
from .real_data import load_london


@dataclass
class HomeResult:
    home_id: str
    total_kwh: float
    projected_monthly_cost_cents: int
    projected_monthly_saving_cents: int
    peak_usage_hours: list[int]
    peak_in_window: int


@dataclass
class RealBenchmarkReport:
    n_homes: int
    results: list[HomeResult]
    mean_total_kwh: float
    mean_monthly_cost_cents: float
    mean_monthly_saving_cents: float
    median_saving_fraction: float  # saving / cost, across homes
    peak_hour_distribution: dict[int, int]  # hour-of-day -> how many homes peak there
    sample_home_id: str
    sample_headline: str
    sample_advisory: str


def analyse_home(series: list[int], settings: Settings | None = None) -> Analysis:
    """Analyse one real home's hourly watt-hour series."""
    return analyse(series, settings or Settings())


def run_benchmark(
    homes: list[tuple[str, list[int]]] | None = None,
    settings: Settings | None = None,
) -> RealBenchmarkReport:
    """Run the engine + offline advisor over the real homes and summarise."""
    settings = settings or Settings()
    homes = homes if homes is not None else load_london()
    advisor = Advisor(llm=None)  # offline deterministic template, no network

    results: list[HomeResult] = []
    peak_hours: Counter[int] = Counter()
    saving_fractions: list[float] = []
    for home_id, series in homes:
        a = analyse_home(series, settings)
        results.append(
            HomeResult(
                home_id=home_id,
                total_kwh=a.total_kwh,
                projected_monthly_cost_cents=a.projected_monthly_cost_cents,
                projected_monthly_saving_cents=a.projected_monthly_saving_cents,
                peak_usage_hours=a.peak_usage_hours,
                peak_in_window=a.usage_peak_in_tariff_window,
            )
        )
        for h in a.peak_usage_hours:
            peak_hours[h] += 1
        if a.total_cost_cents > 0:
            saving_fractions.append(a.total_saving_cents / a.total_cost_cents)

    # Render one real advisory in full (the first home), via the offline template.
    sample_id, sample_series = homes[0]
    sample_advisory = advisor.advise(analyse_home(sample_series, settings))

    return RealBenchmarkReport(
        n_homes=len(homes),
        results=results,
        mean_total_kwh=statistics.mean(r.total_kwh for r in results),
        mean_monthly_cost_cents=statistics.mean(
            r.projected_monthly_cost_cents for r in results
        ),
        mean_monthly_saving_cents=statistics.mean(
            r.projected_monthly_saving_cents for r in results
        ),
        median_saving_fraction=statistics.median(saving_fractions),
        peak_hour_distribution=dict(sorted(peak_hours.items())),
        sample_home_id=sample_id,
        sample_headline=sample_advisory.headline,
        sample_advisory=sample_advisory.text,
    )


def format_report(report: RealBenchmarkReport) -> str:
    lines = [
        "EnerGPT real-data report — Low Carbon London smart meters",
        "=" * 58,
        f"homes analysed        : {report.n_homes} (14 days of hourly readings each)",
        f"mean energy / home    : {report.mean_total_kwh:.1f} kWh over the period",
        f"mean projected cost   : ${report.mean_monthly_cost_cents / 100:.2f} / month",
        f"mean projected saving : ${report.mean_monthly_saving_cents / 100:.2f} / month",
        f"median saving / cost  : {report.median_saving_fraction:.1%} of the bill",
        "",
        "when each home's usage peaks (hour-of-day -> homes):",
    ]
    for hour, count in report.peak_hour_distribution.items():
        lines.append(f"  {hour:02d}:00  {'#' * count} ({count})")
    lines += [
        "",
        f"sample advisory for home {report.sample_home_id} (offline template):",
        f"  {report.sample_headline}",
    ]
    lines += [f"  {ln}" for ln in report.sample_advisory.splitlines()]
    return "\n".join(lines)


def main() -> None:
    print(format_report(run_benchmark()))


if __name__ == "__main__":
    main()
