"""EnerGPT command-line demo and entry point."""

from __future__ import annotations

import argparse

from .analysis import Analysis
from .generate import SAMPLES, build_sample
from .service import EnerGPTService

_BAR = "=" * 64


def _money(cents: int) -> str:
    return f"${cents / 100:,.2f}"


def _kwh(wh: int) -> str:
    return f"{wh / 1000:.2f} kWh"


def _hour(h: int) -> str:
    return f"{h:02d}:00"


def _print_analysis(a: Analysis) -> None:
    start, end = a.peak_window
    print("\n2) Deterministic analysis (computed, not written by any model):")
    print(f"   period            {a.days} days ({a.hours} hourly readings)")
    print(f"   total consumption {_kwh(a.total_wh)}")
    print(f"   average / peak    {a.average_wh} W / {a.peak_wh} W")
    print(f"   base load (night) {a.base_load_wh} W")
    print(f"   load factor       {a.load_factor}  (1.0 = perfectly flat)")
    print(
        f"   usage peaks at    {', '.join(_hour(h) for h in a.peak_usage_hours)} "
        f"(up to {a.peak_usage_avg_wh} W)"
    )
    print(
        f"   tariff            {_hour(start)}-{_hour(end)} peak "
        f"@ {a.peak_rate_cents}c/kWh, off-peak @ {a.offpeak_rate_cents}c/kWh"
    )
    print(
        f"   peak energy/cost  {_kwh(a.peak_energy_wh)}  ->  {_money(a.peak_cost_cents)}"
    )
    print(
        f"   off-peak e./cost  {_kwh(a.offpeak_energy_wh)}  ->  "
        f"{_money(a.offpeak_cost_cents)}"
    )
    print(
        f"   total bill        {_money(a.total_cost_cents)}  "
        f"({_money(a.avg_daily_cost_cents)}/day, "
        f"~{_money(a.projected_monthly_cost_cents)}/month)"
    )
    print("\n3) Quantified savings opportunities (exact arithmetic):")
    for opp in a.opportunities:
        print(
            f"   - {opp.title:<34} save {_money(opp.saving_cents)}  "
            f"({_kwh(opp.energy_wh)})"
        )
        print(f"     why: {opp.rationale}")
    print(
        f"   => total {_money(a.total_saving_cents)} over the period, "
        f"~{_money(a.projected_monthly_saving_cents)}/month"
    )


def demo() -> None:
    print("EnerGPT demo\n" + _BAR)
    print("\n1) Building a sample consumption series ...")
    series = build_sample("home", days=14)
    print(f"   sample 'home': {SAMPLES['home'].description}")
    print(f"   {len(series)} hourly readings in watt-hours")

    service = EnerGPTService()  # no API key -> offline template, no network
    analysis = service.analyse(series)
    _print_analysis(analysis)

    advisory = service.advise(analysis)
    print(f"\n4) Advisory (source: {advisory.source}):")
    print(f"   {advisory.headline}")
    for line in advisory.text.splitlines():
        print(f"   {line}")

    print("\n5) A free-text question, answered from the tip knowledge base:")
    result = service.answer_question("how do I cut standby power when I am away?")
    print(f'   Q: "{result["question"]}"')
    print(f"   A: {result['answer']}")
    print(f"   cited tip: [{result['topic']}]  (match score {result['score']})")

    print(
        "\nNote: offline, a deterministic template phrases the computed figures. "
        "Set a\nprovider API key and the LLM phrases the same numbers instead "
        "(source: llm)."
    )


def ask(question: str) -> None:
    result = EnerGPTService().answer_question(question)
    print(f'Q: "{result["question"]}"')
    print(f"A: {result['answer']}")
    print(f"cited tip: [{result['topic']}]  (match score {result['score']})")


def main() -> int:
    parser = argparse.ArgumentParser(description="EnerGPT CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("demo", help="analyse a sample home and print the advisory")
    ask_cmd = sub.add_parser("ask", help="answer one energy-efficiency question")
    ask_cmd.add_argument("question", help="the question text")
    args = parser.parse_args()
    if args.command == "demo":
        demo()
    elif args.command == "ask":
        ask(args.question)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
