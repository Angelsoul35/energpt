"""EnerGPT HTTP API."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .generate import sample_names
from .service import EnerGPTService

app = FastAPI(
    title="EnerGPT",
    version="1.0.0",
    summary="Deterministic electricity-consumption analysis with an LLM-phrased advisory.",
)

_service: EnerGPTService | None = None


def get_service() -> EnerGPTService:
    global _service
    if _service is None:
        _service = EnerGPTService()
    return _service


class AnalyzeRequest(BaseModel):
    # Supply either a raw hourly series (watt-hours) or a sample id.
    series: list[int] | None = Field(default=None, description="Hourly readings in watt-hours")
    sample: str | None = Field(default=None, description="Named sample id (see /samples)")
    days: int = Field(default=14, gt=0, le=90)
    question: str | None = Field(default=None, description="Optional free-text tip question")


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1)


@app.get("/health", tags=["ops"])
def health() -> dict:
    return {"status": "ok"}


@app.get("/samples", tags=["analysis"])
def samples() -> dict:
    return {"samples": sample_names()}


@app.post("/analyze", tags=["analysis"])
def analyze(request: AnalyzeRequest) -> dict:
    if request.series is not None and len(request.series) == 0:
        raise HTTPException(status_code=422, detail="series must not be empty")
    try:
        return get_service().run(
            series=request.series,
            sample=request.sample,
            question=request.question,
            days=request.days,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/ask", tags=["tips"])
def ask(request: QuestionRequest) -> dict:
    return get_service().answer_question(request.question)
