from __future__ import annotations

import json
import shutil
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[2]
UPLOADS_DIR = Path(__file__).resolve().parent / "storage" / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class UploadJob:
    id: str
    status: Literal["uploading", "processing", "done", "error"] = "uploading"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    match_name: str = ""
    half_1_path: str | None = None
    half_2_path: str | None = None
    half_1_size: int = 0
    half_2_size: int = 0
    features_status: Literal["pending", "extracting", "done", "error"] = "pending"
    match_dir: str | None = None
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
            "match_name": self.match_name,
            "half_1_path": self.half_1_path,
            "half_2_path": self.half_2_path,
            "half_1_size": self.half_1_size,
            "half_2_size": self.half_2_size,
            "features_status": self.features_status,
            "match_dir": self.match_dir,
            "message": self.message,
            "error": self.error,
        }


_JOBS: dict[str, UploadJob] = {}
_LOCK = threading.Lock()


def create_upload_job(match_name: str) -> str:
    """Crée un nouveau job d'upload et retourne son ID."""
    job_id = f"upload_{uuid4().hex[:12]}"
    job = UploadJob(id=job_id, match_name=match_name)
    
    # Créer le répertoire du match immédiatement
    match_upload_dir = UPLOADS_DIR / job_id / job.match_name
    match_upload_dir.mkdir(parents=True, exist_ok=True)
    job.match_dir = str(match_upload_dir)
    
    with _LOCK:
        _JOBS[job_id] = job
    
    return job_id


def get_upload_job(job_id: str) -> UploadJob | None:
    """Récupère les informations d'un job d'upload."""
    with _LOCK:
        return _JOBS.get(job_id)


def save_video_file(job_id: str, half: int, video_data: bytes, original_filename: str = "") -> dict:
    """Sauvegarde un fichier vidéo et retourne les informations."""
    with _LOCK:
        job = _JOBS.get(job_id)
        if not job:
            raise ValueError(f"Job d'upload non trouvé: {job_id}")

        if half not in (1, 2):
            raise ValueError("La mi-temps doit être 1 ou 2")

        # Créer le dossier du match
        if not job.match_dir:
            match_upload_dir = UPLOADS_DIR / job_id / job.match_name
            match_upload_dir.mkdir(parents=True, exist_ok=True)
            job.match_dir = str(match_upload_dir)

        # Préserver l'extension du fichier original
        ext = Path(original_filename).suffix.lower() if original_filename else ".mp4"
        if ext not in {".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v"}:
            ext = ".mp4"

        # Sauvegarder la vidéo
        video_path = Path(job.match_dir) / f"{half}{ext}"
        with open(video_path, "wb") as f:
            f.write(video_data)
        
        file_size = len(video_data)
        
        if half == 1:
            job.half_1_path = str(video_path)
            job.half_1_size = file_size
        else:
            job.half_2_path = str(video_path)
            job.half_2_size = file_size
        
        job.touch()
        job.message = f"Mi-temps {half} uploadée ({file_size / 1024 / 1024:.1f} MB)"
    
    return {
        "job_id": job_id,
        "half": half,
        "path": str(video_path),
        "size": file_size,
    }


def finalize_upload(job_id: str) -> dict:
    """Finalise l'upload et retourne l'état du job."""
    with _LOCK:
        job = _JOBS.get(job_id)
        if not job:
            raise ValueError(f"Job d'upload non trouvé: {job_id}")
        
        # Vérifier que les deux mi-temps sont présentes
        if not job.half_1_path or not job.half_2_path:
            job.error = "Les deux mi-temps (1 et 2) doivent être uploadées"
            job.status = "error"
            job.touch()
            raise ValueError(job.error)
        
        # Vérifier que les fichiers existent
        if not Path(job.half_1_path).exists() or not Path(job.half_2_path).exists():
            job.error = "Un ou plusieurs fichiers vidéo sont manquants"
            job.status = "error"
            job.touch()
            raise ValueError(job.error)
        
        job.status = "processing"
        job.features_status = "pending"
        job.message = "Upload terminé. Prêt à extraire les features."
        job.touch()
    
    return job.as_dict()


def list_upload_jobs() -> list[dict]:
    """Liste tous les jobs d'upload."""
    with _LOCK:
        return [job.as_dict() for job in _JOBS.values()]


def delete_upload_job(job_id: str) -> bool:
    """Supprime un job d'upload et ses fichiers."""
    with _LOCK:
        job = _JOBS.pop(job_id, None)
        if not job:
            return False
        
        if job.match_dir and Path(job.match_dir).exists():
            shutil.rmtree(Path(job.match_dir).parent, ignore_errors=True)
    
    return True


def import_features_files(job_id: str, files: dict[int, Path]) -> dict:
    """
    Importe les fichiers .npy de features directement.
    
    Args:
        job_id: ID du job d'upload
        files: Dict {1: Path to 1_ResNET_TF2_PCA512.npy, 2: Path to 2_ResNET_TF2_PCA512.npy}
    
    Returns:
        Dict avec les chemins importés et le statut
    """
    with _LOCK:
        job = _JOBS.get(job_id)
        if not job:
            raise ValueError(f"Job d'upload non trouvé: {job_id}")
        
        if not job.match_dir:
            raise ValueError("Le répertoire du match n'est pas défini")
        
        match_dir = Path(job.match_dir)
        results = {"halves": {}}
        
        for half, source_path in files.items():
            source_path = Path(source_path)
            if not source_path.exists():
                results["halves"][half] = {
                    "status": "error",
                    "message": f"Fichier source non trouvé: {source_path}"
                }
                continue
            
            # Copier le fichier .npy vers le répertoire du match
            dest_filename = f"{half}_ResNET_TF2_PCA512.npy"
            dest_path = match_dir / dest_filename
            
            try:
                shutil.copy2(source_path, dest_path)
                results["halves"][half] = {
                    "status": "success",
                    "features_path": str(dest_path),
                    "file_size": dest_path.stat().st_size,
                }
            except Exception as e:
                results["halves"][half] = {
                    "status": "error",
                    "message": str(e)
                }
        
        # Mettre à jour le statut du job
        job.features_status = "done"
        job.status = "processing"
        job.message = "Features importées avec succès."
        job.touch()
        
        return {
            "job_id": job_id,
            "match_dir": str(match_dir),
            "halves": results["halves"],
            "message": "Features importées avec succès. Le match peut maintenant être analysé.",
        }
