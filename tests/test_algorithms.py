from __future__ import annotations

import unittest

from pacman_ai.algorithms import SearchProblem, run_search
from pacman_ai.models import Algorithm, Position


class MiniGrid:
    def __init__(
        self,
        width: int,
        height: int,
        walls: set[Position] | None = None,
        costs: dict[Position, float] | None = None,
    ) -> None:
        self.width = width
        self.height = height
        self.walls = walls or set()
        self.costs = costs or {}

    def neighbors(self, position: Position):
        x, y = position
        for candidate in ((x + 1, y), (x, y + 1), (x - 1, y), (x, y - 1)):
            if not (0 <= candidate[0] < self.width and 0 <= candidate[1] < self.height):
                continue
            if candidate not in self.walls:
                yield candidate

    def cost(self, _current: Position, destination: Position) -> float:
        return self.costs.get(destination, 1.0)


def assert_valid_path(
    test_case: unittest.TestCase,
    grid: MiniGrid,
    path: list[Position],
    start: Position,
    goal: Position,
) -> None:
    test_case.assertTrue(path)
    test_case.assertEqual(path[0], start)
    test_case.assertEqual(path[-1], goal)
    for current, nxt in zip(path, path[1:]):
        test_case.assertIn(nxt, set(grid.neighbors(current)))


class SearchAlgorithmTests(unittest.TestCase):
    def test_every_algorithm_finds_a_valid_path(self) -> None:
        grid = MiniGrid(5, 4, walls={(2, 0), (2, 1), (2, 2)})
        problem = SearchProblem((0, 0), (4, 0), grid.neighbors, grid.cost)

        for algorithm in Algorithm:
            with self.subTest(algorithm=algorithm.value):
                result = run_search(algorithm, problem)
                self.assertTrue(result.found)
                assert_valid_path(self, grid, result.path, problem.start, problem.goal)
                self.assertGreater(result.expanded_nodes, 0)
                self.assertGreaterEqual(result.frontier_peak, 1)

    def test_bfs_minimizes_steps_but_not_weighted_cost(self) -> None:
        expensive_direct_route = {(1, 1): 9.0, (2, 1): 9.0, (3, 1): 9.0}
        grid = MiniGrid(5, 3, costs=expensive_direct_route)
        problem = SearchProblem((0, 1), (4, 1), grid.neighbors, grid.cost)

        bfs = run_search(Algorithm.BFS, problem)
        ucs = run_search(Algorithm.UCS, problem)

        self.assertEqual(bfs.steps, 4)
        self.assertEqual(ucs.steps, 6)
        self.assertLess(ucs.path_cost, bfs.path_cost)

    def test_weighted_algorithms_return_the_optimal_cost(self) -> None:
        grid = MiniGrid(
            5,
            3,
            costs={(1, 1): 9.0, (2, 1): 9.0, (3, 1): 9.0},
        )
        problem = SearchProblem((0, 1), (4, 1), grid.neighbors, grid.cost)

        results = {
            algorithm: run_search(algorithm, problem)
            for algorithm in (Algorithm.UCS, Algorithm.DIJKSTRA, Algorithm.A_STAR)
        }
        self.assertEqual(results[Algorithm.UCS].path_cost, 6.0)
        self.assertEqual(
            results[Algorithm.UCS].path_cost,
            results[Algorithm.DIJKSTRA].path_cost,
        )
        self.assertEqual(
            results[Algorithm.DIJKSTRA].path_cost,
            results[Algorithm.A_STAR].path_cost,
        )

    def test_no_path_returns_a_safe_empty_result(self) -> None:
        grid = MiniGrid(3, 3, walls={(1, 0), (1, 1), (1, 2)})
        problem = SearchProblem((0, 1), (2, 1), grid.neighbors, grid.cost)

        for algorithm in Algorithm:
            with self.subTest(algorithm=algorithm.value):
                result = run_search(algorithm, problem)
                self.assertFalse(result.found)
                self.assertEqual(result.path, [])
                self.assertEqual(result.steps, 0)


if __name__ == "__main__":
    unittest.main()

