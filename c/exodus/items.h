/* items.h: the routines of ITEMS.ASM (src/exodus/ITEMS.ASM). Data: exodus_data.h (generated).
 * Parameters are named after the registers they come in; see c/README.md "Calling conventions".
 * A player record is a `u8 *` (BX, DI) to the 64 bytes in Players (docs/FORMATS.md 6). */
#ifndef U3_EXODUS_ITEMS_H
#define U3_EXODUS_ITEMS_H
#include "../u3.h"
#include "exodus_data.h"

bool InExodusCastle(void);                  /* true = ZF set (AL = 0FFh): the party is in the castle of Exodus */
void MoonGateJump(void);
bool DexRoll(const u8 *bx);                 /* BX = the record; true = ZF set = success */
void CmdFire(const u8 *si);                 /* SI = the prompt */
void CmdJoinGold(const u8 *si);             /* SI = the prompt */
void CmdKlimbDescend(const u8 *si);         /* SI = the prompt */
void CmdIgnite(const u8 *si);               /* SI = the prompt */
void CmdNegate(const u8 *si);               /* SI = the prompt */
u16 ReadKeyUpper(void);                     /* returns AX: AL = the key, AH = the key with a-z made upper case */
void AddHitPoints(u8 al, u8 *bx);           /* AL = BCD amount, BX = the record */
void AddExp(u8 al, u8 *bx);                 /* AL = BCD amount, BX = the record */
void AddGold(u8 al, u8 *bx);                /* AL = BCD amount, BX = the record */

#endif
