"""Deterministic maze generation and map loading."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import json
from pathlib import Path
import random
from typing import Any, Iterable

from .models import Position


@dataclass(frozen=True, slots=True)
class MapConfig:
    map_id: str
    name: str
    width: int
    height: int
    seed: int
    loop_chance: float
    food_count: int
    power_food_count: int
    ghost_count: int
    terrain_count: int
    accent: tuple[int, int, int]

    @classmethod
    def for_explicit_map(cls, data: dict[str, Any]) -> "MapConfig":
        """Build display metadata for a hand-authored map."""

        width = int(data["width"])
        height = int(data["height"])
        if width < 11 or height < 11:
            raise ValueError("Custom map width and height must be at least 11")
        accent_values = tuple(int(value) for value in data.get("accent", (45, 224, 255)))
        if len(accent_values) != 3 or any(not 0 <= value <= 255 for value in accent_values):
            raise ValueError("accent must contain three RGB values from 0 to 255")
        return cls(
            map_id=str(data.get("id", "custom_map")),
            name=str(data.get("name", "Custom Map")),
            width=width,
            height=height,
            seed=int(data.get("seed", 0)),
            loop_chance=0.0,
            food_count=len(data.get("foods", [])),
            power_food_count=len(data.get("power_foods", [])),
            ghost_count=len(data.get("ghost_starts", [])),
            terrain_count=len(data.get("terrain_costs", [])),
            accent=accent_values,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MapConfig":
        required = {
            "id",
            "name",
            "width",
            "height",
            "seed",
            "loop_chance",
            "food_count",
            "power_food_count",
            "ghost_count",
            "terrain_count",
            "accent",
        }
        missing = required.difference(data)
        if missing:
            raise ValueError(f"Map configuration is missing: {sorted(missing)}")

        width = int(data["width"])
        height = int(data["height"])
        if width < 11 or height < 11 or width % 2 == 0 or height % 2 == 0:
            raise ValueError("Maze width and height must be odd integers of at least 11")
        loop_chance = float(data["loop_chance"])
        if not 0.0 <= loop_chance <= 1.0:
            raise ValueError("loop_chance must be between 0 and 1")

        accent_values = tuple(int(value) for value in data["accent"])
        if len(accent_values) != 3 or any(not 0 <= value <= 255 for value in accent_values):
            raise ValueError("accent must contain three RGB values from 0 to 255")

        return cls(
            map_id=str(data["id"]),
            name=str(data["name"]),
            width=width,
            height=height,
            seed=int(data["seed"]),
            loop_chance=loop_chance,
            food_count=int(data["food_count"]),
            power_food_count=int(data["power_food_count"]),
            ghost_count=int(data["ghost_count"]),
            terrain_count=int(data["terrain_count"]),
            accent=accent_values,
        )


@dataclass(slots=True)
class Maze:
    config: MapConfig
    walls: set[Position]
    start: Position
    exit: Position
    foods: set[Position]
    power_foods: set[Position]
    ghost_starts: list[Position]
    terrain_costs: dict[Position, int]

    @property
    def width(self) -> int:
        return self.config.width

    @property
    def height(self) -> int:
        return self.config.height

    @classmethod
    def from_file(cls, path: str | Path) -> "Maze":
        path = Path(path)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"Map file not found: {path}") from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"Map file contains invalid JSON: {path}") from exc
        if data.get("format") == "explicit-v1":
            return cls.from_explicit_dict(data)
        return cls.generate(MapConfig.from_dict(data))

    @staticmethod
    def _positions(values: Iterable[Iterable[int]], field_name: str) -> set[Position]:
        positions: set[Position] = set()
        for value in values:
            pair = tuple(int(item) for item in value)
            if len(pair) != 2:
                raise ValueError(f"{field_name} entries must contain x and y")
            positions.add((pair[0], pair[1]))
        return positions

    @classmethod
    def from_explicit_dict(cls, data: dict[str, Any]) -> "Maze":
        """Load a validated map created by the built-in Map Studio."""

        config = MapConfig.for_explicit_map(data)
        walls = cls._positions(data.get("walls", []), "walls")
        foods = cls._positions(data.get("foods", []), "foods")
        power_foods = cls._positions(data.get("power_foods", []), "power_foods")
        ghost_starts = sorted(
            cls._positions(data.get("ghost_starts", []), "ghost_starts"),
            key=lambda item: (item[1], item[0]),
        )
        start_values = tuple(int(item) for item in data.get("start", (1, 1)))
        exit_values = tuple(
            int(item)
            for item in data.get("exit", (config.width - 2, config.height - 2))
        )
        if len(start_values) != 2 or len(exit_values) != 2:
            raise ValueError("start and exit must contain x and y")

        terrain_costs: dict[Position, int] = {}
        for entry in data.get("terrain_costs", []):
            if not isinstance(entry, dict) or "position" not in entry or "cost" not in entry:
                raise ValueError("terrain_costs entries require position and cost")
            position_values = tuple(int(item) for item in entry["position"])
            if len(position_values) != 2:
                raise ValueError("terrain position must contain x and y")
            cost = int(entry["cost"])
            if cost not in {1, 2, 3}:
                raise ValueError("terrain cost must be 1, 2, or 3")
            if cost > 1:
                terrain_costs[(position_values[0], position_values[1])] = cost

        maze = cls(
            config=config,
            walls=walls,
            start=(start_values[0], start_values[1]),
            exit=(exit_values[0], exit_values[1]),
            foods=foods,
            power_foods=power_foods,
            ghost_starts=ghost_starts,
            terrain_costs=terrain_costs,
        )
        maze.validate()
        return maze

    def to_explicit_dict(self, *, name: str | None = None, map_id: str | None = None) -> dict[str, Any]:
        """Serialize the current maze without changing its generated source."""

        order = lambda position: (position[1], position[0])
        return {
            "format": "explicit-v1",
            "id": map_id or self.config.map_id,
            "name": name or self.config.name,
            "width": self.width,
            "height": self.height,
            "accent": list(self.config.accent),
            "start": list(self.start),
            "exit": list(self.exit),
            "walls": [list(position) for position in sorted(self.walls, key=order)],
            "foods": [list(position) for position in sorted(self.foods, key=order)],
            "power_foods": [
                list(position) for position in sorted(self.power_foods, key=order)
            ],
            "ghost_starts": [list(position) for position in self.ghost_starts],
            "terrain_costs": [
                {"position": list(position), "cost": cost}
                for position, cost in sorted(
                    self.terrain_costs.items(), key=lambda item: order(item[0])
                )
            ],
        }

    @classmethod
    def generate(cls, config: MapConfig) -> "Maze":
        """Generate a connected perfect maze, then open loops for more choices."""

        rng = random.Random(config.seed)
        walls: set[Position] = {
            (x, y) for y in range(config.height) for x in range(config.width)
        }
        start = (1, 1)
        walls.remove(start)
        stack = [start]

        while stack:
            x, y = stack[-1]
            candidates: list[tuple[Position, Position]] = []
            for dx, dy in ((2, 0), (0, 2), (-2, 0), (0, -2)):
                target = (x + dx, y + dy)
                if not (1 <= target[0] < config.width - 1):
                    continue
                if not (1 <= target[1] < config.height - 1):
                    continue
                if target not in walls:
                    continue
                between = (x + dx // 2, y + dy // 2)
                candidates.append((target, between))

            if not candidates:
                stack.pop()
                continue

            target, between = rng.choice(candidates)
            walls.discard(between)
            walls.discard(target)
            stack.append(target)

        # Open selected wall separators to create cycles and alternative routes.
        separators: list[Position] = []
        for y in range(1, config.height - 1):
            for x in range(1, config.width - 1):
                position = (x, y)
                if position not in walls:
                    continue
                horizontal = (x - 1, y) not in walls and (x + 1, y) not in walls
                vertical = (x, y - 1) not in walls and (x, y + 1) not in walls
                if horizontal ^ vertical:
                    separators.append(position)
        rng.shuffle(separators)
        for position in separators:
            if rng.random() < config.loop_chance:
                walls.remove(position)

        # A small central arena improves readability and ghost movement.
        center_x = config.width // 2
        center_y = config.height // 2
        for y in range(center_y - 1, center_y + 2):
            for x in range(center_x - 2, center_x + 3):
                if 0 < x < config.width - 1 and 0 < y < config.height - 1:
                    walls.discard((x, y))

        temporary = cls(
            config=config,
            walls=walls,
            start=start,
            exit=start,
            foods=set(),
            power_foods=set(),
            ghost_starts=[],
            terrain_costs={},
        )
        distances = temporary.distances_from(start)
        if not distances:
            raise ValueError("Generated maze contains no walkable cells")
        exit_position = max(distances, key=lambda pos: (distances[pos], pos[1], pos[0]))

        open_cells = [position for position in distances if position not in {start, exit_position}]
        ghost_starts = cls._choose_ghost_starts(
            open_cells, distances, config.ghost_count, rng, config.width + config.height
        )

        reserved = {start, exit_position, *ghost_starts}
        food_candidates = [position for position in open_cells if position not in reserved]
        rng.shuffle(food_candidates)

        power_count = min(config.power_food_count, max(0, len(food_candidates) // 8))
        power_foods = set(
            sorted(food_candidates, key=lambda pos: distances[pos], reverse=True)[:power_count]
        )
        normal_candidates = [position for position in food_candidates if position not in power_foods]
        foods = set(normal_candidates[: min(config.food_count, len(normal_candidates))])

        terrain_candidates = [
            position
            for position in normal_candidates[config.food_count :]
            if position not in reserved
        ]
        rng.shuffle(terrain_candidates)
        terrain_costs: dict[Position, int] = {}
        for index, position in enumerate(terrain_candidates[: config.terrain_count]):
            terrain_costs[position] = 3 if index % 4 == 0 else 2

        maze = cls(
            config=config,
            walls=walls,
            start=start,
            exit=exit_position,
            foods=foods,
            power_foods=power_foods,
            ghost_starts=ghost_starts,
            terrain_costs=terrain_costs,
        )
        maze.validate()
        return maze

    @staticmethod
    def _choose_ghost_starts(
        open_cells: list[Position],
        distances: dict[Position, int],
        count: int,
        rng: random.Random,
        scale: int,
    ) -> list[Position]:
        candidates = sorted(open_cells, key=lambda pos: distances[pos], reverse=True)
        selected: list[Position] = []
        minimum_spacing = max(4, scale // 10)

        for candidate in candidates:
            if distances[candidate] < scale // 4:
                continue
            if any(
                abs(candidate[0] - other[0]) + abs(candidate[1] - other[1])
                < minimum_spacing
                for other in selected
            ):
                continue
            selected.append(candidate)
            if len(selected) == count:
                return selected

        remaining = [position for position in candidates if position not in selected]
        rng.shuffle(remaining)
        selected.extend(remaining[: max(0, count - len(selected))])
        return selected

    def validate(self) -> None:
        entities = {self.start, self.exit, *self.ghost_starts, *self.foods, *self.power_foods}
        invalid = [position for position in entities if not self.is_walkable(position)]
        if invalid:
            raise ValueError(f"Map entities placed on invalid cells: {invalid}")

        reachable = set(self.distances_from(self.start))
        unreachable = entities.difference(reachable)
        if unreachable:
            raise ValueError(f"Map contains unreachable entities: {sorted(unreachable)}")

        if self.start == self.exit:
            raise ValueError("Start and exit must be different cells")

        invalid_terrain = [
            position
            for position, cost in self.terrain_costs.items()
            if not self.is_walkable(position) or cost not in {1, 2, 3}
        ]
        if invalid_terrain:
            raise ValueError(f"Map contains invalid weighted terrain: {invalid_terrain}")

        if self.foods & self.power_foods:
            raise ValueError("A cell cannot contain both a normal and power pellet")

        for x in range(self.width):
            if (x, 0) not in self.walls or (x, self.height - 1) not in self.walls:
                raise ValueError("The outer map border must be closed by walls")
        for y in range(self.height):
            if (0, y) not in self.walls or (self.width - 1, y) not in self.walls:
                raise ValueError("The outer map border must be closed by walls")

    def is_walkable(self, position: Position) -> bool:
        x, y = position
        return 0 <= x < self.width and 0 <= y < self.height and position not in self.walls

    def neighbors(self, position: Position) -> Iterable[Position]:
        x, y = position
        # Stable order makes classroom demonstrations reproducible.
        for candidate in ((x + 1, y), (x, y + 1), (x - 1, y), (x, y - 1)):
            if self.is_walkable(candidate):
                yield candidate

    def movement_cost(self, _current: Position, destination: Position) -> float:
        return float(self.terrain_costs.get(destination, 1))

    def distances_from(self, source: Position) -> dict[Position, int]:
        if not self.is_walkable(source):
            return {}
        distances = {source: 0}
        frontier: deque[Position] = deque([source])
        while frontier:
            node = frontier.popleft()
            for neighbor in self.neighbors(node):
                if neighbor in distances:
                    continue
                distances[neighbor] = distances[node] + 1
                frontier.append(neighbor)
        return distances


def discover_map_files(map_directory: str | Path) -> list[Path]:
    """Return map files in deterministic display order."""

    paths = sorted(
        Path(map_directory).glob("**/*.json"),
        key=lambda path: ("custom" in path.parts, path.name.lower()),
    )
    if not paths:
        raise FileNotFoundError(f"No JSON maps found in {Path(map_directory).resolve()}")
    return paths
