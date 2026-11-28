"""The controller routine, run on a tiny MIPS interpreter, does exactly what ``hook.swap`` describes."""
import re
import struct
import unittest
from pathlib import Path

from .. import hook

TOOLS = Path(__file__).resolve().parents[2] / "tools"


def run_routine(buttons: int, flags: int, a0: int = 0) -> tuple[int, int, int]:
    """Execute the routine as if Pad_Update called it. PadRead is stubbed to return ``buttons``.
    Returns (v0, sp, ra) on return."""
    mem: dict[int, int] = {hook.FLAGS: flags}
    for index, word in enumerate(hook.ROUTINE):
        mem[hook.CODE + 4 * index] = word
    regs = [0] * 32
    regs[29] = 0x801FFF00
    regs[31] = 0x80016800  # return address into Pad_Update
    regs[4] = a0
    pc, branch_to = hook.CODE, None
    pending_load: tuple[int, int] | None = None  # R3000 load delay: (reg, value) lands after the next instruction

    def s16(value: int) -> int:
        return value - 0x10000 if value & 0x8000 else value

    for _ in range(200):
        word = mem[pc]
        op, rs, rt, rd = word >> 26, (word >> 21) & 31, (word >> 16) & 31, (word >> 11) & 31
        sa, funct, imm = (word >> 6) & 31, word & 63, word & 0xFFFF
        next_pc = branch_to if branch_to is not None else pc + 4
        branch_to = None
        load, pending_load = pending_load, None
        r = regs
        if word == 0:
            pass
        elif op == 0:
            if funct == 0x00: r[rd] = (r[rt] << sa) & 0xFFFFFFFF
            elif funct == 0x02: r[rd] = r[rt] >> sa
            elif funct == 0x08: branch_to = r[rs]
            elif funct == 0x23: r[rd] = (r[rs] - r[rt]) & 0xFFFFFFFF
            elif funct == 0x24: r[rd] = r[rs] & r[rt]
            elif funct == 0x25: r[rd] = r[rs] | r[rt]
            elif funct == 0x26: r[rd] = r[rs] ^ r[rt]
            elif funct == 0x2B: r[rd] = int(r[rs] < r[rt])
            else: raise AssertionError(f"funct {funct:#x}")
        elif op == 3:
            target = (pc & 0xF0000000) | ((word & 0x03FFFFFF) << 2)
            assert target == hook.PAD_READ, hex(target)
            assert r[4] == a0, "a0 must reach PadRead unchanged"
            r[31] = pc + 8
            r[2] = buttons  # the stubbed call returns in the delay slot's wake
            r[8:12] = [0xDEAD0000 + i for i in range(4)]  # PadRead clobbers temporaries
        elif op == 0x09: r[rt] = (r[rs] + s16(imm)) & 0xFFFFFFFF
        elif op == 0x0C: r[rt] = r[rs] & imm
        elif op == 0x0F: r[rt] = imm << 16
        elif op == 0x23: pending_load = (rt, mem[(r[rs] + s16(imm)) & 0xFFFFFFFF])
        elif op == 0x2B: mem[(r[rs] + s16(imm)) & 0xFFFFFFFF] = r[rt]
        else:
            raise AssertionError(f"op {op:#x}")
        if load is not None:
            r[load[0]] = load[1]
        r[0] = 0
        if next_pc == 0x80016800:
            return r[2], r[29], r[31]
        pc = next_pc
    raise AssertionError("routine did not return")


class TestRoutine(unittest.TestCase):
    def test_matches_swap_for_every_button_combination(self) -> None:
        relevant = [hook.PAD_LEFT, hook.PAD_RIGHT, hook.PAD_X, hook.PAD_SQUARE, hook.PAD_CIRCLE, 0x1000, 0x10, 0x800]
        for flags in range(4):
            for combo in range(1 << len(relevant)):
                buttons = sum(bit for i, bit in enumerate(relevant) if combo >> i & 1) | 0xABCD0000
                with self.subTest(flags=flags, buttons=hex(buttons)):
                    v0, sp, ra = run_routine(buttons, flags)
                    self.assertEqual(v0, hook.swap(buttons, flags))
                    self.assertEqual(sp, 0x801FFF00)
                    self.assertEqual(ra, 0x80016800)

    def test_examples(self) -> None:
        self.assertEqual(hook.swap(hook.PAD_LEFT, hook.FLAG_REVERSE_X), hook.PAD_RIGHT)
        self.assertEqual(hook.swap(hook.PAD_RIGHT, hook.FLAG_REVERSE_X), hook.PAD_LEFT)
        self.assertEqual(hook.swap(hook.PAD_X, hook.FLAG_SWAP_BUTTONS), hook.PAD_SQUARE)
        self.assertEqual(hook.swap(hook.PAD_CIRCLE, hook.FLAG_SWAP_BUTTONS), hook.PAD_X)
        self.assertEqual(hook.swap(hook.PAD_X | hook.PAD_LEFT, 0), hook.PAD_X | hook.PAD_LEFT)

    def test_pad_index_passes_through(self) -> None:
        run_routine(0, 3, a0=1)

    def test_encodings(self) -> None:
        self.assertEqual(hook.jal(0x8003E460), 0x0C00F918)
        self.assertEqual(hook.JAL_CAVE, 0x0C003D01)  # 0x8000F404 >> 2


def run_roll(entry: int, a0: int, flags: int) -> tuple[int, int]:
    """Execute a sin / cos wrapper up to its jump. Returns (a0 as the jump lands, jump target)."""
    code = {hook.CODE + 4 * index: word for index, word in enumerate(hook.CAVE_CODE)}
    regs = [0] * 32
    regs[4] = a0
    regs[8] = 0xDEADBEEF
    pc, target, pending = entry, None, None
    for _ in range(20):
        word = code[pc]
        op, rs, rt, rd = word >> 26, (word >> 21) & 31, (word >> 16) & 31, (word >> 11) & 31
        sa, funct, imm = (word >> 6) & 31, word & 63, word & 0xFFFF
        load, pending = pending, None
        if word == 0:
            pass
        elif op == 0 and funct == 0x00: regs[rd] = (regs[rt] << sa) & 0xFFFFFFFF
        elif op == 0 and funct == 0x26: regs[rd] = regs[rs] ^ regs[rt]
        elif op == 0x0C: regs[rt] = regs[rs] & imm
        elif op == 0x0F: regs[rt] = imm << 16
        elif op == 0x23:
            address = (regs[rs] + (imm - 0x10000 if imm & 0x8000 else imm)) & 0xFFFFFFFF
            assert address == hook.FLAGS, hex(address)
            pending = (rt, flags)
        elif op == 2:
            assert target is None
            target = (pc & 0xF0000000) | ((word & 0x03FFFFFF) << 2)
        else:
            raise AssertionError(f"word {word:#010x}")
        if load is not None:
            regs[load[0]] = load[1]
        if target is not None and code[pc - 4] >> 26 == 2:
            return regs[4], target  # the delay slot just ran
        pc += 4
    raise AssertionError("wrapper did not jump")


class TestRoll(unittest.TestCase):
    def test_wrappers(self) -> None:
        for entry, target in ((hook.ROLL_SIN, hook.SIN), (hook.ROLL_COS, hook.COS)):
            for a0 in (0, 0x123, (-0x123) & 0xFFFFFFFF, 0x7FF, 0x800, 0xFFF):
                for flags in range(8):
                    with self.subTest(entry=hex(entry), a0=hex(a0), flags=flags):
                        out, jumped = run_roll(entry, a0, flags)
                        self.assertEqual(jumped, target)
                        want = a0 ^ 0x800 if flags & hook.FLAG_UPSIDE_DOWN else a0
                        self.assertEqual(out, want)
                        if flags & hook.FLAG_UPSIDE_DOWN:  # 180 degrees on the 12-bit circle
                            self.assertEqual((out - a0) % 0x1000, 0x800)

    def test_layout(self) -> None:
        self.assertEqual(hook.CAVE_CODE[:len(hook.ROUTINE)], hook.ROUTINE)
        self.assertEqual(hook.CAVE_SIZE, 4 + 4 * len(hook.CAVE_CODE))
        self.assertLess(hook.CAVE + hook.CAVE_SIZE, 0x80010000)  # below the executable


class TestFindCall(unittest.TestCase):
    def test_one_call(self) -> None:
        block = bytearray(hook.PAD_UPDATE_SCAN)
        struct.pack_into("<I", block, 0x40, hook.JAL_PAD_READ)
        self.assertEqual(hook.find_call(bytes(block)), hook.PAD_UPDATE + 0x40)
        struct.pack_into("<I", block, 0x40, hook.JAL_CAVE)
        self.assertEqual(hook.find_call(bytes(block)), hook.PAD_UPDATE + 0x40)

    def test_none_or_two(self) -> None:
        block = bytearray(hook.PAD_UPDATE_SCAN)
        self.assertIsNone(hook.find_call(bytes(block)))
        struct.pack_into("<I", block, 0x40, hook.JAL_PAD_READ)
        struct.pack_into("<I", block, 0x80, hook.JAL_PAD_READ)
        self.assertIsNone(hook.find_call(bytes(block)))


class TestFindCalls(unittest.TestCase):
    def test_all_three(self) -> None:
        pad = bytearray(hook.PAD_UPDATE_SCAN)
        struct.pack_into("<I", pad, 0x40, hook.JAL_PAD_READ)
        gfx = bytearray(hook.GFX_SCAN)
        struct.pack_into("<I", gfx, 0x08, hook.jal(0x80026138))  # Level_Noop
        struct.pack_into("<I", gfx, 0x18, hook.JAL_ROLL_SIN)
        struct.pack_into("<I", gfx, 0x20, hook.JAL_COS)
        struct.pack_into("<I", gfx, 0x50, hook.JAL_SIN)  # later calls (rot x) are left alone
        calls = hook.find_calls(bytes(pad), bytes(gfx))
        self.assertEqual(calls, {
            hook.PAD_UPDATE + 0x40: (hook.JAL_PAD_READ, hook.JAL_CAVE),
            hook.GFX_UPDATE_MATRICES + 0x18: (hook.JAL_SIN, hook.JAL_ROLL_SIN),
            hook.GFX_UPDATE_MATRICES + 0x20: (hook.JAL_COS, hook.JAL_ROLL_COS),
        })

    def test_missing(self) -> None:
        pad = bytearray(hook.PAD_UPDATE_SCAN)
        struct.pack_into("<I", pad, 0x40, hook.JAL_PAD_READ)
        self.assertIsNone(hook.find_calls(bytes(pad), bytes(hook.GFX_SCAN)))


class TestLuaScript(unittest.TestCase):
    def test_lua_routine_matches(self) -> None:
        """tools/c1ap_trap_test.lua carries its own copy of the cave code; it must be the same"""
        text = (TOOLS / "c1ap_trap_test.lua").read_text(encoding="utf-8")
        block = re.search(r"ROUTINE = \{(.*?)\}", text, re.S)
        self.assertIsNotNone(block)
        words = tuple(int(word, 16) for word in re.findall(r"0x([0-9A-Fa-f]{8})", block.group(1)))
        self.assertEqual(words, hook.CAVE_CODE)
        for name, value in (("CAVE", hook.CAVE), ("PAD_UPDATE", hook.PAD_UPDATE),
                            ("JAL_PAD_READ", hook.JAL_PAD_READ), ("JAL_CAVE", hook.JAL_CAVE),
                            ("GFX_UPDATE_MATRICES", hook.GFX_UPDATE_MATRICES),
                            ("JAL_SIN", hook.JAL_SIN), ("JAL_ROLL_SIN", hook.JAL_ROLL_SIN),
                            ("JAL_COS", hook.JAL_COS), ("JAL_ROLL_COS", hook.JAL_ROLL_COS)):
            self.assertRegex(text, rf"local {name} = 0x{value:08X}\b", name)
