# Notes of worker x3 (EXODUS PARTY, ACTIONS, TRANSACT, EQUIP)

## Corrections to docs

- **TRANSACT.ASM is the H command (Hand Equipment)**, not Transact: LOOP 1E55 asks giver and
  receiver and calls 7B54 (menu F, G, E, W, A). The T command "Transact" is **7FC6** (EQUIP):
  talking to creatures, Lord British's levels, and buying at shop counters. MAP.md's module
  line and FORMATS-style descriptions saying "Transact and its menus" should say Hand Equipment.
- **FORMATS.md 6, byte 0E**: the card bits are 3 Death, 2 Moons, 1 Sol, 0 Love (not "Death,
  Sol, Love, Moons"). Ztats prints bits 7..0 as Kings, Snake, Fire, Force, Death, Moons, Sol,
  Love (table 6DB1); Insert wants bit n with the key "LSMD"[n]; Search gives 1 << (x & 3).
- **FORMATS.md 6, 29-2F and 31-3F**: the counts are for armours 1-7 (Cloth ... Exotic) and
  weapons 1-15 (Dagger ... Exotic); index 0 (Skin, Hand) is never counted. Exotic is counted
  too (Dig adds one at 2F/3F), not only flagged.
- **Header flags 14C8-14CB**: 0FFh means *found* (the menus get all entries), set by Other DIG
  (7534). Weapon menu: 18 entries if 14C8 = 0FFh, 17 if 14CA = 0FFh, else 10; armour 10/9/7 by
  14C9/14CB. DIG sets both flags of a kind at once.
- **1320/1321 ("GateState", "GatePos" in exodus-core.map) are the whirlpool's x, y**, and
  1322/1323 its step (dx, dy): MoveWhirlpool 7347 moves it, WORLD 2168 (the party swallowed)
  resets it to x 3, y 7-3Dh. Suggest WhirlX, WhirlY, WhirlDx, WhirlDy (defined in EXDATA).
- **Location**: 2 = a towne (Pray tests it with PartyXY = the entrance), 80h = a fight.
- **L15CD** is the player's y (PlayerXY+1); MonMove seems to hold the map byte under a creature
  (Bribe writes it back to the map) rather than a movement code: check with the monster code.
- Map bytes are shape * 4 (2Ch frigate, 30h whirlpool, 48h guard, 4Ch Lord British, 7Ch
  Exodus, 40h merchant); CheckTerrain (7254) and L259D work with shape numbers.

## Game mechanics found

- Level = experience/100 + 1 on the status line (max 99). Lord British adds 100 max HP when
  exp/100 >= maxHP/100, up to 2500; from 500 the Mark of Kings is needed.
- Per turn (6FDF; off the surface every 4th call): magic regen by class (Wizard to Int, Cleric
  to Wis, Lark/Druid/Alchemist to Int/2, Paladin/Illusionist/Druid to Wis/2 (a Druid can get
  two points), Ranger to min(Int/2, Wis/2); Fighter/Thief/Barbarian none), 0.10 food, poison -1
  HP, every 10th turn +1 HP. Starving: food 0 and 5 HP damage per turn.
- Force field (shape 32): the party never passes unless all members have the Mark of Force;
  only the *first* unmarked member takes 99 (no IsUp test: a dead or ashes member can be the
  one, and HurtPlayer then sets 'D' even on Ashes). Lava (33): each living member without the
  Mark of Fire takes 50, the party passes.
- A frigate cannot sail when the wind is calm or into the wind (7233).
- Class limits for Ready/Wear: tables 79EF/79FA, Exotic always allowed (see ACTIONS comments).
- Dig: Exotic weapon at (21h, 03h), Exotic armour at (13h, 2Ch) on Sosaria. Pray hint at
  (30h, 30h) in the towne entered from x = 22h. Yell EVOCARE at x 0Ah, y 38h/3Bh with the Mark
  of the Snake. Bribe: 100 gold, guards only. Insert: cards at x 1Eh-21h in order L, S, M, D.
- Shop counters: the service is chosen by the player's y & 7 (table 77CE), except a counter to
  the west, which always gives the Equine Emporium (AD70).
- Chest gold is 48-63 or 12-27 ((random(100) | 30h) mod 100), plus 1 in 4 an item.

## Bugs, dead code

- 6BF9: a stray `ret` byte (0C3h) after HurtPlayer, unreachable.
- 73F2 (MoveWhirlpool): `int 15h` with AH = 2Ch where the main loop uses `int 21h` (get time):
  the key-wait deadline it returns is probably garbage.
- 7B54 HandEquip pops AX and BX swapped (harmless: the caller jumps to MainLoop).
- The shared exits (MsgWhat ...) jump to MainLoop, which never resets SP: HandEquip's "A" entry
  (7D02) leaves 18 bytes on the 256-byte stack each time. Not checked whether repeated use
  can overflow it.
- 8050: `shr al, cl` with CL = 0 (a leftover; MonTalk's speech number is not shifted).
- 7967+9: "No One There" follows "<-What?" with nothing pointing at it.
- 76E6: 10 unused zero bytes.

## Open questions

- Sound codes 0F8h (lava), 0FCh and 0FDh (with BL/BH parameters): what each sounds like.
- 7704: dungeon event 7 has no handler (DUNMOVE skips it).
- ACFC is listed as "Radrion's shrine" in MAP.md: not checked.
