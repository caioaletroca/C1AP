-- C1AP Death Link: find the in-level lives counter.
-- The GOOL global LIFECOUNT only syncs at level end, so the HUD reads lives from somewhere else while playing.
-- This narrows every byte of MainRAM down to the ones that move with the lives count (plain n, or n << 8: then
-- its second byte moves by 1).
--
-- Play inside a level and press, after each event:
--   U  snapshot: lives Unchanged (did NOT change) since the last snapshot
--   L  snapshot: Lost exactly one life since the last snapshot (press after Crash respawns)
--   G  snapshot: Gained exactly one life since the last snapshot (life box / 100 fruit)
--   O  start Over
-- (U, L, G, O were already used by the poke test, so none of them is a BizHawk hotkey.)
-- The first key press only takes the starting snapshot. Candidates are printed once 20 or fewer remain.

memory.usememorydomain("MainRAM")
local SIZE = 0x200000

local previous = nil
local candidates = nil   -- set of byte offsets still possible
local count = 0

local function snapshot()
  return memory.read_bytes_as_array(0, SIZE, "MainRAM")   -- 1-indexed
end

local function show()
  console.log(string.format("[%d] %d candidates", emu.framecount(), count))
  if count <= 20 then
    local list = {}
    for offset in pairs(candidates) do list[#list + 1] = offset end
    table.sort(list)
    for _, offset in ipairs(list) do
      local aligned = offset - offset % 4
      console.log(string.format("  0x%08X  byte=%d  word@0x%08X=%08X", 0x80000000 + offset,
        memory.read_u8(offset), 0x80000000 + aligned, memory.read_u32_le(aligned)))
    end
  end
end

local function step(delta, label)
  local now = snapshot()
  if previous == nil then
    previous = now
    console.log(string.format("[%d] start snapshot taken; now play and press U / L / G", emu.framecount()))
    return
  end
  local kept, n = {}, 0
  if candidates == nil then
    for i = 1, SIZE do
      if now[i] <= 99 and (now[i] - previous[i]) % 256 == delta % 256 then kept[i - 1] = true n = n + 1 end
    end
  else
    for offset in pairs(candidates) do
      local value = now[offset + 1]
      if value <= 99 and (value - previous[offset + 1]) % 256 == delta % 256 then kept[offset] = true n = n + 1 end
    end
  end
  candidates, count, previous = kept, n, now
  console.log(string.format("[%d] %s", emu.framecount(), label))
  show()
end

local actions = {
  U = function() step(0, "no change") end,
  L = function() step(-1, "lost a life") end,
  G = function() step(1, "gained a life") end,
  O = function()
    previous, candidates, count = nil, nil, 0
    console.log("reset; press U / L / G for the start snapshot")
  end,
}

console.log("C1AP lives search ready: in a level, press U for the start snapshot")
local held = {}
while true do
  local keys = input.get()
  for key, action in pairs(actions) do
    if keys[key] and not held[key] then action() end
    held[key] = keys[key] == true
  end
  emu.frameadvance()
end
