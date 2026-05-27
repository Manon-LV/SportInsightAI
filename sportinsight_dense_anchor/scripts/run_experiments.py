"""Lance plusieurs expériences d'entraînement SportInsight en séquence.

Utilisation :
    python scripts/run_experiments.py --all
    python scripts/run_experiments.py --configs default downsample ohem asl
    python scripts/run_experiments.py --all --skip-existing
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIGS_DIR = ROOT / "configs"
REGISTRY_PATH = ROOT / "experiments_registry.json"

# Ordre des 20 expériences (nom du fichier config sans .yaml)
ALL_EXPERIMENTS = [
    # 4 classes — avec projection
    "default",
    "downsample",
    "oversample",
    "ohem",
    "asl",
    # 4 classes — sans projection
    "no_projection",
    "downsample_no_proj",
    "oversample_no_proj",
    "ohem_no_proj",
    "asl_no_proj",
    # 10 classes — avec projection
    "default_10",
    "downsample_10",
    "oversample_10",
    "ohem_10",
    "asl_10",
    # 10 classes — sans projection
    "default_no_proj_10",
    "downsample_no_proj_10",
    "oversample_no_proj_10",
    "ohem_no_proj_10",
    "asl_no_proj_10",
]


def load_registry() -> dict:
    if REGISTRY_PATH.exists():
        with REGISTRY_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {"experiments": {}}


def save_registry(registry: dict) -> None:
    with REGISTRY_PATH.open("w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)


def run_one(config_name: str) -> dict:
    config_path = CONFIGS_DIR / f"{config_name}.yaml"
    started_at = datetime.now().isoformat()

    if not config_path.exists():
        return {
            "status": "error",
            "error": f"Config introuvable : {config_path}",
            "started_at": started_at,
            "finished_at": started_at,
            "duration_sec": 0.0,
        }

    t0 = time.time()
    print(f"\n{'='*62}")
    print(f"  Expérience : {config_name}")
    print(f"  Config     : {config_path.relative_to(ROOT)}")
    print(f"  Démarrage  : {started_at}")
    print(f"{'='*62}\n", flush=True)

    proc = subprocess.run(
        [sys.executable, "-m", "sportinsight.train", "--config", str(config_path)],
        cwd=str(ROOT),
    )

    duration = round(time.time() - t0, 1)
    finished_at = datetime.now().isoformat()
    status = "done" if proc.returncode == 0 else "error"
    icon = "OK" if status == "done" else "FAIL"
    print(f"\n[{icon}] {config_name} — {duration}s", flush=True)

    return {
        "status": status,
        "config": str(config_path.relative_to(ROOT)),
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_sec": duration,
        "returncode": proc.returncode,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Lance les expériences SportInsight")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="Lance les 20 expériences")
    group.add_argument(
        "--configs", nargs="+", metavar="NOM",
        help="Noms des configs à lancer (sans .yaml), ex: default ohem asl",
    )
    parser.add_argument(
        "--skip-existing", action="store_true",
        help="Ignore les expériences dont le statut est déjà 'done' dans le registre",
    )
    args = parser.parse_args()

    to_run: list[str] = ALL_EXPERIMENTS if args.all else list(args.configs)

    registry = load_registry()

    if args.skip_existing:
        done = {
            name for name, entry in registry.get("experiments", {}).items()
            if entry.get("status") == "done"
        }
        skipped = [n for n in to_run if n in done]
        to_run = [n for n in to_run if n not in done]
        if skipped:
            print(f"Ignorées ({len(skipped)}) : {skipped}")

    if not to_run:
        print("Rien à lancer.")
        return

    print(f"Expériences à lancer ({len(to_run)}) : {to_run}")

    t_total = time.time()
    summary: list[tuple[str, str, float]] = []

    for name in to_run:
        entry = run_one(name)
        registry.setdefault("experiments", {})[name] = entry
        save_registry(registry)
        summary.append((name, entry["status"], entry.get("duration_sec", 0.0)))

    elapsed = round(time.time() - t_total, 1)

    print(f"\n{'='*62}")
    print("RÉSUMÉ")
    print(f"{'='*62}")
    for name, status, dur in summary:
        icon = "OK  " if status == "done" else "FAIL"
        print(f"[{icon}] {name:<40} {dur:>8.1f}s")

    n_ok = sum(1 for _, s, _ in summary if s == "done")
    n_fail = len(summary) - n_ok
    print(f"\nTotal : {n_ok}/{len(summary)} réussies en {elapsed}s")
    if n_fail:
        failed = [n for n, s, _ in summary if s != "done"]
        print(f"Échecs : {failed}")
    print(f"Registre : {REGISTRY_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
