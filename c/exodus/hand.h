/* hand.h: the routines of HAND.ASM (src/exodus/HAND.ASM). Data: exodus_data.h (generated).
 * Parameters are named after the registers they come in; see c/README.md "Calling conventions".
 * A player record is a `u8 *` (SI, DI, BX) to the 64 bytes in Players (docs/FORMATS.md 6). */
#ifndef U3_EXODUS_HAND_H
#define U3_EXODUS_HAND_H
#include "../u3.h"
#include "exodus_data.h"

/* Out: DX = the step (DL x, DH y: -1, 0, 1), BX = PlayerXY + step wrapped at 64 (BL x, BH y), both
 * through the pointers; the return value is ZF: true = Esc (DX = 0, BX = PlayerXY). */
bool AskDirection(u16 *dx, u16 *bx);
void HandEquip(u8 *si, u8 *di);             /* SI = the giver's record, DI = the receiver's */
void HandQuit(void);
/* The handlers of the Hand menu are reached by `jmp HandCmds[bx]` from HandEquip and end by jumping
 * to its exits (Done!, an error, HandQuit): in the C HandEquip calls one and returns. The
 * assembly finds the two records on HandEquip's stack frame ([bp+2] = SI, [bp] = DI); the C passes them. */
void HandGold(u8 *si, u8 *di);
void HandFood(u8 *si, u8 *di);
void HandItems(u8 *si, u8 *di);
void HandWeapons(u8 *si, u8 *di);
void HandArmour(u8 *si, u8 *di);

#endif
