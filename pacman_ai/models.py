"""Shared data models for search and gameplay."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TypeAlias

Position: TypeAlias = tuple[int, int]


class Algorithm(str, Enum):
    """Search algorithms available in the visualizer."""

    BFS = "BFS"
    DFS = "DFS"
    UCS = "UCS"
    DIJKSTRA = "Dijkstra"
    A_STAR = "A*"

    @property
    def short_description(self) -> str:
        return {
            Algorithm.BFS: "Shortest path by steps on an unweighted grid",
            Algorithm.DFS: "Deep exploration; fast sometimes, not optimal",
            Algorithm.UCS: "Lowest accumulated movement and danger cost",
            Algorithm.DIJKSTRA: "Shortest weighted path with non-negative costs",
            Algorithm.A_STAR: "Weighted search guided by a goal heuristic",
        }[self]

    @property
    def uses_costs(self) -> bool:
        return self in {Algorithm.UCS, Algorithm.DIJKSTRA, Algorithm.A_STAR}


class HeuristicMode(str, Enum):
    """Heuristic variants available to the A* laboratory."""

    MANHATTAN = "Manhattan"
    EUCLIDEAN = "Euclidean"
    WEIGHTED = "Weighted A*"

    @property
    def short_label(self) -> str:
        return {
            HeuristicMode.MANHATTAN: "L1",
            HeuristicMode.EUCLIDEAN: "L2",
            HeuristicMode.WEIGHTED: "1.65×",
        }[self]

    @property
    def description(self) -> str:
        return {
            HeuristicMode.MANHATTAN: "Grid-aware and admissible for four-direction movement",
            HeuristicMode.EUCLIDEAN: "Straight-line estimate; admissible but less informed here",
            HeuristicMode.WEIGHTED: "Faster goal bias with no guarantee of the optimal route",
        }[self]

    @property
    def guarantees_optimality(self) -> bool:
        return self is not HeuristicMode.WEIGHTED


class GhostBehavior(str, Enum):
    """Transparent movement policy assigned to an advanced ghost."""

    AGGRESSIVE = "Aggressive"
    PREDICTIVE = "Predictive"
    RANDOM = "Random"
    DEFENSIVE = "Defensive"


@dataclass(slots=True)
class SearchResult:
    """A complete, visualizable result returned by a search algorithm."""

    algorithm: Algorithm
    found: bool
    path: list[Position] = field(default_factory=list)
    explored_order: list[Position] = field(default_factory=list)
    path_cost: float = 0.0
    elapsed_ms: float = 0.0
    frontier_peak: int = 0
    heuristic_mode: HeuristicMode | None = None

    @property
    def steps(self) -> int:
        """Number of moves in the returned path."""

        return max(0, len(self.path) - 1)

    @property
    def expanded_nodes(self) -> int:
        return len(self.explored_order)


@dataclass(slots=True)
class GhostState:
    """Logical state for one ghost."""

    name: str
    position: Position
    spawn: Position
    color: tuple[int, int, int]
    behavior: GhostBehavior = GhostBehavior.AGGRESSIVE


@dataclass(slots=True)
class AggregateMetrics:
    """Metrics accumulated across a complete run."""

    searches: int = 0
    expanded_nodes: int = 0
    planning_ms: float = 0.0
    travelled_steps: int = 0
    weighted_cost: float = 0.0

    def include(self, result: SearchResult) -> None:
        self.searches += 1
        self.expanded_nodes += result.expanded_nodes
        self.planning_ms += result.elapsed_ms
