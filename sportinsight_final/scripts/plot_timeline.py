from __future__ import annotations

import argparse
from pathlib import Path

from sportinsight.labels import load_events_from_labels
from sportinsight.utils import read_json
from sportinsight.visualization import plot_timeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Trace une timeline des prédictions, avec labels optionnels.")
    parser.add_argument("--predictions", required=True, help="Fichier predictions.json produit par sportinsight.infer")
    parser.add_argument("--labels", default=None, help="Chemin vers Labels-v2.json pour afficher la vérité terrain")
    parser.add_argument("--output", default="timeline.png")
    parser.add_argument(
        "--classes",
        nargs="+",
        default=["Goal", "Corner", "Yellow card", "Red card"],
        help="Classes à afficher, dans l'ordre vertical souhaité",
    )
    args = parser.parse_args()

    predictions = read_json(args.predictions)
    labels = None
    if args.labels:
        events = load_events_from_labels(args.labels, classes=args.classes)
        labels = [
            {"half": e.half, "timestamp": e.time_sec, "label": e.label}
            for e in events
        ]

    out = plot_timeline(
        predictions=predictions,
        labels=labels,
        classes=args.classes,
        output_path=args.output,
    )
    print(f"Timeline générée : {out}")


if __name__ == "__main__":
    main()
