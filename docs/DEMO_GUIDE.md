# Five-Minute Demo and Viva Guide

## Recommended live demonstration

### 0:00–0:35 — Problem and established game

Say:

> A route with the fewest cells is not always the safest route. This game turns
> each walkable cell into a graph node and compares five classical AI searches
> while terrain and ghosts create different costs.

Point out the maze, route, explored cells, risk heatmap, score, lives, and exit.

### 0:35–1:20 — Five original algorithms

Freeze ghosts for repeatability. Select BFS and step once. Then select DFS.
Explain:

- BFS uses a queue and guarantees the fewest steps.
- DFS uses a stack and may find a longer path.
- BFS/DFS do not optimize weighted danger.

Select UCS or Dijkstra and show how weighted terrain and risk affect the route.

State:

> UCS and Dijkstra normally match here because the grid has non-negative costs,
> one source, one goal, and both expand by the lowest accumulated cost.

### 1:20–2:05 — A* heuristic laboratory

Select A*, open **AI Workbench**, then **Heuristics**.

```text
f(n) = g(n) + w × h(n)
```

- Manhattan and Euclidean use `w=1` and remain admissible.
- Weighted A* uses `w=1.65`; it may expand fewer cells but is not guaranteed
  optimal.

Do not call Weighted A* universally faster or better.

### 2:05–2:45 — Explainable AUTO and ghost intelligence

Enable AUTO. Point to the selected engine and visible reason.

Say:

> AUTO is a transparent controller that chooses one of the five required
> algorithms. It is not a sixth algorithm.

Show the four ghost policy labels:

- Aggressive;
- Predictive;
- Random;
- Defensive.

Switch to Classic ghost AI briefly to demonstrate backward compatibility.

### 2:45–3:35 — Experiment and explanation

Open **Experiment**. Explain that five deterministic targets and unchanged
snapshot conditions are used. Compare average steps, cost, expanded nodes, and
time.

Open **Explain Route** and show:

- data structure;
- expansion rule;
- correctness/optimality statement;
- route reason;
- current measured evidence.

### 3:35–4:20 — Map Studio and replay

Open **Map Studio**. Select a terrain or pellet brush and edit one safe interior
cell. Press **Validate**.

Explain:

> The editor works on a copy, checks connectivity and entity placement, then
> saves a new JSON map. Packaged maps are not overwritten.

Return without saving during a short demo if time is limited. Open **Replay** to
show logical frames and telemetry.

### 4:20–5:00 — Export and conclusion

Open **Export CSV/PDF**.

- CSV: raw scenario evidence;
- PDF: formatted summary;
- JSON: replay timeline.

Finish:

> The upgraded system preserves the original classical searches but adds
> explainability, controlled experimentation, creation tools, and reproducible
> evidence. It is classical AI, not reinforcement learning.

## Likely viva questions

### Why is this an AI project?

It uses state-space search, a goal test, path cost, heuristic guidance, dynamic
replanning, and explainable decision rules.

### Why is the maze a graph?

Each walkable cell is a node; each legal up/down/left/right move is an edge.

### Why can BFS choose an unsafe path?

BFS minimizes steps and ignores terrain/risk when choosing. A short route can
pass close to a ghost.

### Why is DFS not optimal?

DFS follows one deep branch based on neighbor order and can reach the goal
before examining shorter or cheaper alternatives.

### Why do UCS and Dijkstra match?

Here both use a min-priority queue, non-negative costs, one source, one target,
and early stopping. Their accumulated-cost expansion rules therefore match.

### Why is Manhattan admissible?

The player moves only horizontally or vertically and each step costs at least
one. Manhattan distance cannot overestimate the remaining true cost.

### Why is Euclidean usually weaker here?

Straight-line distance is no greater than Manhattan distance on this movement
model, so it gives less specific guidance while remaining admissible.

### Why can Weighted A* lose optimality?

Multiplying the heuristic by 1.65 can make estimated remaining distance dominate
known path cost. The search may accept an earlier but more expensive goal route.

### Is AUTO machine learning?

No. AUTO is an explainable deterministic rule set that selects an existing
algorithm.

### What makes ghost AI different?

Each ghost has a visible policy: current-position chase, ahead prediction,
seeded random movement, or defensive retreat/guard behavior.

### How is comparison fair?

Every algorithm receives the same start, goal, map, terrain, ghost positions,
and power state.

### Why not trust the smallest time alone?

Sub-millisecond measurements vary across computers and background load.
Deterministic steps, cost, expanded nodes, and frontier peak are stronger
evidence.

### How does Map Studio protect previous work?

It edits a copied `Maze`, validates it, creates a new timestamped file, and
refuses to overwrite an existing file.

### What is replay storing?

Logical frames: player, ghosts, route, target, score, lives, event, and status.
It is inspectable JSON rather than a large video.

## Backup plan

If the classroom machine cannot create a Pygame window:

1. Show the verified images in `screenshots/`.
2. Open the sample PDF and CSV from `sample_outputs/`.
3. Run `python run_tests.py`.
4. Explain the architecture and algorithm tables from the documentation.

