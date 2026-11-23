/* bcd.h: the 8086's decimal adjust (daa, das, aam), as the BCD routines of ITEMS, EQUIP and MAGIC use it.
 * Not routines of the game: stand-ins for instructions (c/README.md, "The machine"), written out
 * exactly (the flags included) so that the carry the assembly tests afterwards is the carry
 * computed here. */
#ifndef U3_EXODUS_BCD_H
#define U3_EXODUS_BCD_H
#include "../u3.h"

/* `add a, b` (or `adc a, b` when *cf is set on entry) followed by `daa`; *cf is the carry flag after the daa. */
static inline u8 AddDaa(u8 a, u8 b, bool *cf)
{
    unsigned cin = *cf ? 1 : 0;
    unsigned sum = (unsigned)a + b + cin;
    bool af = ((a & 0x0F) + (b & 0x0F) + cin) > 0x0F;
    u8 al = sum & 0xFF, old_al = al;
    bool old_cf = sum > 0xFF;
    bool c = false;
    if ((al & 0x0F) > 9 || af) {
        c = old_cf || (unsigned)al + 6 > 0xFF;
        al = (u8)(al + 6);
    }
    if (old_al > 0x99 || old_cf) {
        al = (u8)(al + 0x60);
        c = true;
    }
    *cf = c;
    return al;
}

/* `sub a, b` (or `sbb a, b` when *cf is set on entry) followed by `das`; *cf is the carry (borrow) flag after the das. */
static inline u8 SubDas(u8 a, u8 b, bool *cf)
{
    unsigned cin = *cf ? 1 : 0;
    bool af = (unsigned)(a & 0x0F) < (unsigned)(b & 0x0F) + cin;
    bool old_cf = (unsigned)a < (unsigned)b + cin;
    u8 al = (u8)(a - b - cin), old_al = al;
    bool c = false;
    if ((al & 0x0F) > 9 || af) {
        c = old_cf || al < 6;
        al = (u8)(al - 6);
    }
    if (old_al > 0x99 || old_cf) {
        al = (u8)(al - 0x60);
        c = true;
    }
    *cf = c;
    return al;
}

/* `aam / mov cl, 4 / shl ah, cl / or al, ah`: the binary AL (0-99) as a BCD byte (aam: AH = AL / 10, AL = AL % 10). */
static inline u8 ToBcd(u8 al)
{
    u8 ah = al / 10;
    al = al % 10;
    return (u8)(al | (u8)(ah << 4));
}

#endif
