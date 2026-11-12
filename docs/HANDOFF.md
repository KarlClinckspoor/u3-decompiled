# Handoff: Ultima III decompilation (u3-decompiled)

State as of 2026-11-12: phases 0-6 of docs/PLAN.md done (phase 3 statically; the play test of a
shifted build is still to do). Read this first, then docs/PLAN.md and docs/FORMATS.md.
The sister projects `../u1-decompiled` and `../u2-decompiled` are the models for conventions
and tools.

## Headline

**All four files (three programs and the DUNGEON.DAT overlay) rebuild byte-identical** from `src/` with `python3 tools/build.py` (~8 s),
with MASM 4.00 and with MASM 3.00 (`ASM=MASM3`). **The shared library is one source**,
`src/LIB.INC`, linked into each program as a module of its own:

| file | bytes | sha1 | modules |
|---|---|---|---|
| ULTIMA.COM | 36692 | 2736836127771823f9ed1463f306400a36bde0e2 | UDATA, INTRO, LIB (3) |
| BOOTUP.BIN | 19572 | d30df2917fbeae202f62dbf34c1ab41ba4988983 | BDATA, TITLE, ORGANIZE, CREATE, LIB (5) |
| EXODUS.BIN | 44234 | 06f5ef9b9dfb4f86a0edf1e723e90a34df651705 | 18 subsystem modules and LIB (19), docs/MAP.md |
| DUNGEON.DAT | 1866 | 2d04c79751fa1e1b27f14922d0d9e17872173028 | DUNGEON (1) |

Each `src/TARGET/LIB.ASM` is three lines: it defines `PROG_ULTIMA`, `PROG_BOOTUP` or
`PROG_EXODUS` and includes `LIB.INC`. No instruction is written as `db`. `src/` is frozen and
is the source of truth: edit by hand and run `tools/build.py` after every change. The
generators re-derive pieces; they never write to src/.

## Toolchain facts (proven)

- MASM 4.00 and MASM 3.00 produce the same bytes for all three files. Forward jumps were
  written SHORT almost everywhere: there are only 1/2/6 `EB xx 90`. That is consistent with
  MASM, so no other assembler is needed. LINK 3.05 links them.
- COM build: every module has `CODE SEGMENT ... PUBLIC`, the first one `ORG 100h`, ASSUME
  CS/DS/ES/SS:CODE. LINK writes an EXE ("no STACK segment" warning, harmless) whose image
  starts with 0100h zero bytes; build.py writes the image from 0100.
- The library module is `CODE SEGMENT PARA PUBLIC`. LINK's paragraph alignment produces the
  zero bytes before it (BOOTUP 1E34-1E40, ULTIMA 6113-6120, EXODUS 298E-2990), exactly as in
  the originals. The program modules are BYTE.
- MASM runs out of memory on EXODUS.BIN as one module (MASM 3: "Out of Memory"; MASM 4 dies
  silently). Modules of ~9 KB are fine (30 KB+ symbol space free in each). gen.py cuts at
  routine entries that no 8-bit relative branch crosses: MASM cannot make a short jump to an
  external. Cross-module labels are EXTRN/PUBLIC, declared inside the segment.
- MASM encodes `xchg r1,r2` with r1 in the reg field; capstone prints the rm operand first,
  so gen.py swaps them (43 places).
- `lea bx,[bx+0000]` (ULTIMA) keeps its 16-bit displacement only with a relocatable symbol.
  PSP offsets (L005C, L006C, L00FE, ...) and program symbols that live in the PSP are labels
  placed with `ORG` before `ORG 100h`.
- A relocatable immediate (`mov si, offset K0124`) always gets 16 bits, as in the originals.
- capstone names 98/99 `cwde`/`cdq`; in 16-bit code they are `cbw`/`cwd`.
- Never kill all DOSBox processes: other projects' sessions run their own. A LINK given a
  missing object waits for input forever; the build guards it with `IF EXIST`.

## The shared library (phase 2)

- **It was a separately assembled module.** It starts on a paragraph in every file, and its
  first 256 bytes are the stack each program sets up with `lea sp, K0000` / `add sp, 100h`.
  Labels in it are `Kxxxx`, the offset from its start in BOOTUP.BIN (K2BF0 = BOOTUP 4A30, load
  a file). K0100/K0101 are the text cursor, K25A9 the screen segment.
- **ULTIMA.COM links the identical object.** Its copy differs from BOOTUP's only in relocated
  words.
- **EXODUS.BIN links a slightly different version**, in two places, written `IFDEF
  PROG_EXODUS`:
  1. The disk-check stub and routine (BOOTUP 44B0-4503). The stub `K2670` returns AL=0 in
     BOOTUP and ULTIMA and AL=0FFh in EXODUS. The real track-9 check after it is reached by
     nobody. Only ULTIMA calls the stub (5D8D): it stores AL in L432C, and the intro hangs
     (5DD1) while L432C is 0FFh. So **the protection is defeated by the stub returning 0**.
     Whether Origin or GOG did that needs an original disk.
  2. The zero area before the sound flag (BOOTUP 4B76-4B80) is 10 bytes shorter.
- How the source was proven (tools/genlib.py): each copy's library was compared with
  BOOTUP's, aligned. Every word that differs is an address. It is **internal** if all three
  point to the same place in their own library (96 such words, written Kxxxx or `offset
  Kxxxx`), or **external** if it points into the program. External words are written after
  their value in BOOTUP.BIN: X0103, X0109, X01A9, X01AD, X01B1, X01B5, X01BE (19 uses). Each
  program defines them as PUBLIC labels at its own addresses (in ULTIMA, X0103/X0109 are 0000
  and X01A9-X01B5 are in the PSP at 00A0-00AC: tables ULTIMA does not have). Words that are
  the same in all three stay numbers (PSP offsets, video segments, constants). Relative
  branches across EXODUS's shorter parts are checked to reach the same place.
- The library's text is BOOTUP's copy, disassembled with the union of what the three
  programs reach. The programs reference 81 of its labels (the PUBLICs in LIB.INC).

## Relocatable (phase 3)

Every address the code uses is now a symbol. Proof so far: `tools/shift.py` pads every program
module (19/5/7/11 NOPs by default; also checked with 3/13/21/9), rebuilds, and finds only
addresses moved. The library moved by one or two paragraphs with it. The shifted files are
runnable in build/shift/; `tools/play.py build/shift --dir build/play_shift` plays them. **Not
yet played**: a play-through of the shifted build is what catches an address still written as
a number. That needs Karl, or a session with screen access.

What phase 3 had to find by hand (all in `u3an.TARGETS`, each checked against its use):
- **Immediates that are addresses** (`immaddr`, written `offset Lxxxx`): the int 23h/24h
  handler offsets in all three, ULTIMA 5F8E (`add si, offset L0115`: the picture buffer plus a
  row offset), BOOTUP 1D69 (`mov bx, offset L02CE`: the roster, 40h bytes per character). The
  survey (`tools/cands.py`) lists every 16-bit immediate in the image range. All the others are
  constants: sizes (1228h = a map file, 4000h, 1400h, ...), CGA screen offsets (1CC0h, 0530h,
  0DC2h, ...; DI for the library's tile drawer K26E8 is a screen offset), row/column pairs in
  DX, key codes (3920h, 011Bh, ...), delay counts (ULTIMA 9FFh, 9000h), BIOS 0040:0010 (410h),
  the planted `int 21h` (21CDh) and `jmp word ptr [1328h]` (26FFh, 1328h), and the DTA/load
  address 100h (the next program always loads at 0100, so it stays a number).
- **Data-pointer tables** (`ptrs`, written `dw Lxxxx`): 7 in BOOTUP (status, weapons and
  armour, two menus, sexes, races, classes) and 18 in EXODUS (map file names, command prompts,
  spell names, the 136 tile/monster/item/spell names at 6556, menus, marks and cards, long
  messages and verses; plus the entry vector at 1328). Found from indexed word loads
  (`tools/ptrtabs.py`) and from `lea si, table` passed to the menu routine; lengths from the
  strings and the code. The menus' tables end with two "Quit" pointers followed by their key
  string (e.g. 7928 "Q",1Bh,"ABCD...").
- **DS is video memory** in four short EXODUS routines (`dsforeign`: 717C-71BA, 71C6-71E7,
  71F0-722F, A496-A4B3: `push ds` / `mov ds, K25A9` / XOR on the screen / `pop ds`). Their
  operands are screen offsets. The generator had made labels of them (L2000, L204F+1, L00A0);
  they are numbers now.
- In EXODUS, `L0100`..`L1327` (the map buffer, where SOSARIA.ULT and the other maps are
  loaded) is addressed with labels inside the buffer: L0900, L1100 (the talk-string offsets in
  a town file), L1280 (monsters). They move with the buffer, which is right as long as the
  buffer stays first. The entry code at 24C4 is reused as a buffer after start-up
  (`lea bx, L24C4[bx]`; also the library's X0109 in EXODUS).
- **Cross-program constants**, which stay numbers and must not move: BOOTUP plants
  `jmp word ptr [1328h]` to enter EXODUS. 1328h is EXODUS's entry vector, right after the
  1228h-byte map buffer at 0100. So EXODUS1.ASM must keep the buffer and the vector first,
  and shift.py pads EXODUS only after the vector. Every program is loaded at 0100 and
  ULTIMA's/BOOTUP's entry is the `jmp` at 0100.
- No program operand with a cs:/ss:/es: prefix points into the image, and no DS operand
  points past the end of a file.

## Names and comments (phase 6)

**Every label in all sources has a name** (`tools/dups.py`: 0 labels named after an address, no
duplicates), every module has an overview header and every routine a header; all four files
still rebuild identical with MASM 4.00 and 3.00, and shift.py passes. How it was done:
- Tools: `tools/syms.py` (symbol table per scope, addresses from the `;@` tags), `tools/rename.py`
  (checked renames; scope = a program for its own labels, `lib` for the shared library names and
  the X symbols), `tools/lint.py` (CRLF, line length, tags; `--code-unchanged REV` checks that only
  names and comments changed), `tools/dups.py`, `tools/applyprops.py`. Conventions:
  docs/NAMING.md; the workers' brief: docs/BRIEF-naming.md.
- 147 established names first (`names/*-core.map`), then eight workers in parallel on disjoint
  files (the library; EXODUS in five groups; BOOTUP + ULTIMA; DUNGEON.DAT): about 1,240 local
  renames with `--only`, and 710 proposals for names other modules use, applied centrally
  (`names/proposed-*.map`, `names/integrated-*.map`). Every map is kept in `names/`.
- Integration decisions: the library's X01BE and X0103 merged with the programs' own labels at
  the same byte (now `Location` and `CombatPlayer` everywhere); corrections of earlier names that
  the code contradicted (`GateState`/`GatePos` are the whirlpool: `WhirlpoolX/Y`; `MonMove` is
  `MonUnder`; the four party flags are `ExoticWeaponFound`, `ExoticArmourFound`,
  `ExtraWeaponsOk`, `ExtraArmoursOk`); the module TRANSACT is really the H command and is now
  HAND; the offset label 80h is the neutral `Ofs80h` (it serves two arrays).
- What the code revealed (mechanics, bugs, dead code, the protection removal): docs/FINDINGS.md,
  and the workers' notes in `names/notes-*.md`. docs/FORMATS.md and docs/MAP.md are corrected.

## Modules (phase 5)

Every program is split into modules named for their subsystem; docs/MAP.md lists them (address
range, size, what is in them, with the command key tables). EXODUS: EXDATA, LOOP, WORLD, VIEW,
[LIB], ITEMS, MAGIC, SHRINE, PARTY, ACTIONS, TRANSACT, EQUIP, DUNMOVE, CMDTAB, COMBAT, DUNEVENT,
TEXT, ENDING, TOWNS. The cut addresses are `modules` in `tools/u3an.py`; gen.py snaps each to a
valid place (none needed moving). `tools/routines.py TARGET [FROM [TO]]` is the survey they came
from (routines, callers, dispatch entries, strings) and `tools/modmap.py` prints the module
table. Module headers say what the module is. The first module of each program (EXDATA, BDATA,
UDATA) holds the program's data, and TEXT, CMDTAB are data-only modules, so the data is where
the original source had it, not split by use. shift.py pads every module (it passes with 18
paddings in EXODUS). A remaining weakness of the split: data in the middle of the code (the
tables at 6493-6B91, 7708-7AEA, 84DB-888B, A3A7) belongs to the module it sits in even where one
routine of another module uses it; moving it is a hand job for the readability pass.

## Data formats (phase 4)

docs/FORMATS.md describes every data file (loader, address, layout, with sure/likely/open marks)
and `tools/u3fmt.py` reads and renders them: `shapes`, `chars`, `cga FILE.IBM`, `map FILE`,
`dungeon FILE`, `combat FILE`, `demo`, `animate`, `name`, `moves`, `party [FILE]`, `roster
[FILE]`, and `check` (parses all 45 data files). PNGs go to build/formats/ (not committed: they
are the game's art). Highlights:
- Tiles are 16x16, 64 bytes, **even scan lines first, then odd** (the two CGA banks); the map
  byte is a multiple of 4 and `byte >> 2` is the shape number. Rendering BRITISH.ULT gives
  Lord British's castle at once, which confirms the layout.
- A town file is the 4096-byte map, 4 to 8 speeches (offset table + strings), five arrays of
  32 creature slots (tile, movement, x, y, talk code) and 8 state bytes (the two moons'
  phases and counters on Sosaria). Dungeons: eight 16x16 levels (bit 10h ladder up, 20h ladder
  down, 80h wall) and one message per level.
- PARTY.ULT = 18-byte header + four 64-byte characters; ROSTER.ULT = 20 characters. The record
  layout (name, status, stats, race/class/sex letters, HP, MP, experience, food, gold, gems,
  keys, powders, torches, marks/cards, armour and weapon tables) is decoded from the code; the
  shipped files are empty, so **no real character was available to check it against**.
- **DUNGEON.DAT is machine code** (`jmp 0447` first): an overlay loaded over the map buffer at
  0100 in a dungeon that draws the 3D view into B800. It is a fourth program and rebuilds
  identical from `src/dungeon/DUNGEON.ASM` (phase 4b: gen.py and regen.py unchanged apart from
  the `equs` of its two EXODUS addresses, `DMAP`=0900 and `ROWTAB`=132A; no library, no external
  calls; shifting it moves only address operands, 12 of them, checked).
- ANIMATE.DAT = 4 pictures x 4 one-pixel shifts of the party facing the dragon (16 rows of 23
  bytes). NAME.DAT = the title's wave line (266 points). MOVES.ULT/DEMO.ULT = the menu's
  scrolling scenery script.
- **Hazard found and fixed**: EXODUS loads the combat maps over its own start-up code (24C4-2574)
  and the sources addressed them through labels inside that code. They are now `L24C4+offset`
  (`bufrel`), so the start-up code can change size (docs/FORMATS.md section 9).

## Findings about the program

- **Three COM images, each loading the next over itself.** The running program opens the next
  file through the FCB at PSP:5C with the record size set to the file size, plants `int 21h`
  at 00FE (ULTIMA: `mov [00FE],21CDh`) and jumps there with AH=14h. The read lands at 0100
  over the running code, and execution falls through into the new image. ULTIMA does this at
  5E18-5E54 (falls into BOOTUP's `jmp 120A` at 0100). BOOTUP does it at ~1470-1491: it plants
  `int 21h` / `jmp word ptr [1328h]` at 00FA and does `jmp sp` there. EXODUS.BIN's first
  non-zero word, at 1328, is its entry 24C4.
- **EXODUS 0100-1327 is the map buffer**: SOSARIA.ULT (0x1228 = 4648 bytes) is loaded there
  at 251A. The file has zeros there. EXODUS 9648 calls 0100 when the byte at 15CE is set
  (written `call near ptr L0100`). What code would sit at 0100 then is open: a .ULT file
  with a code stub?
- **Interrupt hooks**: each program points int 23h (Ctrl-Break) and int 24h (critical error)
  at bytes just before its entry (ULTIMA 5CDF/5CDD, BOOTUP 1209/1207, EXODUS 24C3/24C1).
- **Jump tables** (all in u3an.TARGETS): the sound table (12 words: ULTIMA 8E61, BOOTUP 4B81,
  EXODUS 56C1, indexed by `not al` for codes F4-FF; now in LIB.INC); EXODUS command dispatch
  190B (33 keys at 1887, prompt-string pointers at 18C9), 774A (keys 7708, strings 778C), 85BB
  (keys 8579), spells 594B/596B (16 each; names via 590B), and 76F8, 85FD, 77CE, 654C, 794D,
  A3A7, 9BEC.

## Repository

| file | what |
|---|---|
| `src/LIB.INC` | the shared library (frozen 2026-11-09 from genlib.py's output) |
| `src/TARGET/*.ASM`, `NAME.lnk` | the program modules and LIB.ASM, in link order |
| `tools/build.py` | assemble (MASM 4.00, `ASM=MASM3` for 3.00), LINK 3.05, image from 0100, sha1 check |
| `tools/u3an.py` | per-target facts (entries, tables, data areas, module size limit, `lib`) and recursive disassembly; run it for coverage and indirect branches |
| `tools/gen.py` | the program generator (labels, modules, PSP labels, xchg order, the library as its own module, aliases for the library's externals) |
| `tools/genlib.py` | the library generator: ranges, alignment of the three copies, internal/external address words, the EXODUS conditionals |
| `tools/regen.py` | gen → MASM with listings → LINK → compare, forcing differing lines to `db` (none needed); `regen.py TARGET [WORKDIR] [MASM4/MASM3]` |
| `tools/shift.py` | relocation test: pads every program module, rebuilds into build/shift/, checks that only addresses moved (`--pad 19,5,7,11`) |
| `tools/play.py` | play a build in a DOSBox window with GOG's settings, from a copy of the data files (`play.py [BUILDDIR] [--dir DIR]`) |
| `tools/u3fmt.py` | readers and PNG renderers for every data file (docs/FORMATS.md); `u3fmt.py check` |
| `tools/routines.py`, `tools/modmap.py` | the routine survey for the split, and the module table of docs/MAP.md |
| `tools/syms.py`, `rename.py`, `lint.py`, `dups.py`, `applyprops.py` | the naming tools (docs/NAMING.md) |
| `tools/cands.py`, `tools/ptrtabs.py` | phase 3 surveys: immediates and operands that might be addresses; indexed word tables and what they point to |
| `tools/dos.py`, `setup.py`, `fat12.py` | DOSBox runner and toolchain unpacking (from u2) |

Git: `master`, local only.

## Next steps

1. **Play the shifted build** (`tools/play.py build/shift --dir build/play_shift`; make it with
   `tools/shift.py`): intro, menu, roster, a character, journey onward; in the game walk, enter a
   town, talk, buy, cast, fight, enter a dungeon with a torch. A break points at an address still
   written as a number. Also try the bugs of docs/FINDINGS.md that are marked unverified.
2. Check the character record against a real save (`u3fmt.py roster FILE`, `party FILE`).
3. Phase 7 (optional): a port (docs/PLAN.md). The speed-dependent parts are listed at the end of
   docs/FINDINGS.md; FCB file I/O, CGA and the PC speaker are the rest.
4. Smaller: OCR the manual and check FORMATS.md against it; decide whether to move the data blocks
   that sit inside another module's range (6493-6B91, 7708-7AEA, 84DB-888B) to their users.
