/* view.h: the routines of VIEW.ASM (src/exodus/VIEW.ASM). Data: exodus_data.h (generated).
 * Parameters are named after the registers they come in; see c/README.md "Calling conventions".
 * The view buffer (the 11 x 11 shape numbers BuildView fills) is ViewTiles, declared in lib.c / world.h. */
#ifndef U3_EXODUS_VIEW_H
#define U3_EXODUS_VIEW_H
#include "../u3.h"
#include "exodus_data.h"

void ShowGemMap(void);
void XorGemPixel(u8 cl, u8 ch, u8 dl, u8 dh, u8 ah);   /* CL, CH = the map cell x, y; DL, DH = the sub-pixel;
                                                           AH = the colour in the top pixel position (ES = the screen) */
void PrintMsg(const u8 *si);                /* SI = the NUL-ended text */
void ScrollMsg(void);
void DrawFrame(void);
void BuildView(void);
void ClearView(void);
/* In: BL = x, BH = y (0-63). Returns AL = the map byte; *bx = its address in MapBuf (y * 64 + x). */
u8 MapCellAddr(u8 bl, u8 bh, u8 **bx);
/* In: BL = x, BH = y (0-15). Returns AL = the dungeon byte; *bx = its address in DungeonMap (level * 256 + y * 16 + x). */
u8 DungeonCell(u8 bl, u8 bh, u8 **bx);
void ShowDungeonMap(void);

#endif
