/* loop.h: the routines of LOOP.ASM (src/exodus/LOOP.ASM). Data: exodus_data.h (generated).
 * Parameters are named after the registers they come in; see c/README.md "Calling conventions".
 * Every surface command is entered from ReadCommand by `jmp SurfaceCmds[bx]` with SI = the command's
 * prompt (SurfacePrompts) and ends with `jmp MainLoop` (the turn ends): in the C it takes `si` and just
 * returns; ReadCommandNoView (EXDATA) then runs MainLoop. */
#ifndef U3_EXODUS_LOOP_H
#define U3_EXODUS_LOOP_H
#include "../u3.h"
#include "exodus_data.h"

void MainLoop(void);                        /* the end of every turn; ends in MonTurn (WORLD), never comes back */
void CmdPass(const u8 *si);                 /* SI = the prompt */
void CmdNorth(const u8 *si);                /* SI = the prompt (CmdSouth, CmdEast, CmdWest likewise) */
void CmdSouth(const u8 *si);
void CmdEast(const u8 *si);
void CmdWest(const u8 *si);
void CmdBoard(const u8 *si);
void CmdCast(const u8 *si);
void CmdEnter(const u8 *si);
void CmdHand(const u8 *si);
void CmdLook(const u8 *si);
void CmdModify(const u8 *si);
void CmdPeer(const u8 *si);
void CmdQuit(const u8 *si);
void CmdSteal(const u8 *si);
void CmdUnlock(const u8 *si);
void CmdVolume(const u8 *si);
void CmdXit(const u8 *si);
void CmdZtats(const u8 *si);

#endif
