/* combat.h: the routines of COMBAT.ASM (src/exodus/COMBAT.ASM). Data: exodus_data.h (generated).
 * Parameters are named after the registers they come in; see c/README.md "Calling conventions".
 *
 * The combat arrays are the tail of the CNFLCT file in StartUp's memory (docs/FORMATS.md 5, 9).
 * The assembly writes them `CmbMonHP[si]` with SI = StartUp + slot (EXDATA's CmbMonY ... CmbPlrTile
 * are plain offsets 88h ... 0ACh, ORG labels). In the C a register that holds `StartUp + n` is a
 * `u8 *` into StartUp, and `CmbMonHP[si]` is `si[CmbMonHP]`. */
#ifndef U3_EXODUS_COMBAT_H
#define U3_EXODUS_COMBAT_H
#include "../u3.h"
#include "exodus_data.h"

/* EXDATA's offsets into the combat area (ORG 80h ... 0ACh; no storage, so no generated C). */
#ifndef Ofs80h
#define Ofs80h      0x80    /* the 8 foes' x (also MonTalk = MonTile + 80h, LOOP) */
#define CmbMonY     0x88    /* the 8 foes' y */
#define CmbMonUnder 0x90    /* the tile under each foe */
#define CmbMonHP    0x98    /* the foes' hit points, 0 = dead (or a free slot) */
#define CmbPlrX     0xA0    /* the 4 players' x (0FFh = not in the fight) */
#define CmbPlrY     0xA4    /* the 4 players' y */
#define CmbPlrUnder 0xA8    /* the tile under each player */
#define CmbPlrTile  0xAC    /* each player's own tile, by class */
#endif
/* DOS get time (int 21h AH=2Ch), DH = the seconds: a stand-in for the instruction (see u3.h, not defined) */
u8 DosGetSeconds(void);
extern u8 StartUp[];        /* StartUp (WORLD, a code label at 24C4): the view buffer / combat area */

void CmdAttack(const u8 *si);               /* SI = what the main loop left (the command's name) */
void FightCreature(u16 bx);                 /* BX = creature slot 0-31 */
void StartCombat(void);                     /* FoeTile set */
u8 ClassTile(u8 al);                        /* AL = class letter; returns AL = the tile */
void PrintFoeName(u8 al);                   /* AL = 0FFh plural, 0 singular */
void CombatRound(void);
void PlayerTurn(void);
void PlayerTurn_Prompt(void);               /* a label inside PlayerTurn, also jumped to by CCmdBad */
void PlayerTurnEnd(void);                   /* every combat command ends here; also MainLoop while Location = 80h */
void CCmdMove(i8 dl, i8 dh, const u8 *si);  /* DL, DH = the step, SI = the direction's name */
u8 CanWalkOn(u8 al);                        /* returns AL = 0 may enter, 0FFh not */
void CCmdNorth(void);
void CCmdSouth(void);
void CCmdEast(void);
void CCmdWest(void);
void CCmdVolume(void);
void CCmdReady(void);
void CCmdZtats(void);
void CCmdCast(void);
void CCmdNegate(void);
void CCmdPass(void);
void CCmdBad(void);
void CCmdAttack(void);
u16 FindFoeAt(u8 dl, u8 dh);                /* returns BX = the foe's slot 0-7, or 0FFFFh */
u16 ShootLine(u8 dl, u8 dh, i8 cl, i8 ch);  /* from DL, DH stepping CL, CH; returns BX = foe slot or 0FFFFh */
void AttackMissed(void);
void AttackHit(u16 bx);                     /* BX = the foe's slot */
void DamageFoe(u8 al, u8 *bx, u8 *di);      /* AL damage, BX = StartUp + slot, DI = the player's record */
void Victory(void);
u8 FoeCanEnter(u8 al, u8 dl, u8 dh);        /* AL = tile at DL, DH; returns AL = 0FFh may enter, else 0 */
/* In: DI = foe 0-7. Out: AL = distance (0 adjacent, 0FFh no step); BX = the player (0FFFFh none),
 * CX = the step (CL x, CH y), DX = the cell (DL x, DH y) through the pointers. */
u8 FoeChooseMove(u8 di, u16 *bx, u16 *cx, u16 *dx);
void FoeBreathe(u8 di, i8 cl, i8 ch);       /* DI = foe 0-7, CL, CH = the direction */
void FoesTurn(void);
void FoeStep(u8 di, u8 dl, u8 dh);          /* DI = foe 0-7, DL, DH = the cell */
void FoeAttack(u8 bl);                      /* BL = player 0-3 */
void FoeHurtPlayer(u8 bl);                  /* BL = player 0-3 */
void FoePoison(u8 bl);
void FoeSteal(u8 bl);

#endif
