# Team Collaboration Guide

1. Create one branch for one focused task, such as `feature/a-star-metrics`.
2. Do not change another member's module without discussing the interface first.
3. Run `python run_tests.py` before every commit.
4. Start the game and verify the changed interaction manually.
5. Use a clear commit message, such as `feat: add A-star search metrics`.
6. Ask at least one teammate to review algorithm or game-rule changes.
7. Merge only when tests pass and the owner of the affected module approves.

When adding an upgraded feature, also add a focused test in
`tests/test_upgrades.py`, update the relevant user guide, and confirm the
feature is reachable from either Play Control or AI Workbench. Search logic
must remain independent from Pygame so it can be tested headlessly.

Do not commit `.venv`, cache directories, IDE settings, or generated build files.
