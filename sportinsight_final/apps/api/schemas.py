from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "sportinsight-api"


class MatchSummary(BaseModel):
    id: str
    path: str
    name: str
    has_first_half: bool
    has_second_half: bool
    split: str | None = None


class SplitSummary(BaseModel):
    name: str
    path: str
    exists: bool
    count: int


class SplitIntegrityResponse(BaseModel):
    counts: dict[str, int]
    overlap_count: int
    overlaps: list[dict]
    is_disjoint: bool


class CheckpointSummary(BaseModel):
    id: str
    path: str
    name: str


class EventPrediction(BaseModel):
    half: int
    timestamp: float
    gameTime: str
    label: str
    score: float


class VideoHalfInfo(BaseModel):
    available: bool
    name: str | None = None
    path: str | None = None
    media_type: str | None = None


class VideoAvailabilityResponse(BaseModel):
    match_dir: str
    halves: dict[str, VideoHalfInfo]




class SoccerNetDownloadRequest(BaseModel):
    root: str = Field("data/SoccerNet", description="Dossier local de destination SoccerNet")
    password: str | None = Field(None, description="Mot de passe SoccerNet/NDA. Optionnel si SOCCERNET_PASSWORD est défini.")
    split: list[Literal["train", "valid", "test", "challenge"]] = Field(default_factory=lambda: ["train", "valid", "test"])
    resolution: Literal["224p", "720p", "both"] = "224p"
    game: str | None = Field(None, description="Match unique au format league/season/game. Si absent, télécharge les splits.")
    include_features: bool = False
    include_labels: bool = False


class SoccerNetDownloadStatus(BaseModel):
    job_id: str
    status: Literal["queued", "running", "done", "error"]
    created_at: str
    updated_at: str
    root: str
    files: list[str]
    split: list[str]
    game: str | None = None
    message: str
    error: str | None = None


class ClipRequest(BaseModel):
    match_dir: str
    half: int = Field(..., ge=1, le=2)
    timestamp: float = Field(..., ge=0.0)
    before_sec: float = Field(10.0, ge=0.0, le=120.0)
    after_sec: float = Field(10.0, ge=1.0, le=120.0)


class InferenceRequest(BaseModel):
    match_dir: str = Field(..., description="Dossier SoccerNet contenant Labels-v2.json et les features .npy")
    checkpoint: str = Field(..., description="Chemin vers best.pt ou last.pt")
    half: Literal["first", "second", "both"] = "both"
    score_threshold: float = Field(0.30, ge=0.0, le=1.0)
    nms_radius_sec: float = Field(6.0, ge=0.0)
    selected_classes: list[str] | None = None
    device: str = "auto"


class RunSummary(BaseModel):
    run_id: str
    match_dir: str
    checkpoint: str
    half: str
    event_count: int
    counts_by_class: dict[str, int]
    counts_by_half: dict[str, int]


class InferenceResponse(BaseModel):
    run_id: str
    events: list[EventPrediction]
    summary: RunSummary


class UploadStatus(BaseModel):
    job_id: str
    status: Literal["uploading", "processing", "done", "error"]
    created_at: str
    updated_at: str
    match_name: str
    half_1_path: str | None = None
    half_2_path: str | None = None
    half_1_size: int = 0
    half_2_size: int = 0
    features_status: Literal["pending", "extracting", "done", "error"] = "pending"
    match_dir: str | None = None
    message: str
    error: str | None = None


class VideoUploadResponse(BaseModel):
    job_id: str
    half: int
    path: str
    size: int


class FeaturesExtractionStatus(BaseModel):
    job_id: str
    status: Literal["success", "error"]
    message: str
    match_dir: str | None = None
    halves: dict[int, dict] = {}
