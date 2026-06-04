"""Évaluation officielle SoccerNet sur le test set (100 matchs).

Calcule loose avg-mAP et tight avg-mAP via :
  1. Notre implémentation interne (temporal_map)
  2. L'API officielle SoccerNet (SoccerNet.Evaluation.ActionSpotting.evaluate)

Usage :
    python scripts/evaluate_test_official.py --checkpoint runs/calf_17_slim_tdrop_sam/best_map.pt
    python scripts/evaluate_test_official.py --checkpoint runs/calf_17_slim_tdrop_sam/best_map.pt --output-dir /tmp/eval_preds
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import torch
from tqdm import tqdm

from sportinsight.data import find_feature_file, load_features
from sportinsight.infer import predict_half
from sportinsight.labels import load_events_from_labels
from sportinsight.metrics import temporal_map, LOOSE_TOLERANCES, TIGHT_TOLERANCES
from sportinsight.model import build_model
from sportinsight.postprocess import nms_predictions
from sportinsight.utils import get_device

from SoccerNet.utils import getListGames
from SoccerNet.Evaluation.ActionSpotting import evaluate as soccernet_evaluate


def load_checkpoint(checkpoint_path: str, device_name: str = "auto"):
    device = get_device(device_name)
    ckpt = torch.load(checkpoint_path, map_location=device)
    cfg = ckpt["config"]
    classes = list(ckpt.get("classes", cfg["data"]["classes"]))
    model = build_model(cfg).to(device)
    model.load_state_dict(ckpt["model_state"])
    model.eval()
    return model, cfg, classes, device


def run_inference_on_game(model, game_dir: Path, cfg: dict, classes: list, device):
    data_cfg = cfg["data"]
    post_cfg = dict(cfg.get("postprocess", {}))
    post_cfg["score_threshold"] = 0.01  # seuil bas pour courbe PR complète

    feature_fps    = float(data_cfg.get("feature_fps", 2.0))
    window_size_sec = float(data_cfg.get("window_size_sec", 120.0))
    stride_sec     = float(data_cfg.get("stride_sec", 60.0))
    nms_radius     = float(cfg.get("postprocess", {}).get("nms_radius_sec", 6.0))
    max_preds      = int(cfg.get("postprocess", {}).get("max_predictions_per_class", 200))

    raw = []
    for half_idx in (1, 2):
        fpath = find_feature_file(game_dir, half_idx)
        if fpath is None:
            continue
        features = load_features(fpath)
        raw.extend(predict_half(
            model, features, classes=classes, half=half_idx,
            feature_fps=feature_fps, window_size_sec=window_size_sec,
            stride_sec=stride_sec, post_cfg=post_cfg, device=device,
        ))

    return nms_predictions(
        raw, classes=classes,
        radius_sec=nms_radius,
        score_threshold=0.0,
        max_predictions_per_class=max_preds,
    )


def predictions_to_soccernet_json(predictions) -> dict:
    """Convertit nos prédictions au format attendu par SoccerNet.Evaluation."""
    return {
        "predictions": [
            {
                "position": int(p.timestamp * 1000),   # secondes → millisecondes
                "half": p.half,
                "label": p.label,
                "confidence": float(p.score),
            }
            for p in predictions
        ]
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True, help="Chemin vers best_map.pt")
    parser.add_argument("--output-dir", default=None,
                        help="Dossier où sauvegarder les prédictions JSON (défaut: temp)")
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()

    ckpt_path = Path(args.checkpoint)
    print(f"Checkpoint : {ckpt_path}")
    model, cfg, classes, device = load_checkpoint(str(ckpt_path), args.device)
    print(f"Device     : {device}")
    print(f"Classes    : {len(classes)} — {classes}")

    data_root = Path(cfg["data"]["root"])
    test_games = getListGames(split="test")

    # Dossier de sortie pour les prédictions
    use_temp = args.output_dir is None
    out_dir = Path(tempfile.mkdtemp(prefix="sn_eval_")) if use_temp else Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Prédictions → {out_dir}")

    all_preds = []
    all_events = []
    games_processed = 0

    print(f"\nInférence sur {len(test_games)} matchs test...")
    for game_path in tqdm(test_games):
        game_dir = data_root / game_path
        feat1 = find_feature_file(game_dir, 1)
        feat2 = find_feature_file(game_dir, 2)
        if feat1 is None and feat2 is None:
            continue

        with torch.no_grad():
            preds = run_inference_on_game(model, game_dir, cfg, classes, device)

        # Sauvegarde au format SoccerNet
        pred_file = out_dir / game_path / "results_spotting.json"
        pred_file.parent.mkdir(parents=True, exist_ok=True)
        pred_file.write_text(
            json.dumps(predictions_to_soccernet_json(preds), indent=2),
            encoding="utf-8",
        )

        all_preds.extend(preds)

        labels_path = game_dir / "Labels-v2.json"
        if labels_path.exists():
            all_events.extend(load_events_from_labels(labels_path, classes))

        games_processed += 1

    print(f"\nMatchs traités : {games_processed}/{len(test_games)}")

    # ── Métriques internes ──────────────────────────────────────────────────
    print("\n=== Métriques internes (temporal_map) ===")
    loose = temporal_map(all_preds, all_events, classes=classes, tolerances_sec=LOOSE_TOLERANCES)
    tight = temporal_map(all_preds, all_events, classes=classes, tolerances_sec=TIGHT_TOLERANCES)

    print(f"Loose avg-mAP : {loose['avg_mAP']*100:.2f}%")
    print(f"Tight avg-mAP : {tight['avg_mAP']*100:.2f}%")
    print(f"\nAP@5s par classe (loose) :")
    for c in classes:
        ap5  = loose.get(f"AP@5s/{c}", 0)
        ap1  = tight.get(f"AP@1s/{c}", 0)
        print(f"  {c:<26} loose@5s={ap5*100:>6.1f}%   tight@1s={ap1*100:>6.1f}%")

    # ── API officielle SoccerNet ────────────────────────────────────────────
    print("\n=== API officielle SoccerNet ===")
    try:
        res_loose = soccernet_evaluate(
            SoccerNet_path=str(data_root),
            Predictions_path=str(out_dir),
            split="test",
            version=2,
            framerate=2,
            metric="loose",
        )
        res_tight = soccernet_evaluate(
            SoccerNet_path=str(data_root),
            Predictions_path=str(out_dir),
            split="test",
            version=2,
            framerate=2,
            metric="tight",
        )
        print(f"Loose avg-mAP (officiel) : {res_loose['a_mAP']*100:.2f}%")
        print(f"Tight avg-mAP (officiel) : {res_tight['a_mAP']*100:.2f}%")
        if "a_mAP_per_class" in res_loose:
            from SoccerNet.Evaluation.ActionSpotting import EVENT_DICTIONARY_V2
            inv = {v: k for k, v in EVENT_DICTIONARY_V2.items()}
            print("\nAP par classe (loose officiel) :")
            for idx, ap in enumerate(res_loose["a_mAP_per_class"]):
                label = inv.get(idx, f"class_{idx}")
                print(f"  {label:<26} {ap*100:>6.1f}%")
    except Exception as e:
        print(f"[WARN] API officielle indisponible : {e}")

    # ── Sauvegarde résultats ────────────────────────────────────────────────
    results = {
        "checkpoint": str(ckpt_path),
        "games_processed": games_processed,
        "internal": {
            "loose_avg_mAP": loose["avg_mAP"],
            "tight_avg_mAP": tight["avg_mAP"],
            "loose_per_class_ap5s": {c: loose.get(f"AP@5s/{c}", 0) for c in classes},
            "tight_per_class_ap1s": {c: tight.get(f"AP@1s/{c}", 0) for c in classes},
        },
    }
    results_path = ckpt_path.parent / "test_eval_results.json"
    results_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nRésultats sauvegardés → {results_path}")


if __name__ == "__main__":
    main()
