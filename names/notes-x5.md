# Notes of worker x5 (EXODUS TOWNS, ENDING, TEXT, EXDATA)

Maps: `names/towns.map`, `ending.map`, `text.map`, `exdata.map` (applied), `names/proposed-x5.map`
(175 symbols used by other modules, plus two corrections of established names).

## Corrections to docs/FORMATS.md

- **1320-1323 are the whirlpool, not the moon gate** (FORMATS 3). PARTY 7347-7403 moves it every
  4th call by (1322, 1323) (from the tables L7337/L733F) while the cell ahead is water, turns a
  frigate it meets (2Ch) into whirlpool (30h), and takes the party when it reaches PlayerXY;
  WORLD 21A4 then puts it at (3, 7-3Dh). SOSARIA.ULT starts it at (5, 3Ah). Proposed:
  GateState -> WhirlpoolX, GatePos -> WhirlpoolY, L1322 WhirlpoolDX, L1323 WhirlpoolDY.
- **Combat file tail** (FORMATS 5): A8-AB is the tile under each player (saved when he is put on
  the map, restored when he moves: COMBAT 8A19, 8C78); AC-AF is each player's own tile, from his
  class (COMBAT 8A0F via L862F). 90-97 is likewise the tile under each monster (restored when it
  dies, 8F80), 98-9F the monsters' hit points (damage subtracted, 0 = dead). The values in the
  files are overwritten at the start of a fight.
- **14C8-14CB** (FORMATS 6): the shops use only 14CA (weapons) and 14CB (armours). They are set to
  0FFh when the price list is shown in Dawn, and only then do the menus offer the +2/+4 goods
  (weapon keys B-H or B-O: 10 or 17 keys with the Q/Esc/0 entries; armour B-E or B-G: 7 or 9).
  "FF = not yet found" is so far right for these two; 14C8/14C9 are someone else's (Ready?).
- **Dawn**: the shops test `PartyXY.x == 25h`: the saved surface position, i.e. the town entered
  is Dawn (MapPosTbl entry 8 = (25h, 35h)). Dawn's map cell is MapBuf+0D65 (L0E65, proposed
  DawnCell): WORLD 211E writes Towne (18h) there when both moons are in phase 7 and Forest (0Ch)
  when both are 0.

## Game mechanics the code shows

- Pub: you name the amount (2 digits). Under 7: thrown out. The tip is PubTips[tens digit]:
  7-9 gp gives only "Thank you, kindly!", 10-19 the Ambrosia tip, ... 90-99 "Seek ye out the
  Lord of Time". Paying exactly all your gold counts as "Can't pay".
- Radrion (Prophet of Life): the verse is OracleVerses[hundreds offered, as BCD]; 0 hundred is
  free and gives verse 0. **Bug**: an offer of 10 or more hundreds indexes past the 10-entry
  table (it reads pointers out of the Equine Emporium strings at A1C4...).
- Temple: Heal sets hit points = maximum without looking at the status (a dead player is
  "healed" and charged) and refuses only when hit points exceed the maximum, so a healthy player
  is charged 200 too. Resurrect only sets the status to G (hit points stay). Curing a dead or
  ashen player says "Failed!" without charge.
- Weapons/armour: selling pays the **full** buy price (same tables), and selling any weapon
  unreadies the current one (Hand), any armour unwears it (Skin). Counts stop at 99, gold at 9999.
- Guild: price = rate x count in binary (ReadNumber's AH), turned into BCD; counts stop at 99.
- Horses: PartySize horses for PartySize x 200 gp; PartyTile becomes 0Ah. EQUIP 8018 also calls
  the horse sale (from talking to a merchant?).
- Surface turn (ReadCommand, 1B77): with no key for about 5 seconds (DOS time) the game passes.
  The whirlpool routine is called in that wait loop and moves it every 4th pass, so its speed
  probably depends on the CPU.
- On a horse or ship, moving with the arrow keys toggles RideToggle (15D1): the creatures move
  only every other step (WORLD 226C-228A).
- New surface creatures (WORLD 22D2): SpawnTiles[rnd(13) AND rnd(13)], which makes orcs and
  thieves common and dragons/balrons rare. SpawnMoves gives 0 to the sea creatures (Serpent,
  Man-O-War, Pirate) and 4 to the rest: a hint for FORMATS 3's open movement code.
- EndGame: after the final text it waits for a key and jumps to PARTY L7252 (`jmp $`): the
  program hangs. It sets Location = 1 just before (why is open).

## Dead code and data, oddities

- "Oh well, maybe next time." (TEXT 9C96, inside L9C6A's db) is never pointed at.
- XorMapWindow (ENDING A491) duplicates PARTY L71C1 except that the pattern comes in AX.
- Duplicate strings: "Failed!" (EXDATA 1A05, TEXT 9BCC), North/South/East/West (EXDATA 1B4D...,
  and ITEMS' MsgNorth...). Hence the names MsgStealFailed, MsgTempleFailed, MsgMoveNorth ....
- PayGold's borrow branch (A5A6, gold = 0) cannot run: the binary compare before it already
  orders BCD words correctly.
- The weapon/armour key lists contain a 0 entry that can never match (K2AD8 rejects character 0);
  it pads the menus to the pointer tables in ACTIONS (L7904, L7932).
- L0080 (CmbMonX) is also used by LOOP 1F96 as a plain displacement 80h: `L0080[bx]` with BX
  in MonTile addresses MonTalk. The integrator might prefer `MonTile+80h`-style there (code
  untouched by me).

## Open questions

- ShopTemple's sound 0FDh with BL = 0C0h, BH = 80h: the library's Sound parameters (pitch,
  length?). PARTY L7176/L71C1 around it seem to flash a status line and the map window.
- EndGame's call to PARTY L6B91 and the `Location = 1` before hanging.
