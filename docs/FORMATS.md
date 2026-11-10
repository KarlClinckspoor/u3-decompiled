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

Every load goes through the library routine `K2BF0` (BOOTUP 4A30, EXODUS 557A, ULTIMA 8D10):
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
(the library routine K26E8 copies them to the two CGA banks that way). Shape numbers 0-63 are
map tiles, 64-79 are other symbols (letters for signs, ...). **sure** The name table in
EXODUS (6556, 136 pointers) lists the names; numbers 0-79 are the shapes:

| | | | | | |
|---|---|---|---|---|---|
| 0 Water | 1 Grass | 2 Brush | 3 Forest | 4 Mountains | 5 Dungeon |
| 6 Towne | 7 Castle | 8 Floor | 9 Chest | 10 Horse | 11 Frigate |
| 12 Whirlpool | 13 Serpent | 14 Man-O-War | 15 Pirate | 16 Merchant | 17 Jester |
| 18 Guard | 19 Lord British | 20 Fighter | 21 Cleric | 22 Wizard | 23 Thief |
| 24 Orc | 25 Skeleton | 26 Giant | 27 Daemon | 28 Pincher | 29 Dragon |
| 30 Balron | 31 Exodus | 32 Force Field | 33 Lava | 34 Moon Gate | 35 Wall |
| 36 Void | 37 Wall | 38-57 sign letters A B C D E F G H I U Y L M N O P W R S T | 58, 59 Snake | 60 Magic | 61 Fire |
| 62 Shrine | 63 Ranger | 64-79 the weapon names (Hand ... Exotic) | | | |

Names 80-87 are the armours (Skin ... Exotic), 88-119 spells (Repond ... Anju Sermani), 120-135
monsters (Brigand ... Devil). The routine at 6BFA prints name number `al - 1`. The weapon and
armour tables in BOOTUP (0DFF, 0E1F) are the same words again. **sure** for the table, **likely**
that shapes 64-79 are not weapon pictures (the sheet shows a character set of runes, a symbol
or two and the party's members).

**CHARSET.ULT** (2048 bytes = 128 characters of 16 bytes): 8x8 pixels, 2 bytes a row, even
lines first then odd (library K2600 writes a character to the two banks in that order).
Characters 0x20-0x7E are ASCII in a runic face; below that the game's symbols (the two parentheses
around the moon phases are 28h and 29h; 10h and 11h are the moon symbols, 08h is backspace).
**sure**

## 3. Maps: overworld, towns and castles (4648 bytes)

Loaded at 0100 by EXODUS.BIN, which is why 0100-1327 is a buffer there. **sure** (rendered:
`u3fmt.py map BRITISH.ULT`)

| file offset | memory | size | what |
|---|---|---|---|
| 0000-0FFF | 0100 | 4096 | the map, 64 x 64 bytes, row by row (`byte = y*64 + x`). The **shape number is `byte >> 2`** (EXODUS 281D): the two low bits are never used, so every byte is a multiple of 4 (Water 00, Grass 04, Brush 08, ...). A moon gate on the overworld is written as 88h (shape 34). |
| 1000-117F | 1100 | 384 | **town speeches**: a table of `n` words (`n` = first word / 2; 4 to 8), each an offset from 1100 to a NUL-ended string, then the strings (start and end with a line feed). All zero on Sosaria. |
| 1180-119F | 1280 | 32 | **creature tile** (a shape number times 4; 0 = slot empty). 16 slots are used by a town; the overworld starts all empty and the program fills slots as monsters appear (EXODUS 22EA). |
| 11A0-11BF | 12A0 | 32 | **movement code**. Seen in towns: 00 (stands), 04, 08, 0C, 20. Meaning **open**; the program's movement routine reads it (EXODUS 2231 ff.). |
| 11C0-11DF | 12C0 | 32 | x position |
| 11E0-11FF | 12E0 | 32 | y position |
| 1200-121F | 1300 | 32 | **talk code**: the low 6 bits are the speech number (1 = first entry of the speech table) and the two high bits flag the kind of talker; C0 means "does not talk" (all spawned monsters get C0; EXODUS 2312, 8047). Seen: 01-08, 41-45, 83, C0. The kind bits' meaning is **open**. |
| 1220-1227 | 1320 | 8 | **state**, used on Sosaria only: 1320 and 1321 are the moon gate (EXODUS 21A4 stores 3 and a position when it opens); 1324 and 1325 are the **two moons' phases** (0-7); 1326 and 1327 count down the steps to the next phase (12 and 4 steps; EXODUS 20AE). In SOSARIA.ULT they are `05 3A 00 00 00 00 0C 04`. The moons' phases are saved with the map, not in PARTY.ULT. |

The creature tile uses the same numbering as the map (shape number times 4): the code
special-cases 74h (Dragon, EXODUS 2456), 3Ch (Pirate, 245D) and 4Ch (Lord British, EXODUS 803E: he
does not speak through the table). The file is exactly 1228h bytes from 0100, so the map buffer
ends where EXODUS's entry vector (1328) begins.

**Moon gates**: the eight positions (x, y) are in EXODUS at 194D and 1955: (8,8) (57,46) (15,27)
(36,58) (15,29) (12,55) (31,31) (58,31), one for each phase of the first moon. **sure**
(EXODUS 20F0-2110: the gate of the old phase is replaced by grass, the new one set to 88h.)

AMBROSIA.ULT is the second continent (reached by a moon gate when PARTY.ULT's location byte is
0FFh, see 6). The towns hold in the 4096-byte map the town with its surroundings (BRITISH is
a castle with a moat of Water and Grass around it, 64 x 64).

## 4. Dungeons (2192 bytes)

Loaded at 0900 (0900-1189). **sure** for the layout.

| file offset | memory | what |
|---|---|---|
| 0000-07FF | 0900 | eight levels, each 16 x 16 bytes (`byte = y*16 + x`, 256 bytes a level) |
| 0800-080F | 1100 | eight words: offsets from 1100 to each level's message |
| 0810-088F | 1110 | the eight messages ("Dardin's Pit!", "Secret slides!", ...), NUL ended; the rest is zero |

Cell bytes seen (the 3D view draws them; the high nibble is the main kind):

| value | cells (all dungeons) | meaning |
|---|---|---|
| 00 | 5622 | open floor |
| 80 | 5753 | wall |
| A0 | 452 | a wall-like kind that cannot be turned in (door or secret door; the turn commands refuse cells >= A0) **likely** |
| C0 | 176 | like A0 (secret door or similar) **likely** |
| 10 / 20 / 30 | 101 / 94 / 45 | **ladder up / ladder down / both** (the Klimb command tests bit 10h, Descend bit 20h: EXODUS 8401, 842A) **sure** |
| 40 | 673 | a special cell (chest, fountain or trap) **open** |
| 01-08 | 76 (02), 451 (03), 367 (04), 17 (05), 249 (06), 259 (08), 1 (01) | the low bits: trap or event codes, one per cell **open** |

`python3 tools/u3fmt.py dungeon DARDIN.ULT` prints the messages and draws the eight levels as
grids of hex values. The game-state commands for dungeons are in EXODUS's table at 774A.

## 5. Combat maps

**CNFLCT_x.ULT** (176 bytes at 24C4) and the four **.IMG** files (BRAND, FOUNTAIN, SHRINE, TIME:
121 bytes, only the map). The map is 11 x 11 bytes (`y*11 + x`), each a **shape number** (not
times 4): Grass 01, Brush 02, ... **sure** (rendered: `u3fmt.py combat CNFLCT_G.ULT`). The
screen picture of a combat is the same 11 x 11 block the library draws at K2CAA.

CNFLCT files add 55 bytes, which the combat code reads through labels inside its own memory
(24C4 + offset; see section 9):

| file offset | memory | size | what |
|---|---|---|---|
| 79-7F | 253D | 7 | unknown (all the files hold `7F 00 00 7F 7F 00 00`) |
| 80-87 | 2544 | 8 | monsters' x |
| 88-8F | 254C | 8 | monsters' y |
| 90-97 | 2554 | 8 | monsters' tile or kind (all 01 in the files; filled in at the start of a fight) |
| 98-9F | 255C | 8 | monsters' state (all 00; non-zero = alive, EXODUS 9160) |
| A0-A3 | 2564 | 4 | the four party members' x |
| A4-A7 | 2568 | 4 | the party members' y |
| A8-AB | 256C | 4 | party member state (01) **open** |
| AC-AF | 2570 | 4 | `FF FF 00 00` **open** |

**sure** for the x and y arrays (the code subtracts them and tests the positions), **likely** for
the rest.

## 6. The party and the roster

**ROSTER.ULT** (1280 bytes = 20 characters of 64 bytes) and **PARTY.ULT** (274 bytes = an
18-byte header and **four** characters of 64 bytes, at 14CC in EXODUS: `address = 14CC + 40h *
slot`). The shipped files are all zero (a new game). A slot is empty when its first byte is 0.

### Character record (64 bytes)

| offset | what | |
|---|---|---|
| 00-09 | name, at most 9 letters, NUL ended (BOOTUP 1BD7: `cx = 9`) | sure |
| 0A-0D | not seen used | open |
| 0E | **marks** in bits 7-4 (Kings, Snake, Fire, Force: tables at 6DB1 "Mark of ...") and **cards** in bits 3-0 (Death, Sol, Love, Moons) as bit flags; the position bit is `1 << (4 + (y & 3))` (EXODUS 957A) | likely |
| 0F | torches (BCD): the "Ignite a torch" command (EXODUS 5CC9) takes one | sure |
| 10 | roster slot flag: 00 free, FF **chosen for the party** while "Form the Party" runs (BOOTUP 1814, 18D0) | likely |
| 11 | status letter: `G` good, `P` poisoned, `D` dead, `A` ashes (BOOTUP 0D5D) | sure |
| 12-15 | strength, dexterity, intelligence, wisdom (BCD, one byte each) | sure |
| 16 | race letter: `H` human, `E` elf, `D` dwarf, `B` bobbit, `F` fuzzy | sure |
| 17 | class letter: `F`ighter `C`leric `W`izard `T`hief `P`aladin `L`ark `B`arbarian `D`ruid `I`llusionist `A`lchemist `R`anger | sure |
| 18 | sex letter: `M`, `F`, `O` (other) | sure |
| 19 | magic points (BCD): spells subtract their cost (EXODUS 5E35) | likely |
| 1A-1B | hit points (BCD word) | sure |
| 1C-1D | maximum hit points (BCD word) | likely |
| 1E-1F | experience (BCD word; gains cap at 9999: EXODUS 5D4D-5D5F) | sure |
| 20 | food, hundredths (the byte below the food word; subtracted with borrow into 21-22, EXODUS 70E4) | likely |
| 21-22 | food (BCD word) | sure (BOOTUP shows it under "Food:") |
| 23-24 | gold (BCD word) | sure ("Gold:") |
| 25 | gems | sure (EXODUS 1F05, the "Peer at gem" command; the shop at ABBD prices them with 4Bh) |
| 26 | keys | sure (the "Unlock" command, EXODUS 1FF8; the shop prices them with 32h) |
| 27 | powders | sure (the "Negate Time" command, EXODUS 5D00) |
| 28 | armour worn: index 0-7 into Skin, Cloth, Leather, Chain, Plate, +2 Chain, +2 Plate, Exotic | sure |
| 29-2F | armours owned: a count for each of the first 7 (the 8th, Exotic, is a flag in the party header) | likely |
| 30 | weapon readied: index 0-15 into Hand, Dagger, Mace, Sling, Axe, Bow, Sword, 2-H-Swd, +2 Axe, +2 Bow, +2 Swd, Gloves, +4 Axe, +4 Bow, +4 Swd, Exotic | sure |
| 31-3F | weapons owned: a count for each of the first 15 (Exotic is a flag in the header) | likely |

New characters get (BOOTUP 1AFF-1B1F): status `G`, party flag 0, hit points 150, max hit
points 150, food 150, gold 150, one armour of kind 0 (Skin) and one weapon of kind 0 (Hand).
Their strength, dexterity, intelligence, wisdom, race, class and sex come from the creation screen
(BOOTUP 1C01-1CBF).

### PARTY.ULT header (18 bytes, at 14BA in EXODUS)

| offset | memory | what | |
|---|---|---|---|
| 00 | 14BA | **the party's tile** (a shape number): 3Fh = on foot (shape 63, Ranger), 0Ah on a horse, 0Bh in a frigate (0Ch while a whirlpool takes it) | sure |
| 01 | 14BB | not read | open |
| 02 | 14BC | **where the party is**: 00 Sosaria, 01 inside a dungeon (the torch command works only here), FF Ambrosia (EXODUS 21DB). Others seen in compares: 02, 04 (set while the shrine runs), 80 | likely for 00/01/FF, open for the rest |
| 03-06 | 14BD | **move counter**, 8 digits of BCD, incremented by EXODUS 7E02 and printed with "moves" at the end of the game (EXODUS A46F, text at A24A) | sure |
| 07 | 14C1 | number of characters in the party (1-4) | sure |
| 08-09 | 14C2 | position (x, y) where the party stands | sure |
| 0A-0D | 14C4 | not read directly | open |
| 0E-11 | 14C8 | four flags, `FF` = not yet found: 14C8 and 14CA reduce the weapon menu (18, 17 or 10 entries), 14C9 and 14CB the armour menu (10, 9 or 7) | likely |

The party's current position on the map is not in the file: EXODUS keeps it at 15CC (x) and 15CD
(y) and loads it from 14C2 when the game starts and after a dungeon (EXODUS 6458, 2532). 15CE
is the **light flag**: "Ignite a torch" sets it (EXODUS 5CEA), it is cleared at start-up, and the program calls the dungeon overlay at 0100 only while it is
set (EXODUS 9630-9648), so a dungeon is dark without a torch. 15CF is the dungeon level (0-7)
and 15D0 a counter that "Negate Time" sets to 10 (EXODUS 5D0B).

## 7. The intro files

**NAME.DAT** (640 bytes): a list of 266 (x, y) points (x never 0), ended by x = 0; the rest is
zero. ULTIMA.COM plots them in pairs of cells with y counted from the bottom (192 - y), with a delay
between points (ULTIMA 5E68): the **wavy line under the title** (`u3fmt.py name`). **sure**

**ANIMATE.DAT** (5888 bytes): four pictures of the party facing the dragon, each as four copies
shifted by one pixel, so the program can move it in steps of a pixel: **4 pictures x 4 shifts x
368 bytes**, each 16 rows of 23 bytes (92 pixels, even rows in order, no bank interleave).
ULTIMA 6035-6069 selects `picture * 1472 + (x & 3) * 368` and draws 16 rows of 23 bytes. **sure**
(rendered: `u3fmt.py animate`)

**DEMO.ULT** (114 bytes): a 19 x 6 block of shape numbers drawn with K26E8 at the title screen of
BOOTUP's menu (a strip of landscape with a castle). **sure**

**MOVES.ULT** (1024 bytes): the script that changes DEMO's block over time: 512 steps; step `i`
has a **cell number** in byte `i` and a **value** in byte `512 + i`. A cell number of FF is a
pause of `value` rounds; otherwise cell `cell` becomes `value >> 1` and the block is redrawn
when that is 8 or more (BOOTUP 12D3-1311). **sure** for the structure.

## 8. DUNGEON.DAT is code

DUNGEON.DAT (1866 bytes) begins with `E9 44 03`, a `jmp 0447`. It is a **machine-code overlay**:
EXODUS loads it over the map buffer at 0100 whenever it enters a dungeon (the dungeon maps are at
0900, past its end at 084A) and calls 0100 while the light flag (15CE) is set, passing the
party's position (x, y) in `BX`, its facing (0-3) in `AL` and the level in `AH` (it stores them
at 0103-0106; EXODUS 963D-9648). It draws the 3D corridor view into the screen (writes to B800:), reading
the cells through `lea bx,[bx+0900h]` (its last routine). 0103-0446 are its tables (offsets of
the view's walls and the like); the code starts at 0447. **sure** (disassembly: its first
instructions are `pushf; push ax; push es; mov [0103],bx; mov [0105],al; mov [0106],ah; mov
ax,0B800h; mov es,ax`)

This makes **DUNGEON.DAT a fourth program** of the game, in the same position as the three COM
images: it should be rebuilt from source too (docs/PLAN.md, phase 4b). Its references to EXODUS
(calls into EXODUS and the library, the map buffer) are absolute addresses into the running
EXODUS.BIN.

## 9. Memory overlays: what shares an address

The programs reuse memory for different files; a change that moves one of them must keep the
others consistent.

- **0100-1327 in EXODUS** is the map file (4648 bytes). In a dungeon it holds DUNGEON.DAT (0100-
  084A) and, from 0900, the dungeon file (0900-1189), whose messages sit at 1100: the town
  speech label L1100 and the dungeon message table are the same memory. The entry vector at 1328
  must stay right after the buffer: BOOTUP jumps through it.
- **24C4-2574 in EXODUS** is the start-up code. After EXODUS is running (the code ends with
  `call` into the main loop and does not come back), the same memory is used to load the
  **combat maps and the shrine/fountain/brand/time pictures** (`lea bx, L24C4`, 79h or 0B0h bytes)
  and as the 11 x 11 view buffer the library draws with K2CAA (library X0109 is this address in
  EXODUS). The combat arrays are therefore referenced as labels inside the start-up code
  (`L2544`, `L254C`, `L2564` ...: they appear in the sources as `L2542+2`, `L254C`, ...). If the
  start-up code's size changes, those labels move away from `L24C4 + 80h`, `+88h`, ... and the
  combat arrays would break. **Fixed in phase 4**: the sources now write them as `L24C4+0A0h`,
  `L24C4+0ACh[bx]` and so on (`bufrel` in `tools/u3an.py`), so the start-up code can be edited
  (checked by inserting 5 bytes after `L24C4`: the arrays stay at `L24C4 + offset`).
- **BOOTUP and ULTIMA** use library K01A9 for the tiles and K15A9 for the characters, and the
  roster at 02CE, party at 01BC (BOOTUP only).

## 10. Open questions

- The meaning of the movement code and of the two high bits of the talk code (section 3), the low
  bits of the dungeon cells (section 4), the 7 bytes at the start of a combat file's tail and the
  two 4-byte arrays at its end (section 5), and the party header's offsets 01, 0A-0D (section 6).
  They are read by code that phase 5 (modules by subsystem) will name; the file contents above are
  exact meanwhile.
- No shipped ROSTER.ULT or PARTY.ULT contains a character, so the character record's field layout
  is from the code only. A save from a played game (the GOG `cloud_saves/` folder is empty) would
  confirm it: `python3 tools/u3fmt.py roster FILE` and `party FILE` decode one.
- Whether shapes 64-79 are pictures of weapons, or what else.
- The manual (`gamedata/Ultima_3_manual.pdf`) is a scan with no text layer, so the fields and
  names above were **not** checked against it; an OCR pass (race and class tables, item prices,
  spell list) would be a good independent check.
