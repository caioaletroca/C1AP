from dataclasses import dataclass

from Options import Choice, DeathLink, DefaultOnToggle, OptionGroup, PerGameCommonOptions, Range


class Goal(Choice):
    """What you need to do to finish.

    cortex: Defeat Dr. N. Cortex.
    all_gems: Defeat Dr. N. Cortex while holding all 26 gems (requires Gem Checks).
    """

    display_name = "Goal"
    option_cortex = 0
    option_all_gems = 1
    default = option_cortex


class LevelShuffle(DefaultOnToggle):
    """Shuffle which level each map node leads to.

    Dr. N. Cortex always stays at the last node, two bosses are never on adjacent nodes, and no boss is placed on a
    node that is open from the start. Secret levels stay on their vanilla branches.
    """

    display_name = "Level Shuffle"


class GemChecks(DefaultOnToggle):
    """Make every gem (20 clear, 6 colored) a check. Colored gems become items that open their gem paths.

    Gems need every box broken without dying, so turning this off makes the game much shorter and easier.
    """

    display_name = "Gem Checks"


class StartingNodes(Range):
    """How many map nodes are open from the start. Each Map Progress item opens one more node."""

    display_name = "Starting Map Nodes"
    range_start = 1
    range_end = 10
    default = 3


class TrapChance(Range):
    """Chance (in percent) for each filler item to be a trap instead.

    No Lives Trap: you play your next level with 0 lives, so one death is a game over. Back on the map, your lives
    come back (plus any you picked up in the level). A game over ends the trap without giving them back.
    """

    display_name = "Trap Chance"
    range_start = 0
    range_end = 100
    default = 0


@dataclass
class Crash1Options(PerGameCommonOptions):
    goal: Goal
    level_shuffle: LevelShuffle
    gem_checks: GemChecks
    starting_nodes: StartingNodes
    trap_chance: TrapChance
    death_link: DeathLink


option_groups: list[OptionGroup] = [
    OptionGroup("Progression", [Goal, LevelShuffle, StartingNodes]),
    OptionGroup("Checks", [GemChecks]),
    OptionGroup("Traps", [TrapChance]),
]

option_presets: dict[str, dict[str, object]] = {
    "Casual": {
        "goal": Goal.option_cortex,
        "gem_checks": False,
        "starting_nodes": 5,
    },
    "Full": {
        "goal": Goal.option_all_gems,
        "gem_checks": True,
        "starting_nodes": 3,
    },
}
