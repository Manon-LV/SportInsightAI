from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable, List, Sequence

import numpy as np
import torch

from .utils import format_game_time


@dataclass
class Prediction:
    half: int
    timestamp: float
    gameTime: str
    label: str
    score: float

    def to_dict(self) -> dict:
        return asdict(self)


def temporal_nms(
    times: np.ndarray,
    scores: np.ndarray,
    radius_sec: float,
    max_predictions: int | None = None,
) -> List[int]:
    """Hard temporal NMS. Suppresses predictions within radius of a better score."""
    if len(times) == 0:
        return []
    order = np.argsort(-scores)
    keep: List[int] = []
    suppressed = np.zeros(len(times), dtype=bool)
    for idx in order:
        if suppressed[idx]:
            continue
        keep.append(int(idx))
        if max_predictions is not None and len(keep) >= max_predictions:
            break
        close = np.abs(times - times[idx]) <= radius_sec
        suppressed |= close
        suppressed[idx] = False
    keep.sort(key=lambda i: times[i])
    return keep


def temporal_soft_nms(
    times: np.ndarray,
    scores: np.ndarray,
    radius_sec: float,
    score_threshold: float,
    max_predictions: int | None = None,
    sigma: float | None = None,
) -> List[int]:
    """Gaussian Soft-NMS for 1D temporal predictions."""
    if len(times) == 0:
        return []
    sigma = float(sigma or radius_sec)
    remaining = list(range(len(times)))
    scores_mut = scores.astype(np.float32).copy()
    keep: List[int] = []
    while remaining:
        best = max(remaining, key=lambda i: scores_mut[i])
        if scores_mut[best] < score_threshold:
            break
        keep.append(best)
        remaining.remove(best)
        if max_predictions is not None and len(keep) >= max_predictions:
            break
        for i in remaining:
            dist = abs(times[i] - times[best])
            if dist <= radius_sec:
                scores_mut[i] *= np.exp(-(dist * dist) / (2.0 * sigma * sigma))
    keep.sort(key=lambda i: times[i])
    return keep


def predictions_from_window(
    cls_logits: torch.Tensor,
    offsets: torch.Tensor,
    classes: Sequence[str],
    half: int,
    start_time_sec: float,
    feature_fps: float,
    score_threshold: float = 0.3,
) -> List[Prediction]:
    """Convert model output for one window into raw predictions."""
    # cls_logits / offsets: [T, C]
    probs = torch.sigmoid(cls_logits).detach().cpu().numpy()
    off = offsets.detach().cpu().numpy()
    T, C = probs.shape
    anchor_times = start_time_sec + np.arange(T, dtype=np.float32) / float(feature_fps)
    preds: List[Prediction] = []
    for c in range(C):
        idxs = np.where(probs[:, c] >= score_threshold)[0]
        for idx in idxs:
            t = float(anchor_times[idx] + off[idx, c])
            t = max(0.0, t)
            preds.append(
                Prediction(
                    half=half,
                    timestamp=t,
                    gameTime=format_game_time(half, t),
                    label=classes[c],
                    score=float(probs[idx, c]),
                )
            )
    return preds


def nms_predictions(
    predictions: Iterable[Prediction],
    classes: Sequence[str],
    radius_sec: float = 6.0,
    score_threshold: float = 0.3,
    max_predictions_per_class: int | None = 200,
    use_soft_nms: bool = False,
) -> List[Prediction]:
    """Apply class-wise and half-wise temporal NMS."""
    preds = [p for p in predictions if p.score >= score_threshold]
    final: List[Prediction] = []
    for half in (1, 2):
        for label in classes:
            group = [p for p in preds if p.half == half and p.label == label]
            if not group:
                continue
            times = np.asarray([p.timestamp for p in group], dtype=np.float32)
            scores = np.asarray([p.score for p in group], dtype=np.float32)
            if use_soft_nms:
                keep = temporal_soft_nms(times, scores, radius_sec, score_threshold, max_predictions_per_class)
            else:
                keep = temporal_nms(times, scores, radius_sec, max_predictions_per_class)
            final.extend([group[i] for i in keep])
    final.sort(key=lambda p: (p.half, p.timestamp, -p.score))
    return final
