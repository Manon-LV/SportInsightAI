from __future__ import annotations

import json
from pathlib import Path

from sportinsight.data import find_feature_file, find_game_dirs
from sportinsight.splits import read_split_lines, validate_disjoint_splits


def _match_summary(game_dir: Path, root: Path, split: str | None = None) -> dict:
    rel = str(game_dir.relative_to(root)).replace("\\", "/") if game_dir.is_relative_to(root) else str(game_dir)
    return {
        "id": rel,
        "path": str(game_dir),
        "name": game_dir.name,
        "split": split,
        "has_first_half": find_feature_file(game_dir, 1) is not None,
        "has_second_half": find_feature_file(game_dir, 2) is not None,
    }


def list_matches(root: str | Path, limit: int = 100, split_file: str | Path | None = None, split_name: str | None = None) -> list[dict]:
    root = Path(root)
    if not root.exists():
        return []
    matches = []
    for game_dir in find_game_dirs(root, split_file)[:limit]:
        matches.append(_match_summary(game_dir, root, split=split_name))
    return matches


def list_checkpoints(root: str | Path = "runs") -> list[dict]:
    root = Path(root)
    if not root.exists():
        return []
    checkpoints = []
    for path in sorted(root.rglob("*.pt")):
        checkpoints.append(
            {
                "id": str(path.relative_to(root)),
                "path": str(path),
                "name": path.name,
            }
        )
    return checkpoints


def split_file_for_name(splits_dir: str | Path, split_name: str) -> Path:
    allowed = {"train", "valid", "val", "validation", "test"}
    normalized = split_name.lower().strip()
    if normalized not in allowed:
        raise ValueError("split_name doit être train, valid ou test")
    if normalized in {"val", "validation"}:
        normalized = "valid"
    return Path(splits_dir) / f"{normalized}.txt"


def list_split_matches(root: str | Path, splits_dir: str | Path, split_name: str, limit: int = 200) -> list[dict]:
    split_file = split_file_for_name(splits_dir, split_name)
    if not split_file.exists():
        return []
    normalized = "valid" if split_name in {"val", "validation"} else split_name
    return list_matches(root=root, limit=limit, split_file=split_file, split_name=normalized)


def list_splits(splits_dir: str | Path = "splits") -> list[dict]:
    directory = Path(splits_dir)
    result = []
    for name in ["train", "valid", "test"]:
        path = directory / f"{name}.txt"
        lines = read_split_lines(path) if path.exists() else []
        result.append({"name": name, "path": str(path), "exists": path.exists(), "count": len(lines)})
    return result


def read_split_integrity(splits_dir: str | Path = "splits") -> dict:
    directory = Path(splits_dir)
    paths = {name: directory / f"{name}.txt" for name in ["train", "valid", "test"]}
    return validate_disjoint_splits(paths)
