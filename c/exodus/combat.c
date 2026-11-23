/* combat.c: src/exodus/COMBAT.ASM, fights (888B-941E).
 *
 * The whole fight. Entry points: CmdAttack (the surface A command), FightCreature (also when a
 * creature attacks the party: WORLD) and StartCombat (a dungeon's wandering monster, with FoeTile
 * set). StartCombat picks a CNFLCT map by terrain and foe, loads it over StartUp, saves Location
 * (in SavedLocation) and sets Location = 80h, places the party and 1-8 foes, then loops:
 * CombatRound / PlayerTurn (a key through CombatKeys / CombatCmds in CMDTAB, a Pass after 5
 * seconds) / PlayerTurnEnd for each player, then FoesTurn (move, melee, a dragon's fire, magic),
 * until every foe is dead (Victory) or the party (PARTY: CheckAllOut ends the game). There is no
 * fleeing: a move off the 11 x 11 map is refused.
 *
 * The turn. MainLoop jumps to PlayerTurnEnd while Location = 80h, so a handler that ends in
 * MainLoop (Volume) or in a shared exit that does (MsgWhat, MsgNoneLeft, MsgInvalidMove) spends
 * the turn: in the C those handlers call PlayerTurnEnd after the exit (c/README.md says a command
 * just returns; here the fight's own turn end is explicit). The loop PlayerTurn -> command ->
 * PlayerTurnEnd -> PlayerTurn ... is a chain of jumps in the assembly and a chain of calls in the
 * C: nothing comes back until the fight is over (Victory returns, and the calls unwind).
 *
 * The combat arrays are the CNFLCT file's tail in StartUp's memory (docs/FORMATS.md 5 and 9):
 *   StartUp+80h foe x [8], +88h foe y, +90h the tile under the foe, +98h foe hit points (0 dead),
 *   StartUp+A0h player x [4] (0FFh dead), +A4h player y, +A8h the tile under him, +ACh his tile.
 * The assembly writes them `CmbMonHP[si]` (EXDATA's offsets) with SI = StartUp + slot, or
 * `StartUp+0A0h[bx]`; combat.h explains the C's form (`si[CmbMonHP]`, `StartUp[0xA0 + bx]`).
 * FoeTile is the foes' shape number, HitTile the flash tile, CombatPlayer whose turn it is.
 * Foe = a combat monster here; the map's creatures are the Mon arrays.
 */
#include "../u3.h"
#include "../lib/lib.h"
#include "exodus_data.h"
#include "combat.h"
#include "party.h"
#include "view.h"
#include "loop.h"
#include "equip.h"
#include "items.h"
#include "magic.h"
#include "hand.h"
#include "bcd.h"

/* asm: CmdAttack @888B */
void CmdAttack(const u8 *si)
{
    PrintMsg(si);                               /* SI as the main loop left it: the command's name */
    HitTile = 0x3D;                             /* HitTile = fire */
    u16 dx, bx;
    if (AskDirection(&dx, &bx))                 /* AskDirection: BX = target cell; ZF: Esc */
        return;                                 /* Attack_Cancel: jmp MainLoop */
    dx = bx;
    bx = FindMonster(dx & 0xFF, dx >> 8);       /* BX = creature slot or 0FFFFh */
    if (bx == 0xFFFF) {                         /* Attack_NotHere */
        MsgNotHere();
        return;
    }
    FightCreature(bx);
}

/* asm: FightCreature @88AA */
void FightCreature(u16 bx)
{
    BuildView();
    u16 di = bx;                                /* DI = creature slot */
    u8 *cell;
    MapCellAddr(MonX[di], MonY[di], &cell);     /* BX = the creature's map cell (AL is overwritten) */
    u8 al = MonUnder[di];                       /* the map byte under the creature */
    if (al != 0) {                              /* 0 (water): leave water */
        al >>= 2;                               /* shape 1-3 (grass, brush, forest), floor 0 */
        al &= 3;
        al |= 0x24;                             /* a chest (24h-27h) on that ground */
    }
    *cell = al;                                 /* the cell left behind */
    al = MonTile[di];                           /* creature tile ... */
    al >>= 2;
    FoeTile = al;                               /* ... / 4 = FoeTile */
    MonTile[di] = 0;                            /* the creature is gone from the map */
    if (al == 0x0F && PartyTile[0] != 0x0B)     /* Pirate, party not on a frigate? */
        *cell = 0x2C;                           /* the pirates' frigate (shape 11) stays */
    StartCombat();                              /* falls through into StartCombat */
}

/* asm: StartCombat @88EA */
void StartCombat(void)
{
    KillSpellUsed = 0;                          /* the orc/skeleton spells work again */
    u8 *bx = MonTile;
    u16 cx = 0x20;
    do {
        if (*bx == 0x4C || *bx == 0x48)         /* Lord British? Guard? */
            bx[Ofs80h] = 0xC0;                  /* MonTile+80h = MonTalk: 0C0h, no more talking */
        bx++;
    } while (--cx);
    PrintMsg(MsgConflict);                      /* "---Conflict!!---" "->" */
    PrintFoeName(0xFF);                         /* plural */
    ScrollMsg();
    ScrollMsg();

    const u8 *dx;                               /* the map's file name */
    if (Location == 1) {                        /* in a dungeon? */
        dx = FileConflictC;                     /* CNFLCT_C */
        goto Load;
    }
    if (FoeTile == 0x0F) {                      /* Pirate? */
        FoeTile = 0x17;                         /* fought as Thieves */
        dx = FileConflictS;                     /* CNFLCT_S */
        if (PartyTile[0] != 0x0B)               /* party on a frigate? */
            dx = FileConflictA;                 /* CNFLCT_A */
        goto Load;
    }
    if (PartyTile[0] == 0x0B) {                 /* party on a frigate? */
        dx = FileConflictQ;                     /* CNFLCT_Q: sea foe */
        if (FoeTile < 0x10) goto Load;
        dx = FileConflictR;                     /* CNFLCT_R: land foe */
        goto Load;
    }
    if (FoeTile < 0x10) {                       /* sea foe (0Bh-0Fh) ... */
        dx = FileConflictM;                     /* CNFLCT_M */
        if (FoeTile >= 0x0B) goto Load;
    }
    {                                           /* StartCombat_Terrain */
        u8 al = TileHere;                       /* the tile under the party */
        if (al == 9) {                          /* a chest? */
            u8 *p;
            al = MapCellAddr(PlayerXY, PlayerY, &p);
            al &= 3;                            /* low bits 0: on floor */
            if (al == 0) al = 8;                /* treat as floor (else the ground it stands on, 1-3) */
        }
        dx = FileConflict;                      /* CNFLCT_G */
        if (al == 1) goto Load;                 /* grass */
        dx = FileConflictB;                     /* CNFLCT_B */
        if (al == 2) goto Load;                 /* brush */
        dx = FileConflictF;                     /* CNFLCT_F */
        if (al == 3) goto Load;                 /* forest */
        dx = FileConflictC;                     /* CNFLCT_C */
        if (al == 8) goto Load;                 /* floor */
        if (al == 0x20) goto Load;              /* force field */
        if (al == 0x21) goto Load;              /* lava */
        dx = FileConflictC;
        if (FoeTile == 8) goto Load;            /* FoeTile 8 (floor?) */
        dx = FileConflict;                      /* CNFLCT_G */
    }
Load:
    LoadFile(StartUp, 0xB0, dx);                /* the combat map over StartUp */
    SavedLocation = Location;                   /* keep the Location for after the fight */
    Location = 0x80;                            /* 80h: in a fight */

    /* Place the party, last player first: DI = StartUp + slot, SI = his record. A player who is up
     * stands where the file says (+A0h/+A4h) with his class's tile (+ACh); +A8h keeps what he
     * covers. The others get position 0FFh (off the map). */
    {
        u8 al = PartySize;
        u8 *di = StartUp + (al - 1);
        u16 cx2 = al;
        u8 *si = Players + 0x40 * (al - 1);
        do {
            if (si[0x11] == 0x47 || si[0x11] == 0x50) {     /* status 'G' or 'P' */
                u8 bl = di[CmbPlrX];            /* player x, y from the file */
                u8 bh = di[CmbPlrY];
                al = si[0x17];                  /* class letter */
                al = ClassTile(al);             /* AL = his tile */
                di[CmbPlrTile] = al;            /* player tile */
                u8 *p;
                al = ViewTileAt(bl, bh, &p);    /* BX = view cell, AL = what is there */
                di[CmbPlrUnder] = al;           /* tile under him */
                al = di[CmbPlrTile];
                *p = al;                        /* draw him */
            } else {
                di[CmbPlrX] = 0xFF;             /* player x = 0FFh: not in the fight */
                di[CmbPlrY] = 0xFF;
            }
            si -= 0x40;
            di--;
        } while (--cx2);
    }
    for (int i = 0; i < 8; i++)                 /* lea di, StartUp+98h / rep stosb */
        StartUp[0x98 + i] = 0;                  /* all foes dead to start with (CmbMonHP) */

    /* How many foes: 8 in the castle of Exodus; in a town or castle (Location 2 or more, not
     * Ambrosia) 1, or 8 Guards; else (Sosaria, dungeon, Ambrosia) 1-8 at random. */
    u16 cx3;
    if (InExodusCastle()) {                     /* ZF: Exodus's castle */
        cx3 = 8;
    } else if (SavedLocation < 2 || SavedLocation == 0xFF) {    /* StartCombat_RandCount */
        u8 dl = Random(8);                      /* 1-8 */
        dl++;
        cx3 = dl;
    } else if (FoeTile == 0x12) {               /* Guards come eight */
        cx3 = 8;
    } else {
        cx3 = 1;
    }
    do {                                        /* StartCombat_PlaceFoe */
        u8 *si;
        do {
            u8 dl = Random(8);                  /* a random free slot 0-7 */
            si = StartUp + dl;
        } while (si[CmbMonHP] != 0);            /* foe hit points: 0 = free */
        u8 bl = FoeTile & 0x0F;                 /* by FoeTile & 0Fh */
        u8 dh = FoeHitPoints[bl];
        u8 dl = Random(dh);                     /* Random(FoeHitPoints[...]) */
        dl |= 0x0F;                             /* at least 0Fh */
        si[CmbMonHP] = dl;                      /* foe hit points */
        bl = si[Ofs80h];                        /* foe x, y from the file */
        u8 bh = si[CmbMonY];
        u8 *p;
        u8 al = ViewTileAt(bl, bh, &p);         /* BX = view cell, AL = what is there */
        si[CmbMonUnder] = al;                   /* tile under the foe */
        *p = FoeTile;                           /* draw the foe */
    } while (--cx3);
    DrawView();
    SoundBX = 0x10F0;                           /* warble: the fanfare (BL = 0F0h, BH = 10h: its notes?) */
    Sound(0xFD);
    Sound(0xFD);
    SoundBX = 0x04F0;                           /* mov bh, 4 */
    Sound(0xFD);
    SoundBX = 0x10F0;                           /* mov bh, 10h */
    Sound(0xFD);
    FlushKeys();
    CombatRound();                              /* jmp CombatRound: never comes back until the fight is over */
}

/* asm: ClassTile @8AC4 */
u8 ClassTile(u8 al)
{
    /* repne scasb over the ten letters of CombatClassLetters */
    for (u16 bx = 0; bx < 0x0A; bx++)
        if (CombatClassLetters[bx] == al)
            return CombatClassTiles[bx];        /* the class's tile */
    return 0x3F;                                /* Ranger */
}

/* asm: PrintFoeName @8AE6 */
void PrintFoeName(u8 al)
{
    u8 ah = al;                                 /* AH = the plural flag */
    al = PlayerY;                               /* party y ... */
    bool odd = al & 1;                          /* shr al, 1: ... odd? */
    al >>= 1;
    if (odd) {
        al = FoeTile;
        if (al >= 0x17) {                       /* sub al, 17h / jb: 17h-1Eh only */
            al -= 0x17;
            u8 cf = PlayerXY & 1;               /* x's low bit into CF */
            al = (u8)((al << 1) | cf);          /* rcl al, 1: 2 * (kind - 17h) + (x & 1) */
            al += 0x79;                         /* name 120 + that (Brigand ...) */
            PrintName(al);                      /* prints name AL-1 */
            goto Plural;
        }
    }
    /* PrintFoeName_Plain */
    al = FoeTile;
    if (al == 0x17) {                           /* Thief? */
        if (ah == 0xFF) {                       /* PrintFoeName_Thief: the plural is a string of its own */
            PrintMsg(MsgThieves);               /* "Thieves" */
            goto Scroll;
        }
    }
    al += 1;                                    /* PrintFoeName_Shape: the shape's name */
    PrintName(al);
Plural:
    if (ah != 0xFF) return;
    if (al == 2) goto Scroll;                   /* AL = name + 1: Grass? */
    if (al == 9) goto Scroll;                   /* Floor? */
    if (al == 0x14) goto Scroll;                /* Lord British */
    if (al == 0x87) goto Scroll;                /* Orcus */
    {
        const u8 *si = MsgPluralE;              /* "es": the "e" runs on into the "s" (types.txt) */
        if (al != 0x83)                         /* Snatch */
            si = MsgPluralS;                    /* "s" */
        PrintMsg(si);
    }
    return;
Scroll:
    ScrollMsg();
    ScrollMsg();
}

/* asm: CombatRound @8B52 */
void CombatRound(void)
{
    PartyUpkeep();
    CombatPlayer = 0;                           /* CombatPlayer = 0 */
    PlayerTurn();                               /* falls through into PlayerTurn */
}

/* asm: PlayerTurn @8B5A */
void PlayerTurn(void)
{
    u8 al = CombatPlayer;
    al++;
    InvertPlayerNum(al);                        /* highlight his status line (AL = 1-4) */
    al--;
    u8 *bx = Players + 0x40 * al;               /* BX = his record */
    if (!IsUp(bx)) {                            /* not up: next player */
        PlayerTurnEnd();
        return;
    }
    PrintMsg(MsgPlayerBar);                     /* "----Player " */
    al = CombatPlayer;
    al++;
    PrintDigit(al);                             /* n */
    PrintMsg(MsgBarEnd);                        /* "----" */
    PlayerTurn_Prompt();                        /* falls through into PlayerTurn_Prompt */
}

/* asm: PlayerTurn_Prompt @8B8C */
void PlayerTurn_Prompt(void)
{
    PutChar(0x10);                              /* the prompt character */
    BlinkCount = 2;                             /* the library blinks his tile (K2928) */
    u8 dh = DosGetSeconds();                    /* DOS get time: DH = seconds */
    u8 bl = dh;
    bl += 5;                                    /* 5 seconds from now */
    if (bl >= 0x3C) bl -= 0x3C;
    u16 ax;
    for (;;) {                                  /* PlayerTurn_Wait */
        if (KeyReady()) {                       /* key waiting? */
            ax = ReadKey();                     /* PlayerTurn_Key */
            if ((ax & 0xFF) >= 0x61 && (ax & 0xFF) <= 0x7A)     /* 'a'-'z' -> 'A'-'Z' */
                ax -= 0x20;
            break;
        }
        dh = DosGetSeconds();
        if (bl == dh) {                         /* timeout: his tile back on the map */
            u16 b = CombatPlayer;
            u8 ah = StartUp[0xAC + b];          /* player tile */
            u8 al = StartUp[0xA4 + b];          /* player y */
            u8 x = StartUp[0xA0 + b];           /* player x */
            u8 *p;
            ViewTileAt(x, al, &p);
            *p = ah;
            DrawView();
            ax = 0x3920;                        /* Space = Pass */
            break;
        }
    }
    /* PlayerTurn_Find: repne scasw over CombatKeys, 33 key words (character, scan code) */
    for (u16 entry = 0; entry < 0x21; entry++) {
        if ((CombatKeys[2 * entry] | (CombatKeys[2 * entry + 1] << 8)) == ax) {
            /* SI is not set: the handlers load their own message */
            ((void (*)(void))CombatCmds[entry])();      /* jmp word ptr CombatCmds[bx] */
            return;
        }
    }
    MsgWhat();                                  /* jmp MsgWhat: not a key of the table */
    PlayerTurnEnd();                            /* its jmp MainLoop with Location = 80h */
}

/* asm: PlayerTurnEnd @8BFC */
void PlayerTurnEnd(void)
{
    AddMoves(1);                                /* one move */
    if (InExodusCastle())                       /* ZF: Exodus's castle */
        TimeStop = 0;                           /* no Negate Time there */
    u8 al = CombatPlayer;
    al++;
    InvertPlayerNum(al);                        /* his status line back (toggles) */
    int i;
    for (i = 0; i < 8; i++)                     /* lea di, StartUp+98h / repe scasb: foe hit points all 0? */
        if (StartUp[0x98 + i] != 0) break;
    if (i == 8) {                               /* PlayerTurnEnd_Won */
        Victory();
        return;
    }
    DrawView();
    StatusLine();
    CombatPlayer++;                             /* next player */
    al = CombatPlayer;
    if (al < PartySize)
        PlayerTurn();                           /* PlayerTurnEnd_Next */
    else
        FoesTurn();                             /* all have had their turn: the foes */
}

/* asm: CCmdMove @8C3C */
void CCmdMove(i8 dl, i8 dh, const u8 *si)
{
    PrintMsg(si);
    u8 *plr = StartUp + CombatPlayer;           /* SI = StartUp + player */
    u8 bh = plr[CmbPlrY];                       /* player y */
    u8 bl = plr[CmbPlrX];                       /* player x */
    u8 old_x = bl, old_y = bh;                  /* BP = where he stands */
    bl = (u8)(bl + dl);
    if (bl >= 0x0B) goto Invalid;               /* off the map? (0FFh too) */
    bh = (u8)(bh + dh);
    if (bh >= 0x0B) goto Invalid;
    {
        u8 cl = bl, ch = bh;                    /* CX = the new cell */
        u8 *newcell, *oldcell;
        u8 al = ViewTileAt(bl, bh, &newcell);   /* BX = its view address, AL = tile */
        u8 ah = al;
        al = CanWalkOn(al);                     /* walkable? */
        if (al == 0xFF) goto Invalid;
        u8 *di = newcell;                       /* DI = the new cell's address */
        ViewTileAt(old_x, old_y, &oldcell);
        al = plr[CmbPlrUnder];                  /* the tile under him ... */
        *oldcell = al;                          /* ... goes back on the old cell */
        plr[CmbPlrUnder] = ah;                  /* the new tile under him */
        al = plr[CmbPlrTile];                   /* player tile */
        *di = al;
        plr[CmbPlrY] = ch;                      /* player y */
        plr[CmbPlrX] = cl;                      /* player x */
        PlayerTurnEnd();
        return;
    }
Invalid:
    MsgInvalidMove();
    PlayerTurnEnd();                            /* its jmp MainLoop with Location = 80h */
}

/* asm: CanWalkOn @8C96 */
u8 CanWalkOn(u8 al)
{
    if (al != 1 && al != 2 && al != 3 && al != 8)   /* grass, brush, forest, floor */
        return 0xFF;
    Sound(0xF6);                                /* tick sound */
    for (u16 cx = 0x2000; cx; cx--)             /* delay (speed dependent) */
        ;
    Sound(0xF6);                                /* again (AL is still 0F6h) */
    return 0;
}

/* asm: CCmdNorth @8CBE */
void CCmdNorth(void)
{
    CCmdMove(0, -1, MsgMoveNorth);              /* "North": DL = 0, DH = 0FFh: y - 1 */
}

/* asm: CCmdSouth @8CC9 */
void CCmdSouth(void)
{
    CCmdMove(0, 1, MsgMoveSouth);               /* "South" */
}

/* asm: CCmdEast @8CD4 */
void CCmdEast(void)
{
    CCmdMove(1, 0, MsgMoveEast);                /* "East" */
}

/* asm: CCmdWest @8CDF */
void CCmdWest(void)
{
    CCmdMove(-1, 0, MsgMoveWest);               /* "West": DL = 0FFh: x - 1 */
}

/* asm: CCmdVolume @8CEA */
void CCmdVolume(void)
{
    CmdVolume(MsgVolume);                       /* "Volume ": the surface command, which jumps to MainLoop ... */
    PlayerTurnEnd();                            /* ... i.e. here to PlayerTurnEnd: the turn is spent */
}

/* asm: CCmdReady @8CF1 */
void CCmdReady(void)
{
    PrintMsg(MsgCombatReady);                   /* "Ready a weapon!" */
    ReadyWeapon(Players + 0x40 * CombatPlayer);
    PlayerTurnEnd();
}

/* asm: CCmdZtats @8D0B */
void CCmdZtats(void)
{
    PrintMsg(MsgCombatZtats);                   /* "Ztats" */
    u8 al = CombatPlayer;
    u8 dh = al;
    dh += 0x31;                                 /* DH = '1' + player */
    al++;
    InvertPlayerNum(al);                        /* highlight off (toggle) */
    al--;
    u8 *di = Players + 0x40 * al;
    ShowZtats(dh, di);                          /* Ztats of the record at DI */
    al = dh;
    al -= 0x30;
    InvertPlayerNum(al);                        /* highlight on again */
    PlayerTurnEnd();
}

/* asm: CCmdCast @8D38 */
void CCmdCast(void)
{
    PrintMsg(MsgCombatCast);                    /* "Cast Spell!" */
    HitTile = 0x3C;                             /* HitTile = magic (shape 60) */
    CastSpell(Players + 0x40 * CombatPlayer);
    PlayerTurnEnd();
}

/* asm: CCmdNegate @8D57 */
void CCmdNegate(void)
{
    PrintMsg(MsgCombatNegate);                  /* "Negate Time!" */
    u8 *bx = Players + 0x40 * CombatPlayer;
    u8 al = bx[0x27];                           /* powders */
    if (al == 0) {                              /* CCmdNegate_None */
        MsgNoneLeft();
        PlayerTurnEnd();                        /* its jmp MainLoop with Location = 80h */
        return;
    }
    bool cf = false;
    al = SubDas(al, 1, &cf);                    /* sub al, 1 / das */
    bx[0x27] = al;
    TimeStop = 0x0A;                            /* the foes stop for 10 rounds */
    PlayerTurnEnd();
}

/* asm: CCmdPass @8D83 */
void CCmdPass(void)
{
    PrintMsg(MsgCombatPass);                    /* "Pass" */
    PlayerTurnEnd();
}

/* asm: CCmdBad @8D8D */
void CCmdBad(void)
{
    PrintMsg(MsgNotUsableCmd);                  /* "Not usable cmd!" */
    Sound(0xFE);                                /* beep */
    FlushKeys();
    PlayerTurn_Prompt();                        /* the turn is not spent: ask again */
}

/* asm: CCmdAttack @8D9F */
void CCmdAttack(void)
{
    HitTile = 0x3D;                             /* HitTile = fire */
    u8 *si = Players + 0x40 * CombatPlayer;
    u8 al = si[0x30];                           /* weapon readied */
    al += 0x41;                                 /* name 40h + weapon: the weapon names */
    PrintName(al);
    u8 *di = si;
    PrintMsg(MsgAttackDir);                     /* " Attack" "Dir-" */
    si = di;
    u16 dx, bx16;
    if (AskDirection(&dx, &bx16)) {             /* DL, DH = the step; ZF: Esc */
        PlayerTurnEnd();                        /* CCmdAttack_Cancel: Esc spends the turn */
        return;
    }
    u8 bl = CombatPlayer;
    bl <<= 3;
    bl += 0xE0;                                 /* BL = 0E0h + 8 * player: the warble's pitch? */
    SoundBX = (u16)(6 << 8 | bl);               /* mov bh, 6 */
    Sound(0xFD);                                /* warble */
    al = si[0x30];                              /* weapon readied */
    u8 *plr = StartUp + CombatPlayer;           /* BX = StartUp + player */
    u8 step_x = dx & 0xFF, step_y = dx >> 8;    /* DX = the step */
    u16 foe;
    if (al == 3 || al == 5 || al == 9 || al == 0x0D)    /* Sling, Bow, +2 Bow, +4 Bow */
        goto Shoot;
    {
        u8 cell_y = plr[CmbPlrY];               /* player y */
        u8 cell_x = plr[CmbPlrX];               /* player x */
        cell_y += step_y;
        cell_x += step_x;                       /* CX = the next cell (xchg dx, cx swaps it with the step) */
        foe = FindFoeAt(cell_x, cell_y);        /* a foe there? */
        if (foe != 0xFFFF) goto Hit;
        if (al != 1) goto Miss;                 /* a Dagger? */
        al = si[0x31];                          /* thrown: daggers owned (record 31h) */
        bool cf = false;
        al = SubDas(al, 1, &cf);
        si[0x31] = al;
        if (al == 0)
            si[0x30] = 0;                       /* the last one: readied = Hand */
    }
Shoot:
    {
        i8 cl = (i8)step_x, ch = (i8)step_y;    /* CX = the step */
        u8 dh = plr[CmbPlrY];                   /* from the player's y ... */
        u8 dl = plr[CmbPlrX];                   /* ... and x */
        foe = ShootLine(dl, dh, cl, ch);        /* BX = foe hit or 0FFFFh */
        if (foe == 0xFFFF) goto Miss;
    }
Hit:
    AttackHit(foe);
    return;
Miss:
    AttackMissed();
}

/* asm: FindFoeAt @8E46 */
u16 FindFoeAt(u8 dl, u8 dh)
{
    u8 *si = StartUp + 7;                       /* SI = StartUp + slot, from the last */
    u16 cx = 8;
    do {
        if (si[CmbMonHP] != 0 &&                /* foe hit points: alive? */
            si[Ofs80h] == dl &&                 /* foe x */
            si[CmbMonY] == dh)                  /* foe y */
            return (u16)(si - StartUp);         /* BX = SI - StartUp: the slot */
        si--;
    } while (--cx);
    return 0xFFFF;
}

/* asm: ShootLine @8E7A */
u16 ShootLine(u8 dl, u8 dh, i8 cl, i8 ch)
{
    for (;;) {
        dh = (u8)(dh + ch);
        if (dh >= 0x0B) break;                  /* ShootLine_Edge */
        dl = (u8)(dl + cl);
        if (dl >= 0x0B) break;
        u8 *p;
        u8 al = ViewTileAt(dl, dh, &p);         /* BX = view address, AL = tile there */
        u8 ah = HitTile;
        *p = ah;                                /* the flash ... */
        DrawView();
        *p = al;                                /* ... and the tile back */
        u16 bx = FindFoeAt(dl, dh);
        if (bx != 0xFFFF)
            return bx;                          /* met a foe (walls and players do not stop it) */
    }
    DrawView();
    return 0xFFFF;
}

/* asm: AttackMissed @8EAF */
void AttackMissed(void)
{
    PrintMsg(MsgAttackMissed);                  /* "Missed!" */
    DrawView();
    PlayerTurnEnd();
}

/* asm: AttackHit @8EBC */
void AttackHit(u16 bx)
{
    u8 *di = Players + 0x40 * CombatPlayer;     /* DI = his record */
    if (InExodusCastle() && di[0x30] != 0x0F) { /* in the castle only the Exotic weapon hits */
        AttackMissed();                         /* AttackHit_Miss */
        return;
    }
    /* AttackHit_Roll */
    u8 dl = Random(0xFF);
    if (!(dl & 0x80)) {                         /* shl dl, 1 / jb: half the time a sure hit */
        dl = Random(0x63);                      /* 0-98 ... */
        u8 al = ToBcd(dl);                      /* ... as BCD (aam, shl ah, 4, or) */
        if (al >= di[0x13]) {                   /* < dexterity hits */
            AttackMissed();
            return;
        }
    }
    PrintFoeName(0);                            /* AttackHit_Hit: singular */
    PrintMsg(MsgAttackHit);                     /* "Hit!" */
    u8 *rec = di;                               /* BP = record */
    u8 *foe = StartUp + bx;                     /* DI = StartUp + slot */
    u8 bh = foe[CmbMonY];                       /* foe y */
    u8 bl = foe[Ofs80h];                        /* foe x */
    u8 *p;
    u8 ah = ViewTileAt(bl, bh, &p);
    u8 al = HitTile;
    *p = al;                                    /* flash on the foe */
    DrawView();
    Sound(0xF7);                                /* hit sound */
    *p = ah;
    /* strength (BCD) to binary: AH = tens digit, AL = ones digit, aad */
    u8 str = rec[0x12];
    al = (u8)((str >> 4) * 10 + (str & 0x0F));
    al |= 1;                                    /* Random(strength | 1) */
    dl = Random(al);
    al = str;                                   /* + the BCD byte / 2 (+1 if odd) */
    dl = (u8)(dl + (al >> 1) + (al & 1));       /* shr al, 1 / adc dl, al: the half is taken of the BCD byte
                                                   itself, so 25 gives 12h = 18: probably meant to use the
                                                   number. BUG, as in the original */
    al = rec[0x30];                             /* weapon readied * 3 */
    al = (u8)(al << 1);
    al += rec[0x30];
    al += dl;
    al += 4;                                    /* + 4 */
    DamageFoe(al, foe, rec);                    /* xchg di, bx: BX = StartUp + slot, DI = record */
    DrawView();
    PlayerTurnEnd();
}

/* asm: DamageFoe @8F5A */
void DamageFoe(u8 al, u8 *bx, u8 *di)
{
    if (FoeTile == 0x13) return;                /* Lord British: unhurt */
    u8 hp = bx[CmbMonHP];                       /* foe hit points */
    u8 ah = (u8)(hp - al);
    bx[CmbMonHP] = ah;
    if (ah != 0 && hp >= al) return;            /* je Killed / jae Done: alive when no borrow and not zero */
    PrintMsg(MsgKilledExp);                     /* "Killed! Exp.+" */
    bx[CmbMonHP] = 0;                           /* foe hit points = 0: dead */
    ah = bx[CmbMonUnder];                       /* tile under the foe */
    u8 dh = bx[CmbMonY];                        /* foe y */
    u8 dl = bx[Ofs80h];                         /* foe x */
    u8 *p;
    ViewTileAt(dl, dh, &p);
    *p = ah;                                    /* back on the map */
    u8 idx = FoeTile & 0x0F;
    al = FoeExp[idx];                           /* the experience it is worth */
    PrintBcdByte(al);
    AddExp(al, di);                             /* add AL (BCD) to the record at BX (= DI) */
    ScrollMsg();
    DrawView();
}

/* asm: Victory @8FB6 */
void Victory(void)
{
    TimeStop = 0;                               /* Negate Time ends */
    PrintMsg(MsgVictory);                       /* "****Victory!****" */
    FlushKeys();
    SoundBX = 0x1080;                           /* warble: the fanfare */
    Sound(0xFD);
    Sound(0xFD);
    Sound(0xFD);
    SoundBX = 0x4060;
    Sound(0xFD);
    u8 al = SavedLocation;                      /* Location before the fight */
    Location = al;
    if (al != 1)                                /* a dungeon? */
        BuildView();
    /* jmp MainLoop: the surface turn, or DungeonTurnEnd when Location is 1; the C returns */
}

/* asm: FoeCanEnter @8FEB */
u8 FoeCanEnter(u8 al, u8 dl, u8 dh)
{
    if (FoeTile < 0x10 && FoeTile >= 0x0B) {    /* sea foe (0Bh-0Fh)? */
        if (al != 0) return 0;                  /* water? */
    } else {                                    /* FoeCanEnter_Land */
        if (al != 1 && al != 2 && al != 3 && al != 8)   /* grass, brush, forest, floor */
            return 0;                           /* FoeCanEnter_No */
    }
    al = 0xFF;                                  /* FoeCanEnter_Free */
    if (FindFoeAt(dl, dh) != 0xFFFF)            /* a foe there? */
        return 0;
    return al;
}

/* asm: FoeChooseMove @9020 */
u8 FoeChooseMove(u8 di, u16 *bxp, u16 *cxp, u16 *dxp)
{
    /* Locals [bp] record pointer, [bp+2] step, [bp+4] cell. The two words are not initialised in
     * the assembly (stack garbage): a result CX, DX of "no step found" is whatever was on the
     * stack; the C starts them at 0. */
    u16 step = 0, cell = 0;
    u16 si = 0xFFFF;                            /* SI = the player chosen: none */
    const u8 *rec = Players;                    /* [bp] = record pointer */
    u16 bx = 0;                                 /* BX = player number */
    u8 ah = 0xFF;                               /* AH = best distance so far */
    u8 al, cl, ch, dl, dh;
    for (;;) {                                  /* FoeChoose_Loop */
        if (IsUp(rec)) {                        /* FoeChoose_Dist */
            dl = StartUp[0xA0 + bx];            /* player x ... */
            dl -= StartUp[0x80 + di];           /* ... - foe x */
            cl = dl;
            if ((i8)cl < 0) cl = -cl;
            dh = StartUp[0xA4 + bx];            /* player y ... */
            dh -= StartUp[0x88 + di];           /* ... - foe y */
            ch = dh;
            if ((i8)ch < 0) ch = -ch;
            al = cl | ch;                       /* adjacent: both 1 or less */
            if (al <= 1) {                      /* FoeChoose_Adjacent: AL = 0, BX = player */
                *bxp = bx;
                *cxp = step;
                *dxp = cell;
                return 0;
            }
            al = cl + ch;                       /* |dx| + |dy| */
            if (al <= ah) {                     /* no nearer than the best (ties go to the later one) */
                u8 save_al = al;                /* push ax / push bx */
                u8 t = dl;                      /* mov al, dl */
                cl = SignStep(&t);              /* AH = -1, 0, 1 (library) */
                t = dh;
                ch = SignStep(&t);
                dl = StartUp[0x80 + di];        /* diagonal step */
                dh = StartUp[0x88 + di];
                dl += cl;
                dh += ch;
                u8 *p;
                al = ViewTileAt(dl, dh, &p);
                al = FoeCanEnter(al, dl, dh);   /* allowed? */
                if (al != 0xFF) {
                    dl = StartUp[0x80 + di];    /* vertical: foe x, y + step */
                    al = ViewTileAt(dl, dh, &p);
                    al = FoeCanEnter(al, dl, dh);
                    if (al != 0xFF) {
                        dl += cl;               /* horizontal: x + step, foe y */
                        dh = StartUp[0x88 + di];
                        al = ViewTileAt(dl, dh, &p);
                        al = FoeCanEnter(al, dl, dh);
                    }
                }
                if (al == 0xFF) {               /* FoeChoose_Keep */
                    ah = save_al;               /* pop ax / mov ah, al: the new best */
                    si = bx;
                    step = (u16)((u8)cl | ((u8)ch << 8));       /* [bp+2] = CX, the step */
                    cell = (u16)(dl | (dh << 8));               /* [bp+4] = DX, the cell */
                }
            }
        }
        bx++;                                   /* FoeChoose_Next */
        rec += 0x40;
        if ((u8)bx >= PartySize) break;
    }
    *bxp = si;                                  /* FoeChoose_End: mov al, ah / mov bx, si */
    *cxp = step;
    *dxp = cell;
    return ah;
}

/* asm: FoeBreathe @90FD */
void FoeBreathe(u8 di, i8 cl, i8 ch)
{
    Sound(0xFB);                                /* fall sound */
    u8 dl = StartUp[0x80 + di];                 /* from the foe's x ... */
    u8 dh = StartUp[0x88 + di];                 /* ... and y */
    for (;;) {                                  /* FoeBreathe_Step */
        dl = (u8)(dl + cl);
        if (dl >= 0x0B) break;
        dh = (u8)(dh + ch);
        if (dh >= 0x0B) break;
        for (int bx = PartySize - 1; bx >= 0; bx--) {           /* FoeBreathe_Plr: dec bx / jns */
            if (dl == StartUp[0xA0 + bx] &&     /* player x? */
                dh == StartUp[0xA4 + bx]) {     /* player y? */
                FoeHurtPlayer((u8)bx);          /* BX = the player hit */
                goto Done;
            }
        }
        u8 *p;
        u8 al = ViewTileAt(dl, dh, &p);
        *p = 0x3D;                              /* the flame */
        DrawView();
        *p = al;
    }
Done:
    DrawView();
}

/* asm: FoesTurn @914F */
void FoesTurn(void)
{
    if (TimeStop != 0) {                        /* Negate Time: the foes miss the round */
        TimeStop--;                             /* one round less */
        CombatRound();                          /* FoesTurn_Done */
        return;
    }
    for (u8 di = 0; di < 8; di++) {             /* FoesTurn_Start / Loop / Next */
        if (StartUp[0x98 + di] == 0) continue;  /* foe hit points: alive? */
        u16 bx, cx, dx;
        u8 al = FoeChooseMove(di, &bx, &cx, &dx);   /* AL = distance, BX = player, CX step, DX cell */
        HitTile = 0x3D;                         /* HitTile = fire */
        if (al == 0) {                          /* adjacent? */
            FoeAttack((u8)bx);                  /* attack player BL */
            continue;
        }
        if (bx != 0xFFFF) {                     /* a target? */
            u8 dl = Random(0xFF);
            if (!(dl & 0x80) &&                 /* shl dl, 1 / jb: half the time */
                FoeTile == 0x1D) {              /* Dragon? */
                FoeBreathe(di, (i8)(cx & 0xFF), (i8)(cx >> 8));     /* breathe along CX */
                continue;
            }
        }
        /* FoesTurn_TryMagic: Random(0C0h) >= 80h: one time in 3 */
        {
            u8 dl = Random(0xC0);
            if (dl & 0x80) {                    /* shl dl, 1 / jae not taken */
                u8 ah = FoeTile;
                if (ah == 0x0D ||               /* Serpent */
                    ah == 0x0E ||               /* Man-O-War */
                    ah == 0x16 ||               /* Wizard */
                    ah == 0x1B ||               /* Daemon */
                    ah == 0x1D ||               /* Dragon */
                    ah == 0x1E) {               /* Balron */
                    /* FoesTurn_Magic */
                    dl = Random(0xFF);
                    dl &= 3;                    /* a player 0-3 (not PartySize) */
                    u8 bl = dl;
                    if (PlrStatus[0x40 * bl] == 0x47) {     /* status (Players + 11h): Good (a poisoned player is safe) */
                        FlashView();            /* flash the screen */
                        SoundBX = 0x4040;
                        Sound(0xFD);            /* warble */
                        FlashView();
                        HitTile = 0x3C;         /* HitTile = magic */
                        FoeAttack(bl);          /* attack player BL */
                        continue;
                    }
                    /* not Good: move instead (FoesTurn_Move) */
                } else if (ah == 0x13) {        /* Lord British: steps even with no step found */
                    FoeStep(di, (u8)(dx & 0xFF), (u8)(dx >> 8));
                    /* The cell DX is whatever FoeChooseMove left when it found no step: stack
                     * garbage in the original. BUG, as in the original */
                    continue;
                }
            }
        }
        if ((i8)al < 0) continue;               /* FoesTurn_Move: no step (AL = 0FFh): stays */
        FoeStep(di, (u8)(dx & 0xFF), (u8)(dx >> 8));    /* FoesTurn_Step */
    }
    CombatRound();                              /* FoesTurn_Done: the next round */
}

/* asm: FoeStep @9215 */
void FoeStep(u8 di, u8 dl, u8 dh)
{
    u8 *p;
    ViewTileAt(StartUp[0x80 + di], StartUp[0x88 + di], &p);     /* foe x, y */
    *p = StartUp[0x90 + di];                    /* tile under the foe back */
    StartUp[0x80 + di] = dl;                    /* foe x */
    StartUp[0x88 + di] = dh;                    /* foe y */
    u8 al = ViewTileAt(dl, dh, &p);
    StartUp[0x90 + di] = al;                    /* the new tile under it */
    *p = FoeTile;                               /* draw the foe */
    DrawView();
}

/* asm: FoeAttack @9244 */
void FoeAttack(u8 bl)
{
    u8 al = FoeTile;
    if (al == 0x0E ||                           /* Man-O-War */
        al == 0x1E ||                           /* Balron */
        al == 0x1C)                             /* Pincher */
        FoePoison(bl);                          /* may poison */
    else if (al == 0x17)                        /* Thief? */
        FoeSteal(bl);                           /* may steal */
    PrintMsg(MsgPlrN);                          /* "Plr " */
    al = bl;
    al += 0x31;                                 /* '1' + player */
    PutChar(al);
    Sound(0xF8);                                /* noise-rise sound */
    u8 *si = Players + 0x40 * bl;
    if (!InExodusCastle() || si[0x28] == 7) {   /* ZF: Exodus's castle: always a hit unless Exotic armour */
        u8 dh = si[0x28];                       /* FoeAttack_Armour: armour worn + 16 */
        dh += 0x10;
        u8 dl = Random(dh);
        if (dl >= 8) {                          /* 7 or less: hit */
            PrintMsg(MsgFoeMissed);             /* " Missed!" */
            return;
        }
    }
    PrintMsg(MsgFoeHit);                        /* FoeAttack_Hit: " Hit!" */
    FoeHurtPlayer(bl);
}

/* asm: FoeHurtPlayer @92AF */
void FoeHurtPlayer(u8 bl)
{
    u16 si = bl;                                /* SI = player number */
    u8 *bx = Players + 0x40 * bl;               /* BX = his record */
    u8 al = FoeHitPoints[FoeTile & 0x0F];
    al >>= 3;                                   /* the foe's hit point range / 8 */
    al += bx[0x1D];                             /* + max hit points, high byte (BCD) */
    al |= 1;
    u8 dl = Random(al);
    dl += 1;                                    /* 1 ... */
    al = ToBcd(dl);                             /* ... as BCD (aam, mov cl, 4, shl ah, cl, or) */
    HurtPlayer(al, bx);                         /* subtract from his hit points */
    al = SavedLocation;                         /* the Location before the fight */
    al &= 3;
    al = (u8)(al << 4);                         /* shl al, cl with CL = 4 still: 0, 10, 20, 30 (BCD) */
    HurtPlayer(al, bx);                         /* subtract that too */
    FlashPlayer((u8)si);                        /* flash his status line */
    u8 *p;
    ViewTileAt(StartUp[0xA0 + si], StartUp[0xA4 + si], &p);     /* player x, y */
    al = HitTile;
    *p = al;                                    /* flash on him */
    DrawView();
    Sound(0xF7);                                /* hit sound */
    al = StartUp[0xAC + si];                    /* his tile back */
    *p = al;
    DrawView();
    FlashPlayer((u8)si);
    if (bx[0x11] == 0x44) {                     /* status 'D' dead? */
        ViewTileAt(StartUp[0xA0 + si], StartUp[0xA4 + si], &p);
        al = StartUp[0xA8 + si];                /* the tile he stood on */
        *p = al;
        StartUp[0xA0 + si] = 0xFF;              /* player x, y = 0FFh: off the map */
        StartUp[0xA4 + si] = 0xFF;
        PrintMsg(MsgPlrKilled);                 /* "Killed!!!" */
        CheckAllOut();                          /* all dead? (does not come back then) */
    }
    StatusLine();
}

/* asm: FoePoison @9360 */
void FoePoison(u8 bl)
{
    u8 dl = Random(0xFF);
    dl &= 3;
    if (dl != 0) return;                        /* one time in 4 */
    if (PlrStatus[0x40 * bl] != 0x47) return;   /* status (Players + 11h) 'G'? */
    PlrStatus[0x40 * bl] = 0x50;                /* 'P' */
    PrintMsg(MsgPlrN);                          /* "Plr " */
    PutChar(bl + 0x31);
    PrintMsg(MsgPlrPoisoned);                   /* " Poisoned!" */
    Sound(0xFA);                                /* rise sound */
    StatusLine();
}

/* asm: FoeSteal @93A2 */
void FoeSteal(u8 bl)
{
    u8 *si = Players + 0x40 * bl;
    u8 di = bl;                                 /* DI = player number */
    u8 dl = Random(0xFF);
    u8 bx, al;
    bool cf;
    if (!(dl & 0x80)) {                         /* rol dl, 1 / jb FoeSteal_Armour not taken */
        dl = Random(0x10);                      /* a weapon kind 0-15 */
        if (dl == 0) return;                    /* Hand: nothing */
        bx = 0x30;                              /* weapon readied */
        if (dl == si[bx]) return;
        bx += dl;                               /* weapons owned (record 30h + kind) */
        if (si[bx] == 0) return;
        al = si[bx];
        cf = false;
        al = SubDas(al, 1, &cf);
        si[bx] = al;
    } else {                                    /* FoeSteal_Armour */
        dl = Random(8);                         /* an armour kind 0-7 */
        if (dl == 0) return;                    /* Skin: nothing */
        bx = 0x28;                              /* armour worn */
        if (dl == si[bx]) return;
        bx += dl;                               /* armours owned (record 28h + kind) */
        if (si[bx] == 0) return;
        al = si[bx];
        cf = false;
        al = SubDas(al, 1, &cf);
        si[bx] = al;
    }
    PrintMsg(MsgPlrN);                          /* FoeSteal_Msg: "Plr " */
    PutChar(di + 0x31);
    PrintMsg(MsgPlrPilfered);                   /* " Pilfered!" */
    Sound(0xFA);                                /* rise sound */
}
