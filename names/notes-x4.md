# Notes of worker x4 (DUNMOVE, DUNEVENT, COMBAT, CMDTAB)

## Corrections to the docs

- **MAP.md**: Get Chest is DUNMOVE 8190 (surface table 1943, dungeon table 774E), not ITEMS 5BCF;
  5BCF is the Fire (cannon) command. DUNMOVE also holds the dungeon's own loop: 8314 enter,
  8327 the key loop, 838D the end of every dungeon turn (MainLoop jumps there while Location = 1).
- **FORMATS.md 3**: the creature "movement code" (MonMove, 12A0) is the **map byte under the
  creature**: WORLD 2477-248D puts it back and takes the new one when a creature moves, and
  CmdAttack turns it into the chest left behind. That is why the values are 00, 04, 08, 0C, 20
  (water, grass, brush, forest, floor).
- **FORMATS.md 4, dungeon cells** (DUNMOVE 838D, 83F7-84D8, DUNEVENT):
  - only cells exactly 01-08 are events: 1 time vision (TIME.IMG), 2 fountain, 3 strange wind
    (torch out), 4 trap, 5 the rod (BRAND.IMG, a mark), 6 gremlins, 7 nothing, 8 misty writing
    (the level's message). 1, 4, 6 and 8 clear their cell; 2, 3, 5 stay.
  - 40h is a **chest** (Get Chest in a dungeon wants exactly 40h); a wandering monster's cell is
    set to 40h before the fight, so it leaves a chest.
  - 10h up, 20h down (Descend also refuses bit 7); 80h wall: Advance is stopped only by exactly
    80h, so A0h/C0h can be walked into; Retreat is stopped by any bit-7 cell; turning is refused
    while standing in a cell >= A0h. So A0h/C0h behave like doors entered from the front.
- **FORMATS.md 5, combat file tail**: +90h-97h is the **tile under each foe** (saved when it is
  placed or moves, put back when it moves or dies), +98h-9Fh the **foes' hit points** (0 dead),
  +A8h-ABh the **tile under each player**, +ACh-AFh the **player's tile** (from his class). The
  file values there are overwritten. The 7 bytes at +79h are not read by COMBAT.
- **FORMATS.md 6**: LightOn (15CE) is a **counter**, not a flag: Ignite sets 0FFh and every
  dungeon turn takes one, so a torch lasts 255 turns; the strange wind sets it to 0.
- **FORMATS.md 6**: Location 04 = a picture (TIME/FOUNTAIN/BRAND .IMG) is on show; 80h = in a
  fight (the old value is kept at 58CB). FileConflict (8538) is CNFLCT_G: nothing patches a
  letter; StartCombat picks one of nine name pointers.

## Game mechanics found

- Combat map: dungeon C; pirates S (from a frigate) or A; from a frigate Q (sea foe) or R; a sea
  foe from land M; else the party's tile: grass G, brush B, forest F, floor/force field/lava C.
- Number of foes: 8 in Exodus's castle, 8 Guards, 1 in other towns/castles, else 1-8.
- Foe hit points Random(FoeHitPoints[kind & 0Fh]) | 0Fh. Player hit: 50% sure, else
  Random(99) < dexterity; damage weapon*3 + 4 + Random(str) + strBCD/2. Foe hit: Random(armour +
  16) < 8; damage Random(FoeHitPoints/8 + high byte of the victim's max HP) + 1 + 10 * (old
  Location & 3), so it grows with the victim's max hit points and is worst in castles/Ambrosia.
- In Exodus's castle (ITEMS 5B28) only the Exotic weapon hits, non-Exotic armour never stops a
  blow, and Negate Time is cancelled each turn.
- Casters' magic (Serpent, Man-O-War, Wizard, Daemon, Dragon, Balron, 1 in 3) only strikes a
  player whose status is Good: a poisoned player is immune. Man-O-War, Balron, Pincher poison;
  Thieves pilfer a weapon or armour (not the readied/worn one), even when their blow misses.
- Missiles (bows, slings, thrown daggers, ShootLine; a dragon's fire) pass through walls and
  players. A dagger with no adjacent foe is thrown and used up.
- Monster names: on an odd y, Thief..Balron use the 16 monster names (Brigand ... Devil), two per
  kind chosen by x & 1.
- Dungeon encounters: chance (level+2)/(level+130) per turn on a floor cell; Orc + Random(level+2)
  capped at Balron.
- Gremlins eat 100 food (the high byte of the food word); the rod's mark bit is 4 + (x & 3).
- An invalid key in combat goes through MsgWhat -> MainLoop -> PlayerTurnEnd: the turn is spent;
  CCmdBad (the listed but unusable keys) does not spend it. The Volume key spends it too.

## Bugs / oddities

- Get Chest trap choice compares the whole random byte AL with 1 and 2 instead of DL: poison and
  gas traps come ~1/256 each, acid 9/16, bomb the rest. AL = 0 on the acid path is a silent evade.
- AttackHit adds the BCD strength byte / 2 to the damage, not the number.
- FoesTurn: Lord British (1 in 3) calls FoeStep without checking that a step was found; DX is
  then whatever was on the stack ([bp+4] of FoeChooseMove). Possibly a wild jump. Unverified.
- The plural skip list in PrintFoeName (2, 9, 14h, 87h = names Grass, Floor, Lord British,
  Orcus) has two odd entries; probably meant other names.
- The magic target is a random player 0-3, not 0..PartySize-1 (empty slots just make it move).

## Open questions

- Sound FD (warble) parameters BL/BH: pitch and length? (fanfares, 8DD3 pitch by player).
- L259D (WORLD) is used as "the tile under the party"; who sets it was not checked.
- CmdTab_Unused (84DB, 5 zero bytes) is never referenced.
- L84E1 and the library's X0103 are the same byte; proposed CombatPlr here, CombatPlayer in
  proposed-lib.map: the integrator may want one name.
