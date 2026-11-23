# Ultima III: the game's mechanics, read from its source

This is how *Ultima III: Exodus* (the PC version by James R. Van Artsdalen, 1983, as sold by GOG)
actually works: turns, the moons, character creation, combat, both schools of magic, money,
Sosaria and Ambrosia, the dungeons, the marks, the cards and the end of the game. It is read from
the byte-identical 8086 assembly in `src/` (the ground truth): `src/exodus/` (EXODUS.BIN, the
game), `src/bootup/` (BOOTUP.BIN: menu, roster, character creation), `src/dungeon/` (DUNGEON.DAT,
the 3D view overlay) and `src/LIB.INC` (the library shared by all programs: screen, keyboard,
files, sound, the random numbers, the wind). Data tables were decoded from `gamedata/` with the
layouts of `docs/FORMATS.md`. Not from the manual, wikis or memory of the game: where those
disagree, this is what the program does.

**Conventions**

- **Citations** are `src/<prog>/<FILE>:Routine` with the routine's original address (`@1BD5`);
  inside a section the program and file are often dropped once named. `python tools/syms.py
  exodus NAME` maps names and addresses.
- **Numbers.** `..h` is hexadecimal. A **map byte** is a shape number × 4 (water 00, grass 04,
  brush 08, forest 0C, mountains 10, ..., floor 20, chest 24-27, force field 80, lava 84, moon gate
  88, shrine F8); combat maps, the 11 × 11 view and creature kinds use the **shape number** itself
  (grass 1, floor 8, orc 18h ...). The text says which. The shape list is in docs/FORMATS.md 2.
- **BCD.** Every counter the player sees is packed BCD (two decimal digits per byte): hit points,
  maximum hit points, experience, gold, food (2 bytes, plus a byte of hundredths for food), the
  four attributes, magic points and every item count (1 byte, 00-99). Most sums use
  `daa`/`das` and are capped (gold, experience at 9999; item counts at 99) but some wrap; each case
  is stated. Where the code uses a BCD byte as a binary number the text says
  **BCD-as-binary**: attribute "25" is then the byte 25h = 37.
- **Random numbers.** `rnd(n)` is one call of `src/LIB.INC:Random` (@4601 in BOOTUP numbering;
  section 12) with DH = n: it returns `b mod n`, where `b` is the generator's top byte (0-255).
  **This is not uniform when n does not divide 256**, and several tests in the code are much
  rarer than they look: a test "rnd(135) ≥ 128" succeeds only for b = 128-134, i.e. 7 in 256,
  not 7 in 135. All probabilities below are exact over the 256 values of `b`, assuming `b` is
  uniform **(inferred:** the generator is a long additive one; its uniformity was not tested**)**.
  `rnd(0FFh)` (used for most coin flips) gives 0 for b = 0 and b = 255, so "rnd(0FFh) ≥ 128" is
  127/256 and "rnd(0FFh) & 3 = 0" is 65/256.
- **Marks.** **(inferred)** marks a conclusion drawn from how several pieces of code (or code and
  data) interact rather than read from one routine. **[data]** marks something read from
  `gamedata/` files. **(FINDINGS)** means docs/FINDINGS.md says it too and it was re-checked here.
- **Player** means one of the four characters; **party** the group; **creature** a monster or
  townsperson on the map (32 slots per map); **foe** a monster on the 11 × 11 combat map (8 slots).
- **Location** is the variable at PARTY.ULT header byte 2 (`Location`, 14BC): 00 Sosaria, 01 a
  dungeon, 02 a towne, 03 a castle, 04 a picture on show (shrine, fountain, rod, time vision),
  80h a fight, FFh Ambrosia.

Contents: [1 Overview](#1-overview--core-game-loop) ·
[2 Character creation](#2-character-creation--attributes) · [3 Progression](#3-progression) ·
[4 Combat](#4-combat) · [5 Magic](#5-magic) · [6 Economy](#6-inventory-equipment--economy) ·
[7 World & travel](#7-world-structure--travel) · [8 Dungeons](#8-dungeons) ·
[9 NPCs](#9-npcs--conversation) · [10 Party](#10-party) ·
[11 Survival](#11-survival-food-hp-healing-poisonstatus-death-ashes--resurrection) ·
[12 RNG](#12-random-number-generation) · [13 Quest](#13-quest-structure--endgame) ·
[14 Commands](#14-commands) · [15 Bugs & quirks](#15-notable-bugs-quirks-dead-code--pc-port-differences) ·
[16 Open questions](#16-open-questions--unverified)

---

## At a glance

Things the code does that a player would not expect:

- **Race and class change nothing at creation.** There are no bonuses and no class
  requirements: every character spends 50 points on four attributes of 5-25 each (2.2). Race
  only sets how high the Ambrosian shrines will raise an attribute (3.3); class sets the spell
  school, the magic point limit, the weapons and armour allowed and a few dexterity bonuses.
- **Level does almost nothing.** It is the experience's hundreds plus one, shown on the status
  line. Its only use is Lord British's test: he adds 100 to the *maximum* hit points (never heals)
  whenever experience/100 ≥ maximum/100 (3.2). Raising your maximum hit points also raises the
  damage every foe deals to you (4.6).
- **Many "1 in N" chances are much rarer than the code comments say**, because `Random` is the top
  byte *mod* N (section 12): a creature appears on Sosaria with 7/256 (2.7 %) a turn, not 7/135; a
  dungeon encounter comes with (level + 1)/256 on level 1-8 (0.8 %-3.5 %), not (L+2)/(L+130);
  foes' spells come 1 time in 4, not 1 in 3.
- **Food is eaten at full rate only on Sosaria.** The upkeep (magic points, food, poison,
  regeneration) runs every turn on Sosaria but only every 4th turn in towns, Ambrosia, dungeons and
  fights (11.1).
- **Hit points exactly 0 are alive**, and a player raised from death (temple or spell) keeps 0 hit
  points (11.4).
- **There is no fleeing.** A fight ends when all foes are dead or all players are (4.8).
- **Lord British cannot be hurt.** Any fight in his castle makes him and the guards hostile; he
  then chases the party, and a fight with him can only end in the party's death **(inferred)**
  (4.11, 9.4).
- **The cards are found with Search on the four Ambrosian shrines, the marks by touching the red
  hot rods in the dungeons' depths, the Exotic arms by Dig at two spots on Sosaria**; the "fight"
  with Exodus is no fight: you Insert the four cards into the four panels, left to right, Love, Sol,
  Moons, Death; a wrong card or panel kills the player who tried (13).
- **Castle Exodus has invisible monsters**: hostile creature slots whose tile is Floor, Grass or a
  Chest **[data]** (9.6).
- **Ambrosia is reloaded on every visit and has no way out on foot**: its edges are mountains. The
  code's only exit is a whirlpool, which only a frigate can enter; the only frigates there are the
  ones pirate ships leave when they are fought from land **(inferred)** (7.6).
- **The wind, the whirlpool and all animation run at keyboard-polling speed** (faster on a faster
  CPU), and a command not given within about 5 seconds of wall-clock time is a Pass (1.2, 7.5).

---

## 1. Overview & core game loop

### 1.1 Program flow

ULTIMA.COM (the intro) loads BOOTUP.BIN over itself; BOOTUP's main menu offers *Return to the
View*, *Organize a Party* and *Journey Onward* (`src/bootup/TITLE.ASM:RunMainMenu` @13A0).
Journey Onward (`JourneyOnward` @1437) refuses "(No Party)" without a party and "(No Active
Players)" when none of the four party records is Good or Poisoned; otherwise it chain-loads
EXODUS.BIN over itself and jumps through EXODUS's entry vector at 1328.

`src/exodus/WORLD.ASM:StartUp` (@24C4) loads CHARSET, PARTY.ULT, SOSARIA.ULT and SHAPES, calls
`AdvanceMoons` once (**the moons step once every time EXODUS starts**), puts the party at its saved
position (`PartyXY`), sets sound on, light off, Negate Time off, seeds the random generator from
the DOS date and time (section 12) and enters the key loop. The party always starts on Sosaria:
PARTY.ULT is always written with Location 0 (11.5). EXODUS never returns to BOOTUP; character
records go back to the roster only when the party is dispersed in BOOTUP (10.4).

### 1.2 One turn on the surface and in towns

There is no clock: **every command is one turn**, including Z)tats, V)olume, L)ook, a failed command
and an unknown key (all of them end in `jmp MainLoop`; the shared error exits `MsgWhat`,
`MsgNotHere`, ... in `EQUIP.ASM` @7DA8-7DFF also jump to `MainLoop`).

1. **Key** (`EXDATA.ASM:ReadCommand` @1B77): `BuildView`, `CheckAllOut` (all four records out:
   "All Players Out!", save, hang; 11.5), prompt. It waits until the DOS clock's seconds reach
   *now + 5*; meanwhile it calls `MoveWhirlpool` on every poll (7.5). **No key within about 5
   seconds = Space (Pass)**. Letters are upper-cased and looked up in the 33-entry `SurfaceKeys`;
   not found: "<-What?" (still a turn). The key word is kept in `LastKey`.
2. **Command**: the handler runs and jumps to `MainLoop`.
3. **`LOOP.ASM:MainLoop`** (@1BD5), the end of every turn:
   - Location 80h (a fight) → `COMBAT.ASM:PlayerTurnEnd`; Location 1 (dungeon) →
     `DUNMOVE.ASM:DungeonTurnEnd` (section 8).
   - `MoveCount += PartySize` (BCD, 8 digits; `EQUIP.ASM:AddMoves` @7E02). The "moves" printed by
     Quit and at the end of the game are therefore **player-moves**, not turns.
   - In a towne, castle or Ambrosia (Location ≥ 2 unsigned, i.e. 2, 3, FFh), a party at x = 0 or
     y = 0 leaves (`SHRINE.ASM:ExitToSosaria` @6458; 7.3).
   - `PARTY.ASM:PartyUpkeep` (@6FDF): magic points, food, poison, regeneration (11.1).
   - Moon gates and moons: if the party stands on a moon gate (map byte 88h) it is teleported
     (`ITEMS.ASM:MoonGateJump` @5B51) and then the moons step (`WORLD.ASM:AdvanceMoons` @20AE);
     otherwise the moons step and, if the party now stands on a gate (it may have just appeared
     under it), it is teleported.
   - A whirlpool (map byte 30h) under the party → `WORLD.ASM:Whirlpool` (7.5).
   - In Castle Exodus (`ITEMS.ASM:InExodusCastle` @5B28): Negate Time is cancelled and fire strikes
     a random view cell (13.4).
   - `WORLD.ASM:MonTurn` (@226C): the creatures (4.10) and the spawn (4.9), unless Negate Time
     (`TimeStop`) is counting down; then `BuildView` and back to step 1.

The turn order is therefore: **player command → move counter → town-edge exit → upkeep → moon gate
/ moons → whirlpool → Exodus fire → creatures move or attack → a creature may spawn**.

**Riding.** On a horse or in a frigate (`PartyTile` ≠ 3Fh), `MonTurn` flips `RideToggle` between
+1 and -1 after each arrow-key move and lets the creatures act only on every other one; any other
command resets the toggle so that they act (@2273-228A). The skipped half-turns also do not count
down Negate Time. A horse or frigate thus doubles the party's speed against creatures; it has no
other effect on land travel (the horse plays its step sound three times instead of twice:
`PARTY.ASM:CheckTerrain` @7285).

### 1.3 Moons and moon gates

`WORLD.ASM:AdvanceMoons` (@20AE) does real work only on Sosaria (Location 0); elsewhere it only
reprints the phases at the top of the screen.

- `Moon1Count` and `Moon2Count` count down; at -1 moon 1's phase advances (reload 11: **a phase
  every 12 steps**, a cycle of 96) and moon 2's (reload 3: **every 4 steps**, a cycle of 32). The
  phases (0-7) and counters are part of SOSARIA.ULT (FORMATS.md 3); the shipped file starts them at
  0, 0 with counters 12 and 4, so moon 1's first change comes after 13 steps **[data]**.
- **The gate**: only when moon 2's phase changed, the cell of the gate for moon 1's *old* phase
  becomes grass (map byte 04, whatever was there) and the cell for moon 1's *new* phase becomes a
  gate (88h). The eight positions (`EXDATA.ASM:GateXTbl/GateYTbl` @194D):

  | phase | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
  |---|---|---|---|---|---|---|---|---|
  | (x, y) | (8, 8) | (57, 46) | (15, 27) | (36, 58) | (15, 29) | (12, 55) | (31, 31) | (58, 31) |

- **Travel** (`ITEMS.ASM:MoonGateJump` @5B51): stepping on (or standing on) a gate moves the party to
  the gate position of **moon 2's** phase. Gates can be entered on foot or horseback
  (`CheckTerrain` accepts shape 22h), not by frigate.
- **Dawn** (map cell (37, 53), `DawnCell`): at a moon-2 change, if both *old* phases were 7 the cell
  becomes a Towne (18h); if both were 0 it becomes Forest (0Ch). With the shipped start, Dawn
  appears at moon step 97 and vanishes at step 101, then every 96 steps: **Dawn is open for 4
  moon steps in 96** (simulated from the code **(inferred)**). Entering it works only while the
  cell is a towne (Enter checks the tile, 7.3).
- Extra moon steps: one at every start of EXODUS, and one each time M)odify order is used on
  Sosaria (`LOOP.ASM:CmdModify` @1EED calls `AdvanceMoons`).
- `MainLoop` tests the map byte 88h whatever the Location, so **the moon-gate tiles inside Lord
  British's castle (four at (19-22, 43)) and Castle Exodus (six at (29-34, 9)) [data] teleport the
  party within that castle's map** to the Sosaria gate coordinates of moon 2's phase **(inferred)**;
  the moons do not advance there.

### 1.4 Time elsewhere

- **Dungeon** turns: section 8.3. **Fights**: section 4.3. In both, `PartyUpkeep` runs every 4th
  call (11.1).
- **Negate Time** (`TimeStop`, set to 10 by the N command, the Altair spell and the combat N): on
  the map the creatures neither move nor spawn for 10 creature turns (`MonTurn` @228C); in a fight
  the foes miss 10 rounds (`FoesTurn` @914F). It is cleared by a victory, by entering Castle Exodus
  (every turn there and every combat turn there) and, oddly, by trying to Board a horse in Ambrosia
  (`CmdBoard` @1D24).

---

## 2. Character creation & attributes

### 2.1 The roster and the procedure

ROSTER.ULT holds 20 characters of 64 bytes (record layout: FORMATS.md 6). *Organize a Party*
(`src/bootup/ORGANIZE.ASM:RunOrganizeMenu` @14C9) offers Examine the register, Create, Form the
party, Disperse, Terminate and Look at a character.

`src/bootup/CREATE.ASM:CreateChar` (@1A6D) asks a roster number 1-20; the slot must be empty
("(Not Empty!)"). `EnterCharacter` (@1BC8) then asks, in this order:

1. **Name**: at most 9 characters (`ReadLine` with CX = 9); an empty name abandons the creation.
2. **Sex**: M Male, F Female, O Other (`SexKeys` "MFO"). Stored as the letter; **no effect**.
3. **Race**: H Human, E Elf, D Dwarf, B Bobbit, F Fuzzy (`RaceKeys`).
4. **Type** (class): F Fighter, C Cleric, W Wizard, T Thief, P Paladin, L Lark, B Barbarian, D
   Druid, I Illusionist, A Alchemist, R Ranger (`ClassKeys`).
5. **Attributes** from **50 points** (BCD in CL), each entered as two digits and re-asked until
   valid:
   - Strength: 5-25.
   - Dexterity: 5-25 and at least 10 points must remain (`cmp al,10h; jb` @1C75).
   - Intelligence: 5-25, not more than remains, and at least 5 must remain (@1C99-1CA0).
   - Wisdom: 5-25 and not more than remains (`cmp cl,al; jb` @1CBB).
   - Points left over are lost. So every attribute starts at 5-25 and the total is 20-50.
6. **O.K.?** Y keeps the character, N clears the slot.

**There are no race or sex bonuses and no class requirements**: nothing in BOOTUP reads the race,
sex or class while the numbers are entered. (The Apple II original applied race maxima at creation
according to its manual; this code does not; the race only caps the shrine increases, 3.3.)

### 2.2 Starting state

On Y (`CreateChar_Accept` @1AFF): status Good ('G'), not in a party, **150 hit points and 150
maximum**, **150 food**, **150 gold**, **one Dagger and one Cloth armour** owned (counts at record
31h and 29h) but **Hand readied and Skin worn**, 0 experience (level 1), 0 magic points, no gems,
keys, powders, torches, marks or cards. ROSTER.ULT is saved at once.

### 2.3 What each attribute does

| attribute | used by | effect |
|---|---|---|
| Strength | `COMBAT.ASM:AttackHit` @8F25 | melee and missile damage (4.4) |
| Dexterity | `AttackHit` @8EEE; `ITEMS.ASM:DexRoll` @5B85 | the second half of the to-hit roll (4.4); stealing, evading chest traps, the dungeon trap cell (6.8, 8.5) |
| Intelligence | `PARTY.ASM:PartyUpkeep` @701C...; `MAGIC.ASM:SpellMentar`, `SpellDagMentar` | magic point limit of Wizards, Larks, Druids, Alchemists, Rangers (5.2); the damage of Mentar and Dag Mentar |
| Wisdom | `PartyUpkeep` @702D...; `SpellAnjuSermani` | magic point limit of Clerics, Paladins, Illusionists, Druids, Rangers; Anju Sermani costs 5 Wisdom |

The attributes play no part in prices, hit points or armour. Strength and dexterity are converted
from BCD to binary (`aad`) before use, except one term of the damage formula (4.4).

### 2.4 Race

Race has exactly one use: the most an Ambrosian shrine raises each attribute to
(`ITEMS.ASM:RaceStatMax` @58D2, used by `SHRINE.ASM:EnterShrine` @6366):

| race | Str | Dex | Int | Wis |
|---|---|---|---|---|
| Human | 75 | 75 | 75 | 75 |
| Elf | 75 | 99 | 75 | 50 |
| Dwarf | 99 | 75 | 50 | 75 |
| Bobbit | 75 | 50 | 75 | 99 |
| Fuzzy | 25 | 99 | 99 | 75 |

A race letter not in the table (impossible from BOOTUP) would use the Fuzzy row.

### 2.5 Class

| class | spells (5.1) | magic point limit (5.2) | weapons (6.2) | armour (6.3) | DexRoll bonus | combat tile |
|---|---|---|---|---|---|---|
| Fighter F | none | - | all | all | 0 | Fighter |
| Cleric C | cleric | Wis | Hand-Mace | up to Chain | 0 | Cleric |
| Wizard W | wizard | Int | Hand, Dagger | Cloth | 0 | Wizard |
| Thief T | none | - | up to Sword | up to Leather | +128 | Thief |
| Paladin P | cleric | Wis/2 | all | up to Plate | 0 | Fighter |
| Lark L | wizard | Int/2 | all | Cloth | 0 | Jester |
| Barbarian B | none | - | all | up to Leather | +64 | Fighter |
| Druid D | either (asked) | Int/2 and Wis/2 | Hand-Mace | Cloth | 0 | Cleric |
| Illusionist I | cleric | Wis/2 | Hand-Mace | up to Leather | +64 | Wizard |
| Alchemist A | wizard | Int/2 | Hand, Dagger | Cloth | 0 | Wizard |
| Ranger R | either (asked) | min(Int/2, Wis/2) | up to +2 Swd | up to +2 Plate | +64 | Ranger |

Sources: `MAGIC.ASM:CastSpell` @5D83, `PARTY.ASM:PartyUpkeep` @7013-7091,
`ACTIONS.ASM:MaxWeaponTbl/MaxArmourTbl` @79EF/@79FA, `ITEMS.ASM:DexRoll` @5B85,
`CMDTAB.ASM:CombatClassLetters/CombatClassTiles` @8625 (a class not in that table, i.e. Ranger,
shows as the Ranger shape 3Fh). The Exotic weapon and armour are allowed to every class.

### 2.6 Roster management

- **Terminate** (`TerminateChar` @19DB) zeroes a record and saves; refused for a party member.
- **Look** (`LookAtChar` @158F) shows the party's copy for a party member, the roster copy otherwise.
- **Form** and **Disperse**: section 10.4.

---

## 3. Progression

### 3.1 Experience and level

Experience is a BCD word capped at 9999 (`ITEMS.ASM:AddExp` @5D4B). It comes **only from killing
foes in fights**: `FoeExp[FoeTile & 0Fh]` to the player whose blow or spell killed (4.7). Chests,
cannon kills, stealing and quests give none.

**Level = experience hundreds + 1**, BCD, shown as at most 99 (`PARTY.ASM:StatusLine` @6D19). The
level is used nowhere: not for hit chance, damage, magic points or spells.

### 3.2 Lord British: maximum hit points

Transacting with Lord British (`EQUIP.ASM:CmdTransact` @807B; he is recognised by his tile 4Ch, not
by talk) compares two BCD bytes, the maximum hit points' hundreds `M` and the experience's
hundreds `E`:

1. `M > E`: "Experience more!"
2. `M ≥ 25h`: "No more!"
3. `M ≥ 5` and the player lacks the Mark of Kings (record 0Eh bit 7): "Seek ye the Mark of Kings!"
4. Otherwise `M += 1` (BCD): **+100 maximum hit points**, "Thou art greater", and the screen flashes.

He never heals and charges nothing; one visit gives one +100, and he can be asked again at once.
Since a new character starts at 150, the maximum goes 150, 250, ..., **2550** (the cap tests the
hundreds byte, so the 50 stays; FINDINGS says 2500). The Mark of Kings is needed from 550 on (raising
550 → 650 and beyond). Current hit points are not changed: the new maximum must be filled by
regeneration, fountains, temples or spells.

### 3.3 Raising attributes: the shrines of Ambrosia

`SHRINE.ASM:EnterShrine` (@6366): E)nter on a shrine (map byte F8h) in Ambrosia. "Who enters?" (the
player must be up). **The attribute is chosen by the shrine's x & 3**: 0 Strength, 1 Dexterity,
2 Intelligence, 3 Wisdom. The four shrines are at **[data]** (4, 36) Strength, (45, 52) Dexterity,
(6, 6) Intelligence, (55, 27) Wisdom. "Offering*100-": two digits, read as BCD `n`:

- 0: "Then be off!".
- `n` > the gold's hundreds byte (BCD-as-binary compare of two BCD bytes, which orders them
  correctly): "You can't cheat the Gods!".
- Otherwise the gold's hundreds byte loses `n` (the tens and units of gold are untouched), and
  the attribute becomes `attr + n` (BCD); if that carries past 99 or exceeds the race maximum
  (2.4) it is set to the maximum. **Gold paid beyond the cap is lost.** "Shazam!".

So **one gold piece per hundred is one attribute point**, up to the race maximum, at any of the
shrines any number of times. The shrine picture is shown with Location 4 meanwhile.

`ReadNumber` also accepts the digits A-F and the shrine does not reject them (it ignores AH, the
"not decimal" flag): "0A" behaves like 10, while a mixed entry such as "1F" leaves non-BCD bytes in
the gold and the attribute **(computed from the 8086's DAS/DAA rules, not tested)** (15.1).

### 3.4 Caps

| quantity | cap | where |
|---|---|---|
| experience | 9999 | `AddExp` |
| level shown | 99 | `StatusLine` |
| maximum hit points | hundreds byte 25 (2550 from a 150 start) | `CmdTransact` |
| hit points | the maximum (healing), no cap on the BCD sum otherwise | `AddHitPoints` @5D2B |
| attributes | 25 at creation, the race maximum via shrines | `EnterCharacter`, `EnterShrine` |
| magic points | class limit for regeneration only (5.2) | `PartyUpkeep` |
| gold | 9999 (chests and Join; sales refuse) | `AddGold` @5D67, `CmdJoinGold`, shops |
| food | 9999 (grocer refuses) | `ShopGrocer` |
| items | 99 each | shops, chests, Hand |

---

## 4. Combat

### 4.1 How a fight starts

All fights take place on an 11 × 11 combat map (CNFLCT_x.ULT) loaded over the start-up code's
memory (FORMATS.md 5, 9). Three ways in:

- **A)ttack** on the surface or in a town (`COMBAT.ASM:CmdAttack` @888B): a direction; the creature
  in that adjacent cell (`EQUIP.ASM:FindMonster` @7F96) is fought; none: "Not Here!".
- **A creature reaches the party** (`WORLD.ASM:MoveMonsters` @23C5): a hostile creature whose next
  step would land on the party's cell starts the fight (`FightCreature` @88AA).
- **A dungeon encounter** (`DUNMOVE.ASM:DungeonTurnEnd` @83B2; 8.4) → `StartCombat` @88EA.

`FightCreature` removes the creature from the map: its cell becomes **a chest on the ground it
stood on** (map byte 24h + (MonUnder/4 & 3): on floor 24h, grass 25h, brush 26h, forest 27h), or
stays water for a sea creature. A **pirate ship fought by a party not in a frigate leaves an empty
frigate (2Ch)** in its cell. `FoeTile` = the creature's shape.

`StartCombat`:

1. Clears `KillSpellUsed` (5.4). Every guard (48h) and Lord British (4Ch) on the current map gets
   talk code C0h: **hostile from now on** (it also stops them talking). This happens for every
   fight, wherever it starts.
2. Prints "---Conflict!!---" and the foes' plural name (4.12).
3. Picks the combat map:

   | situation | map |
   |---|---|
   | in a dungeon | C (all floor) |
   | pirates (FoeTile 0Fh, then fought as Thieves 17h), party in a frigate | S (two decks) |
   | pirates, party ashore | A (ship deck beside a beach) |
   | party in a frigate, sea foe (FoeTile < 10h) | Q (frigate deck in open water) |
   | party in a frigate, land foe | R (deck, then beach) |
   | sea foe (FoeTile 0Bh-0Fh) and party ashore | M (water half, land half) |
   | by the tile under the party: grass | G |
   | brush | B |
   | forest | F |
   | floor, a chest on floor, force field, lava | C |
   | anything else; FoeTile 8 (an invisible Floor creature) | C |
   | otherwise | G |

4. Saves Location in `SavedLocation` and sets Location 80h.
5. **Players**: each player who is Good or Poisoned is placed at the map's start position for his
   slot with his class tile (2.5); dead and ashen players are absent (x = FFh).
6. **Number of foes**: **8 in Castle Exodus**; in a towne or castle (`SavedLocation` 2 or 3) **8 if
   the foes are Guards, else 1**; elsewhere (Sosaria, Ambrosia, dungeons) **`rnd(8) + 1`, 1-8
   uniformly**. Each goes into a random free slot of 8, at that slot's start position in the file.
   **Foe hit points = `rnd(FoeHitPoints[FoeTile & 0Fh]) | 0Fh`** (4.7).

All foes of a fight are of one kind. The fight starts with a fanfare and the key buffer is flushed.

### 4.2 The combat screen and commands

`PlayerTurn` (@8B5A) highlights the player's number, prints "----Player n----" and blinks his tile;
the key is looked up in `CMDTAB.ASM:CombatKeys` (@8579):

| key | handler | effect | turn spent |
|---|---|---|---|
| arrows | `CCmdNorth`... → `CCmdMove` @8C3C | one step onto grass, brush, forest or floor, inside the 11 × 11 map | yes (also when refused: "Invalid Move!" → MainLoop) |
| A | `CCmdAttack` @8D9F | attack in a direction (4.4); Esc spends the turn | yes |
| C | `CCmdCast` @8D38 | cast a spell (section 5) | yes |
| R | `CCmdReady` @8CF1 | ready a weapon (6.2) | yes |
| N | `CCmdNegate` @8D57 | one powder: foes miss 10 rounds; none: "None Left!" | yes |
| Z | `CCmdZtats` @8D0B | Ztats | yes |
| Space | `CCmdPass` @8D83 | pass | yes |
| V, Alt-S, Alt-V | `CCmdVolume` → `CmdVolume` | sound on/off | yes |
| B D E F G H I J K L M O P Q S T U W X Y | `CCmdBad` @8D8D | "Not usable cmd!" | **no** |
| any other key | `MsgWhat` | "<-What?" | yes |
| no key for 5 s | | Pass | yes |

**There is no flee command and no way off the map**: `CCmdMove` refuses cells outside 0-10 (4.8).

### 4.3 Turn order (initiative)

There is no initiative roll. A **round** (`CombatRound` @8B52) is: `PartyUpkeep` (which acts only
every 4th call off Sosaria, 11.1), then each player in party order 1, 2, 3, 4 (dead and ashen
players are skipped), then `FoesTurn` (@914F): foes in slot order 0-7. After every player action
`PlayerTurnEnd` (@8BFC) adds 1 to the move counter, cancels Negate Time in Castle Exodus and checks
for victory, so the fight ends the moment the last foe dies.

### 4.4 The player's attack

`CCmdAttack` (@8D9F): the readied weapon's name, a direction.

- **Missile weapons**: Sling (3), Bow (5), +2 Bow (9), +4 Bow (13) always shoot: `ShootLine` (@8E7A)
  steps from the player along the direction, flashing each cell, until it finds a live foe or
  leaves the map. **Walls, water and players do not stop it.**
- **Every other weapon** (including Hand, Gloves, Exotic) strikes only the adjacent cell (no
  diagonals). With a **Dagger** and no foe in that cell the dagger is **thrown**: one Dagger is
  taken from the owned count (if that leaves 0, the readied weapon becomes Hand) and it flies like
  an arrow.
- No foe hit: "Missed!".

`AttackHit` (@8EBC), when a foe is reached:

1. **In Castle Exodus only the Exotic weapon (15) can hit**; any other: "Missed!".
2. **To hit**: if `rnd(0FFh) ≥ 128` (127/256) the blow hits; otherwise `r = rnd(99)` (0-98), turned
   into BCD (`aam`), hits if `r < Dex` (BCD compare). Because 256 = 2 × 99 + 58, the values 0-57
   come 3 times in 256 and 58-98 twice, so with dexterity `d`:

   `P(hit) = 127/256 + 129/256 × (3·min(d, 58) + 2·max(0, d − 58)) / 256`

   | Dex | 5 | 10 | 15 | 20 | 25 | 30 | 40 | 50 | 60 | 75 | 99 |
   |---|---|---|---|---|---|---|---|---|---|---|---|
   | P(hit) | 52.6 % | 55.5 % | 58.5 % | 61.4 % | 64.4 % | 67.3 % | 73.2 % | 79.1 % | 84.6 % | 90.6 % | 100 % |

3. **Damage** (binary byte, no overflow possible):

   `damage = 3 × weapon + 4 + rnd(Str | 1) + (StrBCD >> 1) + (StrBCD & 1)`

   where `Str` is the strength in binary and `StrBCD` the BCD byte **used as binary** (`shr al,1;
   adc dl,al` @8F3C): the last two terms are ceil(StrBCD / 2), e.g. strength 25 → 25h = 37 → 19,
   strength 50 → 40, 75 → 59, 99 → 77 (FINDINGS: probably meant to use the number). Examples
   (minimum-maximum):

   | strength | Hand (0) | Dagger (1) | Sword (6) | +4 Swd (14) | Exotic (15) |
   |---|---|---|---|---|---|
   | 15 (15h → 11) | 15-29 | 18-32 | 33-47 | 57-71 | 60-74 |
   | 25 (25h → 19) | 23-47 | 26-50 | 41-65 | 65-89 | 68-92 |
   | 50 (50h → 40) | 44-93 | 47-96 | 62-111 | 86-135 | 89-138 |
   | 99 (99h → 77) | 81-179 | 84-182 | 99-197 | 123-221 | 126-224 |

4. `DamageFoe` (@8F5A): **Lord British (FoeTile 13h) takes no damage at all.** Otherwise the foe's
   hit points (a byte) minus the damage; **0 or below kills** ("Killed! Exp.+nn"): the foe's cell
   gets back the tile it stood on and the killer gets `FoeExp` (3.1).

### 4.5 Weapons and armour in combat

The weapon's only properties are its index (×3 damage) and whether it is a missile; the armour's
only property is its index in the foes' to-hit roll (4.6). Class limits: 6.2, 6.3. Weapons never
break; only thrown daggers are used up.

### 4.6 Foes' attacks

`FoesTurn` (@914F), for each live foe in slot order. If Negate Time runs, the whole round is skipped
(the counter drops by 1).

1. `FoeChooseMove` (@9020) looks at the players who are up, in party order. **A player adjacent to
   the foe, diagonals included, is attacked at once** (the first such player in party order).
2. Otherwise, if some player is reachable, and `rnd(0FFh) < 128` (129/256), and the foe is a
   **Dragon** (1Dh): it **breathes** (`FoeBreathe` @90FD) along its step direction towards the nearest
   player: fire moves cell by cell and hurts the first player whose cell it enters (`FoeHurtPlayer`,
   with no armour roll), or leaves the map. The direction is the sign vector of the movement step,
   so the breath reaches a player only if he lies on that line.
3. Otherwise, with `rnd(0C0h) ≥ 128` (**64/256 = 1/4**; the comment's "1 in 3" assumes a uniform
   rnd), a **caster** (Serpent 0Dh, Man-O-War 0Eh, Wizard 16h, Daemon 1Bh, Dragon 1Dh, Balron 1Eh)
   casts at a random player slot `rnd(0FFh) & 3` (0-3, whatever the party size). If that player's
   status is not exactly Good (empty slot, absent, dead or **poisoned**) the foe moves instead;
   otherwise the screen flashes and a normal `FoeAttack` follows (with its armour roll and its
   poison/theft extras) with the magic flash tile. **A poisoned player cannot be targeted by magic.**
4. Otherwise it **steps** towards the nearest player (`FoeStep` @9215): `|dx| + |dy|`, ties going to
   the later player; the step tried is diagonal, then vertical, then horizontal, onto a cell the
   foe may enter (`FoeCanEnter` @8FEB: sea foes 0Bh-0Fh water only, others grass, brush, forest or
   floor, never a cell with a live foe). No step possible: it stays.

**`FoeAttack`** (@9244) against player `p`:

- Man-O-War (0Eh), Balron (1Eh), Pincher (1Ch): `FoePoison` first: `rnd(0FFh) & 3 = 0` (65/256) and
  status Good → Poisoned.
- Thief (17h, which includes pirates): `FoeSteal` first (4.13).
- These extras happen **whether or not the blow lands**.
- **To hit**: in Castle Exodus the blow **always hits unless the player wears Exotic armour (7)**;
  otherwise it hits when `rnd(armour + 16) < 8`:

  | armour worn | 0 Skin | 1 Cloth | 2 Leather | 3 Chain | 4 Plate | 5 +2 Chain | 6 +2 Plate | 7 Exotic |
  |---|---|---|---|---|---|---|---|---|
  | foe hit chance | 50.0 % | 47.3 % | 45.3 % | 43.8 % | 40.6 % | 39.1 % | 37.5 % | 35.5 % |

  (exact under the mod model; 8/(16 + armour) would give 50.0 ... 34.8 %).

**`FoeHurtPlayer`** (@92AF), the damage of a hit, breath or spell:

```
range  = (FoeHitPoints[FoeTile & 0Fh] >> 3) + MaxHP_hundreds_byte     ; that byte BCD-as-binary
damage = rnd(range | 1) + 1                 ; then converted to BCD with aam
HP    -= damage                             ; HurtPlayer
HP    -= (SavedLocation & 3) * 10           ; Sosaria 0, dungeon 10, towne 20, castle 30, Ambrosia 30
```

- **The damage grows with the victim's maximum hit points**: the hundreds byte of the maximum is
  added to the range, BCD-as-binary (1 at 150, 25h = 37 at 2550). A character at 2550 maximum
  takes up to 37 more per blow than a new one.
- **The location surcharge**: 10 in dungeons, 20 in townes, 30 in castles and in Ambrosia (FFh & 3
  = 3), 0 on Sosaria, on every hit.
- The largest possible range is (F0h >> 3) + 37 = 67, so the conversion never overflows.
- A player who dies is removed from the map ("Killed!!!"); if nobody is left, `CheckAllOut` ends
  the game (11.5).

### 4.7 Monster table

From `CMDTAB.ASM:FoeHitPoints` and `FoeExp` (@8605, @8615), indexed by `FoeTile & 0Fh` (so the sea
monsters share the Dragon's and Balron's rows):

| idx | foe (shape) | HP range | hit points (`rnd(range) | 0Fh`) | exp | damage range add | notes |
|---|---|---|---|---|---|---|---|
| 0 | Merchant (10h) | 20h | 15, 31 | 1 | 4 | |
| 1 | Jester (11h) | 20h | 15, 31 | 2 | 4 | |
| 2 | Guard (12h) | F0h | 15-239 | 15 | 30 | 8 at once in towns |
| 3 | Lord British (13h) | F0h | 15-239 | 20 | 30 | **takes no damage** |
| 4 | Fighter (14h) | C0h | 15-191 | 8 | 24 | |
| 5 | Cleric (15h) | 60h | 15-95 | 6 | 12 | |
| 6 | Wizard (16h) | A0h | 15-159 | 10 | 20 | caster |
| 7 | Thief (17h), Pirate (0Fh) | 80h | 15-127 | 5 | 16 | steals |
| 8 | Orc (18h), "Floor" (08) | 30h | 15, 31, 47 | 3 | 6 | |
| 9 | Skeleton (19h), "Chest" (09) | 50h | 15-79 | 4 | 10 | |
| A | Giant (1Ah), Horse (0Ah) | 70h | 15-111 | 6 | 14 | |
| B | Daemon (1Bh), Frigate (0Bh) | A0h | 15-159 | 8 | 20 | caster |
| C | Pincher (1Ch), Whirlpool (0Ch) | C0h | 15-191 | 10 | 24 | poisons |
| D | Dragon (1Dh), Serpent (0Dh) | E0h | 15-223 | 15 | 28 | Dragon breathes; both cast; Serpent sea |
| E | Balron (1Eh), Man-O-War (0Eh) | F0h | 15-239 | 20 | 30 | both cast and poison; Man-O-War sea |
| F | Exodus (1Fh) | F0h | - | 5 | 30 | never fought (13.4) |

The hit points are always of the form 16k + 15. "Damage range add" is `range >> 3` above. The
experience values are BCD (15h = 15). A Grass creature (shape 1, Castle Exodus) uses row 1.

### 4.8 Fleeing and the end of a fight

No fleeing: moves off the map are refused, and the party leaves the fight only by **Victory**
(`Victory` @8FB6: all 8 foe slots at 0 hit points; Negate Time cleared, Location restored, back to
the main loop) or by dying. On the surface and in towns the reward is the chest left where the
creature stood (4.1, 6.8); in a dungeon the encounter's cell was turned into a chest (8.4).

### 4.9 Spawning on Sosaria

`WORLD.ASM:SpawnMonster` (@22A5), at the end of each creature turn, **on Sosaria only** (Location 0;
never in Ambrosia, towns or dungeons):

1. `rnd(87h) ≥ 128`: **7/256 = 2.7 % per turn** (the code comment says "7 in 135").
2. The first free slot (0-31); none: nothing.
3. **Kind** = `rnd(13) AND rnd(13)` into `SpawnTiles` (@1965):

   | index | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
   |---|---|---|---|---|---|---|---|---|---|---|---|---|---|
   | kind | Orc | Thief | Skeleton | Fighter | Giant | Daemon | Serpent | Pincher | Wizard | Man-O-War | Pirate | Dragon | Balron |
   | chance | 42.5 % | 12.4 % | 12.4 % | 4.2 % | 10.1 % | 1.8 % | 1.8 % | 0.6 % | 9.7 % | 1.6 % | 1.6 % | 0.6 % | 0.6 % |

   Serpent, Man-O-War and Pirate need water (`SpawnMoves` 0), the others grass (4).
4. Position: `x = rnd(64)`, refused if equal to the party's x; `y = rnd(64)`, refused if equal to
   the party's y; the cell must be exactly the kind's ground (grass, or water). A refusal frees the
   slot: nothing appears this turn (a different kind is drawn next time).
5. The creature gets talk code C0h (hostile).

Creatures never despawn; they are saved with SOSARIA.ULT, so Sosaria fills up to 32 creatures over
time **(inferred)**.

### 4.10 Creature movement on the map

`WORLD.ASM:MoveMonsters` (@23A5), slots 31 down to 0, every creature turn:

- **On Sosaria** every creature chases the party: `MonStepToPlayer` (`SHRINE.ASM` @633B) gives a
  step of -1/0/+1 per axis towards the party the short way round the wrapping map. If that step is
  the party's cell, **the creature attacks: the fight begins** (4.1). Otherwise it tries the
  diagonal, vertical and horizontal steps onto a cell `MonCanEnter` (@2228) allows: sea creatures
  (tiles 2Ch-3Fh) water only; others grass, brush, forest or floor; never a cell holding another
  creature (a "Grass" creature only onto grass).
- **In towns, castles and Ambrosia** (any Location other than 0) the talk code's bits 7-6 decide:
  0 stands still; 1 wanders (half the time, a random step of -1/0/+1 per axis, never onto x or
  y = 0); 2 approaches the party but never attacks (the move onto the party's cell is refused);
  3 behaves as on Sosaria: chases and starts a fight.
- **Dragons (74h) and pirate ships (3Ch)** also fire at the party after moving or failing to move
  (`MonShoot` @232F): half the time (`rnd(0FFh) < 128`), if the creature is inside the 11 × 11 view,
  a fire bolt flies up to 3 cells along the step towards the party, stopped by mountains, walls and
  void; reaching the party's cell it calls `DamageParty` (every player who is up takes `(rnd & 77h)
  + 8`, 8.5).

### 4.11 Lord British and guards in fights

Fighting anything in a town or castle turns every guard and Lord British of that map hostile
(4.1, step 1); hostile guards chase the party and each contact is a fight against **8 guards**.
Lord British, once hostile, also chases (his creature mode becomes 3) and **cannot be damaged**
(`DamageFoe` @8F5F; Necorp's "5 hit points" changes nothing either), so a fight with him ends only
with the party's death **(inferred)**. In combat he walks even when no step was found
(`FoesTurn` @91C5), using a DX left over from `FoeChooseMove` (FINDINGS). Leaving the castle and
re-entering resets everyone (towns are reloaded, 7.3).

### 4.12 Monster names

`PrintFoeName` (@8AE6) normally prints the shape's name. For kinds Thief to Balron (17h-1Eh), **when
the party's y is odd**, one of 16 alternative names is used, picked by the party's x parity:
Thief → Brigand/Cutpurse, Orc → Goblin/Troll, Skeleton → Ghoul/Zombie, Giant → Golem/Titan, Daemon
→ Gargoyle/Mane, Pincher → Snatch/Bradle, Dragon → Griffon/Wyvern, Balron → Orcus/Devil (even x
first). The name is all that changes. Plurals add "s" ("es" for Snatch; none for Grass, Floor, Lord
British, Orcus; "Thieves" spelled out).

### 4.13 Thieves

`FoeSteal` (@93A2), before a thief's blow: half the time a weapon kind `rnd(16)`, otherwise an armour
kind `rnd(8)`; kind 0 (Hand, Skin), the readied weapon or worn armour, or a kind not owned: nothing;
otherwise one of them is taken: "Plr n Pilfered!". Thieves never take gold, food or items.

### 4.14 The frigate's cannons

`ITEMS.ASM:CmdFire` (@5BCF), only in a frigate: a direction; the shot travels up to 3 cells (the
map wraps), flashing fire on each, and stops at the first creature: a pirate ship needs two coin
flips (`rnd(0FFh) ≥ 128` twice, about 1/4), any other creature one (127/256). A hit removes the
creature ("<name>s Destroyed!") with **no experience and no chest**; a miss leaves it. The shot
crosses land and is not blocked by terrain.

### 4.15 Treasure chests and traps

Section 6.8.

---

## 5. Magic

### 5.1 Who casts what

C)ast (`LOOP.ASM:CmdCast` @1D4E, and the combat C) asks a player who must be up, then
`MAGIC.ASM:CastSpell` (@5D83) chooses the school by class: **cleric spells for Cleric, Paladin,
Illusionist; wizard spells for Wizard, Lark, Alchemist; Druid and Ranger are asked "Spell type
W/C-"**; Fighter, Thief, Barbarian: "Not a mage!" (the turn is still spent). A letter A-P picks the
spell. **Cost = 5 × the letter's index (A 0, B 5, ..., P 75)**; more than the caster's magic points:
"M.P. too low!". The points are taken before the spell's own checks, so **a spell that then fails
("Failed!") still costs its points**. There are no spell books, reagents or levels: any caster may
cast any letter of his school that he can pay for.

### 5.2 Magic points

Magic points (record 19h, BCD) start at 0 and come back only through `PARTY.ASM:PartyUpkeep`
(@6FDF; every turn on Sosaria, every 4th turn elsewhere). For each player who is up, by class:

| class | +1 when | so the limit is |
|---|---|---|
| Wizard | MP < Int | Int |
| Cleric | MP < Wis | Wis |
| Lark, Alchemist | MP < Int/2 | Int/2 |
| Paladin, Illusionist | MP < Wis/2 | Wis/2 |
| Druid | MP < Int/2, then again MP < Wis/2 | max(Int/2, Wis/2), up to 2 a tick |
| Ranger | MP < Wis/2 and MP < Int/2 | min(Int/2, Wis/2) |
| Fighter, Thief, Barbarian | never | 0 |

The halves are BCD halvings rounded down (`HalveBcd` @7149: 99 → 49, 75 → 37). So **only Wizards and
Clerics can reach the 75 points of a P spell** (with Int or Wis ≥ 75); half-casters top out at 49
points, i.e. spell J (45). The limits apply to regeneration only: points above them (after a
Wisdom loss, or the Alcort refund) are kept.

### 5.3 Wizard spells

`ITEMS.ASM:WizardSpellCmds` (@594B); handlers in `MAGIC.ASM`.

| | spell | cost | where | effect |
|---|---|---|---|---|
| A | Repond | 0 | fight vs. Orcs (18h) only | once per fight, then half the time: each orc killed with 3/4 (191/256) chance |
| B | Mittar | 5 | fight | directed: `rnd(40) | 10h` = 16-31 or 48-55 damage (not 16-55) |
| C | Lorum | 10 | anywhere | light: `LightOn = 10` (dungeon turns) |
| D | Dor Acron | 15 | dungeon, not level 8 | one level down, random empty cell |
| E | Sur Acron | 20 | dungeon | one level up, random empty cell; from level 1 out to Sosaria |
| F | Fulgar | 25 | fight | directed: 75 damage |
| G | Dag Acron | 30 | Sosaria | teleport to a random cell (see 15.1: the terrain test is broken) |
| H | Mentar | 35 | fight | directed: 2 × Int (binary) damage |
| I | Dag Lorum | 40 | anywhere | light: `LightOn = 250` |
| J | Fal Divi | 45 | anywhere | opens the cleric menu: cast a cleric spell, paying its cost too |
| K | Noxum | 50 | fight | 75 damage to each foe with 3/4 chance |
| L | Decorp | 55 | fight | directed: kills (255 damage) |
| M | Altair | 60 | anywhere | Negate Time: `TimeStop = 10` |
| N | Dag Mentar | 65 | fight | 2 × Int damage to each foe with 3/4 chance |
| O | Necorp | 70 | fight | every live foe's hit points become 5 |
| P | (no name) | 75 | fight | the Zxkuqyb handler: each foe killed with 3/4 chance |

### 5.4 Cleric spells

`ITEMS.ASM:ClericSpellCmds` (@596B).

| | spell | cost | where | effect |
|---|---|---|---|---|
| A | Pontori | 0 | fight vs. Skeletons (19h) only | as Repond, against skeletons |
| B | Appar Unem | 5 | on a chest | 3/4 (191/256): open the chest the party stands on without its trap (gold and maybe an item, 6.8); 1/4: "Failed!"; no chest: "Not Here!", "Failed!" |
| C | Sanctu | 10 | anywhere | heal a chosen player `rnd(20) + 10` = 10-29 (capped at the maximum) |
| D | Luminae | 15 | anywhere | = Lorum (10 turns of light) |
| E | Rec Su | 20 | dungeon | = Sur Acron |
| F | Rec Du | 25 | dungeon | = Dor Acron |
| G | Lib Rec | 30 | dungeon | random empty cell on the same level |
| H | Alcort | 35 | anywhere | cure: a Poisoned player becomes Good; others "Failed!"; no player chosen: refund (15.1) |
| I | Sequitu | 40 | dungeon | out to Sosaria |
| J | Sominae | 45 | anywhere | = Dag Lorum (250 turns of light) |
| K | Sanctu Mani | 50 | anywhere | heal `rnd(80) + 20` = 20-99 |
| L | Vieda | 55 | not in a fight | the Peer-at-gem map (7.8, 8.6) |
| M | Excuun | 60 | fight | = Decorp: directed kill |
| N | Surmandum | 65 | not in a fight | a Dead player becomes Good with 191/256, else Ashes ("Failed!"); hit points stay 0 |
| O | Zxkuqyb | 70 | fight | each foe killed with 3/4 chance |
| P | Anju Sermani | 75 | not in a fight | an Ashes player becomes Good (hit points stay 0); the caster loses 5 Wisdom |

### 5.5 How the spells resolve

- **"Each foe with 3/4 chance"** (`HitAllMonsters` @5EAA): for each of the 8 slots, `rnd(0FFh) & 3 = 0`
  (65/256) spares it; otherwise a live foe flashes and takes the damage through `DamageFoe` (4.4),
  experience to the caster. Damage 0FFh always kills (except Lord British).
- **Directed spells** (`CastDirected` @5F2D): only in a fight; a direction (Esc: nothing, points
  gone); a `ShootLine` from the caster to the first foe in that line, through walls; none: "Failed!".
  Outside a fight: "Failed!".
- **Repond and Pontori** set `KillSpellUsed` before their coin flip, so each can be tried once a fight
  (by anyone); the flip is `rnd(0FFh) < 128` (129/256).
- **Teleports in a dungeon** (`DungeonTeleport` @5F7B) pick random cells until one is exactly 00.
- **Light**: `LightOn` counts dungeon turns; outside a dungeon it is not used (the torch and spells
  can be cast, `EnterDungeon` clears it).
- **Healing** (`HealPlayer` @5F0A, `AddHitPoints` @5D2B) asks "Heal whom?" and does not look at the
  status: it can "heal" a dead player's hit points.
- **Necorp** does not kill: it sets 5 hit points, so the foes must still be hit.
- In a fight the spells that act on foes use the combat arrays; Mentar and Dag Mentar read the
  intelligence of `CombatPlayer`, which is the caster during a fight.

### 5.6 Monster magic

Section 4.6, step 3: foes' "spells" are ordinary attacks at a random player slot, aimed only at
players whose status is exactly Good.

---

## 6. Inventory, equipment & economy

### 6.1 Items a player carries

All per player (record offsets, FORMATS.md 6): gold (BCD word, max 9999), food (BCD word + hundredths),
gems, keys, powders, torches (BCD bytes, max 99), counts of weapons 1-15 and armours 1-7 (BCD
bytes, max 99), the readied weapon and worn armour, marks and cards (bits of byte 0Eh).

| item | use |
|---|---|
| gem | P)eer: the whole-map view (7.8, 8.6) |
| key | U)nlock a locked door east or west of the party (7.9) |
| powder | N)egate time: creatures/foes stop for 10 turns/rounds |
| torch | I)gnite in a dungeon: 255 turns of light |
| marks | Force, Fire, Snake, Kings (13.1) |
| cards | Love, Sol, Moons, Death (13.2) |

### 6.2 Weapons

Prices from `TEXT.ASM:WeaponPrices` (@9E1F); buying and selling at the same price.

| # | key | weapon | price | damage bonus (3 × #) | missile | classes |
|---|---|---|---|---|---|---|
| 0 | A | Hand | - | 0 | | all |
| 1 | B | Dagger | 5 | 3 | thrown if no foe adjacent | all |
| 2 | C | Mace | 30 | 6 | | all but W, A |
| 3 | D | Sling | 60 | 9 | yes | F P B L T R |
| 4 | E | Axe | 125 | 12 | | F P B L T R |
| 5 | F | Bow | 350 | 15 | yes | F P B L T R |
| 6 | G | Sword | 200 | 18 | | F P B L T R |
| 7 | H | 2-H-Swd | 250 | 21 | | F P B L R |
| 8 | I | +2 Axe | 400 (Dawn) | 24 | | F P B L R |
| 9 | J | +2 Bow | 1050 (Dawn) | 27 | yes | F P B L R |
| 10 | K | +2 Swd | 800 (Dawn) | 30 | | F P B L R |
| 11 | L | Gloves | 1200 (Dawn) | 33 | | F P B L |
| 12 | M | +4 Axe | 2700 (Dawn) | 36 | | F P B L |
| 13 | N | +4 Bow | 6550 (Dawn) | 39 | yes | F P B L |
| 14 | O | +4 Swd | 4550 (Dawn) | 42 | | F P B L |
| 15 | P | Exotic | not sold (Dig) | 45 | | all |

R)eady (`EQUIP.ASM:ReadyWeapon` @7E48) shows 10, 17 or 18 menu entries depending on the party flags
`ExtraWeaponsOk` and `ExoticWeaponFound` (6.5); a key at or beyond the class's `MaxWeaponTbl` entry is
"Not allowed!" (Exotic always allowed); a weapon not owned is "None owned". The two-handed sword is
as fast as a dagger: there is no speed or two-hand rule.

### 6.3 Armour

`TEXT.ASM:ArmourPrices` (@9ED3).

| # | key | armour | price | foe hit chance | classes |
|---|---|---|---|---|---|
| 0 | A | Skin | - | 50.0 % | all |
| 1 | B | Cloth | 75 | 47.3 % | all |
| 2 | C | Leather | 195 | 45.3 % | F C T P B I R |
| 3 | D | Chain | 575 | 43.8 % | F C P R |
| 4 | E | Plate | 2500 | 40.6 % | F P R |
| 5 | F | +2 Chain | 6130 (Dawn) | 39.1 % | F R |
| 6 | G | +2 Plate | 8250 (Dawn) | 37.5 % | F R |
| 7 | H | Exotic | not sold (Dig) | 35.5 %; the only protection in Castle Exodus | all |

Armour never reduces damage; it only turns blows aside, and not by much (4.6).

### 6.4 Shops: how a counter is chosen

T)ransact (`EQUIP.ASM:CmdTransact` @7FC6): a player and a direction. If no creature is in the
adjacent cell, that cell must be a counter (map byte 94h-E4h: a wall or sign letter) **with a
Merchant tile (40h) right behind it**; then the service is **`ShopCmds[party's y & 7]`**
(`ACTIONS.ASM:ShopCmds` @77CE): 0 Pub, 1 Grocer, 2 Temple, 3 Weapons, 4 Armour, 5 Guild, 6 Radrion
(the oracle), 7 Horses — **except that facing west always gives the Equine Emporium** (@8012). The
towns' counters are laid out so that each lands on its service **[data]**:

| town (file, entrance) | services found |
|---|---|
| Castle British (BRITISH, (45, 18)) | Temple, Radrion |
| Britain? (LCB, (46, 19)) | Pub, Weapons, Armour, Grocer |
| Moon (MOON, (6, 13)) | Pub, Grocer, Temple |
| Yew (YEW, (34, 16)) | Temple, Grocer |
| Montor East (MONTOR_E, (49, 58)) | Weapons ×2, Armour ×2, Pub |
| Montor West (MONTOR_W, (47, 58)) | Armour, Weapons, Grocer |
| Grey (GREY, (7, 44)) | Guild, Pub, Grocer, Weapons, Armour |
| Dawn (DAWN, (37, 53)) | Weapons, Armour, Guild, Horses ×2, Grocer, Temple, Radrion, Pub |
| Devil Guard (DEVIL, (18, 31)) | Horses, Pub, Grocer, Temple, Guild |
| Fawn (FAWN, (30, 2)) | Guild, Pub, Temple, Grocer |
| Death Gulch (DEATH, (56, 31)) | Weapons, Pub, Grocer, Armour |

(Found by placing the party two cells from each merchant across a counter on a walkable cell; the
name "Britain" for LCB is a guess.) The paying player is the one who transacts.

### 6.5 Weapons and armour shops

`TOWNS.ASM:ShopWeapons` (@A8A5), `ShopArmour` (@AA25): "List?" then Buy/Sell until Q or Esc.

- **Normal shops** sell weapons B-H (Dagger to 2-H-Swd) and armour B-E (Cloth to Plate).
- **Dawn** (recognised by the saved entrance x = 25h) sells the +2 and +4 goods too, **but only
  after its price list has been shown** ("List? Y"), which sets the party flags `ExtraWeaponsOk` /
  `ExtraArmoursOk` for good; the Dig of the Exotics sets them too. The flags only open the Dawn
  menus and the longer R)eady/W)ear/H)and menus: other towns still sell B-H / B-E only.
- **Buying**: one at a time, price `Prices[n]` (BCD), "No more room!" at 99.
- **Selling**: **the full price back**, refused if the gold would pass 9999 ("Too much gold!"), and
  **the readied weapon becomes Hand (or the armour Skin) whatever was sold** (@A949, @AAC9). The
  Exotics cannot be sold.

Since buying and selling prices are equal, weapons and armour from chests (6.8) are a gold source.

### 6.6 Other services

| service | routine | price | effect |
|---|---|---|---|
| Pub | `ShopPub` @A5AC | pay `n` ≥ 7 g.p., strictly less than all your gold | a tip `PubTips[tens digit of n]`; "Another?" |
| Grocer | `ShopGrocer` @A630 | 1 g.p. a ration | up to 4 digits; refused above the gold or past 9999 food |
| Temple: Curing | `TempleCure` @A6D4 | 100 | Poisoned → Good; Good: "Not injured!"; Dead/Ashes: "Failed!" (unpaid) |
| Temple: Healing | `TempleHeal` @A761 | 200 | hit points := maximum; charged even at full health; status ignored (a dead player is "healed", still dead) |
| Temple: Resurrection | `TempleResurrect` @A7B6 | 500 | Dead → Good, hit points unchanged (0); Good "Not injured!", Poisoned "Not dead!", Ashes "Failed!" (unpaid) |
| Temple: Recalling | `TempleRecall` @A833 | 900 | Ashes → Good (hit points 0); Good "Not injured!", others "Not ashes!" |
| Guild | `ShopGuild` @AB93 | gems 75, keys 50, powders 90, torches 6 | 2-digit count; refused past 99 owned or above the gold |
| Radrion | `ShopRadrion` @ACFC | `n` × 100 g.p. | verse `n` (0-9; 0 is free; 10+ reads past the table, 15.1) |
| Equine Emporium | `ShopHorses` @AD70 | 200 × party size | the party rides a horse (`PartyTile` 0Ah), even inside the town |

The temple asks the payer first ("Wilt thou pay?") and checks his gold before asking for the
patient. The pub's tips **[data]**, by the tens digit paid: 7-9 "Thank you kindly!"; 10-19 Ambrosia;
20-29 Dawn, the city of myths & magic; 30-39 "The conjunction of the moons finds link!"; 40-49 nasty
creatures, nasty dark; 50-59 "None return ... from the pool"; 60-69 shrines of knowledge and
strength; 70-79 fountains fair & foul in dungeons; 80-89 "EXODUS: Ultima III, which is next?";
90-99 "Seek ye out the Lord of Time". Radrion's ten verses (by hundreds offered) are one rhyme about
four marks used in Devil Guard, four shrines, four cards (Sol, Moon, Death, Love), the Montors and the
Lord of Time in the dungeons.

### 6.7 Gold and food sources

- **Start**: 150 gold and 150 food per character.
- **Chests** (6.8): 12-63 gold each.
- **Steal** (9.3): a chest behind a shop counter, the same chest contents.
- **Selling** weapons and armour at full price.
- **Join gold** (10.2) and **Hand** (10.3) only move gold between players.
- Food comes only from grocers; it is lost to gremlins (8.5) and eaten by the upkeep (11.1).

### 6.8 Chests and traps

**Where chests are**: on the surface and in towns a chest is a map byte 24h-27h (its low bits keep the
ground under it); every creature fought on the map leaves one (4.1); towns contain fixed chests
**[data]** (e.g. 67 in Death Gulch, 21 in Castle British); towns are reloaded on every visit, so
their chests refill **(inferred)**. In dungeons a chest is cell 40h (8.5).

**G)et chest** (`DUNMOVE.ASM:CmdGetChest` @8190, surface and dungeon tables): a player who is up,
standing on the chest. The chest goes (the ground comes back), then:

- **Trap** with `rnd(0FFh) ≥ 128` (127/256). Its kind: two random bytes `a`, `d`; if `a & d & 3 =
  0` acid (56.8 %), else `a = 1` poison (0.2 %), `a = 2` gas (0.2 %), else bomb (42.8 %): the code tests
  the whole byte `a` instead of the masked one (FINDINGS: "about 1 in 256"; it is about 1 in 515 each).
  Each trap allows a `DexRoll` (below) to evade ("Trap evaded!"):
  - acid: the opener loses `rnd(0FFh) & 37h` hit points (BCD, 0-37, average 18); if `a` was 0 the
    trap is silently evaded (15.1);
  - poison: the opener becomes Poisoned;
  - gas: every player who is up becomes Poisoned;
  - bomb: `DamageParty` (8.5).
- **Contents** (`EQUIP.ASM:ChestLoot` @80D9), always, trap or not: **gold** `(rnd(100) | 30h)`, minus
  100 if ≥ 100: 48-55 (12/256 each) and 56-63 (11/256 each), 71.9 % in all; 12-15 (6/256 each) and 16-27 (4/256
  each), 28.1 %; average 45. Then with
  `rnd(0FFh) < 64` (65/256) an item: weapon `(r1 & r2) & 7` (r1 < 128) — Dagger, Mace, Axe 7.0 % each,
  Sling, Bow, Sword 2.3 %, 2-H-Swd 0.8 % of item rolls — or, failing that, armour `(r3 & r4) & 3` —
  Cloth, Leather 6.7 %, Chain 2.2 % — or nothing (55.8 % of item rolls). Counts are capped at 99.

**DexRoll** (`ITEMS.ASM:DexRoll` @5B85): success when `rnd(0FFh) < Dex + bonus`, Dex in binary, bonus
+128 Thief, +64 Barbarian, Illusionist, Ranger, 0 otherwise. Chance ≈ (Dex + bonus + 1)/256.

---

## 7. World structure & travel

### 7.1 Maps

| map | file | size | wraps | saved |
|---|---|---|---|---|
| Sosaria | SOSARIA.ULT | 64 × 64 | yes | yes (whole file incl. creatures, whirlpool, moons) |
| Ambrosia | AMBROSIA.ULT | 64 × 64 | yes | **no**: reloaded from the shipped file every visit |
| 10 townes, 2 castles | BRITISH, LCB, MOON, YEW, MONTOR_E, MONTOR_W, GREY, DAWN, DEVIL, FAWN, DEATH, EXODUS (.ULT) | 64 × 64 | no (outside shows grass) | **no** |
| 7 dungeons | DARDIN, FIRE, MINE, PERINIAN, TIME, M, P (.ULT) | 8 × 16 × 16 | each level wraps | **no** |

The entrances (`EXDATA.ASM:MapPosTbl` @16E1) **[data]**: Castle British (45, 18), Castle Exodus
(10, 53), LCB (46, 19), Moon (6, 13), Yew (34, 16), Montor East (49, 58), Montor West (47, 58),
Grey (7, 44), Dawn (37, 53), Devil Guard (18, 31), Fawn (30, 2), Death Gulch (56, 31); dungeons
M (19, 57), Fire (49, 34), Time (58, 30), P (58, 44), Perinian (56, 6), Mines of Morinia (9, 28),
Dardin's Pit (46, 7).

### 7.2 Terrain and movement

`PARTY.ASM:CheckTerrain` (@7254) judges the target cell (from the view built last turn):

- **Frigate**: water and whirlpool only, and `AgainstWind` (@7233) refuses **every move in a calm
  and any move in the direction the wind is named after** (a "North Wind" blocks sailing north).
- **On foot or horseback**: grass, brush, forest, dungeon, towne, castle, floor, chest, horse,
  frigate (shapes 1-11 except 4), moon gates and shrines. Water, mountains and everything from
  shape 12 up (whirlpool, creatures, walls, signs, counters, ...) are refused.
- **Force field** (shape 32): the screen flashes; if every party member (the first `PartySize`
  records, **dead or not**) has the **Mark of Force** the party passes; otherwise the **first one
  without it takes 99 hit points** (BCD) and the party is stopped. The damage ignores status, so an
  Ashes player hit by it becomes Dead (11.4).
- **Lava** (shape 33): every player who is up and lacks the **Mark of Fire** takes 50; the party
  passes.

A refused move: "Invalid Move!" (and still a turn). Coordinates wrap at 64 on every map; in towns the
wrap takes the party to x or y = 0, which leaves the town (7.3).

### 7.3 Entering and leaving

E)nter (`LOOP.ASM:CmdEnter` @1D69):

- **Sosaria**: the party's position must be one of the 19 entrances, and the tile there decides
  (so Dawn's entrance works only while the Towne is there): dungeon → level 1 at (1, 1) facing east,
  no light; towne → (1, 32), the west edge; castle → (32, 62), the south edge, and the cards-inserted
  counter is reset. "Please wait...", **SOSARIA.ULT and PARTY.ULT are saved** (the entrance is kept
  in `PartyXY`), and the map file is loaded, the moon phases kept.
- **Ambrosia**: E)nter on a shrine (3.3).
- Elsewhere: "<-What?".

**Leaving a town or castle**: reaching x = 0 or y = 0 (moving off any edge, since coordinates wrap)
runs `ExitToSosaria` (@6458): Sosaria is reloaded from the file saved at entry and the party is put
back on the entrance cell, in whatever vehicle it now has (a horse bought in town stays). The town is
forgotten: chests, killed or bribed people, unlocked doors and hostile guards are all reset on the
next visit **(inferred:** no code saves a town map**)**. Dungeons are left by Klimb on level 1, Sur
Acron/Rec Su from level 1, or Sequitu (8.2).

### 7.4 Horses and frigates

- **B)oard** (`CmdBoard` @1D01), on foot, on a horse (map 28h) or frigate (2Ch): the craft leaves the
  map (grass or water stays) and becomes the party's tile. **There is no horse to mount in
  Ambrosia** ("<-What?"; it also cancels Negate Time).
- **X)-it** (`CmdXit` @2035): only on water or grass (map byte ≤ 4); the craft is put on the map and the
  party is on foot. Leaving a frigate on open water leaves the party standing on water on foot; it
  can step onto land or board again **(inferred)**. In town floors (20h) a bought horse cannot be left
  ("Not Here!").
- Horses come from the Equine Emporium (6.6) and from horse tiles on maps; frigates from the map, and
  from pirate ships defeated from land (4.1).
- Both halve the creatures' speed (1.2); the frigate fires cannons (4.14).

### 7.5 The whirlpool and the wind

**The whirlpool** (state at SOSARIA.ULT 1220-1223: x, y, dx, dy; it starts at (5, 58) **[data]**):
`PARTY.ASM:MoveWhirlpool` (@7347) is called **on every keyboard poll while the game waits for a
command** (`ReadCommand` @1B93), and acts on every 4th call, on Sosaria only: with `rnd(8) = 0` or when
the next cell is neither water nor a frigate, it picks a new direction among 8; onto water it moves;
onto a **frigate** it destroys it ("A ship was Destroyed!", the cell becomes the whirlpool); reaching
the party it swallows it. **Its speed therefore depends on the CPU and on how long the player waits
(FINDINGS).**

**Swallowed** (`WORLD.ASM:Whirlpool` @2168; also when a frigate sails into it): on Sosaria the frigate
is lost (water), the whirlpool restarts at x 3, `y = rnd(55) + 7`, the world is saved, AMBROSIA.ULT is
loaded and the party wakes **on foot at (32, 54)**, Location FFh. In Ambrosia (a frigate on its
whirlpool at (32, 58) **[data]**): "All is Dark!", SOSARIA.ULT is reloaded and the party is back at the
place it was swallowed, **in a frigate**, Location 0.

**The wind** (`src/LIB.INC:WindUpdate`): every 25 calls (it is called from the idle animation on every
keyboard poll, not in a dungeon, a fight or a shrine) a new direction: `rnd(9)` = 0 calm, 1-4 N/E/S/W,
5-8 one of N/E/S/W but different from the current one (else drawn again). From a blowing wind the next
is calm with 1/8, the same with 1/8, each other direction 1/4; from a calm, calm 1/9 and each direction
2/9 (exact for a uniform draw; the mod-9 bias shifts these slightly). The wind matters only to the
frigate (7.2).

### 7.6 Ambrosia

Reached only by the whirlpool. Its map is surrounded by mountains on all four edges **[data]**, so the
town-edge exit never triggers there **(inferred)**; the shipped map holds a whirlpool at (32, 58) and
16 hostile creatures, among them three pirate ships (35, 10), (18, 56), (43, 60) **[data]**. The only
way back is the whirlpool, which needs a frigate; fighting a pirate ship from land leaves its frigate
(4.1) **(inferred:** the intended exit**)**. In Ambrosia:

- no creatures spawn; the 16 creatures chase by their talk codes (all C0h) and reset on every visit;
- the moons do not advance; upkeep runs every 4th turn;
- foes hit 30 harder (`SavedLocation` FFh & 3 = 3, 4.6);
- the four shrines raise attributes (3.3) and give the cards (13.2);
- Quit & Save is refused ("Only on surface!").

### 7.7 Dawn

The tenth towne exists only while both moons line up (1.3). Its shops alone sell the +2/+4 goods
(6.5); its people hint at the Dig **[data]** ("<Dig> on isles", "<Dig> up Exotics").

### 7.8 Peer at a gem

P)eer (`LOOP.ASM:CmdPeer` @1EFD): one gem; on the surface or in a town `VIEW.ASM:ShowGemMap` (@259E)
draws the whole 64 × 64 map at 2 × 2 pixels (water black; grass, brush, forest, mountains, floor, walls
and "other" in different dot patterns) with the party blinking, until a key. In a dungeon: 8.6.

### 7.9 Locked doors

U)nlock (`CmdUnlock` @1FD6) works **only east or west** of the party (a north or south door: "Not
Here!"); the door is map byte B8h (the sign shape "I"); a player gives one key and the door becomes the
tile the party stands on. Towns hold locked doors **[data]** (12 in Castle British, 10 in Castle Exodus).

---

## 8. Dungeons

### 8.1 Layout

A dungeon file holds 8 levels of 16 × 16 cells and a message per level (FORMATS.md 4). Cell values:

| cell | meaning |
|---|---|
| 00 | floor (encounters happen only here) |
| 80 | wall |
| A0 | secret door: drawn as wall, walkable forwards |
| C0 | door: walkable forwards |
| 10 / 20 / 30 | ladder up / down / both |
| 40 | chest |
| 01-08 | events: 1 time vision, 2 fountain, 3 strange wind, 4 trap, 5 rod, 6 gremlins, 7 nothing, 8 misty writing |

Every level wraps at 16 in both directions (`CmdAdvance` @847D `and dx, 0F0Fh`). No level 8 in the
shipped files has a down ladder **[data]**, which matters because Descend has no lower bound (15.1).

### 8.2 Moving

The dungeon key table (`ACTIONS.ASM:DungeonKeys` @7708): Up = **Advance** (stopped only by exactly 80h,
so doors and secret doors are entered), Down = **Retreat** (stopped by anything ≥ 80h, i.e. walls and
both kinds of door), Left/Right = **turn** (refused while standing in a door cell, ≥ A0h), **K)limb**
(ladder-up bit 10h; from level 1 out to Sosaria), **D)escend** (ladder-down bit 20h, cell < 80h). The
other surface movement and travel commands answer "Not a DNG cmd!" — and still spend a turn
(`CmdNotDungeon` @8472 ends in `DungeonTurnEnd`). Facing: 0 north, 1 east, 2 south, 3 west.

### 8.3 A dungeon turn

`DUNMOVE.ASM:DungeonLoop` (@8327): `CheckAllOut`, "It's dark!" while no light burns, a 5-second wait
(no key = Pass). Every command ends in `DungeonTurnEnd` (@838D):

1. `MoveCount += PartySize`; `PartyUpkeep` (every 4th turn, 11.1).
2. If a light burns, `LightOn -= 1` (a torch lasts 255 turns, Lorum 10, Dag Lorum 250).
3. The level header ("LVL:0n", "Head-<facing>") and the 3D view (8.7).
4. On a floor cell (00): a possible **encounter** (8.4). On an event cell 1-8 (not 7): the event (8.5);
   events end the turn directly. Note that the party does not move by itself: a Pass on a fountain or
   rod cell triggers it again.

**Without light the view is blank but movement, combat and events work as usual**: light is purely
visual. The strange wind puts the light out.

### 8.4 Encounters

On a floor cell, `rnd(82h + L) ≥ 128` where L = level − 1 (0-7): **(L + 2)/256**, i.e. **0.8 % on level
1 rising to 3.5 % on level 8** per turn (the comment's (L+2)/(L+130) assumes a uniform draw). The kind is
`18h + min(rnd(L + 2), 6)`:

| level | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| kinds (about equal shares) | Orc, Skeleton | + Giant | + Daemon | + Pincher | + Dragon | + Balron | all; Balron 2/8 | all; Balron 3/9 |

The party's cell becomes a chest (40h) *before* the fight, so a victory leaves a chest; 1-8 foes, combat
map C, and every foe hit costs 10 more (4.6). Dungeon monsters do not exist on the map between
encounters: there is no wandering or visible monster in the dungeon.

### 8.5 Events

`DUNEVENT.ASM`, dispatched through `ACTIONS.ASM:DungeonEventCmds` (@76F8):

| cell | event | routine | effect | cell after |
|---|---|---|---|---|
| 1 | Time vision | `EventTimeVision` @941E | TIME.IMG and the Time Lord: "The one way is Love, Sol, Moons & Death, all else fails." | cleared |
| 2 | Fountain | `EventFountain` @9457 | any number of players drink until Esc; effect by the fountain's **x & 3**: 0 poison, 1 heal to maximum, 2 lose 25 HP, 3 cure poison; "Can't!" for a player who is not up | stays |
| 3 | Strange wind | `EventWind` @9517 | the light goes out | stays |
| 4 | Trap | `EventTrap` @9529 | **only player 1's** `DexRoll` (also when he is dead): "Evaded!!", else `DamageParty` | cleared |
| 5 | Red hot rod | `EventRod` @9550 | the chosen player gets **mark 1 << (4 + (x & 3))** (x&3: 0 Force, 1 Fire, 2 Snake, 3 Kings) and loses 50 HP; no status check | stays |
| 6 | Gremlins | `EventGremlins` @95B3 | a random member (`rnd(PartySize)`), if up, loses 100 food; under 100: food 0, "Starving!", 5 HP | cleared |
| 7 | - | | nothing | |
| 8 | Misty writing | `EventWriting` @960D | the level's message | cleared |

**`DamageParty`** (`DUNMOVE.ASM` @82C6), for the trap cell, the bomb trap and surface fire: every player
who is up loses `rnd(0FFh) & 77h` (BCD, 0-77, average 38) and then `(L + 1) × 8` **computed in binary but
subtracted as BCD**: levels 1-8 cost 8, 10, 18, 20, 28, 30, 38, 40 more (not 8-64 as the comment says).
On the surface the level variable is 0 (exits reset it), so the extra is 8.

**Marks and fountains [data]**: the rods sit on the bottom levels: Force in Fire L8 (4, 10) and M L8
(8, 9); Fire in Fire L8 (5, 14), Mines L8 (13, 15), Perinian L8 (5, 5); Snake only in P L8 (6, 15);
Kings in most dungeons (e.g. Dardin L2 (11, 3), Time L2 (7, 7), Mines L3 (3, 5), Perinian L1 (15, 11)).
The only time vision is Time L8 (1, 1). Every dungeon has fountains of all four kinds; their x & 3
decides the effect (e.g. Dardin L3 (13, 13) heals).

### 8.6 Peer at a gem in a dungeon

`VIEW.ASM:ShowDungeonMap` (@290B): the current level as a 16 × 16 character map: doors (C0h), **secret
doors (A0h)**, walls, the three ladder kinds and floor each have their own character; chests and events
show as "?"; a blinking "*" is the party. A gem therefore reveals secret doors. The Vieda spell shows the
same.

### 8.7 The 3D view

DUNGEON.DAT is a code overlay (FORMATS.md 8; `src/dungeon/DUNGEON.ASM:DrawDungeonView`) called by
`DUNEVENT.ASM:DrawDungeon` (@9630) only while a light burns: up to 3 cells ahead, walls and doors (secret
doors drawn as walls), ladders and chests up to 2 cells away; standing in a door shows only straight
ahead. It draws; it decides nothing.

### 8.8 Treasure

Dungeon chests (cell 40h) are opened with G)et chest like surface chests, traps included (6.8), and
leave a floor cell. The dungeons hold 0-54 chests per level **[data]** (M L8 54, Perinian L7 36, Time
L3 34); encounters add one each. They refill on the next visit (the file is reloaded).

---

## 9. NPCs & conversation

### 9.1 Talking

T)ransact at a creature (`EQUIP.ASM:CmdTransact` @803A): Lord British → 3.2. Otherwise by the creature's
talk code (`MonTalk`): exactly C0h → "Eat Death Scum!"; low 6 bits 0 → "Good day!"; n → speech n of the
map's speech table (MapText, up to 8 per town, FORMATS.md 3). There are no keywords, no names, no
questions: each person has one line **[data]**. The lines carry the game's clues (e.g. "<Bribe>
guards! They will leave!", "<Dig> up Exotics", "<Pray> in the Circle of Light!", "<Insert> cards into
pannels!", "Exodus lies beyond the Silver Snake!", "Seek the Jester in castle Fire!").

### 9.2 Creature modes in towns

Talk code bits 7-6 (FORMATS.md 3; 4.10): 0 stands, 1 wanders, 2 approaches (most merchants), 3 hostile.
Every town also holds hostile mode-3 creatures from the start in some places **[data]** (Castle British
has a thief, balron, pincher and daemon in a cell block; Castle Exodus is full of them).

### 9.3 Stealing

S)teal (`LOOP.ASM:CmdSteal` @1F53): a player who is up and a direction. If his `DexRoll` (6.8) succeeds
**and** the adjacent cell is a counter (94h-E4h) **and** two cells away is a chest (24h), the chest
becomes floor and he gets its contents (`ChestLoot`: gold and maybe an item, no trap). Any failure
(roll, wrong cell, no chest) is "Failed!", except that with `rnd(0FFh) & 3 = 0` (65/256) **"Watch
out!": every guard on the map turns hostile** (C0h).

### 9.4 Guards and Lord British

- Guards (shape 18) are normal creatures; their hostility comes from S)teal failures and from any fight
  in the town (4.1). Each fight with a guard is against 8 guards (15-239 HP, 15 exp each, hitting for up
  to 30 + max-HP-hundreds + 20/30).
- **Bribe** (Other BRIBE, `ACTIONS.ASM:CmdBribe` @75A9): a direction; a guard there takes **100 gold**
  from the player and vanishes (his cell gets back what was under him); not a guard: "No effect!"; less
  than 100 gold: "Not enough gold!". It works on hostile guards too.
- Lord British: talking raises maximum hit points (3.2); fighting him is fatal (4.11).

### 9.5 Other words

O)ther (`ACTIONS.ASM:CmdOther` @74D5) asks a word: INSERT, DIG, SEARCH, BRIBE, PRAY (`SHRINE.ASM:OtherWords`
@6540; "SCORE" follows PRAY in memory but is not in the list). Y)ell asks a word too (only EVOCARE does
anything). Both are case-insensitive and allow spaces around the word (`PARTY.ASM:MatchWord` @7423).

- **PRAY** (`CmdPray` @7580): only in the towne entered from x = 22h (Yew) at (48, 48): "Yell 'Evocare'".
  Elsewhere "No effect!".
- DIG, SEARCH, INSERT: section 13.

### 9.6 Special inhabitants [data]

- **Castle Exodus** has, besides dragons, balrons, pinchers, daemons, a serpent and a man-o-war (all
  hostile), **six hostile creatures whose tile is Floor (4), Grass (2) or a Chest (2)**: invisible or
  disguised monsters that chase the party. Fought, they use the stat rows 8, 1 and 9 of 4.7 (Orc, Jester,
  Skeleton) and print as "Floor", "Grass", "Chest"; the combat code has special cases for their names
  and the Floor creature's map (4.1, 4.12).
- Ambrosia's 16 creatures include a hostile Jester and two hostile Horses (fought with the Giant row).
- Devil Guard has wandering Horse creatures.
- Castle British's jester at (48, 50) says "West 8, South 35 and await Dawn!" (from Castle British's
  entrance at (45, 18), x − 8 = 37, y + 35 = 53: Dawn's cell). Lord British's own talk code points at the
  same line, but he never uses it.

---

## 10. Party

### 10.1 Size and order

One to four characters, formed in BOOTUP (10.4). Party order matters for: combat turn order (4.3); foes'
tie-breaking and which adjacent player is attacked first (4.6); the force field (the first player without
the Mark of Force is burnt, 7.2); the dungeon trap cell (only player 1 rolls, 8.5); the starting combat
positions. M)odify order (`LOOP.ASM:CmdModify` @1E9B) swaps two players' records and their roster
numbers; on Sosaria it also advances the moons one step (1.3).

There is no "active member": every command asks which player acts (`AskPlayer` @6C76: 1-4, Esc or 0 =
nobody; an empty slot is "No one there!"). The party shares one position and one vehicle.

### 10.2 Join gold

J)oin gold (`ITEMS.ASM:CmdJoinGold` @5C73): the sum of the gold of the first `PartySize` players goes to
the chosen one; a sum over 9999 is refused ("No more room!"). **All four records' gold is cleared**, even
beyond the party size (FINDINGS).

### 10.3 Hand equipment

H)and (`HAND.ASM:HandEquip` @7B54): from one player to another (not the same): Food or Gold (up to 4
digits; whole food units only, the hundredths stay), Equipment (gems, keys, powders, torches, up to 2
digits), Weapons, Armour (a kind and a count). Refused: more than the giver has ("Not enough!"), more than
99 for the receiver or 9999 gold/food ("No more room!"), the giver's readied weapon or worn armour ("In
use!"). Hand and Skin cannot be given ("<-What?", 15.1).

### 10.4 Forming and dispersing

- **Form the Party** (`src/bootup/ORGANIZE.ASM:FormParty` @1792): only when no party exists; up to four
  roster numbers (0 ends the list); a number over 20, an empty slot or a repeat cancels the whole
  selection. The members' roster records are marked "in party" (+10h = FFh) and copied into PARTY.ULT;
  the party starts **on foot on Sosaria at (44, 20)**, next to Castle British. Only those four header
  fields are set: the move counter, the Exotic and Dawn flags kept in PARTY.ULT's header survive from the
  previous party, and SOSARIA.ULT (creatures, whirlpool, moons) is never reset **(inferred)**.
- **Disperse** (`DisperseParty` @18DF): the party's records are copied back to their roster slots, the
  flags cleared, PARTY.ULT's four records zeroed. This is the only moment the roster learns what happened
  in the game.
- The "(No Active Players)" test of Form runs on the old (zeroed) records, so it never refuses; a party of
  dead characters can be formed and is then refused by Journey Onward (FINDINGS) (15.1).

### 10.5 Shared and individual resources

Everything is individual: gold, food, items, equipment, marks, cards. Shops charge the transacting player,
the temple the payer it asks first; the horse price counts the whole party. The checks for the marks are
per player (Force: every member; Fire: each member separately; Snake: the yelling player; Kings: the
player at Lord British; cards: the inserting player, 13).

---

## 11. Survival: food, HP, healing, poison/status, death, ashes & resurrection

### 11.1 The upkeep: food, poison, regeneration

`PARTY.ASM:PartyUpkeep` (@6FDF) is called once per turn by the main loop, once per dungeon turn and once
per combat round. **On Sosaria it acts every call; anywhere else (towns, castles, Ambrosia, dungeons,
fights) only every 4th call** (`UpkeepTick`). When it acts, for each player who is up (Good or Poisoned),
from player 4 to player 1:

1. **Magic points** +1 by class (5.2).
2. **Food −0.10** (`SpendFood` @70E4, BCD with hundredths). If the food runs out: food 0, "Starving!",
   **5 hit points** lost, every time the upkeep acts.
3. **Poisoned: −1 hit point**, "Poisoned!" (it can kill).
4. Every **10th** time the upkeep acts (`RegenTick` 9 → 0): **+1 hit point** up to the maximum.

So a player eats 1 food every 10 surface turns, or every 40 turns elsewhere, and regenerates 1 hit point
every 10 surface turns (40 elsewhere). Dead and ashen players eat nothing.

### 11.2 Hit points and damage

All damage goes through `PARTY.ASM:HurtPlayer` (@6BC9): a BCD subtraction of a byte (at most 99 at a time;
bigger amounts are applied in steps by the callers). **Only a borrow below 0 kills: exactly 0 hit points is
alive.** Death sets status 'D', hit points 0, and saves the game (11.5).

| source | damage |
|---|---|
| foe blow, breath, spell | 4.6 |
| force field | 99 (first member without the Mark of Force) |
| lava | 50 per member without the Mark of Fire |
| starving | 5 per upkeep |
| poison | 1 per upkeep |
| acid trap | 0-37 |
| bomb trap, trap cell, dragon/pirate fire on the map, Exodus castle fire | `(rnd & 77h)` + 8 ... 40 (8.5) |
| rod | 50 |
| bad fountain | 25 |
| gremlins | 5 if they leave the player without food |
| wrong card at Exodus | death (13.3) |

### 11.3 Healing

Regeneration (11.1), fountains (heal to maximum, cure), the temple (6.6), Sanctu (10-29), Sanctu Mani
(20-99), Alcort (cure). Lord British does not heal.

### 11.4 Status

| letter | status | can act | upkeep | notes |
|---|---|---|---|---|
| G | Good | yes | yes | the only status foes' magic can target |
| P | Poisoned | yes | yes, −1 HP | from Pinchers, Balrons, Man-O-Wars (65/256 a blow), poison and gas traps, poison fountains; cured by Alcort, temple (100), cure fountains |
| D | Dead | no | no | HP 0; resurrected by Surmandum (191/256, else Ashes) or the temple (500) |
| A | Ashes | no | no | only from a failed Surmandum; recalled by Anju Sermani or the temple (900) |

Raised players keep **0 hit points** and must be healed. Two odd paths: a force field or a rod touched by an
**Ashes** player makes him **Dead** (the damage borrows and `HurtPlayer` writes 'D'), which a temple then
resurrects for 500 instead of 900 **(inferred)**.

### 11.5 Death and the end

- A player's death saves the game (`SaveGame` @6B91): PARTY.ULT, and SOSARIA.ULT too when the party is on
  Sosaria (or fighting there). **PARTY.ULT always says Location 0**: after a restart the party is on
  Sosaria at `PartyXY` — the entrance of the town or dungeon it was in, or on the surface the position of the
  last town entry, Quit or whirlpool, not where it died **(inferred)**.
- **All four records out** (`CheckAllOut` @6C29, every turn and on every death in combat): "All Players Out!",
  save, and the program **hangs** (`Hang` @7252). The saved party has nobody alive, so Journey Onward refuses
  it; the player must disperse and form a party with a living character to carry the dead to a temple.

---

## 12. Random number generation

`src/LIB.INC:Random` (EXODUS @4601 region; the same code in all three programs):

- **State**: `RandState`, 16 bytes = one 128-bit number, byte 0 the most significant.
- **Step**: for i = 14 down to 0, `byte[i] = byte[i] + byte[i+1] + carry` (byte[i+1] already updated,
  the carry chained from the previous addition); then the whole 128-bit number is incremented by 1.
- **Output**: `DL = byte[0] mod DH`, by repeated subtraction (DH = 0 would loop for ever; no caller passes
  0). As stated in the conventions, this makes `rnd(n)` biased when n does not divide 256, and turns tests
  like "rnd(n) ≥ 128" into (n − 128)/256.
- **Seeding**: EXODUS's `StartUp` (@2554-2578) and ULTIMA seed the eight words from the DOS time (seconds
  and hundredths, hour and minute) and date (month and day, year), each twice. **BOOTUP never seeds it** (its
  state stays zero), but BOOTUP uses no random numbers for characters.
- **Uses**: everything random in this document: spawns, creature wandering, combat rolls, foe hit points and
  counts, spell success, chest contents and traps, the wind, the whirlpool, dungeon encounters, fire in
  Castle Exodus, noise in the sound routines.

Exact distributions used above: `rnd(0FFh) ≥ 128` 127/256; `rnd(0FFh) & 3 = 0` 65/256; `rnd(0FFh) < 64`
65/256; `rnd(87h) ≥ 128` 7/256; `rnd(0C0h) ≥ 128` 64/256; `rnd(82h+L) ≥ 128` (L+2)/256; `rnd(99)` gives 0-57
with 3/256 and 58-98 with 2/256.

---

## 13. Quest structure & endgame

### 13.1 The marks

Record byte 0Eh bits 7-4. All four come from the **red hot rods** in dungeons (8.5): touching one costs 50 hit
points and gives the mark of the rod's x & 3. Their uses:

| mark | bit | needed for | code |
|---|---|---|---|
| Force | 4 | passing force fields: **every** party member must have it, else the first without it takes 99 and the party is stopped | `CheckTerrain` @72C8 |
| Fire | 5 | crossing lava unhurt (each member without it takes 50, but the party passes) | `CheckTerrain` @730D |
| Snake | 6 | Yell EVOCARE at the Silver Snake | `CmdYell` @748F |
| Kings | 7 | Lord British's raises from 550 maximum hit points on | `CmdTransact` @8094 |

### 13.2 The cards and the Exotics

- **Cards** (bits 3-0: Love, Sol, Moons, Death): Other SEARCH (`ACTIONS.ASM:CmdSearch` @7607) while standing on a
  shrine (any shrine tile, i.e. Ambrosia's) gives the card `1 << (x & 3)`: (4, 36) Love, (45, 52) Sol, (6, 6)
  Moons, (55, 27) Death **[data]**. Each player can collect his own; searching again does nothing new.
- **Exotics**: Other DIG (`CmdDig` @7534) **on Sosaria** at **(33, 3)** (a brush cell) gives one Exotic weapon,
  at **(19, 44)** (grass) one Exotic armour **[data]**, to the digging player (count +1, max 99, repeatable), and
  sets the party flags that show them (and the Dawn goods) in the menus: "Exotics!".

### 13.3 Castle Exodus

- **Reaching it**: the castle is at (10, 53), north of the Silver Snake (snake tiles at (10, 57) and (10, 58),
  water at (10, 56) and (10, 59), mountains on both sides) **[data]**. Y)elling **EVOCARE** by a player with
  the Mark of the Snake, on Sosaria, at x = 10 and y = 56 or 59 (i.e. in a frigate) moves the party to the other
  side (`y XOR 3`) (`ACTIONS.ASM:CmdYell` @7458).
- **Inside** (`InExodusCastle`: Location 3 and the entrance x = 10): every turn Negate Time is cancelled and a
  random view cell is struck by fire (`rnd(11)` twice): on the party's cell (≈ 0.8 % a turn) `DamageParty` hits
  everyone; on floor it is harmless. Every fight has 8 foes; **only the Exotic weapon hits** and **only Exotic
  armour turns blows** (all others are always hit). The castle is a maze of floor, walls, 84 force fields, 304
  lava cells and 10 locked doors **[data]** (Marks of Force and Fire and keys are needed in practice).
- **Exodus** is four map cells of shape 31 at (30-33, 11) **[data]**, reached from the floor row below
  (y = 12). It is never fought.

### 13.4 The end: inserting the cards

Other INSERT (`ACTIONS.ASM:CmdInsert` @762F): a direction to an Exodus cell (map byte 7Ch; else "No effect!"),
then a card key M, D, L, S (Q or Esc cancels). With `n` = cards inserted so far (`CardsInserted`, reset on
entering any castle):

1. The player must own **card bit n** (Love, Sol, Moons, Death for n = 0-3); otherwise "No effect!". (The bit
   tested is that of the *position*, not of the key pressed.)
2. The target's x must be **30 + n** and the key must be **"LSMD"[n]**. Either wrong: **the player dies**
   (hit points 0, then 255 more).
3. Right: the panel flashes and becomes floor; on the fourth, `ENDING.ASM:EndGame` (@A4B9): "Congratulations!
   Thou hast compleated Exodus: Ultima 3 in <moves> moves. Report thy feat!", the closing text, a save, a key,
   and **the program hangs on purpose**. There is no other win condition and no score beyond the move count
   (a player-move count, 1.2).

So the order is left to right: **Love at x 30, Sol at 31, Moons at 32, Death at 33** — the Time Lord's "Love,
Sol, Moons & Death".

### 13.5 What the code makes necessary

A minimal winning party needs: a player with the Mark of the Snake (Yell); the cards Love, Sol, Moons, Death in
the hands of whoever inserts each (one player can hold all four); the Exotic weapon and armour for survival in
the castle's fights (not strictly needed if no fight happens); the Mark of Force on every member (force fields)
and in practice the Mark of Fire; a frigate to reach the Snake; keys. The Mark of Kings only matters for
growing beyond 550 hit points. Ambrosia must be visited for the cards (and the shrines); its exit needs a
pirate's frigate **(inferred)**.

---

## 14. Commands

Surface and town keys (`EXDATA.ASM:SurfaceKeys`/`SurfaceCmds` @1887/@190B); "D" marks those also in the
dungeon table, "C" the combat table. Every command costs a turn (1.2).

| key | command | effect |
|---|---|---|
| A | Attack (C) | fight the creature in an adjacent cell (4.1; combat 4.4) |
| B | Board | mount a horse / board a frigate on the party's cell (7.4) |
| C | Cast (D, C) | a spell (section 5) |
| D | Descend (D) | dungeon: down a ladder; surface: "<-What?" |
| E | Enter | a town, castle or dungeon on Sosaria; a shrine in Ambrosia (7.3, 3.3) |
| F | Fire | the frigate's cannons, 3 cells (4.14) |
| G | Get chest (D) | open a chest, traps and contents (6.8) |
| H | Hand equipment (D) | give food, gold, items, weapons, armour (10.3) |
| I | Ignite a torch (D) | dungeon only: a torch, 255 turns of light |
| J | Join gold (D) | all gold to one player (10.2) |
| K | Klimb (D) | dungeon: up a ladder, out from level 1; surface: "<-What?" |
| L | Look | the name of the shape in a direction |
| M | Modify order (D) | swap two players (10.1) |
| N | Negate time (D, C) | a powder: creatures stop 10 turns (foes 10 rounds) |
| O | Other (D) | a word: INSERT, DIG, SEARCH, BRIBE, PRAY (9.5, 13) |
| P | Peer at gem (D) | a gem: the map (7.8, 8.6) |
| Q | Quit & Save | Sosaria only: save SOSARIA.ULT and PARTY.ULT, print the moves; **play goes on** |
| R | Ready (D, C) | ready a weapon (6.2) |
| S | Steal | rob a shop chest (9.3) |
| T | Transact | talk, shops, Lord British (9.1, 6.4, 3.2) |
| U | Unlock | a locked door east or west, one key (7.9) |
| V | Volume (D, C) | sound on/off (also Alt-S, Alt-V) |
| W | Wear (D) | wear armour (6.3) |
| X | X-it | leave the horse or frigate, on grass or water (7.4) |
| Y | Yell (D) | a word; EVOCARE at the Snake (13.3) |
| Z | Ztats (D, C) | a player's full sheet, a line per key |
| Space | Pass (D, C) | nothing; also after ~5 seconds without a key |
| arrows | move | surface: one cell (7.2); dungeon: Advance, Retreat, turn (8.2); combat: one cell |

In the dungeon B A E F L Q T X S give "Not a DNG cmd!" (a turn). In combat the unlisted letters give "Not usable
cmd!" without spending the turn (4.2). Z)tats lists: name, Str, Dex, Int, Wis, hit points, then on Enter/Space/
Down (Esc stops) maximum hit points, gold, experience, gems, keys, powders, torches, marks and cards owned,
weapon readied, armour worn, and every weapon and armour owned with its menu letter.

---

## 15. Notable bugs, quirks, dead code & PC-port differences

### 15.1 Bugs and quirks (as the code runs)

- **Biased random tests** (12): the code's comments (and FINDINGS) quote 7/135 for spawns, (L+2)/(L+130) for
  dungeon encounters, 1/3 for foes' magic; the real chances are 7/256, (L+2)/256, 1/4, because `Random` takes the
  top byte mod n.
- **Chest traps** (`CmdGetChest` @81F5): the trap kind compares the whole random byte AL instead of the masked
  value: poison and gas traps come about 1 time in 515 each; and AL = 0 on the acid path makes the trap silently
  "evaded" (FINDINGS).
- **Attack damage** adds the BCD strength byte / 2 (rounded up) as if binary (FINDINGS).
- **DamageParty** adds `(level + 1) × 8` in binary to a BCD subtraction: 8, 10, 18, 20, 28, 30, 38, 40.
- **Mittar** deals `rnd(40) | 10h`: 16-31 or 48-55, never 32-47.
- **Lord British's cap** is on the hundreds byte: maximum hit points end at 2550, not 2500.
- **Fal Divi** charges its 45 points and then the cleric spell's cost (FINDINGS).
- **Alcort** with no player chosen adds 35 (BCD, wrapping past 99) to the record in BX: the caster after Esc or
  0, but an **empty slot's record** if an empty slot was picked (FINDINGS).
- **Anju Sermani** subtracts 5 from Wisdom without a check; below 5 the BCD would wrap to 98 (03 → 98), but no
  caster able to pay 75 points can have Wisdom under 75 (5.2).
- **Dag Acron** (`SpellDagAcron` @6034) passes a map byte (shape × 4) to `CheckTerrain`, which expects a shape
  number. On Sosaria's map bytes this means: on foot or horseback only brush (08, read as "floor") passes — grass
  (04) reads as mountains, forest (0C) and everything above as whirlpool-or-higher — so the spell always lands on
  brush; in a frigate water (00) and **forest** (0C, read as "whirlpool") pass, so a frigate can be teleported
  into a forest **(computed from the code, not tried; FINDINGS: unverified)**.
- **Descend has no lower limit**: a down ladder on level 8 would take the party to "level 9", past the map; no
  shipped level 8 has one **[data]**.
- **Radrion** with 10 or more hundreds indexes past his 10 verses (FINDINGS).
- **The shrine accepts hex digits** (3.3): `ReadNumber` returns AH = FFh for A-F but `EnterShrine` only looks at AL.
- **Join gold** clears all four records' gold (FINDINGS).
- **Form the Party**'s "No Active Players" test reads the old records (FINDINGS).
- **Error exits leave the stack**: `MsgWhat` and friends jump to `MainLoop` without resetting SP; H)and's "A"
  choice leaks 18 bytes each time (`HAND.ASM` @7D02), unchecked (FINDINGS).
- **`MoveWhirlpool`** reads the time with `int 15h` instead of `int 21h` (@73F2), so the key-wait deadline after a
  whirlpool takes the party is arbitrary (FINDINGS).
- **Lord British in combat** may step to an uninitialised DX (FINDINGS).
- **Foes' magic** picks a slot 0-3 regardless of party size (harmless: empty slots are not "Good").
- **Force field and rod** ignore status: an Ashes player becomes Dead (11.4).
- **Temple Healing** charges a player already at full health and heals the dead (FINDINGS).
- **Selling** any weapon unreadies the readied one (and any armour unwears) (FINDINGS).
- **Board in Ambrosia** cancels Negate Time.
- **Moon gates in castles** teleport within the castle map (1.3).
- **Modify order** advances the moons on Sosaria.
- **The Insert test** checks ownership of the card bit of the slot being filled, not of the key pressed.
- **An invalid key** in combat or anywhere spends the turn (FINDINGS); combat letters in the table do not.
- **"Unable to read/write file"** never shows the name and hangs (FINDINGS).
- BOOTUP's status key string is "GPDP" (a typo for "GPDA", harmless) (FINDINGS).

### 15.2 Dead code and data

The copy-protection disk check in all programs (patched out), BOOTUP's `AskScenarioDisk` (a `ret` written over its
first byte), "SCORE" after PRAY, "Oh well, maybe next time." and "No One There" (never pointed at), PayGold's
unreachable borrow branch, a stray `ret` at 6BF9, zero runs (FINDINGS). The Exodus row of the foe tables (index F)
and Lord British's speech number are never used. `KillSpellUsed` is the only per-fight state besides the arrays.

### 15.3 PC-port specifics evidenced by the code

- **Real-time passes**: the surface, dungeon and combat key loops each pass after about 5 seconds of DOS time.
- **Speed**: the wind, the whirlpool, the tile animation, step sounds and delays run at polling/CPU speed (`LIB.INC`
  Animate, `CheckTerrain` delay loops) (FINDINGS).
- **The 3D dungeon view is a separate code overlay**, DUNGEON.DAT, loaded over the map buffer.
- **Saving**: SOSARIA.ULT and PARTY.ULT only; towns, Ambrosia and dungeons are never saved; Quit continues the game.
- **Sex "Other"** exists as a third choice (no effect).
- Comparisons with the Apple II original are out of scope; nothing in the code refers to it. Where this document
  mentions the original (2.1) it is from the original's documentation, not from this code.

### 15.4 Heritage from Ultima II

The code shares U2's habits: packed BCD for every visible number, a 64 × 64 map with 32 creature slots, shops chosen
by position, one blow per turn. It departs in important ways: U3 regenerates hit points and magic points (U2 had
neither); Lord British raises maximum hit points for experience instead of selling hit points for gold; monster
damage is a ranged random number plus a location surcharge instead of U2's bit-subset of a running total; armour
lowers the foes' hit chance to 8/(16 + armour) instead of (8 − armour)/16; attributes are converted to binary for
most uses (U2 used BCD-as-binary throughout); foes die at exactly 0 hit points (U2's survived at 0); fights moved to a
separate tactical map with a party of four.

---

## 16. Open questions / unverified

1. **Uniformity of the generator's top byte**: every probability here assumes it; the additive 128-bit generator
   was not tested statistically.
2. **Dag Acron**: the computed landing rule (brush only on foot or horseback; water or forest in a frigate, 15.1)
   was not tried in play.
3. **Ambrosia's exit**: confirmed in code and data that the edges are mountains and the whirlpool needs a frigate,
   and that a pirate fought from land leaves a frigate; not tried in play (7.6).
4. **Moon gates inside Castle British and Castle Exodus**: where they lead in each castle map and whether that was
   intended (1.3).
5. **The shrine with hex digits**: the exact results of offerings such as "1F" (computed from DAS/DAA rules only).
6. **Restart position after a death on the surface**: inferred from `SaveGame` not updating `PartyXY` (11.5).
7. **Header persistence across parties**: the move count and the Exotic/Dawn flags surviving a Disperse/Form
   (10.4) follows from the code; not checked with a real save.
8. **Lord British fights**: that a hostile Lord British actually reaches and engages the party (his mode becomes 3,
   floor is walkable) and that nothing ends such a fight but death (4.11).
9. **Town and counter names**: "Britain" for LCB.ULT is a guess; the shop table in 6.4 comes from a geometric search
   of the maps (merchant behind a counter, a walkable cell for the party) and may miss or invent a counter.
10. **The wind's exact probabilities** under the mod-9 bias (7.5) were not computed.
11. **The level-8 down-ladder guard**: whether any player-made situation (e.g. a teleport onto a ladder) could still
    reach "level 9".
12. **PARTY.ULT header byte 01 and record bytes 0A-0D** are never read (FORMATS.md).
