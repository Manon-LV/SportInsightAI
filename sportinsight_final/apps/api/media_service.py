from __future__ import annotations

import subprocess
from pathlib import Path
from shutil import which

REPO_ROOT = Path(__file__).resolve().parents[2]
CLIP_CACHE_DIR = Path(__file__).resolve().parent / "storage" / "clips"
CLIP_CACHE_DIR.mkdir(parents=True, exist_ok=True)

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v"}
MEDIA_TYPES = {
    ".mp4": "video/mp4",
    ".m4v": "video/mp4",
    ".webm": "video/webm",
    ".mkv": "video/x-matroska",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
}


def resolve_project_path(path_value: str) -> Path:
    """Resolve a path passed by the local frontend.

    Relative paths are interpreted from the repository root. Absolute paths are
    accepted for local development, but the resolved path must exist.
    """
    raw = Path(path_value)
    path = raw if raw.is_absolute() else REPO_ROOT / raw
    return path.resolve()


def media_type_for(path: Path) -> str:
    return MEDIA_TYPES.get(path.suffix.lower(), "application/octet-stream")


def _video_candidates(match_dir: Path) -> list[Path]:
    if not match_dir.exists() or not match_dir.is_dir():
        return []
    return sorted(
        [path for path in match_dir.iterdir() if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS],
        key=lambda path: path.name.lower(),
    )


def find_half_video(match_dir_value: str, half: int) -> Path | None:
    """Find the best local video file for a SoccerNet half.

    Common SoccerNet layouts use files such as 1.mkv / 2.mkv, 1.mp4 / 2.mp4,
    or variants prefixed by the half number. If exact names are absent, the
    function falls back to the sorted list of video files.
    """
    match_dir = resolve_project_path(match_dir_value)
    candidates = _video_candidates(match_dir)
    if not candidates:
        return None

    half_str = str(half)
    exact_names = [
        f"{half_str}.mp4",
        f"{half_str}.mkv",
        f"{half_str}.webm",
        f"{half_str}.mov",
        f"{half_str}.avi",
        f"{half_str}_720p.mp4",
        f"{half_str}_720p.mkv",
        f"{half_str}_224p.mp4",
        f"{half_str}_224p.mkv",
        f"{half_str}_HQ.mp4",
        f"{half_str}_HQ.mkv",
        f"{half_str}_LQ.mp4",
        f"{half_str}_LQ.mkv",
    ]
    lookup = {path.name.lower(): path for path in candidates}
    for name in exact_names:
        if name.lower() in lookup:
            return lookup[name.lower()]

    prefixed = [path for path in candidates if path.stem.lower().startswith(half_str)]
    if prefixed:
        return prefixed[0]

    semantic_tokens = [f"half{half_str}", f"half_{half_str}", f"period{half_str}", f"period_{half_str}"]
    semantic = [path for path in candidates if any(token in path.stem.lower() for token in semantic_tokens)]
    if semantic:
        return semantic[0]

    if len(candidates) >= half:
        return candidates[half - 1]
    return None


def video_availability(match_dir_value: str) -> dict:
    match_dir = resolve_project_path(match_dir_value)
    result = {
        "match_dir": str(match_dir),
        "halves": {},
    }
    for half in (1, 2):
        path = find_half_video(match_dir_value, half)
        result["halves"][str(half)] = {
            "available": path is not None,
            "name": path.name if path else None,
            "path": str(path) if path else None,
            "media_type": media_type_for(path) if path else None,
        }
    return result


def ffmpeg_available() -> bool:
    return which("ffmpeg") is not None


def build_clip(
    match_dir_value: str,
    half: int,
    timestamp: float,
    before_sec: float = 10.0,
    after_sec: float = 10.0,
) -> Path:
    """Create and cache a small MP4 clip around an event.

    This is optional: it requires ffmpeg on the user's machine. The frontend can
    still use /media/video when ffmpeg is unavailable.
    """
    source = find_half_video(match_dir_value, half)
    if source is None:
        raise FileNotFoundError(
            "Aucune vidéo trouvée pour cette mi-temps. Ajoute 1.mp4/1.mkv et 2.mp4/2.mkv dans le dossier du match."
        )
    if not ffmpeg_available():
        raise RuntimeError("ffmpeg est introuvable. Installe ffmpeg ou utilise la lecture de la mi-temps complète.")

    start = max(0.0, timestamp - before_sec)
    duration = max(1.0, before_sec + after_sec)
    safe_name = f"{source.parent.name}_{half}_{int(timestamp * 10)}_{int(before_sec)}_{int(after_sec)}.mp4"
    safe_name = "".join(ch if ch.isalnum() or ch in {"_", "-", "."} else "_" for ch in safe_name)
    output = CLIP_CACHE_DIR / safe_name
    if output.exists() and output.stat().st_size > 0:
        return output

    command = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{start:.3f}",
        "-i",
        str(source),
        "-t",
        f"{duration:.3f}",
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(output),
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr[-1200:] or "ffmpeg n'a pas pu générer l'extrait vidéo.")
    return output
