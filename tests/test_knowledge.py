from __future__ import annotations

from energpt.knowledge import TipBase


def test_retrieves_standby_tip_for_standby_question():
    tips = TipBase().retrieve("how do I cut standby or vampire power?", k=3)
    assert tips[0].topic == "standby_power"
    assert "standby" in tips[0].answer.lower()


def test_retrieves_load_shifting_tip():
    tips = TipBase().retrieve("when should I run the washing machine to pay less?", k=3)
    assert "load_shifting" in [t.topic for t in tips]


def test_scores_are_sorted_descending():
    tips = TipBase().retrieve("how do I save on heating in winter?", k=3)
    scores = [t.score for t in tips]
    assert scores == sorted(scores, reverse=True)
    assert tips[0].topic == "heating"
