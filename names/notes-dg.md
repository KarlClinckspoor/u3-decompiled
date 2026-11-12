# Notes from DUNGEON.ASM (worker dg)

## Cell values (corrections / additions to docs/FORMATS.md 4)

How DUNGEON.DAT draws a cell (DrawSlot 0533):

- **80-BF**: a plain wall face (stripes). So **A0 looks exactly like a wall: the secret door**. **sure**
- **C0-FF**: the wall face plus a solid door shape in it (FaceTbl 32-63): **C0 is the door**. **sure**
- **below 80** (open): bit **10h** ladder up, **20h** ladder down (both drawn, so 30 shows two ladders),
  **40h a filled box on the floor: the chest**. **sure** (also EXODUS MAGIC 61BB: a spell turns a
  dungeon cell 40h into 00 and gives gold, L80D9). The low nibble (01-08, the events) is not drawn.
- What EXODUS does with them (seen while checking, DUNMOVE): Advance (847D) refuses only the value
  80h, so you can walk into A0 and C0 (and into any other 81-FF); Retreat (84A9) refuses every
  cell >= 80h; the turns (8438, 8455) are refused while you stand in a cell >= A0 (a doorway).
  The time-vision map (VIEW 2909) prints C0 as character 1, A0 as 2, 80 as 3, 30/20/10 as 4/5/6,
  00 blank, anything else '?'.

## How the view works

- Facing 0 north (y-1), 1 east, 2 south, 3 west (DrawSlot turns the slot offsets (dx,dy) ->
  (-dy,dx) per quarter; matches EXODUS L76F0/L76F4).
- 32 view slots (SlotDXTbl/SlotDYTbl), up to 3 cells ahead; a cell can be in two slots (front face
  and side face); for ladders and chests each of the two slots draws half of the object, so a half
  stays hidden when only one line of sight is open. Ladders and chests only to slot 20 (2 cells away).
- Lines of sight stop at the first wall; no other hidden-surface work. Everything is ORed in
  white; walls are stripes every second pixel, doors fill the gaps, so they look solid.
- Fake perspective: each step away halves the size (front faces 80h, 40h, 20h, 10h wide).
- View coordinates 00-80h (x) by 00-7Fh (y), drawn at screen pixel +20h (centre 60h = 96, the
  middle of the map window). Some entries start at x = 80h, i.e. screen x 160 (one column right of
  a 128-pixel view?).
- Facing east or west shifts every wall line one pixel right (inc cl, 05F3): the stripes change
  phase when you turn, probably so a turn is visible even in a symmetric corridor.
- Standing in a door (C0): the whole view is wall with the opening erased (FaceTbl 32, the only
  erase), then only the cells straight ahead are drawn. Standing in a secret door (A0, or any
  80-BF you could enter): only the full-view wall, nothing else.

## Dead / unused data, latent bugs

- LadderTbl bytes +6, +7 of every entry (rung y for the lower half) are never read: the code
  mirrors with 7Fh - y instead. 01EF-01F2 (FF,0,0,0) after LadderTbl are unused (a slot 21?).
- FaceTbl byte +7 always 0, unused. DrawFace's `cmp al,1` (step 1) never matches (steps are +-2).
  The `x >= 80h = none` tests in DrawLadder/DrawChest never match.
- DrawLine with equal end points, and DrawVLine with top = bottom, would loop 65536 times; no
  table entry asks for it.

## Open questions

- Is the view really 129 pixels wide (x 00-80h)? The slot 0 face covers 00-80h.
