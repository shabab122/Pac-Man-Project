from __future__ import annotations

from pathlib import Path
import unittest

from pacman_ai.maze import Maze, discover_map_files

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class MazeTests(unittest.TestCase):
    def test_every_packaged_map_is_valid_and_connected(self) -> None:
        for path in discover_map_files(PROJECT_ROOT / "maps"):
            with self.subTest(map=path.name):
                maze = Maze.from_file(path)
                maze.validate()
                reachable = set(maze.distances_from(maze.start))
                expected = {
                    maze.exit,
                    *maze.foods,
                    *maze.power_foods,
                    *maze.ghost_starts,
                }
                self.assertTrue(expected.issubset(reachable))
                self.assertNotEqual(maze.start, maze.exit)
                self.assertGreater(len(maze.foods), 10)
                self.assertTrue(all(cost >= 1 for cost in maze.terrain_costs.values()))

    def test_generation_is_deterministic(self) -> None:
        path = discover_map_files(PROJECT_ROOT / "maps")[0]
        first = Maze.from_file(path)
        second = Maze.from_file(path)
        self.assertEqual(first.walls, second.walls)
        self.assertEqual(first.foods, second.foods)
        self.assertEqual(first.exit, second.exit)
        self.assertEqual(first.ghost_starts, second.ghost_starts)


if __name__ == "__main__":
    unittest.main()

