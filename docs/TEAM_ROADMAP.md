# Role Assignment and Three-Week Roadmap

This neutral plan assigns responsibilities by role and keeps the delivered
project free of personal identifiers.

## Role assignment

| Role | Primary responsibility | Required cross-review |
|---|---|---|
| Integration lead | Architecture, branches, integration, release ZIP | Review session boundaries and final checklist |
| Search engineer | BFS, DFS, UCS, Dijkstra, A*, heuristics, tests | Explain correctness and weighted trade-offs |
| Game-AI engineer | Cost model, AUTO rules, ghost policies, replay | Review dynamic behavior and collision cases |
| Interface engineer | Pygame UI, workbench, Map Studio, accessibility | Review demo readability and input behavior |
| Quality/documentation engineer | Experiments, reports, QA, docs, slides | Verify fresh install and coordinate rehearsal |

Every contributor must explain:

- how the grid becomes a graph;
- queue, stack, and priority queue;
- why BFS ignores weighted danger;
- why UCS and Dijkstra normally match;
- `g(n)`, `h(n)`, `f(n)`, and heuristic weight;
- why Weighted A* is not guaranteed optimal;
- why AUTO is a controller, not a sixth algorithm;
- one automated test and one known limitation.

## Week 1 — Preserve and extend the AI foundation

### Tasks

- Run the original regression suite before editing.
- Preserve the shared `SearchProblem` and `SearchResult` interfaces.
- Add Euclidean and Weighted A* without changing the Manhattan default.
- Implement deterministic AUTO rules.
- Add explicit-map serialization and isolated editor logic.
- Add tests for compatibility, heuristics, and map round-trip.

### Milestone

All original tests pass; every A* mode finds valid routes; packaged maps produce
the same deterministic content.

### Deliverables

- algorithm/heuristic implementation;
- AUTO decision table;
- explicit map format;
- regression and feature tests.

## Week 2 — Established game and workbench

### Tasks

- Add Aggressive, Predictive, Random, and Defensive ghosts.
- Keep Classic BFS chase selectable.
- Add risk heatmap and two-tab control panel.
- Build Map Studio interaction and safe save/load.
- Add explanation, experiment, heuristic, and replay screens.
- Add bounded replay capture and export.

### Milestone

The original game remains playable while every upgraded tool is accessible from
the AI Workbench.

### Deliverables

- advanced ghost system;
- polished game/workbench UI;
- Map Studio;
- replay and explanation features;
- integration tests.

## Week 3 — Evidence, quality, and submission

### Tasks

- Add multi-target experiment summaries.
- Export CSV, PDF, and JSON replay.
- Render every major screen for visual QA.
- Run test, compile, smoke, report, and archive checks.
- Verify setup from a freshly extracted ZIP.
- Update report, algorithm guide, architecture, demo guide, and presentation.
- Rehearse a five-minute evidence-based demo.

### Milestone

One complete ZIP installs from the README, passes every test, launches without
network access, exports evidence, and supports the full demonstration.

### Deliverables

- source ZIP;
- verified test log;
- upgraded screenshots;
- sample CSV/PDF/replay;
- neutral presentation;
- demo and viva guide.

## Familiarity checklist

- [ ] I installed the ZIP using the README.
- [ ] I ran `python run_tests.py` successfully.
- [ ] I can explain one required algorithm with its data structure.
- [ ] I can explain one A* heuristic and its guarantee.
- [ ] I can justify UCS–Dijkstra equivalence in this project.
- [ ] I can show why AUTO is not a new algorithm.
- [ ] I can demonstrate one ghost policy.
- [ ] I can create and validate one safe map edit.
- [ ] I can interpret the experiment without overclaiming runtime.
- [ ] I know the project limitations and backup demo plan.
