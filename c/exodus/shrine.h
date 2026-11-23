/* shrine.h: the routines of SHRINE.ASM (src/exodus/SHRINE.ASM). Data: exodus_data.h (generated).
 * Parameters are named after the registers they come in; see c/README.md "Calling conventions". */
#ifndef U3_EXODUS_SHRINE_H
#define U3_EXODUS_SHRINE_H
#include "../u3.h"
#include "exodus_data.h"

void PrintLevelHead(void);                  /* "LVL:0n" and "Head-<facing>"; keeps the cursor */
/* In: SI = creature slot (0-31). Out: CL, CH = the step (-1, 0, 1) in x, y, returned as one word
 * (low byte CL, high byte CH); DL, DH = the creature's x, y plus the step, wrapped to 0-63,
 * through *dx (low byte DL, high byte DH). */
u16 MonStepToPlayer(u16 si, u16 *dx);
void EnterShrine(void);                     /* Enter on a shrine in Ambrosia */
void ExitToSosaria(void);                   /* leave a dungeon */

#endif
