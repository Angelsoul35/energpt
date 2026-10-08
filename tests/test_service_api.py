from __future__ import annotations

from fastapi.testclient import TestClient

from energpt.config import Settings
from energpt.llm.fake import FailingLLM
from energpt.service import EnerGPTService


def _service() -> EnerGPTService:
    # FailingLLM -> deterministic template advisory; no network, offline.
    return EnerGPTService(settings=Settings(), llm=FailingLLM())


def test_run_on_sample_is_offline_and_grounded():
    result = _service().run(sample="home", question="how do I cut standby power?")
    assert result["advisory"]["source"] == "template"
    assert result["analysis"]["tariff"]["total_cost_cents"] > 0
    assert result["analysis"]["opportunities"]
    assert result["tip"]["topic"] == "standby_power"


def test_run_accepts_a_raw_series():
    series = [1000 if 17 <= (i % 24) <= 20 else 100 for i in range(48)]
    result = _service().run(series=series)
    assert result["analysis"]["tariff"]["total_cost_cents"] == 288
    assert result["analysis"]["base_load_wh"] == 100


def _client(service):
    import energpt.main as main

    main._service = service
    return TestClient(main.app)


def test_api_endpoints():
    client = _client(_service())

    assert client.get("/health").json() == {"status": "ok"}
    assert "home" in client.get("/samples").json()["samples"]

    analyze = client.post("/analyze", json={"sample": "home", "question": "cut standby?"})
    assert analyze.status_code == 200
    body = analyze.json()
    assert body["advisory"]["source"] == "template"
    assert body["tip"]["citations"]

    series = [1000 if 17 <= (i % 24) <= 20 else 100 for i in range(48)]
    raw = client.post("/analyze", json={"series": series})
    assert raw.status_code == 200
    assert raw.json()["analysis"]["tariff"]["total_cost_cents"] == 288

    assert client.post("/analyze", json={"series": []}).status_code == 422
    ask = client.post("/ask", json={"question": "how do I save on lighting?"})
    assert ask.status_code == 200
    assert ask.json()["topic"] == "lighting"
    assert client.post("/ask", json={"question": ""}).status_code == 422
