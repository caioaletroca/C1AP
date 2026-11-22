from BaseClasses import Location

from .data import FINAL_BOSS, GEM_LEVELS, KEYS, LEVELS
from .items import BASE_ID, GAME_NAME


class Crash1Location(Location):
    game = GAME_NAME


CORTEX_EVENT = FINAL_BOSS.complete_location
"""Event location (no ID) that holds the locked Victory item"""

# IDs are derived from the in-game level ID so they never change when the list is reordered.
LEVEL_COMPLETE_OFFSET = 0x000
GEM_OFFSET = 0x100
KEY_OFFSET = 0x200

location_name_to_id: dict[str, int] = {
    **{
        level.complete_location: BASE_ID + LEVEL_COMPLETE_OFFSET + level.lid
        for level in LEVELS
        if level is not FINAL_BOSS
    },
    **{level.gem_location: BASE_ID + GEM_OFFSET + level.lid for level in GEM_LEVELS},
    **{key.location: BASE_ID + KEY_OFFSET + key.pool2_bit for key in KEYS},
}

location_name_groups: dict[str, set[str]] = {
    "Level Completions": {level.complete_location for level in LEVELS if not level.is_boss},
    "Bosses": {level.complete_location for level in LEVELS if level.is_boss and level is not FINAL_BOSS},
    "Gems": {level.gem_location for level in GEM_LEVELS},
    "Keys": {key.location for key in KEYS},
}
