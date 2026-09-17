"""Generate deterministic demonstration evidence for documentation."""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pacman_ai.experiments import export_csv, export_pdf  # noqa: E402
from pacman_ai.session import GameSession  # noqa: E402


def main() -> int:
    destination = PROJECT_ROOT / "sample_outputs"
    destination.mkdir(parents=True, exist_ok=True)
    session = GameSession(PROJECT_ROOT / "maps")
    session.dynamic_ghosts = False
    report = session.run_research_experiment()
    export_csv(report, destination / "algorithm_experiment_sample.csv")
    export_pdf(report, destination / "algorithm_experiment_sample.pdf")
    for index in range(12):
        session.step_player(now=100.0 + index * 0.1)
    session.replay.save(
        destination,
        algorithm=session.last_effective_algorithm.value,
        heuristic=session.heuristic_mode.value,
        filename="mission_replay_sample.json",
        overwrite=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
