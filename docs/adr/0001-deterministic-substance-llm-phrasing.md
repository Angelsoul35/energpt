# ADR 0001 — Compute the substance deterministically; the LLM only phrases it

## Status
Accepted.

## Context
The obvious way to build an "AI energy advisor" is to give the consumption data
to a language model and ask it for savings advice. The model then produces the
numbers too — "you could save about 15%" — and those numbers are untethered to
the data, not reproducible, and impossible to audit. That is the exact failure
mode that makes such tools untrustworthy.

## Decision
Split the system in two:

- **The analysis engine computes every figure.** Peak-usage hours, base load,
  load factor, the cost split under the tariff, and each quantified saving are
  computed in `analysis.py`, deterministically, from the series.
- **The advisor only phrases those figures.** It builds a fixed dict of formatted
  *facts* from the analysis and renders only those. When an LLM provider is
  configured it is handed the facts and instructed to ground strictly in them and
  invent nothing; offline, a template renders the same facts. The structured
  analysis is always returned alongside the prose.

The LLM is never asked a quantitative question. It receives the answer and writes
it up.

## Consequences
- **Reproducible and auditable.** The advice is a deterministic function of the
  series and the settings; the by-hand probe in the tests recomputes it to the
  cent.
- **Offline and online agree on substance.** The template and the LLM phrase the
  *same* figures, so the advice does not change with the provider — only the
  wording does, and `source` records which ran.
- **No invented numbers.** A test asserts every money/energy/percentage figure in
  the template's output was computed by the analysis. The LLM path carries the
  same instruction and the checkable analysis beside it.
- **Trade-off.** The advice is only as rich as what the engine computes; the LLM
  cannot add a genuinely new insight. For a tool whose value is trust, that is the
  right bound — new insight belongs in the engine, where it can be tested.
