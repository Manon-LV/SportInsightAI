from __future__ import annotations

import argparse
from pathlib import Path

from sportinsight.visualization import load_history, plot_training_history, save_history_csv


def main() -> None:
    parser = argparse.ArgumentParser(description="Génère les courbes d'entraînement depuis runs/.../history.json")
    parser.add_argument("--run-dir", default="runs/dense_anchor", help="Dossier contenant history.json")
    parser.add_argument("--history", default=None, help="Chemin explicite vers history.json")
    parser.add_argument("--output-dir", default=None, help="Dossier de sortie des figures")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    history_path = Path(args.history) if args.history else run_dir / "history.json"
    output_dir = Path(args.output_dir) if args.output_dir else run_dir / "plots"

    history = load_history(history_path)
    save_history_csv(history, run_dir / "history.csv")
    files = plot_training_history(history, output_dir)

    print("Figures générées :")
    for f in files:
        print(f"- {f}")


if __name__ == "__main__":
    main()
