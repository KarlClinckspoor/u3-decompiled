# Notes from worker "lib" (src/LIB.INC)

## Corrections to the docs and to names/lib-core.map's notes

- **SignStep** returns the sign in **AH** (-1, 0, +1), not AL. On Sosaria (X01BE = 0) AL is taken
  as a 6-bit signed number (the map wraps at 64) and comes back with its top two bits cleared.
- **ReadLine** returns the count typed in **BX** (CX is preserved); no NUL is stored.
- **DrawTileBlock** takes the graphics base in **BP** (not always TileGfx); **ViewTileAt** also
  returns BX = the cell's address in ViewTiles (callers write tiles through it).
- **ReadNumber** returns AL = the digits as BCD and AH = the decimal value (0FFh after a hex digit).
- FORMATS.md 2: SHAPES.ULT tiles **64-79 are the second animation frames** of tiles 16-30
  (merchant .. balron) and 12 (whirlpool): K28E7 swaps 64-78 with 16-30 and 79 with 12 every
  10th call. Not "other symbols"; the "party's members" on the sheet are those frames.

## Mechanics

- **Random**: RandState is one 128-bit number (byte 0 most significant). Each step adds every
  byte's lower neighbour plus carry (bytes 14 .. 0), then increments the whole number; DL = byte 0
  mod DH by repeated subtraction (DH = 0 would hang). ULTIMA (5D18) and EXODUS (2554) seed it with
  the DOS date and time: +0 year, +2 month/day, +4 hour/min, +6 sec/hundredths, then again from
  +8. BOOTUP never seeds it (it only uses the beep, which does not call Random).
- **Animation runs from KeyReady** (Animate, K2987) on every poll, unless X01BE = 1 (dungeon;
  ULTIMA keeps 1 in its X01BE): wind (not in combat 80h or shrine 4), water/lava/force
  field/moon gate scroll one pixel line (ScrollTile) every 3/2/3/2 polls, flags of castle/towne/
  frigate swap two pixel lines every 4/3/2, figure frames every 10, the combat blink, then a full
  DrawView. All of it, and the wind, run at polling speed: CPU dependent.
- **Wind**: every 25 polls; Random 0-8: 0-4 taken as is (so calm is 1/9), 5-8 give north..west
  but never the current direction (retry). Printed at row 17h col 6 between glyphs 10h and 11h
  (FORMATS calls 10h/11h the moon symbols; here they frame the wind text: same glyphs?).
- **Combat blink** (BlinkPlayer, K011B): the active member (X0103) shows his own tile (X01B5) for
  10 polls and the tile under him (X01B1) for 3. So the CNFLCT file bytes A8-AB (01 = grass) are
  the tiles under the members and AC-AF their own tiles (FORMATS 5 has them as open).
- **ReadKey** draws glyph 1Eh as the cursor and calls an empty routine (IdleNop, a bare ret) every
  80 polls: a hook left empty.
- **K2AD8** (AskChoice) is the menu input: letter list at ES:DI, string table at SI, Enter accepts,
  Backspace/left undoes.
- **Sounds**: all by toggling port 61h bit 1 in delay loops. 0FFh buzz, 0FEh error beep, 0FDh
  duty-cycle warble (pitch constant: high + low time = BL+1), 0FCh noise, 0FBh falling sweep,
  0FAh rising sweep, 0F9h warble with BL=0E0h BH=4, 0F8h rising noise, 0F7h noise burst (hits),
  0F6h tick, 0F5h random notes (count from DL), 0F4h slow falling sweep.

## Copy protection (DiskCheckStub, K2670)

The routine after the stub reads track 9, head 0, sectors 16 down to 1 (int 13h, 4 tries each,
into C000:0000) on drive A: or B:; a normal track has 8/9 sectors, so only a specially formatted
track 9 passes. The stub's 3 bytes overwrite the routine's own first 3 bytes (its pushes: the
code still pops flags/BX/AX - EXODUS flags/DS/BX - it no longer pushes). So it is a patch of the
original routine, not a separate stub. EXODUS's copy is 6 bytes shorter and has no final ret.

## Bugs and dead code

- LoadFile / SaveFile error path: "Unable to read/write file " is meant to be followed by the
  file name (they keep SI past the DOS parse for it), but OpenFile has loaded SI with the 15-space
  message, so blanks are printed. Then both hang (jmp $).
- LoadFile treats a file whose size's low word is 0 as unreadable. A missing file gives
  "Wrong Diskette!" (OpenFile retries on any key), not "Unable to read".
- SndWarble (0FDh) and SndNoise (0FCh) use the caller's BX/BL, which Sound does not set (?).
- The rest of the disk check is dead in all three programs.

## Open questions

- Which game events use which sound code (names are by the sound's character).
- X01BE values 2 and the others (0, 1, 4, 80h, 0FFh seen here).
