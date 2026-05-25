from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from sportinsight.data import find_game_dirs
from sportinsight.labels import load_events_from_labels


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--classes", nargs="+", default=["Goal", "Corner", "Yellow card", "Red card"])
    args = parser.parse_args()

    counts = Counter()
    games = find_game_dirs(args.root)
    for game in games:
        events = load_events_from_labels(game / "Labels-v2.json", args.classes)
        counts.update(e.label for e in events)
    print(f"Games: {len(games)}")
    total = sum(counts.values())
    print(f"Events: {total}")
    for label in args.classes:
        print(f"{label:12s}: {counts[label]}")
    if counts:
        max_count = max(counts.values())
        print("\nSuggested positive class weights:")
        for label in args.classes:
            c = max(1, counts[label])
            print(f"{label:12s}: {max_count / c:.3f}")


if __name__ == "__main__":
    main()
