from __future__ import annotations

from pathlib import Path
import unittest

from pacman_ai.models import Algorithm
from pacman_ai.session import GameSession

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class GameSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.session = GameSession(PROJECT_ROOT / "maps")

    def test_algorithm_selection_invalidates_the_old_route(self) -> None:
        self.session.plan_next_route()
        self.assertTrue(self.session.route)
        self.session.set_algorithm(Algorithm.BFS)
        self.assertEqual(self.session.route, [])
        self.assertIsNone(self.session.last_result)

    def test_compare_uses_all_five_algorithms(self) -> None:
        results = self.session.compare_current_problem()
        self.assertEqual({result.algorithm for result in results}, set(Algorithm))
        self.assertTrue(all(result.found for result in results))

    def test_a_star_can_complete_a_static_mission(self) -> None:
        self.session.set_algorithm(Algorithm.A_STAR)
        self.session.dynamic_ghosts = False
        # Remove static ghost blockers for a deterministic controller test.
        self.session.ghosts.clear()

        for step in range(20_000):
            if self.session.won:
                break
            self.session.step_player(now=100.0 + step * 0.1)

        self.assertTrue(self.session.won)
        self.assertFalse(self.session.foods)
        self.assertFalse(self.session.power_foods)
        self.assertEqual(self.session.player, self.session.maze.exit)
        self.assertGreater(self.session.metrics.searches, 0)

    def test_reset_preserves_user_preferences(self) -> None:
        self.session.set_algorithm(Algorithm.DIJKSTRA)
        self.session.set_speed(4)
        self.session.toggle_dynamic_ghosts()
        self.session.step_player()
        self.session.reset()

        self.assertEqual(self.session.algorithm, Algorithm.DIJKSTRA)
        self.assertEqual(self.session.speed, 4)
        self.assertFalse(self.session.dynamic_ghosts)
        self.assertEqual(self.session.player, self.session.maze.start)
        self.assertEqual(self.session.score, 0)


if __name__ == "__main__":
    unittest.main()

