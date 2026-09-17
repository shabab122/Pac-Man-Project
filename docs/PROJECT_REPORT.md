# Project Proposal and Implementation Report

## Project title

**Adaptive and Explainable Pac-Man Pathfinding Using Classical AI Search**

Course context: Artificial Intelligence Laboratory

## 1. Problem statement

A shortest route by cell count is not always the safest or cheapest route when
terrain and nearby ghosts have different costs. A game demonstration also needs
to show *why* a route was selected and compare algorithms fairly.

The project asks:

> How can classical AI search guide Pac-Man through a changing weighted maze
> while making route quality, search effort, heuristic behavior, and decisions
> visible and reproducible?

The technical problems are:

- represent a maze as a graph;
- find valid routes around walls;
- model terrain and ghost danger;
- compare algorithms on identical input;
- react when moving ghosts invalidate a route;
- explain algorithm choices and guarantees;
- create and validate custom maps safely;
- produce evidence that can be inspected after the demo.

## 2. Proposed solution

The solution is a Python desktop game built with Pygame Community Edition.
Every walkable cell is a graph node and each legal four-direction move is an
edge. Pac-Man selects a pellet or exit, plans a route, displays explored nodes
and metrics, moves one cell, and replans when required.

The game includes manual BFS, DFS, UCS, Dijkstra, and A*. An optional
explainable AUTO controller chooses among those five using deterministic rules.
AUTO does not replace or modify the required algorithms.

The AI Workbench adds:

- Manhattan, Euclidean, and Weighted A*;
- Aggressive, Predictive, Random, and Defensive ghost policies;
- fixed-snapshot comparison and multi-scenario experiments;
- a route explanation panel;
- logical replay and JSON saving;
- CSV and PDF reports;
- a visual Map Studio that creates new validated maps.

## 3. Objectives

- Preserve five independent, inspectable classical-search implementations.
- Demonstrate unweighted versus weighted planning.
- Compare steps, cost, expanded nodes, frontier peak, and time fairly.
- Show the role and limitation of A* heuristics.
- Make dynamic replanning and ghost behavior observable.
- Provide reproducible experiments rather than unsupported performance claims.
- Keep setup local and beginner-friendly.
- Validate maps, exports, and game behavior automatically.

## 4. Key features

### Search and explainability

- BFS, DFS, UCS, Dijkstra, and A*
- Manual and explainable AUTO selection
- Manhattan, Euclidean, and Weighted A*
- Explored-order animation and route overlay
- Per-route explanation of structure, priority, guarantee, and evidence
- Same-snapshot algorithm and heuristic comparisons

### Established game system

- Three deterministic neon mazes
- Pellets, power pellets, score, lives, and locked exit
- Weighted terrain
- Four transparent advanced ghost policies
- Classic BFS ghost mode
- Ghost risk heatmap
- Dynamic replanning
- Speed, pause, step, reset, map, and freeze controls

### Research and creation tools

- Five-target controlled experiment
- Three timing samples per algorithm/target
- CSV raw-data export
- PDF summary report
- Bounded mission replay and JSON export
- Safe custom Map Studio
- Headless smoke test and visual QA gallery

## 5. State and cost model

A state is `(x, y)`. Walls are excluded. A state has at most four neighbors.

For weighted algorithms:

```text
step_cost = terrain_cost(destination) + ghost_danger(destination)
```

Terrain cost is 1, 2, or 3. Ghost danger is:

| Manhattan distance | Added cost |
|---:|---:|
| 0 | 40 |
| 1 | 12 |
| 2 | 5 |
| 3 | 2 |
| 4+ | 0 |

BFS and DFS do not use weights for path selection. They still report the actual
weighted cost of the returned path.

## 6. Algorithms

| Algorithm | Data structure | Uses weights | Guarantee in this finite grid |
|---|---|---:|---|
| BFS | FIFO queue | No | Fewest steps |
| DFS | LIFO stack | No | Finds a route, not necessarily optimal |
| UCS | Min-priority queue | Yes | Lowest weighted cost |
| Dijkstra | Priority queue + settled set | Yes | Lowest weighted cost |
| A* | Priority queue | Yes | Depends on heuristic mode |

### A* modes

```text
f(n) = g(n) + w × h(n)
```

- Manhattan: `h(n)=|dx|+|dy|`, `w=1`; admissible and consistent.
- Euclidean: `h(n)=sqrt(dx²+dy²)`, `w=1`; admissible but weaker here.
- Weighted A*: Manhattan with `w=1.65`; stronger goal bias, no optimality
  guarantee.

### UCS and Dijkstra

With one source, one goal, non-negative costs, and early termination, both
normally expand using the same accumulated-cost priority and return the same
answer. They remain separate functions for teaching and code comparison.

## 7. Dynamic behavior

Search runs on a snapshot. A ghost may move afterward. Before Pac-Man enters the
next route cell, the controller checks whether that cell now contains an active
ghost. If blocked, the old route is discarded and a new search begins.

Advanced ghost policies are:

- Aggressive: BFS toward the current player cell.
- Predictive: aims four cells ahead of the player direction.
- Random: selects a deterministic-seeded legal random move.
- Defensive: retreats when Pac-Man is close and guards the exit when distant.

Power mode temporarily changes every active ghost policy to flee behavior.

## 8. AUTO selection

AUTO uses simple visible rules:

- active ghost danger → A*;
- short weighted target → UCS;
- other weighted target → Dijkstra;
- nearby unweighted target → BFS;
- distant unweighted target → A*.

The selected algorithm and reason are displayed. DFS remains available manually
but is not selected automatically because it has no route-quality guarantee.

## 9. Map Studio safety

Map Studio clones the active maze. A user can edit floor, walls, start, exit,
pellets, power pellets, ghosts, and cost-2/cost-3 terrain.

Before saving, the editor verifies:

- closed outer wall;
- distinct valid start and exit;
- at least one pellet and ghost;
- every entity reachable from the start;
- no conflicting pellet types;
- valid weighted terrain.

Saving creates a timestamped `explicit-v1` file under `maps/custom/`. The
packaged source map is not modified.

## 10. Experiment design

The experiment selects up to five deterministic targets distributed from near
to far, including the exit. Each algorithm receives the same start, target,
terrain, ghost positions, risk cost, and power state.

Recorded metrics:

- route found;
- route steps;
- weighted route cost;
- expanded nodes;
- peak frontier;
- average planning milliseconds.

Timing is averaged over three runs but remains hardware-dependent. Conclusions
should prioritize deterministic path and search-work metrics.

## 11. Technology

| Technology | Purpose |
|---|---|
| Python 3.10+ | Algorithms, game rules, editor, replay, experiments |
| pygame-ce 2.5.6 | Graphics, input, timing, procedural audio |
| ReportLab 4.4.9 | PDF experiment report |
| JSON/CSV | Maps, replay, raw evidence |
| `deque`, `heapq`, `dataclasses`, `enum` | Core implementation |
| unittest / pytest | Regression, feature, and integration tests |

There is no API, database, cloud service, or pre-trained model.

## 12. Validation

The test suite checks:

- valid routes for all five algorithms;
- BFS shortest-step behavior;
- weighted optimality of UCS, Dijkstra, and default Manhattan A*;
- unreachable-goal safety;
- deterministic connected packaged maps;
- complete static missions;
- reset and compatibility behavior;
- all A* modes;
- deterministic AUTO selection;
- legal advanced ghost movement;
- explicit-map round-trip;
- non-mutating Map Studio save;
- experiment coverage and CSV/PDF generation;
- replay capture and JSON export.

Use `python run_tests.py`, `python main.py --smoke-test`, and
`python main.py --qa-gallery qa_gallery`.

## 13. Limitations

- This is classical symbolic search, not machine learning.
- AUTO uses transparent rules rather than a learned policy.
- Weighted A* may return a non-optimal route.
- Small-map timing is noisy.
- Target selection optimizes one segment at a time, not the globally shortest
  complete pellet tour.
- Replays store logical state rather than video.

