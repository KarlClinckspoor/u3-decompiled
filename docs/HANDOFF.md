# Handoff: Ultima III decompilation (u3-decompiled)

State as of 2026-11-09, after phase 2 of docs/PLAN.md. Read this first, then docs/PLAN.md.
The sister projects `../u1-decompiled` and `../u2-decompiled` are the models for conventions
and tools.

## Headline

**All three files rebuild byte-identical** from `src/` with `python3 tools/build.py` (~8 s),
with MASM 4.00 and with MASM 3.00 (`ASM=MASM3`). **The shared library is one source**,
`src/LIB.INC`, linked into each program as a module of its own:

| file | bytes | sha1 | modules (`src/TARGET/NAME.lnk`) |
|---|---|---|---|
| ULTIMA.COM | 36692 | 2736836127771823f9ed1463f306400a36bde0e2 | ULTIMA (0100-6113), LIB (6120-9054) |
| BOOTUP.BIN | 19572 | d30df2917fbeae202f62dbf34c1ab41ba4988983 | BOOTUP (0100-1E34), LIB (1E40-4D74) |
| EXODUS.BIN | 44234 | 06f5ef9b9dfb4f86a0edf1e723e90a34df651705 | EXODUS1 (0100-298E), LIB (2990-58B4), EXODUS2 (58B4-7D74), EXODUS3 (-9630), EXODUS4 (-ADCA) |

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
  A3A7, 9BEC. The string-pointer tables in the programs (18C9, 778C, 590B, 6540) are still
  plain data words; they become `dw Lxxxx` in phase 3. (The library's are already symbolic.)

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
| `tools/dos.py`, `setup.py`, `fat12.py` | DOSBox runner and toolchain unpacking (from u2) |

Git: `master`, local only.

## Next steps

Phase 3 (relocatable) in docs/PLAN.md. Concretely:
1. Immediates that are addresses in the program modules: the int 23h/24h handler offsets
   (`mov word ptr es:[8Ch], 1209h`), loads like ULTIMA 5DBC `mov si,9FFh`, the chain-load
   constants (BOOTUP's 1328h is EXODUS's entry vector, a cross-program constant), the
   string-pointer tables. Check each 16-bit immediate as U2 did. The library needs none of
   this: its addresses are already proven and symbolic.
2. Program operands with a segment prefix (`ss:`, `cs:`, `es:` on program addresses) and
   displacements past the end of the file (buffers beyond the image) are still numbers.
3. Then the NOP test: insert a byte near the start of each program module and play through
   intro → menu → game in DOSBox.
4. Later (readability): name the library first. It is called from everywhere: print string
   at row DH, column DL K2C7E (BOOTUP 4ABE), put character K25CC (440C), read key K29BD,
   load file K2BF0 (4A30), sound K2D59 (4B99), ...
