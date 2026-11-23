/* exdata.h: the routine of EXDATA.ASM (src/exodus/EXDATA.ASM). Data: exodus_data.h (generated).
 * ReadCommand is the top of a surface turn: it jumps (`jmp SurfaceCmds[bx]`) to the command with
 * SI = its prompt; the commands return (they end with `jmp MainLoop`), see loop.h. */
#ifndef U3_EXODUS_EXDATA_H
#define U3_EXODUS_EXDATA_H
#include "../u3.h"
#include "exodus_data.h"

void ReadCommand(void);                     /* BuildView, then ReadCommandNoView; never comes back */
void ReadCommandNoView(void);               /* a label inside ReadCommand, jumped to by MonTurn (WORLD) */

/* The DOS clock and calendar, int 21h AH=2Ch / 2Ah (stand-ins, as c/ultima/intro.c declares them). */
u16 DosGetTime(u16 *cx);                    /* returns DX = second:hundredths (DH:DL), *cx = hour:minute (CH:CL) */
u16 DosGetDate(u16 *cx);                    /* returns DX = month:day (DH:DL), *cx = year */

#endif
