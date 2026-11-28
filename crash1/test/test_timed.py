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


def running(name: str, left: float = 10, banked: int = 0) -> TimedTraps:
    return TimedTraps(current=name, left=left, banked=banked)


def play(state: TimedTraps, seconds: float, snap: ram.Snapshot | None = None, step: float = 1.0):
    """Tick in steps; collect every end and start"""
    snap = snap or level()
    ended: list[str] = []
    started: list[str] = []
    while seconds > 1e-9:
        state, e, s = timed.tick(state, snap, min(step, seconds))
        ended += e
        started += s
        seconds -= step
    return state, ended, started


class TestQueue(unittest.TestCase):
    def test_received_on_the_map_waits_for_a_level(self) -> None:
        state = TimedTraps().add(UPSIDE_DOWN_TRAP, 20)
        state, ended, started = play(state, 60, MAP)
        self.assertEqual((state.current, started), (None, []))
        state, _, started = play(state, timed.START_DELAY - 1)
        self.assertEqual(started, [])
        state, _, started = play(state, 2)
        self.assertEqual(started, [UPSIDE_DOWN_TRAP])
        self.assertTrue(state.active(UPSIDE_DOWN_TRAP))

    def test_one_at_a_time_in_order_with_a_gap(self) -> None:
        state = TimedTraps().add(BUTTON_SWAP_TRAP, 20).add(UPSIDE_DOWN_TRAP, 20).add(BUTTON_SWAP_TRAP, 10)
        state, _, started = play(state, 1)  # received in a level: starts on the next tick, no start delay
        self.assertEqual(started, [BUTTON_SWAP_TRAP])
        state, ended, started = play(state, 20)
        self.assertEqual((ended, started), ([BUTTON_SWAP_TRAP], []))
        self.assertIsNone(state.current)
        state, _, started = play(state, timed.TRAP_GAP + 1)
        self.assertEqual(started, [UPSIDE_DOWN_TRAP])
        self.assertFalse(state.active(BUTTON_SWAP_TRAP))
        state, ended, started = play(state, 20 + timed.TRAP_GAP + 1 + 10)
        self.assertEqual((ended, started), ([UPSIDE_DOWN_TRAP, BUTTON_SWAP_TRAP], [BUTTON_SWAP_TRAP]))
        self.assertFalse(state.busy)

    def test_clocks_freeze_off_level(self) -> None:
        state = running(UPSIDE_DOWN_TRAP, 15)
        for frozen in (MAP, replace(level(), level=ram.LID_LEVEL_END)):
            state, _, _ = timed.tick(state, frozen, 5)
            self.assertEqual(state.left, 15)
        state, _, _ = timed.tick(state, level(), 5)
        self.assertEqual(state.left, 10)

    def test_counts_in_bonus_rounds(self) -> None:
        state, _, _ = timed.tick(running(BUTTON_SWAP_TRAP, 20), replace(level(), level=0x24), 5)
        self.assertEqual(state.left, 15)

    def test_leaving_a_level_between_traps_delays_the_next(self) -> None:
        state = TimedTraps(queue=((NO_LIVES_TRAP, 20),), wait=1)
        state, _, _ = timed.tick(state, MAP, 1)
        self.assertEqual(state.wait, timed.START_DELAY)

    def test_game_over_ends_no_lives_and_drops_the_bank(self) -> None:
        state = running(NO_LIVES_TRAP, banked=5 * U).add(UPSIDE_DOWN_TRAP, 20)
        state, ended, _ = timed.tick(state, replace(MAP, gamestate=ram.GAMESTATE_GAME_OVER), 1)
        self.assertEqual(ended, [NO_LIVES_TRAP])
        self.assertEqual(state.banked, 0)
        self.assertEqual(state.queue, ((UPSIDE_DOWN_TRAP, 20),))

    def test_json_round_trip(self) -> None:
        state = TimedTraps(((NO_LIVES_TRAP, 20), (BUTTON_SWAP_TRAP, 20)), UPSIDE_DOWN_TRAP, 12.34, 2, 3 * U)
        again = TimedTraps.from_json(state.to_json())
        self.assertEqual(again, replace(state, left=12.3))
        self.assertEqual(TimedTraps.from_json(None), TimedTraps())
        self.assertEqual(TimedTraps.from_json({"queue": [["Unknown", 5]], "current": "Unknown", "left": 5}),
                         TimedTraps())


class TestControls(unittest.TestCase):
    def test_flags_in_a_level_only(self) -> None:
        state = running(UPSIDE_DOWN_TRAP)
        self.assertEqual(timed.plan(state, level()).flags, hook.FLAG_UPSIDE_DOWN)
        self.assertEqual(timed.plan(running(REVERSE_CONTROLS_TRAP), level()).flags, hook.FLAG_REVERSE_X)
        self.assertEqual(timed.plan(TimedTraps().add(UPSIDE_DOWN_TRAP, 20), level()).flags, 0)  # waiting
        self.assertEqual(timed.plan(state, MAP).flags, 0)
        self.assertEqual(timed.plan(running(BUTTON_SWAP_TRAP), level()).flags,
                         hook.FLAG_SWAP_BUTTONS)


class TestNoLives(unittest.TestCase):
    def test_banks_the_lives_in_a_level(self) -> None:
        out = timed.plan(running(NO_LIVES_TRAP), level(lives=7))
        self.assertEqual(out.writes, {LIVES: 0})
        self.assertEqual(out.guards, {LIVES: 7 * U, ram.CRASH_PTR: PTR})
        self.assertEqual(out.state.banked, 7 * U)

    def test_lives_picked_up_meanwhile_are_banked_too(self) -> None:
        out = timed.plan(running(NO_LIVES_TRAP, banked=7 * U), level(lives=1))
        self.assertEqual(out.writes, {LIVES: 0})
        self.assertEqual(out.state.banked, 8 * U)

    def test_nothing_at_zero(self) -> None:
        out = timed.plan(running(NO_LIVES_TRAP, banked=7 * U), level(lives=0))
        self.assertFalse(out.writes)

    def test_given_back_when_over(self) -> None:
        out = timed.plan(TimedTraps(banked=7 * U), level(lives=1))
        self.assertEqual(out.writes, {LIVES: 8 * U})
        self.assertEqual(out.state.banked, 0)
        self.assertIn("7 lives back", out.notes[0])

    def test_given_back_on_the_map_while_active(self) -> None:
        out = timed.plan(running(NO_LIVES_TRAP, banked=7 * U), MAP)
        self.assertEqual(out.writes, {ram.LIFE_COUNT: 11 * U})
        self.assertEqual(out.guards, {ram.LIFE_COUNT: 4 * U})
        self.assertEqual(out.state.banked, 0)
        self.assertTrue(out.state.active(NO_LIVES_TRAP))

    def test_capped(self) -> None:
        out = timed.plan(TimedTraps(banked=60 * U), level(lives=60))
        self.assertEqual(out.writes, {LIVES: ram.MAX_LIVES})

    def test_waits_without_a_trusted_object(self) -> None:
        loading = replace(level(), crash_ptr=0)
        self.assertFalse(timed.plan(running(NO_LIVES_TRAP), loading).writes)
        self.assertFalse(timed.plan(TimedTraps(banked=4 * U), loading).writes)
