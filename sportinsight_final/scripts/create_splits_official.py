"""Crée les fichiers de split train/valid/test en utilisant le split officiel SoccerNet.

Les listes officielles sont récupérées via SoccerNet.utils.getListGames, puis filtrées
aux matchs disponibles localement (Labels-v2.json + au moins un fichier de features).

Utilisation :
    python scripts/create_splits_official.py --root data/SoccerNet --output-dir splits
    python scripts/create_splits_official.py --root data/SoccerNet --complete-halves
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from SoccerNet.utils import getListGames

from sportinsight.data import find_feature_file
from sportinsight.splits import validate_disjoint_splits


def filter_local(root: Path, game_list: list[str], complete_halves: bool = False) -> list[str]:
    """Retourne les chemins du game_list qui existent localement avec features.

    Les chemins sont normalisés en POSIX (/) quel que soit l'OS.
    """
    usable = []
    for game_path in game_list:
        posix_path = game_path.replace("\\", "/")
        game_dir = root / posix_path
        if not (game_dir / "Labels-v2.json").exists():
            continue
        has_first = find_feature_file(game_dir, 1) is not None
        has_second = find_feature_file(game_dir, 2) is not None
        if complete_halves:
            if has_first and has_second:
                usable.append(posix_path)
        else:
            if has_first or has_second:
                usable.append(posix_path)
    return usable


def write_split_file(path: Path, games: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(games) + ("\n" if games else ""), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Génère les splits officiels SoccerNet (train/valid/test) en filtrant "
            "les matchs disponibles localement."
        )
    )
    parser.add_argument("--root", default="data/SoccerNet", help="Racine locale SoccerNet")
    parser.add_argument("--output-dir", default="splits", help="Dossier de sortie pour les fichiers .txt")
    parser.add_argument(
        "--complete-halves",
        action="store_true",
        help="Ne garder que les matchs avec les features pour les deux mi-temps.",
    )
    args = parser.parse_args()

    root = Path(args.root)
    output_dir = Path(args.output_dir)

    print("Récupération des listes officielles SoccerNet...")
    official_train = getListGames(split="train")
    official_valid = getListGames(split="valid")
    official_test = getListGames(split="test")

    print(f"  Officiel — train: {len(official_train)}, valid: {len(official_valid)}, test: {len(official_test)}")

    print(f"Filtrage des matchs disponibles sous {root}...")
    train_games = filter_local(root, official_train, args.complete_halves)
    valid_games = filter_local(root, official_valid, args.complete_halves)
    test_games = filter_local(root, official_test, args.complete_halves)

    print(f"  Disponibles — train: {len(train_games)}, valid: {len(valid_games)}, test: {len(test_games)}")
    if not train_games:
        raise RuntimeError(
            f"Aucun match d'entraînement trouvé sous {root}. "
            "Vérifiez que les données SoccerNet sont bien téléchargées (Labels-v2.json + features .npy)."
        )

    write_split_file(output_dir / "train.txt", train_games)
    write_split_file(output_dir / "valid.txt", valid_games)
    write_split_file(output_dir / "test.txt", test_games)

    summary = {
        "source": "official_soccernet_split",
        "complete_halves": args.complete_halves,
        "official_counts": {
            "train": len(official_train),
            "valid": len(official_valid),
            "test": len(official_test),
        },
        "counts": {
            "train": len(train_games),
            "valid": len(valid_games),
            "test": len(test_games),
            "total": len(train_games) + len(valid_games) + len(test_games),
        },
        "principle": "Split officiel SoccerNet — aucun match partagé entre ensembles",
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    report = validate_disjoint_splits({
        "train": output_dir / "train.txt",
        "valid": output_dir / "valid.txt",
        "test": output_dir / "test.txt",
    })
    (output_dir / "integrity.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps({"created": str(output_dir), **summary, "integrity": report}, indent=2, ensure_ascii=False))

    if not report["is_disjoint"]:
        raise RuntimeError("Les splits officiels ne sont pas disjoints — anomalie inattendue.")


if __name__ == "__main__":
    main()
