from BaseClasses import Item, ItemClassification

from .data import COLORED_GEMS, KEYS

GAME_NAME = "Crash Bandicoot"
BASE_ID = 7_310_000


class Crash1Item(Item):
    game = GAME_NAME


MAP_PROGRESS = "Map Progress"
CLEAR_GEM = "Clear Gem"
VICTORY = "Victory"

FILLER_WEIGHTS: dict[str, int] = {
    "Extra Life": 3,
    "Aku Aku Mask": 4,
    "Wumpa Fruit Bundle": 3,
}

# IDs are permanent once released: never renumber, only append.
item_name_to_id: dict[str, int] = {
    MAP_PROGRESS: BASE_ID + 1,
    **{key.item_name: BASE_ID + 10 + index for index, key in enumerate(KEYS)},
    **{gem.item_name: BASE_ID + 20 + index for index, gem in enumerate(COLORED_GEMS)},
    CLEAR_GEM: BASE_ID + 30,
    **{name: BASE_ID + 40 + index for index, name in enumerate(FILLER_WEIGHTS)},
}

item_name_groups: dict[str, set[str]] = {
    "Keys": {key.item_name for key in KEYS},
    "Colored Gems": {gem.item_name for gem in COLORED_GEMS},
    "Gems": {gem.item_name for gem in COLORED_GEMS} | {CLEAR_GEM},
    "Filler": set(FILLER_WEIGHTS),
}

DEFAULT_CLASSIFICATION: dict[str, ItemClassification] = {
    MAP_PROGRESS: ItemClassification.progression,
    **{key.item_name: ItemClassification.progression for key in KEYS},
    **{gem.item_name: ItemClassification.progression for gem in COLORED_GEMS},
    CLEAR_GEM: ItemClassification.filler,
    **{name: ItemClassification.filler for name in FILLER_WEIGHTS},
}
