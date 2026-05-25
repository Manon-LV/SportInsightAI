from __future__ import annotations

import os
import threading
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[2]

VIDEO_FILES_BY_RESOLUTION = {
    "224p": ["1_224p.mkv", "2_224p.mkv"],
    "720p": ["1_720p.mkv", "2_720p.mkv"],
}
FEATURE_FILES = ["1_ResNET_TF2_PCA512.npy", "2_ResNET_TF2_PCA512.npy"]
LABEL_FILES = ["Labels-v2.json"]


@dataclass
class DownloadJob:
    id: str
    status: Literal["queued", "running", "done", "error"] = "queued"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    root: str = "data/SoccerNet"
    files: list[str] = field(default_factory=list)
    split: list[str] = field(default_factory=list)
    game: str | None = None
    message: str = "En attente."
    error: str | None = None

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def as_dict(self) -> dict:
        return {
            "job_id": self.id,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "root": self.root,
            "files": self.files,
            "split": self.split,
            "game": self.game,
            "message": self.message,
            "error": self.error,
        }


_JOBS: dict[str, DownloadJob] = {}
_LOCK = threading.Lock()


def _selected_video_files(resolution: str) -> list[str]:
    if resolution == "both":
        return VIDEO_FILES_BY_RESOLUTION["224p"] + VIDEO_FILES_BY_RESOLUTION["720p"]
    return VIDEO_FILES_BY_RESOLUTION[resolution]


def _build_files(resolution: str, include_features: bool, include_labels: bool) -> list[str]:
    files: list[str] = []
    files.extend(_selected_video_files(resolution))
    if include_features:
        files.extend(FEATURE_FILES)
    if include_labels:
        files.extend(LABEL_FILES)
    return list(dict.fromkeys(files))


def _resolve_root(root_value: str) -> Path:
    raw = Path(root_value)
    return (raw if raw.is_absolute() else REPO_ROOT / raw).resolve()


def _run_download(job_id: str, payload: dict) -> None:
    with _LOCK:
        job = _JOBS[job_id]
        job.status = "running"
        job.message = "Import de SoccerNetDownloader."
        job.touch()

    try:
        try:
            from SoccerNet.Downloader import SoccerNetDownloader
        except ImportError as exc:
            raise RuntimeError("Package SoccerNet absent. Lance : pip install SoccerNet") from exc

        password = payload.get("password") or os.environ.get("SOCCERNET_PASSWORD")
        if not password:
            raise RuntimeError("Mot de passe SoccerNet manquant. Fournis-le dans l'interface ou via SOCCERNET_PASSWORD.")

        root = _resolve_root(payload.get("root") or "data/SoccerNet")
        root.mkdir(parents=True, exist_ok=True)
        files = _build_files(
            payload.get("resolution", "224p"),
            bool(payload.get("include_features", False)),
            bool(payload.get("include_labels", False)),
        )
        split = payload.get("split") or ["train", "valid", "test"]
        game = payload.get("game") or None

        with _LOCK:
            job = _JOBS[job_id]
            job.root = str(root)
            job.files = files
            job.split = split
            job.game = game
            job.message = "Téléchargement SoccerNet en cours. Cette opération peut être longue."
            job.touch()

        downloader = SoccerNetDownloader(LocalDirectory=str(root))
        downloader.password = password
        if game:
            downloader.downloadGame(files=files, game=game)
        else:
            downloader.downloadGames(files=files, split=split)

        with _LOCK:
            job = _JOBS[job_id]
            job.status = "done"
            job.message = "Téléchargement terminé."
            job.touch()
    except Exception as exc:
        with _LOCK:
            job = _JOBS[job_id]
            job.status = "error"
            job.message = "Téléchargement échoué."
            job.error = f"{exc}\n{traceback.format_exc()}"
            job.touch()


def start_soccernet_download(payload: dict) -> dict:
    files = _build_files(
        payload.get("resolution", "224p"),
        bool(payload.get("include_features", False)),
        bool(payload.get("include_labels", False)),
    )
    job_id = f"download_{uuid4().hex[:10]}"
    job = DownloadJob(
        id=job_id,
        root=payload.get("root") or "data/SoccerNet",
        files=files,
        split=payload.get("split") or ["train", "valid", "test"],
        game=payload.get("game") or None,
        message="Téléchargement planifié.",
    )
    with _LOCK:
        _JOBS[job_id] = job

    thread = threading.Thread(target=_run_download, args=(job_id, payload), daemon=True)
    thread.start()
    return job.as_dict()


def read_download_job(job_id: str) -> dict | None:
    with _LOCK:
        job = _JOBS.get(job_id)
        return job.as_dict() if job else None
