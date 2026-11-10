# Plan: Ultima III decompilation (u3-decompiled)

Written 2026-11-09. **Status: phases 0-4 done (2026-11-09), phase 3 statically: all three
files rebuild byte-identical from `src/` with MASM 3.00 and 4.00, no `db` instructions, one
shared library source (`src/LIB.INC`), and every address a symbol (tools/shift.py). A play test
of a shifted build is still to do. See docs/HANDOFF.md for the results and what changed against
the survey below.**

It draws on the two sister projects: `../u1-decompiled` (docs/HANDOFF.md,
MAP.md, MATCHING.md, build/pilot/BRIEF.md) and `../u2-decompiled` (docs/HANDOFF.md). It also
uses a first survey of the GOG files in `gamedata/`. The goal is the same as theirs: source
that rebuilds every executable byte for byte with period tools, then readable names, then
(optionally) a port.

## 1. Lessons carried over from U1 and U2

| # | lesson | from | how it applies to U3 |
|---|---|---|---|
| 1 | The gate is a whole-file sha1 match, checked by `build.py` after every change. Generate the source once, freeze it, then edit by hand. | both | Same gate, three targets. |
| 2 | Find out what the code is before choosing a method. U1 was Lattice C (match functions in C); U2 was hand-written assembly (no C, so the work is symbol recovery and readability). | both | U3 is hand-written assembly (§2.3), so it takes the **U2 path**. No C matching. |
| 3 | Generate-and-iterate: recursive disassembly → MASM → LINK → compare. Lines that encode differently get added to a force list and written as `db`; remove those `db`s later. | U2 `gen.py`/`regen.py`/`U2.force` | Reuse the tools. Extend them for COM images, several entry points and large zero buffers. |
| 4 | Toolchain: MASM 3.00 (4.00 gives the same bytes), LINK 3.05, run in headless DOSBox (`gamedata/DOSBOX`). Use a batch file, because DOSBox 0.74's autoexec overflows at ~4 KB. capstone lives in `../u1-decompiled/build/venv`. `setup.py` takes the archives from the sister projects. | both | Copy `dos.py`, `setup.py`, `fat12.py`, `exediff.py` as they are. |
| 5 | MASM 3.00 limits: ~12 KB of symbol space (~900 labels), and it runs out of memory above ~15 KB of code in one module. | both | EXODUS.BIN has ~38 KB of code. Plan for MASM 4.00 or several include files from the start. |
| 6 | Assembler fingerprints are evidence: `EB xx 90` (forward JMP without SHORT), the direction of reg,reg encodings, disp16 on small offsets (= named variables in the source, a free naming hint), stray `2E` prefixes. | U2 | U3's fingerprints differ from U2's (§2.4). Settle the assembler in phase 1. |
| 7 | When the same code sits in several executables, diffing the copies recovers symbols. U1's `xmap.py`/`addrimm.py` found shared modules, and found which immediates are addresses because they differ between copies at different origins. | U1 | U3 has one shared library in all three images (§2.2). This is the main lever. |
| 8 | Make the source relocatable before making it readable: every absolute address becomes a symbol. Test by inserting a NOP and playing. | U2 next steps, U4/U6 | Same. U3 also has contracts *between* programs (§2.1). |
| 9 | Releases can be binary-patched: U2's 1989 EXE has dead islands of old code. Keep them as bytes, labelled. | U2 | Expect the same around the copy protection (§2.5). |
| 10 | U1's ULTIMA.EXE and U2 carried a 1989 protection envelope that a post-link step copies in at build time. | both | The U3 files end in plain code and have no MZ header. Expect **no** envelope step (still to be confirmed). |
| 11 | Repo hygiene. Never commit gamedata or tool archives. `.gitattributes` sets `*.ASM -text` (MASM needs CRLF). Git Bash `sed -i` drops CRs, so edit .ASM files with the Edit tool or binary-mode Python. Don't name a tool `dis.py`: it shadows Python's `dis` and breaks capstone (U2 did; rename it here). Follow the git author and trailer conventions in U1's HANDOFF. | both | Set up in phase 0. |
| 12 | Parallel agents work when each gets a disjoint address range and its own work files, follows a written brief, and one integrator merges. | U1 `BRIEF.md` | Use it for the split and the readability pass (phases 5-6), not before the source is relocatable. |

## 2. What U3 is (survey of the GOG files)

### 2.1 Three COM images, each loading the next over itself

| file | bytes | sha1 | role | own entry |
|---|---|---|---|---|
| ULTIMA.COM | 36692 | 27368361… | Intro: loads BLANK.IBM, EXOD.IBM (16 KB CGA screens), NAME.DAT, ANIMATE.DAT; title animation and sound | `jmp 5CE0` at 0100 |
| BOOTUP.BIN | 19572 | d30df291… | Main menu: Organize a Party, roster, character creation ("Entry# (1-20 Only!)"). Loads SHAPES, ROSTER, PARTY, DEMO, MOVES, CHARSET | `jmp 120A` at 0100 |
| EXODUS.BIN | 44234 | 06f5ef9b… | The game. Loads PARTY, DUNGEON.DAT, the 22 .ULT maps, the CNFLCT_* combat maps; command prompts A-Z | word at 1328 = 24C4 |

- None has an MZ header. All are loaded at CS:0100 with CS=DS=ES=SS: COM layout.
- **Chain load**: the running program opens the next file by FCB at PSP:5C and sets the record
  size to the file size. It plants `int 21h` just below 0100 and jumps there with AH=14h
  (sequential read, DTA=0100). The read overwrites the running program and execution falls
  into the new image. ULTIMA does this at 5E18, BOOTUP at ~1470. BOOTUP passes EXODUS's entry
  through the vector at 1328, a constant inside BOOTUP that depends on EXODUS's layout.
- EXODUS.BIN 0100-1327 is zeros in the file. It is a buffer the game then fills with a
  0x1228-byte file (load at 251A).
- Each program hooks int 23h and int 24h at start-up (vectors written to 0000:008C/0090), turns
  Ctrl-Break checking off, and seeds from the DOS date and time (ULTIMA).
- State handed between programs through memory: still to be mapped (e.g. flag bytes at 0105
  and 01BE). It becomes a documented contract, shared EQUs.

### 2.2 A shared runtime library inside all three

Each image contains a copy of the same library. It covers text output and cursor, CGA
tile/character drawing (screen segment in a variable), loading a file by name (BOOTUP 4A30 /
ULTIMA 8D10 / EXODUS 557A), the disk check, and the PC-speaker sound routines. Its data comes
with it: the "Calm/North/… Wind" strings, "Unable to read file", "Wrong Diskette!", and
large zeroed buffers.

| image | library data starts | offset from BOOTUP |
|---|---|---|
| BOOTUP.BIN | 1F48 | 0 |
| ULTIMA.COM | 6228 | +42E0 |
| EXODUS.BIN | 2A98 | +0B50 (later parts +0B4A, +0B40) |

- A 9409-byte run (data plus position-independent code) is identical in all three. It stops
  exactly where the first absolute address appears (BOOTUP 4414 `inc byte [1F40]`). So the
  same source was **assembled into each program at a different origin**: it was not copied as
  binary. The small extra shifts in EXODUS mean the library differed slightly per program.
- Consequences: (a) every immediate or displacement that differs between copies is an
  address, so U1's `addrimm.py` method names them automatically; (b) one `LIB.INC`, with
  conditionals for the per-program differences, can serve all three builds.
- Nothing is shared with ULTIMAII.EXE (checked by byte runs). U2's symbol names do not
  transfer. Only its methods do.

### 2.3 Code character

Hand-written 8086. There are no compiler frames (one stray `push bp; mov bp,sp` per image,
inside a save-all prologue). It uses save-all prologues (`push ax bx cx dx [bp] si di`) and
`lea reg,[addr]` for addresses. Delay loops depend on CPU speed (e.g. ULTIMA 5E5A). Sound
goes through port 61h. File I/O is FCB-style DOS calls. Video is CGA. Credits: "(C)-1983 By
James R. Van Artsdalen and Lord British".

### 2.4 Assembler fingerprints (to settle in phase 1)

- `EB xx 90` occurs only 1 / 2 / 6 times (ULTIMA / BOOTUP / EXODUS); U2 has 113. Either the
  author wrote SHORT on nearly every forward jump, or a different assembler was used.
- reg,reg moves are mostly in the 8B/8A form (MASM style), but EXODUS has a fair number of
  89/88 forms (rough count, needs a proper decode).
- No `2E`-prefixed LEA (U2's open question doesn't arise).
- First test: MASM 3.00 and 4.00 through `regen.py`; count forced lines. If the count is
  large, try the other assemblers on hand before accepting `db`s.

### 2.5 Copy protection

Each library copy has an int 13h read of track 9, sector 16 into C000:0000 (BOOTUP 44B3).
That sector does not exist on a normal 9-sector disk. Each also has the "Wrong Diskette!"
message. Find out how the result is used and whether GOG's files are patched around it. If
Karl has an original 1983/84 disk image, comparing against it settles the question (as with
U2's dead islands).

### 2.6 Data files (format hypotheses for phase 4)

| files | bytes | hypothesis |
|---|---|---|
| SOSARIA, AMBROSIA, BRITISH, EXODUS, LCB, MOON, YEW, MONTOR_E/W, GREY, DAWN, DEVIL, FAWN, DEATH .ULT | 4648 | 64×64 map (4096) + 552 bytes of monster/object tables |
| DARDIN, FIRE, M, MINE, P, PERINIAN, TIME .ULT | 2192 | dungeons, probably 8 levels × 16×16 (2048) + 144 bytes |
| CNFLCT_A…S.ULT | 176 | combat map 11×11 (121) + 55 bytes of start positions |
| BRAND, FOUNTAIN, SHRINE, TIME .IMG | 121 | 11×11 maps |
| ROSTER.ULT / PARTY.ULT | 1280 / 274 | 20 characters × 64 bytes / current party and position |
| SHAPES.ULT, CHARSET.ULT | 5120 / 2048 | CGA tiles / font |
| BLANK.IBM, EXOD.IBM | 16384 | raw CGA screens |
| MOVES, DEMO, ANIMATE.DAT, NAME.DAT, DUNGEON.DAT | various | to be identified from the code that loads them |

## 3. Phases

Each phase ends with all three builds identical, a commit, and HANDOFF.md updated.

**Phase 0: repository.** Copy the U2 skeleton: `.gitignore` (gamedata/, build/, archives),
`.gitattributes`, README.md, docs/HANDOFF.md, and the tools `dos.py`, `setup.py`, `fat12.py`,
`exediff.py`, `build.py`, `gen.py`, `regen.py`, `rdis.py`, `refs.py`, `u2an.py` (renamed). Make
`build.py` take a target (`ultima`, `bootup`, `exodus`): MASM → LINK (CODE segment `ORG 100h`,
as U2 does) → strip the EXE to its image from 0100 (a 10-line Python "exe2bin"; same bytes as
DOS EXE2BIN) → sha1 against gamedata. No post-link step. Ask Karl before the first commit
about the default branch (git says `main`, the checkout is `master`).

**Phase 1: frozen, identical sources (U2 method).** Teach `gen.py`:
- COM loading
- entry points: the 0100 jumps, EXODUS's vector at 1328, the int 23h/24h handlers (found
  from the IVT writes)
- indirect jumps and jump tables (find them with `rdis.py`)
- any routine that reads data after its return address (U2 had inline strings after
  `call 4FDF`; check U3's print routines)
- zero runs emitted as `db n dup(0)`

Order: BOOTUP (smallest) → ULTIMA → EXODUS (split into include files, or use MASM 4.00).
Record the assembler verdict (§2.4). Gate: three sha1 matches. Freeze `src/`.

**Phase 2: one library source.** Pull the shared library out into `src/LIB.INC`, included
by all three, with IF/ENDIF for the per-program differences. Write a U3 `addrimm`-style tool
that aligns the three copies and lists the operands that differ, so they become symbols. Name
the library routines first (print, draw tile, load file, sound, disk check). They are called
from everywhere, which makes the rest easier to read. Gate: three identical builds from one
library source.

**Phase 3: relocatable.** Every absolute DS/CS reference becomes a label; tables become
`dw label`; each forced `db` is resolved. Cross-program constants (EXODUS entry vector,
buffer addresses, flags handed from one program to the next) become EQUs in
`src/SHARED.INC`. Test: insert a NOP near the start of each image and play through title →
menu → party → game in GOG's DOSBox. Each image must still chain-load the next.

**Phase 4: data formats.** Read the loaders and users of each file in §2.6. Write
`docs/FORMATS.md` and small viewers/dumpers in `tools/` (maps to PNG, roster/party fields),
checked against the manual (`gamedata/Ultima_3_manual.pdf`).

**Phase 4b (found in phase 4): DUNGEON.DAT.** It is not data but a 1866-byte code overlay
(`jmp 0447` first) that EXODUS loads at 0100 in a dungeon and calls to draw the 3D view
(docs/FORMATS.md section 8). Rebuild it identical like the three COM images (gen.py with
origin 0100, fixed addresses of EXODUS and the library as symbols).

**Phase 5: modules by subsystem.** Split EXODUS along the command dispatch (the A-Z prompt
table at ~1619), plus movement, combat, dungeon view, towns and talk, shops, magic, moongates
and the endgame. Split BOOTUP (menu, character creation, roster) and ULTIMA (intro, animation)
the same way. Parallel agents with disjoint ranges and a BRIEF.md adapted from U1's.

**Phase 6: readable pass.** Names and comments throughout, using the manual, the data formats,
and the abedegno Exhume skills (`../underworld-exhumed-enhanced/exhume/`: readability-pass,
`syncnames.py`).

**Phase 7 (optional): port.** Use the u4/u6 `port` directories as models. Replace the delay
loops, FCB I/O, the int 13h check and CGA output. Check behaviour against recorded DOSBox
sessions (Exhume's `runtime/port` + `replay`).

## 4. Open questions and risks

- **Assembler**: does MASM reproduce the encodings, given the near-absence of `EB xx 90`? If
  not, which assembler did Van Artsdalen use in 1983-84?
- **Copy protection**: is it intact or patched in the GOG files? Is an original disk image
  available for comparison?
- **Library drift**: how much do the three copies differ? Many differences would mean three
  library sources instead of one with conditionals.
- **EXODUS size**: MASM limits (lesson 5). Decide early between MASM 4.00 and include files.
- **Zero buffers**: large `dup(0)` areas must land exactly. Watch MASM's handling of ORG and
  DUP in a single segment.
- **No envelope expected**: confirm there are no trailing bytes after the last instruction or
  data in each file.

## 5. First session checklist

1. Phase 0 skeleton and `build.py` for three targets; a NUL-source smoke test of MASM + LINK +
   strip.
2. Run `gen.py` and `regen.py` on BOOTUP.BIN until it rebuilds identical; note the forced
   lines and the assembler verdict.
3. Repeat for ULTIMA.COM, then EXODUS.BIN.
4. Write HANDOFF.md in the sister projects' format (state, toolchain facts, next steps, loose
   ends).
