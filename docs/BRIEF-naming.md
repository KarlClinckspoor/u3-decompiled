# Brief: name and comment some modules of the Ultima III sources (phase 6)

Repo: `C:\Users\karl9\Downloads\Claude\u3-decompiled` (Windows; use the Bash tool = Git Bash).
It rebuilds the PC Ultima III (1983) byte for byte from hand-written 8086 assembly in `src/`:
three COM programs (ULTIMA.COM intro, BOOTUP.BIN menu/character creation, EXODUS.BIN the game),
the DUNGEON.DAT overlay, and a shared library `src/LIB.INC` linked into the first three. The
sources were generated from the binaries: most labels are still address names (`L1234` = address
1234 in that program, `K1234` = library offset). A first set of names exists already
(`names/*-core.map`). Your job: give every label in **your files** a real name and add comments,
without changing a single byte of the build.

Read first: `docs/NAMING.md` (the rules and style: essential), `docs/MAP.md` (what each module
does), `docs/FORMATS.md` (data files, the character record, the party header, the map buffer:
most variables are explained there), and the module headers.

## Python and tools

    PY=../u1-decompiled/build/venv/Scripts/python.exe        # has capstone; plain python works too for most
    $PY tools/syms.py exodus L6C76                 # where a symbol is, its original address
    $PY tools/syms.py exodus --refs L6C76          # every line that uses it (all modules)
    $PY tools/routines.py exodus 5D83 62FD         # routines of a range: size, callers, table entry, strings
    $PY tools/rename.py exodus MAP --only MAGIC    # rename labels used only in MAGIC.ASM
    $PY tools/build.py --out build/OUTDIR          # build all four into your own directory: IDENTICAL x4
    $PY tools/lint.py src/exodus/MAGIC.ASM --code-unchanged HEAD   # only names/comments changed

The original bytes of a program are in `gamedata/` (EXODUS.BIN etc., loaded at 0100: file offset
= address - 100h). `tools/u3an.py` disassembles (`import u3an; a = u3an.analyse('exodus')`).

## Rules (others work on other files at the same time)

- **Edit only your files** (listed below). Comments and blank lines with the Edit tool; names only
  with `tools/rename.py SCOPE MAP --only MODULE`, one of your modules at a time. Keep your maps in
  `names/` as `names/<module>.map` (one per module; append, don't rewrite applied lines).
- `--only` refuses a label that another module uses (EXTRN/PUBLIC). For those, and for any label
  defined in your files that others use, **do not rename**: write your proposal to
  `names/proposed-<your id>.map`, one `OLD NEW ; SCOPE ; what it is` per line, with the scope
  (the program, or `lib` for library/K/X names). Propose names only for symbols defined in your
  own files. Use the proposed name in your comments if you like; the integrator applies the
  proposals at the end.
- Library names (`Kxxxx`, `Xxxxx`) are scope `lib`; if you are not the library's owner, you may
  only use them.
- Never change code: no instruction, operand, db/dw value, EXTRN/PUBLIC line, segment line, ORG,
  ASSUME, IFDEF. Keep each `;@ADDR` tag as the last thing on its line. Lines <= 120 characters.
- Build into your own directory (`--out build/<your id>`) after each module, and run lint with
  `--code-unchanged HEAD` on your files. Both must pass before you report.
- Do not commit, do not run regen.py/shift.py, do not touch docs/ (except your notes file).
- Names must be unique in the program (rename.py checks); prefix local labels with their routine
  name (`AskPlayer_Loop`) so parallel workers don't pick the same name.

## What to produce

1. Every `Lxxxx`/`Kxxxx` label defined in your files renamed (directly or by proposal), local
   branch targets included. Data labels too (strings: `Msg...`, tables, variables).
2. A module header overview under the existing header lines, and a routine header before each
   routine (call target or table entry): what it does, inputs/outputs where clear.
3. Inline comments where values need explaining (record offsets, sound codes, tile numbers,
   key codes, DOS/BIOS calls). Say `?` where unsure.
4. `names/notes-<your id>.md`, short: anything the code revealed that the docs don't say (game
   mechanics, bugs, dead code, corrections to FORMATS.md/MAP.md), and open questions.

## Report back (final message, under 25 lines)

Labels renamed / proposed / left (with why), build and lint results, the notes file's main points.
