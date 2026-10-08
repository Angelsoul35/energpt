"""Turn a computed :class:`~energpt.analysis.Analysis` into a readable advisory.

The split that keeps this honest:

* **The substance is computed, not written.** Every figure — the current cost,
  the peak/off-peak split, the base load, each saving — comes from
  :mod:`energpt.analysis`. This module never calculates anything new.
* **The LLM only phrases.** When a provider is configured, the LLM is handed the
  computed figures and asked to render them as prose, grounded strictly in those
  numbers. When no provider is available (the default, offline), a deterministic
  template renders the *same* figures into the *same* substantive advice.

Either way the result records which path produced it (``source`` is ``"llm"`` or
``"template"``), and the structured analysis is always returned alongside, so a
reader can check the prose against the numbers.
"""

from __future__ import annotations

from dataclasses import dataclass

from .analysis import Analysis
from .llm.base import LLMClient, LLMError

_SYSTEM = (
    "You are an energy-efficiency advisor. Write a short, plain advisory for a "
    "household, using ONLY the figures provided. Do not invent, estimate, or add "
    "any number that is not in the figures. Do not give safety or electrical-wiring "
    "advice. Keep it to a few short sentences grouped as: the current bill, the "
    "consumption profile, and the savings opportunities."
)


def _money(cents: int) -> str:
    return f"${cents / 100:,.2f}"


def _kwh(wh: int) -> str:
    return f"{wh / 1000:.2f} kWh"


def _hour(h: int) -> str:
    return f"{h:02d}:00"


def _hours(hours: list[int]) -> str:
    return ", ".join(_hour(h) for h in hours)


def build_facts(analysis: Analysis) -> dict[str, str]:
    """The exact, formatted figures the advisory is allowed to use.

    Both the template and the LLM prompt are built only from this dict, so no
    number can enter the advisory that was not computed by the analysis.
    """
    a = analysis
    start, end = a.peak_window
    facts = {
        "period": f"{a.days} days ({a.hours} hourly readings)",
        "total_energy": _kwh(a.total_wh),
        "current_cost": _money(a.total_cost_cents),
        "peak_window": f"{_hour(start)}-{_hour(end)}",
        "peak_rate": f"{a.peak_rate_cents}c/kWh",
        "offpeak_rate": f"{a.offpeak_rate_cents}c/kWh",
        "peak_energy": _kwh(a.peak_energy_wh),
        "offpeak_energy": _kwh(a.offpeak_energy_wh),
        "peak_cost": _money(a.peak_cost_cents),
        "offpeak_cost": _money(a.offpeak_cost_cents),
        "avg_daily_cost": _money(a.avg_daily_cost_cents),
        "projected_monthly_cost": _money(a.projected_monthly_cost_cents),
        "base_load": f"{a.base_load_wh} W",
        "load_factor": f"{a.load_factor}",
        "peak_usage_hours": _hours(a.peak_usage_hours),
        "peak_usage_level": f"{a.peak_usage_avg_wh} W",
        "usage_in_window": (
            f"{a.usage_peak_in_tariff_window} of {len(a.peak_usage_hours)}"
        ),
        "total_saving": _money(a.total_saving_cents),
        "projected_monthly_saving": _money(a.projected_monthly_saving_cents),
    }
    for opp in a.opportunities:
        facts[f"opp_{opp.key}_saving"] = _money(opp.saving_cents)
        facts[f"opp_{opp.key}_energy"] = _kwh(opp.energy_wh)
        facts[f"opp_{opp.key}_title"] = opp.title
        facts[f"opp_{opp.key}_rationale"] = opp.rationale
    return facts


@dataclass
class Advisory:
    headline: str
    text: str
    source: str  # "llm" | "template"


def _render_template(analysis: Analysis, facts: dict[str, str]) -> str:
    """Render the advisory deterministically from the facts (the offline path)."""
    a = analysis
    overlap = (
        "and they fall inside the expensive peak window"
        if a.usage_peak_in_tariff_window
        else "but they fall outside the peak window"
    )
    lines = [
        f"Over {facts['period']} this home used {facts['total_energy']}, "
        f"costing {facts['current_cost']} on a {facts['peak_rate']} peak / "
        f"{facts['offpeak_rate']} off-peak tariff. Of that, {facts['peak_cost']} "
        f"was run in the {facts['peak_window']} peak window "
        f"({facts['peak_energy']}) and {facts['offpeak_cost']} off-peak "
        f"({facts['offpeak_energy']}). That averages {facts['avg_daily_cost']} a "
        f"day, or about {facts['projected_monthly_cost']} a month.",
        f"The always-on base load sits at {facts['base_load']} and the load "
        f"factor is {facts['load_factor']} (1.0 would be perfectly flat). Usage "
        f"peaks at {facts['peak_usage_hours']} (up to {facts['peak_usage_level']}), "
        f"{overlap} ({facts['usage_in_window']} peak hours).",
        "Opportunities:",
    ]
    for opp in a.opportunities:
        lines.append(
            f"  - {facts[f'opp_{opp.key}_title']}: save "
            f"{facts[f'opp_{opp.key}_saving']} over the period "
            f"({facts[f'opp_{opp.key}_energy']}) - "
            f"{facts[f'opp_{opp.key}_rationale']}."
        )
    lines.append(
        f"Taken together these could save {facts['total_saving']} over the period, "
        f"roughly {facts['projected_monthly_saving']} a month, without cutting the "
        "total energy used (the load-shift opportunity just moves it to cheaper hours)."
    )
    return "\n".join(lines)


def _build_prompt(facts: dict[str, str]) -> str:
    lines = ["Figures (use only these):"]
    lines += [f"- {k}: {v}" for k, v in facts.items()]
    lines.append("\nWrite the advisory.")
    return "\n".join(lines)


class Advisor:
    def __init__(self, llm: LLMClient | None = None, max_tokens: int = 500) -> None:
        self.llm = llm
        self.max_tokens = max_tokens

    def advise(self, analysis: Analysis) -> Advisory:
        facts = build_facts(analysis)
        headline = (
            f"You could save about {facts['total_saving']} over "
            f"{facts['period']} ({facts['projected_monthly_saving']}/month projected)."
        )
        if self.llm is not None:
            try:
                result = self.llm.complete(
                    _SYSTEM, _build_prompt(facts), max_tokens=self.max_tokens
                )
                text = result.text.strip()
                if text:
                    return Advisory(headline=headline, text=text, source="llm")
            except LLMError:
                pass  # fall through to the deterministic template
        return Advisory(
            headline=headline,
            text=_render_template(analysis, facts),
            source="template",
        )
