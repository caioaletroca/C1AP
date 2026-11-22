from typing import Any, ClassVar, TextIO

from BaseClasses import ItemClassification, Region, Tutorial
from Options import OptionError
from rule_builder.rules import Has, HasAll, Rule
from worlds.AutoWorld import WebWorld, World

from .data import (
    CLEAR_GEM_COUNT, COLORED_GEMS, FINAL_BOSS, KEY_BY_SECRET, KEYS, LEVEL_BY_LID, MAP_NODES, SECRET_LEVELS, Gem,
    Level,
)
from .items import (
    CLEAR_GEM, DEFAULT_CLASSIFICATION, FILLER_WEIGHTS, GAME_NAME, MAP_PROGRESS, VICTORY, Crash1Item, item_name_groups,
    item_name_to_id,
)
from .locations import CORTEX_EVENT, Crash1Location, location_name_groups, location_name_to_id
from .options import Crash1Options, Goal, option_groups, option_presets
from .shuffle import shuffle_order, vanilla_order


class Crash1Web(WebWorld):
    game = GAME_NAME
    theme = "jungle"
    bug_report_page = "https://github.com/caioaletroca/C1AP/issues"
    option_groups = option_groups
    options_presets = option_presets
    tutorials = [
        Tutorial(
            "Multiworld Setup Guide",
            "A guide to setting up Crash Bandicoot (PS1) for Archipelago with BizHawk.",
            "English",
            "setup_en.md",
            "setup/en",
            ["C1AP contributors"],
        ),
    ]


def node_region_name(node: int) -> str:
    return f"Map Node {node}"


class Crash1World(World):
    """
    Crash Bandicoot (PS1, 1996). Spin and jump across the three islands of the Wumpa archipelago to stop Dr. Neo Cortex.
    Map progress, colored gems and keys are shuffled into the multiworld, and the order of the levels on the map can be
    shuffled too.
    """

    game = GAME_NAME
    web = Crash1Web()
    options_dataclass = Crash1Options
    options: Crash1Options
    topology_present = True

    item_name_to_id: ClassVar[dict[str, int]] = item_name_to_id
    location_name_to_id: ClassVar[dict[str, int]] = location_name_to_id
    item_name_groups = item_name_groups
    location_name_groups = location_name_groups

    level_order: list[Level]
    """Level on each map node; index 0 is node 1"""

    def generate_early(self) -> None:
        if self.options.goal == Goal.option_all_gems and not self.options.gem_checks:
            raise OptionError(f"{self.player_name}: goal 'all_gems' requires gem_checks to be on")

        # Universal Tracker regenerates from slot data so the tracked level order matches the real seed.
        passthrough: dict[str, Any] = getattr(self.multiworld, "re_gen_passthrough", {}).get(self.game, {})
        if passthrough:
            self.options.starting_nodes.value = passthrough["starting_nodes"]
            self.options.gem_checks.value = passthrough["gem_checks"]
            self.options.goal.value = passthrough["goal"]
            self.level_order = [LEVEL_BY_LID[lid] for lid in passthrough["level_order"]]
        elif self.options.level_shuffle:
            self.level_order = shuffle_order(self.random, self.options.starting_nodes.value)
        else:
            self.level_order = vanilla_order()

    # Regions and locations

    def create_regions(self) -> None:
        menu = Region("Menu", self.player, self.multiworld)
        self.multiworld.regions.append(menu)

        previous = menu
        node_regions: dict[int, Region] = {}
        for node, level in enumerate(self.level_order, start=1):
            region = Region(node_region_name(node), self.player, self.multiworld)
            self.multiworld.regions.append(region)
            node_regions[node] = region
            self.create_entrance(previous, region, Has(MAP_PROGRESS, node - self.options.starting_nodes.value))
            self.add_level_locations(region, level)
            previous = region

        for secret in SECRET_LEVELS:
            key = KEY_BY_SECRET[secret.name]
            region = Region(secret.name, self.player, self.multiworld)
            self.multiworld.regions.append(region)
            self.create_entrance(node_regions[key.branch_node], region, Has(key.item_name))
            self.add_level_locations(region, secret)

    def add_level_locations(self, region: Region, level: Level) -> None:
        if level is FINAL_BOSS:
            event = Crash1Location(self.player, CORTEX_EVENT, None, region)
            event.place_locked_item(Crash1Item(VICTORY, ItemClassification.progression, None, self.player))
            region.locations.append(event)
            return

        self.add_location(region, level.complete_location)

        if self.options.gem_checks and level.gem != Gem.NONE:
            gem_location = self.add_location(region, level.gem_location)
            if level.gem_requires:
                self.set_rule(gem_location, HasAll(*(gem.item_name for gem in level.gem_requires)))

        for key in KEYS:
            if key.source == level.name:
                self.add_location(region, key.location)

    def add_location(self, region: Region, name: str) -> Crash1Location:
        location = Crash1Location(self.player, name, self.location_name_to_id[name], region)
        region.locations.append(location)
        return location

    # Items

    def create_item(self, name: str) -> Crash1Item:
        classification = DEFAULT_CLASSIFICATION[name]
        if name == CLEAR_GEM and self.options.goal == Goal.option_all_gems:
            classification = ItemClassification.progression_skip_balancing
        return Crash1Item(name, classification, self.item_name_to_id[name], self.player)

    def create_items(self) -> None:
        pool: list[Crash1Item] = [
            self.create_item(MAP_PROGRESS) for _ in range(MAP_NODES - self.options.starting_nodes.value)
        ]
        pool += [self.create_item(key.item_name) for key in KEYS]
        if self.options.gem_checks:
            pool += [self.create_item(gem.item_name) for gem in COLORED_GEMS]
            pool += [self.create_item(CLEAR_GEM) for _ in range(CLEAR_GEM_COUNT)]

        unfilled = len(self.multiworld.get_unfilled_locations(self.player))
        if len(pool) > unfilled:
            raise OptionError(f"{self.player_name}: {len(pool)} items for only {unfilled} locations")
        pool += [self.create_filler() for _ in range(unfilled - len(pool))]
        self.multiworld.itempool += pool

    def get_filler_item_name(self) -> str:
        names = list(FILLER_WEIGHTS)
        return self.random.choices(names, weights=[FILLER_WEIGHTS[name] for name in names])[0]

    # Logic

    def set_rules(self) -> None:
        goal: Rule[Any] = Has(VICTORY)
        if self.options.goal == Goal.option_all_gems:
            goal = goal & Has(CLEAR_GEM, CLEAR_GEM_COUNT) & HasAll(*(gem.item_name for gem in COLORED_GEMS))
        self.set_completion_rule(goal)

    # Output

    def fill_slot_data(self) -> dict[str, Any]:
        return {
            "level_order": [level.lid for level in self.level_order],
            "starting_nodes": self.options.starting_nodes.value,
            "gem_checks": self.options.gem_checks.value,
            "goal": self.options.goal.value,
            "death_link": self.options.death_link.value,
            "world_version": "0.1.0",
        }

    def interpret_slot_data(self, slot_data: dict[str, Any]) -> dict[str, Any]:
        """Universal Tracker: return the slot data so it is passed back in through re_gen_passthrough."""
        return slot_data

    def write_spoiler(self, spoiler_handle: TextIO) -> None:
        spoiler_handle.write(f"\n\nCrash Bandicoot level order ({self.player_name}):\n\n")
        for node, level in enumerate(self.level_order, start=1):
            spoiler_handle.write(f"  Node {node:2}: {level.name}\n")

    def extend_hint_information(self, hint_data: dict[int, dict[int, str]]) -> None:
        if not self.options.level_shuffle:
            return
        info: dict[int, str] = {}
        for node, level in enumerate(self.level_order, start=1):
            for name in (level.complete_location, level.gem_location, *(k.location for k in KEYS if k.source == level.name)):
                if name in self.location_name_to_id:
                    info[self.location_name_to_id[name]] = node_region_name(node)
        hint_data[self.player] = info
