/* intro.h: the routines of ULTIMA.COM (src/ultima/INTRO.ASM) as the C calls them.
 * Data: ultima_data.h (generated). Parameters are named after the registers they come in;
 * see c/README.md "Calling conventions". */
#ifndef U3_INTRO_H
#define U3_INTRO_H
#include "../u3.h"
#include "../lib/lib.h"
#include "ultima_data.h"

u8 CritErrRetry(void);                          /* int 24h handler: AL = 1 (retry) */
void BreakHandler(void);                        /* int 23h handler: iret */
void StartUp(void);                             /* the entry; never returns */
void Delay(u16 ax);
void DrawSignature(u16 si);                     /* SI = wait between two points */
void DissolveExodus(void);
void DrawDragonFire(void);
void DrawDragonAlone(void);
void DissolveUltima(void);
void DrawBy(void);
void DrawCopyright(void);
void PlotPixel(u8 cl, u8 ch);                   /* x (+20 inside), scan line; ES = the video segment */
void CopyPicture(u8 bl, u8 bh, u8 dl, u8 dh, u16 cx, u8 ah, u8 al);
                                                /* picture line, screen line, lines, words, first byte,
                                                   0 = plain copy / else dissolve, threshold */
void AnimateParty(void);
void DrawAnimFrame(u8 al, u16 bx);              /* AH = 0 is assumed (`mul cx` multiplies AX) */
void SetGraphicsMode(void);

#endif
