from __future__ import annotations

import argparse
import math
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from sportinsight.data import find_game_dirs
from sportinsight.labels import load_events_from_labels

DEFAULT_CLASSES = [
    "Goal", "Corner", "Yellow card", "Red card", "Penalty",
    "Substitution", "Offside", "Foul", "Shots on target", "Shots off target",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--split-file", default=None)
    parser.add_argument("--classes", nargs="+", default=DEFAULT_CLASSES)
    args = parser.parse_args()

    counts: Counter = Counter()
    games = find_game_dirs(args.root, args.split_file)
    for game in games:
        events = load_events_from_labels(game / "Labels-v2.json", args.classes)
        counts.update(e.label for e in events)

    print(f"Games : {len(games)}")
    print(f"Events: {sum(counts.values())}\n")

    max_count = max((counts[c] for c in args.classes), default=1)
    ref = max(1, counts[args.classes[-1]])  # Foul ou derniere classe comme reference

    print(f"{'Classe':<24} {'Count':>7}  {'1/N':>8}  {'1/sqrt(N)':>10}")
    print("-" * 56)
    for label in args.classes:
        n = max(1, counts[label])
        w_inv = max_count / n
        w_sqrt = math.sqrt(max_count) / math.sqrt(n)
        print(f"{label:<24} {counts[label]:>7}  {w_inv:>8.3f}  {w_sqrt:>10.3f}")

    most_common = args.classes[0]
    for c in args.classes:
        if counts[c] > counts[most_common]:
            most_common = c
    ref_sqrt = math.sqrt(max(1, counts[most_common]))

    print(f"\nPoids 1/sqrt(N) normalises a {most_common}=1.0 :")
    weights = []
    for label in args.classes:
        n = max(1, counts[label])
        w = ref_sqrt / math.sqrt(n)
        weights.append(round(w, 1))
    print("  " + str(weights))


if __name__ == "__main__":
    main()
