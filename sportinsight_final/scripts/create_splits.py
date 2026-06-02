from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from sportinsight.splits import scan_usable_games, split_games, validate_disjoint_splits, write_split_file, write_split_summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Crée des splits train/valid/test par match pour SoccerNet. Aucun match n'est partagé entre les ensembles."
    )
    parser.add_argument("--root", default="data/SoccerNet", help="Racine locale SoccerNet")
    parser.add_argument("--output-dir", default="splits", help="Dossier où écrire train.txt, valid.txt, test.txt")
    parser.add_argument("--train-ratio", type=float, default=0.70)
    parser.add_argument("--valid-ratio", type=float, default=0.15)
    parser.add_argument("--test-ratio", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--complete-halves",
        action="store_true",
        help="Ne garde que les matchs ayant les features pour les deux mi-temps. Par défaut, une seule mi-temps suffit.",
    )
    parser.add_argument("--limit-games", type=int, default=None, help="Optionnel : limite utile pour une démo légère")
    args = parser.parse_args()

    root = Path(args.root)
    games = scan_usable_games(root, complete_halves=args.complete_halves)
    if args.limit_games is not None:
        games = games[: args.limit_games]
    if not games:
        raise RuntimeError(f"Aucun match utilisable trouvé sous {root}. Vérifie Labels-v2.json et les features .npy.")

    split_set = split_games(
        games,
        train_ratio=args.train_ratio,
        valid_ratio=args.valid_ratio,
        test_ratio=args.test_ratio,
        seed=args.seed,
    )

    output_dir = Path(args.output_dir)
    write_split_file(output_dir / "train.txt", split_set.train, root)
    write_split_file(output_dir / "valid.txt", split_set.valid, root)
    write_split_file(output_dir / "test.txt", split_set.test, root)
    write_split_summary(
        output_dir / "summary.json",
        root=root,
        split_set=split_set,
        seed=args.seed,
        ratios={"train": args.train_ratio, "valid": args.valid_ratio, "test": args.test_ratio},
    )

    report = validate_disjoint_splits(
        {
            "train": output_dir / "train.txt",
            "valid": output_dir / "valid.txt",
            "test": output_dir / "test.txt",
        }
    )
    (output_dir / "integrity.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps({"created": str(output_dir), **report}, indent=2, ensure_ascii=False))
    if not report["is_disjoint"]:
        raise RuntimeError("Les splits ne sont pas disjoints. Vérifie integrity.json.")


if __name__ == "__main__":
    main()
