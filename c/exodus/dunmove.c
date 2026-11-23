/* dunmove.c: src/exodus/DUNMOVE.ASM, the dungeon: traps, darkness, turning, advancing (8190-84DB).
 *
 * The Get Chest command (surface and dungeon) with its four traps, the hurt-the-whole-party
 * routine shared by traps and cannon fire, and the dungeon's own main loop: EnterDungeon starts
 * it, DungeonLoop reads a key (a Pass after 5 seconds) and dispatches through DungeonKeys /
 * DungeonCmds (ACTIONS), and every command ends in DungeonTurnEnd: moves, food, the torch burns
 * down, the view is redrawn, then the cell under the party may start a fight or an event
 * (DUNEVENT, through DungeonEventCmds). The movement commands are here too.
 *
 * PlayerXY is the party's x (the low byte) and y (PlayerY) as one word (`mov bx, word ptr
 * PlayerXY`): BL = x, BH = y. Dungeon cells: 00 floor, 01-08 events, 10h ladder up, 20h ladder
 * down, 40h chest, 80h wall, A0h/C0h door kinds.
 *
 * `jmp MainLoop` is the end of the turn. In the C a command returns, except where the routine
 * only runs in the dungeon: there MainLoop is DungeonTurnEnd (Location = 1), so a shared exit
 * (MsgInvalidMove, MsgWhat) is followed by a call of DungeonTurnEnd, as the assembly's jump
 * chain goes. CmdGetChest also runs on the surface and just returns.
 */
#include "../u3.h"
#include "../lib/lib.h"
#include "exodus_data.h"
#include "dunmove.h"
#include "dunevent.h"
#include "combat.h"
#include "party.h"
#include "equip.h"
#include "items.h"
#include "shrine.h"

/* from VIEW, not yet read: */
void PrintMsg(const u8 *si);                    /* SI = the string (saves all) */
void ClearView(void);
u8 DungeonCell(u8 bl, u8 bh, u8 **bx);          /* x = BL, y = BH; returns AL = the cell's byte, *bx = its address */
u8 MapCellAddr(u8 bl, u8 bh, u8 **bx);          /* x = BL, y = BH; returns AL = the byte, *bx = its address in MapBuf */

/* asm: CmdGetChest @8190 */
void CmdGetChest(const u8 *si)
{
    PrintMsg(si);
    u8 *bx;
    u8 al = AskPlayer(&bx);                     /* 0 = Esc; else 1-4, BX = record */
    if (al == 0) return;                        /* GetChest_Done: jmp MainLoop */
    al--;
    u8 bp = al;                                 /* BP = player number 0-3 (AH is whatever AskPlayer kept; only AL is read) */
    u8 *di = bx;                                /* DI = the player's record */
    if (!IsUp(bx)) { MsgIncapacitated(); return; }
    u8 x = PlayerXY & 0xFF, y = PlayerY;        /* BX = PlayerXY: BL = x, BH = y */
    u8 *cell;
    if (Location == 1) {                        /* in a dungeon */
        al = DungeonCell(x, y, &cell);
        if (al != 0x40) { MsgNotHere(); return; }   /* 40h: chest in a dungeon */
        *cell = 0;                              /* becomes floor */
    } else {
        al = MapCellAddr(x, y, &cell);
        if (al < 0x24 || al > 0x27) { MsgNotHere(); return; }   /* chest tiles 24h-27h (shape 9 times 4) */
        al &= 3;                                /* low bits: the tile it stood on */
        al = (u8)(al << 2);                     /* 1-3: grass 04h, brush 08h, forest 0Ch */
        if (al == 0) al = 0x20;                 /* 0: floor (shape 8) */
        *cell = al;
    }
    /* GetChest_Open */
    u8 dl = Random(0xFF);                       /* DH = 0FFh */
    if (!(dl & 0x80)) {                         /* shl dl, 1 / jb: half the time a trap */
        ChestLoot(di);                          /* gold etc. for the player at DI */
        return;                                 /* GetChest_Done: jmp MainLoop */
    }
    /* GetChest_Trap. Which trap: AL and DL two random bytes. (DL & AL & 3) = 0 gives acid (9 times
     * in 16); else AL = 1 poison, AL = 2 gas, others bomb. AL is the whole random byte, not DL, so
     * poison and gas come about once in 256 (probably meant DL). BUG, as in the original. */
    dl = Random(0xFF);
    al = dl;
    dl = Random(0xFF);
    dl &= al;
    dl &= 3;
    if (dl == 0) goto Acid;
    if (al == 1) goto Poison;
    if (al == 2) goto Gas;
    goto Bomb;
Gas:
    PrintMsg(MsgGasTrap);                       /* "Gas trap!" */
    al = TryEvadeTrap(al, di);
    if (al != 0) {                              /* GetChest_GasAll: gas poisons every player who is up */
        bx = Players;
        u8 cl = 0;
        do {
            if (IsUp(bx)) {
                FlashPlayer(cl);                /* flash the player's status line */
                Sound(0xF7);                    /* hit sound */
                FlashPlayer(cl);
                bx[0x11] = 0x50;                /* status 'P' poisoned */
            }
            bx += 0x40;                         /* next record */
            cl++;
        } while (cl < PartySize);
    }
    goto Gold;
Acid:
    PrintMsg(MsgAcidTrap);                      /* "Acid trap!" */
    al = TryEvadeTrap(al, di);                  /* AL = 0 from the random byte also counts as evaded */
    if (al == 0) goto Gold;
    FlashPlayer(bp);
    Sound(0xF7);
    FlashPlayer(bp);
    dl = Random(0xFF);                          /* (mov dl, 0FFh first, but DL is only the result; DH is still 0FFh: Random up to 0FEh) */
    dl &= 0x37;                                 /* damage 00-37 BCD */
    HurtPlayer(dl, di);                         /* subtract AL (BCD) from the hit points */
    StatusLine();
    goto Gold;
Poison:
    PrintMsg(MsgPoisonTrap);                    /* "Poison trap!" */
    al = TryEvadeTrap(al, di);
    if (al == 0) goto Gold;
    FlashPlayer(bp);
    Sound(0xF7);
    FlashPlayer(bp);
    di[0x11] = 0x50;                            /* status 'P' poisoned */
    goto Gold;
Bomb:
    PrintMsg(MsgBombTrap);                      /* "Bomb trap!" */
    al = TryEvadeTrap(al, di);
    if (al != 0)
        DamageParty();                          /* everyone is hurt */
Gold:
    ChestLoot(di);                              /* the chest's gold anyway */
    StatusLine();
    /* jmp MainLoop */
}

/* asm: TryEvadeTrap @82AA */
u8 TryEvadeTrap(u8 al, u8 *di)
{
    if (DexRoll(di)) {                          /* ZF set: evaded */
        PrintMsg(MsgTrapEvaded);                /* "Trap evaded!" */
        Sound(0xFA);                            /* rise sound */
        al = 0;
    }
    return al;                                  /* else AL as the caller left it */
}

/* asm: DamageParty @82C6 */
void DamageParty(void)
{
    u8 *bx = Players;
    u8 cl = 0;
    do {
        if (IsUp(bx)) {
            FlashPlayer(cl);                    /* flash the status line */
            Sound(0xF7);                        /* hit sound */
            FlashPlayer(cl);
            u8 dl = Random(0xFF);
            dl &= 0x77;                         /* damage 00-77 BCD */
            HurtPlayer(dl, bx);                 /* subtract from the hit points */
            u8 al = DungeonLevel;
            al++;
            al = (u8)(al << 3);
            HurtPlayer(al, bx);                 /* then (level + 1) * 8 more */
        }
        bx += 0x40;
        cl++;
    } while (cl < PartySize);
    StatusLine();
}

/* asm: EnterDungeon @8314 */
void EnterDungeon(void)
{
    LightOn = 0;
    DungeonLevel = 0;
    PrintLevelHead();                           /* the "LVL" header (SHRINE) */
    ClearView();
    DungeonLoop();                              /* never comes back */
}

/* asm: DungeonLoop @8327 */
void DungeonLoop(void)
{
    CheckAllOut();                              /* all dead? (does not come back then) */
    if (LightOn == 0)
        PrintMsg(MsgItsDark);                   /* "It's dark!" */
    PutChar(0x10);                              /* the prompt character */
    u8 dh = DosGetSeconds();
    u8 bl = dh + 5;                             /* 5 seconds from now */
    if (bl >= 0x3C) bl -= 0x3C;
    u16 ax;
    for (;;) {
        if (KeyReady()) {                       /* key waiting? */
            ax = ReadKey();
            if ((ax & 0xFF) >= 0x61 && (ax & 0xFF) <= 0x7A)   /* 'a'-'z' -> 'A'-'Z' (AL only) */
                ax -= 0x20;
            break;
        }
        dh = DosGetSeconds();
        if (bl == dh) {                         /* timeout: Space = Pass */
            ax = 0x3920;
            break;
        }
    }
    /* repne scasw over DungeonKeys: 33 key words (character, scan code) */
    for (u16 entry = 0; entry < 0x21; entry++) {
        if ((DungeonKeys[2 * entry] | (DungeonKeys[2 * entry + 1] << 8)) == ax) {
            const u8 *si = DungeonPrompts[entry];   /* SI = the command's prompt, BX = entry * 2 */
            ((void (*)(const u8 *))DungeonCmds[entry])(si);     /* jmp word ptr DungeonCmds[bx] */
            return;
        }
    }
    MsgWhat();                                  /* jmp MsgWhat: not a key of the table */
    DungeonTurnEnd();                           /* its jmp MainLoop with Location = 1 */
}

/* asm: DungeonTurnEnd @838D */
void DungeonTurnEnd(void)
{
    AddMoves(PartySize);
    PartyUpkeep();                              /* food (PARTY) */
    if (LightOn != 0)
        LightOn--;                              /* a torch turn */
    PrintLevelHead();
    DrawDungeon();                              /* the 3D view */
    u8 *bx;
    u8 al = DungeonCell(PlayerXY & 0xFF, PlayerY, &bx);     /* AL = cell under the party, BX = its address */
    if (al == 0) {
        u8 dh = 0x82;                           /* Random(82h + level) ... */
        dh += DungeonLevel;
        u8 dl = Random(dh);
        if (!(dl & 0x80)) {                     /* shl dl, 1 / jae: ... >= 80h: a monster */
            DungeonLoop();
            return;
        }
        dh = DungeonLevel;
        dh += 2;
        dl = Random(dh);
        if (dl >= 7) dl = 6;                    /* at most 6 */
        dl += 0x18;                             /* Orc (18h) ... Balron (1Eh) */
        FoeTile = dl;
        *bx = 0x40;                             /* a chest where it stood */
        StartCombat();
        return;
    }
    if (al > 8 || al == 7) {                    /* only cells 1-8 are events; 7: none */
        DungeonLoop();
        return;
    }
    al--;
    FlushKeys();
    /* 1 time, 2 fountain, 3 wind, 4 trap, 5 rod, 6 gremlins, 8 writing */
    ((void (*)(u8 *))DungeonEventCmds[al])(bx);     /* jmp word ptr DungeonEventCmds[si], BX = the cell */
}

/* asm: CmdKlimb @83F7 */
void CmdKlimb(const u8 *si)
{
    PrintMsg(si);
    u8 *bx;
    u8 al = DungeonCell(PlayerXY & 0xFF, PlayerY, &bx);
    al &= 0x10;                                 /* ladder up? */
    if (al == 0) {                              /* Klimb_Invalid */
        MsgInvalidMove();
        DungeonTurnEnd();                       /* its jmp MainLoop with Location = 1 */
        return;
    }
    if (DungeonLevel == 0) {                    /* Klimb_Exit: from level 1 out of the dungeon */
        ExitToSosaria();                        /* back to Sosaria */
        return;                                 /* jmp MainLoop (Location is 0 now: the surface turn) */
    }
    DungeonLevel--;
    DungeonTurnEnd();
}

/* asm: CmdDescend @841C */
void CmdDescend(const u8 *si)
{
    PrintMsg(si);
    u8 *bx;
    u8 al = DungeonCell(PlayerXY & 0xFF, PlayerY, &bx);
    if ((al & 0x80) || (al & 0x20) == 0) {      /* 80h and up: no; ladder down (bit 20h)? */
        MsgInvalidMove();
        DungeonTurnEnd();                       /* its jmp MainLoop with Location = 1 */
        return;
    }
    DungeonLevel++;
    DungeonTurnEnd();
}

/* asm: CmdTurnRight @8438 */
void CmdTurnRight(const u8 *si)
{
    PrintMsg(si);
    u8 *bx;
    u8 al = DungeonCell(PlayerXY & 0xFF, PlayerY, &bx);
    if (al >= 0xA0) {                           /* door cell: no turning */
        MsgInvalidMove();
        DungeonTurnEnd();                       /* its jmp MainLoop with Location = 1 */
        return;
    }
    Facing++;                                   /* clockwise */
    Facing &= 3;
    DungeonTurnEnd();
}

/* asm: CmdTurnLeft @8455 */
void CmdTurnLeft(const u8 *si)
{
    PrintMsg(si);
    u8 *bx;
    u8 al = DungeonCell(PlayerXY & 0xFF, PlayerY, &bx);
    if (al >= 0xA0) {                           /* door cell: no turning */
        MsgInvalidMove();
        DungeonTurnEnd();                       /* its jmp MainLoop with Location = 1 */
        return;
    }
    Facing--;                                   /* anticlockwise */
    Facing &= 3;
    DungeonTurnEnd();
}

/* asm: CmdNotDungeon @8472 */
void CmdNotDungeon(const u8 *si)
{
    PrintMsg(si);
    Sound(0xFF);                                /* buzz sound */
    DungeonTurnEnd();
}

/* asm: CmdAdvance @847D */
void CmdAdvance(const u8 *si)
{
    PrintMsg(si);
    u8 bl = Facing;
    u8 dl = PlayerXY & 0xFF, dh = PlayerY;      /* DX = PlayerXY */
    dl += FacingDxTbl[bl];                      /* x step for this facing */
    dh += FacingDyTbl[bl];                      /* y step */
    u16 dx = (u16)(dl | (dh << 8)) & 0x0F0F;    /* the level wraps round */
    u8 *bx;
    u8 al = DungeonCell(dx & 0xFF, dx >> 8, &bx);
    if (al == 0x80) {                           /* wall? only exactly 80h: the door kinds can be entered */
        MsgInvalidMove();
        DungeonTurnEnd();                       /* its jmp MainLoop with Location = 1 */
        return;
    }
    PlayerXY = dx;                              /* mov word ptr PlayerXY, dx */
    DungeonTurnEnd();
}

/* asm: CmdRetreat @84A9 */
void CmdRetreat(const u8 *si)
{
    PrintMsg(si);
    u8 bl = Facing;
    bl += 2;                                    /* the opposite facing */
    bl &= 3;
    u8 dl = PlayerXY & 0xFF, dh = PlayerY;
    dl += FacingDxTbl[bl];
    dh += FacingDyTbl[bl];
    u16 dx = (u16)(dl | (dh << 8)) & 0x0F0F;
    u8 *bx;
    u8 al = DungeonCell(dx & 0xFF, dx >> 8, &bx);
    if (al & 0x80) {                            /* rol al, 1 / jb: bit 7, wall or door */
        MsgInvalidMove();
        DungeonTurnEnd();                       /* its jmp MainLoop with Location = 1 */
        return;
    }
    PlayerXY = dx;
    DungeonTurnEnd();
}
