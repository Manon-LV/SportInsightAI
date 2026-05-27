from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from sportinsight.data import SoccerNetDenseAnchorDataset, dense_anchor_collate
from sportinsight.losses import AsymmetricLoss, DenseAnchorLoss, OHEMLoss, build_loss
from sportinsight.model import DenseAnchorSpotter, build_model
from sportinsight.postprocess import nms_predictions, predictions_from_window


CLASSES = ["Goal", "Corner", "Yellow card", "Red card"]


def create_synthetic_game(root: Path) -> Path:
    game_dir = root / "synthetic_league" / "2026" / "game_001"
    game_dir.mkdir(parents=True)
    fps = 2.0
    T = int(8 * 60 * fps)
    D = 512
    rng = np.random.default_rng(42)
    for half in (1, 2):
        x = rng.normal(0, 0.2, size=(T, D)).astype(np.float32)
        if half == 1:
            x[int(75 * fps):int(80 * fps), :16] += 2.0
            x[int(210 * fps):int(215 * fps), 16:32] += 2.0
        if half == 2:
            x[int(150 * fps):int(155 * fps), 32:48] += 2.0
        np.save(game_dir / f"{half}_ResNET_PCA512.npy", x)

    labels = {
        "annotations": [
            {"gameTime": "1 - 01:17", "label": "Corner",      "position": "77000",  "visibility": "shown"},
            {"gameTime": "1 - 03:32", "label": "Goal",        "position": "212000", "visibility": "shown"},
            {"gameTime": "2 - 02:32", "label": "Yellow card", "position": "152000", "visibility": "shown"},
        ]
    }
    with open(game_dir / "Labels-v2.json", "w", encoding="utf-8") as f:
        json.dump(labels, f)
    return game_dir


def _make_model() -> DenseAnchorSpotter:
    return DenseAnchorSpotter(
        input_dim=512, hidden_dim=64, num_classes=len(CLASSES),
        num_layers=2, dropout=0.1,
    )


def _forward_backward(model, criterion, batch):
    optim = torch.optim.AdamW(model.parameters(), lr=1e-3)
    outputs = model(batch["x"])
    losses = criterion(outputs, batch)
    losses["loss"].backward()
    optim.step()
    return losses, outputs


def check_dataset(tmp: Path, strategy: str) -> int:
    ds = SoccerNetDenseAnchorDataset(
        root=tmp,
        classes=CLASSES,
        feature_fps=2.0,
        window_size_sec=60.0,
        stride_sec=30.0,
        positive_radius_sec=2.0,
        ignore_radius_sec=5.0,
        imbalance_strategy=strategy,
        neg_pos_ratio=2.0,
    )
    assert len(ds) > 0, f"strategy={strategy}: dataset vide"
    _ = ds[0]
    return len(ds)


def check_loss(loss_cls, batch):
    model = _make_model()
    losses, _ = _forward_backward(model, loss_cls, batch)
    val = float(losses["loss"].detach())
    assert val >= 0.0 and not (val != val), f"loss invalide: {val}"
    return val


def main() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="sportinsight_sanity_"))
    ok = True
    try:
        create_synthetic_game(tmp)

        # ── Dataset strategies ─────────────────────────────────────────────
        print("\n[1/3] Dataset - strategies de sampling")
        for strat in ("none", "downsample", "oversample"):
            n = check_dataset(tmp, strat)
            print(f"  {strat:<12} -> {n} windows  OK")

        # ── Loss types ─────────────────────────────────────────────────────
        print("\n[2/3] Loss types (focal / ohem / asl)")
        ds = SoccerNetDenseAnchorDataset(
            root=tmp, classes=CLASSES, feature_fps=2.0,
            window_size_sec=60.0, stride_sec=30.0,
            positive_radius_sec=2.0, ignore_radius_sec=5.0,
        )
        batch = dense_anchor_collate([ds[0], ds[1]])

        losses_to_test = [
            ("focal",      DenseAnchorLoss(class_weights=[1.0, 1.0, 1.5, 3.0], focal_gamma=2.0)),
            ("ohem",       OHEMLoss(ohem_ratio=0.25, class_weights=[1.0, 1.0, 1.5, 3.0], focal_gamma=2.0)),
            ("asl",        AsymmetricLoss(gamma_pos=1.0, gamma_neg=4.0, prob_shift=0.05, class_weights=[1.0, 1.0, 1.5, 3.0])),
        ]
        for name, criterion in losses_to_test:
            v = check_loss(criterion, batch)
            print(f"  {name:<12} -> loss={v:.4f}  OK")

        # ── build_loss factory ─────────────────────────────────────────────
        print("\n[3/3] build_loss factory (dispatch par config)")
        for t in ("focal", "ohem", "asl"):
            cfg = {
                "loss": {"type": t, "focal_gamma": 2.0, "ohem_ratio": 0.25,
                         "gamma_pos": 1.0, "gamma_neg": 4.0, "prob_shift": 0.05,
                         "lambda_cls": 1.0, "lambda_reg": 0.5,
                         "class_weights": [1.0, 1.0, 1.5, 3.0]}
            }
            criterion = build_loss(cfg)
            v = check_loss(criterion, batch)
            print(f"  type={t:<8} -> loss={v:.4f}  OK")

        # ── build_model factory (projection on/off) ────────────────────────
        print("\n[bonus] build_model - projection on/off")
        for use_proj in (True, False):
            cfg = {
                "data": {"classes": CLASSES},
                "model": {"input_dim": 512, "hidden_dim": 64, "num_layers": 2,
                          "dropout": 0.1, "backbone": "unet", "max_offset_sec": 5.0,
                          "use_projection": use_proj},
            }
            model = build_model(cfg)
            out = model(batch["x"])
            assert out["cls_logits"].shape == (2, batch["x"].shape[1], len(CLASSES))
            label = "avec proj" if use_proj else "sans proj"
            print(f"  {label}  OK")

        print("\n" + "=" * 50)
        print("Sanity check complet - tous les tests OK")

    except Exception as exc:
        ok = False
        print(f"\n[ERREUR] {exc}")
        raise
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        if ok:
            print("Fichiers temporaires supprimés")


if __name__ == "__main__":
    main()
