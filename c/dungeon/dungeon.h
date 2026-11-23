/* dungeon.h: the routines of DUNGEON.DAT (src/dungeon/DUNGEON.ASM), the 3D dungeon view, as the C
 * calls them. Data: dungeon_data.h (generated). Parameters are named after the registers they come
 * in; see c/README.md "Calling conventions". */
#ifndef U3_DUNGEON_H
#define U3_DUNGEON_H
#include "../u3.h"
#include "dungeon_data.h"

/* EXODUS loads this overlay at 0100 and calls it there (a `jmp DrawDungeonView` sits at 0100). */
void DrawDungeonView(u16 bx, u8 al, u8 ah);     /* BL x, BH y; AL facing 0-3; AH level 0-7 */
i8 DrawSlot(u8 al);                             /* 0 = ZF set (open cell), -1 = SF set (wall or door),
                                                   1 = neither (slot 0 is a door); the result is in the
                                                   flags only: AL is the slot again after the final pop */
void DrawFace(u8 ah);                           /* FaceTbl entry 0-63 */
void DrawLadder(u8 ah, u8 al);                  /* slot; 0 up, 1 down */
void DrawLine(u8 cl, u8 ch, u8 dl, u8 dh);      /* from (CL,CH) to (DL,DH), view coordinates */
void DrawChest(u8 ah);                          /* slot */
void DrawVLine(u8 cl, u8 ch, u8 dl, u8 ah);     /* x, top y, bottom y (excluded); AH = 20h erases */
void PlotPixel(u8 cl, u8 ch);                   /* view x, y */
u8 GetCell(u8 bl, u8 bh, const u8 **bx);        /* x, y; returns AL = the cell, *bx = its address */

#endif
