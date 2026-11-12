# Naming and commenting conventions (phase 6)

How the sources in `src/` are named and commented. The rules exist so that names never change the
bytes (`tools/build.py` must stay IDENTICAL for all four files) and so that the tools keep working.
Adapted from `../u2-decompiled/docs/NAMING.md`.

## Namespaces

- A program's own labels (generated as `Lxxxx`, xxxx = the address in that program) belong to
  that program: ULTIMA, BOOTUP, EXODUS and DUNGEON each have their own `L1234`.
- The library's labels (`Kxxxx` = offset from the library start in BOOTUP.BIN) and the program
  symbols the library uses (`X0103` ... `X01BE`, defined in each program that links it) are
  **shared**: they appear in `src/LIB.INC` and in ULTIMA, BOOTUP and EXODUS.
- MASM ignores case, so a name must be unique ignoring case within a program's own names plus
  the shared ones (`tools/rename.py` checks this).

## Hard rules (the tools enforce or rely on these)

- **Rename only with `tools/rename.py SCOPE MAP`.** SCOPE is the program (`ultima`, `bootup`,
  `exodus`, `dungeon`) for its own labels, or `lib` for the shared names. It renames a symbol
  everywhere at once (definition, EXTRN/PUBLIC lines, every use, mentions in comments) and refuses
  invalid or clashing names. Map lines are `OLD NEW ; optional note`. Keep the maps in `names/`.
- `--only MODULE` refuses renames of symbols that other modules use: use it when several people
  work on different modules at the same time.
- A name: letters, digits, `_`; not starting with a digit; **at most 31 characters**; not a MASM
  reserved word (`loop`, `length`, `name`, `size`, `type`, `mask`, `width`, `str`, `out`, `stack`,
  `page`, `title`, `label`, `seg`, `offset`, `code` ...).
- **Every code line keeps its `;@ADDR` tag as the last thing on the line.** An inline comment goes
  between the instruction and the tag: `	mov al, byte ptr [bx+11h]	; status	;@6C17`. Comment
  lines and blank lines carry no tag. The tags are the original addresses: tools/syms.py, regen.py
  and shift.py use them.
- **Lines at most 120 characters** (MASM 4.00 silently drops what follows an over-long line).
- Never change an instruction, an operand's value, a `db`/`dw` value, a label's position, a
  segment line, EXTRN/PUBLIC lines (rename.py maintains those), `ASSUME`, `ORG`, the `IFDEF
  PROG_...` blocks of LIB.INC or the module order. `tools/lint.py --code-unchanged REV` checks that
  only names, comments and blank lines changed since REV.
- After every batch: `tools/build.py` (IDENTICAL x4) and `tools/lint.py`.

## Style

MASM ignores case; write names in CamelCase.

| what | style | examples |
|---|---|---|
| routine (a `call` target) | VerbObject | `PrintMsg`, `ReadKey`, `LoadFile`, `BuildView`, `AskPlayer` |
| command handler (a command table entry) | `Cmd` + command | `CmdAttack`, `CmdBoard`, `CmdKlimb`; combat ones `CCmd...` |
| spell handler | `Spell` + spell name | `SpellRepond`, `SpellPontori` |
| town service | the service | `ShopPub`, `ShopGrocer`, `TempleHeal` |
| other entry points / big blocks | descriptive | `MainLoop`, `StartUp`, `CombatLoop` |
| label inside a routine | `Routine_What` (shorten the routine part if needed) | `PrintMsg_Wrap`, `Attack_Miss` |
| variable | noun, what it holds | `CursorCol`, `PartySize`, `Moon1Phase`, `LightOn` |
| table / array | plural or `Tbl` | `GateXTbl`, `NameTbl`, `MonTile` |
| string | `Msg` + text, or `File` + file name | `MsgNotHere`, `FileShapesUlt` |
| shared error exit (message + back to the main loop) | `Msg...` | `MsgNoneLeft` |
| dead code (nothing reaches it) | `Dead_` + what it was | `Dead_DiskCheck` |

- Every label gets a name, local branch targets included (`_Next`, `_Done`, `_Loop`, `_Retry`,
  in a chain of compares the test it starts: `_TryHorse`).
- A reference into the middle of an instruction or a buffer stays `Name+n` with a comment.
- Keep the game's own terms (the strings it prints, docs/FORMATS.md): `Ztats`, `HitPoints`,
  `Exp`, `Food`, `Gold`, `Gems`, `Keys`, `Powders`, `Torches`, `Marks`, `Cards`, `MoonGate`,
  `Whirlpool`, `Ambrosia`, `Exodus`.

## Comments

- **Module header**: below the existing three lines, a short overview: what the module does, its
  main entry points, the data it owns or mostly uses.
- **Routine header** before each routine (call target or table entry):

```
;------------------------------------------------------------------------------
; PrintMsg: print the NUL-ended string at SI in the message window (rows 11h-17h,
; columns 18h-27h), wrapping and scrolling. 0Ah = new line.
; In: SI. Out: cursor after the text. Uses: nothing (saves all).
;------------------------------------------------------------------------------
```

- Inline comments where the meaning is not obvious from the names: what a value means
  (`cmp al, 47h ; 'G' good`), record offsets (`[bx+23h] ; gold`; docs/FORMATS.md 6 lists the
  character record), DOS/BIOS calls, sound codes, speed-dependent delays.
- Say what you don't know: `; ?` or "probably", rather than guessing silently.
- English, short, no ASCII art beyond the routine rule lines.

## Character record offsets (docs/FORMATS.md 6)

Code that works on a player has BX, DI or SI at the 64-byte record. Comment these displacements
when they appear: 0E marks/cards, 0F torches, 10 party flag, 11 status, 12-15 Str/Dex/Int/Wis,
16 race, 17 class, 18 sex, 19 magic points, 1A hit points, 1C max hit points, 1E experience,
20-22 food (hundredths, word), 23 gold, 25 gems, 26 keys, 27 powders, 28 armour worn, 29-2F
armours, 30 weapon readied, 31-3F weapons.
