from dataclasses import dataclass

from Options import Choice, DeathLink, DefaultOnToggle, OptionGroup, OptionSet, PerGameCommonOptions, Range

from .data import LIFE_COUNTS


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


class BoxChecks(Choice):
    """Make breaking part of each level's boxes a check (the gem is all of them).

    off: no box checks.
    half: 50% of the boxes in each level (26 checks).
    quarters: 25%, 50% and 75% of the boxes in each level (78 checks).

    Boxes only count in the level you break them in; dying takes back the boxes broken since the last checkpoint,
    as in the game. 75% may need the level's colored gem path, so it is only a check where that path's gem is an
    item (Gem Checks on) or the level has no gem path.
    """

    display_name = "Box Checks"
    option_off = 0
    option_half = 1
    option_quarters = 2
    default = option_off


class BonusRoundChecks(DefaultOnToggle):
    """Make reaching each Tawna and Brio bonus round a check (19 checks): collect the three tokens of a kind in a
    level. The two Cortex bonus rounds are already checks, since they give the keys.
    """

    display_name = "Bonus Round Checks"


class LifeCountChecks(OptionSet):
    """Life counts that are checks the first time you reach them, from 5 to 99. Extra lives from the multiworld
    count too. Higher counts are expected later: a count of N needs about N / 3 map nodes open.
    """

    display_name = "Life Count Checks"
    valid_keys = frozenset(str(lives) for lives in LIFE_COUNTS)
    default = frozenset({"10", "20", "30"})


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
    box_checks: BoxChecks
    bonus_round_checks: BonusRoundChecks
    life_count_checks: LifeCountChecks
    starting_nodes: StartingNodes
    trap_chance: TrapChance
    death_link: DeathLink


option_groups: list[OptionGroup] = [
    OptionGroup("Progression", [Goal, LevelShuffle, StartingNodes]),
    OptionGroup("Checks", [GemChecks, BoxChecks, BonusRoundChecks, LifeCountChecks]),
    OptionGroup("Traps", [TrapChance]),
]

option_presets: dict[str, dict[str, object]] = {
    "Casual": {
        "goal": Goal.option_cortex,
        "gem_checks": False,
        "box_checks": BoxChecks.option_off,
        "bonus_round_checks": False,
        "life_count_checks": [],
        "starting_nodes": 5,
    },
    "Full": {
        "goal": Goal.option_all_gems,
        "gem_checks": True,
        "box_checks": BoxChecks.option_quarters,
        "bonus_round_checks": True,
        "life_count_checks": ["10", "20", "30", "40", "50"],
        "starting_nodes": 3,
    },
}
