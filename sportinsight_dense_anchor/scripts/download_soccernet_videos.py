from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Iterable

VIDEO_FILES_BY_RESOLUTION = {
    "224p": ["1_224p.mkv", "2_224p.mkv"],
    "720p": ["1_720p.mkv", "2_720p.mkv"],
}
FEATURE_FILES = ["1_ResNET_TF2_PCA512.npy", "2_ResNET_TF2_PCA512.npy"]
LABEL_FILES = ["Labels-v2.json"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Télécharge les vidéos SoccerNet dans data/SoccerNet avec SoccerNetDownloader. "
            "Les vidéos nécessitent le mot de passe obtenu après signature du NDA SoccerNet."
        )
    )
    parser.add_argument("--root", default="data/SoccerNet", help="Dossier local SoccerNet cible.")
    parser.add_argument(
        "--password",
        default=None,
        help="Mot de passe SoccerNet/NDA. Si absent, utilise la variable SOCCERNET_PASSWORD.",
    )
    parser.add_argument(
        "--split",
        nargs="+",
        default=["train", "valid", "test"],
        choices=["train", "valid", "test", "challenge"],
        help="Splits SoccerNet à télécharger.",
    )
    parser.add_argument(
        "--resolution",
        default="224p",
        choices=["224p", "720p", "both"],
        help="Qualité vidéo. 224p est recommandé pour la démo web.",
    )
    parser.add_argument(
        "--game",
        default=None,
        help=(
            "Jeu unique au format SoccerNet, par ex. "
            "england_epl/2014-2015/2015-02-21 - 18-00 Chelsea 1 - 1 Burnley. "
            "Si absent, télécharge tous les matchs des splits demandés."
        ),
    )
    parser.add_argument(
        "--include-features",
        action="store_true",
        help="Télécharge aussi les features PCA512 associées.",
    )
    parser.add_argument(
        "--include-labels",
        action="store_true",
        help="Télécharge aussi Labels-v2.json.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Affiche les fichiers qui seraient téléchargés sans lancer SoccerNetDownloader.",
    )
    return parser.parse_args()


def selected_video_files(resolution: str) -> list[str]:
    if resolution == "both":
        return VIDEO_FILES_BY_RESOLUTION["224p"] + VIDEO_FILES_BY_RESOLUTION["720p"]
    return VIDEO_FILES_BY_RESOLUTION[resolution]


def build_files(args: argparse.Namespace) -> list[str]:
    files: list[str] = []
    files.extend(selected_video_files(args.resolution))
    if args.include_features:
        files.extend(FEATURE_FILES)
    if args.include_labels:
        files.extend(LABEL_FILES)
    # Preserve order, remove duplicates.
    return list(dict.fromkeys(files))


def require_password(value: str | None) -> str:
    password = value or os.environ.get("SOCCERNET_PASSWORD")
    if not password:
        raise RuntimeError(
            "Mot de passe SoccerNet manquant. Passe --password ou définis SOCCERNET_PASSWORD. "
            "Les vidéos SoccerNet nécessitent l'accès NDA."
        )
    return password


def download(args: argparse.Namespace) -> None:
    files = build_files(args)
    root = Path(args.root)

    print("Configuration téléchargement SoccerNet")
    print(f"- root       : {root}")
    print(f"- split      : {args.split}")
    print(f"- resolution : {args.resolution}")
    print(f"- game       : {args.game or 'tous les matchs des splits'}")
    print(f"- files      : {files}")

    if args.dry_run:
        print("Dry-run : aucun téléchargement lancé.")
        return

    password = require_password(args.password)

    try:
        from SoccerNet.Downloader import SoccerNetDownloader
    except ImportError as exc:
        raise RuntimeError(
            "Le package SoccerNet n'est pas installé. Lance : pip install SoccerNet"
        ) from exc

    root.mkdir(parents=True, exist_ok=True)
    downloader = SoccerNetDownloader(LocalDirectory=str(root))
    downloader.password = password

    if args.game:
        downloader.downloadGame(files=files, game=args.game)
    else:
        downloader.downloadGames(files=files, split=args.split)

    print("Téléchargement terminé.")


def main() -> int:
    args = parse_args()
    try:
        download(args)
    except Exception as exc:  # CLI should print clean errors on Windows terminals.
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
