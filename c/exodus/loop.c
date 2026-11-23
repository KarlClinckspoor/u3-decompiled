/* loop.c: the main loop and the surface commands (src/exodus/LOOP.ASM, 1BD5-207D).
 *
 * The turn on the surface and in towns, and the surface commands. The key loop itself is
 * ReadCommand / ReadCommandNoView at the end of EXDATA (exdata.c): it looks the key up in SurfaceKeys
 * and jumps through SurfaceCmds with SI = the prompt. Every command ends with `jmp MainLoop`, the end
 * of the turn: in the C a command just returns (README, "The turn"), and ReadCommandNoView runs MainLoop
 * afterwards. MainLoop itself ends by jumping to MonTurn (WORLD), which comes back to ReadCommandNoView:
 * those jumps are calls here.
 *
 * Every handler takes `si`, the prompt it was entered with; most print it first (CmdBoard, CmdEnter's
 * Sosaria test and the others that do not start with PrintMsg say so).
 */
#include "../u3.h"
#include "../lib/lib.h"
#include "exodus_data.h"
#include "loop.h"
#include "bcd.h"
#include "view.h"
#include "world.h"
#include "equip.h"
#include "party.h"
#include "items.h"
#include "hand.h"
#include "shrine.h"
#include "magic.h"
#include "dunmove.h"
#include "combat.h"
#include "ending.h"

static u16 Rd(const u8 *p) { return p[0] | (p[1] << 8); }      /* a word of a byte table: low byte first */

/* asm: MainLoop @1BD5 */
void MainLoop(void)
{
    u8 al;
    u8 *cell;                                   /* BX after MapCellAddr */

    if (Location == 0x80) {                     /* 80h: a fight */
        PlayerTurnEnd();                        /* jmp PlayerTurnEnd */
        return;
    }
    if (Location == 1) {                        /* dungeon */
        DungeonTurnEnd();                       /* jmp DungeonTurnEnd */
        return;
    }
    AddMoves(PartySize);                        /* MoveCount += PartySize */
    if (Location >= 2) {                        /* towns and castles (2, 3), also Ambrosia (0FFh) */
        if (PlayerXY == 0 || PlayerY == 0)      /* at the map's edge (x 0 or y 0; PlayerY = y) */
            ExitToSosaria();                    /* MainLoop_LeaveTown: "Exit to Sosaria" */
    }
    PartyUpkeep();                              /* poison */
    al = MapCellAddr(PlayerXY, PlayerY, &cell); /* mov bx, word ptr PlayerXY */
    if (al == 0x88) {                           /* on a moon gate (shape 34) */
        MoonGateJump();                         /* the gate teleport */
        AdvanceMoons();                         /* (AL is still 88h: both save AX) */
    } else {
        AdvanceMoons();
        al = MapCellAddr(PlayerXY, PlayerY, &cell);
        if (al == 0x88)                         /* the step of the moons brought a gate under the party */
            MoonGateJump();                     /* (saves AX: AL stays 88h) */
    }
    if (al == 0x30)                             /* whirlpool (shape 12) */
        Whirlpool();
    if (InExodusCastle()) {                     /* ZF set: inside Exodus's castle */
        u8 bl, bh;
        u8 *tile;
        TimeStop = 0;                           /* Negate Time does not work there */
        bl = Random(0x0B);                      /* a random view cell: BL = column, BH = row (0-10) */
        bh = Random(0x0B);
        bool party = (bl == 5 && bh == 5);      /* cmp bx, 505h: the party's own cell (ViewTileAt keeps the flags) */
        al = ViewTileAt(bl, bh, &tile);
        if (party) {
            BuildView();
            *tile = 0x3D;                       /* Fire on the party */
            DrawView();
            DamageParty();                      /* DamageParty: damage every player (DUNMOVE DamageParty) */
        } else if (al == 8) {                   /* floor */
            DrawView();
            *tile = 0x3D;                       /* Fire there, harmless */
            DrawView();
            Sound(0xF7);                        /* sound 0F7h */
        }
    }
    MonTurn();                                  /* jmp MonTurn: the creatures' turn (WORLD) */
}

/* asm: CmdPass @1C77 */
void CmdPass(const u8 *si)
{
    PrintMsg(si);                               /* "Pass" */
}

/* asm: CmdNorth @1C7D */
void CmdNorth(const u8 *si)
{
    PrintMsg(si);
    if (AgainstWind(1) != 0) {                  /* direction 1 = north; ZF clear: refused */
        MsgInvalidMove();                       /* CmdNorth_Blocked: jmp MsgInvalidMove */
        return;
    }
    if (CheckTerrain(TileNorth) != 0) {         /* TileNorth = the tile north; ZF clear: refused */
        MsgInvalidMove();
        return;
    }
    PlayerY--;                                  /* y - 1 */
    PlayerY &= 0x3F;                            /* the coordinates wrap at 64 */
}

/* asm: CmdSouth @1C9E */
void CmdSouth(const u8 *si)
{
    PrintMsg(si);
    if (AgainstWind(3) != 0) {                  /* 3 = south */
        MsgInvalidMove();
        return;
    }
    if (CheckTerrain(TileSouth) != 0) {
        MsgInvalidMove();
        return;
    }
    PlayerY++;
    PlayerY &= 0x3F;
}

/* asm: CmdEast @1CBF */
void CmdEast(const u8 *si)
{
    PrintMsg(si);
    if (AgainstWind(2) != 0) {                  /* 2 = east */
        MsgInvalidMove();
        return;
    }
    if (CheckTerrain(TileEast) != 0) {
        MsgInvalidMove();
        return;
    }
    PlayerXY++;                                 /* PlayerXY = x */
    PlayerXY &= 0x3F;
}

/* asm: CmdWest @1CE0 */
void CmdWest(const u8 *si)
{
    PrintMsg(si);
    if (AgainstWind(4) != 0) {                  /* 4 = west */
        MsgInvalidMove();
        return;
    }
    if (CheckTerrain(TileWest) != 0) {
        MsgInvalidMove();
        return;
    }
    PlayerXY--;
    PlayerXY &= 0x3F;
}

/* asm: CmdBoard @1D01 -- does not print the prompt first: SI is printed only on the "What?" path */
void CmdBoard(const u8 *si)
{
    u8 al;
    u8 *cell;

    if (PartyTile[0] == 0x3F) {                 /* on foot? */
        al = MapCellAddr(PlayerXY, PlayerY, &cell);
        if (al == 0x28) {                       /* horse (shape 10) */
            if (Location != 0xFF) {             /* CmdBoard_Mount */
                *cell = 4;                      /* grass under the horse */
                PartyTile[0] = 0x0A;            /* on a horse */
                PrintMsg(MsgMountHorse);        /* "Mount Horse!" */
                return;
            }
            TimeStop = 0;                       /* an odd side effect: Negate Time ends (no horse to mount in Ambrosia) */
        } else if (al == 0x2C) {                /* frigate (shape 11) */
            *cell = 0;                          /* water under the frigate */
            PartyTile[0] = 0x0B;                /* in a frigate */
            PrintMsg(MsgBoardFrigate);          /* "Board Frigate!" */
            return;
        }
    }
    PrintMsg(si);                               /* CmdBoard_What: the prompt ... */
    MsgWhat();                                  /* ... and "What?" */
}

/* asm: CmdCast @1D4E */
void CmdCast(const u8 *si)
{
    u8 *bx = NULL;

    PrintMsg(si);
    if (AskPlayer(&bx) == 0) return;            /* ZF set: nobody */
    if (!IsUp(bx)) {                            /* ZF clear: dead or ashes */
        MsgIncapacitated();                     /* CmdCast_Down */
        return;
    }
    HitTile = 0x3C;                             /* 3Ch outside a fight (COMBAT sets 3Dh) ? */
    CastSpell(bx);
}

/* asm: CmdEnter @1D69 */
void CmdEnter(const u8 *si)
{
    u8 al, dl;
    u8 *cell;
    u16 ax;
    unsigned idx;
    const u8 *dx;

    PrintMsg(si);
    if (Location != 0) {
        if (Location != 0xFF) {                 /* neither Sosaria nor Ambrosia */
            MsgWhat();                          /* CmdEnter_What */
            return;
        }
        al = MapCellAddr(PlayerXY, PlayerY, &cell);
        if (al != 0xF8) {                       /* shrine (shape 62) */
            MsgWhat();
            return;
        }
        EnterShrine();                          /* Ambrosia: a shrine */
        return;
    }
    /* CmdEnter_Sosaria: the party's place must be one of the 19 entrances of MapPosTbl */
    ax = PlayerXY | (PlayerY << 8);             /* mov ax, word ptr PlayerXY */
    for (idx = 0; idx < 0x13; idx++)            /* repne scasw over 19 (x, y) words */
        if (Rd(&MapPosTbl[idx * 2]) == ax) break;
    if (idx == 0x13) {
        MsgWhat();                              /* not an entrance */
        return;
    }
    /* BX = the entrance's index * 2 (the offset into MapFileNames) */
    PartyXY[0] = PlayerXY;                      /* the place to come back to: mov word ptr PartyXY, ax */
    PartyXY[1] = PlayerY;
    if (TileHere == 5) {                        /* dungeon (shape 5) */
        PrintMsg(MsgDungeon);                   /* "Dungeon!" */
        dl = 1;                                 /* the new Location */
        DungeonLevel = 0;
        PlayerXY = 0x01;                        /* mov word ptr PlayerXY, 101h: x 1, y 1 */
        PlayerY = 0x01;
        Facing = 1;
    } else if (TileHere == 6) {                 /* Towne (shape 6) */
        PrintMsg(MsgTowne);                     /* "Towne!" */
        dl = 2;
        PlayerXY = 0x01;                        /* mov word ptr PlayerXY, 2001h: x 1, y 32: the west edge */
        PlayerY = 0x20;
        MapWraps = 0;                           /* no wrapping in a town */
    } else if (TileHere == 7) {                 /* castle (shape 7) */
        PrintMsg(MsgCastle);                    /* "Castle!" */
        dl = 3;
        PlayerXY = 0x20;                        /* mov word ptr PlayerXY, 3E20h: x 32, y 62: the south edge */
        PlayerY = 0x3E;
        MapWraps = 0;
        CardsInserted[0] = 0;                   /* mov word ptr CardsInserted, 0: the cards inserted (ACTIONS 7670) */
        CardsInserted[1] = 0;
    } else {
        MsgWhat();                              /* CmdEnter_What */
        return;
    }
    /* CmdEnter_Load */
    PrintMsg(MsgPleaseWait);                    /* "Please wait..." */
    SaveSosaria();                              /* save Sosaria and the party (saves DX) */
    Location = dl;
    dx = MapFileNames[idx];                     /* mov si, bx / mov dx, word ptr MapFileNames[si]: the map's file name */
    if (Location != 1) {
        u8 m1 = Moon1Phase, m2 = Moon2Phase;    /* push word ptr Moon1Phase: the phases are part of the map file: keep them */
        LoadFile(MapBuf, 0x1228, dx);
        Moon1Phase = m1;                        /* pop word ptr Moon1Phase */
        Moon2Phase = m2;
        return;                                 /* CmdEnter_Done */
    }
    LoadFile(DungeonMap, 0x890, dx);            /* the dungeon: eight levels and messages */
    LoadFile(MapBuf, 0x800, FileDungeonDat);    /* DUNGEON.DAT, the code overlay */
    EnterDungeon();                             /* jmp EnterDungeon: the dungeon loop */
}

/* asm: CmdHand @1E55 */
void CmdHand(const u8 *si)
{
    u8 *bx = NULL;
    u8 *giver, *receiver;

    PrintMsg(si);
    if (AskPlayer(&bx) == 0) return;
    PrintMsg(MsgToPlayer);                      /* "  To Player: " */
    giver = bx;                                 /* mov si, bx: SI = the giver */
    if (AskPlayer(&bx) == 0) return;
    receiver = bx;                              /* mov di, bx */
    if (giver == receiver) {
        MsgWhat();                              /* CmdHand_Same: the same player */
        return;
    }
    HandEquip(giver, receiver);                 /* asks what and how much */
}

/* asm: CmdLook @1E7A */
void CmdLook(const u8 *si)
{
    u16 dx = 0, bx = 0;
    u8 al;
    u8 *cell;

    PrintMsg(si);
    if (AskDirection(&dx, &bx)) return;         /* ZF set: Esc */
    PrintMsg(MsgArrow);                         /* "->" */
    al = MapCellAddr(bx & 0xFF, bx >> 8, &cell);   /* BX = the cell (BL x, BH y) */
    al >>= 1;                                   /* the shape number */
    al >>= 1;
    al++;                                       /* PrintName prints name AL-1 */
    PrintName(al);
    ScrollMsg();
}

/* asm: CmdModify @1E9B */
void CmdModify(const u8 *si)
{
    u8 *bx = NULL;
    u8 dl, dh, al;
    u8 *di, *second;
    unsigned i;

    PrintMsg(si);
    if ((al = AskPlayer(&bx)) == 0) return;
    dl = al - 1;                                /* DL = the first slot (0-3), DI = its record */
    di = bx;
    PrintMsg(MsgPlayer);                        /* "Player: " */
    if ((al = AskPlayer(&bx)) == 0) return;
    dh = al - 1;                                /* DH = the second slot, SI = its record */
    second = bx;
    /* exchange the two slots' bytes in the PARTY.ULT header: 0Ah + slot (14C4 + slot: the roster numbers) */
    al = PartyTile[0x0A + dl];
    {
        u8 t = PartyTile[0x0A + dh];            /* xchg byte ptr [bx+si+0Ah], al */
        PartyTile[0x0A + dh] = al;
        al = t;
    }
    PartyTile[0x0A + dl] = al;
    for (i = 0; i < 0x40; i++) {                /* exchange the 64-byte records */
        al = di[i];                             /* mov al, [di] / xchg [si], al / stosb */
        u8 t = second[i];
        second[i] = al;
        di[i] = t;
    }
    DrawFrame();                                /* DrawFrame */
    DrawPlayerNums();                           /* the player numbers */
    if (Location != 1)                          /* no moons in a dungeon */
        AdvanceMoons();
    StatusLine();
    PrintMsg(MsgExchanged);                     /* "Exchanged!" */
}

/* asm: CmdPeer @1EFD */
void CmdPeer(const u8 *si)
{
    u8 *bx = NULL;
    u8 al;
    bool cf = false;

    PrintMsg(si);
    if (AskPlayer(&bx) == 0) return;
    al = SubDas(bx[0x25], 1, &cf);              /* gems (BCD): sub al, 1 / das; carry: none */
    if (cf) {
        MsgNoneLeft();                          /* CmdPeer_None */
        return;
    }
    bx[0x25] = al;
    if (Location == 1)
        ShowDungeonMap();
    else
        ShowGemMap();
}

/* asm: CmdQuit @1F25 */
void CmdQuit(const u8 *si)
{
    PrintMsg(si);
    if (Location != 0) {                        /* CmdQuit_NotSurface */
        PrintMsg(MsgOnlyOnSurface);             /* "Only on surface!" */
        Sound(0xFF);
        return;
    }
    PartyXY[0] = PlayerXY;                      /* keep the position in PARTY.ULT: mov word ptr PartyXY, ax */
    PartyXY[1] = PlayerY;
    PrintMoves();                               /* the moves so far */
    PrintMsg(MsgPleaseWait);                    /* "Please wait..." */
    SaveSosaria();                              /* save Sosaria and the party; the game goes on */
}

/* asm: CmdSteal @1F53 */
void CmdSteal(const u8 *si)
{
    u8 *bx = NULL;
    u16 dx = 0, cell_xy = 0;
    u8 *thief, *cell, *mon;
    u8 al, cl, ch, dl, dh;
    int n;

    PrintMsg(si);
    if (AskPlayer(&bx) == 0) return;
    thief = bx;                                 /* DI = the thief */
    if (!IsUp(thief)) {                         /* ZF clear: dead or ashes */
        MsgIncapacitated();                     /* CmdSteal_Down */
        return;
    }
    PrintMsg(MsgDirect);                        /* "Direct? " */
    if (AskDirection(&dx, &cell_xy)) return;    /* ZF set: Esc */
    cl = cell_xy & 0xFF;                        /* CX = the cell, DX = the step (AskDirection) */
    ch = cell_xy >> 8;
    dl = dx & 0xFF;
    dh = dx >> 8;
    if (DexRoll(thief)) {                       /* ZF set: the roll succeeded */
        al = MapCellAddr(cl, ch, &cell);        /* CmdSteal_Counter */
        if (al >= 0x94 && al <= 0xE4) {         /* counter: shapes 37 (wall) - 57 (letters) */
            cl += dl;                           /* two steps on: behind the counter */
            cl += dl;
            ch += dh;
            ch += dh;
            al = MapCellAddr(cl, ch, &cell);
            if (al == 0x24) {                   /* chest (shape 9) */
                *cell = 0x20;                   /* floor */
                ChestLoot(thief);               /* the gold in the chest */
                return;
            }
        }
    }
    /* CmdSteal_Fail */
    dl = Random(0xFF) & 3;                      /* one time in four: the guards */
    if (dl == 0) {                              /* CmdSteal_Alarm */
        mon = MonTile;                          /* lea bx, MonTile */
        for (n = 0; n < 0x20; n++, mon++)       /* the 32 creature slots */
            if (mon[0] == 0x48)                 /* guard (shape 18) */
                mon[Ofs80h] = 0xC0;             /* 0080h + MonTile + n = MonTalk + n: hostile */
        PrintMsg(MsgWatchOut);                  /* "Watch out!" */
        Sound(0xFA);                            /* sound 0FAh */
        return;
    }
    PrintMsg(MsgStealFailed);                   /* "Failed!" */
}

/* asm: CmdUnlock @1FD6 */
void CmdUnlock(const u8 *si)
{
    u8 *bx = NULL;
    u16 dx = 0, cell_xy = 0;
    u8 *door, *cell;
    u8 al;
    bool cf = false;

    PrintMsg(si);
    if (AskDirection(&dx, &cell_xy)) return;    /* ZF set: Esc */
    if ((dx >> 8) != 0) {                       /* test dh, 0FFh: east or west only */
        MsgNotHere();                           /* CmdUnlock_NotHere */
        return;
    }
    al = MapCellAddr(cell_xy & 0xFF, cell_xy >> 8, &cell);
    if (al != 0xB8) {                           /* locked door (shape 46) */
        MsgNotHere();
        return;
    }
    PrintMsg(MsgWhoseKey);                      /* "Whose key? " */
    door = cell;                                /* mov si, bx: SI = the door's cell */
    if (AskPlayer(&bx) == 0) return;
    al = SubDas(bx[0x26], 1, &cf);              /* keys (BCD) */
    if (cf) {
        MsgNoneLeft();                          /* CmdUnlock_None */
        return;
    }
    bx[0x26] = al;
    *door = (u8)(TileHere << 2);                /* the door becomes the tile the party stands on (TileHere) */
    BuildView();
}

/* asm: CmdVolume @2018 */
void CmdVolume(const u8 *si)
{
    PrintMsg(si);
    SoundOn ^= 0xFF;
    si = MsgOff;                                /* "Off!" */
    if (SoundOn != 0)
        si = MsgOn;                             /* "On!" */
    PrintMsg(si);
}

/* asm: CmdXit @2035 */
void CmdXit(const u8 *si)
{
    u8 al;
    u8 *cell;

    PrintMsg(si);
    if (PartyTile[0] == 0x3F) {                 /* on foot */
        MsgWhat();                              /* CmdXit_What */
        return;
    }
    al = MapCellAddr(PlayerXY, PlayerY, &cell);
    if (al > 4) {                               /* water (0) or grass (4) only */
        MsgNotHere();                           /* CmdXit_NotHere */
        return;
    }
    *cell = (u8)(PartyTile[0] << 2);            /* the craft's tile into the map */
    PartyTile[0] = 0x3F;                        /* on foot */
    PrintMsg(MsgCraft);                         /* "Craft" */
}

/* asm: CmdZtats @2068 */
void CmdZtats(const u8 *si)
{
    u8 *bx = NULL;
    u8 al;

    PrintMsg(si);
    if ((al = AskPlayer(&bx)) == 0) return;
    ShowZtats(al + 0x30, bx);                   /* DH = the player's digit '1'-'4', DI = the record */
}
