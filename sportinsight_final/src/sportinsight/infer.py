from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List, Literal, Sequence

import numpy as np
import torch

from .data import find_feature_file, load_features
from .model import build_model
from .postprocess import Prediction, nms_predictions, predictions_from_window
from .utils import get_device, save_json

HalfSelector = Literal["first", "second", "both"]


def _resolve_halves(half: str) -> tuple[int, ...]:
    normalized = half.lower().strip()
    if normalized in {"1", "first", "h1", "half1", "mi-temps-1", "premiere", "première"}:
        return (1,)
    if normalized in {"2", "second", "h2", "half2", "mi-temps-2", "deuxieme", "deuxième"}:
        return (2,)
    if normalized in {"both", "all", "match", "full", "complet", "toutes"}:
        return (1, 2)
    raise ValueError("half must be one of: first, second, both")


def _filtered_classes(classes: Sequence[str], selected_classes: Sequence[str] | None) -> list[str]:
    if not selected_classes:
        return list(classes)
    allowed = set(classes)
    filtered = [label for label in selected_classes if label in allowed]
    return filtered or list(classes)


@torch.no_grad()
def predict_half(
    model,
    features: np.ndarray,
    classes: List[str],
    half: int,
    feature_fps: float,
    window_size_sec: float,
    stride_sec: float,
    post_cfg: dict,
    device: torch.device,
) -> List[Prediction]:
    model.eval()
    window_len = max(1, int(round(window_size_sec * feature_fps)))
    stride_len = max(1, int(round(stride_sec * feature_fps)))
    n = features.shape[0]
    if n <= window_len:
        starts = [0]
    else:
        starts = list(range(0, n - window_len + 1, stride_len))
        last_start = n - window_len
        if starts[-1] != last_start:
            starts.append(last_start)

    raw: List[Prediction] = []
    for start in starts:
        end = min(start + window_len, n)
        x = features[start:end]
        if x.shape[0] < window_len:
            pad = np.zeros((window_len - x.shape[0], x.shape[1]), dtype=np.float32)
            x = np.concatenate([x, pad], axis=0)
        xb = torch.from_numpy(x.astype(np.float32)).unsqueeze(0).to(device)
        outputs = model(xb)
        raw.extend(
            predictions_from_window(
                outputs["cls_logits"][0],
                outputs["offsets"][0],
                classes=classes,
                half=half,
                start_time_sec=start / feature_fps,
                feature_fps=feature_fps,
                score_threshold=float(post_cfg.get("score_threshold", 0.3)),
            )
        )
    return raw


def load_checkpoint_model(checkpoint: str | Path, device_name: str = "auto"):
    """Load a SportInsight checkpoint and return (model, config, classes, device)."""
    device = get_device(device_name)
    ckpt = torch.load(checkpoint, map_location=device)
    cfg = ckpt["config"]
    classes = list(ckpt.get("classes", cfg["data"]["classes"]))
    model = build_model(cfg).to(device)
    model.load_state_dict(ckpt["model_state"])
    model.eval()
    return model, cfg, classes, device


def run_inference(
    checkpoint: str | Path,
    game_dir: str | Path,
    output: str | Path | None = None,
    device_name: str = "auto",
    half: str = "both",
    score_threshold: float | None = None,
    nms_radius_sec: float | None = None,
    max_predictions_per_class: int | None = None,
    selected_classes: Sequence[str] | None = None,
) -> list[dict]:
    """Run inference on one SoccerNet match directory.

    The public contract is match-level: `game_dir` contains the SoccerNet files and
    `half` chooses first, second, or both halves. The model still receives windowed
    ResNet PCA512 features internally.
    """
    model, cfg, classes, device = load_checkpoint_model(checkpoint, device_name=device_name)

    data_cfg = cfg["data"]
    post_cfg = dict(cfg.get("postprocess", {}))
    if score_threshold is not None:
        post_cfg["score_threshold"] = float(score_threshold)
    if nms_radius_sec is not None:
        post_cfg["nms_radius_sec"] = float(nms_radius_sec)
    if max_predictions_per_class is not None:
        post_cfg["max_predictions_per_class"] = int(max_predictions_per_class)

    feature_fps = float(data_cfg.get("feature_fps", 2.0))
    window_size_sec = float(data_cfg.get("window_size_sec", 120.0))
    stride_sec = float(data_cfg.get("stride_sec", 60.0))

    game_dir = Path(game_dir)
    halves = _resolve_halves(half)
    raw_preds: List[Prediction] = []

    loaded_halves: list[int] = []
    missing_halves: list[int] = []

    for half_idx in halves:
        fpath = find_feature_file(game_dir, half_idx)
        if fpath is None:
            missing_halves.append(half_idx)
            continue
        loaded_halves.append(half_idx)
        features = load_features(fpath)
        raw_preds.extend(
            predict_half(
                model,
                features,
                classes=classes,
                half=half_idx,
                feature_fps=feature_fps,
                window_size_sec=window_size_sec,
                stride_sec=stride_sec,
                post_cfg=post_cfg,
                device=device,
            )
        )

    if not loaded_halves:
        expected = ", ".join([
            "1_ResNET_PCA512.npy",
            "2_ResNET_PCA512.npy",
            "1_ResNET_TF2_PCA512.npy",
            "2_ResNET_TF2_PCA512.npy",
        ])
        raise FileNotFoundError(
            f"Aucune feature SoccerNet PCA512 trouvée dans {game_dir}. "
            f"Fichiers attendus : {expected}. "
            "Les vidéos seules ne suffisent pas pour lancer le modèle actuel."
        )

    classes_to_keep = _filtered_classes(classes, selected_classes)
    final = nms_predictions(
        raw_preds,
        classes=classes_to_keep,
        radius_sec=float(post_cfg.get("nms_radius_sec", 6.0)),
        score_threshold=float(post_cfg.get("score_threshold", 0.3)),
        max_predictions_per_class=int(post_cfg.get("max_predictions_per_class", 200)),
        use_soft_nms=bool(post_cfg.get("use_soft_nms", False)),
    )
    result = [p.to_dict() for p in final]
    if output is not None:
        save_json(result, output)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--game-dir", required=True, help="Dossier SoccerNet contenant les features d'un match")
    parser.add_argument("--output", default="predictions.json")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--half", default="both", choices=["first", "second", "both"])
    parser.add_argument("--score-threshold", type=float, default=None)
    parser.add_argument("--nms-radius-sec", type=float, default=None)
    parser.add_argument("--selected-classes", nargs="*", default=None)
    args = parser.parse_args()

    final = run_inference(
        checkpoint=args.checkpoint,
        game_dir=args.game_dir,
        output=args.output,
        device_name=args.device,
        half=args.half,
        score_threshold=args.score_threshold,
        nms_radius_sec=args.nms_radius_sec,
        selected_classes=args.selected_classes,
    )
    print(f"{len(final)} prédictions sauvegardées dans {args.output}")


if __name__ == "__main__":
    main()
