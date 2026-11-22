# Crash Bandicoot

## What does randomization do to this game?

- **Map progress** is an item. You start with a few map nodes open; every *Map Progress* item opens the next one.
- **Level shuffle** (on by default) changes which level each map node leads to. Dr. N. Cortex always stays at the
  end, two bosses are never next to each other, and no boss sits on a node that is open from the start.
- **Colored gems** (Green, Orange, Blue, Red, Purple, Yellow) are items. Their gem paths only appear once you
  receive them, wherever they were found.
- **Keys** to *Whole Hog* and *Fumbling in the Dark* are items.
- Leftover slots are filled with extra lives, Aku Aku masks and Wumpa fruit.

## What is the goal?

Defeat Dr. N. Cortex (`cortex`), or defeat him while holding all 26 gems (`all_gems`).

## What are the locations?

- Finishing each level and defeating each boss.
- Each level's gem (20 clear, 6 colored), when *Gem Checks* is on.
- Each of the two keys (the Cortex bonus rounds in Jaws of Darkness and Sunset Vista).

## What does another world's item look like in Crash Bandicoot?

The game shows nothing special. The item is sent as soon as the client sees the check.

## When the player receives an item, what happens?

Colored gems and keys appear in your inventory right away; a gem path shows up the next time you enter the
level (the game only checks gems when a level loads). Map progress takes effect the next time you are on
the map. Filler (lives, masks, fruit) is applied the next time you are playing a level.

## Known limitations (v0.1)

- NTSC-U (SCUS-94900) only.
- Death Link only sends deaths; received deaths are not applied yet.
- The game itself does not show which shuffled level a node leads to until you enter it.
