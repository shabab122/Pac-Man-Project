# Five-Minute Demo and Viva Guide

## Recommended live demonstration

### 0:00–0:40 — Problem and interface

Say:

> Traditional movement may be long or unsafe. We model the maze as a graph and
> compare five search algorithms while Pac-Man collects every pellet and reaches
> the exit.

Open the game and point out the maze, algorithm selector, route overlay, ghost
danger aura, and metrics.

### 0:40–1:30 — BFS versus DFS

Freeze ghosts for a repeatable result. Select BFS, click Step Once, and explain
the breadth-wise explored cells. Select DFS and repeat. Point out that DFS finds
a route but does not guarantee the shortest one.

### 1:30–2:30 — Weighted search

Select UCS or Dijkstra. Point at purple/pink terrain and red ghost danger. Explain
that the planner may accept extra steps to reduce total cost.

State clearly:

> UCS and Dijkstra are mathematically equivalent in this single-goal,
> non-negative weighted implementation. We included both because the syllabus
> names both approaches and our code shows their conventional structures.

### 2:30–3:25 — A* and heuristic

Select A*. Explain:

```text
f(n) = g(n) + h(n)
```

`g(n)` is known cost. `h(n)` is Manhattan distance to the target. A* uses both to
focus exploration while keeping the result optimal under the current snapshot.

### 3:25–4:15 — Compare mode

Press `C`. Explain that every row used exactly the same start, target, costs, and
ghost positions. Compare steps, cost, expanded nodes, frontier peak, and time.
Do not claim that the smallest runtime is universally fastest from one tiny run.

### 4:15–5:00 — Dynamic behavior and conclusion

Close the comparison, activate ghosts, set speed to 2×, and run the AI. Explain
that a moving ghost can invalidate a static search result, so the controller
checks the next step and replans.

Finish with the limitation: this system uses classical graph search, not machine
learning or reinforcement learning.

## Likely viva questions

### Why is this an AI project?

It uses state-space search, goal testing, path cost, heuristic search, and dynamic
replanning. These are core classical AI problem-solving techniques.

### Why use a graph?

Each valid grid cell is a node and each legal move is an edge. Pathfinding then
becomes a standard graph-search problem.

### Why can BFS be unsafe?

BFS minimizes the number of steps and does not read terrain or ghost-risk costs.
A short path can therefore pass close to a ghost.

### Why is DFS not optimal?

DFS commits to one deep branch based on neighbor order. It can reach the goal
before examining a much shorter alternative.

### Are UCS and Dijkstra different here?

Their naming and common teaching context differ, but with non-negative costs, a
priority queue, one source, and early stopping at one target, they expand by the
same accumulated-cost rule and normally return the same result.

### Why is Manhattan distance admissible?

The game moves only up, down, left, or right, and every move costs at least 1.
Manhattan distance cannot be greater than the real remaining route cost.

### Is A* always faster?

No. It often expands fewer nodes toward one goal when the heuristic is helpful.
Its worst case can behave like Dijkstra, and measured runtime also includes
implementation and hardware effects.

### What makes the game dynamic?

Ghost positions change after planning. The controller treats a newly occupied
next cell as invalid and searches again from Pac-Man's current state.

### Why freeze ghosts during comparison?

A fair comparison requires identical input. If ghosts move between runs, the
cost function changes and the metrics no longer describe the same problem.

## Backup plan

If the presentation computer cannot open a Pygame window:

1. Show `screenshots/gameplay.png`.
2. Run `python run_tests.py` to prove the logic works.
3. Explain the comparison table and algorithm guide from the documentation.
4. Use a team member's verified laptop for the live animation if permitted.

