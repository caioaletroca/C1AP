"""Box milestones, bonus rounds, life counts and in-level filler (v0.3)."""
import unittest
from collections import Counter
from dataclasses import replace

from .. import filler, ram
from ..data import LEVEL_BY_NAME, Bonus
from .bases import Crash1TestBase
from .test_watcher import MAP, lid, loc, make_watcher

PTR = 0x800A0000
U = ram.UNIT


def crash(lives: int = 4, fruit: int = 0, tawna: int = 0, brio: int = 0, cortex: int = 0) -> ram.CrashFields:
    return ram.CrashFields(fruit=fruit * U, lives=lives * U, cortex=cortex * U, brio=brio * U, tawna=tawna * U)


class Tier1WatcherTest(unittest.TestCase):
    def setUp(self) -> None:
        self.watcher = make_watcher()
        self.received: Counter[str] = Counter()
        self.checked: set[int] = set()

    def step(self, snap: ram.Snapshot) -> ram.Snapshot:
        self.actions = self.watcher.step(snap, self.received, self.checked)
        self.checked |= self.actions.locations
        return snap

    def in_level(self, name: str, fields: ram.CrashFields | None = None, **kwargs) -> ram.Snapshot:
        kwargs.setdefault("gamestate", ram.GAMESTATE_PLAYING)
        return replace(MAP, level=lid(name), crash_ptr=PTR, crash=fields if fields is not None else crash(), **kwargs)


class TestBoxMilestones(Tier1WatcherTest):
    def setUp(self) -> None:
        super().setUp()
        self.watcher = make_watcher(box_checks=2)

    def test_quarters(self) -> None:
        # Boulders: 16 boxes -> 4, 8, 12
        self.step(self.in_level("Boulders", box_count=3 * U))
        self.assertFalse(self.actions.locations)
        self.step(self.in_level("Boulders", box_count=4 * U))
        self.assertEqual(self.actions.locations, {loc("Boulders - 25% Boxes")})
        self.step(self.in_level("Boulders", box_count=12 * U))
        self.assertTrue({loc("Boulders - 50% Boxes"), loc("Boulders - 75% Boxes")} <= self.checked)

    def test_rounds_up(self) -> None:
        level = LEVEL_BY_NAME["Upstream"]  # 14 boxes
        self.assertEqual([level.box_threshold(p) for p in (25, 50, 75)], [4, 7, 11])

    def test_counts_for_the_played_level(self) -> None:
        # Level shuffle: node 1 loads Boulders, so its boxes count for Boulders
        self.step(self.in_level("Boulders", current_node=1, box_count=4 * U))
        self.assertEqual(self.actions.locations, {loc("Boulders - 25% Boxes")})

    def test_not_in_bonus_rounds(self) -> None:
        self.step(self.in_level("Jungle Rollers"))
        self.step(replace(self.in_level("Jungle Rollers"), level=0x24, box_count=30 * U))
        self.assertFalse({loc("Jungle Rollers - 25% Boxes")} & self.checked)

    def test_off_by_default(self) -> None:
        self.watcher = make_watcher()
        self.step(self.in_level("Boulders", box_count=16 * U))
        self.assertFalse(self.actions.locations)

    def test_gem_path_milestone_needs_gem_checks(self) -> None:
        self.watcher = make_watcher(box_checks=2, gem_checks=False)
        self.step(self.in_level("Jungle Rollers", box_count=38 * U))
        self.assertIn(loc("Jungle Rollers - 50% Boxes"), self.checked)
        self.assertNotIn(loc("Jungle Rollers - 75% Boxes"), self.checked)

    def test_box_total_note_when_won_state_is_missed(self) -> None:
        # BizHawk round 8: lag hid 0x500; the 0x300 exit shows with the map's level ID
        self.step(self.in_level("Boulders", box_count=16 * U))
        self.step(replace(MAP, gamestate=ram.GAMESTATE_EXIT_TO_MAP))
        self.assertEqual(len(self.actions.notes), 1)
        self.assertIn("up to 16 boxes", self.actions.notes[0])

    def test_box_total_note_on_win(self) -> None:
        self.step(self.in_level("Boulders", box_count=16 * U))
        self.step(self.in_level("Boulders", box_count=16 * U, gamestate=ram.GAMESTATE_LEVEL_WON))
        self.assertEqual(len(self.actions.notes), 1)
        self.assertIn("up to 16 boxes", self.actions.notes[0])
        self.step(self.in_level("Boulders", box_count=16 * U, gamestate=ram.GAMESTATE_LEVEL_WON))
        self.assertFalse(self.actions.notes)


class TestBonusRounds(Tier1WatcherTest):
    def setUp(self) -> None:
        super().setUp()
        self.watcher = make_watcher(bonus_round_checks=3)

    def test_cleared(self) -> None:
        # Crash warps out with 0x300, which lasts through the load back into the level
        self.enter_bonus("Rolling Stones", 0x25, crash(brio=3))
        self.step(replace(self.in_level("Rolling Stones"), level=0x25, gamestate=ram.GAMESTATE_EXIT_TO_MAP))
        self.assertIn(loc("Rolling Stones - Brio Bonus Cleared"), self.actions.locations)
        self.assertIn("cleared", self.actions.notes[0])
        self.step(self.in_level("Rolling Stones", gamestate=ram.GAMESTATE_EXIT_TO_MAP))
        self.step(self.in_level("Rolling Stones"))
        self.assertNotIn(loc("Rolling Stones - Complete"), self.checked)
        self.assertFalse(self.actions.notes)

    def test_died_in_the_bonus(self) -> None:
        # Dying in a bonus zone keeps 0x100 and loads the level's checkpoint
        self.enter_bonus("Rolling Stones", 0x25, crash(brio=3))
        self.step(replace(self.in_level("Rolling Stones"), level=0x25))
        self.step(self.in_level("Rolling Stones"))
        self.assertIn(loc("Rolling Stones - Brio Bonus"), self.checked)
        self.assertNotIn(loc("Rolling Stones - Brio Bonus Cleared"), self.checked)
        self.assertIn("left without clearing", self.actions.notes[0])

    def test_reach_only(self) -> None:
        self.watcher = make_watcher(bonus_round_checks=1)
        self.enter_bonus("Rolling Stones", 0x25, crash(brio=3))
        self.step(replace(self.in_level("Rolling Stones"), level=0x25, gamestate=ram.GAMESTATE_EXIT_TO_MAP))
        self.assertEqual(self.checked, {loc("Rolling Stones - Brio Bonus")})

    def test_clear_only(self) -> None:
        self.watcher = make_watcher(bonus_round_checks=2)
        self.enter_bonus("Rolling Stones", 0x25, crash(brio=3))
        self.assertFalse(self.checked)
        self.step(replace(self.in_level("Rolling Stones"), level=0x25, gamestate=ram.GAMESTATE_EXIT_TO_MAP))
        self.assertEqual(self.checked, {loc("Rolling Stones - Brio Bonus Cleared")})

    def enter_bonus(self, name: str, bonus_lid: int, fields: ram.CrashFields) -> None:
        self.step(self.in_level(name, fields))
        self.step(self.in_level(name, fields))
        self.step(replace(self.in_level(name, crash(tawna=0)), level=bonus_lid))

    def test_two_bonus_rounds_in_one_level(self) -> None:
        # BizHawk round 8: Rolling Stones' Brio bonus (0x25) was missed after its Tawna bonus (0x33)
        self.enter_bonus("Rolling Stones", 0x33, crash(tawna=3, brio=2))
        self.step(replace(self.in_level("Rolling Stones"), level=0x33))
        self.step(self.in_level("Rolling Stones", crash(brio=2)))
        self.step(self.in_level("Rolling Stones", crash(brio=3)))
        self.step(replace(self.in_level("Rolling Stones"), level=0x25))
        self.assertTrue({loc("Rolling Stones - Tawna Bonus"), loc("Rolling Stones - Brio Bonus")} <= self.checked)

    def test_leaving_the_bonus_is_not_a_win(self) -> None:
        # BizHawk round 8: Jungle Rollers - Complete fired when the Tawna bonus ended
        self.watcher = make_watcher(box_checks=2)
        self.enter_bonus("Jungle Rollers", 0x24, crash(tawna=3))
        for state in (ram.GAMESTATE_EXIT_TO_MAP, ram.GAMESTATE_LEVEL_WON):
            self.step(replace(self.in_level("Jungle Rollers"), level=0x24, gamestate=state))
            self.step(self.in_level("Jungle Rollers", gamestate=state))
            self.assertNotIn(loc("Jungle Rollers - Complete"), self.checked)
            self.assertFalse(any("won with" in note for note in self.actions.notes))
        # back in the level, then won for real
        self.step(self.in_level("Jungle Rollers"))
        self.step(self.in_level("Jungle Rollers", gamestate=ram.GAMESTATE_EXIT_TO_MAP))
        self.assertIn(loc("Jungle Rollers - Complete"), self.checked)
        self.assertTrue(any("won with" in note for note in self.actions.notes))

    def test_tawna_from_tokens(self) -> None:
        self.enter_bonus("Jungle Rollers", 0x26, crash(tawna=3))
        self.assertEqual(self.actions.locations, {loc("Jungle Rollers - Tawna Bonus")})
        self.assertIn("counted as Tawna", self.actions.notes[0])

    def test_brio_from_tokens_beats_level_id(self) -> None:
        self.enter_bonus("Rolling Stones", 0x24, crash(brio=3, tawna=1))
        self.assertEqual(self.actions.locations, {loc("Rolling Stones - Brio Bonus")})

    def test_level_id_when_tokens_unknown(self) -> None:
        self.step(replace(MAP, level=lid("Rolling Stones"), gamestate=ram.GAMESTATE_PLAYING))
        self.step(replace(MAP, level=ram.LID_BONUS_BRIO, gamestate=ram.GAMESTATE_PLAYING))
        self.assertEqual(self.actions.locations, {loc("Rolling Stones - Brio Bonus")})

    def test_once_per_visit(self) -> None:
        self.enter_bonus("Jungle Rollers", 0x24, crash(tawna=3))
        self.step(replace(self.in_level("Jungle Rollers"), level=0x24))
        self.assertFalse(self.actions.notes)

    def test_cortex_bonus_is_the_key_not_a_bonus_check(self) -> None:
        self.enter_bonus("Sunset Vista", ram.LID_BONUS_CORTEX, crash(cortex=3))
        self.assertFalse(self.actions.locations)
        self.assertIn("counted as Cortex", self.actions.notes[0])

    def test_unlisted_bonus_is_noted(self) -> None:
        self.enter_bonus("Boulders", 0x24, crash(tawna=3))
        self.assertFalse(self.actions.locations)
        self.assertIn("no Tawna bonus", self.actions.notes[-1])

    def test_off(self) -> None:
        self.watcher = make_watcher()
        self.enter_bonus("Jungle Rollers", 0x24, crash(tawna=3))
        self.assertFalse(self.actions.locations)


class TestLifeCounts(Tier1WatcherTest):
    def setUp(self) -> None:
        super().setUp()
        self.watcher = make_watcher(life_count_checks=(10, 20))

    def test_on_map(self) -> None:
        self.step(replace(MAP, lives=10 * U))
        self.assertEqual(self.actions.locations, {loc("Reach 10 Lives")})

    def test_in_level_after_two_polls(self) -> None:
        self.step(self.in_level("Boulders", crash(lives=12)))
        self.assertFalse(self.actions.locations, "the pointer is trusted from the second poll")
        self.step(self.in_level("Boulders", crash(lives=12)))
        self.assertEqual(self.actions.locations, {loc("Reach 10 Lives")})

    def test_stale_global_in_level_is_ignored(self) -> None:
        self.step(self.in_level("Boulders", crash(lives=4), lives=30 * U))
        self.step(self.in_level("Boulders", crash(lives=4), lives=30 * U))
        self.assertFalse(self.actions.locations)

    def test_implausible_fields_are_ignored(self) -> None:
        junk = ram.CrashFields(fruit=0x1234, lives=50 * U, cortex=0, brio=0, tawna=0)
        self.step(self.in_level("Boulders", junk))
        self.step(self.in_level("Boulders", junk))
        self.assertFalse(self.actions.locations)
        self.assertFalse(self.actions.can_apply_live_filler)

    def test_pointer_change_resets_trust(self) -> None:
        self.step(self.in_level("Boulders", crash(lives=12)))
        self.step(replace(self.in_level("Boulders", crash(lives=12)), crash_ptr=PTR + 0x400))
        self.assertFalse(self.actions.locations)


class TestLiveFiller(Tier1WatcherTest):
    def test_live_filler_needs_two_polls(self) -> None:
        self.step(self.in_level("Boulders"))
        self.assertFalse(self.actions.can_apply_live_filler)
        self.step(self.in_level("Boulders"))
        self.assertTrue(self.actions.can_apply_live_filler)
        self.assertFalse(self.actions.can_apply_filler)

    def test_not_on_level_end_screen(self) -> None:
        self.step(replace(self.in_level("Boulders"), level=ram.LID_LEVEL_END))
        self.step(replace(self.in_level("Boulders"), level=ram.LID_LEVEL_END))
        self.assertFalse(self.actions.can_apply_live_filler)


class TestFillerPlans(unittest.TestCase):
    def level(self, **kwargs) -> ram.Snapshot:
        return replace(MAP, level=lid("Boulders"), gamestate=ram.GAMESTATE_PLAYING, crash_ptr=PTR,
                       crash=crash(**kwargs))

    def test_extra_life_in_level(self) -> None:
        plan = filler.plan_in_level(filler.EXTRA_LIFE, self.level(lives=5))
        lives_at = ram.field_address(PTR, ram.FIELD_LIVES)
        self.assertEqual(lives_at, PTR + 0x164)
        self.assertEqual(plan.writes, {lives_at: 6 * U})
        self.assertEqual(plan.guards, {ram.CRASH_PTR: PTR, lives_at: 5 * U})

    def test_wumpa_rolls_over_into_a_life(self) -> None:
        plan = filler.plan_in_level(filler.WUMPA_BUNDLE, self.level(lives=5, fruit=95))
        self.assertEqual(plan.writes, {ram.field_address(PTR, ram.FIELD_FRUIT): 5 * U,
                                       ram.field_address(PTR, ram.FIELD_LIVES): 6 * U})

    def test_life_cap(self) -> None:
        plan = filler.plan_in_level(filler.EXTRA_LIFE, self.level(lives=99))
        self.assertEqual(plan.writes, {})

    def test_mask_waits_for_the_map(self) -> None:
        self.assertIsNone(filler.plan_in_level(filler.AKU_AKU_MASK, self.level()))
        self.assertEqual(filler.plan_on_map(filler.AKU_AKU_MASK, MAP).writes, {ram.HEALTH: U})

    def test_pending_skips_applied_per_name(self) -> None:
        received = [filler.AKU_AKU_MASK, filler.EXTRA_LIFE, filler.EXTRA_LIFE, filler.AKU_AKU_MASK]
        applied = Counter({filler.EXTRA_LIFE: 1})
        self.assertEqual(filler.pending(received, applied),
                         [filler.AKU_AKU_MASK, filler.EXTRA_LIFE, filler.AKU_AKU_MASK])

    def test_old_storage_is_converted(self) -> None:
        received = [filler.EXTRA_LIFE, filler.AKU_AKU_MASK, filler.EXTRA_LIFE]
        self.assertEqual(filler.applied_counts(2, received),
                         Counter({filler.EXTRA_LIFE: 1, filler.AKU_AKU_MASK: 1}))
        self.assertEqual(filler.applied_counts({"Extra Life": 2}, received), Counter({filler.EXTRA_LIFE: 2}))
        self.assertEqual(filler.applied_counts(None, received), Counter())

    def test_parse_reads_the_pointer_and_fields(self) -> None:
        globals_block = bytes(ram.GLOBALS_SIZE)
        snap = ram.parse(globals_block, bytes(ram.LID_BLOCK_SIZE), ram.word_bytes(PTR))
        self.assertEqual(snap.crash_ptr, PTR)
        words = [7 * U, 3 * U, 0, 0, 0, 0, 1 * U, 2 * U, 3 * U]
        snap = ram.with_crash(snap, b"".join(ram.word_bytes(word) for word in words))
        self.assertEqual(snap.crash, ram.CrashFields(fruit=7 * U, lives=3 * U, cortex=U, brio=2 * U, tawna=3 * U))
        self.assertEqual(ram.crash_request(PTR), (PTR + 0x160 - ram.RAM_BASE, 36, ram.DOMAIN))


class TestTier1Options(Crash1TestBase):
    options = {"box_checks": "quarters", "life_count_checks": ["5", "99"], "level_shuffle": False}

    def test_location_counts(self) -> None:
        names = {location.name for location in self.multiworld.get_locations(self.player)}
        self.assertEqual(sum(name.endswith("% Boxes") for name in names), 26 * 3)
        self.assertEqual(sum(name.endswith(" Bonus") for name in names), 19)
        self.assertEqual({name for name in names if name.startswith("Reach ")}, {"Reach 5 Lives", "Reach 99 Lives"})

    def test_gem_path_milestone_rule(self) -> None:
        self.assertAccessDependency(["Jungle Rollers - 75% Boxes"], [["Green Gem"]], only_check_listed=True)
        self.collect_by_name("Map Progress")
        self.assertTrue(self.can_reach_location("Jungle Rollers - 50% Boxes"))

    def test_life_counts_need_map_progress(self) -> None:
        self.assertTrue(self.can_reach_location("Reach 5 Lives"))
        self.assertFalse(self.can_reach_location("Reach 99 Lives"))


class TestTier1WithoutGems(Crash1TestBase):
    options = {"box_checks": "quarters", "gem_checks": False}

    def test_gem_path_milestones_are_left_out(self) -> None:
        names = {location.name for location in self.multiworld.get_locations(self.player)}
        self.assertNotIn("Jungle Rollers - 75% Boxes", names)
        self.assertIn("Boulders - 75% Boxes", names)
        self.assertEqual(sum(name.endswith("75% Boxes") for name in names), 26 - 10)


class TestTier1Off(Crash1TestBase):
    options = {"bonus_round_checks": False, "life_count_checks": []}

    def test_v02_locations_only(self) -> None:
        locations = [loc for loc in self.multiworld.get_locations(self.player) if loc.address is not None]
        self.assertEqual(len(locations), 60)
        self.assertEqual(Bonus.TAWNA.value, "Tawna")
