from __future__ import annotations

import json
import os
import random
from pathlib import Path
from typing import Any, Dict

import numpy as np
import torch
import yaml


def load_config(path: str | os.PathLike) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_json(obj: Any, path: str | os.PathLike) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def read_json(path: str | os.PathLike) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def get_device(name: str = "auto") -> torch.device:
    if name == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(name)


def format_game_time(half: int, seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    minutes = int(seconds // 60)
    sec = int(round(seconds - 60 * minutes))
    if sec == 60:
        minutes += 1
        sec = 0
    return f"{half} - {minutes:02d}:{sec:02d}"


def ensure_2d_features(arr: np.ndarray) -> np.ndarray:
    """Return features as [T, D]. SoccerNet files are usually [T, D]."""
    arr = np.asarray(arr)
    if arr.ndim != 2:
        raise ValueError(f"Expected a 2D feature array [T, D], got shape {arr.shape}.")
    # Some feature exporters save [D, T]. Keep the common [T, D], transpose if D=512 on axis 0.
    if arr.shape[0] == 512 and arr.shape[1] != 512:
        arr = arr.T
    return arr.astype(np.float32, copy=False)
