from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np
import torch
from tqdm import tqdm

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from sportinsight.data import find_feature_file, find_game_dirs, load_features
from sportinsight.infer import predict_half
from sportinsight.labels import load_events_from_labels
from sportinsight.model import build_model
from sportinsight.postprocess import Prediction, nms_predictions
from sportinsight.utils import get_device


def safe_relpath(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return path.name


def average_precision(recalls: np.ndarray, precisions: np.ndarray) -> float:
    if len(recalls) == 0:
        return float("nan")
    mrec = np.concatenate([[0.0], recalls, [1.0]])
    mpre = np.concatenate([[0.0], precisions, [0.0]])
    for i in range(len(mpre) - 1, 0, -1):
        mpre[i - 1] = max(mpre[i - 1], mpre[i])
    idx = np.where(mrec[1:] != mrec[:-1])[0]
    return float(np.sum((mrec[idx + 1] - mrec[idx]) * mpre[idx + 1]))


def ap_for_class(
    predictions: List[dict],
    targets: List[dict],
    label: str,
    tolerance_sec: float,
) -> tuple[float, list[dict]]:
    preds = [p for p in predictions if p["label"] == label]
    preds.sort(key=lambda p: -float(p["score"]))
    gts = [t for t in targets if t["label"] == label]

    if len(gts) == 0:
        return float("nan"), []

    matched = np.zeros(len(gts), dtype=bool)
    tp = np.zeros(len(preds), dtype=np.float32)
    fp = np.zeros(len(preds), dtype=np.float32)

    for i, pred in enumerate(preds):
        best_j = -1
        best_dist = float("inf")
        for j, gt in enumerate(gts):
            if matched[j]:
                continue
            if gt["game"] != pred["game"] or int(gt["half"]) != int(pred["half"]):
                continue
            dist = abs(float(gt["time_sec"]) - float(pred["timestamp"]))
            if dist <= tolerance_sec and dist < best_dist:
                best_j = j
                best_dist = dist
        if best_j >= 0:
            matched[best_j] = True
            tp[i] = 1.0
        else:
            fp[i] = 1.0

    cum_tp = np.cumsum(tp)
    cum_fp = np.cumsum(fp)
    recalls = cum_tp / max(1, len(gts))
    precisions = cum_tp / np.maximum(cum_tp + cum_fp, 1e-12)
    ap = average_precision(recalls, precisions)

    curve = []
    for rank, (r, p, tpi, fpi) in enumerate(zip(recalls, precisions, cum_tp, cum_fp), start=1):
        curve.append(
            {
                "class": label,
                "tolerance_sec": tolerance_sec,
                "rank": rank,
                "recall": float(r),
                "precision": float(p),
                "cum_tp": int(tpi),
                "cum_fp": int(fpi),
            }
        )
    return ap, curve


def detection_metrics_at_tolerance(
    predictions: List[dict],
    targets: List[dict],
    classes: Sequence[str],
    tolerance_sec: float,
) -> tuple[list[dict], list[float]]:
    rows = []
    all_errors: list[float] = []

    for label in classes:
        preds = [p for p in predictions if p["label"] == label]
        preds.sort(key=lambda p: -float(p["score"]))
        gts = [t for t in targets if t["label"] == label]
        matched = np.zeros(len(gts), dtype=bool)

        tp = 0
        fp = 0
        errors: list[float] = []

        for pred in preds:
            best_j = -1
            best_dist = float("inf")
            for j, gt in enumerate(gts):
                if matched[j]:
                    continue
                if gt["game"] != pred["game"] or int(gt["half"]) != int(pred["half"]):
                    continue
                dist = abs(float(gt["time_sec"]) - float(pred["timestamp"]))
                if dist <= tolerance_sec and dist < best_dist:
                    best_j = j
                    best_dist = dist
            if best_j >= 0:
                matched[best_j] = True
                tp += 1
                errors.append(best_dist)
                all_errors.append(best_dist)
            else:
                fp += 1

        fn = int(len(gts) - matched.sum())
        precision = tp / max(tp + fp, 1)
        recall = tp / max(len(gts), 1)
        f1 = 2 * precision * recall / max(precision + recall, 1e-12)
        rows.append(
            {
                "class": label,
                "tolerance_sec": tolerance_sec,
                "gt": len(gts),
                "pred": len(preds),
                "tp": int(tp),
                "fp": int(fp),
                "fn": int(fn),
                "precision": float(precision),
                "recall": float(recall),
                "f1": float(f1),
                "mean_temporal_error_sec": float(np.mean(errors)) if errors else float("nan"),
            }
        )
    return rows, all_errors


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def plot_metrics(output_dir: Path, classes: Sequence[str], tolerances: Sequence[float], ap_rows: list[dict], point_rows: list[dict], pr_rows: list[dict], errors: list[float]) -> None:
    import matplotlib.pyplot as plt

    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    # mAP vs tolerance
    map_by_tol = []
    for tol in tolerances:
        vals = [r["ap"] for r in ap_rows if float(r["tolerance_sec"]) == float(tol) and not math.isnan(float(r["ap"]))]
        map_by_tol.append(float(np.mean(vals)) if vals else float("nan"))

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.plot(tolerances, map_by_tol, marker="o")
    ax.set_xlabel("Tolérance temporelle (s)")
    ax.set_ylabel("mAP")
    ax.set_title("mAP en fonction de la tolérance temporelle")
    ax.set_ylim(0, 1)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(plots_dir / "map_vs_tolerance.png", dpi=180)
    plt.close(fig)

    # AP heatmap
    mat = np.full((len(classes), len(tolerances)), np.nan, dtype=np.float32)
    for i, cls in enumerate(classes):
        for j, tol in enumerate(tolerances):
            vals = [r["ap"] for r in ap_rows if r["class"] == cls and float(r["tolerance_sec"]) == float(tol)]
            if vals:
                mat[i, j] = vals[0]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    im = ax.imshow(mat, aspect="auto", vmin=0, vmax=1)
    ax.set_xticks(np.arange(len(tolerances)))
    ax.set_xticklabels([f"{t:g}s" for t in tolerances])
    ax.set_yticks(np.arange(len(classes)))
    ax.set_yticklabels(classes)
    ax.set_xlabel("Tolérance")
    ax.set_title("AP par classe et par tolérance")
    for i in range(len(classes)):
        for j in range(len(tolerances)):
            val = mat[i, j]
            if not np.isnan(val):
                ax.text(j, i, f"{val:.2f}", ha="center", va="center")
    fig.colorbar(im, ax=ax, label="AP")
    fig.tight_layout()
    fig.savefig(plots_dir / "ap_heatmap.png", dpi=180)
    plt.close(fig)

    # F1/Precision/Recall at smallest or 10s tolerance
    target_tol = 10.0 if 10.0 in [float(t) for t in tolerances] else float(tolerances[0])
    rows_tol = [r for r in point_rows if float(r["tolerance_sec"]) == target_tol]
    x = np.arange(len(classes))
    precision = [next((r["precision"] for r in rows_tol if r["class"] == c), 0.0) for c in classes]
    recall = [next((r["recall"] for r in rows_tol if r["class"] == c), 0.0) for c in classes]
    f1 = [next((r["f1"] for r in rows_tol if r["class"] == c), 0.0) for c in classes]

    fig, ax = plt.subplots(figsize=(9, 4.8))
    width = 0.25
    ax.bar(x - width, precision, width, label="Précision")
    ax.bar(x, recall, width, label="Rappel")
    ax.bar(x + width, f1, width, label="F1")
    ax.set_xticks(x)
    ax.set_xticklabels(classes, rotation=20, ha="right")
    ax.set_ylim(0, 1)
    ax.set_ylabel("Score")
    ax.set_title(f"Précision / rappel / F1 à ±{target_tol:g}s")
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(plots_dir / f"precision_recall_f1_{target_tol:g}s.png", dpi=180)
    plt.close(fig)

    # Counts by class
    gt_counts = [next((r["gt"] for r in rows_tol if r["class"] == c), 0) for c in classes]
    pred_counts = [next((r["pred"] for r in rows_tol if r["class"] == c), 0) for c in classes]
    tp_counts = [next((r["tp"] for r in rows_tol if r["class"] == c), 0) for c in classes]
    fig, ax = plt.subplots(figsize=(9, 4.8))
    width = 0.25
    ax.bar(x - width, gt_counts, width, label="Vérité terrain")
    ax.bar(x, pred_counts, width, label="Prédictions")
    ax.bar(x + width, tp_counts, width, label="Vrais positifs")
    ax.set_xticks(x)
    ax.set_xticklabels(classes, rotation=20, ha="right")
    ax.set_ylabel("Nombre")
    ax.set_title(f"Nombre d'événements par classe à ±{target_tol:g}s")
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(plots_dir / f"counts_by_class_{target_tol:g}s.png", dpi=180)
    plt.close(fig)

    # PR curves at target tolerance
    fig, ax = plt.subplots(figsize=(7, 5))
    for cls in classes:
        rows = [r for r in pr_rows if r["class"] == cls and float(r["tolerance_sec"]) == target_tol]
        if not rows:
            continue
        ax.plot([r["recall"] for r in rows], [r["precision"] for r in rows], label=cls)
    ax.set_xlabel("Rappel")
    ax.set_ylabel("Précision")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_title(f"Courbes précision-rappel à ±{target_tol:g}s")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(plots_dir / f"pr_curves_{target_tol:g}s.png", dpi=180)
    plt.close(fig)

    # Temporal error histogram
    if errors:
        fig, ax = plt.subplots(figsize=(7, 4.5))
        ax.hist(errors, bins=20)
        ax.set_xlabel("Erreur temporelle absolue (s)")
        ax.set_ylabel("Nombre de prédictions appariées")
        ax.set_title(f"Distribution des erreurs temporelles à ±{target_tol:g}s")
        ax.grid(True, axis="y", alpha=0.3)
        fig.tight_layout()
        fig.savefig(plots_dir / f"temporal_error_hist_{target_tol:g}s.png", dpi=180)
        plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Évalue Dense Anchor Spotter sur un dossier SoccerNet et génère graphes + métriques.")
    parser.add_argument("--checkpoint", required=True, help="Chemin vers best.pt ou last.pt")
    parser.add_argument("--root", required=True, help="Racine SoccerNet ou split de validation")
    parser.add_argument("--output-dir", default="runs/dense_anchor/eval")
    parser.add_argument("--split-file", default=None, help="Optionnel : fichier texte listant les matchs à évaluer")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--limit-games", type=int, default=None)
    parser.add_argument("--score-threshold", type=float, default=0.05, help="Seuil bas recommandé pour AP/mAP.")
    parser.add_argument("--nms-radius-sec", type=float, default=None)
    parser.add_argument("--use-soft-nms", action="store_true")
    parser.add_argument("--tolerances", nargs="+", type=float, default=[5, 10, 20, 30, 60])
    parser.add_argument("--classes", nargs="+", default=None)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    device = get_device(args.device)
    checkpoint = torch.load(args.checkpoint, map_location=device)
    cfg = checkpoint["config"]
    classes = args.classes or list(checkpoint.get("classes", cfg["data"]["classes"]))
    model = build_model(cfg).to(device)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()

    root = Path(args.root)
    games = find_game_dirs(root, args.split_file)
    if args.limit_games is not None:
        games = games[: args.limit_games]
    if not games:
        raise RuntimeError(f"Aucun match SoccerNet trouvé sous {root}")

    data_cfg = cfg["data"]
    post_cfg = dict(cfg.get("postprocess", {}))
    post_cfg["score_threshold"] = float(args.score_threshold)
    if args.nms_radius_sec is not None:
        post_cfg["nms_radius_sec"] = float(args.nms_radius_sec)
    if args.use_soft_nms:
        post_cfg["use_soft_nms"] = True

    feature_fps = float(data_cfg.get("feature_fps", 2.0))
    window_size_sec = float(data_cfg.get("window_size_sec", 120.0))
    stride_sec = float(data_cfg.get("stride_sec", 60.0))

    all_predictions: list[dict] = []
    all_targets: list[dict] = []

    skipped_missing_labels = 0
    skipped_missing_features = 0
    skipped_partial_halves = 0
    evaluated_games = 0

    for game_dir in tqdm(games, desc="Évaluation des matchs"):
        game_id = safe_relpath(game_dir, root)

        labels_path = game_dir / "Labels-v2.json"
        if not labels_path.exists():
            skipped_missing_labels += 1
            print(f"[WARN] Labels-v2.json absent, match ignoré : {game_id}")
            continue

        feature_paths: dict[int, Path] = {}
        for half in (1, 2):
            fpath = find_feature_file(game_dir, half)
            if fpath is None:
                skipped_partial_halves += 1
                print(f"[WARN] Pas de features pour {game_id}, mi-temps {half}. Cette mi-temps est ignorée.")
                continue
            feature_paths[half] = fpath

        if not feature_paths:
            skipped_missing_features += 1
            print(f"[WARN] Aucune feature disponible, match ignoré : {game_id}")
            continue

        evaluated_games += 1

        # Targets : on ne conserve que les mi-temps qui ont des features.
        # Sinon, les événements d'une mi-temps absente seraient comptés comme faux négatifs.
        for e in load_events_from_labels(labels_path, classes):
            if int(e.half) not in feature_paths:
                continue
            all_targets.append(
                {
                    "game": game_id,
                    "half": int(e.half),
                    "time_sec": float(e.time_sec),
                    "label": e.label,
                    "visibility": e.visibility,
                }
            )

        # Predictions
        raw_preds: list[Prediction] = []
        for half, fpath in feature_paths.items():
            features = load_features(fpath)
            raw_preds.extend(
                predict_half(
                    model=model,
                    features=features,
                    classes=classes,
                    half=half,
                    feature_fps=feature_fps,
                    window_size_sec=window_size_sec,
                    stride_sec=stride_sec,
                    post_cfg=post_cfg,
                    device=device,
                )
            )

        final_preds = nms_predictions(
            raw_preds,
            classes=classes,
            radius_sec=float(post_cfg.get("nms_radius_sec", 6.0)),
            score_threshold=float(post_cfg.get("score_threshold", 0.05)),
            max_predictions_per_class=int(post_cfg.get("max_predictions_per_class", 200)),
            use_soft_nms=bool(post_cfg.get("use_soft_nms", False)),
        )

        for p in final_preds:
            d = p.to_dict()
            d["game"] = game_id
            all_predictions.append(d)

    # Save raw data
    (output_dir / "predictions_all.json").write_text(json.dumps(all_predictions, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "targets_all.json").write_text(json.dumps(all_targets, indent=2, ensure_ascii=False), encoding="utf-8")

    # AP / mAP
    ap_rows: list[dict] = []
    pr_rows: list[dict] = []
    map_by_tol: dict[str, float] = {}

    for tol in args.tolerances:
        aps = []
        for cls in classes:
            ap, curve = ap_for_class(all_predictions, all_targets, cls, tol)
            ap_rows.append({"class": cls, "tolerance_sec": tol, "ap": ap})
            pr_rows.extend(curve)
            if not math.isnan(ap):
                aps.append(ap)
        map_by_tol[f"mAP@{tol:g}s"] = float(np.mean(aps)) if aps else float("nan")

    avg_map = float(np.mean([v for v in map_by_tol.values() if not math.isnan(v)])) if map_by_tol else float("nan")

    # Point metrics at all tolerances
    point_rows: list[dict] = []
    all_errors_for_target_tol: list[float] = []
    target_tol = 10.0 if 10.0 in [float(t) for t in args.tolerances] else float(args.tolerances[0])
    for tol in args.tolerances:
        rows, errors = detection_metrics_at_tolerance(all_predictions, all_targets, classes, tol)
        point_rows.extend(rows)
        if float(tol) == target_tol:
            all_errors_for_target_tol = errors

    summary = {
        "num_games_found": len(games),
        "num_games_evaluated": evaluated_games,
        "num_games_skipped_missing_labels": skipped_missing_labels,
        "num_games_skipped_missing_features": skipped_missing_features,
        "num_missing_halves_skipped": skipped_partial_halves,
        "num_targets": len(all_targets),
        "num_predictions": len(all_predictions),
        "classes": classes,
        "score_threshold": float(args.score_threshold),
        "nms_radius_sec": float(post_cfg.get("nms_radius_sec", 6.0)),
        "use_soft_nms": bool(post_cfg.get("use_soft_nms", False)),
        **map_by_tol,
        "avg_mAP": avg_map,
        f"mean_temporal_error@{target_tol:g}s": float(np.mean(all_errors_for_target_tol)) if all_errors_for_target_tol else float("nan"),
    }

    (output_dir / "metrics_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    write_csv(output_dir / "ap_by_class.csv", ap_rows)
    write_csv(output_dir / "precision_recall_f1_by_class.csv", point_rows)
    write_csv(output_dir / "pr_curves.csv", pr_rows)

    plot_metrics(output_dir, classes, args.tolerances, ap_rows, point_rows, pr_rows, all_errors_for_target_tol)

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\nFichiers générés dans : {output_dir.resolve()}")


if __name__ == "__main__":
    main()
