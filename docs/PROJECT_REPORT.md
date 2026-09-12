# Project Proposal and Implementation Report

## Project title

**Optimized Pac-Man Pathfinding Using Artificial Intelligence**

Course context: Artificial Intelligence Lab, United International University  
Team: Group 7

## 1. Problem statement

Traditional Pac-Man movement controlled by fixed directions or uninformed manual
choices can take unnecessarily long routes, move toward hazards, and explore the
maze inefficiently. A route that has the fewest cells is also not always the
safest route when terrain and nearby ghosts carry different costs.

The project therefore asks:

> How can classical AI search algorithms guide Pac-Man to collect all food and
> reach the exit while exposing the trade-off between route length, risk, search
> effort, and planning time?

The main technical problems are:

- representing the maze as a graph;
- finding a route around walls;
- handling weighted terrain and ghost danger;
- comparing algorithms on the same input;
- responding when moving ghosts make an earlier route unsafe;
- presenting search behavior clearly enough for an AI Lab demonstration.

## 2. Proposed solution

The solution is a Python desktop simulation built with Pygame Community Edition.
Every walkable maze cell becomes a graph node. Legal up, down, left, and right
moves become graph edges.

Pac-Man automatically selects a nearby remaining pellet, runs the selected search
algorithm, visualizes explored nodes and the returned path, and moves through the
route. When no pellet remains, the planner targets the exit. Moving ghosts create
a soft danger cost around their current locations. A blocked next step triggers
replanning from the new game state.

The interface also provides a comparison mode. It freezes one logical snapshot
and runs BFS, DFS, UCS, Dijkstra, and A* from the same start cell to the same goal.

## 3. Objectives

- Implement five classical search algorithms without a pathfinding library.
- Make every search result reconstructable and visually inspectable.
- Compare step count, weighted cost, expanded nodes, frontier size, and runtime.
- Demonstrate the difference between unweighted and weighted planning.
- Keep maps deterministic so a classroom result can be repeated.
- Provide a complete game loop with lives, score, food, ghosts, power mode, and exit.
- Make the project easy to install, test, explain, and extend.

## 4. Key features

### AI and visualization

- BFS, DFS, UCS, Dijkstra, and A* selection
- Animated explored-node overlay
- Current path and target marker
- Automatic food target selection
- Dynamic route replanning
- Same-snapshot algorithm comparison

### Game system

- Three generated but deterministic mazes
- Normal and power pellets
- Three lives and score system
- Moving BFS-controlled ghosts
- Temporary frightened-ghost mode
- Locked exit that opens after collection
- Adjustable simulation speed

### Reliability and usability

- Validated JSON map definitions
- Graceful fallback when an audio device is unavailable
- Headless smoke-test and screenshot modes
- Standard-library and pytest-compatible automated tests
- Windows, macOS, and Linux instructions

## 5. Algorithm and approach

### State representation

A state is a coordinate `(x, y)`, where `x` is the column and `y` is the row.
Walls are excluded. A state can have up to four neighbors.

### Goal test

For one search segment, the test is:

```text
current_position == target_position
```

### Cost model

For weighted algorithms:

```text
step_cost = terrain_cost(destination) + ghost_danger(destination)
```

Terrain costs are 1, 2, or 3. Ghost danger adds:

| Manhattan distance from a ghost | Added danger cost |
|---:|---:|
| 0 cells | 40 |
| 1 cell | 12 |
| 2 cells | 5 |
| 3 cells | 2 |
| 4 or more cells | 0 |

BFS and DFS ignore these weights while choosing a path, but the system calculates
the actual weighted cost afterward for comparison.

### A* heuristic

```text
h(n) = |x_current - x_goal| + |y_current - y_goal|
f(n) = g(n) + h(n)
```

The heuristic is Manhattan distance. It never overestimates the remaining cost
because movement uses four directions and every step costs at least 1. Therefore,
A* returns an optimal weighted path under the current static snapshot.

### Dynamic behavior

Search algorithms plan against a snapshot. Ghosts can move after that search.
Before Pac-Man takes the next step, the controller checks whether a non-frightened
ghost now occupies that cell. If so, it discards the old route and searches again.

See `ALGORITHMS.md` for pseudocode, properties, and complexity.

## 6. Programming language and technologies

| Technology | Purpose |
|---|---|
| Python 3.10+ | Algorithms, data model, game logic, and entry point |
| Pygame Community Edition 2.5.6 | Window, graphics, input, timing, and optional audio |
| JSON | Small, readable map configuration files |
| `dataclasses`, `enum`, `heapq`, `deque` | Typed state, algorithms, queues, and priority queues |
| `unittest` | Dependency-free automated verification |
| pytest 8.4.2 | Optional developer-friendly test execution |
| Git and GitHub | Recommended version control and collaboration |

No AI API, database, network service, or pre-trained model is needed.

## 7. System workflow

1. Load and validate a deterministic maze.
2. Select one of five algorithms.
3. Select a nearby remaining food target, or the exit when food is finished.
4. Build a search problem from the maze, target, terrain, and ghost positions.
5. Run the algorithm and reconstruct its path.
6. Visualize explored states and route metrics.
7. Move Pac-Man and update pellets, score, power mode, ghosts, and collisions.
8. Replan when the route finishes or becomes blocked.
9. Unlock and enter the exit to complete the mission.

## 8. Expected results

- BFS should return the fewest-step path on an unweighted grid.
- DFS should find a path but may produce a long, non-optimal route.
- UCS and Dijkstra should return the same minimum-cost result in this problem.
- A* should return the same optimal cost while often expanding fewer cells toward
  one target because Manhattan distance directs the search.
- Weighted algorithms may choose more steps when that route has lower terrain or
  ghost-danger cost.

These are expected algorithm properties, not fixed numeric results. Exact metrics
depend on the current map, start, target, and ghost positions.

## 9. Validation

The included automated suite covers:

- path validity for all five algorithms;
- BFS shortest-step behavior;
- weighted optimality for UCS, Dijkstra, and A*;
- safe failure when no route exists;
- map connectivity and determinism;
- complete five-algorithm comparison output;
- controller reset behavior;
- completion of a full static A* mission.

Run `python run_tests.py` from the project folder.

## 10. Limitations and future work

- Ghost behavior uses deterministic graph search, not reinforcement learning.
- The target selector evaluates a shortlist of nearby food items instead of
  solving the globally optimal travelling-salesperson route.
- Search comparisons use small maps, so runtime differences can be noisy.
- Future versions could add user-created maps, replay export, multi-agent search,
  minimax ghosts, or reinforcement-learning baselines.

