import unittest
from collections import Counter
from dataclasses import replace

from .. import ram
from ..data import LEVEL_BY_NAME
from ..locations import location_name_to_id
from ..shuffle import vanilla_order
from ..watcher import SlotInfo, Watcher

MAP = ram.Snapshot(level=ram.LID_MAP, gamestate=ram.GAMESTATE_MAP, current_node=1, lives=4 * ram.UNIT,
                   health=0, fruit=0, levels_unlocked=3, pool1=0, pool2=0, death_count=0, next_lid=ram.NO_LEVEL)


def lid(name: str) -> int:
    return LEVEL_BY_NAME[name].lid


def loc(name: str) -> int:
    return location_name_to_id[name]


def make_watcher(**kwargs) -> Watcher:
    slot = dict(level_order=tuple(level.lid for level in vanilla_order()), starting_nodes=3, gem_checks=True, goal=0)
    slot.update(kwargs)
    return Watcher(SlotInfo(**slot))


class TestWatcher(unittest.TestCase):
    def setUp(self) -> None:
        self.watcher = make_watcher()
        self.received: Counter[str] = Counter()
        self.checked: set[int] = set()

    def step(self, snap: ram.Snapshot) -> "ram.Snapshot":
        actions = self.watcher.step(snap, self.received, self.checked)
        self.checked |= actions.locations
        self.actions = actions
        return snap

    def in_level(self, name: str, **kwargs) -> ram.Snapshot:
        return replace(MAP, level=lid(name), gamestate=ram.GAMESTATE_PLAYING, **kwargs)

    def test_round2_log(self) -> None:
        """Replays the BizHawk log of finishing N. Sanity Beach on a new game."""
        self.step(replace(MAP, levels_unlocked=1))
        level = self.step(self.in_level("N. Sanity Beach", levels_unlocked=1))
        self.assertFalse(self.actions.locations)
        self.step(replace(level, levels_unlocked=2))
        self.step(replace(level, levels_unlocked=2, gamestate=ram.GAMESTATE_LEVEL_WON))
        self.assertEqual(self.actions.locations, {loc("N. Sanity Beach - Complete")})
        end = self.step(replace(level, level=ram.LID_LEVEL_END, levels_unlocked=2))
        self.step(replace(end, pool1=1 << 1))
        self.assertEqual(self.actions.locations, {loc("N. Sanity Beach - Gem")})
        self.step(replace(end, pool1=1 << 1, gamestate=ram.GAMESTATE_EXIT_TO_MAP))
        self.step(replace(MAP, levels_unlocked=2, pool1=1 << 1))
        self.assertFalse(self.actions.locations)
        self.assertIsNone(self.watcher.level)

    def test_round4_log(self) -> None:
        """Replays BizHawk round 4: Boulders won without its gem, then a game over in Jungle Rollers."""
        self.step(MAP)
        level = self.step(self.in_level("Boulders", levels_unlocked=1))
        self.step(replace(level, levels_unlocked=2))
        self.assertFalse(self.actions.locations)
        self.step(replace(level, levels_unlocked=2, gamestate=ram.GAMESTATE_EXIT_TO_MAP))
        self.assertEqual(self.actions.locations, {loc("Boulders - Complete")})
        self.step(replace(MAP, gamestate=ram.GAMESTATE_EXIT_TO_MAP))
        self.step(replace(MAP, levels_unlocked=2))
        self.assertFalse(self.actions.locations)

        level = self.step(self.in_level("Jungle Rollers", current_node=2, levels_unlocked=2))
        self.step(replace(level, gamestate=ram.GAMESTATE_GAME_OVER))
        self.step(replace(MAP, gamestate=ram.GAMESTATE_GAME_OVER, current_node=2, levels_unlocked=2))
        self.step(replace(MAP, current_node=1, levels_unlocked=1))
        self.assertNotIn(loc("Jungle Rollers - Complete"), self.checked)

    def test_exit_seen_only_on_map(self) -> None:
        """First connected run: Road to Nowhere's 0x300 lasted 1 frame with its own ID; the client saw it on the map."""
        self.step(MAP)
        self.step(self.in_level("Road to Nowhere", current_node=3, levels_unlocked=5))
        self.step(replace(MAP, gamestate=ram.GAMESTATE_EXIT_TO_MAP, current_node=3, levels_unlocked=5))
        self.assertEqual(self.actions.locations, {loc("Road to Nowhere - Complete")})
        self.step(replace(MAP, gamestate=ram.GAMESTATE_EXIT_TO_MAP, current_node=3, levels_unlocked=5))
        self.step(replace(MAP, current_node=3, levels_unlocked=5))
        self.assertFalse(self.actions.locations)

    def test_quit_is_not_completion(self) -> None:
        """BizHawk round 6: quitting The Great Gate from the pause menu goes 0x100 -> 0x400 -> map."""
        self.step(MAP)
        level = self.step(self.in_level("The Great Gate", current_node=3, levels_unlocked=31))
        self.step(replace(level, gamestate=ram.GAMESTATE_QUIT_TO_MAP))
        self.step(replace(MAP, gamestate=ram.GAMESTATE_QUIT_TO_MAP, current_node=3, levels_unlocked=31))
        self.step(replace(MAP, current_node=3, levels_unlocked=31))
        self.assertNotIn(loc("The Great Gate - Complete"), self.checked)

    def test_bonus_round_win_is_not_completion(self) -> None:
        self.step(self.in_level("Hog Wild"))
        self.step(replace(MAP, level=0x24, gamestate=ram.GAMESTATE_LEVEL_WON))
        self.assertFalse(self.actions.locations)
        self.step(replace(MAP, level=0x24, gamestate=ram.GAMESTATE_EXIT_TO_MAP))
        self.assertFalse(self.actions.locations)
        self.step(replace(self.in_level("Hog Wild"), gamestate=ram.GAMESTATE_LEVEL_WON))
        self.assertEqual(self.actions.locations, {loc("Hog Wild - Complete")})

    def test_filler_only_on_map(self) -> None:
        self.step(self.in_level("Boulders"))
        self.assertFalse(self.actions.can_apply_filler)
        self.step(MAP)
        self.assertTrue(self.actions.can_apply_filler)

    def test_clear_gem(self) -> None:
        in_level = self.step(replace(MAP, level=lid("Boulders"), gamestate=ram.GAMESTATE_PLAYING))
        self.step(replace(in_level, pool1=1 << 1))
        self.assertEqual(self.actions.locations, {loc("Boulders - Gem")})

    def test_colored_gem_masked_then_checked(self) -> None:
        green = 1 << ram.COLORED_GEM_BITS["Green"]
        self.received["Green Gem"] = 1
        in_level = self.step(replace(MAP, level=lid("The Lost City"), gamestate=ram.GAMESTATE_PLAYING, pool1=green,
                                     current_node=12))
        self.assertEqual(self.actions.writes.get(ram.ITEM_POOL1), 0, "bit is masked on the node that awards it")
        self.assertFalse(self.actions.locations)
        self.step(replace(in_level, pool1=0))
        self.assertFalse(self.actions.locations, "the masked bit was the received item, not a collection")
        self.step(replace(in_level, pool1=green))
        self.assertEqual(self.actions.locations, {loc("The Lost City - Gem")})
        self.assertNotIn(ram.ITEM_POOL1, self.actions.writes, "received, so the bit stays")

    def test_gem_follows_node_not_level(self) -> None:
        """First connected run: Toxic Waste (vanilla Blue) on node 4 awarded bit 4, a clear gem."""
        self.received["Blue Gem"] = 0
        level = self.step(self.in_level("Toxic Waste", current_node=4))
        self.assertNotIn(ram.ITEM_POOL1, self.actions.writes, "node 4 is not a colored node: nothing to mask")
        self.step(replace(level, level=ram.LID_LEVEL_END, gamestate=ram.GAMESTATE_PLAYING))
        self.step(replace(level, level=ram.LID_LEVEL_END, pool1=1 << 4))
        self.assertEqual(self.actions.locations, {loc("Toxic Waste - Gem")})

    def test_other_nodes_bit_is_not_this_levels_gem(self) -> None:
        level = self.step(self.in_level("Boulders", current_node=4))
        self.step(replace(level, pool1=1 << 1))
        self.assertFalse(self.actions.locations)

    def test_shuffled_level_on_colored_node(self) -> None:
        """Any level on node 21 earns the Blue gem bit, so it's masked there and its appearance is that level's gem."""
        blue = 1 << ram.COLORED_GEM_BITS["Blue"]
        self.received["Blue Gem"] = 1
        level = self.step(self.in_level("Hog Wild", current_node=21, pool1=blue))
        self.assertEqual(self.actions.writes[ram.ITEM_POOL1], 0)
        self.step(replace(level, pool1=0))
        self.step(replace(level, pool1=blue))
        self.assertEqual(self.actions.locations, {loc("Hog Wild - Gem")})

    def test_colored_source_level_elsewhere_keeps_its_color(self) -> None:
        """The Lost City off node 12: Green stays as received, its gem check comes from its node's clear bit."""
        green = 1 << ram.COLORED_GEM_BITS["Green"]
        self.received["Green Gem"] = 1
        level = self.step(self.in_level("The Lost City", current_node=5, pool1=green))
        self.assertNotIn(ram.ITEM_POOL1, self.actions.writes)
        self.step(replace(level, pool1=green | 1 << 5))
        self.assertEqual(self.actions.locations, {loc("The Lost City - Gem")})

    def test_boss_node_gem(self) -> None:
        """BizHawk: N. Sanity Beach on node 6 (Papu Papu's) awarded ITEMPOOL1 bit 6."""
        level = self.step(self.in_level("N. Sanity Beach", current_node=6))
        self.step(replace(level, level=ram.LID_LEVEL_END, pool1=1 << 6))
        self.assertEqual(self.actions.locations, {loc("N. Sanity Beach - Gem")})

    def test_colored_gem_mirrors_items(self) -> None:
        self.step(MAP)
        self.assertNotIn(ram.ITEM_POOL1, self.actions.writes)
        self.received["Yellow Gem"] = 1
        self.step(MAP)
        self.assertEqual(self.actions.writes[ram.ITEM_POOL1], 1 << ram.COLORED_GEM_BITS["Yellow"])

    def test_key(self) -> None:
        bit = 1 << 20
        in_level = self.step(replace(MAP, level=lid("Sunset Vista"), gamestate=ram.GAMESTATE_PLAYING))
        self.step(replace(in_level, level=0x33, pool2=bit))
        self.assertEqual(self.actions.locations, {loc("Sunset Vista - Key")})
        self.assertEqual(self.actions.writes[ram.ITEM_POOL2], 0, "key not received yet")

    def test_map_nodes(self) -> None:
        self.received["Map Progress"] = 2
        self.step(MAP)
        self.assertEqual(self.actions.writes[ram.LEVELS_UNLOCKED], 5)
        self.assertEqual(self.actions.writes[ram.MAP_LEVEL_LINKS], (1 << 6) - 1)

    def test_redirect(self) -> None:
        order = [level.lid for level in vanilla_order()]
        order[0], order[3] = order[3], order[0]
        self.watcher = make_watcher(level_order=tuple(order))
        self.step(replace(MAP, current_node=1, next_lid=lid("N. Sanity Beach")))
        self.assertEqual(self.actions.writes[ram.NEXT_LID], lid("Boulders"))
        self.assertEqual(self.actions.guards[ram.NEXT_LID], lid("N. Sanity Beach"))

    def test_redirect_after_missing_the_request(self) -> None:
        order = [level.lid for level in vanilla_order()]
        order[0], order[3] = order[3], order[0]
        self.watcher = make_watcher(level_order=tuple(order))
        self.step(replace(MAP, current_node=1, level=lid("N. Sanity Beach"), next_lid=ram.NO_LEVEL))
        self.assertEqual(self.actions.writes[ram.NEXT_LID], lid("Boulders"))
        self.assertEqual(self.actions.guards[ram.NEXT_LID], ram.NO_LEVEL)
        self.step(replace(MAP, current_node=1, level=lid("Boulders"), next_lid=ram.NO_LEVEL))
        self.assertNotIn(ram.NEXT_LID, self.actions.writes)

    def test_goal_and_death(self) -> None:
        self.step(replace(MAP, level=lid("Dr. N. Cortex"), gamestate=ram.GAMESTATE_PLAYING))
        self.step(replace(MAP, level=lid("Dr. N. Cortex"), gamestate=ram.GAMESTATE_PLAYING, death_count=1))
        self.assertTrue(self.actions.died)
        self.step(replace(MAP, level=ram.LID_GAME_WIN))
        self.assertTrue(self.actions.goal)

    def test_all_gems_goal_needs_items(self) -> None:
        self.watcher = make_watcher(goal=1)
        self.step(replace(MAP, level=ram.LID_GAME_WIN))
        self.assertFalse(self.actions.goal)
