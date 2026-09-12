# Group 7 Team Assignment and Three-Week Roadmap

The assignments below provide clear ownership while requiring code review across
the team. The team can swap names before submission, but the final presentation
and repository should show one agreed version.

## Task assignment

| Team member | ID | Primary responsibility | Required cross-review |
|---|---:|---|---|
| Sk. Istiaq Arefin | 112410323 | Team lead, architecture, integration, Git branches, final build | Review game-state integration and run final checklist |
| Ratul Ghosh | 112410038 | BFS, DFS, UCS implementation and algorithm unit tests | Explain and review Dijkstra/A* differences |
| Shihabun Shakib | 112410073 | Dijkstra, A*, heuristic, cost model, comparison metrics | Review BFS/DFS/UCS and validate fair inputs |
| Sumaiya Akther | 112410318 | Pygame UI, animation, maze visuals, controls, accessibility | Review gameplay flow and demo readability |
| Rushdania Bushra | 112230039 | Gameplay rules, maps, testing, documentation, slides, demo script | Run acceptance tests and coordinate rehearsal |

### Shared responsibility

Every member must be able to explain:

- how a grid becomes a graph;
- the difference between queue, stack, and priority queue;
- why BFS ignores weighted danger;
- why UCS and Dijkstra match in this project;
- what `g(n)`, `h(n)`, and `f(n)` mean in A*;
- how one test proves a claimed behavior;
- how to install and run the application.

## Week 1: Search foundation

### Tasks

- Agree on grid state, neighbor order, goal test, and movement-cost interface.
- Implement BFS, DFS, UCS, Dijkstra, and A* in isolated functions.
- Implement parent-based path reconstruction and metrics.
- Build deterministic map generation and connectivity validation.
- Create weighted and unreachable test scenarios.

### Milestone

All five algorithms return valid `SearchResult` objects on test grids. Packaged
maps load and every entity is reachable.

### Deliverables

- `algorithms.py`, `models.py`, and `maze.py`
- Initial JSON maps
- Algorithm and map tests
- Algorithm explanation draft

## Week 2: Gameplay and visualization

### Tasks

- Implement score, lives, food, power mode, exit, collision, and reset rules.
- Add target selection, danger cost, moving ghosts, and replanning.
- Build the start screen, live maze, controls, route overlay, and metrics panel.
- Add Compare, Pause, Step, Speed, Ghost Freeze, and Map Switch features.
- Integrate optional procedural audio with a safe fallback.

### Milestone

Pac-Man can automatically complete a static mission and can react to live ghosts.
Users can switch algorithms without restarting the program.

### Deliverables

- Playable integrated application
- Three complete maps
- Comparison dialog
- Gameplay screenshot
- Session integration tests

## Week 3: Quality, presentation, and submission

### Tasks

- Run automated tests on at least two team computers.
- Rehearse the same-snapshot comparison and weighted-grid explanation.
- Verify setup from a newly extracted ZIP.
- Fix visual clipping, button behavior, dead ends, and unclear labels.
- Finish project report, README, demo guide, and presentation.
- Prepare backup screenshots in case the classroom machine blocks a window.

### Milestone

One release ZIP installs from the README, passes all tests, starts the game, and
supports a five-minute live presentation.

### Deliverables

- Final source ZIP
- Passing test log
- Final presentation/report
- Five-minute demo script and viva answers
- Signed team familiarity checklist

## Familiarity checklist

Before submission, each member should tick and initial every item:

- [ ] I installed the project from the README on my own machine.
- [ ] I ran `python run_tests.py` and saw all tests pass.
- [ ] I can demonstrate my assigned module without reading the source line by line.
- [ ] I can explain one weakness or limitation of my implementation.
- [ ] I can explain the UCS and Dijkstra equivalence in this project.
- [ ] I can answer what changes when ghost movement makes the environment dynamic.
- [ ] I know who presents each slide and who operates the live demo.

