from __future__ import annotations

import pytest

from energpt import cli


def test_demo_runs(capsys):
    cli.demo()
    out = capsys.readouterr().out
    assert "EnerGPT demo" in out
    assert "Deterministic analysis" in out
    assert "savings opportunities" in out.lower()
    # The advisory is produced offline by the template.
    assert "source: template" in out
    # The tip knowledge base answers a free-text question.
    assert "cited tip:" in out


def test_ask_prints_a_tip(capsys):
    cli.ask("how do I reduce heat loss from draughts?")
    out = capsys.readouterr().out
    assert "insulation" in out


def test_main_requires_a_command():
    with pytest.raises(SystemExit):
        cli.main()
