from .bases import Crash1TestBase


class TestVanillaLogic(Crash1TestBase):
    options = {"level_shuffle": False, "starting_nodes": 3}

    def test_starting_nodes_open(self) -> None:
        self.assertTrue(self.can_reach_location("N. Sanity Beach - Complete"))
        self.assertTrue(self.can_reach_location("The Great Gate - Complete"))
        self.assertFalse(self.can_reach_location("Boulders - Complete"))

    def test_map_progress_opens_nodes(self) -> None:
        self.collect(self.get_items_by_name("Map Progress")[:1])
        self.assertTrue(self.can_reach_location("Boulders - Complete"))
        self.assertFalse(self.can_reach_location("Upstream - Complete"))

    def test_colored_gem_rules(self) -> None:
        self.assertAccessDependency(["Jungle Rollers - Gem"], [["Green Gem"]], only_check_listed=True)
        self.assertAccessDependency(["The Great Gate - Gem"], [["Yellow Gem"]], only_check_listed=True)

    def test_keys(self) -> None:
        self.assertAccessDependency(["Whole Hog - Complete"], [["Whole Hog Key"]], only_check_listed=True)
        self.assertAccessDependency(["Fumbling in the Dark - Complete"], [["Fumbling in the Dark Key"]],
                                    only_check_listed=True)

    def test_victory_needs_all_map_progress(self) -> None:
        self.collect_all_but(["Map Progress", "Victory"])
        self.assertFalse(self.can_reach_region("Map Node 31"))
        self.collect_by_name("Map Progress")
        self.assertTrue(self.can_reach_region("Map Node 31"))


class TestAllGemsGoalLogic(Crash1TestBase):
    options = {"goal": "all_gems", "level_shuffle": False}

    def test_needs_gems(self) -> None:
        self.collect_all_but(["Clear Gem"])
        self.assertBeatable(False)
        self.collect_by_name("Clear Gem")
        self.assertBeatable(True)
