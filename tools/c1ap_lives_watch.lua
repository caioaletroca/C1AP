-- C1AP Death Link: check the respawn counter.
-- The decompilation (esplonky/c1 level.c) adds 0x100 to respawn_count (GOOL global 0x800618A0) every time Crash
-- respawns, and resets it when a level starts. death_count (0x80061A3C) is reset at every checkpoint, which is why
-- it looked unreliable. The three byte candidates found by the search were object fields, not lives.
-- On the map (no AP client running):
--   O  open every node (LEVELSUNLOCKED = 31, MAPLEVELLINKS = all)
--   L  No Lives Trap (LIFECOUNT = 0)

memory.usememorydomain("MainRAM")

local WATCH = {
  {name = "RESPAWNCOUNT", addr = 0x0618A0},
  {name = "DEATHCOUNT", addr = 0x061A3C},
  {name = "LIFECOUNT", addr = 0x0618EC},
  {name = "GAMESTATE", addr = 0x0618D0},
  {name = "cur_lid", addr = 0x056710},
}

local last, held = {}, {}
console.log("C1AP respawn watch ready")
while true do
  local keys = input.get()
  if keys.O and not held.O then
    memory.write_u32_le(0x061948, 31)
    memory.write_u32_le(0x0619B0, 0xFFFFFFFF)
    console.log(string.format("[%d] poke O: all nodes open", emu.framecount()))
  end
  held.O = keys.O == true
  if keys.L and not held.L then
    memory.write_u32_le(0x0618EC, 0)
    console.log(string.format("[%d] poke L: lives = 0", emu.framecount()))
  end
  held.L = keys.L == true
  for _, w in ipairs(WATCH) do
    local value = memory.read_u32_le(w.addr)
    if value ~= last[w.name] then
      console.log(string.format("[%d] %s %08X -> %08X", emu.framecount(), w.name, last[w.name] or 0, value))
      last[w.name] = value
    end
  end
  emu.frameadvance()
end
