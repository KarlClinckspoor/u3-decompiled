/* equip.h: the routines of EQUIP.ASM (src/exodus/EQUIP.ASM). Data: exodus_data.h (generated).
 * Parameters are named after the registers they come in; see c/README.md "Calling conventions".
 * A player record is a `u8 *` (BX, DI) to the 64 bytes in Players (docs/FORMATS.md 6).
 * The shared exits (MsgNoneLeft ... MsgIncapacitated) end with `jmp MainLoop`: they print, beep,
 * drop the waiting keys and the turn ends. In the C a command calls one and returns. */
#ifndef U3_EXODUS_EQUIP_H
#define U3_EXODUS_EQUIP_H
#include "../u3.h"
#include "exodus_data.h"

u16 ReadAmount(void);                       /* returns AX = the number (up to 4 digits) as BCD */
u16 TransferBcd(u16 ax, u16 *cx, u16 *dx);  /* AX = amount, CX = from, DX = to (in/out); returns AX: 0 done,
                                               1 CX too small, 2 DX would pass 9999 (CX, DX unchanged then) */
void MsgNoneLeft(void);
void MsgWhat(void);
void MsgInvalidMove(void);
void MsgNotHere(void);
void MsgIncapacitated(void);
void AddMoves(u8 al);                       /* AL = BCD amount */
void CmdReady(const u8 *si);                /* SI = the prompt */
void ReadyWeapon(u8 *bx);                   /* BX = the record */
void CmdWear(const u8 *si);                 /* SI = the prompt */
void WearArmour(u8 *bx);                    /* BX = the record */
u16 FindMonster(u8 dl, u8 dh);              /* DL, DH = x, y; returns BX = the slot 0-31 or 0FFFFh */
void CmdTransact(const u8 *si);             /* SI = the prompt */
void ChestLoot(u8 *di);                     /* DI = the record */

#endif
