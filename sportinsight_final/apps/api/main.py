from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Allows `uvicorn apps.api.main:app --reload` from repository root without installing the package.
REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from fastapi import UploadFile, File, Form
from fastapi.responses import JSONResponse

from apps.api.inference_service import create_inference_run, read_run_file
from apps.api.download_service import read_download_job, start_soccernet_download
from apps.api.media_service import build_clip, find_half_video, media_type_for, video_availability
from apps.api.match_service import list_checkpoints, list_matches, list_split_matches, list_splits, read_split_integrity
from apps.api.upload_service import (
    create_upload_job,
    get_upload_job,
    save_video_file,
    finalize_upload,
    list_upload_jobs,
    delete_upload_job,
    import_features_files,
)
from apps.api.features_service import extract_features_from_match_videos
from apps.api.schemas import (
    CheckpointSummary,
    ClipRequest,
    EventPrediction,
    HealthResponse,
    InferenceRequest,
    InferenceResponse,
    MatchSummary,
    SplitIntegrityResponse,
    SplitSummary,
    VideoAvailabilityResponse,
    SoccerNetDownloadRequest,
    SoccerNetDownloadStatus,
    RunSummary,
    UploadStatus,
)

app = FastAPI(title="SportInsight AI API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@app.get("/matches", response_model=list[MatchSummary])
def matches(
    root: str = Query("data/SoccerNet"),
    limit: int = Query(100, ge=1, le=1000),
    split_file: str | None = Query(None),
):
    return list_matches(root, limit=limit, split_file=split_file)


@app.get("/splits", response_model=list[SplitSummary])
def splits(splits_dir: str = Query("splits")):
    return list_splits(splits_dir)


@app.get("/splits/integrity", response_model=SplitIntegrityResponse)
def splits_integrity(splits_dir: str = Query("splits")):
    return read_split_integrity(splits_dir)


@app.get("/splits/{split_name}/matches", response_model=list[MatchSummary])
def split_matches(
    split_name: str,
    root: str = Query("data/SoccerNet"),
    splits_dir: str = Query("splits"),
    limit: int = Query(200, ge=1, le=2000),
):
    try:
        return list_split_matches(root=root, splits_dir=splits_dir, split_name=split_name, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/checkpoints", response_model=list[CheckpointSummary])
def checkpoints(root: str = Query("runs")):
    return list_checkpoints(root)


@app.post("/inference/run", response_model=InferenceResponse)
def run_inference_endpoint(request: InferenceRequest):
    try:
        return create_inference_run(request.model_dump())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/runs/{run_id}/events", response_model=list[EventPrediction])
def run_events(run_id: str):
    events = read_run_file(run_id, "events.json")
    if events is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return events


@app.get("/runs/{run_id}/summary", response_model=RunSummary)
def run_summary(run_id: str):
    summary = read_run_file(run_id, "summary.json")
    if summary is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return summary

@app.get("/media/video/availability", response_model=VideoAvailabilityResponse)
def media_video_availability(match_dir: str = Query(...)):
    return video_availability(match_dir)


@app.get("/media/video")
def media_video(match_dir: str = Query(...), half: int = Query(..., ge=1, le=2)):
    path = find_half_video(match_dir, half)
    if path is None:
        raise HTTPException(
            status_code=404,
            detail="Aucune vidéo trouvée pour cette mi-temps. Ajoute 1.mp4/1.mkv et 2.mp4/2.mkv dans le dossier du match.",
        )
    return FileResponse(path, media_type=media_type_for(path), filename=path.name)


@app.get("/media/clip")
def media_clip_get(
    match_dir: str = Query(...),
    half: int = Query(..., ge=1, le=2),
    timestamp: float = Query(..., ge=0.0),
    before_sec: float = Query(10.0, ge=0.0, le=120.0),
    after_sec: float = Query(10.0, ge=1.0, le=120.0),
):
    try:
        clip_path = build_clip(
            match_dir_value=match_dir,
            half=half,
            timestamp=timestamp,
            before_sec=before_sec,
            after_sec=after_sec,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    return FileResponse(clip_path, media_type="video/mp4", filename=clip_path.name)


@app.post("/media/clip")
def media_clip(request: ClipRequest):
    try:
        clip_path = build_clip(
            match_dir_value=request.match_dir,
            half=request.half,
            timestamp=request.timestamp,
            before_sec=request.before_sec,
            after_sec=request.after_sec,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    return FileResponse(clip_path, media_type="video/mp4", filename=clip_path.name)



@app.post("/download/soccernet/videos", response_model=SoccerNetDownloadStatus)
def download_soccernet_videos(request: SoccerNetDownloadRequest):
    try:
        return start_soccernet_download(request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/download/soccernet/status/{job_id}", response_model=SoccerNetDownloadStatus)
def download_soccernet_status(job_id: str):
    status = read_download_job(job_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Download job not found")
    return status


# ============================================================================
# API pour l'import et l'analyse de vidéos personnalisées
# ============================================================================

@app.post("/upload/create", response_model=dict)
def upload_create(match_name: str = Form(...)):
    """
    Crée un nouveau job d'upload pour un match.
    
    Retourne un job_id à utiliser pour uploader les vidéos des deux mi-temps.
    """
    try:
        job_id = create_upload_job(match_name)
        return {
            "job_id": job_id,
            "message": f"Job créé pour le match: {match_name}",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/upload/{job_id}/video/{half}", response_model=dict)
async def upload_video(
    job_id: str,
    half: int,
    file: UploadFile = File(...),
):
    """
    Upload une vidéo pour une mi-temps (1 ou 2).
    
    Accepte les formats: MP4, MKV, WebM, MOV, AVI.
    """
    if half not in (1, 2):
        raise HTTPException(status_code=400, detail="half doit être 1 ou 2")
    
    try:
        # Vérifier que le job existe
        job = get_upload_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
        
        # Lire les données de la vidéo
        video_data = await file.read()
        
        # Sauvegarder le fichier (préserver l'extension originale)
        result = save_video_file(job_id, half, video_data, original_filename=file.filename or "")
        
        return result
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/upload/{job_id}/finalize", response_model=UploadStatus)
def upload_finalize(job_id: str):
    """
    Finalise l'upload après avoir uploadé les deux mi-temps.
    
    Les deux mi-temps doivent avoir été uploadées avant d'appeler ce endpoint.
    """
    try:
        result = finalize_upload(job_id)
        return UploadStatus(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/upload/{job_id}/extract-features", response_model=dict)
def upload_extract_features(
    job_id: str,
    fps: float = Query(2.0, ge=0.5, le=30.0),
    device: str = Query("auto"),
):
    """
    Extrait les features ResNET des vidéos uploadées.
    
    Cela génère les fichiers .npy nécessaires pour l'inférence.
    """
    try:
        job = get_upload_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
        
        if not job.match_dir:
            raise HTTPException(status_code=400, detail="Match directory not set. Finalize upload first.")
        
        # Extraire les features
        results = extract_features_from_match_videos(
            job.match_dir,
            fps=fps,
            device=device,
        )
        
        return {
            "job_id": job_id,
            "status": "features_extracted",
            "match_dir": results["match_dir"],
            "halves": results["halves"],
            "message": "Features extraites avec succès. Le match peut maintenant être analysé.",
        }
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/upload/{job_id}/import-features", response_model=dict)
def upload_import_features(
    job_id: str,
    files: dict = Form(None),
):
    """
    Importe directement les fichiers .npy de features pré-extraits.
    
    Au lieu d'extraire les features des vidéos, utilise des fichiers .npy existants.
    Les fichiers doivent être nommés: 1_ResNET_TF2_PCA512.npy et 2_ResNET_TF2_PCA512.npy
    """
    try:
        job = get_upload_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
        
        if not job.match_dir:
            raise HTTPException(status_code=400, detail="Match directory not set. Finalize upload first.")
        
        # Obtenir les chemins des fichiers uploadés
        # Supposons que les fichiers sont uploadés via un endpoint séparé
        import json
        
        if files and isinstance(files, str):
            try:
                files = json.loads(files)
            except:
                pass
        
        if not files or not isinstance(files, dict):
            raise HTTPException(status_code=400, detail="No feature files provided")
        
        file_dict = {}
        for half_str, path_str in files.items():
            try:
                half = int(half_str)
                file_dict[half] = Path(path_str)
            except (ValueError, TypeError):
                continue
        
        if not file_dict:
            raise HTTPException(status_code=400, detail="No valid feature files provided")
        
        # Importer les features
        results = import_features_files(job_id, file_dict)
        return results
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/upload/{job_id}/upload-features")
async def upload_features_files(
    job_id: str,
    half: int = Form(...),
    file: UploadFile = File(...),
):
    """
    Endpoint pour uploader les fichiers .npy de features directement.
    
    Alternative à l'extraction vidéo - permet d'importer des features pré-extraites.
    """
    try:
        job = get_upload_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
        
        if half not in (1, 2):
            raise HTTPException(status_code=400, detail="half must be 1 or 2")
        
        if not job.match_dir:
            raise HTTPException(status_code=400, detail="Match directory not set. Create upload job first.")
        
        if not file.filename.endswith(".npy"):
            raise HTTPException(status_code=400, detail="File must be .npy format")
        
        # Sauvegarder le fichier de features
        match_dir = Path(job.match_dir)
        features_filename = f"{half}_ResNET_TF2_PCA512.npy"
        features_path = match_dir / features_filename
        
        # Lire et sauvegarder le fichier
        contents = await file.read()
        features_path.write_bytes(contents)
        
        # Mettre à jour le statut du job si les deux fichiers sont présents
        half_1_features = (match_dir / "1_ResNET_TF2_PCA512.npy").exists()
        half_2_features = (match_dir / "2_ResNET_TF2_PCA512.npy").exists()
        
        if half_1_features and half_2_features:
            job.features_status = "done"
            job.status = "processing"
            job.message = "Features importées. Prêt pour l'analyse."
            job.touch()
        else:
            job.message = f"Features mi-temps {half} uploadées"
            job.touch()
        
        return {
            "job_id": job_id,
            "half": half,
            "path": str(features_path),
            "size": len(contents),
            "status": job.features_status,
            "message": job.message,
        }
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/upload/{job_id}", response_model=UploadStatus)
def upload_status(job_id: str):
    """
    Récupère l'état d'un job d'upload.
    """
    job = get_upload_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    
    return UploadStatus(**job.as_dict())


@app.get("/upload", response_model=list)
def upload_list():
    """
    Liste tous les jobs d'upload.
    """
    return list_upload_jobs()


@app.delete("/upload/{job_id}")
def upload_delete(job_id: str):
    """
    Supprime un job d'upload et ses fichiers.
    """
    if delete_upload_job(job_id):
        return {"message": f"Job supprimé: {job_id}"}
    else:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
