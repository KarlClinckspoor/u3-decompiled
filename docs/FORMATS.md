# Data file formats of Ultima III (PC, GOG release)

Written 2026-11-09 (phase 4 of docs/PLAN.md). Every statement comes from the code of the three
programs (`src/`) or from the files themselves; `tools/u3fmt.py` parses and renders what is
described here (`python3 tools/u3fmt.py check` parses every file in `gamedata/`). Addresses are
the programs' memory addresses (COM images loaded at 0100). Confidence is marked: **sure** (the
code reads it that way and the rendering or text confirms it), **likely** (consistent with the
code, no single proof), **open**.

Numbers on the disk are little-endian. Counts (hit points, gold, food, ...) are packed BCD:
`bcd` below means that, least significant byte first. The game rebuilds nothing from these
files: they are the game's data, read by FCB calls at run time.

## 1. Which program reads what

Every load goes through the library routine `LoadFile` (BOOTUP 4A30, EXODUS 557A, ULTIMA 8D10):
`BX` = destination, `CX` = bytes to read, `DX` = file name. A file shorter than `CX` is read
whole.

| file | bytes | read by | to (size read) |
|---|---|---|---|
| BLANK.IBM, EXOD.IBM | 16384 | ULTIMA | 0115 (4000h each, in turn) |
| NAME.DAT | 640 | ULTIMA | 4117 (215h; the 266 points are 532 bytes) |
| ANIMATE.DAT | 5888 | ULTIMA | 432D (1700h) |
| SHAPES.ULT | 5120 | BOOTUP, EXODUS | library K01A9 (1400h) |
| CHARSET.ULT | 2048 | BOOTUP, EXODUS | library K15A9 (800h) |
| DEMO.ULT | 114 | BOOTUP | 07D2 (72h) |
| MOVES.ULT | 1024 | BOOTUP | 0844 (400h) |
| ROSTER.ULT | 1280 | BOOTUP | 02CE (500h) |
| PARTY.ULT | 274 | BOOTUP; EXODUS | 01BC (112h); 14BA (112h) |
| SOSARIA.ULT, AMBROSIA.ULT and the 12 towns and castles | 4648 | EXODUS | 0100 (1228h) |
| DARDIN, FIRE, MINE, PERINIAN, TIME, M, P .ULT | 2192 | EXODUS | 0900 (890h) |
| DUNGEON.DAT | 1866 | EXODUS | 0100 (800h, i.e. all of it): **code**, see section 8 |
| CNFLCT_*.ULT (9) | 176 | EXODUS | 24C4 (0B0h) |
| BRAND, FOUNTAIN, SHRINE, TIME .IMG | 121 | EXODUS | 24C4 (79h) |

The town and castle files are BRITISH, LCB, MOON, YEW, MONTOR_E, MONTOR_W, GREY, DAWN, DEVIL,
FAWN, DEATH, EXODUS (.ULT). The nine combat maps are A, B, C, F, G, M, Q, R, S.
`goggame-*`, `unins000.*`, `*.ico`, `webcache.zip`, `EULA.txt`, the manual and DOSBox files are
GOG's, not the game's. The programs themselves (ULTIMA.COM, BOOTUP.BIN, EXODUS.BIN) are
described in docs/HANDOFF.md.

## 2. Graphics

**Pixels** are CGA mode 4, 2 bits a pixel, four pixels a byte, high bits first. ULTIMA.COM sets
palette 1 (`int 10h AH=0Bh BH=1 BL=1`): 0 black, 1 cyan, 2 magenta, 3 white (`u3fmt.py` draws
them (0,0,0), (0,170,170), (170,0,170), (170,170,170)). **sure**

**Whole screens** (BLANK.IBM, EXOD.IBM): 16384 bytes = the CGA video memory image: scan lines
0, 2, 4, ... 198 at offsets 0, 80, 160, ..., then (from 2000h) lines 1, 3, ..., 199; the last
192 bytes of each bank are unused. EXOD.IBM is the title picture; BLANK.IBM the frame it is
drawn into. **sure** (rendered: `u3fmt.py cga EXOD.IBM`)

**SHAPES.ULT** (5120 bytes = 80 tiles of 64 bytes): a tile is 16x16 pixels, 4 bytes a row. The
64 bytes hold the **eight even scan lines first (rows 0, 2, ..., 14), then the eight odd lines**
(the library routine DrawTileBlock copies them to the two CGA banks that way). Shape numbers 0-63
are the map tiles; **64-79 are the second animation frames** of shapes 16-30 (merchant ... balron)
and 12 (whirlpool): the library's idle animation (SwapFrames) exchanges them every 10th keyboard
poll. **sure** The name table in EXODUS (`NameTbl`, 6556, 136 pointers) lists the names; numbers
0-63 are the shapes:

| | | | | | |
|---|---|---|---|---|---|
| 0 Water | 1 Grass | 2 Brush | 3 Forest | 4 Mountains | 5 Dungeon |
| 6 Towne | 7 Castle | 8 Floor | 9 Chest | 10 Horse | 11 Frigate |
| 12 Whirlpool | 13 Serpent | 14 Man-O-War | 15 Pirate | 16 Merchant | 17 Jester |
| 18 Guard | 19 Lord British | 20 Fighter | 21 Cleric | 22 Wizard | 23 Thief |
| 24 Orc | 25 Skeleton | 26 Giant | 27 Daemon | 28 Pincher | 29 Dragon |
| 30 Balron | 31 Exodus | 32 Force Field | 33 Lava | 34 Moon Gate | 35 Wall |
| 36 Void | 37 Wall | 38-57 sign letters A B C D E F G H I U Y L M N O P W R S T | 58, 59 Snake | 60 Magic | 61 Fire |
| 62 Shrine | 63 Ranger | | | | |

Names 64-79 are the weapons (Hand ... Exotic), 80-87 the armours (Skin ... Exotic), 88-119 the
spells (Repond ... Anju Sermani; 103 is empty), 120-135 monsters (Brigand ... Devil: on an odd y a
monster kind gets one of two of these names). `PrintName` (6BFA) prints name number `al - 1`. The
weapon and armour tables in BOOTUP (0DFF, 0E1F) are the same words again. **sure**

The library animates the map while it waits for a key (`Animate`, from KeyReady, not in a dungeon or
in BOOTUP/ULTIMA): water, lava, force fields and moon gates scroll a pixel line every 2 or 3 polls,
the flags of castles, townes and frigates wave, the figures swap frames every 10. All of it runs at
polling speed, so it depends on the CPU.

**CHARSET.ULT** (2048 bytes = 128 characters of 16 bytes): 8x8 pixels, 2 bytes a row, even
lines first then odd (library DrawChar writes a character to the two banks in that order).
Characters 0x20-0x7E are ASCII in a runic face; below that the game's symbols (10h and 11h frame
the moon phases and the wind on the status line; 1Eh is the input cursor; 08h is backspace).
**sure**

## 3. Maps: overworld, towns and castles (4648 bytes)

Loaded at 0100 by EXODUS.BIN (`MapBuf`), which is why 0100-1327 is a buffer there. **sure**
(rendered: `u3fmt.py map BRITISH.ULT`)

| file offset | memory | size | what |
|---|---|---|---|
| 0000-0FFF | 0100 | 4096 | the map, 64 x 64 bytes, row by row (`byte = y*64 + x`). The **shape number is `byte >> 2`** (EXODUS BuildView): the two low bits are never used by the tile lookup, so map bytes are multiples of 4 (Water 00, Grass 04, Brush 08, ..., Frigate 2Ch, Whirlpool 30h, Guard 48h, Lord British 4Ch, Exodus 7Ch). A moon gate on the overworld is written as 88h (shape 34). On the overworld a chest's low two bits remember the ground under it (MAGIC, Appar Unem). |
| 1000-117F | 1100 | 384 | **town speeches** (`MapText`): a table of `n` words (`n` = first word / 2; 4 to 8), each an offset from 1100 to a NUL-ended string, then the strings (start and end with a line feed). All zero on Sosaria. |
| 1180-119F | 1280 | 32 | **creature tile** (`MonTile`, a map byte: shape x 4; 0 = slot empty). A town uses 16 slots; on Sosaria the program fills slots as monsters appear (WORLD, 7 times in 135 a turn, never on Ambrosia). |
| 11A0-11BF | 12A0 | 32 | **the map byte under the creature** (`MonUnder`): put back when the creature leaves a cell, taken from the new one. For a spawned monster it is first its required ground (04 grass, 00 water for sea creatures). Hence the town values 00, 04, 08, 0C, 20 (water, grass, brush, forest, floor). A creature killed in a fight leaves a chest there. |
| 11C0-11DF | 12C0 | 32 | x (`MonX`) |
| 11E0-11FF | 12E0 | 32 | y (`MonY`) |
| 1200-121F | 1300 | 32 | **talk code** (`MonTalk`): the low 6 bits are the speech number (1 = first entry of the speech table, 0 = none) and **bits 7-6 how the creature moves**: 0 stands, 1 wanders (half the time, never onto x or y 0), 2 approaches the party (never attacks), 3 hostile: chases the party and starts a fight when it steps onto it. Every spawned monster gets C0h; Steal's alarm sets every guard to C0h. |
| 1220-1223 | 1320 | 4 | **the whirlpool** (Sosaria only): x, y (`WhirlpoolX`, `WhirlpoolY`) and its step dx, dy. Every 4th turn it moves by its step while the cell ahead is water, turns a frigate it meets into a whirlpool, and swallows the party when it reaches it (WORLD `Whirlpool`: to Ambrosia; the whirlpool restarts at x 3, random y). SOSARIA.ULT starts it at (5, 3Ah). |
| 1224-1227 | 1324 | 4 | **the two moons' phases** (`Moon1Phase`, `Moon2Phase`, 0-7) and the steps left to the next phase (12 and 4). In SOSARIA.ULT: 0, 0, 0Ch, 04. The moons are saved with the map, not in PARTY.ULT. |

The creature tile uses the same numbering as the map. The code special-cases 74h (Dragon),
3Ch (Pirate), both of which fire at the party up to 3 cells, and 4Ch (Lord British, who does
not speak through the table). The file is exactly 1228h bytes from 0100, so the map buffer
ends where EXODUS's entry vector (1328) begins.

**Moon gates**: the eight positions (x, y) are in EXODUS at `GateXTbl` (194D) and `GateYTbl`
(1955): (8,8) (57,46) (15,27) (36,58) (15,29) (12,55) (31,31) (58,31). The gate on the map is the
one of the first moon's phase. It moves (the old cell becomes grass, the new one 88h) only when the
second moon changes phase. Stepping into it takes the party to the gate of the second moon's phase
(ITEMS `MoonGateJump`). **sure**

**Dawn**: the town of Dawn has no fixed map cell. Its cell (37, 53), `DawnCell` at MapBuf+0D65,
becomes a Towne (18h) when both moons were in phase 7 and turns back to Forest (0Ch) when both
were 0 (WORLD `AdvanceMoons`). Its shops alone sell the +2 and +4 goods (section 6).

AMBROSIA.ULT is the second continent, reached through a whirlpool. The town and castle files hold
the town with its surroundings in the 64 x 64 map (BRITISH is a castle with a moat).

## 4. Dungeons (2192 bytes)

Loaded at 0900 (`DungeonMap`, 0900-1189). **sure** for the layout.

| file offset | memory | what |
|---|---|---|
| 0000-07FF | 0900 | eight levels, each 16 x 16 bytes (`byte = y*16 + x`, 256 bytes a level) |
| 0800-080F | 1100 | eight words: offsets from 1100 to each level's message |
| 0810-088F | 1110 | the eight messages ("Dardin's Pit!", "Secret slides!", ...), NUL ended; the rest is zero |

Cell bytes (DUNGEON.DAT draws them, EXODUS DUNMOVE and DUNEVENT act on them); **sure** unless marked:

| value | cells (all dungeons) | meaning |
|---|---|---|
| 00 | 5622 | open floor |
| 80-BF (80 seen) | 5753 | **wall**: drawn as a plain wall face |
| A0 | 452 | **secret door**: drawn exactly like a wall, but Advance walks into it (only exactly 80h stops Advance) |
| C0-FF (C0 seen) | 176 | **door**: a wall face with a door in it; Advance walks in |
| 10 / 20 / 30 | 101 / 94 / 45 | **ladder up / ladder down / both** (Klimb tests bit 10h, Descend bit 20h and refuses bit 7) |
| 40 | 673 | **a chest** (drawn as a box on the floor; Get Chest wants exactly 40h). A wandering monster's cell is set to 40h before the fight, so it leaves a chest |
| 01-08 | 76 (02), 451 (03), 367 (04), 17 (05), 249 (06), 259 (08), 1 (01) | **events** (DUNEVENT): 1 time vision (TIME.IMG), 2 fountain, 3 strange wind (the torch goes out), 4 trap, 5 the rod (BRAND.IMG, gives a mark), 6 gremlins (eat 100 food), 7 nothing, 8 misty writing (the level's message). 1, 4, 6 and 8 clear their cell; 2, 3 and 5 stay. Not drawn |

Moving: Advance is stopped only by exactly 80h; Retreat by any cell from 80h up; turning is refused
while the party stands in a cell from A0h up (a doorway). A wandering encounter comes with chance
(level+2)/(level+130) per turn on a floor cell.

`python3 tools/u3fmt.py dungeon DARDIN.ULT` prints the messages and draws the eight levels as
grids of hex values.

## 5. Combat maps

**CNFLCT_x.ULT** (176 bytes at 24C4) and the four **.IMG** files (BRAND, FOUNTAIN, SHRINE, TIME:
121 bytes, only the map). The map is 11 x 11 bytes (`y*11 + x`), each a **shape number** (not
times 4): Grass 01, Brush 02, ... **sure** (rendered: `u3fmt.py combat CNFLCT_G.ULT`). The
screen picture of a combat is the same 11 x 11 block the library draws with DrawView.

The map chosen: in a dungeon C; pirates S (from a frigate) or A; from a frigate Q (a sea foe) or R;
a sea foe from land M; otherwise by the party's tile: grass G, brush B, forest F, floor, force field
or lava C. FileConflict (8538) is "CNFLCT_G.ULT"; COMBAT picks one of nine name pointers.

CNFLCT files add 55 bytes, which the combat code reads as `StartUp + offset` (section 9). The
values after +80h are overwritten when the fight starts; the files only give the start positions.

| file offset | memory | size | what |
|---|---|---|---|
| 79-7F | 253D | 7 | not read (all files hold `7F 00 00 7F 7F 00 00`) |
| 80-87 | 2544 | 8 | foes' x |
| 88-8F | 254C | 8 | foes' y |
| 90-97 | 2554 | 8 | the map tile under each foe (put back when it moves or dies) |
| 98-9F | 255C | 8 | foes' hit points (0 = dead or absent) |
| A0-A3 | 2564 | 4 | the four players' x (0FFh = not in the fight) |
| A4-A7 | 2568 | 4 | the players' y |
| A8-AB | 256C | 4 | the map tile under each player |
| AC-AF | 2570 | 4 | each player's own tile (from his class) |

**sure** (COMBAT, and the library's combat blink, which shows +ACh for 10 polls and +A8h for 3).
Number of foes: 8 in Exodus's castle, 8 guards, 1 in the other towns and castles, else 1-8.

## 6. The party and the roster

**ROSTER.ULT** (1280 bytes = 20 characters of 64 bytes) and **PARTY.ULT** (274 bytes = an
18-byte header and **four** characters of 64 bytes, at `Players` (14CC) in EXODUS: `address =
14CC + 40h * slot`). The shipped files are all zero (a new game). A slot is empty when its first
byte is 0.

### Character record (64 bytes)

| offset | what | |
|---|---|---|
| 00-09 | name, at most 9 letters, NUL ended (BOOTUP: `cx = 9`) | sure |
| 0A-0D | not seen used | open |
| 0E | **marks** in bits 7-4 (7 Kings, 6 Snake, 5 Fire, 4 Force) and **cards** in bits 3-0 (3 Death, 2 Moons, 1 Sol, 0 Love). The rod gives the mark `1 << (4 + (x & 3))`, Search a card `1 << (x & 3)`; Insert wants card n with the key "LSMD"[n] | sure |
| 0F | torches (BCD): "Ignite a torch" takes one | sure |
| 10 | roster slot flag: 00 free, FF **in the party** (set by Form the Party) | sure |
| 11 | status letter: `G` good, `P` poisoned, `D` dead, `A` ashes (BOOTUP's key string is "GPDP", a typo; an unknown letter still shows "Ashes") | sure |
| 12-15 | strength, dexterity, intelligence, wisdom (BCD, one byte each; caps by race, SHRINE `RaceStatMax`) | sure |
| 16 | race letter: `H` human, `E` elf, `D` dwarf, `B` bobbit, `F` fuzzy | sure |
| 17 | class letter: `F`ighter `C`leric `W`izard `T`hief `P`aladin `L`ark `B`arbarian `D`ruid `I`llusionist `A`lchemist `R`anger | sure |
| 18 | sex letter: `M`, `F`, `O` (other) | sure |
| 19 | magic points (BCD): a spell costs 5 x its letter's index; they regenerate by class | sure |
| 1A-1B | hit points (BCD word) | sure |
| 1C-1D | maximum hit points (BCD word; Lord British adds 100 when experience/100 >= max/100, up to 2500; from 500 the Mark of Kings is needed) | sure |
| 1E-1F | experience (BCD word, capped at 9999); the level shown is experience/100 + 1 | sure |
| 20 | food, hundredths (0.10 is eaten every turn; borrowed into 21-22) | sure |
| 21-22 | food (BCD word); at 0 the player starves (5 hit points a turn) | sure |
| 23-24 | gold (BCD word) | sure |
| 25 | gems | sure |
| 26 | keys | sure |
| 27 | powders | sure |
| 28 | armour worn: 0-7 = Skin, Cloth, Leather, Chain, Plate, +2 Chain, +2 Plate, Exotic | sure |
| 29-2F | armours owned: counts of kinds 1-7 (Cloth ... Exotic), indexed `[record + 28h + kind]`; Skin (0) is never counted | sure |
| 30 | weapon readied: 0-15 = Hand, Dagger, Mace, Sling, Axe, Bow, Sword, 2-H-Swd, +2 Axe, +2 Bow, +2 Swd, Gloves, +4 Axe, +4 Bow, +4 Swd, Exotic | sure |
| 31-3F | weapons owned: counts of kinds 1-15 (Dagger ... Exotic), indexed `[record + 30h + kind]`; Hand (0) is never counted | sure |

New characters get (BOOTUP `EnterCharacter`): status `G`, party flag 0, hit points 150, max hit
points 150, food 150, gold 150, **one Cloth armour and one Dagger** (counts at 29h and 31h), with
Skin worn and Hand readied. Their strength, dexterity, intelligence, wisdom (50 points to share),
race, class and sex come from the creation screen; points not spent are lost.

### PARTY.ULT header (18 bytes, at 14BA in EXODUS)

| offset | memory | what | |
|---|---|---|---|
| 00 | 14BA | **the party's tile** (`PartyTile`, a shape number): 3Fh on foot (shape 63, Ranger), 0Ah on horses, 0Bh in a frigate (0Ch while a whirlpool takes it) | sure |
| 01 | 14BB | not read | open |
| 02 | 14BC | **where the party is** (the library's `Location`): 00 Sosaria, 01 a dungeon (the torch works only here; the library's tile animation stops), 02 a towne, 03 a castle, 04 a picture on show (shrine, time vision, fountain, rod), 80h a fight (the old value is kept at `SavedLocation`, 58CB), FFh Ambrosia. SaveGame writes 0 | sure |
| 03-06 | 14BD | **move counter** (`MoveCount`), 8 digits of BCD, printed with "moves" at the end of the game | sure |
| 07 | 14C1 | number of characters in the party (`PartySize`, 1-4) | sure |
| 08-09 | 14C2 | the party's position on Sosaria/Ambrosia (`PartyXY`), also while it is in a town or dungeon: the shops test its x to know they are in Dawn | sure |
| 0A-0D | 14C4 | the roster numbers (1-20) of the four members (BOOTUP writes them; Modify order swaps them with the records) | sure |
| 0E | 14C8 | `ExoticWeaponFound`: 0FFh once Dig found the Exotic weapon; the weapon menus then list all 18 entries | sure |
| 0F | 14C9 | `ExoticArmourFound`: the same for the armour (armour menus: 10 entries) | sure |
| 10 | 14CA | `ExtraWeaponsOk`: 0FFh once the +2/+4 weapons are for sale (set by Dig, and by Dawn's weapon shop when it shows its price list): 17 menu entries instead of 10 | sure |
| 11 | 14CB | `ExtraArmoursOk`: the same for the +2 armours (9 entries instead of 7) | sure |

The party's current position on the map is not in the file: EXODUS keeps it at `PlayerXY` (15CC
x, 15CD y) and loads it from 14C2 when the game starts and after a town or dungeon. `LightOn`
(15CE) is a **torch counter**: Ignite sets 0FFh, every dungeon turn takes one (a torch lasts 255
turns; Lorum gives 10, Dag Lorum 250), the strange wind sets it to 0, and the dungeon view is
drawn only while it is not 0. `DungeonLevel` (15CF) is the level (0-7) and `TimeStop` (15D0) the
counter "Negate Time" sets to 10.

## 7. The intro files

**NAME.DAT** (640 bytes): a list of 266 (x, y) points (x never 0), ended by x = 0; the rest is
zero. It is the **handwritten "Lord British"** under "Ultima III" (screen x 107-235, y 129-144):
ULTIMA's `DrawSignature` writes it point by point with a delay, two pixels wide, y counted from the
bottom (192 - y). **sure** (`u3fmt.py name`)

**ANIMATE.DAT** (5888 bytes): four pictures of the party facing the dragon, each as four copies
shifted by one pixel: **4 pictures x 4 shifts x 368 bytes**, each 16 rows of 23 bytes (92 pixels,
rows in order, no bank interleave). ULTIMA selects `picture * 1472 + shift * 368` and draws 16 rows
of 23 bytes; its x is in 2-pixel units, so only shifts 0 and 2 are ever used. **sure** (rendered:
`u3fmt.py animate`)

**DEMO.ULT** (114 bytes): a 19 x 6 block of shape numbers drawn with DrawTileBlock under BOOTUP's
menu (a strip of landscape with a castle). **sure**

**MOVES.ULT** (1024 bytes): the script that changes DEMO's block over time: 512 steps; step `i`
has a **cell number** in byte `i` and a **value** in byte `512 + i`. A cell number of FF is a
pause of `value` rounds; otherwise cell `cell` becomes `value >> 1` and the block is redrawn
when that is 8 or more (BOOTUP `TitleLoop`). **sure** for the structure.

## 8. DUNGEON.DAT is code

DUNGEON.DAT (1866 bytes) begins with `E9 44 03`, a `jmp 0447`. It is a **machine-code overlay**:
EXODUS loads it over the map buffer at 0100 whenever it enters a dungeon (the dungeon maps are at
0900, past its end at 084A) and calls 0100 while the torch counter (`LightOn`, 15CE) is not 0, passing the
party's position (x, y) in `BX`, its facing (0-3) in `AL` and the level in `AH` (it stores them
at 0103-0106; EXODUS 963D-9648). It draws the 3D corridor view into the screen (writes to B800:), reading
the cells through `lea bx,[bx+0900h]` (its last routine). 0103-0446 are its tables (offsets of
the view's walls and the like); the code starts at 0447. **sure** (disassembly: its first
instructions are `pushf; push ax; push es; mov [0103],bx; mov [0105],al; mov [0106],ah; mov
ax,0B800h; mov es,ax`)

This makes **DUNGEON.DAT a fourth program** of the game, in the same position as the three COM
images, and it is rebuilt from `src/dungeon/DUNGEON.ASM` (phase 4b). It is self-contained: no call
leaves it, and it reads only two things of EXODUS, written as the constants `DMAP EQU 900h` (the
dungeon map) and `ROWTAB EQU 132Ah` (EXODUS's `ScreenRowTbl`). 0103-0106 are its variables
(`ViewPos`, `ViewFacing`, `ViewLevel`), 0107-0446 byte tables (none holds an address), the code
0447-084A (`DrawDungeonView`).

How it draws (DUNGEON.ASM's header has the details): 32 view slots up to 3 cells ahead
(`SlotDXTbl`/`SlotDYTbl`, turned by the facing: 0 north, 1 east, 2 south, 3 west); lines of sight
stop at the first wall; each step away halves the size (a fake perspective); walls are stripes
every second pixel, doors fill the gaps (`FaceTbl`: 64 entries of 8 bytes, 0-31 wall faces, 32-63
doors), ladders (`LadderTbl`) and chests (`ChestTbl`) only up to two cells away. Standing in a door
shows only the cells straight ahead; standing in a secret door only a wall.

## 9. Memory overlays: what shares an address

The programs reuse memory for different files; a change that moves one of them must keep the
others consistent.

- **0100-1327 in EXODUS** is the map file (4648 bytes). In a dungeon it holds DUNGEON.DAT (0100-
  084A) and, from 0900, the dungeon file (0900-1189), whose messages sit at 1100: the town
  speeches (`MapText`) and the dungeon message table are the same memory. The entry vector at 1328
  must stay right after the buffer: BOOTUP jumps through it.
- **24C4-2574 in EXODUS** is the start-up code. After EXODUS is running (the code ends with
  `call` into the main loop and does not come back), the same memory is used to load the
  **combat maps and the shrine/fountain/brand/time pictures** (`lea bx, StartUp`, 79h or 0B0h bytes)
  and as the 11 x 11 view buffer the library draws with DrawView (library ViewTiles is this address in
  EXODUS). The combat arrays are therefore referenced as labels inside the start-up code
  (`L2544`, `L254C`, `L2564` ...: they appear in the sources as `L2542+2`, `L254C`, ...). If the
  start-up code's size changes, those labels move away from `L24C4 + 80h`, `+88h`, ... and the
  combat arrays would break. **Fixed in phase 4**: the sources now write them as `StartUp+0A0h`,
  `StartUp+0ACh[bx]` and so on (`bufrel` in `tools/u3an.py`), or through the constant offsets
  `CmbMonY` (88h) ... `CmbPlrTile` (0ACh) added to a register that holds `StartUp + n`, so the
  start-up code can be edited (checked by inserting 5 bytes after `StartUp`).
- **BOOTUP and ULTIMA** use the library's `TileGfx` for the tiles and `CharGfx` for the
  characters, and the roster at `Roster` (02CE), the party at `PartyBuf` (01BC) (BOOTUP only).

## 10. Open questions

- The party header's byte 01 and the character record's 0A-0D are never seen used.
- The parameters of the warble sound (0FDh, BL/BH from the caller) and which events use which sound.
- No shipped ROSTER.ULT or PARTY.ULT contains a character, so the character record is decoded from
  the code only (thoroughly: every field has its readers and writers named in the sources). A save
  from a played game would confirm it: `python3 tools/u3fmt.py roster FILE` and `party FILE`.
- The manual (`gamedata/Ultima_3_manual.pdf`) is a scan with no text layer, so the fields and
  names above were **not** checked against it; an OCR pass (race and class tables, item prices,
  spell list) would be a good independent check.
- More on what the code does with these data (mechanics, bugs): docs/FINDINGS.md.
