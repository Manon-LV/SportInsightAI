from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from uuid import uuid4

from sportinsight.infer import run_inference
from sportinsight.utils import save_json

STORAGE_DIR = Path(__file__).resolve().parent / "storage" / "runs"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def _summarize_events(run_id: str, payload: dict, events: list[dict]) -> dict:
    by_class = Counter(event["label"] for event in events)
    by_half = Counter(str(event["half"]) for event in events)
    return {
        "run_id": run_id,
        "match_dir": payload["match_dir"],
        "checkpoint": payload["checkpoint"],
        "half": payload.get("half", "both"),
        "event_count": len(events),
        "counts_by_class": dict(sorted(by_class.items())),
        "counts_by_half": dict(sorted(by_half.items())),
    }


def create_inference_run(payload: dict) -> dict:
    run_id = f"run_{uuid4().hex[:12]}"
    run_dir = STORAGE_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    events = run_inference(
        checkpoint=payload["checkpoint"],
        game_dir=payload["match_dir"],
        output=run_dir / "events.json",
        device_name=payload.get("device", "auto"),
        half=payload.get("half", "both"),
        score_threshold=payload.get("score_threshold", 0.30),
        nms_radius_sec=payload.get("nms_radius_sec", 6.0),
        selected_classes=payload.get("selected_classes"),
    )
    summary = _summarize_events(run_id, payload, events)
    save_json(payload, run_dir / "request.json")
    save_json(summary, run_dir / "summary.json")
    return {"run_id": run_id, "events": events, "summary": summary}


def read_run_file(run_id: str, filename: str):
    path = STORAGE_DIR / run_id / filename
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
