# Map of the programs: modules and routines

Phase 5 of docs/PLAN.md split each program into modules named for the subsystem; phase 6 named
every label and commented every module (module headers, a header per routine). This page is the
overview; the sources say the rest. The cut addresses are `modules` in `tools/u3an.py`;
`tools/routines.py TARGET [FROM [TO]]` lists a range's routines (size, callers, dispatch entry,
strings) and `tools/modmap.py` prints the table below. A module's range is its place in the
original image; data sits where the original program had it (EXDATA, TEXT, CMDTAB, BDATA and
UDATA are mostly or only data). Names are looked up with `tools/syms.py SCOPE NAME|ADDR`.

## Modules

### ULTIMA.COM (`src/ultima/`)

| module | image range | bytes | what |
|---|---|---|---|
| UDATA.ASM | 0100-5CDD | 23517 | buffers, strings, tables |
| INTRO.ASM | 5CDD-6113 | 1078 | the title animation, sound and the chain load of BOOTUP.BIN |
| LIB.ASM | 6120-9054 | 12084 | the shared library (src/LIB.INC) |

### BOOTUP.BIN (`src/bootup/`)

| module | image range | bytes | what |
|---|---|---|---|
| BDATA.ASM | 0100-1209 | 4361 | tables, strings and the roster/party buffers |
| TITLE.ASM | 1209-14C9 | 704 | start-up and the scrolling title picture |
| ORGANIZE.ASM | 14C9-194B | 1154 | the party menu: look, form, disperse |
| CREATE.ASM | 194B-1E34 | 1257 | register, terminate, create a character, then load EXODUS.BIN |
| LIB.ASM | 1E40-4D74 | 12084 | the shared library (src/LIB.INC) |

### EXODUS.BIN (`src/exodus/`)

| module | image range | bytes | what |
|---|---|---|---|
| EXDATA.ASM | 0100-1BD5 | 6869 | map buffer, entry vector, tables and strings |
| LOOP.ASM | 1BD5-207D | 1192 | main loop and the surface commands |
| WORLD.ASM | 207D-259E | 1313 | moons, moon gates, creatures, start-up |
| VIEW.ASM | 259E-298E | 1008 | the map window and map access |
| LIB.ASM | 2990-58B4 | 12068 | the shared library (src/LIB.INC) |
| ITEMS.ASM | 58B4-5D83 | 1231 | chests, torches, negate time |
| MAGIC.ASM | 5D83-62FD | 1402 | casting and the spells |
| SHRINE.ASM | 62FD-6B91 | 2196 | stats header, shrines, leaving a dungeon |
| PARTY.ASM | 6B91-7458 | 2247 | names, status lines, hit points, food, poison |
| ACTIONS.ASM | 7458-7AEA | 1682 | Word, Cmd, Insert, Dig, Search, Bribe, Pray |
| HAND.ASM | 7AEA-7D1A | 560 | the H command (Hand Equipment) and its menus; AskDirection |
| EQUIP.ASM | 7D1A-8190 | 1142 | error exits, ready weapon, wear armour, Transact (T: talk, shops), gold |
| DUNMOVE.ASM | 8190-84DB | 843 | dungeon: traps, darkness, turning, advancing |
| CMDTAB.ASM | 84DB-888B | 944 | tables of the combat commands |
| COMBAT.ASM | 888B-941E | 2963 | fights |
| DUNEVENT.ASM | 941E-964F | 561 | dungeon events: fountains, the rod, gremlins |
| TEXT.ASM | 964F-A46F | 3616 | long messages, shop and verse text |
| ENDING.ASM | A46F-A5AC | 317 | the move count and the end of the game |
| TOWNS.ASM | A5AC-ADCA | 2078 | pub, grocer, temple, weapons, armour, guild, horses |

### DUNGEON.DAT (`src/dungeon/`)

| module | image range | bytes | what |
|---|---|---|---|
| DUNGEON.ASM | 0100-084A | 1866 |  |


## What is where

**EXODUS** (the game)

- **EXDATA**: the map buffer `MapBuf` (0100-1327; the creature arrays `MonTile`, `MonUnder`,
  `MonX`, `MonY`, `MonTalk`, the whirlpool and the moons at its end), the entry vector (1328),
  `ScreenRowTbl`, the party header and `Players`, `PlayerXY`, the file names, the command tables
  and strings, and at its end `ReadCommand` (1B77): draw the view, prompt, wait for a key (a pass
  after about 5 seconds), look the key up in `SurfaceKeys` and jump through `SurfaceCmds`.
- **LOOP**: `MainLoop` (1BD5) is the end of every turn: every command jumps there; it runs the
  per-turn work and goes back to `ReadCommand` (in a dungeon to `DungeonTurnEnd`). Then the surface
  command handlers: `CmdNorth` ... `CmdWest`, `CmdPass`, `CmdBoard`, `CmdXit`, `CmdEnter`,
  `CmdHand`, `CmdLook`, `CmdModify`, `CmdPeer`, `CmdQuit`, `CmdSteal`, `CmdUnlock`, `CmdVolume`,
  `CmdZtats`, `CmdCast` (the command table below).
- **WORLD**: `SaveSosaria`, `SaveParty`, `AdvanceMoons` (the moons, the moon gate and Dawn),
  `Whirlpool` (swallowed: Sosaria to Ambrosia and back), creatures: `MonCanEnter`, `SpawnMonster`,
  `MonShoot` (dragons and pirates fire), `MoveMonsters`; and `StartUp` (24C4), the start-up code
  that the view buffer and the combat file later overwrite (docs/FORMATS.md 9).
- **VIEW**: `ShowGemMap` (Peer at gem), `PrintMsg`/`ScrollMsg` (the message window), `BuildView`
  (the 11 x 11 view around the party, with line of sight), `MapCellAddr`, `DungeonCell`, the map
  frame and `ShowDungeonMap`.
- **ITEMS**: `InExodusCastle` (fire each turn in Exodus's castle), `MoonGateJump`, `DexRoll`,
  `CmdFire` (a frigate's cannons), `CmdJoinGold`, `CmdKlimbDescend` (K/D on the surface),
  `CmdIgnite` (torch), `CmdNegate` (Negate Time); the spell tables and strings of MAGIC and SHRINE.
- **MAGIC**: `CastSpell` (the Cleric and Wizard menus) and the spell handlers `SpellRepond` ...
  `SpellAnjuSermani` through `WizardSpellCmds`/`ClericSpellCmds` (32 spells, 26 handlers), with
  `HitAllMonsters` and friends.
- **SHRINE**: `PrintLevelHead`, `EnterShrine` (pay gold for a stat), `ExitToSosaria`, and the data
  6493-6B91: the Other words, `NameTbl` and the name strings, the cards.
- **PARTY**: `SaveGame`, `HurtPlayer`, `PrintName`, `StatusLine`, `ShowZtats`, `PartyUpkeep` (magic,
  food, poison, healing every turn), `SpendFood`, `FlashPlayer`/`FlashView`, `CheckTerrain` (where
  the party may go: force fields, lava, the frigate and the wind), `MoveWhirlpool`.
- **ACTIONS**: `CmdYell` (Evocare), `CmdOther` with `CmdDig` (the Exotics), Insert, Search, Bribe,
  `CmdPray`; the dungeon command tables and the menus' strings.
- **HAND**: the H command's menu `HandEquip` (food, gold, equipment, weapons, armour from one
  player to another) and `AskDirection`, the direction prompt of every command.
- **EQUIP**: the shared error exits (`MsgNoneLeft` ... `MsgIncapacitated`), `TransferBcd`,
  `AddMoves`, `ReadyWeapon`, `WearArmour`, **`CmdTransact`** (T: talk to a creature, Lord British's
  levels, the shop counters: the service by the player's y & 7), `ChestLoot`.
- **DUNMOVE**: `CmdGetChest` (and its traps), `DamageParty`, `EnterDungeon`, `DungeonLoop`,
  `DungeonTurnEnd`, `CmdKlimb`, `CmdDescend`, the turns, `CmdAdvance`, `CmdRetreat`.
- **CMDTAB**: data only: `CombatKeys`, `CombatCmds`, the fountain effects, the CNFLCT names.
- **COMBAT**: `CmdAttack` (a fight on the surface), `StartCombat` (the map from a CNFLCT file, the
  foes), the foes' turns, `ShootLine`, `DamageFoe`, victory, the combat commands `CCmd...`.
- **DUNEVENT**: the dungeon events `EventTimeVision`, `EventFountain`, wind, trap, `EventRod`,
  `EventGremlins`, `EventWriting`, and `DrawDungeon` (9630), the call into the DUNGEON.DAT overlay.
- **TEXT**: data only: long messages, the pub tips, Radrion's verses, shop texts.
- **ENDING**: `PrintMoves`, the Congratulations screen and `EndGame` (which hangs on purpose),
  `AskYesNo`, `PayGold`.
- **TOWNS**: `ShopPub`, `ShopGrocer`, `ShopTemple` (TempleCure 100, TempleHeal 200,
  TempleResurrect 500, TempleRecall 900 gold), `ShopWeapons`, `ShopArmour`, `ShopGuild` (gems,
  keys, powders, torches), `ShopRadrion` (the verses for gold), `ShopHorses`.

**BOOTUP** (the menu): BDATA holds the strings, tables, the roster and party buffers. TITLE:
`BreakHandler`, start-up, `TitleLoop` (the DEMO.ULT landscape driven by MOVES.ULT). ORGANIZE:
`RunMainMenu`, `JourneyOnward` (save PARTY.ULT, plant the chain load, read EXODUS.BIN over
itself), `RunOrganizeMenu`, `LookAtChar`, `FormParty`, `DisperseParty`. CREATE: `ExamineRegister`,
`TerminateChar`, `CreateChar`, `DrawCreateForm`, `EnterCharacter`, and the disabled
`AskScenarioDisk` (a `ret` patched over its first byte).

**ULTIMA** (the intro): UDATA holds the picture buffer `PictureBuf`, NAME.DAT and ANIMATE.DAT's
buffers. INTRO: `BreakHandler` and start-up (seed `RandState`, load the files), `CopyPicture`
(dissolve a picture in with speaker static), `DrawSignature` (NAME.DAT), `DrawAnimFrame`
(ANIMATE.DAT), `SetGraphicsMode`, the chain load of BOOTUP.BIN (`StartUp_ChainLoad`).

**DUNGEON.DAT**: one module, `DrawDungeonView` and its drawing routines (docs/FORMATS.md 8).

**LIB.INC** (the library): text (`PutChar`, `PrintStr`, `PrintAt`, `PrintBcdWord`, ...), keyboard
(`ReadKey`, `KeyReady` with the idle `Animate`, `ReadLine`, `ReadNumber`, `AskChoice`), screen
(`DrawChar`, `DrawTileBlock`, `DrawView`, `ClearScreen`, `FillCell`), files (`LoadFile`,
`SaveFile`, `OpenFile`), `Random`, the wind (`WindUpdate`), the sounds (`Sound` and `SoundTbl`:
`SndBuzz` 0FFh ... `SndSlowFall` 0F4h), and the copy protection's remains (`DiskCheckStub`).

## The command tables (EXODUS)

Each table is 33 entries: a key word (scan code and character), a handler and a prompt string.
The surface table is used outside dungeons and in towns, the second in a dungeon, the third
during a fight.

**Surface and towns (SurfaceKeys, SurfaceCmds, SurfacePrompts)**

| key | handler | prompt |
|---|---|---|
| Up | CmdNorth (1C7D) | North |
| A | CmdAttack (888B) | Attack- |
| Down | CmdSouth (1C9E) | South |
| Right | CmdEast (1CBF) | East |
| Left | CmdWest (1CE0) | West |
| Space | CmdPass (1C77) | Pass |
| B | CmdBoard (1D01) | Board |
| X | CmdXit (2035) | X-it |
| V | CmdVolume (2018) | Volume |
| Alt-S | CmdVolume (2018) | Volume |
| Z | CmdZtats (2068) | Ztats for # |
| E | CmdEnter (1D69) | Enter |
| L | CmdLook (1E7A) | Look- |
| M | CmdModify (1E9B) | Modify order!/Player: |
| Alt-V | CmdVolume (2018) | Volume |
| K | CmdKlimbDescend (5CC3) | Klimb |
| H | CmdHand (1E55) | Hand Equipment!/From Player: |
| T | CmdTransact (7FC6) | Who will/Transact? |
| U | CmdUnlock (1FD6) | Unlock- |
| I | CmdIgnite (5CC9) | Ignite a torch |
| Q | CmdQuit (1F25) | Quit & Save |
| R | CmdReady (7E33) | Ready for # |
| W | CmdWear (7EE4) | Wear for # |
| C | CmdCast (1D4E) | Cast by whom- |
| F | CmdFire (5BCF) | Fire |
| J | CmdJoinGold (5C73) | Join gold to: |
| D | CmdKlimbDescend (5CC3) | Descend |
| N | CmdNegate (5CF8) | Negate Time!/Whose Powd? |
| G | CmdGetChest (8190) | Get Chest!/Plr to search- |
| P | CmdPeer (1EFD) | Peer at gem!/Whose gem? |
| S | CmdSteal (1F53) | Steal Chest!/Player? |
| Y | CmdYell (7458) | Yell, whom? |
| O | CmdOther (74D5) | Other command!/Whose action? |

**Dungeon (DungeonKeys, DungeonCmds, DungeonPrompts)**

| key | handler | prompt |
|---|---|---|
| Space | CmdPass (1C77) | Pass |
| C | CmdCast (1D4E) | Cast by whom- |
| G | CmdGetChest (8190) | Get Chest!/Plr to search- |
| H | CmdHand (1E55) | Hand Equipment!/From Player: |
| I | CmdIgnite (5CC9) | Ignite a torch |
| J | CmdJoinGold (5C73) | Join gold to: |
| M | CmdModify (1E9B) | Modify order!/Player: |
| N | CmdNegate (5CF8) | Negate Time!/Whose Powd? |
| O | CmdOther (74D5) | Other command!/Whose action? |
| R | CmdReady (7E33) | Ready for # |
| V | CmdVolume (2018) | Volume |
| W | CmdWear (7EE4) | Wear for # |
| Y | CmdYell (7458) | Yell, whom? |
| Z | CmdZtats (2068) | Ztats for # |
| Alt-S | CmdVolume (2018) | Volume |
| Alt-V | CmdVolume (2018) | Volume |
| B | CmdNotDungeon (8472) | Not a DNG cmd! |
| A | CmdNotDungeon (8472) | Not a DNG cmd! |
| E | CmdNotDungeon (8472) | Not a DNG cmd! |
| F | CmdNotDungeon (8472) | Not a DNG cmd! |
| L | CmdNotDungeon (8472) | Not a DNG cmd! |
| Q | CmdNotDungeon (8472) | Not a DNG cmd! |
| T | CmdNotDungeon (8472) | Not a DNG cmd! |
| U | CmdNotDungeon (8472) | Not a DNG cmd! |
| X | CmdNotDungeon (8472) | Not a DNG cmd! |
| K | CmdKlimb (83F7) | Klimb |
| D | CmdDescend (841C) | Descend |
| Right | CmdTurnRight (8438) | Turn right |
| Left | CmdTurnLeft (8455) | Turn left |
| S | CmdNotDungeon (8472) | Not a DNG cmd! |
| Up | CmdAdvance (847D) | Advance |
| Down | CmdRetreat (84A9) | Retreat |
| P | CmdPeer (1EFD) | Peer at gem!/Whose gem? |

**Combat (CombatKeys, CombatCmds)**

| key | handler | prompt |
|---|---|---|
| U | CCmdBad (8D8D) |  |
| Space | CCmdPass (8D83) |  |
| Up | CCmdNorth (8CBE) |  |
| Down | CCmdSouth (8CC9) |  |
| Right | CCmdEast (8CD4) |  |
| Left | CCmdWest (8CDF) |  |
| V | CCmdVolume (8CEA) |  |
| Alt-S | CCmdVolume (8CEA) |  |
| Alt-V | CCmdVolume (8CEA) |  |
| R | CCmdReady (8CF1) |  |
| Z | CCmdZtats (8D0B) |  |
| N | CCmdNegate (8D57) |  |
| C | CCmdCast (8D38) |  |
| A | CCmdAttack (8D9F) |  |
| B | CCmdBad (8D8D) |  |
| D | CCmdBad (8D8D) |  |
| E | CCmdBad (8D8D) |  |
| F | CCmdBad (8D8D) |  |
| G | CCmdBad (8D8D) |  |
| I | CCmdBad (8D8D) |  |
| K | CCmdBad (8D8D) |  |
| P | CCmdBad (8D8D) |  |
| Q | CCmdBad (8D8D) |  |
| S | CCmdBad (8D8D) |  |
| T | CCmdBad (8D8D) |  |
| W | CCmdBad (8D8D) |  |
| X | CCmdBad (8D8D) |  |
| H | CCmdBad (8D8D) |  |
| J | CCmdBad (8D8D) |  |
| L | CCmdBad (8D8D) |  |
| M | CCmdBad (8D8D) |  |
| O | CCmdBad (8D8D) |  |
| Y | CCmdBad (8D8D) |  |

