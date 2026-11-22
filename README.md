# Crash Bandicoot (PS1) for Archipelago

An [Archipelago](https://archipelago.gg) world (apworld) and BizHawk client for **Crash Bandicoot** (PS1, 1996),
NTSC-U version (SCUS-94900).

Archipelago is a multi-game randomizer: the items of every game in a session are shuffled across all the players'
worlds. In Crash Bandicoot, finishing levels and collecting gems sends items to other players (or to yourself), and
the map, the colored gems and the secret keys come back to you as items.

> **Status: alpha (0.1.0).** Every client feature has been tested live in BizHawk (see
> [tools/VERIFY.md](tools/VERIFY.md)). Expect rough edges, and please report them in the
> [issues](https://github.com/caioaletroca/C1AP/issues).

## What is randomized?

- **Map progress.** A few map nodes are open at the start. Each *Map Progress* item opens the next node.
- **Level shuffle** (optional). This changes which level each map node leads to. Dr. N. Cortex always stays last,
  two bosses are never next to each other, and no boss sits on a node that is open from the start.
- **Colored gems.** Green, Orange, Blue, Red, Purple and Yellow are items. Their gem paths appear once you
  receive them.
- **Keys.** The keys to *Whole Hog* and *Fumbling in the Dark* are items.
- **Filler.** Extra lives, Aku Aku masks and Wumpa fruit.

The locations are finishing each level, defeating each boss, each level's gem (optional) and the two keys.

## Goal

Defeat Dr. N. Cortex (`cortex`), or defeat him while holding all 26 gems (`all_gems`).

## Options

| Option | Values | Default |
|---|---|---|
| `goal` | `cortex`, `all_gems` | `cortex` |
| `level_shuffle` | `true` / `false` | `true` |
| `gem_checks` | `true` / `false`: gems are locations | `true` |
| `starting_nodes` | 1-10 map nodes open at the start | 3 |
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
- Death Link does not work reliably yet. The game's death counter misses deaths, so the real lives counter still
  needs to be found.
- Shuffled levels show the vanilla level's name on the loading screen for a couple of seconds.
- Gems belong to map nodes, not levels. The end screen shows the gem of the node you entered from (usually a clear
  gem). The check still counts for the level you played, and colored gems only appear once you receive the item.
- A received gem path appears the next time you enter that level, because the game only reads gems when a level
  loads.
- Avoid loading save states in the middle of a level.

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
| `crash1/client.py` | BizHawk I/O |
| `tools/` | BizHawk Lua scripts used to verify the RAM map, and the results log |
| `docs/DESIGN.md` | Design notes |

No game data (disc images, BIOS, saves) belongs in this repository.

## Credits

- RAM and level data: the Crash 1 decompilation ([esplonky/c1](https://github.com/esplonky/c1)) and GOOL dumps.
- Built on Archipelago's BizHawk client framework.

## License

MIT. Crash Bandicoot is a trademark of its owners. This project is not affiliated with them.
