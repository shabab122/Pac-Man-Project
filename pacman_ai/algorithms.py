"""Search algorithms used by Pac-Man and the comparison laboratory.

The five algorithms intentionally share one problem interface so their results
can be compared fairly on the same maze, target, movement costs, and hazards.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import heapq
import itertools
from math import inf
from time import perf_counter
from typing import Callable, Iterable

from .models import Algorithm, Position, SearchResult

NeighborFunction = Callable[[Position], Iterable[Position]]
CostFunction = Callable[[Position, Position], float]
HeuristicFunction = Callable[[Position, Position], float]


@dataclass(frozen=True, slots=True)
class SearchProblem:
    start: Position
    goal: Position
    neighbors: NeighborFunction
    step_cost: CostFunction


def manhattan(a: Position, b: Position) -> float:
    """Return Manhattan distance for four-directional grid movement."""

    return float(abs(a[0] - b[0]) + abs(a[1] - b[1]))


def _reconstruct(
    parents: dict[Position, Position | None], goal: Position
) -> list[Position]:
    if goal not in parents:
        return []
    node: Position | None = goal
    path: list[Position] = []
    while node is not None:
        path.append(node)
        node = parents[node]
    path.reverse()
    return path


def _path_cost(path: list[Position], cost: CostFunction) -> float:
    return sum(cost(current, nxt) for current, nxt in zip(path, path[1:]))


def _finish(
    algorithm: Algorithm,
    started: float,
    parents: dict[Position, Position | None],
    goal: Position,
    explored: list[Position],
    frontier_peak: int,
    cost_fn: CostFunction,
) -> SearchResult:
    path = _reconstruct(parents, goal)
    return SearchResult(
        algorithm=algorithm,
        found=bool(path),
        path=path,
        explored_order=explored,
        path_cost=_path_cost(path, cost_fn),
        elapsed_ms=(perf_counter() - started) * 1000.0,
        frontier_peak=frontier_peak,
    )


def breadth_first_search(problem: SearchProblem) -> SearchResult:
    """Find the fewest-step path with a FIFO queue.

    BFS does not use movement weights while choosing a path. The returned
    ``path_cost`` still reports the real cost of the selected path so the UI can
    compare it with cost-aware algorithms.
    """

    started = perf_counter()
    frontier: deque[Position] = deque([problem.start])
    parents: dict[Position, Position | None] = {problem.start: None}
    explored: list[Position] = []
    frontier_peak = 1

    while frontier:
        node = frontier.popleft()
        explored.append(node)
        if node == problem.goal:
            break
        for neighbor in problem.neighbors(node):
            if neighbor in parents:
                continue
            parents[neighbor] = node
            frontier.append(neighbor)
        frontier_peak = max(frontier_peak, len(frontier))

    return _finish(
        Algorithm.BFS,
        started,
        parents,
        problem.goal,
        explored,
        frontier_peak,
        problem.step_cost,
    )


def depth_first_search(problem: SearchProblem) -> SearchResult:
    """Find a path with a LIFO stack; the result is not guaranteed optimal."""

    started = perf_counter()
    frontier: list[Position] = [problem.start]
    parents: dict[Position, Position | None] = {problem.start: None}
    explored: list[Position] = []
    frontier_peak = 1

    while frontier:
        node = frontier.pop()
        explored.append(node)
        if node == problem.goal:
            break

        # Reverse keeps visual exploration deterministic relative to BFS.
        neighbors = list(problem.neighbors(node))
        for neighbor in reversed(neighbors):
            if neighbor in parents:
                continue
            parents[neighbor] = node
            frontier.append(neighbor)
        frontier_peak = max(frontier_peak, len(frontier))

    return _finish(
        Algorithm.DFS,
        started,
        parents,
        problem.goal,
        explored,
        frontier_peak,
        problem.step_cost,
    )


def uniform_cost_search(problem: SearchProblem) -> SearchResult:
    """Expand the node with the lowest accumulated path cost."""

    started = perf_counter()
    counter = itertools.count()
    frontier: list[tuple[float, int, Position]] = [(0.0, next(counter), problem.start)]
    best_cost: dict[Position, float] = {problem.start: 0.0}
    parents: dict[Position, Position | None] = {problem.start: None}
    explored: list[Position] = []
    frontier_peak = 1

    while frontier:
        current_cost, _, node = heapq.heappop(frontier)
        if current_cost != best_cost.get(node):
            continue
        explored.append(node)
        if node == problem.goal:
            break

        for neighbor in problem.neighbors(node):
            candidate = current_cost + problem.step_cost(node, neighbor)
            if candidate >= best_cost.get(neighbor, inf):
                continue
            best_cost[neighbor] = candidate
            parents[neighbor] = node
            heapq.heappush(frontier, (candidate, next(counter), neighbor))
        frontier_peak = max(frontier_peak, len(frontier))

    return _finish(
        Algorithm.UCS,
        started,
        parents,
        problem.goal,
        explored,
        frontier_peak,
        problem.step_cost,
    )


def dijkstra_search(problem: SearchProblem) -> SearchResult:
    """Compute shortest weighted distances until the goal becomes permanent.

    In this single-source, single-goal grid, Dijkstra and UCS have the same
    expansion rule. This independent implementation is kept for teaching and
    side-by-side comparison.
    """

    started = perf_counter()
    counter = itertools.count()
    distances: dict[Position, float] = {problem.start: 0.0}
    parents: dict[Position, Position | None] = {problem.start: None}
    settled: set[Position] = set()
    frontier: list[tuple[float, int, Position]] = [(0.0, next(counter), problem.start)]
    explored: list[Position] = []
    frontier_peak = 1

    while frontier:
        distance, _, node = heapq.heappop(frontier)
        if node in settled or distance != distances.get(node):
            continue
        settled.add(node)
        explored.append(node)
        if node == problem.goal:
            break

        for neighbor in problem.neighbors(node):
            if neighbor in settled:
                continue
            candidate = distance + problem.step_cost(node, neighbor)
            if candidate >= distances.get(neighbor, inf):
                continue
            distances[neighbor] = candidate
            parents[neighbor] = node
            heapq.heappush(frontier, (candidate, next(counter), neighbor))
        frontier_peak = max(frontier_peak, len(frontier))

    return _finish(
        Algorithm.DIJKSTRA,
        started,
        parents,
        problem.goal,
        explored,
        frontier_peak,
        problem.step_cost,
    )


def a_star_search(
    problem: SearchProblem, heuristic: HeuristicFunction = manhattan
) -> SearchResult:
    """Find a lowest-cost path using g(n) + an admissible grid heuristic."""

    started = perf_counter()
    counter = itertools.count()
    g_score: dict[Position, float] = {problem.start: 0.0}
    parents: dict[Position, Position | None] = {problem.start: None}
    frontier: list[tuple[float, int, Position]] = [
        (heuristic(problem.start, problem.goal), next(counter), problem.start)
    ]
    closed: set[Position] = set()
    explored: list[Position] = []
    frontier_peak = 1

    while frontier:
        _, _, node = heapq.heappop(frontier)
        if node in closed:
            continue
        closed.add(node)
        explored.append(node)
        if node == problem.goal:
            break

        for neighbor in problem.neighbors(node):
            candidate = g_score[node] + problem.step_cost(node, neighbor)
            if candidate >= g_score.get(neighbor, inf):
                continue
            g_score[neighbor] = candidate
            parents[neighbor] = node
            priority = candidate + heuristic(neighbor, problem.goal)
            heapq.heappush(frontier, (priority, next(counter), neighbor))
        frontier_peak = max(frontier_peak, len(frontier))

    return _finish(
        Algorithm.A_STAR,
        started,
        parents,
        problem.goal,
        explored,
        frontier_peak,
        problem.step_cost,
    )


SEARCH_FUNCTIONS = {
    Algorithm.BFS: breadth_first_search,
    Algorithm.DFS: depth_first_search,
    Algorithm.UCS: uniform_cost_search,
    Algorithm.DIJKSTRA: dijkstra_search,
    Algorithm.A_STAR: a_star_search,
}


def run_search(algorithm: Algorithm, problem: SearchProblem) -> SearchResult:
    """Run one of the supported algorithms."""

    try:
        search_function = SEARCH_FUNCTIONS[algorithm]
    except KeyError as exc:
        raise ValueError(f"Unsupported algorithm: {algorithm}") from exc
    return search_function(problem)


def compare_searches(problem: SearchProblem) -> list[SearchResult]:
    """Run every algorithm against the exact same problem instance."""

    return [run_search(algorithm, problem) for algorithm in Algorithm]

