from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


def main() -> None:
    parser = argparse.ArgumentParser(description="Génère des graphes de diagnostic depuis history.csv ou history.json.")
    parser.add_argument("--history", required=True)
    parser.add_argument("--output-dir", default="runs/dense_anchor/diagnostics")
    args = parser.parse_args()

    history_path = Path(args.history)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if history_path.suffix.lower() == ".json":
        with history_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        df = pd.DataFrame(data)
    else:
        df = pd.read_csv(history_path)

    best_idx = int(df["val_loss"].idxmin())
    best_row = df.loc[best_idx]
    summary = {
        "best_epoch_by_val_loss": int(best_row["epoch"]),
        "best_val_loss": float(best_row["val_loss"]),
        "best_val_loss_cls": float(best_row["val_loss_cls"]),
        "best_val_loss_reg": float(best_row["val_loss_reg"]),
        "final_epoch": int(df["epoch"].iloc[-1]),
        "final_train_loss": float(df["loss"].iloc[-1]),
        "final_val_loss": float(df["val_loss"].iloc[-1]),
        "train_loss_reduction_pct": float((df["loss"].iloc[0] - df["loss"].iloc[-1]) / df["loss"].iloc[0] * 100.0),
        "val_loss_reduction_pct": float((df["val_loss"].iloc[0] - df["val_loss"].iloc[-1]) / df["val_loss"].iloc[0] * 100.0),
        "final_generalization_gap": float(df["val_loss"].iloc[-1] - df["loss"].iloc[-1]),
    }

    with (output_dir / "training_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    pd.DataFrame([summary]).to_csv(output_dir / "training_summary.csv", index=False)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(df["epoch"], df["loss"], marker="o", label="train loss")
    ax.plot(df["epoch"], df["val_loss"], marker="o", label="validation loss")
    ax.axvline(summary["best_epoch_by_val_loss"], linestyle="--", label=f"meilleure val: époque {summary['best_epoch_by_val_loss']}")
    ax.set_xlabel("Époque")
    ax.set_ylabel("Loss")
    ax.set_title("Loss totale avec meilleure époque")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "loss_with_best_epoch.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))
    gap = df["val_loss"] - df["loss"]
    ax.plot(df["epoch"], gap, marker="o")
    ax.axhline(0, linestyle="--")
    ax.set_xlabel("Époque")
    ax.set_ylabel("val_loss - train_loss")
    ax.set_title("Écart de généralisation")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_dir / "generalization_gap.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(df["epoch"], df["val_loss_cls"], marker="o", label="classification validation")
    ax.plot(df["epoch"], df["val_loss_reg"], marker="o", label="offset validation")
    ax.set_yscale("log")
    ax.set_xlabel("Époque")
    ax.set_ylabel("Loss validation (échelle log)")
    ax.set_title("Composantes de validation")
    ax.grid(True, alpha=0.3, which="both")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "validation_components_log.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))
    for col, label in [
        ("loss_reg", "offset train"),
        ("val_loss_reg", "offset validation"),
        ("loss_cls", "classification train"),
        ("val_loss_cls", "classification validation"),
    ]:
        ax.plot(df["epoch"], df[col] / df[col].iloc[0], marker="o", label=label)
    ax.set_xlabel("Époque")
    ax.set_ylabel("Valeur normalisée par rapport à époque 1")
    ax.set_title("Vitesse de convergence des composantes")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "normalized_components.png", dpi=180)
    plt.close(fig)

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"Graphes générés dans : {output_dir.resolve()}")


if __name__ == "__main__":
    main()
