"""Runtime configuration, loaded from environment variables with the ``EP_`` prefix.

The tariff and the savings assumptions are configuration, not code: an operator
can retune the peak window, the peak/off-peak rates, and how aggressively the
advisor assumes load can be shifted or standby cut, without touching the engine.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EP_", env_file=".env", extra="ignore")

    environment: str = "local"

    # Time-of-use tariff. Hours in ``[peak_start_hour, peak_end_hour)`` are billed
    # at the peak rate; every other hour is off-peak. Rates are integer cents per
    # kWh, so all cost arithmetic stays in integer cents (no floats for money).
    peak_start_hour: int = 17
    peak_end_hour: int = 21
    peak_rate_cents: int = 30
    offpeak_rate_cents: int = 12

    # Overnight window ``[overnight_start_hour, overnight_end_hour)`` used to read
    # off the base load (the always-on floor the home never drops below at night).
    overnight_start_hour: int = 0
    overnight_end_hour: int = 6

    # Savings assumptions, as whole percentages so the money math is exact.
    # ``shiftable_pct`` of the energy consumed during peak hours is assumed to be
    # deferrable to off-peak; ``standby_reduction_pct`` of the base load is assumed
    # to be avoidable standby/vampire draw.
    shiftable_pct: int = 30
    standby_reduction_pct: int = 25

    # How many hours-of-day to report as the usage peak.
    top_usage_hours: int = 3

    # LLM provider cascade, tried in order. Each reads its own key from the env.
    # With no key set the advisor uses the deterministic template and makes no
    # network calls; with a key, the LLM phrases the same computed advice.
    llm_spec: str = "anthropic,openai,gemini,deepseek,ollama"
    llm_max_tokens: int = 500


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
