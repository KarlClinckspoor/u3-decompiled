/* world.h: the routines of WORLD.ASM (src/exodus/WORLD.ASM). Data: exodus_data.h (generated).
 * Parameters are named after the registers they come in; see c/README.md "Calling conventions".
 *
 * StartUp (the program's entry, 24C4) has no prototype here: COMBAT's C (combat.h) declares the same
 * name as the combat area `extern u8 StartUp[]` (its memory is reused once it has run), and the two
 * clash in a file that includes both. world.c defines `void StartUp(void)`; nobody calls it (BOOTUP
 * jumps through the vector at 1328, which has no label). */
#ifndef U3_EXODUS_WORLD_H
#define U3_EXODUS_WORLD_H
#include "../u3.h"
#include "exodus_data.h"

void SaveSosaria(void);                     /* the map buffer to SOSARIA.ULT, then SaveParty */
void SaveParty(void);                       /* PARTY.ULT: the 112h bytes of the party record */
void AdvanceMoons(void);
void Whirlpool(void);
/* In: SI = creature slot, DX = the cell (DL x, DH y), AL = its map byte. Returns AL = 0FFh yes, 0 no. */
u8 MonCanEnter(u16 si, u16 dx, u8 al);
void MonTurn(void);                         /* jumped to by MainLoop; ends in ReadCommandNoView, never comes back */
void SpawnMonster(void);
void MonShoot(u16 si);                      /* SI = creature slot */
/* Moves every creature. Returns true when one attacked: the assembly then drops its own frame and MonTurn's and
 * jumps to FightCreature (which never comes back): the caller must return at once. */
bool MoveMonsters(void);

#endif
