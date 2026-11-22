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


@dataclass
class Crash1Options(PerGameCommonOptions):
    goal: Goal
    level_shuffle: LevelShuffle
    gem_checks: GemChecks
    starting_nodes: StartingNodes
    death_link: DeathLink


option_groups: list[OptionGroup] = [
    OptionGroup("Progression", [Goal, LevelShuffle, StartingNodes]),
    OptionGroup("Checks", [GemChecks]),
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
