"""Pure-Python model for the in-game custom map editor."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import json
from pathlib import Path

from .maze import MapConfig, Maze
from .models import Position


class EditorTool(str, Enum):
    FLOOR = "Floor"
    WALL = "Wall"
    START = "Start"
    EXIT = "Exit"
    PELLET = "Pellet"
    POWER = "Power"
    GHOST = "Ghost"
    TERRAIN_2 = "Cost 2"
    TERRAIN_3 = "Cost 3"


@dataclass(slots=True)
class MapEditor:
    """Editable copy of a maze; the active game remains untouched until save."""

    maze: Maze
    tool: EditorTool = EditorTool.WALL
    dirty: bool = False
    status: str = "Choose a tool, then click an interior grid cell"
    saved_path: Path | None = None

    @classmethod
    def from_maze(cls, source: Maze) -> "MapEditor":
        config = MapConfig(
            map_id=f"{source.config.map_id}_custom",
            name=f"{source.config.name} Custom",
            width=source.width,
            height=source.height,
            seed=0,
            loop_chance=0.0,
            food_count=len(source.foods),
            power_food_count=len(source.power_foods),
            ghost_count=len(source.ghost_starts),
            terrain_count=len(source.terrain_costs),
            accent=source.config.accent,
        )
        clone = Maze(
            config=config,
            walls=set(source.walls),
            start=source.start,
            exit=source.exit,
            foods=set(source.foods),
            power_foods=set(source.power_foods),
            ghost_starts=list(source.ghost_starts),
            terrain_costs=dict(source.terrain_costs),
        )
        return cls(clone)

    def set_tool(self, tool: EditorTool) -> None:
        self.tool = tool
        self.status = f"{tool.value} tool selected"

    def _inside(self, position: Position) -> bool:
        return 0 <= position[0] < self.maze.width and 0 <= position[1] < self.maze.height

    def _border(self, position: Position) -> bool:
        x, y = position
        return x in {0, self.maze.width - 1} or y in {0, self.maze.height - 1}

    def _clear_optional_entities(self, position: Position) -> None:
        self.maze.foods.discard(position)
        self.maze.power_foods.discard(position)
        self.maze.terrain_costs.pop(position, None)
        self.maze.ghost_starts = [item for item in self.maze.ghost_starts if item != position]

    def apply(self, position: Position) -> bool:
        """Apply the current brush and return whether the map changed."""

        if not self._inside(position):
            self.status = "Click inside the grid"
            return False
        if self._border(position):
            self.status = "The outer safety border must remain a wall"
            return False

        before = self.maze.to_explicit_dict()
        tool = self.tool

        if tool is EditorTool.WALL:
            if position in {self.maze.start, self.maze.exit}:
                self.status = "Move the start or exit before placing a wall here"
                return False
            self._clear_optional_entities(position)
            self.maze.walls.add(position)
        elif tool is EditorTool.FLOOR:
            self.maze.walls.discard(position)
            self._clear_optional_entities(position)
        elif tool is EditorTool.START:
            if position == self.maze.exit:
                self.status = "Start and exit must use different cells"
                return False
            self.maze.walls.discard(position)
            self._clear_optional_entities(position)
            self.maze.start = position
        elif tool is EditorTool.EXIT:
            if position == self.maze.start:
                self.status = "Start and exit must use different cells"
                return False
            self.maze.walls.discard(position)
            self._clear_optional_entities(position)
            self.maze.exit = position
        elif tool is EditorTool.PELLET:
            self.maze.walls.discard(position)
            self.maze.power_foods.discard(position)
            self.maze.foods.add(position)
        elif tool is EditorTool.POWER:
            self.maze.walls.discard(position)
            self.maze.foods.discard(position)
            self.maze.power_foods.add(position)
        elif tool is EditorTool.GHOST:
            self.maze.walls.discard(position)
            if position in self.maze.ghost_starts:
                self.maze.ghost_starts.remove(position)
            elif len(self.maze.ghost_starts) >= 4:
                self.status = "A maximum of four ghosts keeps the demo readable"
                return False
            else:
                self.maze.ghost_starts.append(position)
        elif tool in {EditorTool.TERRAIN_2, EditorTool.TERRAIN_3}:
            self.maze.walls.discard(position)
            self.maze.terrain_costs[position] = 2 if tool is EditorTool.TERRAIN_2 else 3

        changed = before != self.maze.to_explicit_dict()
        if changed:
            self.dirty = True
            self.saved_path = None
            self.status = f"Applied {tool.value} at {position[0]}, {position[1]}"
        return changed

    def validation_error(self) -> str | None:
        if not self.maze.foods and not self.maze.power_foods:
            return "Add at least one pellet before saving"
        if not self.maze.ghost_starts:
            return "Add at least one ghost before saving"
        try:
            self.maze.validate()
        except ValueError as exc:
            return str(exc)
        return None

    def validate(self) -> bool:
        error = self.validation_error()
        self.status = f"Cannot save: {error}" if error else "Map is connected and ready to save"
        return error is None

    def save(self, directory: str | Path, filename: str | None = None) -> Path:
        """Save a new explicit JSON map; no packaged map is overwritten."""

        error = self.validation_error()
        if error:
            self.status = f"Cannot save: {error}"
            raise ValueError(error)

        destination = Path(directory)
        destination.mkdir(parents=True, exist_ok=True)
        if filename is None:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"custom_map_{stamp}.json"
        path = destination / filename
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite existing map: {path.name}")

        map_id = path.stem
        name = f"Custom Studio {datetime.now().strftime('%H:%M:%S')}"
        data = self.maze.to_explicit_dict(name=name, map_id=map_id)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

        # Reloading validates the exact bytes that the game will later consume.
        Maze.from_file(path)
        self.saved_path = path
        self.dirty = False
        self.status = f"Saved and validated {path.name}"
        return path

