"""AI route planning on top of the search algorithms."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from .algorithms import SearchProblem, compare_searches, manhattan, run_search
from .maze import Maze
from .models import Algorithm, Position, SearchResult


def danger_penalty(position: Position, ghosts: Iterable[Position]) -> float:
    """Return a soft risk penalty based on distance from active ghosts."""

    ghost_list = list(ghosts)
    if not ghost_list:
        return 0.0
    distance = min(manhattan(position, ghost) for ghost in ghost_list)
    if distance == 0:
        return 40.0
    if distance == 1:
        return 12.0
    if distance == 2:
        return 5.0
    if distance == 3:
        return 2.0
    return 0.0


def make_cost_function(
    maze: Maze, ghost_positions: Iterable[Position], frightened: bool = False
) -> Callable[[Position, Position], float]:
    ghosts = tuple(ghost_positions)

    def cost(current: Position, destination: Position) -> float:
        base = maze.movement_cost(current, destination)
        return base if frightened else base + danger_penalty(destination, ghosts)

    return cost


def make_problem(
    maze: Maze,
    start: Position,
    goal: Position,
    ghost_positions: Iterable[Position] = (),
    frightened: bool = False,
) -> SearchProblem:
    return SearchProblem(
        start=start,
        goal=goal,
        neighbors=maze.neighbors,
        step_cost=make_cost_function(maze, ghost_positions, frightened),
    )


def plan_route(
    algorithm: Algorithm,
    maze: Maze,
    start: Position,
    goal: Position,
    ghost_positions: Iterable[Position] = (),
    frightened: bool = False,
) -> SearchResult:
    return run_search(
        algorithm,
        make_problem(maze, start, goal, ghost_positions, frightened),
    )


def choose_target(
    algorithm: Algorithm,
    maze: Maze,
    start: Position,
    foods: set[Position],
    power_foods: set[Position],
    exit_position: Position,
    ghost_positions: Iterable[Position] = (),
    frightened: bool = False,
) -> tuple[Position, SearchResult]:
    """Choose a reachable collectible, then produce the route to it.

    Only the nearest Manhattan candidates are evaluated. This keeps the live
    visualization responsive while still allowing cost-aware algorithms to
    choose a slightly longer but safer target.
    """

    targets = foods | power_foods
    if not targets:
        result = plan_route(
            algorithm,
            maze,
            start,
            exit_position,
            ghost_positions,
            frightened,
        )
        return exit_position, result

    candidates = sorted(
        targets,
        key=lambda target: (manhattan(start, target), target[1], target[0]),
    )[:8]
    evaluated: list[tuple[tuple[float, int, int, int], Position, SearchResult]] = []

    for target in candidates:
        result = plan_route(
            algorithm,
            maze,
            start,
            target,
            ghost_positions,
            frightened,
        )
        if not result.found:
            continue
        primary = result.path_cost if algorithm.uses_costs else float(result.steps)
        score = (primary, result.steps, target[1], target[0])
        evaluated.append((score, target, result))

    if not evaluated:
        # The generator guarantees connectivity, so this is defensive only.
        target = min(targets, key=lambda item: manhattan(start, item))
        return target, plan_route(
            algorithm, maze, start, target, ghost_positions, frightened
        )

    _, target, result = min(evaluated, key=lambda item: item[0])
    return target, result


def compare_algorithms(
    maze: Maze,
    start: Position,
    goal: Position,
    ghost_positions: Iterable[Position] = (),
    frightened: bool = False,
) -> list[SearchResult]:
    return compare_searches(
        make_problem(maze, start, goal, ghost_positions, frightened)
    )

