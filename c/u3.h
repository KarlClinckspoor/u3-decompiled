/* u3.h: what every C file of the reading shares. See c/README.md for the conventions.
 *
 * A reading aid, not a port (see README.md): the assembly in ../src is the ground truth.
 */
#ifndef U3_H
#define U3_H
#include <stdint.h>
#include <stdbool.h>

typedef uint8_t u8;
typedef uint16_t u16;
typedef int8_t i8;
typedef int16_t i16;
typedef void (*Proc)();             /* a routine in a table of addresses; the C casts its own */

/* ---- The machine -----------------------------------------------------------------------------
 * The BIOS, DOS, the ports and the CGA's memory are not part of the game. The C calls these
 * stand-ins where the assembly executes an `int`, an `in`/`out` or writes to the screen segment.
 * (No definitions: the reading is not linked or run.) */
extern u8 CgaMem[0x4000];           /* B800:0000 - 3FFF: even scan lines at 0000, odd ones at 2000h */
extern u8 Psp[0x100];               /* the program segment prefix: the FCB at 5Ch (+0Ch block at 68h,
                                       record size 6Ah, file size 6Ch, current record 7Ch) */
u16 BiosReadKey(void);              /* int 16h AH=0: AH scan code, AL character (waits) */
bool BiosKeyWaiting(void);          /* int 16h AH=1: true when a key waits (ZF clear) */
u8 InPort(u8 port);                 /* in al, port */
void OutPort(u8 port, u8 value);    /* out port, al */
void DosSetDta(u8 *buffer);         /* int 21h AH=1Ah */
void DosParseName(const u8 *name, u8 *fcb);     /* int 21h AH=29h: parse the name into the FCB */
u8 DosOpenFcb(u8 *fcb);             /* int 21h AH=0Fh: AL (0FFh = not found) */
u8 DosReadFcb(u8 *fcb);             /* int 21h AH=14h: sequential read, AL */
u8 DosWriteFcb(u8 *fcb);            /* int 21h AH=15h: sequential write, AL */
void DosCloseFcb(u8 *fcb);          /* int 21h AH=10h */
void Hang(void);                    /* `jmp $`: the program stops here for ever */

#endif
