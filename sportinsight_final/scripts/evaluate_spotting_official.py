"""Évalue un checkpoint SportInsight avec la métrique officielle SoccerNet (Avg-mAP).

Le script :
  1. Charge le checkpoint et tourne l'inférence sur les matchs du split.
  2. Sauvegarde les prédictions au format SoccerNet (results_spotting.json par match).
  3. Appelle SoccerNet.Evaluation.ActionSpotting.evaluate pour loose et tight.
  4. Affiche et sauvegarde les résultats.

Utilisation :
    python scripts/evaluate_spotting_official.py \\
        --checkpoint runs/final/best.pt \\
        --root data/SoccerNet \\
        --split-file splits/test.txt

    # Avec options
    python scripts/evaluate_spotting_official.py \\
        --checkpoint runs/final/best.pt \\
        --root data/SoccerNet \\
        --split-file splits/valid.txt \\
        --predictions-dir runs/final/predictions_valid \\
        --score-threshold 0.25
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from tqdm import tqdm
from SoccerNet.Evaluation.ActionSpotting import evaluate as sn_evaluate
from SoccerNet.utils import getListGames

from sportinsight.data import find_feature_file, load_features
from sportinsight.infer import load_checkpoint_model, predict_half
from sportinsight.postprocess import nms_predictions


def _infer_game(model, cfg, classes, device, game_dir: Path, post_cfg: dict) -> list:
    feature_fps = float(cfg["data"].get("feature_fps", 2.0))
    window_size_sec = float(cfg["data"].get("window_size_sec", 120.0))
    stride_sec = float(cfg["data"].get("stride_sec", 60.0))

    raw = []
    for half_idx in (1, 2):
        fpath = find_feature_file(game_dir, half_idx)
        if fpath is None:
            continue
        feats = load_features(fpath)
        raw.extend(predict_half(
            model, feats, classes=classes, half=half_idx,
            feature_fps=feature_fps, window_size_sec=window_size_sec,
            stride_sec=stride_sec, post_cfg=post_cfg, device=device,
        ))

    return nms_predictions(
        raw, classes=classes,
        radius_sec=float(post_cfg.get("nms_radius_sec", 6.0)),
        score_threshold=float(post_cfg.get("score_threshold", 0.3)),
        max_predictions_per_class=int(post_cfg.get("max_predictions_per_class", 200)),
        use_soft_nms=bool(post_cfg.get("use_soft_nms", False)),
    )


def _write_soccernet_predictions(preds, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"predictions": [p.to_soccernet_dict() for p in preds]}
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _relative_posix(game_dir: Path, root: Path) -> str:
    try:
        return game_dir.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return game_dir.as_posix()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Évaluation officielle SoccerNet Avg-mAP pour un checkpoint SportInsight."
    )
    parser.add_argument("--checkpoint", required=True, help="Chemin vers best.pt ou last.pt")
    parser.add_argument("--root", default="data/SoccerNet", help="Racine SoccerNet (labels + features)")
    parser.add_argument(
        "--split-file", default="splits/test.txt",
        help="Fichier de split à évaluer (défaut: splits/test.txt)",
    )
    parser.add_argument(
        "--predictions-dir", default=None,
        help="Dossier de sortie pour les JSON de prédiction (défaut: <runs_dir>/predictions_<split_name>)",
    )
    parser.add_argument("--device", default="auto")
    parser.add_argument("--score-threshold", type=float, default=None)
    parser.add_argument("--nms-radius-sec", type=float, default=None)
    parser.add_argument(
        "--force-regen", action="store_true",
        help="Recalcule les prédictions même si elles existent déjà",
    )
    parser.add_argument(
        "--metrics", nargs="+", default=["loose", "tight"],
        choices=["loose", "tight", "at1", "at2", "at3", "at4", "at5"],
        help="Métriques à calculer (défaut: loose tight)",
    )
    args = parser.parse_args()

    checkpoint = Path(args.checkpoint)
    root = Path(args.root)
    split_file = Path(args.split_file)

    if args.predictions_dir is None:
        split_name = split_file.stem
        predictions_dir = checkpoint.parent / f"predictions_{split_name}"
    else:
        predictions_dir = Path(args.predictions_dir)
    predictions_dir.mkdir(parents=True, exist_ok=True)

    # ── Chargement du modèle ─────────────────────────────────────────────────
    print(f"Chargement du modèle depuis {checkpoint}...")
    model, cfg, classes, device = load_checkpoint_model(str(checkpoint), args.device)
    print(f"  Classes ({len(classes)}): {classes}")
    print(f"  Device : {device}")

    post_cfg = dict(cfg.get("postprocess", {}))
    if args.score_threshold is not None:
        post_cfg["score_threshold"] = args.score_threshold
    if args.nms_radius_sec is not None:
        post_cfg["nms_radius_sec"] = args.nms_radius_sec

    # ── Chargement de la liste des matchs ─────────────────────────────────────
    from sportinsight.data import find_game_dirs
    game_dirs = find_game_dirs(root, split_file=split_file)
    print(f"Matchs à évaluer : {len(game_dirs)}")

    # ── Inférence par match ───────────────────────────────────────────────────
    n_skipped = 0
    for game_dir in tqdm(game_dirs, desc="inférence"):
        rel_posix = _relative_posix(game_dir, root)
        out_file = predictions_dir / rel_posix / "results_spotting.json"

        if out_file.exists() and not args.force_regen:
            n_skipped += 1
            continue

        preds = _infer_game(model, cfg, classes, device, game_dir, post_cfg)
        _write_soccernet_predictions(preds, out_file)

    if n_skipped:
        print(f"  ({n_skipped} matchs déjà prédits — utilise --force-regen pour recalculer)")

    # ── Évaluation officielle SoccerNet ───────────────────────────────────────
    # On utilise le split officiel SoccerNet correspondant au split_file.
    # La liste dans getListGames et nos prédictions partagent la même structure de dossiers.
    official_split = split_file.stem  # "test", "valid", "train"
    if official_split not in ("test", "valid", "train", "challenge"):
        official_split = "test"
        print(f"[WARN] Split '{split_file.stem}' inconnu pour SoccerNet, on utilise 'test'.")

    event_dict = {cls: i for i, cls in enumerate(classes)}

    print(f"\nÉvaluation officielle SoccerNet (split={official_split})...")
    results: dict = {}
    for metric in args.metrics:
        print(f"  Métrique : {metric}...")
        r = sn_evaluate(
            SoccerNet_path=str(root),
            Predictions_path=str(predictions_dir),
            prediction_file="results_spotting.json",
            split=official_split,
            version=2,
            framerate=2,
            metric=metric,
            dataset="SoccerNet",
            EVENT_DICTIONARY=event_dict,
        )
        results[metric] = r
        a_map = r["a_mAP"]
        print(f"    Avg-mAP ({metric:5s}) : {a_map * 100:.2f}%")
        if r.get("a_mAP_per_class"):
            for cls, ap in zip(classes, r["a_mAP_per_class"]):
                mark = " ←" if ap == max(r["a_mAP_per_class"]) else ""
                print(f"      {cls:<25} {ap * 100:.1f}%{mark}")

    # ── Sauvegarde des résultats ──────────────────────────────────────────────
    eval_out = predictions_dir / "evaluation_results.json"
    eval_out.write_text(
        json.dumps(
            {
                "checkpoint": str(checkpoint),
                "split_file": str(split_file),
                "official_split": official_split,
                "n_games": len(game_dirs),
                "classes": classes,
                "post_cfg": post_cfg,
                "results": {
                    metric: {
                        "a_mAP": r["a_mAP"],
                        "a_mAP_per_class": dict(zip(classes, r.get("a_mAP_per_class") or [])),
                        "a_mAP_visible": r.get("a_mAP_visible"),
                        "a_mAP_unshown": r.get("a_mAP_unshown"),
                    }
                    for metric, r in results.items()
                },
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(f"\nRésultats sauvegardés → {eval_out}")
    print("\n=== RÉSUMÉ ===")
    for metric, r in results.items():
        print(f"  Avg-mAP ({metric:5s}) : {r['a_mAP'] * 100:.2f}%")


if __name__ == "__main__":
    main()
