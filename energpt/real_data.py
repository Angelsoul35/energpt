"""Real household electricity-consumption series for EnerGPT.

The synthetic generator (:mod:`energpt.generate`) builds plausible hourly series; this
module loads **real** household consumption — a 10-home, 14-day subset of the Low
Carbon London smart-meter trial (via the Hugging Face ``eeJunCao/London_smart_meter``
mirror), vendored under ``datasets/london_real.npz``. The half-hourly kWh readings are
aggregated to the hourly watt-hours EnerGPT's deterministic engine expects, so the
engine runs on real homes and produces real advisories.

``fetch_london`` refreshes the vendored subset.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DATASET_PATH = _REPO_ROOT / "datasets" / "london_real.npz"
_HF_ROWS_URL = (
    "https://datasets-server.huggingface.co/rows?dataset=eeJunCao%2FLondon_smart_meter"
    "&config=default&split=train&offset={offset}&length=50"
)


def load_london() -> list[tuple[str, list[int]]]:
    """Return ``[(home_id, hourly_watt_hours), ...]`` for the vendored real homes."""
    if not _DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Vendored London data not found at {_DATASET_PATH}. Run "
            "`python -c 'from energpt.real_data import fetch_london; fetch_london()'`."
        )
    data = np.load(_DATASET_PATH, allow_pickle=True)
    readings, ids = data["readings"], data["item_ids"]
    return [(str(ids[i]), [int(x) for x in readings[i]]) for i in range(len(ids))]


def fetch_london(n_homes: int = 10, days: int = 14, dest: str | Path | None = None) -> int:
    """Download a subset of real London homes into ``datasets/london_real.npz``.

    Half-hourly kWh readings are aggregated to hourly watt-hours. Needs network access
    to the Hugging Face datasets-server. Returns the number of homes written.
    """
    import json
    import urllib.request

    target = Path(dest) if dest is not None else _DATASET_PATH
    half_hours = days * 48
    series: list[np.ndarray] = []
    ids: list[str] = []
    offset = 0
    while len(series) < n_homes and offset < 400:
        with urllib.request.urlopen(_HF_ROWS_URL.format(offset=offset), timeout=60) as resp:
            payload = json.load(resp)
        for row in payload["rows"]:
            t = np.asarray(row["row"]["target"], dtype=float)[:half_hours]
            if t.shape[0] < half_hours or np.isnan(t).any() or (t < 0).any():
                continue
            hourly = (t.reshape(-1, 2).sum(axis=1) * 1000.0).round().astype(int)
            if hourly.sum() <= 0:
                continue
            series.append(hourly)
            ids.append(str(row["row"]["item_id"]))
            if len(series) >= n_homes:
                break
        offset += 50

    target.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(target, readings=np.vstack(series), item_ids=np.array(ids))
    return len(series)
