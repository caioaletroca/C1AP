# Address verification (milestone M0)

Every address in `crash1/ram.py` marked `VERIFY` comes from the decompilation and GOOL dumps, not from a
running game. Before C1AP can be played, each item below needs a short BizHawk test. Record the result
(✅ / ❌ + what you saw) in the table and fix `ram.py` where needed.

Setup: BizHawk 2.9.1+, NTSC-U disc (SCUS-94900), `Tools > Lua Console`, open `tools/c1ap_ram_watch.lua`.
The script draws every watched word and logs each change with the frame number.

| # | Test | Expect | Result |
|---|---|---|---|
| 1 | `validate_rom`: in the Lua console run `memory.usememorydomain("MainRAM")` and search the first 128 KB for `SCUS_949.00` (Tools > Hex Editor > Find) | string found while in game | |
| 2 | Enter a level from the map | `LEVEL` and `cur_lid` become the level ID listed in `crash1/data.py`; `CURRENTLEVEL` becomes the map node | |
| 3 | On the map, freeze nothing; select node 1 and, the moment `next_lid` changes, poke `next_lid` to `0x0E` (Boulders) | Boulders loads instead of N. Sanity Beach (**this is what level shuffle needs**) | |
| 4 | Finish the level from test 3 | Map returns to node 1 (not node 4); note `CURRENTLEVEL` | |
| 5 | Poke `LEVELSUNLOCKED` to 5 on the map, leave and re-enter the map (or enter/exit a level) | nodes 1–5 reachable, 6+ not | |
| 6 | Finish a level normally | `LEVEL` goes level → (0x2D?) → 0x19 with `GAMESTATE` 0x100; no 0x200/0x300 | |
| 7 | Lose all lives in a level | `GAMESTATE` passes through 0x200/0x300 before the map | |
| 8 | Collect a clear gem | exactly one new `ITEMPOOL1`/`ITEMPOOL2` bit, logged with `bitN->1`; write down level → bit | |
| 9 | Collect the Green Gem in The Lost City | `ITEMPOOL1` bit 12; Blue in Toxic Waste: bit 21 or 23? | |
| 10 | Clear `ITEMPOOL1` bit 12 while in Jungle Rollers | green gem path platform does not appear | |
| 11 | Get the Sunset Vista key (Cortex bonus) | `ITEMPOOL2` bit 20 | |
| 12 | Die once | `DEATHCOUNT` +1 | |
| 13 | Poke `LIFECOUNT`, `HEALTH`, `FRUITCOUNT` += 0x100 | +1 life / +1 mask / +1 fruit on HUD | |
| 14 | Beat Cortex | `LEVEL` becomes 0x39 | |
| 15 | Sunset Vista is node 16 and Slippery Climb node 24 on NTSC-U | — | |
| 16 | Is there a level with no gem besides bosses? (assumed The Great Hall) | — | |

If test 3 fails (the engine already read the level ID before the client could write it), level shuffle
needs another approach (a GOOL patch of the map script) and `level_shuffle` must default to off until then.

## Results log

**Round 2 (N. Sanity Beach, new game, no death):**
- `cur_lid` is the plain level ID (`LEVEL` holds it << 8). Lives/masks/fruit are << 8 and only update at level end.
- `GAMESTATE`: 0 on the map, 0x100 in a level, **0x500 the moment the level is won**, 0x300 on the normal exit to
  the map (not a game over).
- `next_lid` is -1 when idle and holds the level ID for only ~3 frames while loading. The level end screen is 0x2D.
- `LEVELSUNLOCKED` +1 when winning the furthest level; the map rebuilds `MAPLEVELLINKS` from it on entry.
- N. Sanity Beach gem = `ITEMPOOL1` bit 1, awarded on the level end screen.

**Round 3 (shuffle):** ✅ swapping `next_lid` 09 → 0E during the map's request loads Boulders; ✅ writing
`next_lid` = 0E while idle on the map loads Boulders.

**Round 4:** ✅ late swap (asking for 0E 5 frames after N. Sanity Beach started loading) loads Boulders, no
glitches; ✅ after the shuffled level the map advances from the node that was entered; ✅ `CURRENTLEVEL` is set on
the frame the node is selected. Level won without a gem: 0x100 → **0x300** (no 0x500). Game over: **0x200** → map;
continue reloads the save (`LEVELSUNLOCKED`, `CURRENTLEVEL`, lives revert). ❌ `DEATHCOUNT` (<< 8) rose once over
several deaths and resets on exit: not usable for Death Link.

**Round 5:** ✅ `LEVELSUNLOCKED` = 5 + `MAPLEVELLINKS` = 0x3F on the map opens nodes 1–5 at once. ✅ Disc ID in
MainRAM at 0x00928C, 0x009E19, 0x00B8B7 (`SCUS_949.00`) and 0x010E8A (`SCUS-94900`), inside the client's 128 KB
scan. ❓ Poking lives +0x100, health +0x100 and fruit +0xA00 on the map, then the emulator paused: F is BizHawk's frame-advance hotkey, not a game crash (fruit moved to N).

**Round 5b:** ✅ lives +0x100, health +0x100 and fruit +0xA00 written on the map carry into the next level
(5 lives, Aku Aku, 10 fruit). Filler on the map works.

**Round 6:** ✅ `O` (`LEVELSUNLOCKED` 31, `MAPLEVELLINKS` 0xFFFFFFFF) opens every node. ✅ Green (bit 12, Jungle
Rollers path) and Yellow (bit 29, The Great Gate path) set on the map make the gem path appear. ⚠️ Setting a colored
gem bit **inside** a level does nothing until the level is reloaded: gem bits are read at level load.
✅ New `GAMESTATE` **0x400** = **quit from the pause menu** (The Great Gate, twice): 0x100 → 0x400 → map, lives/fruit
still sync. Never a completion.

**Round 7:** ✅ winning an already-unlocked level (all nodes open, N. Sanity Beach, died once, no gem): 0x100 →
0x500 → level end (0x2D) → 0x300 → map. 0x500 means "go to the level end screen", gem or not.

**First connected run:** ✅ shuffle, checks, items, key bit (`ITEMPOOL2` bit 20 + `MAPKEYLINKS`), resync after
loading an old save state, bonus round (0x24, returns through `next_lid` = -2) all work. ❌→✅ the 0x300 exit shows
with the level's ID for only 1-2 frames (missed Road to Nowhere); now also counted with the map's ID.
**Gems belong to nodes:** Toxic Waste on node 4 awarded `ITEMPOOL1` bit 4 (a clear gem), not Blue. Gem bit = node
(1-29 minus boss nodes; secret nodes 40/50 → `ITEMPOOL2` bits 8/18). Blue = bit 21 (node 21).
❓ Does a level on a boss node (no gem bit) award anything? → `c1ap_boss_node_test.lua`.
✅ **Boss node:** N. Sanity Beach on node 6 (Papu Papu's) awarded `ITEMPOOL1` bit 6 → every node has a gem slot,
bit = node. Gem levels may go on any node.

**Colored node (seed 1):** ✅ N. Sanity Beach on node 12 (Green's node), Green not owned: the game set `ITEMPOOL1`
bit 12 on the level end screen, the client sent "N. Sanity Beach - Gem" and cleared the bit 4 frames later (no Green
path without the item). Colored-node masking works live.
