/* actions.h: the routines of ACTIONS.ASM (src/exodus/ACTIONS.ASM). Data: exodus_data.h (generated).
 * Every command ends with `jmp MainLoop` (the turn ends): in the C it just returns.
 * The Other command's handlers (CmdInsert, CmdDig, CmdSearch, CmdBribe, CmdPray) are entered
 * by CmdOther with DI = the player's record and BP = his number 0-3; each takes the registers it reads. */
#ifndef U3_EXODUS_ACTIONS_H
#define U3_EXODUS_ACTIONS_H
#include "../u3.h"
#include "exodus_data.h"

void CmdYell(const u8 *si);                 /* SI = the prompt */
void CmdOther(const u8 *si);                /* SI = the prompt */
void CmdDig(u8 *di);
void CmdPray(void);
void CmdBribe(u8 *di);
void CmdSearch(u8 *di);
void CmdInsert(u8 *di, u16 bp);

#endif
