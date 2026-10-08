# ADR 0004 — Provider-agnostic LLM with an offline deterministic fallback

## Status
Accepted.

## Context
The phrasing step needs a language model, but binding to one vendor's SDK makes
the project fragile: it cannot run in CI or a demo without a key, it breaks when a
provider has an outage, and it cannot be moved to a cheaper or local model without
a rewrite. At the same time, the tool's value — grounded, reproducible advice —
must not depend on a model being reachable at all.

## Decision
Depend on a provider-agnostic `LLMClient` interface with a **fallback cascade**
over Anthropic, OpenAI, Gemini, DeepSeek and Ollama (each a thin HTTP adapter
reading its own key from the environment). The advisor tries the cascade and,
on failure, renders the deterministic template.

The default is fully offline: the service builds **no** LLM client unless a
provider key is present in the environment, so with no key the advisor renders
the template and makes no network calls — not even a localhost probe. A provider
key switches the LLM on; the cascade still skips providers that fail and the
advisor still falls back to the template if all of them do.

## Consequences
- **Always available.** The pipeline runs end to end with no keys and no network,
  which is how CI, the tests and the demo run.
- **Same substance either way.** The template and the LLM phrase the *same*
  computed figures, so falling back changes only the wording, and `source`
  (`"llm"` / `"template"`) makes which path ran visible.
- **Provider freedom.** Reordering `EP_LLM_SPEC` or adding an adapter switches or
  extends providers without touching the advisor or the engine.
- **Trade-off.** The HTTP adapters are plain and uniform rather than feature-rich
  per vendor (no streaming, no tool use); the phrasing task does not need those,
  and the uniformity is what keeps the cascade simple.
