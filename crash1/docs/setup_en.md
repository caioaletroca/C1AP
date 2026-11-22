# Crash Bandicoot (PS1) Setup Guide

## Required software

- [Archipelago](https://github.com/ArchipelagoMW/Archipelago/releases) 0.6.8 or newer.
- [BizHawk](https://tasvideos.org/BizHawk/ReleaseHistory) 2.9.1 or newer (2.10 recommended), Windows prerequisites
  installed.
- `crash1.apworld` from the [C1AP releases](https://github.com/caioaletroca/C1AP/releases).
- Your own NTSC-U disc image of Crash Bandicoot (SCUS-94900) and a PS1 BIOS. These are not provided.

## Installation

1. Double-click `crash1.apworld` (or copy it to `Archipelago/custom_worlds`).
2. In BizHawk, set the PSX core to **Nymashock** (`Config > Preferred Cores > PSX`).

## Create a YAML

Use the Archipelago Launcher's *Options Creator* or *Generate Template Options*, and pick
"Crash Bandicoot".

## Playing

1. Start a **new game** (save files from vanilla play will confuse the client).
2. Open the Archipelago Launcher and click **BizHawk Client**.
3. In BizHawk, open `Tools > Lua Console` and run `data/lua/connector_bizhawk_generic.lua` from your
   Archipelago folder.
4. In the client, connect to the server (`/connect address:port`) and enter your slot name.

Keep the client running while you play: it handles map progress, gems, keys and level shuffle live.
Items resync from the server every poll. Avoid loading save states in the middle of a level: a state with
different gems can look like a new gem to the client.
