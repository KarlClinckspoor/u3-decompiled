# Handoff: Ultima III decompilation (u3-decompiled)

State as of 2026-11-09, after phase 1 of docs/PLAN.md. Read this first, then docs/PLAN.md.
The sister projects `../u1-decompiled` and `../u2-decompiled` are the models for conventions
and tools.

## Headline

**All three files rebuild byte-identical** from `src/` with `python3 tools/build.py` (~8 s):

| file | bytes | sha1 | source |
|---|---|---|---|
| ULTIMA.COM | 36692 | 2736836127771823f9ed1463f306400a36bde0e2 | `src/ultima/ULTIMA.ASM` |
| BOOTUP.BIN | 19572 | d30df2917fbeae202f62dbf34c1ab41ba4988983 | `src/bootup/BOOTUP.ASM` |
| EXODUS.BIN | 44234 | 06f5ef9b9dfb4f86a0edf1e723e90a34df651705 | `src/exodus/EXODUS1-4.ASM` (4 modules) |

No instruction is written as `db`: gen.py's first pass assembles identically with both MASM
4.00 and MASM 3.00. `src/` is frozen and is the source of truth from now on; edit by hand and
run `tools/build.py` after every change.

## Toolchain facts (proven)

- MASM 4.00 and MASM 3.00 produce the same bytes for all three files. Forward jumps were
  written SHORT almost everywhere: there are only 1/2/6 `EB xx 90`. That is consistent with
  MASM, so no other assembler is needed. LINK 3.05 links them.
- COM build: one segment `CODE SEGMENT BYTE PUBLIC`, `ORG 100h` in the first module, ASSUME
  CS/DS/ES/SS:CODE. LINK writes an EXE ("no STACK segment" warning, harmless) whose image
  starts with 0100h zero bytes; build.py writes the image from 0100.
- MASM runs out of memory on EXODUS.BIN as one module (MASM 3: "Out of Memory"; MASM 4 dies
  silently). Four modules of ~9 KB each are fine (30 KB+ symbol space free in each). gen.py
  cuts at routine entries that no 8-bit relative branch crosses: MASM cannot make a short
  jump to an external. Cross-module labels are EXTRN/PUBLIC, declared inside the segment.
  EXODUS's modules start at 0100, 583C, 7D1A and 9630.
- MASM encodes `xchg r1,r2` with r1 in the reg field; capstone prints the rm operand first,
  so gen.py swaps them (43 places).
- `lea bx,[bx+0000]` (ULTIMA 8B0C, 8DF8) keeps its 16-bit displacement only with a relocatable
  symbol: it is written `lea bx, L0000[bx]`. PSP offsets (L005C, L006C, L00FE, ...) are labels
  placed with `ORG` before `ORG 100h`.
- capstone names 98/99 `cwde`/`cdq`; in 16-bit code they are `cbw`/`cwd`.
- Never kill all DOSBox processes: other projects' sessions run their own (the u2 session's
  build was running at the same time). A LINK given a missing object waits for input forever;
  the build guards it with `IF EXIST`.

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
  EXODUS 56C1, indexed by `not al` for codes F4-FF); EXODUS command dispatch 190B (33 keys at
  1887, prompt-string pointers at 18C9), 774A (keys 7708, strings 778C), 85BB (keys 8579),
  spells 594B/596B (16 each; names via 590B), and 76F8, 85FD, 77CE, 654C, 794D, A3A7, 9BEC.
  The string-pointer tables (18C9, 778C, 590B, 6540) are still plain data words: they must
  become `dw Lxxxx` in phase 3.
- **Copy protection is dead code**: the library routine that reads track 9 sector 16 with int
  13h (ULTIMA 8793, BOOTUP 44B0, EXODUS 5000) is never reached by the disassembly. Either GOG
  or Origin removed its call. An original disk image would show which.
- The shared library (docs/PLAN.md 2.2) is present in all three; the sources are not yet
  unified (phase 2).

## Repository

| file | what |
|---|---|
| `src/TARGET/*.ASM`, `NAME.lnk` | the sources (frozen 2026-11-09 from gen.py's output), modules in link order |
| `tools/build.py` | assemble (MASM 4.00, `ASM=MASM3` for 3.00), LINK 3.05, image from 0100, sha1 check |
| `tools/u3an.py` | per-target facts (entries, tables, data areas, module size limit) and recursive disassembly; run it for coverage and indirect branches |
| `tools/gen.py` | the generator (labels, modules, PSP labels, xchg order) |
| `tools/regen.py` | gen → MASM with listings → LINK → compare, forcing differing lines to `db` (none needed now); `regen.py TARGET [WORKDIR] [MASM4/MASM3]` |
| `tools/dos.py`, `setup.py`, `fat12.py` | DOSBox runner and toolchain unpacking (from u2) |

Not committed yet: the first commit waits for Karl's choice of branch (git calls `main` the
main branch; the checkout is `master` with no commits).

## Next steps

Phase 2 (one library source) and phase 3 (relocatable) in docs/PLAN.md. Concretely:
1. Align the three copies of the shared library (BOOTUP 1F48.., ULTIMA +42E0, EXODUS +0B50
   with small shifts) and list where they differ. The operands that differ are addresses.
2. Immediates that are addresses: the int 23h/24h handler offsets, `mov si,offset`-style
   loads (e.g. ULTIMA 5DBC `mov si,9FFh`?), the chain-load constants (1328h in BOOTUP), the
   string-pointer tables. Check each 16-bit immediate as U2 did.
3. Then the NOP test: insert a byte near the start of each file and play through intro → menu
   → game in DOSBox.
