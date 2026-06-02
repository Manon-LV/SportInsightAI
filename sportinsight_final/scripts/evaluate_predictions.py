from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from sportinsight.data import find_game_dirs
from sportinsight.labels import load_events_from_labels
from sportinsight.metrics import mean_temporal_error, temporal_map
from sportinsight.postprocess import Prediction


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", required=True)
    parser.add_argument("--root", required=True, help="Racine SoccerNet ou dossier d'un match")
    parser.add_argument("--classes", nargs="+", default=["Goal", "Corner", "Yellow card", "Red card"])
    parser.add_argument("--tolerances", nargs="+", type=float, default=[5, 10, 20, 30, 60])
    args = parser.parse_args()

    with open(args.predictions, "r", encoding="utf-8") as f:
        raw_preds = json.load(f)
    preds = [Prediction(**p) for p in raw_preds]

    root = Path(args.root)
    if (root / "Labels-v2.json").exists():
        games = [root]
    else:
        games = find_game_dirs(root)
    targets = []
    for game in games:
        targets.extend(load_events_from_labels(game / "Labels-v2.json", args.classes))

    metrics = temporal_map(preds, targets, classes=args.classes, tolerances_sec=args.tolerances)
    metrics["mean_temporal_error@10s"] = mean_temporal_error(preds, targets, tolerance_sec=10.0)
    print(json.dumps(metrics, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
