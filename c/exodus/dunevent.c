/* dunevent.c: src/exodus/DUNEVENT.ASM, dungeon events: fountains, the rod, gremlins (941E-964F).
 *
 * The handlers of the dungeon's event cells, reached from DungeonTurnEnd (DUNMOVE) through
 * DungeonEventCmds with BX = the address of the cell (01-08): 1 EventTimeVision, 2 EventFountain,
 * 3 EventWind, 4 EventTrap, 5 EventRod, 6 EventGremlins, 8 EventWriting (7 has none). Time vision,
 * trap, gremlins and writing clear their cell (they happen once); fountain, wind and rod stay.
 * All go back to DungeonLoop (`jmp DungeonLoop`: a call in the C, it never comes back). The
 * pictures (TIME, FOUNTAIN, BRAND .IMG) are loaded over StartUp as the view buffer, with
 * Location = 4 while one is shown.
 *
 * The fountain's effects (FountainCure ... FountainHurt) are entered through FountainCmds with
 * BX = the player's record and CL = the player's number 1-4 as EventFountain left them, and end
 * with `jmp Fountain_Ask`. PlayerXY is the party's x here (a dungeon cell x), low byte.
 */
#include "../u3.h"
#include "../lib/lib.h"
#include "exodus_data.h"
#include "dunevent.h"
#include "dunmove.h"
#include "combat.h"
#include "party.h"
#include "items.h"
#include "bcd.h"

/* from VIEW, not yet read: */
void PrintMsg(const u8 *si);                    /* SI = the string (saves all) */
void ScrollMsg(void);
void ClearView(void);

/* asm: EventTimeVision @941E */
void EventTimeVision(u8 *bx)
{
    *bx = 0;                                    /* the cell becomes floor: once only */
    LoadFile(StartUp, 0x79, FileTimeImg);       /* load the picture over StartUp */
    DrawView();                                 /* draw the view buffer */
    Location = 4;                               /* 4: a picture is shown */
    PrintMsg(MsgTimeVision);                    /* the Time Lord's words */
    FlushKeys();
    while (!KeyReady())                         /* TimeVision_Wait */
        ;
    ReadKey();
    ScrollMsg();
    DrawDungeon();                              /* back to the 3D view */
    Location = 1;                               /* 1: in a dungeon */
    DungeonLoop();                              /* never comes back */
}

/* asm: EventFountain @9457 */
void EventFountain(u8 *bx)
{
    (void)bx;                                   /* not read: the cell stays */
    LoadFile(StartUp, 0x79, FileFountainImg);
    DrawView();
    Location = 4;
    FlushKeys();
    Fountain_Ask();                             /* falls through into Fountain_Ask */
}

/* asm: Fountain_Ask @9470 */
void Fountain_Ask(void)
{
    for (;;) {
        PrintMsg(MsgFountain);
        u8 *bx;
        u8 al = AskPlayer(&bx);                 /* 0: Esc; else AL = 1-4, BX = record */
        if (al == 0) {                          /* Fountain_Done */
            Location = 1;
            DrawDungeon();
            DungeonLoop();                      /* never comes back */
            return;
        }
        u8 cl = al;                             /* CL = player number 1-4 */
        if (!IsUp(bx)) {                        /* Fountain_Cant */
            PrintMsg(MsgFountainCant);          /* "Can't!" */
            Sound(0xFF);                        /* buzz sound */
            continue;                           /* jmp Fountain_Ask */
        }
        al = PlayerXY & 0xFF;                   /* the fountain's x ... */
        al &= 3;                                /* ... & 3 picks the effect */
        ((void (*)(u8 *, u8))FountainCmds[al])(bx, cl);     /* jmp word ptr FountainCmds[si] */
        return;
    }
}

/* asm: FountainCure @94AB */
void FountainCure(u8 *bx, u8 cl)
{
    (void)cl;
    PrintMsg(MsgAhNice);                        /* "Ah! That's nice!" */
    bx[0x11] = 0x47;                            /* status 'G' */
    StatusLine();
    Fountain_Ask();
}

/* asm: FountainPoison @94BB */
void FountainPoison(u8 *bx, u8 cl)
{
    PrintMsg(MsgYuckHorrible);                  /* "Yuck! Horrible!" */
    bx[0x11] = 0x50;                            /* status 'P' */
    cl--;
    FlashPlayer(cl);                            /* flash the status line */
    Sound(0xF7);                                /* hit sound */
    FlashPlayer(cl);
    StatusLine();
    Fountain_Ask();
}

/* asm: FountainHeal @94DC */
void FountainHeal(u8 *bx, u8 cl)
{
    (void)cl;
    bx[0x1A] = bx[0x1C];                        /* max hit points (word 1Ch) ... */
    bx[0x1B] = bx[0x1D];                        /* ... into the hit points (word 1Ah) */
    PrintMsg(MsgHowWonderful);                  /* "How wonderful!" */
    StatusLine();
    Fountain_Ask();
}

/* asm: FountainHurt @94EE */
void FountainHurt(u8 *bx, u8 cl)
{
    PrintMsg(MsgArghBlah);                      /* "Argh! Blah! Yuk!" */
    HurtPlayer(0x25, bx);                       /* 25 (BCD) subtracted from the hit points */
    FlashView();                                /* flash (PARTY) */
    cl--;
    FlashPlayer(cl);
    Sound(0xF7);                                /* hit sound */
    FlashPlayer(cl);
    FlashView();
    StatusLine();
    Fountain_Ask();
}

/* asm: EventWind @9517 */
void EventWind(u8 *bx)
{
    (void)bx;                                   /* not read: the cell stays */
    PrintMsg(MsgStrangeWind);                   /* "Strange wind!" */
    LightOn = 0;                                /* the torch is out */
    ClearView();
    DungeonLoop();                              /* never comes back */
}

/* asm: EventTrap @9529 */
void EventTrap(u8 *bx)
{
    *bx = 0;                                    /* the cell becomes floor */
    PrintMsg(MsgArghTrap);                      /* "Argh!! A trap!!" */
    Sound(0xF6);                                /* tick sound */
    bx = Players;                               /* always player 1 */
    if (DexRoll(bx))                            /* ZF set: evaded */
        PrintMsg(MsgEvadedTrap);                /* "Evaded!!" */
    else
        DamageParty();                          /* Trap_Hit: the whole party */
    DungeonLoop();                              /* never comes back */
}

/* asm: EventRod @9550 */
void EventRod(u8 *bx)
{
    (void)bx;                                   /* not read: the cell stays */
    LoadFile(StartUp, 0x79, FileBrandImg);
    DrawView();
    Location = 4;
    PrintMsg(MsgRedHotRod);                     /* "A red hot rod ..." */
    FlushKeys();
    u8 *rec;
    u8 al = AskPlayer(&rec);                    /* 0: Esc; else AL = 1-4, BX = record */
    if (al != 0) {
        u8 ah = PlayerXY & 0xFF;                /* the rod's x ... */
        ah &= 3;
        u8 cl = ah;
        cl += 4;                                /* ... & 3 + 4: bit 4-7 */
        ah = 1;
        ah = (u8)(ah << cl);
        rec[0x0E] |= ah;                        /* marks (record 0Eh, bits 7-4) */
        al--;
        FlashPlayer(al);                        /* flash the status line */
        ah = al;
        Sound(0xF7);                            /* hit sound (AH survives it) */
        al = ah;
        FlashPlayer(al);
        HurtPlayer(0x50, rec);                  /* 50 (BCD) damage */
        StatusLine();
        PrintMsg(MsgLeftMark);                  /* "It left a mark!" */
    }
    Location = 1;                               /* Rod_Done */
    DrawDungeon();
    DungeonLoop();                              /* never comes back */
}

/* asm: EventGremlins @95B3 */
void EventGremlins(u8 *bx)
{
    *bx = 0;                                    /* the cell becomes floor */
    u8 dh = PartySize;
    u8 dl = Random(dh);                         /* DL = a player 0 .. PartySize-1 */
    bx = Players + 0x40 * dl;                   /* BX = his record */
    if (IsUp(bx)) {
        PrintMsg(MsgGremlins);                  /* "Gremlins!" */
        u8 al = bx[0x22];                       /* food, BCD word 21h-22h: xchg al, ah = the high byte (hundreds) */
        bool cf = false;
        al = SubDas(al, 1, &cf);                /* sub al, 1 / das: 100 food less */
        bx[0x22] = al;                          /* xchg al, ah / mov word ptr [bx+21h], ax */
        if (cf) {                               /* jae not taken: a borrow, less than 100 */
            bx[0x21] = 0;                       /* mov word ptr [bx+21h], 0: no food at all */
            bx[0x22] = 0;
            PrintMsg(MsgStarving);              /* "Starving!" */
            FlashPlayer(dl);                    /* flash the status line */
            Sound(0xF7);                        /* hit sound */
            FlashPlayer(dl);
            HurtPlayer(5, bx);                  /* 5 (BCD) damage */
        }
    }
    StatusLine();                               /* Gremlins_Done */
    Sound(0xFA);                                /* rise sound */
    DungeonLoop();                              /* never comes back */
}

/* asm: EventWriting @960D */
void EventWriting(u8 *bx)
{
    *bx = 0;                                    /* the cell becomes floor */
    PrintMsg(MsgMistyWriting);                  /* "Misty writing:" */
    u16 level2 = (u16)(DungeonLevel << 1);      /* bh = 0, shl bx, 1 */
    u16 si = MapText[level2] | (MapText[level2 + 1] << 8);  /* offset of this level's message */
    PrintMsg(MapText + si);
    ScrollMsg();
    DungeonLoop();                              /* never comes back */
}

/* asm: DrawDungeon @9630 */
void DrawDungeon(void)
{
    ClearView();
    if (LightOn != 0) {                         /* no torch: nothing to see */
        u8 al = Facing;
        u8 ah = DungeonLevel;
        u16 bx = (u16)((PlayerXY & 0xFF) | (PlayerY << 8));     /* mov bx, word ptr PlayerXY */
        /* call near ptr MapBuf: MapBuf (0100) holds DUNGEON.DAT's code here, not a map; its entry
         * (a jump to the code at 0447, c/dungeon/dungeon.c) draws the 3D corridor for AL = facing,
         * AH = level, BX = x, y. */
        void (*overlay)(u8, u8, u16) = (void (*)(u8, u8, u16))(uintptr_t)MapBuf;
        overlay(al, ah, bx);
    }
}
