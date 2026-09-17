"""Bounded, serializable replay recording for completed and partial missions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path

from .models import Position


@dataclass(frozen=True, slots=True)
class ReplayFrame:
    tick: int
    player: Position
    ghosts: tuple[Position, ...]
    target: Position | None
    route: tuple[Position, ...]
    score: int
    lives: int
    collected: int
    event: str
    status: str

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["player"] = list(self.player)
        data["ghosts"] = [list(position) for position in self.ghosts]
        data["target"] = list(self.target) if self.target is not None else None
        data["route"] = [list(position) for position in self.route]
        return data


class ReplayRecorder:
    """Keep recent frames without allowing a long run to consume unlimited RAM."""

    def __init__(self, map_id: str, max_frames: int = 2_500) -> None:
        if max_frames < 2:
            raise ValueError("max_frames must be at least 2")
        self.map_id = map_id
        self.max_frames = max_frames
        self.frames: list[ReplayFrame] = []
        self._tick = 0

    def capture(
        self,
        *,
        player: Position,
        ghosts: tuple[Position, ...],
        target: Position | None,
        route: list[Position],
        score: int,
        lives: int,
        collected: int,
        event: str,
        status: str,
    ) -> ReplayFrame:
        frame = ReplayFrame(
            tick=self._tick,
            player=player,
            ghosts=ghosts,
            target=target,
            route=tuple(route),
            score=score,
            lives=lives,
            collected=collected,
            event=event,
            status=status,
        )
        self._tick += 1
        self.frames.append(frame)
        if len(self.frames) > self.max_frames:
            # Retain the initial frame plus the newest timeline segment.
            self.frames = [self.frames[0], *self.frames[-(self.max_frames - 1) :]]
        return frame

    def save(
        self,
        directory: str | Path,
        *,
        algorithm: str,
        heuristic: str,
        filename: str | None = None,
        overwrite: bool = False,
    ) -> Path:
        destination = Path(directory)
        destination.mkdir(parents=True, exist_ok=True)
        if filename is None:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"replay_{stamp}.json"
        path = destination / filename
        if path.exists() and not overwrite:
            raise FileExistsError(f"Refusing to overwrite replay: {path.name}")
        payload = {
            "format": "pacman-ai-replay-v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "map_id": self.map_id,
            "algorithm": algorithm,
            "heuristic": heuristic,
            "frame_count": len(self.frames),
            "frames": [frame.to_dict() for frame in self.frames],
        }
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return path
