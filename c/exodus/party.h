/* party.h: the routines of PARTY.ASM (src/exodus/PARTY.ASM). Data: exodus_data.h (generated).
 * Parameters are named after the registers they come in; see c/README.md "Calling conventions".
 * A player record is a `u8 *` (BX, DI) to the 64 bytes in Players (docs/FORMATS.md 6). */
#ifndef U3_EXODUS_PARTY_H
#define U3_EXODUS_PARTY_H
#include "../u3.h"
#include "exodus_data.h"

void SaveGame(void);
u8 HurtPlayer(u8 al, u8 *bx);               /* AL = BCD damage; returns AL = 0FFh if the player died, else 0 */
void PrintName(u8 al);
bool IsUp(const u8 *bx);                    /* true = ZF set (AL = 0): status Good or Poisoned;
                                               false = ZF clear (AL = 0FFh): Dead or Ashes */
void CheckAllOut(void);
void FlushKeys(void);
u8 AskPlayer(u8 **bx);                      /* returns AL = 1-4, or 0 (ZF set) for nobody; *bx = the record
                                               (only written when a slot 1-4 was typed); AH is kept */
void StatusLine(void);
void DrawPlayerNums(void);
void PrintNameCentered(u8 al, const u8 *bx);
void ShowZtats(u8 dh, u8 *di);              /* DH = '1'-'4', DI = the record */
u8 WaitMore(void);                          /* returns AL: 0 go on, 0FFh Esc */
void PartyUpkeep(void);
void SpendFood(u8 al, u8 *bx);
void AddMagicPoint(u8 *bx);
u8 HalveBcd(u8 al);
void FlashPlayer(u8 al);                    /* AL = player 0-3 */
void FlashView(void);
void InvertPlayerNum(u8 al);                /* AL = player 1-4 */
u8 AgainstWind(u8 al);                      /* returns AL = 0FFh (ZF clear) = may not go that way, else 0 (ZF set) */
void Hang(void);                            /* `jmp Hang`: never returns (also declared in u3.h) */
u8 CheckTerrain(u8 al);                     /* returns AL = 0 (ZF set) = may enter, 0FFh (ZF clear) = no */
u8 MoveWhirlpool(u8 bl);                    /* BL = the caller's key wait deadline; returns BL (BH is kept) */
void UpcaseBuf(u8 *di, u16 cx);
u8 MatchWord(const u8 *si, const u8 *di, u16 cx);   /* returns AL = 0FFh match, 0 not */

#endif
