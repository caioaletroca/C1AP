-- C1AP boss-node gem test. Run alongside c1ap_ram_watch.lua and c1ap_poke_test.lua (for O = open all nodes).
-- Disconnect the Archipelago client first (stop connector_bizhawk_generic.lua), or it will fight this script.
-- Selecting node 6 (Papu Papu, 0x0A) loads N. Sanity Beach (0x09) instead. Break every box and finish:
-- does the game award a gem on a node that has none (ITEMPOOL1 bit 6 is not a gem bit)?

local NEXT_LID = 0x056714
local FROM, TO = 0x0A, 0x09

memory.usememorydomain("MainRAM")
console.log("C1AP boss-node test: select node 6 (Papu Papu) to play N. Sanity Beach there")

while true do
  if memory.read_u32_le(NEXT_LID) == FROM then
    memory.write_u32_le(NEXT_LID, TO)
    console.log(string.format("[%d] node 6: Papu Papu -> N. Sanity Beach", emu.framecount()))
  end
  emu.frameadvance()
end
