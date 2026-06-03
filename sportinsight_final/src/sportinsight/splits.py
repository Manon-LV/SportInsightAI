from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from .data import find_feature_file, find_game_dirs


@dataclass(frozen=True)
class SplitSet:
    train: list[Path]
    valid: list[Path]
    test: list[Path]


def path_to_split_line(game_dir: Path, root: Path) -> str:
    """Return a stable POSIX-style path suitable for split files."""
    game_dir = game_dir.resolve()
    root = root.resolve()
    try:
        return game_dir.relative_to(root).as_posix()
    except ValueError:
        return game_dir.as_posix()


def read_split_lines(path: str | Path) -> list[str]:
    split_path = Path(path)
    if not split_path.exists():
        return []
    lines: list[str] = []
    with split_path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            lines.append(line.replace("\\", "/"))
    return lines


def write_split_file(path: str | Path, game_dirs: Sequence[Path], root: str | Path) -> None:
    root_path = Path(root)
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [path_to_split_line(Path(game_dir), root_path) for game_dir in game_dirs]
    out_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def has_required_features(game_dir: Path, complete_halves: bool = False) -> bool:
    first = find_feature_file(game_dir, 1) is not None
    second = find_feature_file(game_dir, 2) is not None
    return (first and second) if complete_halves else (first or second)


def scan_usable_games(root: str | Path, complete_halves: bool = False) -> list[Path]:
    root_path = Path(root)
    games = find_game_dirs(root_path)
    return [game for game in games if has_required_features(game, complete_halves=complete_halves)]


def split_games(
    games: Sequence[Path],
    train_ratio: float = 0.70,
    valid_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
) -> SplitSet:
    if train_ratio <= 0 or valid_ratio < 0 or test_ratio < 0:
        raise ValueError("Les ratios doivent être positifs et train_ratio doit être > 0.")
    total_ratio = train_ratio + valid_ratio + test_ratio
    if total_ratio <= 0:
        raise ValueError("La somme des ratios doit être > 0.")

    shuffled = list(games)
    random.Random(seed).shuffle(shuffled)
    n = len(shuffled)
    if n == 0:
        return SplitSet(train=[], valid=[], test=[])

    train_ratio /= total_ratio
    valid_ratio /= total_ratio
    test_ratio /= total_ratio

    n_train = int(round(n * train_ratio))
    n_valid = int(round(n * valid_ratio))

    # Garantit au moins un match de validation/test si le dataset est assez grand.
    if n >= 3:
        n_train = max(1, min(n - 2, n_train))
        n_valid = max(1, min(n - n_train - 1, n_valid))
    elif n == 2:
        n_train = 1
        n_valid = 1
    else:
        n_train = 1
        n_valid = 0

    n_test = max(0, n - n_train - n_valid)
    train = shuffled[:n_train]
    valid = shuffled[n_train:n_train + n_valid]
    test = shuffled[n_train + n_valid:n_train + n_valid + n_test]
    return SplitSet(train=train, valid=valid, test=test)


def validate_disjoint_splits(split_paths: dict[str, str | Path]) -> dict:
    """Check overlap between split files and return a serializable report."""
    sets = {name: set(read_split_lines(path)) for name, path in split_paths.items() if path}
    overlaps: list[dict] = []
    names = list(sets)
    for i, left in enumerate(names):
        for right in names[i + 1:]:
            common = sorted(sets[left] & sets[right])
            if common:
                overlaps.append({"left": left, "right": right, "count": len(common), "examples": common[:10]})
    return {
        "counts": {name: len(values) for name, values in sets.items()},
        "overlap_count": sum(item["count"] for item in overlaps),
        "overlaps": overlaps,
        "is_disjoint": not overlaps,
    }


def write_split_summary(path: str | Path, root: str | Path, split_set: SplitSet, seed: int, ratios: dict[str, float]) -> None:
    summary = {
        "root": str(root),
        "seed": seed,
        "ratios": ratios,
        "counts": {
            "train": len(split_set.train),
            "valid": len(split_set.valid),
            "test": len(split_set.test),
            "total": len(split_set.train) + len(split_set.valid) + len(split_set.test),
        },
        "principle": "split par match : aucun match ne doit apparaître dans plusieurs ensembles",
    }
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
