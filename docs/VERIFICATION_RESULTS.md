# Verified Results

## Automated checks

Verification environment:

- Python 3.12.14
- pygame-ce 2.5.6
- pytest 8.4.2

Both commands passed:

```bash
python run_tests.py
pytest
```

Result: **10 tests passed**.

## Controlled full-mission comparison

The following values came from a complete run on packaged map 1, Cyber Citadel.
For repeatability, ghosts were removed and the simulation used the same food,
terrain, start, exit, target-selection rule, and neighbor order for every engine.

| Algorithm | Mission complete | Travelled steps | Terrain cost | Expanded nodes | Searches | Final score |
|---|---:|---:|---:|---:|---:|---:|
| BFS | Yes | 250 | 272 | 1,168 | 28 | 1,190 |
| DFS | Yes | 664 | 706 | 4,137 | 28 | 1,190 |
| UCS | Yes | 252 | 260 | 1,093 | 28 | 1,190 |
| Dijkstra | Yes | 252 | 260 | 1,093 | 28 | 1,190 |
| A* | Yes | 252 | 260 | 624 | 28 | 1,190 |

## Interpretation

- BFS used two fewer steps than the weighted algorithms, but crossed more costly
  terrain, giving a terrain cost of 272 instead of 260.
- DFS completed the mission but took a substantially longer route.
- UCS and Dijkstra matched, as expected for this problem definition.
- A* matched the optimal weighted cost and expanded fewer nodes than UCS and
  Dijkstra in this controlled run.

These results describe this packaged map and controlled configuration. They do
not prove that one algorithm has the smallest runtime or node count on every map.

