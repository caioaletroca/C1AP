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


class TestLuaScript(unittest.TestCase):
    def test_lua_routine_matches(self) -> None:
        """tools/c1ap_trap_test.lua carries its own copy of the routine; it must be the same code"""
        text = (TOOLS / "c1ap_trap_test.lua").read_text(encoding="utf-8")
        block = re.search(r"ROUTINE = \{(.*?)\}", text, re.S)
        self.assertIsNotNone(block)
        words = tuple(int(word, 16) for word in re.findall(r"0x([0-9A-Fa-f]{8})", block.group(1)))
        self.assertEqual(words, hook.ROUTINE)
        for name, value in (("CAVE", hook.CAVE), ("PAD_UPDATE", hook.PAD_UPDATE),
                            ("JAL_PAD_READ", hook.JAL_PAD_READ), ("JAL_CAVE", hook.JAL_CAVE)):
            self.assertRegex(text, rf"local {name} = 0x{value:08X}\b", name)
