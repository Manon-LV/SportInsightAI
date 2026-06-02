from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

# Allows `uvicorn apps.api.main:app --reload` from repository root without installing the package.
REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from apps.api.inference_service import create_inference_run, read_run_file
from apps.api.download_service import read_download_job, start_soccernet_download
from apps.api.media_service import build_clip, find_half_video, media_type_for, video_availability
from apps.api.match_service import list_checkpoints, list_matches, list_split_matches, list_splits, read_split_integrity
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
