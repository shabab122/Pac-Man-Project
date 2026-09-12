# Search Algorithm Guide

## Shared search problem

The maze is a graph:

- `V` is the set of walkable grid cells.
- `E` is the set of legal four-directional moves between cells.
- `start` is Pac-Man's current cell.
- `goal` is the selected pellet or exit.
- `cost(u, v)` is the cost of entering cell `v` from cell `u`.

Every implementation returns the same fields: whether it found a route, the
reconstructed path, nodes in exploration order, weighted path cost, elapsed
milliseconds, and peak frontier size.

## Breadth-First Search

### What it does

BFS explores the grid level by level with a first-in, first-out queue. It finds
the route containing the fewest moves when each move is treated equally.

### Pseudocode

```text
frontier = queue(start)
visited = {start}

while frontier is not empty:
    node = remove_front(frontier)
    if node is goal:
        return reconstructed path
    for each neighbor of node:
        if neighbor is unvisited:
            remember node as its parent
            mark neighbor visited
            add neighbor to back of frontier
```

### Properties

- Complete on this finite grid: yes
- Optimal by number of steps: yes
- Optimal by weighted cost: no
- Time complexity: `O(V + E)`
- Space complexity: `O(V)`

Analogy: searching every room one doorway away, then every room two doorways
away, and continuing outward.

## Depth-First Search

### What it does

DFS follows one branch as far as possible with a last-in, first-out stack. It
backtracks when the branch ends.

### Pseudocode

```text
frontier = stack(start)
visited = {start}

while frontier is not empty:
    node = pop(frontier)
    if node is goal:
        return reconstructed path
    push every unvisited neighbor
```

### Properties

- Complete on this finite graph with a visited set: yes
- Optimal: no
- Time complexity: `O(V + E)`
- Space complexity: `O(V)` in the graph implementation

Analogy: choosing one corridor and continuing until it ends before trying a
different corridor.

## Uniform Cost Search

### What it does

UCS expands the frontier node with the lowest accumulated cost `g(n)`. It uses a
min-priority queue and can avoid expensive terrain or ghost-danger zones.

### Pseudocode

```text
frontier = priority_queue((0, start))
best_cost[start] = 0

while frontier is not empty:
    cost, node = remove_lowest_cost(frontier)
    if node is goal:
        return reconstructed path
    for each neighbor:
        candidate = cost + step_cost(node, neighbor)
        if candidate is lower than the recorded cost:
            update cost and parent
            add candidate to frontier
```

### Properties

- Complete: yes, because every step cost is positive
- Optimal by weighted cost: yes
- Time complexity in this implementation: `O((V + E) log V)`
- Space complexity: `O(V)`

Analogy: always continuing the cheapest total journey tried so far, even when it
contains more physical steps.

## Dijkstra's Algorithm

### What it does

Dijkstra permanently settles nodes in increasing shortest-known distance from
the source. With a priority queue and early termination at one goal, its behavior
matches UCS in this project.

### Properties

- Requires non-negative edge weights: yes
- Complete: yes
- Optimal by weighted cost: yes
- Time complexity in this implementation: `O((V + E) log V)`
- Space complexity: `O(V)`

### UCS versus Dijkstra

They are commonly taught from different viewpoints:

- UCS is an AI search procedure focused on reaching a goal.
- Dijkstra is a shortest-path algorithm commonly described as computing shortest
  distances from one source.

When both use the same priority queue, non-negative costs, one source, and an
early stop after the goal is settled, their expansion rules and answers match.
The project keeps separate functions so the distinction can be discussed without
claiming they produce different mathematics here.

## A* Search

### What it does

A* balances known cost and estimated remaining cost:

```text
f(n) = g(n) + h(n)
```

- `g(n)` is the exact accumulated cost from the start to node `n`.
- `h(n)` is Manhattan distance from `n` to the goal.
- `f(n)` is the priority used by the frontier.

### Pseudocode

```text
frontier = priority_queue((h(start), start))
g_score[start] = 0

while frontier is not empty:
    node = remove_lowest_f(frontier)
    if node is goal:
        return reconstructed path
    for each neighbor:
        candidate_g = g_score[node] + step_cost(node, neighbor)
        if candidate_g is lower than the recorded score:
            update g score and parent
            priority = candidate_g + h(neighbor)
            add neighbor to frontier
```

### Why Manhattan distance is valid

Pac-Man can move only horizontally or vertically. Ignoring walls, at least
`|x1 - x2| + |y1 - y2|` moves are required. Every move costs at least 1, so this
estimate never exceeds the true remaining cost. The heuristic is admissible and
consistent for this cost model.

### Properties

- Complete: yes on this finite graph
- Optimal by weighted cost: yes with the current heuristic
- Worst-case complexity: comparable to Dijkstra when the heuristic gives little
  guidance; it often expands fewer nodes for one specific grid target
- Space complexity: `O(V)`

Analogy: choosing a route using both the fuel already spent and a realistic
estimate of fuel still needed.

## Common mistakes

- Claiming DFS always finds the shortest route.
- Claiming BFS optimizes weighted cost.
- Using a negative step cost with UCS or Dijkstra.
- Marking a node visited too early in a weighted search without allowing a better
  cost to replace it.
- Using Euclidean straight-line distance without explaining the movement model.
- Comparing algorithms with different starts, targets, or ghost positions.
- Claiming UCS and Dijkstra are meaningfully different in this exact setup.
- Treating runtime below one millisecond as stable across computers.

## Small practice exercise

Create a 5 by 3 empty grid. Put Pac-Man at `(0, 1)` and the goal at `(4, 1)`.
Give the three direct middle cells a cost of 9 and all other cells a cost of 1.

Predict:

1. Which path BFS selects.
2. Which path UCS, Dijkstra, and A* select.
3. Why the weighted route contains more steps but costs less.

The automated test `test_bfs_minimizes_steps_but_not_weighted_cost` implements
this exact scenario.

