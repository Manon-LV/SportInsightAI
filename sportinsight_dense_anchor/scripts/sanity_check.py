from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
import torch

# Allow running from the repository without installation.
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from sportinsight.data import SoccerNetDenseAnchorDataset, dense_anchor_collate
from sportinsight.losses import DenseAnchorLoss
from sportinsight.model import DenseAnchorSpotter
from sportinsight.postprocess import nms_predictions, predictions_from_window


def create_synthetic_game(root: Path) -> Path:
    game_dir = root / "synthetic_league" / "2026" / "game_001"
    game_dir.mkdir(parents=True)
    fps = 2.0
    T = int(8 * 60 * fps)
    D = 512
    rng = np.random.default_rng(42)
    for half in (1, 2):
        x = rng.normal(0, 0.2, size=(T, D)).astype(np.float32)
        # Inject simple patterns around fake events.
        if half == 1:
            x[int(75 * fps):int(80 * fps), :16] += 2.0     # Corner
            x[int(210 * fps):int(215 * fps), 16:32] += 2.0 # Goal
        if half == 2:
            x[int(150 * fps):int(155 * fps), 32:48] += 2.0 # Yellow card
        np.save(game_dir / f"{half}_ResNET_PCA512.npy", x)

    labels = {
        "annotations": [
            {"gameTime": "1 - 01:17", "label": "Corner", "position": "77000", "visibility": "shown"},
            {"gameTime": "1 - 03:32", "label": "Goal", "position": "212000", "visibility": "shown"},
            {"gameTime": "2 - 02:32", "label": "Yellow card", "position": "152000", "visibility": "shown"},
        ]
    }
    with open(game_dir / "Labels-v2.json", "w", encoding="utf-8") as f:
        json.dump(labels, f)
    return game_dir


def main() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="sportinsight_sanity_"))
    try:
        create_synthetic_game(tmp)
        classes = ["Goal", "Corner", "Yellow card", "Red card"]
        ds = SoccerNetDenseAnchorDataset(
            root=tmp,
            classes=classes,
            feature_fps=2.0,
            window_size_sec=60.0,
            stride_sec=30.0,
            positive_radius_sec=2.0,
            ignore_radius_sec=5.0,
        )
        batch = dense_anchor_collate([ds[0], ds[1]])
        model = DenseAnchorSpotter(input_dim=512, hidden_dim=64, num_classes=len(classes), num_layers=2, dropout=0.1)
        criterion = DenseAnchorLoss(class_weights=[1.0, 1.0, 1.5, 3.0])
        optim = torch.optim.AdamW(model.parameters(), lr=1e-3)

        outputs = model(batch["x"])
        losses = criterion(outputs, batch)
        losses["loss"].backward()
        optim.step()

        raw = []
        for i, meta in enumerate(batch["meta"]):
            raw.extend(
                predictions_from_window(
                    outputs["cls_logits"][i],
                    outputs["offsets"][i],
                    classes=classes,
                    half=meta["half"],
                    start_time_sec=meta["start_time_sec"],
                    feature_fps=2.0,
                    score_threshold=0.05,
                )
            )
        final = nms_predictions(raw, classes=classes, radius_sec=6.0, score_threshold=0.05)

        print("Sanity check OK")
        print(f"Dataset windows: {len(ds)}")
        print(f"Batch x shape: {tuple(batch['x'].shape)}")
        print(f"Loss: {float(losses['loss'].detach()):.4f} | cls={float(losses['loss_cls'].detach()):.4f} | reg={float(losses['loss_reg'].detach()):.4f}")
        print(f"Raw predictions: {len(raw)} | after NMS: {len(final)}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        print("Temporary files removed")


if __name__ == "__main__":
    main()
