from __future__ import annotations

import argparse
import math
from pathlib import Path

import torch
from torch.utils.data import DataLoader, Subset
from tqdm import tqdm


class SAM(torch.optim.Optimizer):
    """Sharpness-Aware Minimization (Foret et al., 2021).

    Chaque step requiert deux passes forward-backward :
      1. first_step  : perturbe les poids vers le maximum local (sharpness)
      2. second_step : met à jour depuis le point perturbé, restaure les poids

    Usage dans la boucle d'entraînement :
        loss.backward(); optimizer.first_step(zero_grad=True)
        criterion(model(x), y).backward(); optimizer.second_step(zero_grad=True)
    """

    def __init__(self, params, base_optimizer_cls, rho: float = 0.05, **base_kwargs):
        defaults = dict(rho=rho, **base_kwargs)
        super().__init__(params, defaults)
        self.base_optimizer = base_optimizer_cls(self.param_groups, **base_kwargs)
        self.param_groups = self.base_optimizer.param_groups
        self.defaults.update(self.base_optimizer.defaults)

    @torch.no_grad()
    def first_step(self, zero_grad: bool = False) -> None:
        grad_norm = self._grad_norm()
        for group in self.param_groups:
            scale = group["rho"] / (grad_norm + 1e-12)
            for p in group["params"]:
                if p.grad is None:
                    continue
                self.state[p]["old_p"] = p.data.clone()
                p.add_(p.grad * scale)
        if zero_grad:
            self.zero_grad()

    @torch.no_grad()
    def second_step(self, zero_grad: bool = False) -> None:
        for group in self.param_groups:
            for p in group["params"]:
                if "old_p" in self.state[p]:
                    p.data = self.state[p]["old_p"]
        self.base_optimizer.step()
        if zero_grad:
            self.zero_grad()

    def step(self, closure=None):
        raise RuntimeError("SAM: utiliser first_step() puis second_step() explicitement.")

    def _grad_norm(self) -> torch.Tensor:
        device = self.param_groups[0]["params"][0].device
        norms = [
            p.grad.norm(p=2).to(device)
            for group in self.param_groups
            for p in group["params"]
            if p.grad is not None
        ]
        return torch.stack(norms).norm(p=2) if norms else torch.tensor(0.0, device=device)

    def load_state_dict(self, state_dict: dict) -> None:
        super().load_state_dict(state_dict)
        self.base_optimizer.param_groups = self.param_groups

from .data import ClassStratifiedSampler, SoccerNetDenseAnchorDataset, dense_anchor_collate, find_feature_file, load_features
from .infer import predict_half
from .labels import load_events_from_labels
from .losses import build_loss
from .metrics import temporal_map, LOOSE_TOLERANCES, TIGHT_TOLERANCES
from .model import build_model
from .postprocess import nms_predictions
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


@torch.no_grad()
def validate_map(
    model,
    game_dirs: list[Path],
    classes: list[str],
    data_cfg: dict,
    post_cfg: dict,
    device: torch.device,
) -> dict[str, float]:
    """Calcule le Avg-mAP loose (tolérances officielles SoccerNet) sur les matchs de validation.

    Utilise un seuil bas (0.01) pour obtenir la courbe précision-rappel complète.
    Résultats préfixés par 'val_' pour intégration dans le history.
    """
    feature_fps = float(data_cfg.get("feature_fps", 2.0))
    window_size_sec = float(data_cfg.get("window_size_sec", 120.0))
    stride_sec = float(data_cfg.get("stride_sec", 60.0))
    nms_radius = float(post_cfg.get("nms_radius_sec", 6.0))
    max_preds = int(post_cfg.get("max_predictions_per_class", 200))

    infer_post = dict(post_cfg)
    infer_post["score_threshold"] = 0.01

    all_preds = []
    all_events = []
    model.eval()

    for game_dir in tqdm(game_dirs, desc="mAP val", leave=False):
        raw = []
        for half_idx in (1, 2):
            fpath = find_feature_file(game_dir, half_idx)
            if fpath is None:
                continue
            features = load_features(fpath)
            raw.extend(predict_half(
                model, features, classes=classes, half=half_idx,
                feature_fps=feature_fps, window_size_sec=window_size_sec,
                stride_sec=stride_sec, post_cfg=infer_post, device=device,
            ))

        all_preds.extend(nms_predictions(
            raw, classes=classes,
            radius_sec=nms_radius,
            score_threshold=0.0,
            max_predictions_per_class=max_preds,
        ))

        labels_path = game_dir / "Labels-v2.json"
        if labels_path.exists():
            all_events.extend(load_events_from_labels(labels_path, classes))

    loose = temporal_map(all_preds, all_events, classes=classes, tolerances_sec=LOOSE_TOLERANCES)
    tight = temporal_map(all_preds, all_events, classes=classes, tolerances_sec=TIGHT_TOLERANCES)
    out = {"val_" + k: v for k, v in loose.items()}
    out["val_tight_avg_mAP"] = tight["avg_mAP"]
    out["val_tight_mAP@1s"] = tight.get("mAP@1s", 0.0)
    out["val_tight_mAP@5s"] = tight.get("mAP@5s", 0.0)
    return out


def _dataset_from_config(
    data_cfg: dict,
    classes: list[str],
    split_file: str | None = None,
    seed: int = 42,
    apply_sampling: bool = True,
) -> SoccerNetDenseAnchorDataset:
    raw_strategy = str(data_cfg.get("imbalance_strategy", "none")) if apply_sampling else "none"
    # ClassStratifiedSampler is wired externally; keep all windows in the dataset
    strategy = "none" if raw_strategy == "class_stratified" else raw_strategy
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
        feature_noise_std=float(data_cfg.get("feature_noise_std", 0.0)) if apply_sampling else 0.0,
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

    # Game dirs pour validate_map (disponibles si val_ds est un SoccerNetDenseAnchorDataset)
    val_game_dirs: list[Path] = []
    if isinstance(val_ds, SoccerNetDenseAnchorDataset):
        val_game_dirs = [Path(g) for g in val_ds.game_dirs]
    map_every = int(train_cfg.get("map_every", 0))
    post_cfg = dict(cfg.get("postprocess", {}))
    if map_every > 0 and val_game_dirs:
        print(f"Avg-mAP loose calculé toutes les {map_every} epoch(s) sur {len(val_game_dirs)} matchs.")
    elif map_every > 0:
        print("[WARN] map_every > 0 mais val_game_dirs vide — mAP désactivé (split par fenêtres ?)")

    imbalance_strategy = str(data_cfg.get("imbalance_strategy", "none"))
    train_sampler = None
    if imbalance_strategy == "class_stratified" and isinstance(train_ds, SoccerNetDenseAnchorDataset):
        train_sampler = ClassStratifiedSampler(train_ds, seed=seed)
        print(f"ClassStratifiedSampler activé : {train_sampler._num_classes} classes, {len(train_sampler)} steps/epoch")

    train_loader = DataLoader(
        train_ds,
        batch_size=int(train_cfg.get("batch_size", 16)),
        shuffle=(train_sampler is None),
        sampler=train_sampler,
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
    lr = float(train_cfg.get("lr", 3e-4))
    wd = float(train_cfg.get("weight_decay", 1e-4))
    if str(train_cfg.get("optimizer", "adamw")).lower() == "sam":
        sam_rho = float(train_cfg.get("sam_rho", 0.05))
        optimizer = SAM(model.parameters(), torch.optim.AdamW, rho=sam_rho, lr=lr, weight_decay=wd)
        print(f"Optimizer : SAM(AdamW, rho={sam_rho})")
    else:
        optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=wd)
    epochs = int(train_cfg.get("epochs", 30))
    warmup_epochs = int(train_cfg.get("warmup_epochs", 0))
    # SAM : le scheduler doit être lié au base_optimizer (celui qui appelle .step()
    # réellement) pour que PyTorch ne lève pas de UserWarning sur l'ordre des appels.
    sched_opt = optimizer.base_optimizer if isinstance(optimizer, SAM) else optimizer
    if warmup_epochs > 0:
        warmup_sched = torch.optim.lr_scheduler.LinearLR(
            sched_opt, start_factor=1e-6, end_factor=1.0, total_iters=warmup_epochs
        )
        cosine_sched = torch.optim.lr_scheduler.CosineAnnealingLR(
            sched_opt, T_max=max(1, epochs - warmup_epochs)
        )
        scheduler = torch.optim.lr_scheduler.SequentialLR(
            sched_opt, schedulers=[warmup_sched, cosine_sched], milestones=[warmup_epochs]
        )
        print(f"Scheduler : LinearLR warmup {warmup_epochs} epochs → CosineAnnealingLR {epochs - warmup_epochs} epochs")
    else:
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(sched_opt, T_max=epochs)

    best_val_loss = math.inf
    best_val_map = -math.inf
    history = []

    for epoch in range(1, epochs + 1):
        model.train()
        running = {"loss": 0.0, "loss_cls": 0.0, "loss_reg": 0.0}
        steps = 0
        if train_sampler is not None:
            train_sampler.set_epoch(epoch)
        use_sam = isinstance(optimizer, SAM)
        grad_clip = train_cfg.get("grad_clip_norm", 1.0)
        pbar = tqdm(train_loader, desc=f"epoch {epoch}")
        for batch in pbar:
            batch = move_batch_to_device(batch, device)
            optimizer.zero_grad(set_to_none=True)
            outputs = model(batch["x"])
            losses = criterion(outputs, batch)
            losses["loss"].backward()
            if grad_clip is not None:
                torch.nn.utils.clip_grad_norm_(model.parameters(), float(grad_clip))
            if use_sam:
                optimizer.first_step(zero_grad=True)
                outputs = model(batch["x"])
                losses = criterion(outputs, batch)
                losses["loss"].backward()
                if grad_clip is not None:
                    torch.nn.utils.clip_grad_norm_(model.parameters(), float(grad_clip))
                optimizer.second_step(zero_grad=True)
            else:
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
            if epoch_log["val_loss"] < best_val_loss:
                best_val_loss = epoch_log["val_loss"]
                torch.save(
                    {
                        "model_state": model.state_dict(),
                        "config": cfg,
                        "classes": classes,
                        "epoch": epoch,
                        "val_loss": best_val_loss,
                        "split_info": split_info,
                    },
                    output_dir / "best.pt",
                )

        if map_every > 0 and val_game_dirs and epoch % map_every == 0:
            map_metrics = validate_map(model, val_game_dirs, classes, data_cfg, post_cfg, device)
            epoch_log.update(map_metrics)
            current_map = map_metrics.get("val_avg_mAP", -math.inf)
            if current_map > best_val_map:
                best_val_map = current_map
                torch.save(
                    {
                        "model_state": model.state_dict(),
                        "config": cfg,
                        "classes": classes,
                        "epoch": epoch,
                        "val_avg_map": best_val_map,
                        "split_info": split_info,
                    },
                    output_dir / "best_map.pt",
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

    summary = f"Training done. Best val_loss={best_val_loss:.4f}"
    if best_val_map > -math.inf:
        summary += f", best val_avg_mAP={best_val_map * 100:.2f}%"
    print(summary + f". Checkpoints: {output_dir}")


if __name__ == "__main__":
    main()
