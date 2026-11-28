# Crash Bandicoot (PS1) for Archipelago

An [Archipelago](https://archipelago.gg) world (apworld) and BizHawk client for **Crash Bandicoot** (PS1, 1996),
NTSC-U version (SCUS-94900).

Archipelago is a multi-game randomizer: the items of every game in a session are shuffled across all the players'
worlds. In Crash Bandicoot, finishing levels and collecting gems sends items to other players (or to yourself), and
the map, the colored gems and the secret keys come back to you as items.

> **Status: alpha.** Every client feature has been tested live in BizHawk (see
> [tools/VERIFY.md](tools/VERIFY.md)). Expect rough edges, and please report them in the
> [issues](https://github.com/caioaletroca/C1AP/issues).

## What is randomized?

- **Map progress.** A few map nodes are open at the start. Each *Map Progress* item opens the next node.
- **Level shuffle** (optional). This changes which level each map node leads to. Dr. N. Cortex always stays last,
  two bosses are never next to each other, and no boss sits on a node that is open from the start.
- **Colored gems.** Green, Orange, Blue, Red, Purple and Yellow are items. Their gem paths appear once you
  receive them.
- **Keys.** The keys to *Whole Hog* and *Fumbling in the Dark* are items.
- **Filler.** Extra lives, Aku Aku masks and Wumpa fruit. Extra lives and Wumpa fruit arrive right away, even in
  the middle of a level; masks wait for the map.
- **Traps** (optional). Each lasts `trap_duration` seconds of play in a level, then the game goes back to normal:
  - *No Lives Trap*: 0 lives, so one death is a game over. Your lives come back when it ends.
  - *Upside Down Trap*: the camera rolls upside down.
  - *Reverse Controls Trap*: left and right are swapped.
  - *Button Swap Trap*: jump is on Square/Circle and spin on X.

  The clock stops on the map. The same trap again adds its time; different traps stack.

The locations are:

- Finishing each level and defeating each boss.
- Each level's gem (optional) and the two keys.
- Reaching and clearing each Tawna and Brio bonus round (optional, on by default): 19 checks each.
- Breaking 25%, 50% and 75% of each level's boxes (optional): up to 78 checks.
- Reaching chosen life counts, such as 10, 20 and 30 lives (optional).

## Goal

Defeat Dr. N. Cortex (`cortex`), or defeat him while holding all 26 gems (`all_gems`).

## Options

| Option | Values | Default |
|---|---|---|
| `goal` | `cortex`, `all_gems` | `cortex` |
| `level_shuffle` | `true` / `false` | `true` |
| `gem_checks` | `true` / `false`: gems are locations | `true` |
| `box_checks` | `off`, `half` (50%), `quarters` (25/50/75%) of each level's boxes | `off` |
| `bonus_round_checks` | `off`, `reach`, `clear` or `reach_and_clear` each Tawna and Brio bonus round | `reach_and_clear` |
| `life_count_checks` | life counts from 5 to 99, for example `["10", "20", "30"]` | `["10", "20", "30"]` |
| `starting_nodes` | 1-10 map nodes open at the start | 3 |
| `trap_chance` | 0-100: % of filler replaced by a trap | 0 |
| `trap_duration` | 5-120 seconds of play in a level per trap | 20 |
| `no_lives_trap_weight`, `upside_down_trap_weight`, `reverse_controls_trap_weight`, `button_swap_trap_weight` | 0-10: how often each trap is picked (all 0 = no traps) | 1 |
| `death_link` | `true` / `false` | `false` |

## Setup

What you need:

- [Archipelago](https://github.com/ArchipelagoMW/Archipelago/releases) 0.6.8 or newer.
- [BizHawk](https://tasvideos.org/BizHawk/ReleaseHistory) 2.9.1 or newer, with the PSX core set to **Nymashock**.
- `crash1.apworld` from the [releases page](https://github.com/caioaletroca/C1AP/releases).
- Your own NTSC-U disc image of Crash Bandicoot (SCUS-94900) and a PS1 BIOS. These are not provided.

Steps:

1. Double-click `crash1.apworld` to install it, or copy it into `Archipelago/custom_worlds`.
2. Make a YAML with the Archipelago Launcher's *Options Creator*, picking "Crash Bandicoot".
3. After the game is generated and hosted, start a **new game** in BizHawk.
4. Open **BizHawk Client** from the Archipelago Launcher.
5. In BizHawk, open `Tools > Lua Console` and run `data/lua/connector_bizhawk_generic.lua` from your Archipelago
   folder.
6. Connect the client to the server and enter your slot name.

The full guides are the [setup guide](crash1/docs/setup_en.md) and the
[game page](crash1/docs/en_Crash%20Bandicoot.md).

## Known issues

- Only the NTSC-U version (SCUS-94900) is supported.
- Death Link only sends deaths. Receiving a death (killing Crash) is not supported yet.
- Shuffled levels show the vanilla level's name on the loading screen for a couple of seconds.
- Gems belong to map nodes, not levels. The end screen shows the gem of the node you entered from (usually a clear
  gem). The check still counts for the level you played, and colored gems only appear once you receive the item.
- A received gem path appears the next time you enter that level, because the game only reads gems when a level
  loads.
- Avoid loading save states in the middle of a level. The client only knows what it saw happen, so a save state
  can skip or confuse checks:
  - Box checks follow the game's box counter, which a save state replaces with its own count from when it was saved.
  - A bonus round only counts if the client saw you in its level first. Enter the level, then load the state.
  - The box total in the `[C1AP verify]` log is wrong after a save state, so leave it out of bug reports.
  - Save states on the map, or at the start of a level, are fine.
- Box totals come from the game's own level-end table. The Lost City counts 26 boxes, although the wikis list 31.
  The client logs the count each time a level is won (`[C1AP verify]` lines); please include those lines in bug
  reports.

## Development

You need an Archipelago 0.6.8+ source checkout (Python 3.11-3.13).

```sh
# link the world into the Archipelago checkout
ln -s /path/to/C1AP/crash1 /path/to/Archipelago/worlds/crash1          # Linux/macOS
mklink /J C:\path\to\Archipelago\worlds\crash1 C:\path\to\C1AP\crash1  # Windows

# from the Archipelago checkout
AP_TEST_WORLDS=crash1 python -m pytest worlds/crash1/test test/general
```

| Path | What |
|---|---|
| `crash1/data.py` | Levels, gems, keys (static game data) |
| `crash1/world.py` | The Archipelago world: regions, items, rules, slot data |
| `crash1/shuffle.py` | Level-order shuffle |
| `crash1/ram.py` | RAM map (addresses marked `VERIFY` are unconfirmed) |
| `crash1/watcher.py` | Client game logic, pure and unit-tested |
| `crash1/filler.py` | Which filler to apply next and how (globals on the map, the Crash object in a level) |
| `crash1/client.py` | BizHawk I/O |
| `tools/` | BizHawk Lua scripts used to verify the RAM map, and the results log |
| `docs/DESIGN.md` | Design notes |

No game data (disc images, BIOS, saves) belongs in this repository.

## AI usage

This project was built with heavy use of AI. Most of the code, tests and documentation were written by
[Claude Code](https://claude.com/claude-code), an AI coding assistant, working under my direction. That includes the
world, the BizHawk client, the RAM research from the decompilation, and the Lua test scripts. Commits it co-wrote are
marked `Co-Authored-By: Claude`.

My part was the design decisions and testing. I played every feature in BizHawk, confirmed the RAM addresses against
the real game (the results are in [tools/VERIFY.md](tools/VERIFY.md)), and reported the bugs those tests found until
they were fixed. Nothing in the client was marked as working before it was seen working in the emulator.

## Credits

- RAM and level data: the Crash 1 decompilations ([esplonky/c1](https://github.com/esplonky/c1),
  [khasinski/crash-bandicoot-decomp](https://github.com/khasinski/crash-bandicoot-decomp)) and GOOL dumps
  ([ManDude/goocdump](https://github.com/ManDude/goocdump)).
- Box totals: the game's level-end table (goocdump `GamOC`), checked against the
  [Crash Bandicoot Wiki](https://crashbandicoot.fandom.com/wiki/Crash_Bandicoot_(game)) and the
  [RetroAchievements guide](https://github.com/RetroAchievements/guides/wiki/Crash-Bandicoot). Bonus rounds per level:
  the Crash Bandicoot Wiki.
- Built on Archipelago's BizHawk client framework.

## License

MIT. Crash Bandicoot is a trademark of its owners. This project is not affiliated with them.
