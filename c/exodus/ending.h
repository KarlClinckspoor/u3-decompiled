/* ending.h: the routines of ENDING.ASM (src/exodus/ENDING.ASM). Data: exodus_data.h (generated).
 * Parameters are named after the registers they come in; see c/README.md "Calling conventions". */
#ifndef U3_EXODUS_ENDING_H
#define U3_EXODUS_ENDING_H
#include "../u3.h"
#include "exodus_data.h"

void PrintMoves(void);
void XorMapWindow(u16 ax);                  /* AX = the pattern */
void EndGame(void);                         /* never returns */
u8 AskYesNo(void);                          /* returns AL = 'Y' (59h) or 'N' (4Eh) */
bool PayGold(u8 *di, u16 ax);               /* DI = the record, AX = the price (BCD; AX is kept);
                                               returns true = CF set: not enough gold, nothing taken */

#endif
