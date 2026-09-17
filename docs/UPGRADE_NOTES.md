# Upgrade Notes and Backward Compatibility

## Preserved behavior

The upgrade started from the previously delivered ZIP. The original archive was
kept unchanged, and its complete regression suite passed before modification.

These original capabilities remain:

- BFS, DFS, UCS, Dijkstra, and A*;
- deterministic packaged maps;
- weighted terrain and ghost danger;
- pellets, power mode, lives, score, and exit;
- route/exploration visualization;
- moving ghosts and replanning;
- same-snapshot comparison;
- speed, pause, step, reset, map, and freeze controls;
- headless smoke testing.

## Additive changes

| Area | Upgrade | Compatibility decision |
|---|---|---|
| A* | Manhattan, Euclidean, Weighted modes | Manhattan remains default |
| Selection | Explainable AUTO controller | Manual five-algorithm selection remains |
| Ghosts | Four advanced policies | Classic BFS chase can be restored |
| Visualization | Cell risk heatmap | Can be hidden |
| Maps | Explicit custom-map format and studio | Packaged maps are never overwritten |
| Research | Multi-target experiment | Original one-target Compare remains |
| Explanation | Route rationale and guarantees | Reads existing results; does not change search |
| Replay | Bounded logical frames and JSON | Does not affect game rules |
| Reporting | CSV and PDF evidence | Created only on user request |
| UI | Play and AI Workbench tabs | Original play controls stay together |

## Important semantic changes

- The product name is now neutral: **Adaptive Pac-Man AI Pathfinding
  Laboratory**.
- Weighted A* is explicitly labeled non-optimal; it is not used by default.
- AUTO is described as a controller over the existing algorithms, never as an
  additional search algorithm.
- Advanced ghosts avoid occupying one another's destination cells.
- Custom maps are discovered recursively under `maps/custom/`.

## Regression strategy

The final verification runs:

1. all original algorithm, map, and session tests;
2. new heuristic, AUTO, ghost, editor, experiment, report, and replay tests;
3. Python compilation;
4. headless game startup/rendering;
5. a complete visual QA gallery;
6. PDF/CSV/JSON export inspection;
7. clean extracted-ZIP verification.
