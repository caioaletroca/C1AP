-- C1AP shuffle test. Run alongside c1ap_ram_watch.lua (Lua Console > Script > Open, both can run).
-- Mode C (late swap, like the real client): when N. Sanity Beach (0x09) has already started loading, wait
-- DELAY frames, then ask for Boulders (0x0E). Tests whether a new request replaces a load in progress.
-- Mode B: press the key below while standing on the map: writes next_lid = 0x0E with nothing loading.

local NEXT_LID, CUR_LID = 0x056714, 0x056710
local FROM, TO = 0x09, 0x0E
local DELAY = 6          -- frames; the client polls about every 6 frames
local MODE_B_KEY = "B"

memory.usememorydomain("MainRAM")
console.log("C1AP shuffle test (mode C, delay " .. DELAY .. "): select N. Sanity Beach on the map")
local held, wait = false, nil

while true do
  local cur, nxt = memory.read_u32_le(CUR_LID), memory.read_u32_le(NEXT_LID)
  if cur == FROM and nxt == 0xFFFFFFFF then
    wait = wait or DELAY
    wait = wait - 1
    if wait <= 0 then
      memory.write_u32_le(NEXT_LID, TO)
      console.log(string.format("[%d] mode C: N. Sanity Beach loading, asked for 0E", emu.framecount()))
      wait = nil
    end
  else
    wait = nil
  end
  local keys = input.get()
  if keys[MODE_B_KEY] and not held then
    memory.write_u32_le(NEXT_LID, TO)
    console.log(string.format("[%d] mode B: next_lid -> 0E", emu.framecount()))
  end
  held = keys[MODE_B_KEY] == true
  emu.frameadvance()
end
