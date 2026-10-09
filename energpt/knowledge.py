"""A small energy-efficiency tip knowledge base with TF-IDF retrieval.

A free-text question ("how do I cut standby power?") is answered by retrieving
the closest tip, not by generating one. It is a classic TF-IDF + cosine
similarity search: simple, explainable, offline, with no model to train or host.
Grounding the answer in a fixed tip is what keeps it verifiable — the reply is a
curated tip, with its topic cited, never a fabricated claim.
"""

from __future__ import annotations

from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# A small, general energy-efficiency tip base. The advice is generic and does not
# depend on any particular meter reading.
TIPS: list[dict] = [
    {
        "topic": "standby_power",
        "question": "How do I cut standby or vampire power?",
        "answer": (
            "Switch off devices at the wall or use a standby-saver power strip; "
            "chargers, set-top boxes and idle screens draw power around the clock."
        ),
    },
    {
        "topic": "load_shifting",
        "question": "How do I shift usage to cheaper off-peak hours?",
        "answer": (
            "Run the dishwasher, washing machine and any heavy load on a timer "
            "outside the peak window to pay the lower off-peak rate for the same work."
        ),
    },
    {
        "topic": "heating",
        "question": "How do I save on heating?",
        "answer": (
            "Lower the thermostat by one degree and heat only occupied rooms on a "
            "schedule; heating is usually the largest slice of a winter bill."
        ),
    },
    {
        "topic": "lighting",
        "question": "How do I save on lighting?",
        "answer": (
            "Replace remaining halogen and incandescent bulbs with LEDs, which use "
            "roughly a fifth of the power for the same light."
        ),
    },
    {
        "topic": "water_heating",
        "question": "How do I cut water-heating costs?",
        "answer": (
            "Set the hot-water cylinder to about 60C, insulate the tank and pipes, "
            "and heat water on a timer rather than keeping it hot all day."
        ),
    },
    {
        "topic": "appliances",
        "question": "How do I pick efficient appliances?",
        "answer": (
            "Choose the highest energy-label class you can and run full loads; an "
            "efficient fridge or washer pays back its premium over its lifetime."
        ),
    },
    {
        "topic": "insulation",
        "question": "How do I reduce heat loss from draughts?",
        "answer": (
            "Draught-proof doors and windows and insulate the loft; sealing leaks "
            "keeps heat in and lets the heating run less."
        ),
    },
    {
        "topic": "peak_demand",
        "question": "How do I lower my peak demand charges?",
        "answer": (
            "Avoid running several high-power appliances at once during the peak "
            "window; staggering them flattens the demand spike that drives cost."
        ),
    },
]


@dataclass(frozen=True)
class Tip:
    topic: str
    question: str
    answer: str
    score: float

    @property
    def context_text(self) -> str:
        return f"[{self.topic}] {self.answer}"


class TipBase:
    def __init__(self, entries: list[dict] | None = None) -> None:
        self.entries = entries if entries is not None else TIPS
        self._vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
        corpus = [f"{e['question']} {e['answer']}" for e in self.entries]
        self._matrix = self._vectorizer.fit_transform(corpus)

    def retrieve(self, query: str, k: int = 3) -> list[Tip]:
        q = self._vectorizer.transform([query])
        sims = cosine_similarity(q, self._matrix).ravel()
        order = sims.argsort()[::-1][:k]
        tips: list[Tip] = []
        for i in order:
            e = self.entries[int(i)]
            tips.append(
                Tip(
                    topic=e["topic"],
                    question=e["question"],
                    answer=e["answer"],
                    score=round(float(sims[int(i)]), 4),
                )
            )
        return tips
