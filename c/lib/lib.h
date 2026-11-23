/* lib.h: the library (src/LIB.INC) as the other modules call it. Data: lib_data.h (generated).
 * Parameters are named after the registers they come in; see c/README.md "Calling conventions". */
#ifndef U3_LIB_H
#define U3_LIB_H
#include "../u3.h"
#include "lib_data.h"

/* Registers the library passes through to the routine it calls from Sound's table: the sound
 * routines read BX / DX as the caller of Sound left them (SndWarble BL/BH, SndNoise BL, SndTrill
 * DL). A caller that sets them on purpose writes SoundBX / SoundDX before Sound(). */
extern u16 SoundBX, SoundDX;

u16 PrintStrLen(const u8 *si);                  /* returns CX = the length */
void PrintStr(const u8 *si);
u16 SwapCursor(u16 dx);                         /* DL col / DH row; returns the old cursor (the new DX) */
void PutChar(u8 al);
void DrawChar(u8 al);
u8 DiskCheckStub(void);                         /* AL = 0 (BOOTUP, ULTIMA), see the anchor */
void FillCell(u16 ax, u16 bx);
void DrawTileBlock(u8 ah, u8 al, const u8 *bx, const u8 *bp, u16 di);   /* rows, columns, tile list, gfx, offset */
void ClearScreen(void);
void IdleNop(void);
u16 ReadLine(u8 *di, u16 cx);                   /* returns BX = characters typed */
u8 Random(u8 dh);                               /* returns DL */
void ScrollTile(u8 *dx, u16 bx);
void AnimScroll(void);
void AnimFlags(void);
void SwapFrames(void);
void BlinkPlayer(void);
void Animate(void);
bool KeyReady(void);                            /* true = a key waits (ZF clear) */
u16 ReadKey(void);                              /* AX = scan code << 8 | character */
void PrintBcdWord(u16 ax);
void PrintBcdByte(u8 al);
void PrintDigit(u8 al);
u16 ParseNumber(const u8 *si, u16 cx, u16 *bx); /* returns DX, BX through the pointer */
u8 AskChoice(u16 cx, const u8 *di, const u8 *const *si);   /* returns AL */
u16 ReadNumber(void);                           /* returns AX: AL BCD value, AH decimal value */
void SaveFile(u8 *bx, u16 cx, const u8 *dx);
void LoadFile(u8 *bx, u16 cx, const u8 *dx);
void OpenFile(u8 *di);
void PrintAt(u16 dx, const u8 *si);
i8 SignStep(u8 *al);                            /* returns AH (-1, 0, +1); *al may lose its top two bits */
void DrawView(void);
u8 ViewTileAt(u8 bl, u8 bh, u8 **bx);           /* returns AL; *bx = the address in ViewTiles */
void WindUpdate(void);
void Sound(u8 al);
void SndBuzz(void);
void SndBeep(void);
void SndWarble(u8 bl, u8 bh);
void SndNoise(u8 bl);
void SndFall(void);
void SndRise(void);
void SndWarbleE0(void);
void SndNoiseRise(void);
void SndHit(void);
void SndTick(void);
void NoiseBurst(u8 bl, u8 bh);
void SndTrill(u8 dl);
void SndSlowFall(void);

/* The text cursor is also used as one word (DL = column, DH = row): `xchg word ptr CursorCol, dx`. */
static inline u16 GetCursor(void) { return CursorCol | (CursorRow << 8); }
static inline void SetCursor(u16 dx) { CursorCol = dx & 0xFF; CursorRow = dx >> 8; }

#endif
