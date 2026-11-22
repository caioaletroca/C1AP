import unittest
from random import Random

from ..data import FINAL_BOSS, MAP_NODES, SHUFFLABLE_LEVELS
from ..shuffle import gem_conflict, shuffle_order, vanilla_order


class TestShuffle(unittest.TestCase):
    def test_vanilla(self) -> None:
        order = vanilla_order()
        self.assertEqual([level.vanilla_node for level in order], list(range(1, MAP_NODES + 1)))
        self.assertFalse(gem_conflict(order))

    def test_invariants(self) -> None:
        for starting_nodes in range(1, 11):
            for seed in range(300):
                with self.subTest(starting_nodes=starting_nodes, seed=seed):
                    order = shuffle_order(Random(seed), starting_nodes)
                    self.assertEqual(len(order), MAP_NODES)
                    self.assertIs(order[-1], FINAL_BOSS)
                    self.assertEqual(set(order[:-1]), set(SHUFFLABLE_LEVELS))
                    boss_nodes = [node for node, level in enumerate(order, start=1) if level.is_boss]
                    self.assertTrue(all(node > starting_nodes for node in boss_nodes))
                    self.assertTrue(all(b - a > 1 for a, b in zip(boss_nodes, boss_nodes[1:])))
                    self.assertFalse(gem_conflict(order))

    def test_deterministic(self) -> None:
        self.assertEqual(shuffle_order(Random(5), 3), shuffle_order(Random(5), 3))
