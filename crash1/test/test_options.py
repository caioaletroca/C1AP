from BaseClasses import ItemClassification
from .bases import Crash1TestBase


class TestDefault(Crash1TestBase):
    options = {}


class TestVanillaOrder(Crash1TestBase):
    options = {"level_shuffle": False}


class TestNoGems(Crash1TestBase):
    options = {"gem_checks": False}

    def test_no_gem_locations_or_items(self) -> None:
        locations = {loc.name for loc in self.multiworld.get_locations(self.player)}
        self.assertFalse(any(name.endswith(" - Gem") for name in locations))
        self.assertFalse(self.get_items_by_name("Clear Gem"))
        self.assertFalse(self.get_items_by_name("Green Gem"))


class TestAllGemsGoal(Crash1TestBase):
    options = {"goal": "all_gems", "starting_nodes": 1}


class TestMaxStart(Crash1TestBase):
    options = {"starting_nodes": 10, "gem_checks": False}


class TestTraps(Crash1TestBase):
    options = {"trap_chance": 100}

    def test_all_filler_is_traps(self) -> None:
        traps = self.get_items_by_name("No Lives Trap")
        self.assertTrue(traps)
        self.assertFalse(self.get_items_by_name("Extra Life"))

    def test_every_trap_by_default_weights(self) -> None:
        for name in ("No Lives Trap", "Upside Down Trap", "Reverse Controls Trap", "Button Swap Trap"):
            self.assertTrue(self.get_items_by_name(name), name)


class TestTrapWeights(Crash1TestBase):
    options = {"trap_chance": 100, "no_lives_trap_weight": 0, "upside_down_trap_weight": 0,
               "reverse_controls_trap_weight": 0, "button_swap_trap_weight": 3}

    def test_only_weighted_traps(self) -> None:
        self.assertTrue(self.get_items_by_name("Button Swap Trap"))
        for name in ("No Lives Trap", "Upside Down Trap", "Reverse Controls Trap"):
            self.assertFalse(self.get_items_by_name(name), name)


class TestAllTrapWeightsZero(Crash1TestBase):
    options = {"trap_chance": 100, "no_lives_trap_weight": 0, "upside_down_trap_weight": 0,
               "reverse_controls_trap_weight": 0, "button_swap_trap_weight": 0}

    def test_no_traps(self) -> None:
        self.assertFalse(any(item.classification & ItemClassification.trap for item in self.multiworld.itempool))


class TestNoTrapsByDefault(Crash1TestBase):
    def test_no_traps(self) -> None:
        self.assertFalse(self.get_items_by_name("No Lives Trap"))


class TestPoolSize(Crash1TestBase):
    def test_item_count_matches_locations(self) -> None:
        locations = [loc for loc in self.multiworld.get_locations(self.player) if loc.address is not None]
        items = [item for item in self.multiworld.itempool if item.player == self.player]
        self.assertEqual(len(locations), len(items))
        self.assertEqual(len(locations), 60 + 19 * 2 + 3)  # + bonus rounds reached and cleared + life counts 10/20/30
        self.assertEqual(len(self.get_items_by_name("Map Progress")), 31 - 3)
