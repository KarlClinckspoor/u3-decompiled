/* bdata.h: the routine of BDATA.ASM (the data is in bootup_data.h, generated). */
#ifndef U3_BOOTUP_BDATA_H
#define U3_BOOTUP_BDATA_H
#include "../u3.h"
#include "bootup_data.h"

/* PrintAt / SwapCursor take the cursor as one word: DH = row, DL = column. `mov dh, r / mov dl, c`
 * before the call is AT(r, c) in the C (not in the assembly: a notation of this reading). */
#define AT(row, col)  ((u16)(((row) << 8) | (col)))

/* Labels before 0100: places in the program segment prefix (Psp, u3.h), no data of their own. */
#define PspFcb        (Psp + 0x5C)                  /* the PSP's first FCB */
#define FcbCurBlock   (*(u16 *)(Psp + 0x68))        /* its current block (word) */
#define FcbRecSize    (*(u16 *)(Psp + 0x6A))        /* record size (word) */
#define FcbFileSize   (*(u16 *)(Psp + 0x6C))        /* file size, low word */
#define FcbCurRec     (Psp[0x7C])                   /* current record (byte) */
#define ChainInt21    (*(u16 *)(Psp + 0xFA))        /* where JourneyOnward plants `int 21h` ... */
#define ChainJmp      (*(u16 *)(Psp + 0xFC))        /* ... and `jmp word ptr [...]` */
#define ChainJmpAddr  (*(u16 *)(Psp + 0xFE))        /* ... whose operand is this word */

u8 CritErrRetry(void);              /* the int 24h handler; returns AL = 1, then runs on into BreakHandler's iret */

#endif
