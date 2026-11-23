/* create.h: the routines of CREATE.ASM (roster commands and the helpers of the whole program). */
#ifndef U3_BOOTUP_CREATE_H
#define U3_BOOTUP_CREATE_H
#include "../u3.h"
#include "bootup_data.h"

void ExamineRegister(void);
void TerminateChar(void);
void CreateChar(void);
void DrawCreateForm(void);
void EnterCharacter(u8 *bx);                /* BX = the empty roster record to fill */
void ShowPointsLeft(u8 cl);                 /* CL = the points left, BCD */
void WaitSpace(void);
void PartyToRoster(void);
void RosterToParty(void);
u8 *RosterRecord(u8 bl);                    /* BL = roster number 1-20; returns BX = the record in Roster */
void AnimateDemo(void);
u8 CheckAlive(const u8 *bx);                /* BX = a record; returns AL = 0 if Good or Poisoned, else 0FFh */
u8 AnyAlive(void);                          /* returns AH = 0FFh if one of the four party records is alive, else 0 */
void AskScenarioDisk(void);                 /* disabled: a ret */
u16 AskNumber(void);                        /* returns AX: AL = the number in BCD, AH = in binary */

#endif
