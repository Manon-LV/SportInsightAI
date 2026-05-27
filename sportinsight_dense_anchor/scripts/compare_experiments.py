"""Génère des graphes comparatifs entre les expériences SportInsight.

Utilisation :
    python scripts/compare_experiments.py --all --output plots/comparison
    python scripts/compare_experiments.py --runs runs/default runs/ohem runs/asl
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = ROOT / "runs"

PALETTE = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
    "#aec7e8", "#ffbb78", "#98df8a", "#ff9896", "#c5b0d5",
    "#c49c94", "#f7b6d2", "#c7c7c7", "#dbdb8d", "#9edae5",
]

# Métadonnées pour labels et analyse factorielle
EXP_META: dict[str, dict] = {
    "default":               {"method": "focal",      "proj": True,  "classes": 4,  "run": "dense_anchor"},
    "no_projection":         {"method": "focal",      "proj": False, "classes": 4,  "run": "dense_anchor_no_projection"},
    "downsample":            {"method": "downsample", "proj": True,  "classes": 4,  "run": "downsample"},
    "downsample_no_proj":    {"method": "downsample", "proj": False, "classes": 4,  "run": "downsample_no_proj"},
    "oversample":            {"method": "oversample", "proj": True,  "classes": 4,  "run": "oversample"},
    "oversample_no_proj":    {"method": "oversample", "proj": False, "classes": 4,  "run": "oversample_no_proj"},
    "ohem":                  {"method": "ohem",       "proj": True,  "classes": 4,  "run": "ohem"},
    "ohem_no_proj":          {"method": "ohem",       "proj": False, "classes": 4,  "run": "ohem_no_proj"},
    "asl":                   {"method": "asl",        "proj": True,  "classes": 4,  "run": "asl"},
    "asl_no_proj":           {"method": "asl",        "proj": False, "classes": 4,  "run": "asl_no_proj"},
    "default_10":            {"method": "focal",      "proj": True,  "classes": 10, "run": "default_10"},
    "default_no_proj_10":    {"method": "focal",      "proj": False, "classes": 10, "run": "default_no_proj_10"},
    "downsample_10":         {"method": "downsample", "proj": True,  "classes": 10, "run": "downsample_10"},
    "downsample_no_proj_10": {"method": "downsample", "proj": False, "classes": 10, "run": "downsample_no_proj_10"},
    "oversample_10":         {"method": "oversample", "proj": True,  "classes": 10, "run": "oversample_10"},
    "oversample_no_proj_10": {"method": "oversample", "proj": False, "classes": 10, "run": "oversample_no_proj_10"},
    "ohem_10":               {"method": "ohem",       "proj": True,  "classes": 10, "run": "ohem_10"},
    "ohem_no_proj_10":       {"method": "ohem",       "proj": False, "classes": 10, "run": "ohem_no_proj_10"},
    "asl_10":                {"method": "asl",        "proj": True,  "classes": 10, "run": "asl_10"},
    "asl_no_proj_10":        {"method": "asl",        "proj": False, "classes": 10, "run": "asl_no_proj_10"},
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_history(run_dir: Path) -> list[dict] | None:
    p = run_dir / "history.json"
    if not p.exists():
        return None
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def extract_xy(history: list[dict], key: str) -> tuple[list[float], list[float]]:
    xs, ys = [], []
    for row in history:
        if key in row and row[key] is not None:
            xs.append(float(row.get("epoch", len(xs) + 1)))
            ys.append(float(row[key]))
    return xs, ys


def best_val(history: list[dict]) -> float | None:
    vals = [row["val_loss"] for row in history if "val_loss" in row and row["val_loss"] is not None]
    return min(vals) if vals else None


def exp_label(name: str) -> str:
    m = EXP_META.get(name, {})
    proj = "proj" if m.get("proj", True) else "no_proj"
    return f"{m.get('method', name)}/{proj}/{m.get('classes', '?')}cls"


# ---------------------------------------------------------------------------
# Plot functions
# ---------------------------------------------------------------------------

def plot_curves(
    experiments: dict[str, list[dict]],
    metric: str,
    title: str,
    out: Path,
) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(13, 6))
    for i, (name, hist) in enumerate(experiments.items()):
        xs, ys = extract_xy(hist, metric)
        if xs:
            ax.plot(xs, ys, color=PALETTE[i % len(PALETTE)], label=exp_label(name), linewidth=1.5, alpha=0.85)
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Loss")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=7.5)
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_best_bar(experiments: dict[str, list[dict]], out: Path) -> None:
    import matplotlib.pyplot as plt

    rows = []
    for i, (name, hist) in enumerate(experiments.items()):
        b = best_val(hist)
        if b is not None:
            rows.append((b, exp_label(name), PALETTE[i % len(PALETTE)]))

    if not rows:
        return

    rows.sort()
    vals, labels, colors = zip(*rows)

    fig, ax = plt.subplots(figsize=(max(8, len(labels) * 0.65), 6))
    bars = ax.bar(range(len(labels)), vals, color=colors, alpha=0.85, edgecolor="white", width=0.7)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Meilleure val_loss")
    ax.set_title("Comparaison — meilleure val_loss par expérience (du meilleur au pire)")
    ax.grid(True, axis="y", alpha=0.3)
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, v + max(vals) * 0.003,
                f"{v:.4f}", ha="center", va="bottom", fontsize=7)
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_factorial(experiments: dict[str, list[dict]], out: Path) -> None:
    """3 panneaux : impact méthode / projection / nb classes."""
    import matplotlib.pyplot as plt

    def avg_by(key: str, values: list) -> dict:
        buckets: dict = {v: [] for v in values}
        for name, hist in experiments.items():
            b = best_val(hist)
            v = EXP_META.get(name, {}).get(key)
            if b is not None and v in buckets:
                buckets[v].append(b)
        return {v: sum(lst) / len(lst) for v, lst in buckets.items() if lst}

    fig, axes = plt.subplots(1, 3, figsize=(17, 5))

    # Panel 1 — méthode d'imbalance
    ax = axes[0]
    methods = ["focal", "downsample", "oversample", "ohem", "asl"]
    means = avg_by("method", methods)
    valid = [(m, means[m]) for m in methods if m in means]
    if valid:
        names, vals = zip(*valid)
        bars = ax.bar(names, vals, color=PALETTE[:len(names)], alpha=0.85, edgecolor="white")
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2, v + max(vals) * 0.003,
                    f"{v:.4f}", ha="center", va="bottom", fontsize=8)
    ax.set_title("Impact — méthode imbalance\n(moy. sur projection × classes)")
    ax.set_ylabel("Val loss moyen")
    ax.grid(True, axis="y", alpha=0.3)

    # Panel 2 — projection
    ax = axes[1]
    means = avg_by("proj", [True, False])
    labels_p = ["Avec projection\n(512→256)", "Sans projection\n(512→512)"]
    vals_p = [means.get(True, 0), means.get(False, 0)]
    nonzero = [(l, v) for l, v in zip(labels_p, vals_p) if v > 0]
    if nonzero:
        nl, nv = zip(*nonzero)
        bars = ax.bar(nl, nv, color=[PALETTE[0], PALETTE[1]], alpha=0.85, edgecolor="white")
        for bar, v in zip(bars, nv):
            ax.text(bar.get_x() + bar.get_width() / 2, v + max(nv) * 0.003,
                    f"{v:.4f}", ha="center", va="bottom", fontsize=8)
    ax.set_title("Impact — projection\n(moy. sur méthode × classes)")
    ax.set_ylabel("Val loss moyen")
    ax.grid(True, axis="y", alpha=0.3)

    # Panel 3 — nombre de classes
    ax = axes[2]
    means = avg_by("classes", [4, 10])
    labels_c = ["4 classes", "10 classes"]
    vals_c = [means.get(4, 0), means.get(10, 0)]
    nonzero = [(l, v) for l, v in zip(labels_c, vals_c) if v > 0]
    if nonzero:
        nl, nv = zip(*nonzero)
        bars = ax.bar(nl, nv, color=[PALETTE[2], PALETTE[3]], alpha=0.85, edgecolor="white")
        for bar, v in zip(bars, nv):
            ax.text(bar.get_x() + bar.get_width() / 2, v + max(nv) * 0.003,
                    f"{v:.4f}", ha="center", va="bottom", fontsize=8)
    ax.set_title("Impact — nombre de classes\n(moy. sur méthode × projection)")
    ax.set_ylabel("Val loss moyen")
    ax.grid(True, axis="y", alpha=0.3)

    fig.suptitle("Analyse factorielle — impact de chaque dimension expérimentale", fontsize=12)
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_method_grid(experiments: dict[str, list[dict]], out: Path) -> None:
    """Grille méthode × (proj/classes) : val_loss final."""
    import matplotlib.pyplot as plt
    import numpy as np

    methods = ["focal", "downsample", "oversample", "ohem", "asl"]
    variants = [
        ("proj_4cls",    {"proj": True,  "classes": 4}),
        ("no_proj_4cls", {"proj": False, "classes": 4}),
        ("proj_10cls",   {"proj": True,  "classes": 10}),
        ("no_proj_10cls",{"proj": False, "classes": 10}),
    ]

    matrix = np.full((len(methods), len(variants)), np.nan)
    for name, hist in experiments.items():
        b = best_val(hist)
        m = EXP_META.get(name, {})
        if b is None:
            continue
        meth = m.get("method")
        if meth not in methods:
            continue
        mi = methods.index(meth)
        for vi, (_, cond) in enumerate(variants):
            if all(m.get(k) == v for k, v in cond.items()):
                matrix[mi, vi] = b

    fig, ax = plt.subplots(figsize=(10, 5))
    masked = np.ma.masked_invalid(matrix)
    im = ax.imshow(masked, aspect="auto", cmap="RdYlGn_r")
    ax.set_xticks(range(len(variants)))
    ax.set_xticklabels([v[0] for v in variants], fontsize=9)
    ax.set_yticks(range(len(methods)))
    ax.set_yticklabels(methods, fontsize=9)
    ax.set_title("Heatmap val_loss — méthode × (projection × classes)")

    for i in range(len(methods)):
        for j in range(len(variants)):
            if not np.isnan(matrix[i, j]):
                ax.text(j, i, f"{matrix[i, j]:.4f}", ha="center", va="center", fontsize=8)

    fig.colorbar(im, ax=ax, label="Best val_loss")
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Compare les expériences SportInsight")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="Charge toutes les expériences connues")
    group.add_argument("--runs", nargs="+", metavar="DIR", help="Répertoires de runs spécifiques")
    parser.add_argument("--output", default="plots/comparison", help="Répertoire de sortie des graphes")
    args = parser.parse_args()

    out_dir = ROOT / args.output
    out_dir.mkdir(parents=True, exist_ok=True)

    experiments: dict[str, list[dict]] = {}

    if args.all:
        for exp_name, meta in EXP_META.items():
            run_dir = RUNS_DIR / meta["run"]
            hist = load_history(run_dir)
            if hist:
                experiments[exp_name] = hist
            else:
                print(f"[SKIP] {exp_name} — history.json absent dans {run_dir.relative_to(ROOT)}")
    else:
        for path_str in args.runs:
            p = Path(path_str)
            if not p.is_absolute():
                p = ROOT / p
            hist = load_history(p)
            if hist:
                experiments[p.name] = hist
            else:
                print(f"[SKIP] {p} — history.json absent")

    if not experiments:
        print("Aucune expérience chargée. Lancez d'abord run_experiments.py.")
        return

    print(f"{len(experiments)} expériences chargées : {list(experiments.keys())}")

    generated: list[Path] = []

    out = out_dir / "val_loss_curves.png"
    plot_curves(experiments, "val_loss", "Validation loss — toutes les expériences", out)
    generated.append(out)

    out = out_dir / "train_loss_curves.png"
    plot_curves(experiments, "loss", "Training loss — toutes les expériences", out)
    generated.append(out)

    out = out_dir / "best_val_loss_bar.png"
    plot_best_bar(experiments, out)
    generated.append(out)

    if len(experiments) >= 3:
        out = out_dir / "factorial_analysis.png"
        plot_factorial(experiments, out)
        generated.append(out)

    if len(experiments) >= 4:
        out = out_dir / "method_grid_heatmap.png"
        plot_method_grid(experiments, out)
        generated.append(out)

    for p in generated:
        print(f"[OK] {p.relative_to(ROOT)}")
    print(f"\n{len(generated)} graphes générés dans {out_dir.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
