"""Level-order shuffle for the 31-node map.

Rules (see docs/DESIGN.md §7):
1. Dr. N. Cortex stays on the last node.
2. Every other main level and boss is shuffled across nodes 1..30.
3. No two bosses on adjacent nodes (Cortex counts, so node 30 never holds a boss).
4. No boss on a node that is open from the start (nodes 1..starting_nodes).
5. Gems belong to nodes, so a level that needs colored gem X for its boxes never sits on the node that awards X.

Rules 3 and 4 never need a retry (the bosses' positions are drawn directly from the valid set); rule 5 is met by
redrawing, which rarely takes more than a few tries.
"""
from random import Random

from .data import FINAL_BOSS, MAP_NODES, SHUFFLABLE_LEVELS, Gem, Level


def vanilla_order() -> list[Level]:
    return [*SHUFFLABLE_LEVELS, FINAL_BOSS]


COLOR_BY_NODE: dict[int, Gem] = {level.vanilla_node: level.gem for level in SHUFFLABLE_LEVELS if level.gem.is_colored}
"""Gems belong to map nodes: these nodes award the colored gems"""


def gem_conflict(order: list[Level]) -> bool:
    """A level whose boxes need color X on the node that awards X would need the gem to get the gem."""
    return any(
        COLOR_BY_NODE.get(node) in level.gem_requires
        for node, level in enumerate(order, start=1)
    )


def shuffle_order(random: Random, starting_nodes: int) -> list[Level]:
    """Return the level for each map node, index 0 = node 1, last = node 31 (Cortex)."""
    for _ in range(1000):
        order = _draw(random, starting_nodes)
        if not gem_conflict(order):
            return order
    raise RuntimeError("could not draw a level order without a colored gem conflict")


def _draw(random: Random, starting_nodes: int) -> list[Level]:
    bosses = [level for level in SHUFFLABLE_LEVELS if level.is_boss]
    normals = [level for level in SHUFFLABLE_LEVELS if not level.is_boss]
    random.shuffle(bosses)
    random.shuffle(normals)

    first = starting_nodes + 1  # first node a boss may use
    last = MAP_NODES - 2        # node 30 is next to Cortex
    # Choosing k non-adjacent positions in [first, last] == choosing k distinct values in a range shrunk by (k - 1),
    # then spreading them back out by adding their rank.
    span = last - first + 1 - (len(bosses) - 1)
    if span < len(bosses):
        raise ValueError(f"cannot place {len(bosses)} bosses after {starting_nodes} starting nodes")
    picks = sorted(random.sample(range(span), len(bosses)))
    boss_nodes = {first + pick + rank: boss for rank, (pick, boss) in enumerate(zip(picks, bosses))}

    order: list[Level] = []
    normal_iter = iter(normals)
    for node in range(1, MAP_NODES):
        order.append(boss_nodes[node] if node in boss_nodes else next(normal_iter))
    order.append(FINAL_BOSS)
    return order
