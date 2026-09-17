"""Human-readable explanations for the active search decision."""

from __future__ import annotations

from dataclasses import dataclass

from .models import Algorithm, HeuristicMode, SearchResult


@dataclass(frozen=True, slots=True)
class AlgorithmExplanation:
    title: str
    data_structure: str
    priority_rule: str
    guarantee: str
    route_reason: str
    observation: str


def explain_result(
    algorithm: Algorithm,
    result: SearchResult | None,
    heuristic_mode: HeuristicMode,
    *,
    auto_reason: str = "",
) -> AlgorithmExplanation:
    structures = {
        Algorithm.BFS: "FIFO queue",
        Algorithm.DFS: "LIFO stack",
        Algorithm.UCS: "Min-priority queue",
        Algorithm.DIJKSTRA: "Min-priority queue + settled set",
        Algorithm.A_STAR: "Min-priority queue",
    }
    rules = {
        Algorithm.BFS: "Expand the shallowest discovered cell first.",
        Algorithm.DFS: "Expand the newest discovered cell first.",
        Algorithm.UCS: "Expand the cell with the smallest accumulated cost g(n).",
        Algorithm.DIJKSTRA: "Settle the cell with the smallest known distance.",
        Algorithm.A_STAR: (
            f"Expand the smallest f(n)=g(n)+h(n) using {heuristic_mode.value}."
        ),
    }
    guarantees = {
        Algorithm.BFS: "Fewest steps on this unweighted movement graph; not lowest danger cost.",
        Algorithm.DFS: "Complete on the finite grid, but neither shortest nor lowest-cost.",
        Algorithm.UCS: "Lowest cost because every movement and danger cost is non-negative.",
        Algorithm.DIJKSTRA: "Lowest cost because edges are non-negative.",
        Algorithm.A_STAR: (
            "Fast goal-directed search; optimal with this mode."
            if heuristic_mode.guarantees_optimality
            else "More aggressive goal direction; optimality is not guaranteed."
        ),
    }
    route_reasons = {
        Algorithm.BFS: "The route uses the fewest grid moves, even when a longer route is safer.",
        Algorithm.DFS: "The route reflects deterministic neighbor order and deep exploration.",
        Algorithm.UCS: "Terrain and ghost-danger penalties are added before each expansion.",
        Algorithm.DIJKSTRA: "The goal is accepted only after its cheapest distance is settled.",
        Algorithm.A_STAR: "Accumulated cost is balanced against an estimate of distance to the goal.",
    }
    if result is None:
        observation = "Run or step the AI to generate an evidence-based route observation."
    elif result.found:
        observation = (
            f"Observed route: {result.steps} steps, cost {result.path_cost:.1f}, "
            f"{result.expanded_nodes} expanded nodes, frontier peak {result.frontier_peak}, "
            f"planning time {result.elapsed_ms:.3f} ms."
        )
    else:
        observation = (
            f"No route was found after expanding {result.expanded_nodes} cells."
        )
    if auto_reason:
        observation = f"Auto-selector: {auto_reason}. {observation}"
    return AlgorithmExplanation(
        title=f"Why {algorithm.value} chose this route",
        data_structure=structures[algorithm],
        priority_rule=rules[algorithm],
        guarantee=guarantees[algorithm],
        route_reason=route_reasons[algorithm],
        observation=observation,
    )

