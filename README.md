# u3-decompiled

Source code for the PC version of **Ultima III: Exodus** (Origin Systems 1983, PC conversion
by James R. Van Artsdalen), rebuilt with the original tools into files identical to the GOG
release, byte for byte.

## Status

| file | what | status |
|---|---|---|
| ULTIMA.COM | intro and title animation; loads BOOTUP.BIN over itself | **rebuilds identical** (36692 bytes) from `src/ultima/` |
| BOOTUP.BIN | main menu, party and roster, character creation; loads EXODUS.BIN over itself | **rebuilds identical** (19572 bytes) from `src/bootup/` |
| EXODUS.BIN | the game | **rebuilds identical** (44234 bytes) from `src/exodus/` |

All three link the same library module (screen, text, keyboard, files, sound), one source in
`src/LIB.INC`; EXODUS's slightly different version is two `IFDEF PROG_EXODUS` blocks.

The game is hand-written 8086 assembly. There is no compiler output and no protection envelope.
The sources were generated from the files (`tools/gen.py`, `tools/genlib.py`) and are now
edited by hand. Every branch target and memory operand inside the image is a label (`Lxxxx` in
the programs, `Kxxxx` in the library), and no instruction is written as `db`. In the programs,
immediates are still numbers; in the library every address is symbolic. Next: make the
programs relocatable, then names (docs/PLAN.md, docs/HANDOFF.md).

## Toolchain

Assembly: **MASM 4.00** (MASM 3.00 gives the same bytes). Link: Microsoft **LINK 3.05**. The
images are COM programs: LINK writes an EXE whose image starts with the 0100h bytes left free by
`ORG 100h`, and the build keeps the image from 0100 (what EXE2BIN does).

The repository contains neither the game nor the tools. Put the GOG files in `gamedata/`. The
toolchain archives are taken from the sister projects (`../u6-decompiled/tools/masm300/` for the
MASM 3.0 image, `../u1-decompiled/tools/` for the MASM 4.0 archive) or from `tools/`. Then:

```sh
python3 tools/setup.py     # unpacks MASM 3.00/LINK 3.00 and MASM 4.00/LINK 3.05 into build/tc (needs 7-Zip)
python3 tools/build.py     # builds build/{ultima,bootup,exodus}/ and checks each file against GOG's
```

Builds run the DOS tools in headless DOSBox: `dosbox` on the PATH, or the one named by the
`DOSBOX` environment variable; on Windows the GOG copy in `gamedata/DOSBOX/` is used when
neither is set. The analysis tools need `capstone` (on Karl's machine:
`../u1-decompiled/build/venv/Scripts/python.exe`).

## Layout

- `src/TARGET/`: the sources of one file, `NAME.lnk` lists its modules in link order;
  `src/LIB.INC` the shared library, included by each `src/TARGET/LIB.ASM`. MASM needs CRLF line
  ends (.gitattributes keeps them)
- `tools/build.py`: assemble, link, cut the image, compare; `tools/dos.py`: headless DOSBox;
  `tools/setup.py`, `fat12.py`: toolchain
- `tools/u3an.py`: recursive disassembly and per-file facts (entry points, jump tables, data
  areas); `python3 tools/u3an.py` prints coverage and indirect branches
- `tools/gen.py`, `tools/genlib.py`, `tools/regen.py`: generate the program and library sources
  from the files and iterate until they assemble identically (for re-deriving pieces; `src/` is
  the source of truth)
- `docs/PLAN.md`: the plan; `docs/HANDOFF.md`: state, findings and next steps
