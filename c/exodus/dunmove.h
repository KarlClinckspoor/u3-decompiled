/* dunmove.h: the routines of DUNMOVE.ASM (src/exodus/DUNMOVE.ASM). Data: exodus_data.h (generated).
 * Parameters are named after the registers they come in; see c/README.md "Calling conventions".
 * The dungeon's commands are entered from DungeonLoop with SI = the command's prompt and end with
 * `jmp DungeonTurnEnd` (a call in the C) or `jmp MainLoop` (a plain return). */
#ifndef U3_EXODUS_DUNMOVE_H
#define U3_EXODUS_DUNMOVE_H
#include "../u3.h"
#include "exodus_data.h"

void CmdGetChest(const u8 *si);             /* SI = the prompt (also the surface's) */
u8 TryEvadeTrap(u8 al, u8 *di);             /* AL as the caller left it, DI = the record; returns AL (0 = evaded) */
void DamageParty(void);
void EnterDungeon(void);
void DungeonLoop(void);
void DungeonTurnEnd(void);
void CmdKlimb(const u8 *si);                /* SI = the prompt */
void CmdDescend(const u8 *si);
void CmdTurnRight(const u8 *si);
void CmdTurnLeft(const u8 *si);
void CmdNotDungeon(const u8 *si);
void CmdAdvance(const u8 *si);
void CmdRetreat(const u8 *si);

#endif
