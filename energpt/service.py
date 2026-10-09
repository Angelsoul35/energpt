"""Application service: analyse a series, phrase an advisory, answer tip questions.

The pipeline is: a consumption series (supplied directly or chosen by sample id)
-> the deterministic analysis -> the advisor (LLM phrasing, or the offline
template) -> a structured result. An optional free-text question is answered from
the tip knowledge base.
"""

from __future__ import annotations

import os

from .advisor import Advisor, Advisory
from .analysis import Analysis, Opportunity, analyse
from .config import Settings, get_settings
from .generate import build_sample, sample_names
from .knowledge import TipBase
from .llm.base import LLMClient
from .llm.factory import build_llm

# Provider keys that, if present, mean a real LLM can be reached. With none set
# the advisor stays fully offline (deterministic template, no network calls).
_PROVIDER_KEYS = (
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "DEEPSEEK_API_KEY",
)


def default_llm(settings: Settings) -> LLMClient | None:
    """Build the provider cascade only if a provider key is in the environment.

    Returning ``None`` is the safe default: no key means the advisor uses the
    deterministic template and makes no network calls. When a key is present the
    cascade is built; it still falls back provider-to-provider, and the advisor
    falls back to the template if every provider fails.
    """
    if any(os.getenv(k) for k in _PROVIDER_KEYS):
        return build_llm(settings.llm_spec)
    return None


class EnerGPTService:
    def __init__(
        self,
        settings: Settings | None = None,
        llm: LLMClient | None = None,
        tips: TipBase | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.llm = llm if llm is not None else default_llm(self.settings)
        self.advisor = Advisor(llm=self.llm, max_tokens=self.settings.llm_max_tokens)
        self.tips = tips or TipBase()

    # --- building blocks -------------------------------------------------

    def analyse(self, series: list[int]) -> Analysis:
        return analyse(series, self.settings)

    def advise(self, analysis: Analysis) -> Advisory:
        return self.advisor.advise(analysis)

    def answer_question(self, question: str) -> dict:
        found = self.tips.retrieve(question, k=3)
        best = found[0]
        return {
            "question": question,
            "answer": best.answer,
            "topic": best.topic,
            "score": best.score,
            "citations": [t.topic for t in found],
        }

    # --- end-to-end ------------------------------------------------------

    def run(
        self,
        series: list[int] | None = None,
        sample: str | None = None,
        question: str | None = None,
        days: int = 14,
    ) -> dict:
        """Analyse a series (or a named sample) and phrase an advisory.

        Exactly one of ``series`` or ``sample`` should be given; if neither is,
        the default ``home`` sample is used.
        """
        if series is None:
            series = build_sample(sample or "home", days=days)
        analysis = self.analyse(series)
        advisory = self.advise(analysis)
        result = {
            "analysis": _analysis_to_dict(analysis),
            "advisory": {
                "headline": advisory.headline,
                "text": advisory.text,
                "source": advisory.source,
            },
        }
        if question:
            result["tip"] = self.answer_question(question)
        return result

    def samples(self) -> list[str]:
        return sample_names()


def _opportunity_to_dict(opp: Opportunity) -> dict:
    return {
        "key": opp.key,
        "title": opp.title,
        "energy_kwh": round(opp.energy_wh / 1000, 3),
        "saving_cents": opp.saving_cents,
        "rationale": opp.rationale,
    }


def _analysis_to_dict(a: Analysis) -> dict:
    return {
        "period_days": a.days,
        "hours": a.hours,
        "total_kwh": a.total_kwh,
        "average_wh": a.average_wh,
        "peak_wh": a.peak_wh,
        "base_load_wh": a.base_load_wh,
        "load_factor": a.load_factor,
        "peak_usage_hours": a.peak_usage_hours,
        "usage_peak_in_tariff_window": a.usage_peak_in_tariff_window,
        "tariff": {
            "peak_window": list(a.peak_window),
            "peak_rate_cents": a.peak_rate_cents,
            "offpeak_rate_cents": a.offpeak_rate_cents,
            "peak_energy_kwh": round(a.peak_energy_wh / 1000, 3),
            "offpeak_energy_kwh": round(a.offpeak_energy_wh / 1000, 3),
            "peak_cost_cents": a.peak_cost_cents,
            "offpeak_cost_cents": a.offpeak_cost_cents,
            "total_cost_cents": a.total_cost_cents,
            "avg_daily_cost_cents": a.avg_daily_cost_cents,
            "projected_monthly_cost_cents": a.projected_monthly_cost_cents,
        },
        "opportunities": [_opportunity_to_dict(o) for o in a.opportunities],
        "total_saving_cents": a.total_saving_cents,
        "projected_monthly_saving_cents": a.projected_monthly_saving_cents,
    }
