from __future__ import annotations

import argparse
import math
from pathlib import Path

import torch
from torch.utils.data import DataLoader, Subset
from tqdm import tqdm

from .data import SoccerNetDenseAnchorDataset, dense_anchor_collate
from .losses import build_loss
from .model import build_model
from .splits import validate_disjoint_splits
from .utils import get_device, load_config, save_json, set_seed
from .visualization import plot_training_history, save_history_csv


def move_batch_to_device(batch: dict, device: torch.device) -> dict:
    out = {}
    for key, value in batch.items():
        out[key] = value.to(device) if torch.is_tensor(value) else value
    return out


@torch.no_grad()
def validate_loss(model, criterion, loader, device: torch.device) -> dict[str, float]:
    model.eval()
    running = {"val_loss": 0.0, "val_loss_cls": 0.0, "val_loss_reg": 0.0}
    steps = 0
    for batch in tqdm(loader, desc="validation", leave=False):
        batch = move_batch_to_device(batch, device)
        outputs = model(batch["x"])
        losses = criterion(outputs, batch)
        running["val_loss"] += float(losses["loss"].detach().cpu())
        running["val_loss_cls"] += float(losses["loss_cls"].detach().cpu())
        running["val_loss_reg"] += float(losses["loss_reg"].detach().cpu())
        steps += 1
    return {k: v / max(1, steps) for k, v in running.items()}


def _dataset_from_config(
    data_cfg: dict,
    classes: list[str],
    split_file: str | None = None,
    seed: int = 42,
    apply_sampling: bool = True,
) -> SoccerNetDenseAnchorDataset:
    strategy = str(data_cfg.get("imbalance_strategy", "none")) if apply_sampling else "none"
    return SoccerNetDenseAnchorDataset(
        root=data_cfg["root"],
        split_file=split_file,
        classes=classes,
        feature_fps=float(data_cfg.get("feature_fps", 2.0)),
        window_size_sec=float(data_cfg.get("window_size_sec", 120.0)),
        stride_sec=float(data_cfg.get("stride_sec", 60.0)),
        positive_radius_sec=float(data_cfg.get("positive_radius_sec", 2.0)),
        ignore_radius_sec=float(data_cfg.get("ignore_radius_sec", 5.0)),
        cache_features=bool(data_cfg.get("cache_features", False)),
        imbalance_strategy=strategy,
        neg_pos_ratio=float(data_cfg.get("neg_pos_ratio", 3.0)),
        rng_seed=seed,
    )


def build_train_val_datasets(data_cfg: dict, classes: list[str], seed: int):
    train_split_file = data_cfg.get("train_split_file")
    val_split_file = data_cfg.get("val_split_file") or data_cfg.get("valid_split_file")
    test_split_file = data_cfg.get("test_split_file")

    if train_split_file and val_split_file:
        integrity = validate_disjoint_splits(
            {
                "train": train_split_file,
                "valid": val_split_file,
                "test": test_split_file,
            }
        )
        if not integrity["is_disjoint"]:
            raise ValueError(f"Les fichiers de split ne sont pas disjoints : {integrity}")

        train_ds = _dataset_from_config(data_cfg, classes, split_file=train_split_file, seed=seed, apply_sampling=True)
        val_ds = _dataset_from_config(data_cfg, classes, split_file=val_split_file, seed=seed, apply_sampling=False)
        split_info = {
            "strategy": "match_split_files",
            "train_split_file": train_split_file,
            "val_split_file": val_split_file,
            "test_split_file": test_split_file,
            "integrity": integrity,
            "train_windows": len(train_ds),
            "val_windows": len(val_ds),
            "train_games": len(train_ds.game_dirs),
            "val_games": len(val_ds.game_dirs),
        }
        return train_ds, val_ds, split_info

    # Fallback historique : pratique pour debugger, mais pas un protocole d'évaluation final.
    dataset = _dataset_from_config(data_cfg, classes, split_file=data_cfg.get("split_file"), seed=seed)
    n = len(dataset)
    n_val = max(1, int(0.15 * n))
    n_train = n - n_val
    generator = torch.Generator().manual_seed(seed)
    indices = torch.randperm(n, generator=generator).tolist()
    train_ds = Subset(dataset, indices[:n_train])
    val_ds = Subset(dataset, indices[n_train:])
    split_info = {
        "strategy": "window_random_85_15_fallback",
        "warning": "Split par fenêtres utilisé uniquement pour le développement. Pour les métriques finales, utiliser train_split_file et val_split_file.",
        "train_windows": len(train_ds),
        "val_windows": len(val_ds),
        "source_windows": n,
    }
    print(f"[WARN] {split_info['warning']}")
    return train_ds, val_ds, split_info


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    cfg = load_config(args.config)
    data_cfg = cfg["data"]
    train_cfg = cfg["train"]

    seed = int(train_cfg.get("seed", 42))
    set_seed(seed)
    device = get_device(str(train_cfg.get("device", "auto")))
    print(f"Device : {device}" + (f" ({torch.cuda.get_device_name(device)})" if device.type == "cuda" else ""))
    output_dir = Path(train_cfg.get("output_dir", "runs/dense_anchor"))
    output_dir.mkdir(parents=True, exist_ok=True)

    classes = list(data_cfg["classes"])
    train_ds, val_ds, split_info = build_train_val_datasets(data_cfg, classes, seed)
    save_json(split_info, output_dir / "split_info.json")
    print(f"Split utilisé : {split_info}")

    train_loader = DataLoader(
        train_ds,
        batch_size=int(train_cfg.get("batch_size", 16)),
        shuffle=True,
        num_workers=int(train_cfg.get("num_workers", 2)),
        collate_fn=dense_anchor_collate,
        pin_memory=(device.type == "cuda"),
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=int(train_cfg.get("batch_size", 16)),
        shuffle=False,
        num_workers=int(train_cfg.get("num_workers", 2)),
        collate_fn=dense_anchor_collate,
        pin_memory=(device.type == "cuda"),
    )

    model = build_model(cfg).to(device)
    criterion = build_loss(cfg).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(train_cfg.get("lr", 3e-4)),
        weight_decay=float(train_cfg.get("weight_decay", 1e-4)),
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer,
        T_max=int(train_cfg.get("epochs", 30)),
    )

    best_val = math.inf
    history = []

    for epoch in range(1, int(train_cfg.get("epochs", 30)) + 1):
        model.train()
        running = {"loss": 0.0, "loss_cls": 0.0, "loss_reg": 0.0}
        steps = 0
        pbar = tqdm(train_loader, desc=f"epoch {epoch}")
        for batch in pbar:
            batch = move_batch_to_device(batch, device)
            optimizer.zero_grad(set_to_none=True)
            outputs = model(batch["x"])
            losses = criterion(outputs, batch)
            losses["loss"].backward()
            grad_clip = train_cfg.get("grad_clip_norm", 1.0)
            if grad_clip is not None:
                torch.nn.utils.clip_grad_norm_(model.parameters(), float(grad_clip))
            optimizer.step()
            steps += 1
            for key in running:
                running[key] += float(losses[key].detach().cpu())
            pbar.set_postfix({k: f"{running[k] / steps:.4f}" for k in running})
        scheduler.step()

        epoch_log = {k: running[k] / max(1, steps) for k in running}
        epoch_log["epoch"] = epoch
        epoch_log["lr"] = float(scheduler.get_last_lr()[0])

        if epoch % int(train_cfg.get("validate_every", 1)) == 0:
            epoch_log.update(validate_loss(model, criterion, val_loader, device))
            if epoch_log["val_loss"] < best_val:
                best_val = epoch_log["val_loss"]
                torch.save(
                    {
                        "model_state": model.state_dict(),
                        "config": cfg,
                        "classes": classes,
                        "epoch": epoch,
                        "val_loss": best_val,
                        "split_info": split_info,
                    },
                    output_dir / "best.pt",
                )

        torch.save(
            {
                "model_state": model.state_dict(),
                "config": cfg,
                "classes": classes,
                "epoch": epoch,
                "split_info": split_info,
            },
            output_dir / "last.pt",
        )
        history.append(epoch_log)
        save_json(history, output_dir / "history.json")
        save_history_csv(history, output_dir / "history.csv")

        plot_every = int(train_cfg.get("plot_every", 1))
        if plot_every > 0 and epoch % plot_every == 0:
            try:
                plot_training_history(history, output_dir / "plots")
            except Exception as exc:
                print(f"[WARN] Impossible de générer les graphes d'entraînement: {exc}")

        print(epoch_log)

    print(f"Training done. Best val_loss={best_val:.4f}. Checkpoints: {output_dir}")


if __name__ == "__main__":
    main()
