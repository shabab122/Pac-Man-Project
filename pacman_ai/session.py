"""Gameplay state and AI-controlled simulation rules.

This module has no Pygame dependency, which keeps the logic straightforward to
test in automated environments.
"""

from __future__ import annotations

import random
from pathlib import Path
from time import monotonic

from .algorithms import manhattan
from .maze import Maze, discover_map_files
from .models import AggregateMetrics, Algorithm, GhostState, Position, SearchResult
from .planner import choose_target, compare_algorithms, plan_route
from .settings import POWER_SECONDS, STARTING_LIVES

GHOST_COLORS = (
    (255, 82, 105),
    (255, 91, 190),
    (47, 218, 255),
    (255, 153, 55),
)
GHOST_NAMES = ("Blinky", "Pinky", "Inky", "Clyde")


class GameSession:
    """Owns one playable Pac-Man pathfinding mission."""

    def __init__(self, map_directory: str | Path) -> None:
        self.map_paths = discover_map_files(map_directory)
        self.map_index = 0
        self.algorithm = Algorithm.A_STAR
        self.speed = 1
        self.dynamic_ghosts = True
        self._rng = random.Random(9047)
        self.event_serial = 0
        self.last_event = "ready"
        self.load_map(0)

    def load_map(self, index: int) -> None:
        self.map_index = index % len(self.map_paths)
        self.maze = Maze.from_file(self.map_paths[self.map_index])
        self.foods = set(self.maze.foods)
        self.power_foods = set(self.maze.power_foods)
        self.total_collectibles = len(self.foods) + len(self.power_foods)
        self.player: Position = self.maze.start
        self.player_direction: Position = (1, 0)
        self.ghosts = [
            GhostState(
                name=GHOST_NAMES[index % len(GHOST_NAMES)],
                position=position,
                spawn=position,
                color=GHOST_COLORS[index % len(GHOST_COLORS)],
            )
            for index, position in enumerate(self.maze.ghost_starts)
        ]
        self.lives = STARTING_LIVES
        self.score = 0
        self.running = False
        self.paused = False
        self.won = False
        self.game_over = False
        self.route: list[Position] = []
        self.target: Position | None = None
        self.last_result: SearchResult | None = None
        self.comparison_results: list[SearchResult] = []
        self.metrics = AggregateMetrics()
        self.frightened_until = 0.0
        self.status = "Select an algorithm, then run the AI"
        self._emit("map_loaded")

    @property
    def ghost_positions(self) -> tuple[Position, ...]:
        return tuple(ghost.position for ghost in self.ghosts)

    @property
    def collected(self) -> int:
        return self.total_collectibles - len(self.foods) - len(self.power_foods)

    @property
    def progress(self) -> float:
        if self.total_collectibles == 0:
            return 1.0
        return self.collected / self.total_collectibles

    def is_frightened(self, now: float | None = None) -> bool:
        return (monotonic() if now is None else now) < self.frightened_until

    def _emit(self, event: str) -> None:
        self.last_event = event
        self.event_serial += 1

    def set_algorithm(self, algorithm: Algorithm) -> None:
        if algorithm == self.algorithm:
            return
        self.algorithm = algorithm
        self.route.clear()
        self.target = None
        self.last_result = None
        self.status = f"{algorithm.value} selected"
        self._emit("algorithm_selected")

    def set_speed(self, speed: int) -> None:
        if speed not in {1, 2, 4}:
            raise ValueError("Speed must be 1, 2, or 4")
        self.speed = speed
        self._emit("speed_changed")

    def toggle_dynamic_ghosts(self) -> None:
        self.dynamic_ghosts = not self.dynamic_ghosts
        state = "enabled" if self.dynamic_ghosts else "frozen"
        self.status = f"Dynamic ghosts {state}"
        self._emit("toggle_ghosts")

    def toggle_running(self) -> None:
        if self.won or self.game_over:
            return
        self.running = not self.running
        self.paused = False
        self.status = "AI running" if self.running else "AI stopped"
        self._emit("run" if self.running else "stop")

    def toggle_pause(self) -> None:
        if not self.running or self.won or self.game_over:
            return
        self.paused = not self.paused
        self.status = "Simulation paused" if self.paused else "AI running"
        self._emit("pause" if self.paused else "resume")

    def reset(self) -> None:
        algorithm = self.algorithm
        speed = self.speed
        dynamic_ghosts = self.dynamic_ghosts
        self.load_map(self.map_index)
        self.algorithm = algorithm
        self.speed = speed
        self.dynamic_ghosts = dynamic_ghosts
        self.status = "Mission reset"
        self._emit("reset")

    def next_map(self) -> None:
        algorithm = self.algorithm
        speed = self.speed
        dynamic_ghosts = self.dynamic_ghosts
        self.load_map(self.map_index + 1)
        self.algorithm = algorithm
        self.speed = speed
        self.dynamic_ghosts = dynamic_ghosts
        self.status = f"Loaded {self.maze.config.name}"
        self._emit("map_changed")

    def plan_next_route(self) -> SearchResult:
        self.target, result = choose_target(
            self.algorithm,
            self.maze,
            self.player,
            self.foods,
            self.power_foods,
            self.maze.exit,
            self.ghost_positions,
            self.is_frightened(),
        )
        self.last_result = result
        self.route = result.path[1:] if result.found else []
        self.metrics.include(result)
        if result.found:
            target_type = "exit" if self.target == self.maze.exit else "food"
            self.status = f"{self.algorithm.value} planned a route to {target_type}"
            self._emit("planned")
        else:
            self.status = "No route found from the current position"
            self.running = False
            self._emit("no_route")
        return result

    def step_player(self, now: float | None = None) -> None:
        if self.won or self.game_over or self.paused:
            return
        timestamp = monotonic() if now is None else now

        if not self.route:
            self.plan_next_route()
            if not self.route:
                # The player may already stand on the final exit.
                self._check_exit()
                return

        next_position = self.route[0]
        if next_position in self.ghost_positions and not self.is_frightened(timestamp):
            self.route.clear()
            self.status = "Route blocked by a ghost; replanning"
            self._emit("replan")
            return

        self.route.pop(0)
        previous = self.player
        self.player = next_position
        self.player_direction = (
            self.player[0] - previous[0],
            self.player[1] - previous[1],
        )
        self.metrics.travelled_steps += 1
        self.metrics.weighted_cost += self.maze.movement_cost(previous, self.player)
        self._collect(timestamp)
        self._resolve_collisions(timestamp)

        if self.target == self.player:
            self.route.clear()
            self.target = None
        self._check_exit()

    def _collect(self, now: float) -> None:
        if self.player in self.foods:
            self.foods.remove(self.player)
            self.score += 10
            self.status = "Data pellet collected"
            self._emit("collect")
        if self.player in self.power_foods:
            self.power_foods.remove(self.player)
            self.score += 50
            self.frightened_until = now + POWER_SECONDS
            self.status = "Power core active: ghosts are vulnerable"
            self._emit("power")

    def _check_exit(self) -> None:
        if self.player != self.maze.exit:
            return
        if self.foods or self.power_foods:
            self.status = "Exit locked: collect every data pellet"
            return
        self.won = True
        self.running = False
        self.score += 500 + self.lives * 100
        self.status = "Mission complete: optimized route secured"
        self._emit("win")

    def step_ghosts(self, now: float | None = None) -> None:
        if (
            not self.dynamic_ghosts
            or not self.running
            or self.paused
            or self.won
            or self.game_over
        ):
            return

        timestamp = monotonic() if now is None else now
        frightened = self.is_frightened(timestamp)
        occupied: set[Position] = set()

        for ghost in self.ghosts:
            available = [
                position
                for position in self.maze.neighbors(ghost.position)
                if position not in occupied
            ]
            if not available:
                occupied.add(ghost.position)
                continue

            if frightened:
                best_distance = max(manhattan(position, self.player) for position in available)
                choices = [
                    position
                    for position in available
                    if manhattan(position, self.player) == best_distance
                ]
                next_position = self._rng.choice(choices)
            else:
                chase = plan_route(
                    Algorithm.BFS,
                    self.maze,
                    ghost.position,
                    self.player,
                )
                preferred = chase.path[1] if len(chase.path) > 1 else ghost.position
                if preferred in available:
                    next_position = preferred
                else:
                    next_position = min(
                        available,
                        key=lambda position: (manhattan(position, self.player), position),
                    )

            ghost.position = next_position
            occupied.add(next_position)

        self._resolve_collisions(timestamp)

    def _resolve_collisions(self, now: float) -> None:
        colliding = [ghost for ghost in self.ghosts if ghost.position == self.player]
        if not colliding:
            return

        if self.is_frightened(now):
            for ghost in colliding:
                ghost.position = ghost.spawn
                self.score += 200
            self.status = "Ghost neutralized"
            self._emit("ghost_eaten")
            return

        self.lives -= 1
        self.running = False
        self.route.clear()
        self.target = None
        self.last_result = None
        self.player = self.maze.start
        self.player_direction = (1, 0)
        for ghost in self.ghosts:
            ghost.position = ghost.spawn

        if self.lives <= 0:
            self.game_over = True
            self.status = "Mission failed: no lives remaining"
            self._emit("game_over")
        else:
            self.status = f"Collision detected: {self.lives} lives remaining"
            self._emit("collision")

    def comparison_target(self) -> Position:
        if self.target is not None:
            return self.target
        targets = self.foods | self.power_foods
        if not targets:
            return self.maze.exit
        # A distant target produces a more informative classroom comparison than
        # an adjacent pellet, especially before the first run begins.
        return max(
            targets,
            key=lambda target: (manhattan(self.player, target), target[1], target[0]),
        )

    def compare_current_problem(self) -> list[SearchResult]:
        target = self.comparison_target()
        self.comparison_results = compare_algorithms(
            self.maze,
            self.player,
            target,
            self.ghost_positions,
            self.is_frightened(),
        )
        self.status = "Algorithm comparison ready"
        self._emit("compare")
        return self.comparison_results
