# Architecture and Data Flow

## Components

| Module | Responsibility |
|---|---|
| `main.py` | Parses normal, screenshot, and smoke-test launch options |
| `pacman_ai/app.py` | Owns the event loop, timers, scenes, and UI actions |
| `pacman_ai/ui.py` | Draws the menu, maze, entities, controls, and dialogs |
| `pacman_ai/session.py` | Stores game state and applies gameplay rules |
| `pacman_ai/planner.py` | Builds costs, chooses targets, and starts searches |
| `pacman_ai/algorithms.py` | Implements all five algorithms and result metrics |
| `pacman_ai/maze.py` | Loads JSON, generates a connected maze, and validates it |
| `pacman_ai/models.py` | Defines shared algorithms, positions, entities, and results |
| `pacman_ai/audio.py` | Produces optional short sound effects in memory |

## Planning flow

```text
Input event
  -> GameSession requests a target
  -> Planner builds SearchProblem
  -> Selected algorithm explores the maze
  -> SearchResult contains path and metrics
  -> Session moves Pac-Man and applies game rules
  -> UI renders the updated state
```

The search layer does not import Pygame. The game rules can therefore be tested
without creating a window.

## SearchProblem contract

Every algorithm receives:

```python
SearchProblem(
    start=(x1, y1),
    goal=(x2, y2),
    neighbors=maze.neighbors,
    step_cost=cost_function,
)
```

This dependency-injection approach prevents each algorithm from knowing how the
maze, terrain, or ghosts are stored. It also lets the tests use a tiny in-memory
grid.

## Failure handling

- Invalid or missing map files raise a clear startup error.
- Maps are checked for unreachable entities.
- Search returns `found=False` and an empty path instead of indexing a missing
  parent when no route exists.
- A blocked live route is discarded and replanned.
- Audio failure disables sound but does not stop the visual demo.
- End states stop automatic movement and provide restart or menu actions.

## Extension points

- Add another algorithm to `Algorithm`, implement it in `algorithms.py`, and add
  it to `SEARCH_FUNCTIONS`.
- Add a map by copying one JSON configuration and changing its seed or size.
- Replace the target-selection shortlist with a global food-order optimizer.
- Add replay serialization at the session layer without changing search code.

