from __future__ import annotations

import re

from energpt.advisor import Advisor, build_facts
from energpt.analysis import analyse
from energpt.generate import build_sample
from energpt.llm.fake import FailingLLM, FakeLLM

# Substantive figures that must be grounded: money, energy, and percentages.
_MONEY = re.compile(r"\$\d[\d,]*\.\d{2}")
_KWH = re.compile(r"\d+(?:\.\d+)?\s*kWh")
_PCT = re.compile(r"\d+%")


def _figures(text: str) -> set[str]:
    return set(_MONEY.findall(text)) | set(_KWH.findall(text)) | set(_PCT.findall(text))


def _analysis(settings):
    return analyse(build_sample("home", days=14), settings)


def test_llm_path_phrases_and_is_marked_llm(settings):
    advisor = Advisor(llm=FakeLLM("Your evening peak is the costly part; defer the wash."))
    advisory = advisor.advise(_analysis(settings))
    assert advisory.source == "llm"
    assert "evening peak" in advisory.text


def test_failing_llm_falls_back_to_template(settings):
    analysis = _analysis(settings)
    advisory = Advisor(llm=FailingLLM()).advise(analysis)
    assert advisory.source == "template"
    # The template carries the computed total saving verbatim.
    expected = f"${analysis.total_saving_cents / 100:,.2f}"
    assert expected in advisory.text


def test_empty_llm_text_falls_back(settings):
    advisory = Advisor(llm=FakeLLM("   ")).advise(_analysis(settings))
    assert advisory.source == "template"


def test_no_llm_uses_template(settings):
    advisory = Advisor(llm=None).advise(_analysis(settings))
    assert advisory.source == "template"


def test_template_invents_no_numbers(settings):
    """Every money/energy/percentage figure in the advisory must come from the
    computed facts; the template may not introduce a number of its own."""
    analysis = _analysis(settings)
    facts = build_facts(analysis)
    advisory = Advisor(llm=FailingLLM()).advise(analysis)
    allowed = _figures(" ".join(facts.values()))
    produced = _figures(advisory.headline + "\n" + advisory.text)
    assert produced  # the advisory does contain figures
    unexpected = produced - allowed
    assert not unexpected, f"advisory invented figures not in the analysis: {unexpected}"


def test_facts_cover_every_opportunity(settings):
    analysis = _analysis(settings)
    facts = build_facts(analysis)
    for opp in analysis.opportunities:
        assert f"opp_{opp.key}_saving" in facts
        assert f"opp_{opp.key}_energy" in facts
