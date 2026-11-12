#!/usr/bin/env python3
"""Shared analysis of the three Ultima III images: recursive disassembly and operand facts.

    import u3an; a = u3an.analyse('bootup')       # or 'ultima', 'exodus'

The images are COM-style: no header, loaded at CS:0100 with CS=DS=ES=SS, code and data in one
segment. ULTIMA.COM is started by DOS; it reads BOOTUP.BIN over itself, which reads
EXODUS.BIN over itself (the chain load: docs/PLAN.md section 2.1).

a.img (the file placed at offset 0100: a.img[0x100] is the file's first byte, a.end = 0x100 +
file size), a.insn {addr: capstone insn}, a.kind (per byte: 0 unknown, 1 instruction start,
2 instruction continuation, 3 inline/table data), a.targets (direct branch targets),
a.indirect [(addr, insn)] (jumps and calls through a register or memory).
operands(ins) gives Op records: memory operands with their effective segment, registers and
displacement size, immediates with their size.

The per-image facts (entry points, jump tables, calls followed by inline data) are in TARGETS.
"""
import collections, os, sys
import capstone
from capstone import x86

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GAMEDATA = os.path.join(ROOT, 'gamedata')

# entries: where execution starts (0100, interrupt handlers stored into the vector table,
# routines reached only through pointers). tables: jump tables {addr: words}. inline: calls
# whose target reads data after the return address {target: 'z' (ASCIIZ) or byte count}.
# data: ranges that are data even if something branches there. lib: links the shared library
# as its own module (tools/genlib.py). limit: rough module size for the split. modules: {start:
# NAME}, the program's modules (phase 5), each start moved down to where a module may begin.
# Phase 3 (relocatable), each checked by hand (docs/HANDOFF.md):
# ptrs: tables of data pointers {addr: words}, written dw Lxxxx (a 0000 word stays 0).
# immaddr: instructions whose 16-bit immediate is an address in the image (offset Lxxxx).
# dsforeign: ranges where DS is not the program's segment (DS = video memory there): their
# memory operands are offsets in that segment and stay numbers.
# bufrel: (base label, first, last) address ranges of a buffer that is loaded over code: its
# operands are written base+offset so that editing the code does not move them.
TARGETS = {
    'ultima': dict(file='ULTIMA.COM', sha1='2736836127771823f9ed1463f306400a36bde0e2',
                   entries=[0x100, 0x5CDD, 0x5CDF], tables={0x8E61: 12}, inline={}, data=[], lib=True,
                   modules={0x0100: 'UDATA',       # buffers, strings, tables
                            0x5CDD: 'INTRO'},      # the title animation, sound and the chain load of BOOTUP.BIN

                   ptrs={},
                   immaddr=[0x5CF1, 0x5CFC,        # int 23h/24h handlers
                            0x5F8E],               # picture buffer L0115 + row offset
                   dsforeign=[]),
    'bootup': dict(file='BOOTUP.BIN', sha1='d30df2917fbeae202f62dbf34c1ab41ba4988983',
                   entries=[0x100, 0x1207, 0x1209], tables={0x4B81: 12}, inline={}, data=[], lib=True,
                   modules={0x0100: 'BDATA',       # tables, strings and the roster/party buffers
                            0x1209: 'TITLE',       # start-up and the scrolling title picture
                            0x14C9: 'ORGANIZE',    # the party menu: look, form, disperse
                            0x194B: 'CREATE'},     # register, terminate, create a character, then load EXODUS.BIN
                   ptrs={0x0D61: 4,                # status: Good Poisoned Dead Ashes
                         0x0DFF: 24,               # weapons (16), armour (8, also used from 0E1F)
                         0x0E87: 4,                # menu: Return Organize Journey
                         0x0F62: 9,                # menu: Examine Create Form Disperse ...
                         0x1048: 3,                # sexes
                         0x1070: 5,                # races
                         0x10DB: 11},              # classes
                   immaddr=[0x121A, 0x1225,        # int 23h/24h handlers
                            0x1D69],               # roster L02CE + 40h*(n-1)
                   dsforeign=[]),
    'exodus': dict(file='EXODUS.BIN', sha1='06f5ef9b9dfb4f86a0edf1e723e90a34df651705',
                   entries=[0x24C4, 0x24C1, 0x24C3],
                   tables={0x56C1: 12, 0x190B: 33, 0x85BB: 33, 0x774A: 33, 0x76F8: 8, 0x85FD: 4,
                           0x77CE: 8, 0x654C: 5, 0x794D: 7, 0x594B: 16, 0x596B: 16,
                           0xA3A7: 6, 0x9BEC: 4}, inline={},
                   data=[(0x100, 0x1328)], lib=True,   # 0100: SOSARIA.ULT is loaded there
                   modules={0x0100: 'EXDATA',      # map buffer, entry vector, tables and strings
                            0x1BD5: 'LOOP',        # main loop and the surface commands
                            0x207D: 'WORLD',       # moons, moon gates, creatures, start-up
                            0x259E: 'VIEW',        # the map window and map access
                            0x58B4: 'ITEMS',       # chests, torches, negate time
                            0x5D83: 'MAGIC',       # casting and the spells
                            0x62FD: 'SHRINE',      # stats header, shrines, leaving a dungeon
                            0x6B91: 'PARTY',       # names, status lines, hit points, food, poison
                            0x7458: 'ACTIONS',     # Word, Cmd, Insert, Dig, Search, Bribe, Pray
                            0x7AEA: 'HAND',        # the H command (Hand Equipment) and its menus; AskDirection
                            0x7D1A: 'EQUIP',       # error exits, ready weapon, wear armour, Transact (T: talk, shops), gold
                            0x8190: 'DUNMOVE',     # dungeon: traps, darkness, turning, advancing
                            0x84DB: 'CMDTAB',      # tables of the combat commands
                            0x888B: 'COMBAT',      # fights
                            0x941E: 'DUNEVENT',    # dungeon events: fountains, the rod, gremlins
                            0x964F: 'TEXT',        # long messages, shop and verse text
                            0xA46F: 'ENDING',      # the move count and the end of the game
                            0xA5AC: 'TOWNS'},      # pub, grocer, temple, weapons, armour, guild, horses
                   ptrs={0x1328: 1,                # the entry vector BOOTUP jumps through
                         0x16BB: 19,               # map file names
                         0x18C9: 33,               # command prompts (dispatch 190B)
                         0x590B: 32,               # spell names
                         0x598B: 8,                # directions, then attribute names (also 5993)
                         0x6540: 5,                # INSERT DIG SEARCH BRIBE PRAY (then a 0 word)
                         0x6556: 136,              # tile, monster, item and spell names
                         0x6B08: 6,                # menu: Moons Death Love Sol Quit Quit
                         0x6DB1: 8,                # marks and cards
                         0x778C: 33,               # dungeon command prompts (dispatch 774A)
                         0x78BB: 7,                # menu: Food Gold Equipment Weapons Armour Quit Quit
                         0x78E6: 6,                # menu: Gems Keys Powder Torch Quit Quit
                         0x7904: 18,               # menu: Quit Quit and the weapons
                         0x7932: 10,               # menu: Quit Quit and the armour
                         0x9979: 10,               # long messages (endgame, shrines, ...)
                         0x9C1D: 4,                # menu: Buy Sell Quit Quit
                         0xA1B0: 10,               # the "And so thou ..." verses
                         0xA39B: 6},               # menu: Gems Keys Powders Torches Quit Quit
                   immaddr=[0x24D4, 0x24DF],       # int 23h/24h handlers
                   dsforeign=[(0x717C, 0x71BA), (0x71C6, 0x71E7), (0x71F0, 0x722F), (0xA496, 0xA4B3)],
                   bufrel=[(0x24C4, 0x253D, 0x2574)]),     # the combat file's tail (FORMATS.md 5, 9)
    # the dungeon view: not data but a code overlay that EXODUS loads at 0100 (docs/FORMATS.md 8).
    # equs: addresses of the running EXODUS.BIN that it reads (the dungeon map; the screen row table).
    'dungeon': dict(file='DUNGEON.DAT', sha1='2d04c79751fa1e1b27f14922d0d9e17872173028',
                    entries=[0x100, 0x447], tables={}, inline={}, data=[(0x103, 0x447)],
                    equs={0x0900: 'DMAP', 0x132A: 'ROWTAB'}),
}

md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_16)
md.detail = True

Op = collections.namedtuple('Op', 'n type size seg base index disp disp_size imm imm_size text')


class Analysis:
    pass


def is_branch(ins):
    return (capstone.CS_GRP_JUMP in ins.groups or capstone.CS_GRP_CALL in ins.groups or
            ins.mnemonic in ('loop', 'loope', 'loopne', 'jcxz'))


def direct_target(ins):
    if is_branch(ins) and ins.operands and ins.operands[0].type == x86.X86_OP_IMM:
        return ins.operands[0].imm & 0xFFFF
    return None


def load(name):
    t = TARGETS[name]
    data = open(os.path.join(GAMEDATA, t['file']), 'rb').read()
    return bytes(0x100) + data


def analyse(name, extra_entries=()):
    t = TARGETS[name]
    img = load(name)
    end = len(img)
    kind = bytearray(end)
    insn = {}
    entries = list(t['entries']) + list(extra_entries)
    for tb, n in t['tables'].items():
        for i in range(n):
            entries.append(int.from_bytes(img[tb + 2 * i:tb + 2 * i + 2], 'little'))
        for i in range(tb, tb + 2 * n):
            kind[i] = 3
    for a0, a1 in t['data']:
        for i in range(a0, a1):
            kind[i] = 3
    indirect = []
    seen = set()
    while entries:
        pc = entries.pop()
        while 0x100 <= pc < end and pc not in seen and kind[pc] != 3:
            ins = next(md.disasm(img[pc:pc + 16], pc), None)
            if ins is None or pc + ins.size > end:
                break
            seen.add(pc)
            insn[pc] = ins
            kind[pc] = 1
            for i in range(1, ins.size):
                kind[pc + i] = 2
            nxt = pc + ins.size
            tgt = direct_target(ins)
            m = ins.mnemonic
            if tgt is not None:
                entries.append(tgt)
            elif m in ('jmp', 'call', 'ljmp', 'lcall'):
                indirect.append((pc, ins))
            if m == 'call':
                if tgt in t['inline']:
                    e = img.index(b'\0', nxt) + 1 if t['inline'][tgt] == 'z' else nxt + t['inline'][tgt]
                    for i in range(nxt, e):
                        kind[i] = 3
                    nxt = e
                pc = nxt
                continue
            if m in ('ret', 'retf', 'iret', 'hlt', 'jmp', 'ljmp'):
                break
            pc = nxt
    a = Analysis()
    a.name, a.img, a.end, a.kind, a.insn, a.indirect = name, img, end, kind, insn, indirect
    a.targets = {x for x in (direct_target(i) for i in insn.values()) if x is not None}
    for tb, n in t['tables'].items():
        for i in range(n):
            a.targets.add(int.from_bytes(img[tb + 2 * i:tb + 2 * i + 2], 'little'))
    return a


def prefix_seg(ins):
    for p in ins.prefix:
        if p == 0x2E: return 'cs'
        if p == 0x3E: return 'ds'
        if p == 0x26: return 'es'
        if p == 0x36: return 'ss'
    return None


def operands(ins):
    """Op records for ins's explicit operands (memory: effective segment after prefixes)."""
    out = []
    psg = prefix_seg(ins)
    for n, o in enumerate(ins.operands):
        if o.type == x86.X86_OP_MEM:
            base = ins.reg_name(o.mem.base) if o.mem.base else None
            index = ins.reg_name(o.mem.index) if o.mem.index else None
            seg = psg or ('ss' if base == 'bp' else 'ds')
            if base is None and index is None:
                dsz = 2
            else:
                dsz = {0: 0, 1: 1, 2: 2}.get(ins.modrm >> 6, 0)
                if base == 'bp' and index is None and ins.modrm >> 6 == 0:
                    dsz = 2
            out.append(Op(n, 'mem', o.size, seg, base, index, o.mem.disp & 0xFFFF, dsz, None, 0, ins.op_str))
        elif o.type == x86.X86_OP_IMM:
            out.append(Op(n, 'imm', o.size, None, None, None, None, 0, o.imm & 0xFFFF, o.size, ins.op_str))
        else:
            out.append(Op(n, 'reg', o.size, None, ins.reg_name(o.reg), None, None, 0, None, 0, ins.op_str))
    return out


def report(name):
    a = analyse(name)
    code = sum(1 for k in a.kind if k in (1, 2))
    print('%s: %d bytes, %d instructions, %d bytes as code (%.0f%%)' % (
        name, a.end - 0x100, len(a.insn), code, 100.0 * code / (a.end - 0x100)))
    for pc, ins in a.indirect:
        print('  indirect %04X  %s %s' % (pc, ins.mnemonic, ins.op_str))
    eb90 = sum(1 for pc, i in a.insn.items() if i.bytes[0] == 0xEB and i.bytes[1] < 0x80 and a.img[pc + 2] == 0x90)
    e9s = [pc for pc, i in a.insn.items() if i.bytes[0] == 0xE9 and -128 <= direct_target(i) - (pc + 2) <= 127]
    e9sf = [pc for pc in e9s if direct_target(a.insn[pc]) > pc]
    ebf = sum(1 for pc, i in a.insn.items() if i.bytes[0] == 0xEB and direct_target(i) > pc)
    print('  jmp: EB fwd %d (with NOP %d), E9 within short range %d (forward %d)' % (ebf, eb90, len(e9s), len(e9sf)))
    # unreached gaps
    gaps, s = [], None
    for i in range(0x100, a.end):
        if a.kind[i] == 0 and s is None:
            s = i
        elif a.kind[i] != 0 and s is not None:
            gaps.append((s, i)); s = None
    if s is not None:
        gaps.append((s, a.end))
    big = [(g0, g1) for g0, g1 in gaps if g1 - g0 >= 1 and any(a.img[g0:g1])]
    print('  unreached non-zero gaps: %d, %d bytes' % (len(big), sum(g1 - g0 for g0, g1 in big)))
    return a, big


if __name__ == '__main__':
    for n in (sys.argv[1:] or TARGETS):
        a, big = report(n)
        if '-v' in os.environ.get('U3AN', ''):
            for g0, g1 in big:
                print('    %04X-%04X %d' % (g0, g1, g1 - g0))
