/* towns.h: the routines of TOWNS.ASM (src/exodus/TOWNS.ASM). Data: exodus_data.h (generated).
 * Parameters are named after the registers they come in; see c/README.md "Calling conventions".
 * DI is the record of the player who transacts (a `u8 *` to the 64 bytes in Players). */
#ifndef U3_EXODUS_TOWNS_H
#define U3_EXODUS_TOWNS_H
#include "../u3.h"
#include "exodus_data.h"

void ShopPub(u8 *di);
void ShopGrocer(u8 *di);
void ShopTemple(u8 *di);
void TempleCure(u8 *di);                    /* the four temple services are reached by `jmp TempleCmds[bx]` from */
void TempleHeal(u8 *di);                    /* ShopTemple (TempleCmds is a Proc table): in the C ShopTemple calls */
void TempleResurrect(u8 *di);               /* one and returns; each ends as the assembly's exit says */
void TempleRecall(u8 *di);
void ShopWeapons(u8 *di);
void ShopListWeapons(void);
void ShopArmour(u8 *di);
void ShopListArmour(void);
void ShopGuild(u8 *di);
void GuildGems(u8 *di);                     /* the four purchases and GuildDone are reached by `jmp GuildCmds[bx]` */
void GuildKeys(u8 *di);                     /* from ShopGuild_Menu: the C calls one and returns; each ends as the */
void GuildPowders(u8 *di);                  /* assembly's exit says (ShopGuild_More asks "Anything else?" and goes */
void GuildTorches(u8 *di);                  /* back to the menu with a call: a `jmp` that never comes back) */
void GuildDone(u8 *di);
void ShopRadrion(u8 *di);
void ShopHorses(u8 *di);

#endif
