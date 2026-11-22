# C1AP: Crash Bandicoot (PS1) for Archipelago

An [Archipelago](https://archipelago.gg) world and BizHawk client for **Crash Bandicoot** (PS1, 1996, NTSC-U
SCUS-94900).

> **Status: pre-alpha.** The world generates and is tested. The client's RAM addresses come from the
> decompilation and still need in-emulator verification ([tools/VERIFY.md](tools/VERIFY.md)). It's not playable yet.

## Features

- Checks: finishing every level and boss, every gem (optional), both keys.
- Items: Map Progress (opens map nodes), the six colored gems, the two secret-level keys, clear gems, filler.
- Level shuffle with Cortex fixed last, no adjacent bosses, and no boss on a starting node.
- Goals: defeat Cortex, or defeat Cortex with all 26 gems.
- Universal Tracker support.

Player docs: [game page](crash1/docs/en_Crash%20Bandicoot.md) · [setup guide](crash1/docs/setup_en.md).
Design: [docs/DESIGN.md](docs/DESIGN.md).

## Development

Requires an Archipelago 0.6.8+ source checkout (Python 3.11–3.13).

```sh
# link the world into the Archipelago checkout
ln -s /path/to/C1AP/crash1 /path/to/Archipelago/worlds/crash1          # Linux/macOS
mklink /J C:\path\to\Archipelago\worlds\crash1 C:\path\to\C1AP\crash1  # Windows

# from the Archipelago checkout
AP_TEST_WORLDS=crash1 python -m pytest worlds/crash1/test test/general
```

Layout:

| Path | What |
|---|---|
| `crash1/data.py` | Levels, gems, keys (static game data) |
| `crash1/world.py` | The Archipelago world: regions, items, rules, slot data |
| `crash1/shuffle.py` | Level-order shuffle |
| `crash1/ram.py` | RAM map (addresses marked `VERIFY` are unconfirmed) |
| `crash1/watcher.py` | Client game logic, pure and unit-tested |
| `crash1/client.py` | BizHawk I/O |
| `tools/` | BizHawk Lua RAM watch and the verification checklist |

No game data (disc images, BIOS, saves) belongs in this repository.

## Credits

- RAM and level data: the Crash 1 decompilation ([esplonky/c1](https://github.com/esplonky/c1)) and GOOL dumps
  (goocdump).
- Built on Archipelago's BizHawk client framework.

## License

MIT. Crash Bandicoot is a trademark of its owners. This project is not affiliated with them.
