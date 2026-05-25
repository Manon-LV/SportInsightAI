from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence

import numpy as np
import torch
from torch.utils.data import Dataset

from .labels import Event, filter_events, load_events_from_labels
from .utils import ensure_2d_features


@dataclass(frozen=True)
class WindowIndex:
    game_dir: str
    half: int
    start_idx: int
    end_idx: int
    num_frames: int


def find_game_dirs(root: str | Path, split_file: str | Path | None = None) -> List[Path]:
    root = Path(root)
    if split_file is not None:
        paths: List[Path] = []
        with open(split_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                p = Path(line)
                paths.append(p if p.is_absolute() else root / p)
        return [p for p in paths if (p / "Labels-v2.json").exists()]
    return sorted({p.parent for p in root.rglob("Labels-v2.json")})


def find_feature_file(game_dir: str | Path, half: int) -> Path | None:
    """Find SoccerNet ResNET PCA512 features for a half."""
    game_dir = Path(game_dir)
    exact_names = [
        f"{half}_ResNET_PCA512.npy",
        f"{half}_ResNET_PCA512.npy.gz",
        f"{half}_ResNET_TF2_PCA512.npy",
    ]
    for name in exact_names:
        path = game_dir / name
        if path.exists():
            return path

    candidates = sorted(game_dir.glob(f"{half}_*.npy"))
    for path in candidates:
        low = path.name.lower()
        if "resnet" in low and "pca512" in low:
            return path
    return None


def load_features(path: str | Path) -> np.ndarray:
    arr = np.load(path)
    return ensure_2d_features(arr)


class SoccerNetDenseAnchorDataset(Dataset):
    """Windowed SoccerNet dataset for dense temporal anchor spotting.

    Each item returns:
      - x: [L, D]
      - cls_target: [L, C], values 0/1
      - cls_mask: [L, C], 0 means ignored for classification
      - reg_target: [L, C], offset in seconds
      - reg_mask: [L, C], 1 only for positive anchors
      - meta: game path, half, start time
    """

    def __init__(
        self,
        root: str | Path,
        classes: Sequence[str],
        feature_fps: float = 2.0,
        window_size_sec: float = 120.0,
        stride_sec: float = 60.0,
        positive_radius_sec: float = 2.0,
        ignore_radius_sec: float = 5.0,
        split_file: str | Path | None = None,
        include_not_shown: bool = True,
        cache_features: bool = False,
    ) -> None:
        self.root = Path(root)
        self.classes = list(classes)
        self.feature_fps = float(feature_fps)
        self.window_size_sec = float(window_size_sec)
        self.stride_sec = float(stride_sec)
        self.positive_radius_sec = float(positive_radius_sec)
        self.ignore_radius_sec = float(ignore_radius_sec)
        self.window_len = max(1, int(round(self.window_size_sec * self.feature_fps)))
        self.stride_len = max(1, int(round(self.stride_sec * self.feature_fps)))
        self.include_not_shown = include_not_shown
        self.cache_features = cache_features
        self._feature_cache: Dict[tuple[str, int], np.ndarray] = {}

        self.game_dirs = find_game_dirs(self.root, split_file)
        if not self.game_dirs:
            raise FileNotFoundError(f"No SoccerNet games found under {self.root}")

        self.events_by_game: Dict[str, List[Event]] = {}
        self.feature_paths: Dict[tuple[str, int], Path] = {}
        self.windows: List[WindowIndex] = []
        self._build_index()

        if not self.windows:
            raise RuntimeError("No usable windows were found. Check feature filenames and root path.")

    def _build_index(self) -> None:
        for game_dir in self.game_dirs:
            labels_path = game_dir / "Labels-v2.json"
            events = load_events_from_labels(labels_path, self.classes, self.include_not_shown)
            self.events_by_game[str(game_dir)] = events

            for half in (1, 2):
                feature_path = find_feature_file(game_dir, half)
                if feature_path is None:
                    continue
                features = load_features(feature_path)
                self.feature_paths[(str(game_dir), half)] = feature_path
                n = int(features.shape[0])
                if n <= 0:
                    continue

                if n <= self.window_len:
                    starts = [0]
                else:
                    starts = list(range(0, n - self.window_len + 1, self.stride_len))
                    last_start = n - self.window_len
                    if starts[-1] != last_start:
                        starts.append(last_start)

                for start in starts:
                    self.windows.append(
                        WindowIndex(
                            game_dir=str(game_dir),
                            half=half,
                            start_idx=start,
                            end_idx=min(start + self.window_len, n),
                            num_frames=n,
                        )
                    )

    def __len__(self) -> int:
        return len(self.windows)

    def _get_features(self, game_dir: str, half: int) -> np.ndarray:
        key = (game_dir, half)
        if self.cache_features and key in self._feature_cache:
            return self._feature_cache[key]
        features = load_features(self.feature_paths[key])
        if self.cache_features:
            self._feature_cache[key] = features
        return features

    def _make_targets(self, window: WindowIndex) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        L = self.window_len
        C = len(self.classes)
        cls_target = np.zeros((L, C), dtype=np.float32)
        cls_mask = np.ones((L, C), dtype=np.float32)
        reg_target = np.zeros((L, C), dtype=np.float32)
        reg_mask = np.zeros((L, C), dtype=np.float32)

        start_time = window.start_idx / self.feature_fps
        anchor_times = start_time + np.arange(L, dtype=np.float32) / self.feature_fps
        half_events = filter_events(self.events_by_game.get(window.game_dir, []), half=window.half)

        for event in half_events:
            # Ignore events outside a loose neighborhood of the window.
            if event.time_sec < anchor_times[0] - self.ignore_radius_sec:
                continue
            if event.time_sec > anchor_times[-1] + self.ignore_radius_sec:
                continue

            dist = np.abs(anchor_times - event.time_sec)
            c = event.class_idx

            ignore = (dist <= self.ignore_radius_sec) & (dist > self.positive_radius_sec)
            cls_mask[ignore, c] = 0.0

            positive = dist <= self.positive_radius_sec
            if not np.any(positive):
                continue
            cls_target[positive, c] = 1.0
            cls_mask[positive, c] = 1.0
            reg_target[positive, c] = event.time_sec - anchor_times[positive]
            reg_mask[positive, c] = 1.0

        return cls_target, cls_mask, reg_target, reg_mask

    def __getitem__(self, idx: int) -> dict:
        w = self.windows[idx]
        features = self._get_features(w.game_dir, w.half)
        x = features[w.start_idx:w.end_idx]
        if x.shape[0] < self.window_len:
            pad = np.zeros((self.window_len - x.shape[0], x.shape[1]), dtype=np.float32)
            x = np.concatenate([x, pad], axis=0)

        cls_target, cls_mask, reg_target, reg_mask = self._make_targets(w)
        meta = {
            "game_dir": w.game_dir,
            "half": w.half,
            "start_time_sec": w.start_idx / self.feature_fps,
            "end_time_sec": w.end_idx / self.feature_fps,
        }
        return {
            "x": torch.from_numpy(x.astype(np.float32)),
            "cls_target": torch.from_numpy(cls_target),
            "cls_mask": torch.from_numpy(cls_mask),
            "reg_target": torch.from_numpy(reg_target),
            "reg_mask": torch.from_numpy(reg_mask),
            "meta": meta,
        }


def dense_anchor_collate(batch: List[dict]) -> dict:
    keys = ["x", "cls_target", "cls_mask", "reg_target", "reg_mask"]
    out = {key: torch.stack([item[key] for item in batch], dim=0) for key in keys}
    out["meta"] = [item["meta"] for item in batch]
    return out
