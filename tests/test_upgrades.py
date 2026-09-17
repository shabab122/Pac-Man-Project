from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from pacman_ai.algorithms import SearchProblem, run_search
from pacman_ai.editor import EditorTool, MapEditor
from pacman_ai.experiments import export_csv, export_pdf
from pacman_ai.maze import Maze
from pacman_ai.models import Algorithm, GhostBehavior, HeuristicMode, Position
from pacman_ai.planner import auto_select_algorithm
from pacman_ai.session import GameSession

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class OpenGrid:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height

    def neighbors(self, position: Position):
        x, y = position
        for candidate in ((x + 1, y), (x, y + 1), (x - 1, y), (x, y - 1)):
            if 0 <= candidate[0] < self.width and 0 <= candidate[1] < self.height:
                yield candidate

    @staticmethod
    def cost(_current: Position, _destination: Position) -> float:
        return 1.0


class UpgradeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.session = GameSession(PROJECT_ROOT / "maps")

    def test_all_a_star_heuristics_find_a_route(self) -> None:
        grid = OpenGrid(8, 7)
        problem = SearchProblem((0, 0), (7, 6), grid.neighbors, grid.cost)
        for mode in HeuristicMode:
            with self.subTest(mode=mode.value):
                result = run_search(Algorithm.A_STAR, problem, heuristic_mode=mode)
                self.assertTrue(result.found)
                self.assertEqual(result.heuristic_mode, mode)
                self.assertEqual(result.path[0], problem.start)
                self.assertEqual(result.path[-1], problem.goal)

    def test_auto_selector_is_explainable_and_deterministic(self) -> None:
        target = self.session.comparison_target()
        first = auto_select_algorithm(
            self.session.maze,
            self.session.player,
            target,
            self.session.ghost_positions,
        )
        second = auto_select_algorithm(
            self.session.maze,
            self.session.player,
            target,
            self.session.ghost_positions,
        )
        self.assertEqual(first, second)
        self.assertEqual(first[0], Algorithm.A_STAR)
        self.assertIn("danger", first[1])

    def test_auto_mode_uses_an_original_search_algorithm(self) -> None:
        self.session.toggle_auto_mode()
        result = self.session.plan_next_route()
        self.assertTrue(result.found)
        self.assertIn(self.session.last_effective_algorithm, set(Algorithm))
        self.assertTrue(self.session.auto_reason)

    def test_advanced_ghost_team_has_distinct_legal_behaviors(self) -> None:
        behaviors = {ghost.behavior for ghost in self.session.ghosts}
        self.assertEqual(
            behaviors,
            {
                GhostBehavior.AGGRESSIVE,
                GhostBehavior.PREDICTIVE,
                GhostBehavior.RANDOM,
            },
        )
        self.session.running = True
        self.session.step_ghosts(now=100.0)
        positions = self.session.ghost_positions
        self.assertEqual(len(positions), len(set(positions)))
        self.assertTrue(all(self.session.maze.is_walkable(item) for item in positions))

    def test_explicit_map_round_trip_preserves_game_entities(self) -> None:
        data = self.session.maze.to_explicit_dict(name="Round Trip", map_id="round_trip")
        with TemporaryDirectory() as directory:
            path = Path(directory) / "round_trip.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            loaded = Maze.from_file(path)
        self.assertEqual(loaded.walls, self.session.maze.walls)
        self.assertEqual(loaded.start, self.session.maze.start)
        self.assertEqual(loaded.exit, self.session.maze.exit)
        self.assertEqual(loaded.foods, self.session.maze.foods)
        self.assertEqual(loaded.terrain_costs, self.session.maze.terrain_costs)

    def test_map_editor_saves_a_new_valid_file_without_mutating_source(self) -> None:
        original = self.session.maze.to_explicit_dict()
        editor = MapEditor.from_maze(self.session.maze)
        editable = next(
            position
            for position in self.session.maze.distances_from(self.session.maze.start)
            if position not in {self.session.maze.start, self.session.maze.exit}
            and position not in self.session.maze.foods
            and position not in self.session.maze.power_foods
            and position not in self.session.maze.ghost_starts
        )
        editor.set_tool(EditorTool.TERRAIN_3)
        self.assertTrue(editor.apply(editable))
        with TemporaryDirectory() as directory:
            path = editor.save(directory, "custom_test.json")
            loaded = Maze.from_file(path)
            self.assertEqual(loaded.terrain_costs[editable], 3)
        self.assertEqual(self.session.maze.to_explicit_dict(), original)

    def test_experiment_and_exports_cover_algorithms_and_heuristics(self) -> None:
        report = self.session.run_research_experiment()
        self.assertEqual({item.label for item in report.algorithm_summaries}, {item.value for item in Algorithm})
        self.assertEqual({item.label for item in report.heuristic_summaries}, {item.value for item in HeuristicMode})
        self.assertTrue(all(item.success_rate == 1.0 for item in report.algorithm_summaries))
        with TemporaryDirectory() as directory:
            csv_path = export_csv(report, Path(directory) / "results.csv")
            pdf_path = export_pdf(report, Path(directory) / "results.pdf")
            self.assertIn("algorithm", csv_path.read_text(encoding="utf-8"))
            self.assertEqual(pdf_path.read_bytes()[:4], b"%PDF")

    def test_replay_records_and_exports_json(self) -> None:
        self.session.dynamic_ghosts = False
        self.session.step_player(now=100.0)
        self.assertGreaterEqual(len(self.session.replay.frames), 2)
        with TemporaryDirectory() as directory:
            path = self.session.save_replay(directory)
            payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["format"], "pacman-ai-replay-v1")
        self.assertEqual(payload["frame_count"], len(payload["frames"]))

    def test_reset_preserves_upgrade_preferences(self) -> None:
        self.session.set_heuristic_mode(HeuristicMode.WEIGHTED)
        self.session.toggle_auto_mode()
        self.session.toggle_advanced_ghost_ai()
        self.session.toggle_heatmap()
        self.session.reset()
        self.assertEqual(self.session.heuristic_mode, HeuristicMode.WEIGHTED)
        self.assertTrue(self.session.auto_mode)
        self.assertFalse(self.session.advanced_ghost_ai)
        self.assertFalse(self.session.show_heatmap)


if __name__ == "__main__":
    unittest.main()

