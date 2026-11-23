/* magic.h: the routines of MAGIC.ASM (src/exodus/MAGIC.ASM). Data: exodus_data.h (generated).
 * Parameters are named after the registers they come in; see c/README.md "Calling conventions".
 * A player record is a `u8 *` (BX) to the 64 bytes in Players (docs/FORMATS.md 6).
 * Every spell handler is entered by CastSpell with BX = the caster's record and DL = the spell's
 * index (SpellFlash's pitch) and ends by jumping to Cast_Done or Cast_Failed: in the C CastSpell
 * calls the handler and returns, and the handler calls Cast_Done / Cast_Failed as its last act. */
#ifndef U3_EXODUS_MAGIC_H
#define U3_EXODUS_MAGIC_H
#include "../u3.h"
#include "exodus_data.h"

void CastSpell(u8 *bx);                     /* BX = the caster's record */
void Cast_Menu(u8 *bx, const Proc *di, const u8 *si, u8 dh);   /* the middle of CastSpell: DI = handler table, SI = prompt, DH = 0 / 10h */
void Cast_Done(void);
void Cast_MPLow(void);
void Cast_Failed(void);
void SpellFlash(u8 dl);                     /* DL = the spell's index */
void HitAllMonsters(u8 al);                 /* AL = damage (0FFh: kills) */
void HealPlayer(u8 dh, u8 dl);              /* DH = BCD amount; DL = the spell's index (for SpellFlash) */
void CastDirected(u8 al);                   /* AL = damage (the handlers' DL is lost: AskDirection returns the step in DX) */
void DungeonTeleport(void);

void SpellRepond(u8 *bx, u8 dl);
void SpellMittar(u8 *bx, u8 dl);
void SpellLorum(u8 *bx, u8 dl);
void SpellDorAcron(u8 *bx, u8 dl);
void SpellSurAcron(u8 *bx, u8 dl);
void SpellFulgar(u8 *bx, u8 dl);
void SpellDagAcron(u8 *bx, u8 dl);
void SpellMentar(u8 *bx, u8 dl);
void SpellDagLorum(u8 *bx, u8 dl);
void SpellFalDivi(u8 *bx, u8 dl);
void SpellNoxum(u8 *bx, u8 dl);
void SpellDecorp(u8 *bx, u8 dl);
void SpellAltair(u8 *bx, u8 dl);
void SpellDagMentar(u8 *bx, u8 dl);
void SpellNecorp(u8 *bx, u8 dl);
void SpellZxkuqyb(u8 *bx, u8 dl);
void SpellPontori(u8 *bx, u8 dl);
void SpellApparUnem(u8 *bx, u8 dl);
void SpellSanctu(u8 *bx, u8 dl);
void SpellLibRec(u8 *bx, u8 dl);
void SpellAlcort(u8 *bx, u8 dl);
void SpellSequitu(u8 *bx, u8 dl);
void SpellSanctuMani(u8 *bx, u8 dl);
void SpellVieda(u8 *bx, u8 dl);
void SpellSurmandum(u8 *bx, u8 dl);
void SpellAnjuSermani(u8 *bx, u8 dl);

#endif
