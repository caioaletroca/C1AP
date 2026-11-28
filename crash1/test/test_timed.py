"""Timed traps: clocks, camera, controller flags and the No Lives bank."""
import unittest
from dataclasses import replace

from .. import hook, ram, timed
from ..timed import (
    BUTTON_SWAP_TRAP, NO_LIVES_TRAP, REVERSE_CONTROLS_TRAP, UPSIDE_DOWN_TRAP, TimedTraps,
)
from .test_tier1 import PTR, U, crash
from .test_watcher import MAP, lid

LIVES = ram.field_address(PTR, ram.FIELD_LIVES)


def level(lives: int = 4, **kwargs) -> ram.Snapshot:
    kwargs.setdefault("gamestate", ram.GAMESTATE_PLAYING)
    return replace(MAP, level=lid("Jungle Rollers"), crash_ptr=PTR, crash=crash(lives=lives), **kwargs)


class TestClock(unittest.TestCase):
    def test_counts_only_in_a_level(self) -> None:
        state = TimedTraps().add(UPSIDE_DOWN_TRAP, 20)
        state, ended = timed.tick(state, MAP, 5)
        self.assertEqual(state.remaining[UPSIDE_DOWN_TRAP], 20)
        state, ended = timed.tick(state, level(), 5)
        self.assertEqual(state.remaining[UPSIDE_DOWN_TRAP], 15)
        state, ended = timed.tick(state, replace(level(), level=ram.LID_LEVEL_END), 5)
        self.assertEqual(state.remaining[UPSIDE_DOWN_TRAP], 15)
        state, ended = timed.tick(state, level(), 15)
        self.assertFalse(state.any_active)
        self.assertEqual(ended, [UPSIDE_DOWN_TRAP])

    def test_counts_in_bonus_rounds(self) -> None:
        state, _ = timed.tick(TimedTraps().add(BUTTON_SWAP_TRAP, 20), replace(level(), level=0x24), 5)
        self.assertEqual(state.remaining[BUTTON_SWAP_TRAP], 15)

    def test_same_trap_adds_up(self) -> None:
        state = TimedTraps().add(NO_LIVES_TRAP, 20).add(NO_LIVES_TRAP, 20)
        self.assertEqual(state.remaining[NO_LIVES_TRAP], 40)

    def test_game_over_ends_no_lives_and_drops_the_bank(self) -> None:
        state = TimedTraps({NO_LIVES_TRAP: 10, UPSIDE_DOWN_TRAP: 10}, banked=5 * U)
        state, ended = timed.tick(state, replace(MAP, gamestate=ram.GAMESTATE_GAME_OVER), 1)
        self.assertEqual(ended, [NO_LIVES_TRAP])
        self.assertEqual(state.banked, 0)
        self.assertTrue(state.active(UPSIDE_DOWN_TRAP))

    def test_json_round_trip(self) -> None:
        state = TimedTraps({NO_LIVES_TRAP: 12.34, BUTTON_SWAP_TRAP: 0}, banked=3 * U)
        again = TimedTraps.from_json(state.to_json())
        self.assertEqual(again.remaining, {NO_LIVES_TRAP: 12.3})
        self.assertEqual(again.banked, 3 * U)
        self.assertEqual(TimedTraps.from_json(None), TimedTraps())
        self.assertEqual(TimedTraps.from_json({"remaining": {"Unknown": 5}}), TimedTraps())


class TestControls(unittest.TestCase):
    def test_flags_in_a_level_only(self) -> None:
        state = TimedTraps().add(REVERSE_CONTROLS_TRAP, 20).add(BUTTON_SWAP_TRAP, 20).add(UPSIDE_DOWN_TRAP, 20)
        self.assertEqual(timed.plan(state, level()).flags,
                         hook.FLAG_REVERSE_X | hook.FLAG_SWAP_BUTTONS | hook.FLAG_UPSIDE_DOWN)
        self.assertEqual(timed.plan(state, MAP).flags, 0)
        self.assertEqual(timed.plan(TimedTraps().add(BUTTON_SWAP_TRAP, 20), level()).flags,
                         hook.FLAG_SWAP_BUTTONS)


class TestNoLives(unittest.TestCase):
    def test_banks_the_lives_in_a_level(self) -> None:
        out = timed.plan(TimedTraps().add(NO_LIVES_TRAP, 20), level(lives=7))
        self.assertEqual(out.writes, {LIVES: 0})
        self.assertEqual(out.guards, {LIVES: 7 * U, ram.CRASH_PTR: PTR})
        self.assertEqual(out.state.banked, 7 * U)

    def test_lives_picked_up_meanwhile_are_banked_too(self) -> None:
        out = timed.plan(TimedTraps({NO_LIVES_TRAP: 10}, banked=7 * U), level(lives=1))
        self.assertEqual(out.writes, {LIVES: 0})
        self.assertEqual(out.state.banked, 8 * U)

    def test_nothing_at_zero(self) -> None:
        out = timed.plan(TimedTraps({NO_LIVES_TRAP: 10}, banked=7 * U), level(lives=0))
        self.assertFalse(out.writes)

    def test_given_back_when_over(self) -> None:
        out = timed.plan(TimedTraps(banked=7 * U), level(lives=1))
        self.assertEqual(out.writes, {LIVES: 8 * U})
        self.assertEqual(out.state.banked, 0)
        self.assertIn("7 lives back", out.notes[0])

    def test_given_back_on_the_map_while_active(self) -> None:
        out = timed.plan(TimedTraps({NO_LIVES_TRAP: 10}, banked=7 * U), MAP)
        self.assertEqual(out.writes, {ram.LIFE_COUNT: 11 * U})
        self.assertEqual(out.guards, {ram.LIFE_COUNT: 4 * U})
        self.assertEqual(out.state.banked, 0)
        self.assertTrue(out.state.active(NO_LIVES_TRAP))

    def test_capped(self) -> None:
        out = timed.plan(TimedTraps(banked=60 * U), level(lives=60))
        self.assertEqual(out.writes, {LIVES: ram.MAX_LIVES})

    def test_waits_without_a_trusted_object(self) -> None:
        loading = replace(level(), crash_ptr=0)
        self.assertFalse(timed.plan(TimedTraps({NO_LIVES_TRAP: 10}), loading).writes)
        self.assertFalse(timed.plan(TimedTraps(banked=4 * U), loading).writes)
