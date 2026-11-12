# Notes of worker x2 (EXODUS ITEMS, MAGIC, SHRINE)

## Corrections to docs/MAP.md and the core names

- ITEMS: 5BCF is **Fire** (the frigate's cannons: needs PartyTile 0Bh, "Direct-", three
  cells of range, "<name>s Destroyed!"), not Get Chest (G is 8190). 5CC3 is K and D on the
  surface (prompt, then "What?"). The module also holds the spell tables and most strings of
  MAGIC and SHRINE.
- MAGIC: the table at 594B is the **wizard** list, 596B the **cleric** list; they cover all 32
  spells with 26 handlers (Luminae = Lorum, Rec Su = Sur Acron, Rec Du = Dor Acron, Sominae =
  Dag Lorum, Excuun = Decorp, Zxkuqyb = the nameless wizard spell P). NameTbl 103 is "".
- WORLD 2168 is the **whirlpool** (PartyTile 0Ch, then Ambrosia); the moon gate step is ITEMS
  5B51 (map byte 88h: PlayerXY = GateXTbl/GateYTbl[Moon2Phase]). L1320/L1321 (core names
  GateState/GatePos) look like the **whirlpool's x, y** (PARTY 7347 moves the word at 1320 by
  1322/1323 every 4th turn, a frigate it meets is "Destroyed!"); worth a check by WORLD/PARTY.
- MonMove (L12A0) is used as **the map byte under the creature**: Fire and Bribe put it back
  into the map when they remove a creature.
- L16E1 is a table of (x, y) entrances in MapFileNames order: 16E1 BRITISH (2D,12), 16E3
  EXODUS (0A,35). InExodusCastle compares only PartyXY's x with 16E3.

## Things FORMATS.md does not say

- Location: 2 town, 3 castle, 4 during a shrine, 80h a fight (the old value is kept in
  SavedLocation 58CB and restored after it).
- Counters in SHRINE's data: 64A0 cards inserted (word; 4 = the end), 64A2 upkeep tick (the
  per-turn upkeep runs every turn on the surface, every 4th elsewhere), 64A3 hit point regen
  (1 HP every 10th upkeep), 64A4 whirlpool tick (moves every 4th turn).
- Fight data in the start-up area: StartUp+80h/+88h/+98h = 8 monsters' x, y, hit points;
  +0A0h/+0A4h = the fighters' x, y; L84E1 fighter slot, L84E2 monster shape, L84E3 the
  Repond/Pontori "tried" flag.
- Spell cost = 5 x the letter's index (A 0 ... P 75 MP). Classes: C, P, I cleric; W, L, A
  wizard; D, R choose; F, T, B "Not a mage!". Light: torch 255 moves, Lorum 10, Dag Lorum 250.
- Spells (handler effects): Repond/Pontori kill all orcs/skeletons (shape 18h/19h), once a
  fight, 1 in 2; the "all monsters" spells hit each monster 3 in 4; Mittar 16-55 (random 0-39
  OR 10h), Fulgar 75, Mentar 2 x Int, Decorp kill (directed); Noxum 75, Dag Mentar 2 x Int,
  Zxkuqyb kill (all); Necorp sets every monster's HP to 5; Sanctu heals 10-29, Sanctu Mani
  20-99; Appar Unem opens a chest 3 in 4 (a surface chest's low 2 bits are the ground under
  it); Vieda = the Peer-at-gem view; Surmandum 3 in 4 resurrect, else ashes; Anju Sermani
  costs the caster 5 Wis.
- DexRoll (5B85): chance (Dex + bonus)/255, bonus 128 thief, 64 barbarian/illusionist/ranger.
- Shrines: stat = party x & 3 (Str, Dex, Int, Wis); offering in hundreds from the gold's high
  byte; stat += offering up to RaceStatMax (58D2: Human 75s, Elf Dex 99 Wis 50, Dwarf Str 99
  Int 50, Bobbit Dex 50 Wis 99, Fuzzy Str 25 Dex/Int 99); the overpaid gold is lost.

## Bugs and oddities

- Dag Acron (6034) passes the map byte (shape x 4) to CheckTerrain (PARTY 7254), which wants
  a shape number: on foot it seems to accept only brush (08h) (unverified).
- Alcort refunds 35 MP when no player is chosen: to the caster after Esc/0, but to an empty
  slot's record if one is picked (AskPlayer sets BX first). No cap.
- Fal Divi charges the cleric spell's MP on top of its own. Directed spells: Esc after
  "Direct?" keeps the MP spent. Surmandum's ashes case prints "Failed!". Anju Sermani's Wis
  - 5 is not checked for underflow. Appar Unem with no chest prints "Not Here!" and "Failed!".
- CmdJoinGold clears the gold of all four slots, whatever PartySize.
- Dead data: 58B4 (12 zero bytes), 6493 (13 zero bytes), the word "SCORE" after "PRAY" (not
  in OtherWords).
- ExitToSosaria does not clear LightOn (DUNMOVE 8314 does on its own path).

## Open questions

- PrintAt's DX (row/column?) and whether "LVL:0" + digit shows "LVL:01".
- The 11h after each facing name ("North",11h). Random's exact range (DL = 0..DH-1 assumed).
- L8F5A (COMBAT): assumed "damage monster BX by AX, DI = attacker".
