# Map of the programs: modules and routines

Phase 5 of docs/PLAN.md (2026-11-09). Each program is split into modules in link order, named
for the subsystem, with the library (`src/LIB.INC`) linked as a module of its own. The cuts were
found from the routine survey (`python3 tools/routines.py TARGET`: every routine with its size,
callers, the dispatch table entry that reaches it and the strings it prints) and the dispatch
tables; they are listed in `modules` in `tools/u3an.py`, and `tools/gen.py` moves a start down to
the nearest address where a module may begin (not inside an instruction or table word, and not
crossed by an 8-bit relative branch, because MASM cannot make a short jump to another module).
All cuts needed no move except the library's own bounds. The sources are the truth now: to move a
boundary, move the lines and the EXTRN/PUBLIC declarations by hand (or re-derive with regen.py).

The build is checked as before (`tools/build.py`, all four files identical with MASM 4.00 and
3.00) and by `tools/shift.py`, which now pads **every** module, so a label that works only inside
its module's old place would show.

A module's address range is its place in the original image. Data sits where the original
program had it: strings and tables are in the module that comes after or before the code that
uses them, which is what the table shows (EXDATA, TEXT, CMDTAB, BDATA and UDATA are mostly or
only data).

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
| TRANSACT.ASM | 7AEA-7D1A | 560 | the Transact command and its menus |
| EQUIP.ASM | 7D1A-8190 | 1142 | ready weapon and armour, talk, gold |
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


Where a module's name is not enough:

- **EXODUS LOOP** (1BD5): the main loop at 1BD5 reads a key (library K29BD), looks it up in the
  33-word key table at 1887 and jumps through the handler table at 190B (the table is below).
  The handlers up to 2068 are the movement keys, Pass, Board, X-it, Enter, Exchange, Volume, Look
  and a few more; Attack (888B) and the item and spell handlers are elsewhere.
- **EXODUS WORLD** (207D): 207D and 2097 draw the moons' line, 20AE advances the two moons and
  moves the moon gate (docs/FORMATS.md 3), 2168 is the moon gate teleport (Sosaria and
  Ambrosia), 2228-23A5 create and move the creatures (the arrays at 1280-1320), and 24C4-259E is
  the start-up code, which the combat file later overwrites (FORMATS.md 9).
- **EXODUS VIEW** (259E): the 11 x 11 window (27CD, calling the library tile drawer), map tile
  access (28DF and 28F2: x, y to the byte at 0100 + y*64 + x, and for a dungeon the 0900 + level
  cell) and the screen clearing.
- **EXODUS ITEMS** (58B4): Get Chest (5BCF), Join gold (5C73), Ignite a torch (5CC9), Negate Time
  (5CF8). The data before 5B28 is the item and message text.
- **EXODUS MAGIC** (5D83): the cast command (the Cleric and Wizard menus, 5D83), the first 16
  spells (tables 594B and 596B: Cleric, Wizard) and their handlers 5F9F-62C4 (heal, cure,
  resurrect, recall, ...). The spell names are in the name table (FORMATS.md 2).
- **EXODUS SHRINE** (62FD): the line "LVL" and the player number (62FD), the shrine (6366: pay
  gold for strength, dexterity, intelligence or wisdom), the exit to Sosaria (6458), and the
  big data area 6493-6B91 (the name and message tables of FORMATS.md 2).
- **EXODUS PARTY** (6B91): printing a name (6BFA), the status line (6CC3), the Ztats screen
  (6DC1), hit points and experience (6E23-6E96), food (70E4 and 7136: the food is spent a little
  every step, "Starving!") and poison (6FDF).
- **EXODUS ACTIONS** (7458): the Word of power (Evocare), the Other command (Insert, Dig,
  Search, Bribe, Pray: the table at 654C) and their handlers.
- **EXODUS TRANSACT** (7AEA): Transact and its menus (the pointer tables at 78BB, 78E6, 7904,
  7932 and the handlers at 794D), and the buy/sell loop.
- **EXODUS EQUIP** (7D1A): the move counter (7E02), Ready a weapon and Wear armour (7E48, 7EFA),
  talking to a creature (7FC6) and the gold and experience message (80D9).
- **EXODUS DUNMOVE** (8190): dungeon: traps (8190: gas, acid, poison), darkness (82C6), Klimb,
  Descend, turns, Advance, Retreat (83F7-84A9). The 3D view itself is the overlay DUNGEON.DAT.
- **EXODUS CMDTAB** (84DB): data only: the combat command table (8579 keys, 85BB handlers, 85FD
  the fountain effects) and neighbours.
- **EXODUS COMBAT** (888B): the whole fight: the Attack command (888B), setting up the combat
  map from a CNFLCT file (89BD), the monsters' turns (8AE6), hitting (8E7A), victory (8F5A),
  the combat commands (8CBE-8D9F).
- **EXODUS DUNEVENT** (941E): what happens at the special cells of a dungeon: time vision,
  fountain, strange wind, trap, the rod, gremlins, writing on the wall, and the fountain effects.
  9630-964E is the call into the DUNGEON.DAT overlay.
- **EXODUS TEXT** (964F): the long strings: shrine and fountain text, the endgame and the verses
  the Oracle speaks (the tables at 9979 and A1B0).
- **EXODUS ENDING** (A46F): the move counter printed at the end and the Congratulations screen
  (A491).
- **EXODUS TOWNS** (A5AC): the town services, dispatched by the table at 77CE: Pub (A5AC), Grocer
  (A630), Temple (A692, with the four priest services at A6D4-A833: cure 100, heal 200,
  resurrect 500, recall 900 gold), Weapons (A8A5), Armour (AA25), Guild (AB93: gems, keys,
  powders, torches at ABBD-ACAC), Radrion's shrine (ACFC) and the Equine Emporium (AD70).
- **BOOTUP TITLE** (1209): start-up, the scrolling picture of DEMO.ULT and MOVES.ULT (12D3), and
  the dispatch of the menu keys. **ORGANIZE**: the party menu (14C9), Look at a character
  (158F), Form the party (1792), Disperse (18DF). **CREATE**: Register (194B), Terminate (19DB),
  Create (1A6D), the name and points entry (1B47-1BC8) and the loading of EXODUS.BIN.
- **ULTIMA INTRO** (5CDD): start-up (5CDF), the title pictures and the animations (5E5A-5F41),
  drawing the party and dragon sprites (5F6C, 6024), the check of the graphics mode (607E) and
  the chain load of BOOTUP.BIN.
- **DUNGEON.DAT** is the single module of the overlay (docs/FORMATS.md 8).

## The command tables (EXODUS)

Each table is 33 entries: a key word (scan code and character), a handler address and a prompt
string. The surface table is used outside dungeons and in towns, the second in a dungeon, the
third during a fight. The key word `1F00`, `2F00` and `2C00` are Alt-S, Alt-V and Alt-Z.

**Surface (and towns)**

| key | handler | prompt |
|---|---|---|
| Up | 1C7D | North |
| A | 888B | Attack- |
| Down | 1C9E | South |
| Right | 1CBF | East |
| Left | 1CE0 | West |
| Space | 1C77 | Pass |
| B | 1D01 | Board |
| X | 2035 | X-it |
| V | 2018 | Volume |
| Alt-S | 2018 | Volume |
| Z | 2068 | Ztats for # |
| E | 1D69 | Enter |
| L | 1E7A | Look- |
| M | 1E9B | Modify order!/Player: |
| Alt-V | 2018 | Volume |
| K | 5CC3 | Klimb |
| H | 1E55 | Hand Equipment!/From Player: |
| T | 7FC6 | Who will/Transact? |
| U | 1FD6 | Unlock- |
| I | 5CC9 | Ignite a torch |
| Q | 1F25 | Quit & Save |
| R | 7E33 | Ready for # |
| W | 7EE4 | Wear for # |
| C | 1D4E | Cast by whom- |
| F | 5BCF | Fire |
| J | 5C73 | Join gold to: |
| D | 5CC3 | Descend |
| N | 5CF8 | Negate Time!/Whose Powd? |
| G | 8190 | Get Chest!/Plr to search- |
| P | 1EFD | Peer at gem!/Whose gem? |
| S | 1F53 | Steal Chest!/Player? |
| Y | 7458 | Yell, whom? |
| O | 74D5 | Other command!/Whose action? |

**Dungeon**

| key | handler | prompt |
|---|---|---|
| Space | 1C77 | Pass |
| C | 1D4E | Cast by whom- |
| G | 8190 | Get Chest!/Plr to search- |
| H | 1E55 | Hand Equipment!/From Player: |
| I | 5CC9 | Ignite a torch |
| J | 5C73 | Join gold to: |
| M | 1E9B | Modify order!/Player: |
| N | 5CF8 | Negate Time!/Whose Powd? |
| O | 74D5 | Other command!/Whose action? |
| R | 7E33 | Ready for # |
| V | 2018 | Volume |
| W | 7EE4 | Wear for # |
| Y | 7458 | Yell, whom? |
| Z | 2068 | Ztats for # |
| Alt-S | 2018 | Volume |
| Alt-V | 2018 | Volume |
| B | 8472 | Not a DNG cmd! |
| A | 8472 | Not a DNG cmd! |
| E | 8472 | Not a DNG cmd! |
| F | 8472 | Not a DNG cmd! |
| L | 8472 | Not a DNG cmd! |
| Q | 8472 | Not a DNG cmd! |
| T | 8472 | Not a DNG cmd! |
| U | 8472 | Not a DNG cmd! |
| X | 8472 | Not a DNG cmd! |
| K | 83F7 | Klimb |
| D | 841C | Descend |
| Right | 8438 | Turn right |
| Left | 8455 | Turn left |
| S | 8472 | Not a DNG cmd! |
| Up | 847D | Advance |
| Down | 84A9 | Retreat |
| P | 1EFD | Peer at gem!/Whose gem? |

**Combat**

| key | handler | prompt |
|---|---|---|
| U | 8D8D |  |
| Space | 8D83 |  |
| Up | 8CBE |  |
| Down | 8CC9 |  |
| Right | 8CD4 |  |
| Left | 8CDF |  |
| V | 8CEA |  |
| Alt-S | 8CEA |  |
| Alt-V | 8CEA |  |
| R | 8CF1 |  |
| Z | 8D0B |  |
| N | 8D57 |  |
| C | 8D38 |  |
| A | 8D9F |  |
| B | 8D8D |  |
| D | 8D8D |  |
| E | 8D8D |  |
| F | 8D8D |  |
| G | 8D8D |  |
| I | 8D8D |  |
| K | 8D8D |  |
| P | 8D8D |  |
| Q | 8D8D |  |
| S | 8D8D |  |
| T | 8D8D |  |
| W | 8D8D |  |
| X | 8D8D |  |
| H | 8D8D |  |
| J | 8D8D |  |
| L | 8D8D |  |
| M | 8D8D |  |
| O | 8D8D |  |
| Y | 8D8D |  |

