/* dunevent.h: the routines of DUNEVENT.ASM (src/exodus/DUNEVENT.ASM). Data: exodus_data.h (generated).
 * Parameters are named after the registers they come in; see c/README.md "Calling conventions".
 * Every event ends with `jmp DungeonLoop`: in the C it calls DungeonLoop (never comes back). */
#ifndef U3_EXODUS_DUNEVENT_H
#define U3_EXODUS_DUNEVENT_H
#include "../u3.h"
#include "exodus_data.h"

void EventTimeVision(u8 *bx);               /* BX = the address of the event cell (DungeonEventCmds) */
void EventFountain(u8 *bx);                 /* (BX is not read: the cell stays) */
void Fountain_Ask(void);                    /* a label inside EventFountain, jumped to by the effects */
void FountainCure(u8 *bx, u8 cl);           /* BX = the player's record, CL = player 1-4 */
void FountainPoison(u8 *bx, u8 cl);
void FountainHeal(u8 *bx, u8 cl);
void FountainHurt(u8 *bx, u8 cl);
void EventWind(u8 *bx);                     /* (BX is not read) */
void EventTrap(u8 *bx);
void EventRod(u8 *bx);                      /* (BX is not read) */
void EventGremlins(u8 *bx);
void EventWriting(u8 *bx);
void DrawDungeon(void);

#endif
