/* ending.c: the move count and the end of the game (src/exodus/ENDING.ASM, A46F-A5AC).
 *
 * PrintMoves prints the move counter (also called from LOOP's Quit & Save). EndGame is reached from
 * ACTIONS when Exodus is destroyed: the congratulations and the move count, the map window flashed
 * 21 times, the final text, a key, and the program stops for ever. AskYesNo and PayGold are two
 * helpers of the town services (TOWNS uses them).
 * The texts are in TEXT.ASM (text.c); no data label belongs to this module.
 */
#include "../u3.h"
#include "../lib/lib.h"
#include "exodus_data.h"
#include "ending.h"
#include "party.h"
#include "bcd.h"

/* from VIEW, not yet read: */
extern void PrintMsg(const u8 *si);
extern void ScrollMsg(void);
extern void ClearView(void);

/* asm: PrintMoves @A46F */
void PrintMoves(void)
{
    /* The assembly sets the direction flag (std) and reads with lodsb, so SI runs backwards from
     * the top byte MoveCount+3 down to MoveCount (cld afterwards). The 8 digits come most
     * significant byte first. */
    const u8 *si = MoveCount + 3;
    for (u16 cx = 4; cx != 0; cx--)
        PrintBcdByte(*si--);                    /* two digits */
    PrintMsg(MsgMoves);                         /* " moves" */
}

/* asm: XorMapWindow @A491 -- ScreenSeg is read from the absolute word ds:[4F39h], not a label here;
 * CgaMem stands for that segment */
void XorMapWindow(u16 ax)
{
    u16 bx = 0x142;                             /* scan line 8 (4 x 80 bytes), pixel 8 (byte 2) */
    for (u16 dx = 0x58; dx != 0; dx--) {        /* 58h lines (x 2 banks) */
        for (u16 cx = 0x16; cx != 0; cx--) {    /* 16h words: 176 pixels */
            CgaMem[bx] ^= ax & 0xFF;            /* xor word ptr [bx], ax (little endian) */
            CgaMem[bx + 1] ^= ax >> 8;
            CgaMem[bx + 0x2000] ^= ax & 0xFF;   /* the odd scan line */
            CgaMem[bx + 0x2001] ^= ax >> 8;
            bx += 2;
        }
        bx += 0x24;                             /* to the next line (80 bytes) */
    }
}

/* asm: EndGame @A4B9 */
void EndGame(void)
{
    PrintMsg(MsgCongratulations);
    PrintMoves();
    PrintMsg(MsgReportThyFeat);
    const u8 *si = EndFlashPatterns;            /* cld; lodsw reads the patterns upwards */
    for (u16 cx = 0x15; cx != 0; cx--) {        /* 21 patterns */
        Sound(0xF7);
        u16 ax = si[0] | (si[1] << 8);
        si += 2;
        XorMapWindow(ax);
    }
    ClearView();
    PrintAt(0x0305, MsgEndLine1);               /* row 3, column 5 */
    PrintAt(0x0502, MsgEndLine2);               /* then rows 5, 7, ... 15h at column 2 */
    PrintAt(0x0702, MsgEndLine3);
    PrintAt(0x0902, MsgEndLine4);
    PrintAt(0x0B02, MsgEndLine5);
    PrintAt(0x0D02, MsgEndLine6);
    PrintAt(0x0F02, MsgEndLine7);
    PrintAt(0x1102, MsgEndLine8);
    PrintAt(0x1302, MsgEndLine9);
    PrintAt(0x1502, MsgEndLine10);
    SaveGame();                                 /* ? (PARTY: depends on Location) */
    Location = 1;                               /* Location = 1 (dungeon) ?why */
    while (!KeyReady())                         /* EndGame_WaitKey */
        ;
    ReadKey();
    Hang();                                     /* jmp Hang: never returns */
}

/* asm: AskYesNo @A561 */
u8 AskYesNo(void)
{
    /* AskChoice's string table is YesNoMenuStrs: four words (addresses) written as db in the
     * assembly, so the C casts the byte array to the table of pointers it holds. */
    u8 al = AskChoice(4, YesNoMenuKeys, (const u8 *const *)YesNoMenuStrs);   /* four keys: Y N Q Esc */
    ScrollMsg();
    if (al != 0x59)                             /* 'Y' */
        al = 0x4E;                              /* 'N' for N, Q and Esc */
    return al;
}

/* asm: PayGold @A587 */
bool PayGold(u8 *di, u16 ax)
{
    /* The gold is the BCD word at [di+23h]. The routine swaps it with AX to compare and swaps back
     * (the flags survive the xchg); CF = gold < price: nothing is taken. */
    u16 gold = di[0x23] | (di[0x24] << 8);
    if (gold < ax)                              /* binary compare: it orders BCD words correctly */
        return true;                            /* CF: not enough */
    bool cf = false;
    u8 lo = SubDas(gold & 0xFF, ax & 0xFF, &cf);        /* sub al, [di+23h] / das */
    u8 hi = SubDas(gold >> 8, ax >> 8, &cf);            /* sbb al, [di+24h] / das (the borrow goes on) */
    di[0x23] = lo;                              /* gold = the rest, AX = the price again */
    di[0x24] = hi;
    /* `jae PayGold_Done` is always taken here (no borrow is left); the assembly's
     * `mov word ptr [di+23h], 0` after it is not reached, as its comment says. */
    return false;
}
