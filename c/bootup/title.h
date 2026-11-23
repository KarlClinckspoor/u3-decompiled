/* title.h: the routines of TITLE.ASM (start-up and the title picture). */
#ifndef U3_BOOTUP_TITLE_H
#define U3_BOOTUP_TITLE_H
#include "../u3.h"
#include "bootup_data.h"

void BreakHandler(void);            /* the int 23h handler: an iret */
void StartUp(void);                 /* the program's entry (jmp at 0100); never returns */
void TitleLoop(void);               /* never returns */
void TitleLoop_Prompt(void);        /* TitleLoop from the "Press <Space>" line on: StartUp jumps here */
void DrawMenuFrame(u16 dx);         /* DX = screen offset of the bottom line */
void ClearMenu(void);
void RunMainMenu(void);
void JourneyOnward(void);           /* returns only when the party cannot start; else chain-loads EXODUS.BIN */

#endif
