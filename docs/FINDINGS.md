# What the code revealed

Collected in phase 6 from the naming workers' notes (`names/notes-*.md` keep the full detail and
the reasoning). Module and routine names are those of `src/`; addresses are the original's.
"Unverified" marks what was read from the code but not seen in play.

## The copy protection and how it was removed

- The library's disk check reads track 9, head 0, sectors 16 down to 1 (int 13h, 4 tries each)
  into C000:0000 on drive A: or B:; only a specially formatted track 9 passes. In all three
  programs its first three bytes are overwritten by `mov al, 0 / ret` (`DiskCheckStub`; EXODUS's
  copy says `mov al, 0FFh`, but EXODUS never calls it). The code after the patch still pops
  registers it no longer pushes: it is a patch of the original routine, not a separate stub.
- ULTIMA calls the stub at start-up (`DiskCheckResult`): 0 lets the intro run; 0FFh would hang it.
- BOOTUP's scenario-disk prompt is disabled by one byte: `AskScenarioDisk` (1DC6) is a `ret`
  written over the first byte of `mov dh, 17h`. The dead rest would print "<Insert Scenario Disk>",
  run the disk check and offer drives 1-4/A-D, so "(Strange Disk)" can never appear.
- Whether Origin or GOG made these patches needs an original disk image.

## The world

- **Moons and gates** (WORLD `AdvanceMoons`): moon 1 changes phase every 12 steps, moon 2 every 4;
  the gate on the map is moon 1's, it moves only when moon 2 changes, and it takes the party to
  moon 2's gate. **Dawn** appears at (37, 53) when both moons were in phase 7 and turns back to
  forest when both were 0; only its shops sell the +2/+4 goods. The moons advance one step every
  time EXODUS starts.
- **Whirlpool** (PARTY `MoveWhirlpool`, WORLD `Whirlpool`): it moves every 4th turn over water,
  turns a frigate it meets into a whirlpool, and swallows the party: Sosaria to Ambrosia (the party
  wakes on foot at (32, 54)) and back. Its speed depends on the CPU: it is moved inside the
  key-wait loop.
- **Creatures**: spawn only on Sosaria, 7 times in 135 a turn, kind `rnd(13) AND rnd(13)` (orcs and
  thieves common, dragons and balrons rare), never in the party's row or column. On a horse or
  frigate they move every other step. Dragons and pirates fire up to 3 cells, stopped by mountains,
  walls and void. Town creatures move by their talk code's top bits (stand, wander, approach,
  hostile).
- **Line of sight** (VIEW `BuildView`): forest, mountains, walls and void hide what is behind.
- **Terrain** (PARTY `CheckTerrain`): a force field stops the party unless all members have the
  Mark of Force, and hurts only the first member without it (99, even a dead or ashen one); lava
  hurts each living member without the Mark of Fire (50) but lets the party pass; a frigate cannot
  sail in a calm or into the wind. The wind changes every 25 keyboard polls (1 in 9 calm).
- **Exodus's castle** (ITEMS `InExodusCastle`): fire strikes a random cell each turn, Negate Time is
  cancelled, only the Exotic weapon hits and only Exotic armour protects.
- **Secrets**: Dig gives the Exotic weapon at (21h, 03h) and the Exotic armour at (13h, 2Ch) on
  Sosaria; Pray at (30h, 30h) in the towne entered from x 22h; Yell "Evocare" at x 0Ah, y 38h/3Bh
  with the Mark of the Snake; Insert the cards at x 1Eh-21h in the order L, S, M, D. Bribe costs 100
  gold, guards only. Steal needs a counter with a chest behind it; a failure alarms the guards one
  time in four.
- Quit & Save saves and play goes on; it works only on Sosaria.

## The party

- Level = experience / 100 + 1. Lord British adds 100 maximum hit points when experience/100 >=
  max/100, up to 2500; from 500 the Mark of Kings is needed.
- Every turn on the surface (every 4th elsewhere, PARTY `PartyUpkeep`): magic points come back by
  class (Wizard to Int, Cleric to Wis, Lark/Druid/Alchemist to Int/2, Paladin/Illusionist/Druid to
  Wis/2, Ranger to min(Int/2, Wis/2), none for Fighter, Thief, Barbarian), 0.10 food is eaten,
  poison costs 1 hit point, every 10th turn heals 1; starving costs 5.
- Spells cost 5 x the letter's index. Cleric spells for C, P, I; wizard for W, L, A; D and R
  choose; F, T, B are "Not a mage!". Light: a torch 255 dungeon turns, Lorum 10, Dag Lorum 250.
- `DexRoll`: chance (Dex + bonus) / 255, the bonus 128 for thieves, 64 for barbarians,
  illusionists and rangers. Shrines raise the stat of x & 3 by the hundreds offered, up to the
  race's cap; gold paid beyond it is lost.

## Fights

- The combat map and number of foes: docs/FORMATS.md 5. Foe hit points `Random(FoeHitPoints[kind])
  | 0Fh`. A player hits half the time for sure, else when `Random(99) < Dex`; damage weapon x 3 + 4
  + Random(Str) + StrBCD/2. A foe hits when `Random(armour + 16) < 8`; its damage grows with the
  victim's maximum hit points and with the location (castles and Ambrosia hurt most).
- Casters' magic only strikes a player whose status is Good: a poisoned player is immune.
  Man-O-War, Balron and Pincher poison; thieves pilfer an item even when their blow misses.
  Missiles pass through walls and players; a dagger with no foe next to it is thrown and lost.
- Dungeon encounters: chance (level+2)/(level+130) a turn; a wandering monster leaves a chest.

## Towns

- Pub: the tip is `PubTips[tens digit of the gold paid]` (under 7: thrown out). Temple Heal charges
  players already at full health and "heals" dead ones; Resurrect leaves hit points as they were.
  Shops refund the full price, and selling any weapon or armour unreadies or unwears the current
  one. The service at a counter is chosen by the player's y & 7, a counter to the west is always the
  horse seller.
- After the final screen the game hangs on purpose (`EndGame`).

## Bugs

- **Chest traps** (DUNMOVE `CmdGetChest`): the trap is chosen by comparing AL instead of DL, so
  poison and gas traps come about 1 in 256; acid 9/16; AL = 0 on the acid path is a silent evade.
- **Attack damage** adds the BCD strength byte / 2, not the number.
- **"Unable to read/write file"** never shows the file name (OpenFile has overwritten SI with the
  15-space message), then hangs. A missing file gives "Wrong Diskette!".
- **Radrion's shrine**: an offer of 10 or more hundreds reads past the 10-entry verse table.
- **Spells**: Fal Divi charges magic points twice; Alcort refunds 35 MP to an empty slot if one is
  picked, with no cap; Anju Sermani's Wis - 5 can underflow; Dag Acron passes a map byte where a
  shape number is wanted (on foot it seems to accept only brush; unverified).
- **Join gold** clears the gold of all four slots, whatever the party size.
- **Form the Party** tests the old records for a living member before copying the new ones, so a
  party of dead characters can be formed and is then refused by Journey Onward. A rejected roster
  number is stored in `PartyRosterNums` before it is checked and stays there (at index PartySize).
- The shared error exits jump to MainLoop without resetting SP; HandEquip's "A" path leaks 18
  bytes of stack each time (overflow not checked).
- `MoveWhirlpool` calls `int 15h` with AH = 2Ch where `int 21h` (get time) is meant.
- Lord British may step to an uninitialised DX in a fight (unverified). An invalid key in combat
  spends the turn. BOOTUP's status key string is "GPDP", a typo for "GPDA" (harmless).
- Random with DH = 0 would hang; DUNGEON.DAT's line routines would loop 65536 times on zero-length
  lines (no table entry asks for one).

Found while writing the C reading (`c/`, where each is marked `BUG, as in the original`); read from
the code, unverified in play:

- **Temple healing** (TOWNS `TempleHeal`) never looks at the status letter: a dead or ashen
  character gets maximum hit points (and stays dead or ashes) for 200 g.p. Only hit points above
  the maximum count as "Not injured!", so a character at full hit points is charged too.
- **Food running out** (PARTY `SpendFood`): when the BCD food word goes below zero it is set to 0,
  but the hundredths byte keeps the wrapped result of the subtraction.
- **PrintName** (PARTY) with AL = 0 prints NameTbl entry 0FFh, past the 136 entries (its header's
  "entry -1" is not what the code does).
- **Directed spells** (MAGIC `CastDirected`) lose the spell index: AskDirection returns the step in
  DX, so `SpellFlash`'s pitch is the step's x and depends on the direction, not the spell.
- **Steal** (LOOP `CmdSteal`): on a failed theft, one time in four, every guard (shape 18) in the
  32 creature slots turns hostile, wherever the party is.
- **The title's demo** (BOOTUP `TitleLoop`): a pause of 0 rounds counts down from 0 to 0FFh and
  lasts 256 rounds (`dec ah / jne`).

## Dead code and data

- The disk check in all three programs, BOOTUP's `AskScenarioDisk` rest, VIEW 26DF (an older
  new-line routine), a stray `ret` at 6BF9, unused zero runs (58B4, 6493, 76E6, 84DB, 24B3), the
  word "SCORE" after "PRAY", "Oh well, maybe next time." and "No One There" (never pointed at),
  PayGold's unreachable borrow branch, ULTIMA's animation shifts 1 and 3, ladder table bytes +6/+7
  in DUNGEON.DAT. `ReadKey` calls an empty hook (`IdleNop`) every 80 polls.

## Speed

Animation, the wind and the whirlpool run at keyboard-polling speed (and several sounds and the
intro use delay loops): on a faster CPU they all run faster. A port must pace them.
