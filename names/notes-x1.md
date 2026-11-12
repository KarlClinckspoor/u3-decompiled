# Notes of worker x1 (EXODUS LOOP, WORLD, VIEW)

## Corrections to docs

- **MAP.md, EXODUS WORLD**: 2168 is the **whirlpool**, not the moon gate teleport. A whirlpool
  (map byte 30h) takes the frigate from Sosaria to Ambrosia ("A huge swirling --WhirlPool--...",
  the party wakes on foot at (32, 54)), and in Ambrosia takes it back to the saved place in a
  frigate ("All is Dark!" / "You made it!"). The moon gate teleport is ITEMS 5B51 (destination
  by Moon2Phase).
- **MAP.md, EXODUS LOOP**: the key read and the table lookup are not in LOOP but at the end of
  EXDATA (1B77 BuildView, 1B7A prompt / key / timeout -> Space). `MainLoop` (1BD5) is the end of
  a turn that every command jumps to; it ends in WORLD 226C (creatures), which jumps to 1B7A.
- **FORMATS.md 3, 1320-1323**: `GateState`/`GatePos` (1320, 1321) are the **whirlpool's x and
  y**, and 1322-1323 its step (PARTY 736C-73DE moves it, 21A4 resets it to x 3, random y). The
  names in exodus-core.map should become WhirlX / WhirlY.
- **FORMATS.md 3, movement code (12A0, `MonMove`)**: it is the **map byte under the creature**:
  restored to the old cell when the creature moves (247A), read from the new cell (248D). For a
  spawned monster it is first its required ground (L1972: 04 grass, 00 water). That explains the
  town values 00, 04, 08, 0C, 20 (water, grass, brush, forest, floor). A better name: MonUnder.
- **FORMATS.md 3, talk code kind bits (1300 bits 7-6)**: how the creature moves in a town:
  0 stands, 1 wanders (half the time, never onto x or y 0), 2 approaches the party (never
  attacks), 3 hostile: chases and attacks (a fight when it steps onto the party). C0h is set for
  every spawned monster and, by Steal's alarm, for all guards (tile 48h).
- **FORMATS.md 6, header 0A-0D (14C4-14C7)**: Modify order (1EC5) exchanges these bytes with
  the records, so they belong to the party slots (probably the roster numbers).

## Game mechanics found

- Moons: moon 1 changes phase every 12 steps, moon 2 every 4; the gate moves only when moon 2
  changes. The town of **Dawn** (map cell 37, 53, entrance 8 = DAWN.ULT) appears when both old
  phases were 7 and turns back to forest when both were 0 (20AE).
- Spawning (22A5): Sosaria only (not Ambrosia), 7 in 135 per turn, kind = rnd(13) AND rnd(13)
  from L1965 (Orc, Thief, Skeleton, Fighter, Giant, Daemon, Serpent, Pincher, Wizard, Man-O-War,
  Pirate, Dragon, Balron: the first are the most common), never in the party's row or column.
- On a horse or frigate the creatures move only every other step (while moving with the arrows;
  L15D1 toggles, L15D2 = the last key word). Negate Time (TimeStop) freezes them.
- Dragons and pirates fire up to 3 cells at the party (232F), stopped by mountains/walls/void.
- BuildView hides every view cell whose path to the centre crosses forest, mountains, wall or
  void (shape 24h); in towns the outside of the map shows grass.
- Exodus's castle (L5B28): each turn fire strikes a random view cell (DamageParty on the
  party's cell) and Negate Time is cancelled.
- Steal: success needs a counter (shapes 37-57) with a chest (24h) right behind it; failure
  alarms the guards one time in four. Unlock works only east or west of the party (DH = 0).
- Quit & Save does not end the program; it saves and the game goes on. Q works only on Sosaria.
- Board in Ambrosia on a horse cell: "What?" and Negate Time is cancelled (odd side effect).
- Start-up advances the moons one step (it calls 20AE) at every program start.

## Dead code, small bugs

- VIEW 26DF (9 bytes, db): dead older new-line code (DX = 1718h, call SwapCursor, jmp back).
- WORLD 24B3: 13 zero bytes, unused.
- MonShoot 236B/2372: `ja` lets the bolt reach view coordinate 0Bh (one past the window).
- MonCanEnter 222A: a special case for creature tile 4 (grass) that seems unreachable.
- DrawFrame: the five horizontal lines of the right part draw 17 cells, the 17th lands on the
  left edge of the next scan line (harmless, the edge is drawn anyway).
- In Ambrosia (Location 0FFh >= 2) MainLoop sends a party at x 0 or y 0 to L6458 ("Exit to
  Sosaria") as if it were a town edge (?).

## Open

- L7233: a frigate is refused when WindDir is 0 (calm?) or equals the direction moved.
- L84E0 = 3Ch before casting outside a fight (COMBAT uses 3Dh): meaning open.
- Location 1 during ShowGemMap only to stop the library's idle animation (KeyReady skips K2987
  when X01BE = 1)? Likely.
