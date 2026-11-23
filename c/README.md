# c/ -- Ultima III read as C

A **reading aid**: for a routine in `../src`, "this is what it does, written the way a C programmer
would". It is **not a port**, **not byte-matching**, and **has never been run against the game**.
The assembly is the ground truth; where the two disagree, the C is wrong. The method is the one of
`../../u2-decompiled/c` (the same checks, adapted: U3 prints through pointers to strings, not inline
text, and has a shared library and four programs instead of one).

`c/` mirrors `src/`: one `.c` per assembly module of the same name, in the folder of its program.

| C | reads | |
|---|---|---|
| `lib/lib.c` | `src/LIB.INC` | the library linked into ULTIMA, BOOTUP and EXODUS, **read once** |
| `ultima/*.c` | `src/ultima/` | ULTIMA.COM: intro and title animation (`udata.c`, `intro.c`) |
| `bootup/*.c` | `src/bootup/` | BOOTUP.BIN: menu, party, character creation |
| `dungeon/dungeon.c` | `src/dungeon/` | DUNGEON.DAT: the 3D dungeon view (a code overlay) |
| `exodus/*.c` | `src/exodus/` | EXODUS.BIN: the game, 18 modules |

Shared: `u3.h` (types and the machine stand-ins), `lib/lib.h` (the library's routines),
`SCOPE/SCOPE_data.h` (every table and variable of a program, **generated**: `tools/cdata.py`).

## Status

Routines are the labels under a `;----` header (309 in all: ULTIMA 15, BOOTUP 28, EXODUS 210,
DUNGEON 9, LIB 47, counted as in `tools/progress.py`). Data labels (tables, strings, buffers,
variables) are anchored too. `python3 tools/ccheck.py --cc gcc` prints the same numbers.

<!-- status -->
| scope | module | C file | routines | with C | data labels | with C |
|---|---|---|---|---|---|---|
| lib | LIB.INC | `c/lib/lib.c` | 47 | 47 | 40 | 40 |
| ultima | UDATA.ASM | - | 0 | 0 | 29 | 0 |
| ultima | INTRO.ASM | - | 15 | 0 | 4 | 0 |
| bootup | BDATA.ASM | - | 1 | 0 | 166 | 0 |
| bootup | TITLE.ASM | - | 7 | 0 | 0 | 0 |
| bootup | ORGANIZE.ASM | - | 5 | 0 | 0 | 0 |
| bootup | CREATE.ASM | - | 15 | 0 | 0 | 0 |
| exodus | EXDATA.ASM | - | 1 | 0 | 137 | 0 |
| exodus | LOOP.ASM | - | 16 | 0 | 0 | 0 |
| exodus | WORLD.ASM | - | 9 | 0 | 13 | 0 |
| exodus | VIEW.ASM | - | 10 | 0 | 2 | 0 |
| exodus | ITEMS.ASM | - | 12 | 0 | 42 | 0 |
| exodus | MAGIC.ASM | - | 32 | 0 | 0 | 0 |
| exodus | SHRINE.ASM | - | 4 | 0 | 196 | 0 |
| exodus | PARTY.ASM | - | 25 | 0 | 3 | 0 |
| exodus | ACTIONS.ASM | - | 7 | 0 | 73 | 0 |
| exodus | HAND.ASM | - | 6 | 0 | 0 | 0 |
| exodus | EQUIP.ASM | - | 11 | 0 | 0 | 0 |
| exodus | DUNMOVE.ASM | - | 12 | 0 | 0 | 0 |
| exodus | CMDTAB.ASM | - | 0 | 0 | 61 | 0 |
| exodus | COMBAT.ASM | - | 33 | 0 | 0 | 0 |
| exodus | DUNEVENT.ASM | - | 12 | 0 | 0 | 0 |
| exodus | TEXT.ASM | - | 0 | 0 | 113 | 0 |
| exodus | ENDING.ASM | - | 5 | 0 | 0 | 0 |
| exodus | TOWNS.ASM | - | 15 | 0 | 0 | 0 |
| dungeon | DUNGEON.ASM | - | 9 | 0 | 8 | 0 |
| | **total** | | **309** | **47** | **887** | **40** |
<!-- /status -->

## Rules

- **Anchored.** Every function and table is preceded by a comment line
  `/* asm: NAME @ADDR [options] */` naming the assembly symbol and its original address
  (`python3 tools/syms.py SCOPE NAME` finds both; `ccheck.py --fix-addrs` fills the addresses in).
  Read the C next to the routine it names.
- **Same names.** Variables and routines keep the assembly's names (`PlayerX`, `MsgInvalidMove`,
  `CmdBoard`). The assembly's registers and scratch bytes become locals; the original register
  stays in a comment or in the parameter name (`u8 al`, `u16 dx`, `const u8 *si`).
- **Same behaviour, bugs included.** A bug of the original is written as it behaves and marked
  `BUG, as in the original` (see `docs/FINDINGS.md`). The C never "fixes" anything.
- **Same texts and tables.** Strings and tables are exactly the assembly's bytes (the checker
  compares them); text is `u8 MsgX[] = "..."` where `\n` is the game's 0Ah.
- **Said, not invented.** Where a routine relies on flags, on a register the caller left behind, on
  self-modifying code, on data after the return address or on a jump into the middle of another
  routine, the C says so in a comment and does not invent semantics.

## Calling conventions (what "registers disappear" means here)

- The `In:` registers of the routine's header become parameters, in the header's order, named after
  the register (`u8 al`, `u16 dx`, `const u8 *si`, `u8 *di`). A pointer register is a C pointer
  into the program's data; DS/ES are not written.
- The main `Out:` register is the return value. More results: the first is returned, the others go
  through pointer parameters named after their register (`u16 *bx`). A routine that "saves all"
  has its pushes and pops dropped (no comment needed).
- **Flags.** A routine whose caller tests the zero or carry flag returns a `bool` that is true
  when the routine's header says so (`KeyReady` returns true = a key waits, ZF clear); the anchor
  comment or the function says which flag it is. A flag the C needs only inside one routine is a
  local `bool`.
- **The turn.** U3's commands end with `jmp MainLoop` (the end of the turn). In the C a command
  just `return`s; the checker ignores `jmp MainLoop`. A shared exit (`jmp MsgInvalidMove`,
  `jmp MsgWhat`, ...: a message, then the turn ends) is a call followed by `return`. Name any
  other jump that becomes a plain return in `returns: NAME` on the anchor.
- **A register the caller leaves behind** (`call PrintMsg` with SI as the previous `lea` left it) is
  passed explicitly, with a comment. `Sound`'s routines read the caller's BX/DX: `SoundBX`,
  `SoundDX` (`lib/lib.h`).
- **Data.** Variables are C objects of the program's data header. A label that is accessed as a
  word where the assembly has two byte labels (`PlayerXY` over `PlayerX`/`PlayerY`), or a label
  inside a bigger buffer (`WhirlpoolGfx` in `TileGfx`), is an `alias` in `SCOPE/types.txt`
  (`tools/cdata.py`): a macro for a place inside the object. Say what you do in a comment.
- **Jumps that never come back** (the main loops, the title, the chain loads) are calls in the C,
  and what follows such a call is only the C unwinding.
- **The machine.** The BIOS, DOS, the ports and the CGA memory are not the game: `u3.h` declares
  stand-ins (`BiosReadKey`, `DosOpenFcb`, `OutPort`, `CgaMem`, `Psp` ...). They are not defined:
  the reading is not linked.
- **Loops over the same thing.** Where a C loop replaces repeated assembly the anchor says
  `unrolled: NAME-N` (N calls fewer demanded).

## Checking

```
python3 tools/ccheck.py --cc gcc              # every c/*/*.c
python3 tools/ccheck.py --cc gcc c/lib/lib.c  # one file
python3 tools/ccheck.py --fix-addrs FILE.c    # fill in the @ADDRs from the names
```

(The compiler: MSYS2's gcc at `C:\msys64\mingw64\bin`; from Git Bash it can fail silently, so run it
from PowerShell with that folder first on PATH. The tool needs only Python 3.)

For each anchored item the checker verifies that

- the symbol exists in the module of the same name, at that address (the `;@` tags);
- a **table** (`u8 X[] = {...}`, `"text"`, `u16`, a scalar) holds the same bytes as the assembly's
  `db`/`dw` lines (`db 48 dup (0)` included), a buffer declared without initialiser has the size
  of an all-zero `db n dup`, a table of `dw Name` holds the same names in the same order;
- a **function** calls every routine the assembly calls or jumps to (outside itself) at least as
  often (the C may call more, helpers), and mentions every data label the routine's instructions
  mention (that is how U3's texts are checked: `lea si, MsgX` is `MsgX` in the C);
- the file compiles (`-std=c99 -Wall -Wextra -Wpedantic -fsyntax-only`);

and lists the routines and data labels of each module that have no C yet.

**It cannot check the logic**: the numbers, the conditions, the order of the calls, what a
register held. For that the only checks are reading the C beside the assembly and playing the
game. Options on the anchor (`also:`, `returns:`, `unrolled:`, `ignore:`, `to:`, `check: none`)
say where the C legitimately differs; they are documented in `tools/ccheck.py`.

## Adding a module

1. `python3 tools/cdata.py defs SCOPE MODULE` prints the C of the module's data (anchored,
   byte for byte); `tools/cdata.py header SCOPE` rewrites `SCOPE/SCOPE_data.h` after a change to
   `SCOPE/types.txt`. Never edit the generated header.
2. One `.c` per assembly module, same name; anchor every routine. Prototypes of a module's routines
   go in `SCOPE/MODULE.h`.
3. `ccheck.py --fix-addrs --cc gcc FILE.c`, until it prints `ccheck: OK`.
