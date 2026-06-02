from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

from .utils import read_json


@dataclass(frozen=True)
class Event:
    game_dir: str
    half: int
    time_sec: float
    label: str
    class_idx: int
    visibility: str | None = None


_GAME_TIME_RE = re.compile(r"\s*(\d+)\s*-\s*(\d+):(\d+)\s*")


def parse_game_time(game_time: str) -> tuple[int, float]:
    """Parse SoccerNet gameTime strings such as '1 - 42:15'."""
    match = _GAME_TIME_RE.match(game_time)
    if not match:
        raise ValueError(f"Invalid SoccerNet gameTime: {game_time!r}")
    half = int(match.group(1))
    minutes = int(match.group(2))
    seconds = int(match.group(3))
    return half, float(60 * minutes + seconds)


def load_events_from_labels(
    labels_path: str | Path,
    classes: Sequence[str],
    include_not_shown: bool = True,
) -> List[Event]:
    """Load target events from a SoccerNet Labels-v2.json file.

    The loader uses `gameTime` to get a timestamp relative to the half.
    This is more explicit than the raw `position` field, which can depend on
    the export convention.
    """
    labels_path = Path(labels_path)
    game_dir = str(labels_path.parent)
    label_to_idx = {name: idx for idx, name in enumerate(classes)}
    raw = read_json(labels_path)
    annotations = raw.get("annotations", [])

    events: List[Event] = []
    for ann in annotations:
        label = ann.get("label")
        if label not in label_to_idx:
            continue
        visibility = ann.get("visibility")
        if not include_not_shown and visibility == "not shown":
            continue
        half, time_sec = parse_game_time(ann["gameTime"])
        events.append(
            Event(
                game_dir=game_dir,
                half=half,
                time_sec=time_sec,
                label=label,
                class_idx=label_to_idx[label],
                visibility=visibility,
            )
        )
    events.sort(key=lambda e: (e.half, e.time_sec, e.class_idx))
    return events


def filter_events(events: Iterable[Event], half: int | None = None) -> List[Event]:
    out = [e for e in events if half is None or e.half == half]
    out.sort(key=lambda e: (e.half, e.time_sec, e.class_idx))
    return out
