from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

import json


def load_history(history_path: str | Path) -> list[dict]:
    path = Path(history_path)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Expected a list of epoch logs in {path}")
    return data


def save_history_csv(history: Sequence[dict], output_path: str | Path) -> None:
    """Save a compact CSV history without requiring pandas."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in history:
        for key in row.keys():
            if key not in keys:
                keys.append(key)
    with output_path.open("w", encoding="utf-8") as f:
        f.write(",".join(keys) + "\n")
        for row in history:
            values = []
            for key in keys:
                value = row.get(key, "")
                values.append(str(value))
            f.write(",".join(values) + "\n")


def _extract_xy(history: Sequence[dict], key: str) -> tuple[list[float], list[float]]:
    xs, ys = [], []
    for i, row in enumerate(history, start=1):
        if key in row and row[key] is not None:
            xs.append(float(row.get("epoch", i)))
            ys.append(float(row[key]))
    return xs, ys


def plot_training_history(history: Sequence[dict], output_dir: str | Path) -> list[Path]:
    """Create training plots from the JSON history produced by train.py.

    Files generated:
    - loss_curves.png: train/validation total loss
    - loss_components.png: classification and regression losses
    - learning_rate.png: scheduler trajectory
    """
    import matplotlib.pyplot as plt

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []

    # Total loss: train vs validation.
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    for key, label in [("loss", "train loss"), ("val_loss", "validation loss")]:
        xs, ys = _extract_xy(history, key)
        if xs:
            ax.plot(xs, ys, marker="o", label=label)
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Loss")
    ax.set_title("Courbe d'entraînement — loss totale")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    out = output_dir / "loss_curves.png"
    fig.savefig(out, dpi=180)
    plt.close(fig)
    generated.append(out)

    # Loss components.
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    for key, label in [
        ("loss_cls", "train classification"),
        ("val_loss_cls", "validation classification"),
        ("loss_reg", "train offset"),
        ("val_loss_reg", "validation offset"),
    ]:
        xs, ys = _extract_xy(history, key)
        if xs:
            ax.plot(xs, ys, marker="o", label=label)
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Loss")
    ax.set_title("Décomposition de la loss")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    out = output_dir / "loss_components.png"
    fig.savefig(out, dpi=180)
    plt.close(fig)
    generated.append(out)

    # Learning rate.
    xs, ys = _extract_xy(history, "lr")
    if xs:
        fig, ax = plt.subplots(figsize=(7.0, 4.2))
        ax.plot(xs, ys, marker="o")
        ax.set_xlabel("Epoch")
        ax.set_ylabel("Learning rate")
        ax.set_title("Planification du learning rate")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        out = output_dir / "learning_rate.png"
        fig.savefig(out, dpi=180)
        plt.close(fig)
        generated.append(out)

    return generated


def seconds_to_mmss(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    m = int(seconds // 60)
    s = int(round(seconds - 60 * m))
    return f"{m:02d}:{s:02d}"


def plot_timeline(
    predictions: Sequence[dict],
    output_path: str | Path,
    labels: Sequence[dict] | None = None,
    classes: Sequence[str] | None = None,
    title: str = "Timeline des actions détectées",
) -> Path:
    """Plot prediction and optional ground-truth timelines.

    `predictions` entries are expected to contain at least: half, timestamp, label, score.
    `labels` entries may contain: half, timestamp/time_sec, label.
    """
    import matplotlib.pyplot as plt

    if classes is None:
        cls_set = {str(p.get("label", "unknown")) for p in predictions}
        if labels:
            cls_set.update(str(x.get("label", "unknown")) for x in labels)
        classes = sorted(cls_set)
    class_to_y = {label: i for i, label in enumerate(classes)}

    fig, ax = plt.subplots(figsize=(9.0, 3.8))

    for item in predictions:
        label = str(item.get("label", "unknown"))
        if label not in class_to_y:
            continue
        half = int(item.get("half", 1))
        timestamp = float(item.get("timestamp", item.get("time_sec", 0.0)))
        absolute_time = timestamp + (half - 1) * 45 * 60
        score = float(item.get("score", 0.0))
        ax.scatter(absolute_time / 60.0, class_to_y[label], s=30 + 120 * max(0.0, min(score, 1.0)), alpha=0.75)

    if labels:
        for item in labels:
            label = str(item.get("label", "unknown"))
            if label not in class_to_y:
                continue
            half = int(item.get("half", 1))
            timestamp = float(item.get("timestamp", item.get("time_sec", 0.0)))
            absolute_time = timestamp + (half - 1) * 45 * 60
            ax.scatter(absolute_time / 60.0, class_to_y[label], marker="x", s=80, linewidths=2)

    ax.axvline(45.0, linestyle="--", linewidth=1.0, alpha=0.7)
    ax.set_yticks(list(class_to_y.values()))
    ax.set_yticklabels(list(class_to_y.keys()))
    ax.set_xlabel("Minute du match")
    ax.set_title(title)
    ax.grid(True, axis="x", alpha=0.3)
    fig.tight_layout()

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    return output_path
