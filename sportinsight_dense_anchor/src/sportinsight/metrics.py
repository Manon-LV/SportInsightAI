from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence

import numpy as np

from .labels import Event
from .postprocess import Prediction


@dataclass
class APResult:
    ap: float
    precision: np.ndarray
    recall: np.ndarray


def average_precision(recalls: np.ndarray, precisions: np.ndarray) -> float:
    """VOC-style interpolated AP over all recall points."""
    if len(recalls) == 0:
        return 0.0
    mrec = np.concatenate([[0.0], recalls, [1.0]])
    mpre = np.concatenate([[0.0], precisions, [0.0]])
    for i in range(len(mpre) - 1, 0, -1):
        mpre[i - 1] = max(mpre[i - 1], mpre[i])
    idx = np.where(mrec[1:] != mrec[:-1])[0]
    return float(np.sum((mrec[idx + 1] - mrec[idx]) * mpre[idx + 1]))


def compute_ap_for_class(
    predictions: List[Prediction],
    targets: List[Event],
    label: str,
    tolerance_sec: float,
) -> APResult:
    preds = [p for p in predictions if p.label == label]
    preds.sort(key=lambda p: -p.score)
    gts = [t for t in targets if t.label == label]

    # Each ground truth can be matched once.
    matched = np.zeros(len(gts), dtype=bool)
    tp = np.zeros(len(preds), dtype=np.float32)
    fp = np.zeros(len(preds), dtype=np.float32)

    for i, pred in enumerate(preds):
        best_j = -1
        best_dist = float("inf")
        for j, gt in enumerate(gts):
            if matched[j] or gt.half != pred.half:
                continue
            dist = abs(gt.time_sec - pred.timestamp)
            if dist <= tolerance_sec and dist < best_dist:
                best_dist = dist
                best_j = j
        if best_j >= 0:
            matched[best_j] = True
            tp[i] = 1.0
        else:
            fp[i] = 1.0

    if len(gts) == 0:
        # Undefined class AP. We return 0; mAP function can skip empty classes.
        return APResult(ap=0.0, precision=np.array([]), recall=np.array([]))

    cum_tp = np.cumsum(tp)
    cum_fp = np.cumsum(fp)
    recalls = cum_tp / max(1, len(gts))
    precisions = cum_tp / np.maximum(cum_tp + cum_fp, 1e-12)
    return APResult(ap=average_precision(recalls, precisions), precision=precisions, recall=recalls)


def temporal_map(
    predictions: Iterable[Prediction],
    targets: Iterable[Event],
    classes: Sequence[str],
    tolerances_sec: Sequence[float],
) -> Dict[str, float]:
    preds = list(predictions)
    gts = list(targets)
    results: Dict[str, float] = {}
    maps = []
    for tol in tolerances_sec:
        aps = []
        for label in classes:
            num_gt = sum(1 for gt in gts if gt.label == label)
            if num_gt == 0:
                continue
            ap = compute_ap_for_class(preds, gts, label, float(tol)).ap
            aps.append(ap)
            results[f"AP@{tol:g}s/{label}"] = ap
        m = float(np.mean(aps)) if aps else 0.0
        results[f"mAP@{tol:g}s"] = m
        maps.append(m)
    results["avg_mAP"] = float(np.mean(maps)) if maps else 0.0
    return results


def mean_temporal_error(
    predictions: Iterable[Prediction],
    targets: Iterable[Event],
    tolerance_sec: float = 10.0,
) -> float:
    preds = sorted(list(predictions), key=lambda p: -p.score)
    gts = list(targets)
    matched = np.zeros(len(gts), dtype=bool)
    errors: List[float] = []
    for pred in preds:
        best_j = -1
        best_dist = float("inf")
        for j, gt in enumerate(gts):
            if matched[j] or gt.label != pred.label or gt.half != pred.half:
                continue
            dist = abs(gt.time_sec - pred.timestamp)
            if dist <= tolerance_sec and dist < best_dist:
                best_j = j
                best_dist = dist
        if best_j >= 0:
            matched[best_j] = True
            errors.append(best_dist)
    return float(np.mean(errors)) if errors else float("nan")
