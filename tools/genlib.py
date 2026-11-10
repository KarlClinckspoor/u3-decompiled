#!/usr/bin/env python3
"""Generate the shared library module (src/LIB.INC) from the three copies in the game files.

    genlib.py OUTDIR          writes OUTDIR/LIB.INC (tools/gen.py calls it for each target)

The library is one separately assembled module, linked into each program at a paragraph
boundary (BOOTUP 1E40, ULTIMA 6120, EXODUS 2990). It starts with the 256-byte stack that every
program points SP at. Its text comes from BOOTUP.BIN's copy, disassembled with the union of
what the three programs reach. Its labels are Kxxxx: xxxx is the offset from the library start
in BOOTUP.BIN (K2BF0 = BOOTUP 4A30).

The three copies prove which operands are addresses. A word that differs between the copies is
either internal (it points into each copy's own library at the same place, written Kxxxx) or
external (it points into the program, written Xxxxx after its value in BOOTUP.BIN; each
program defines and PUBLICs that name). Everything else is the same in all three and stays a
number (PSP offsets, constants).

EXODUS.BIN links a slightly different version: the dead disk-check routine is different
(BOOTUP 44B0-4503; even the stub at 44B0 differs: it returns 0FFh, not 0) and a zero area before the sound table is 10 bytes shorter (BOOTUP
4B76-4B80). Those two places are IFDEF PROG_EXODUS. Each program's LIB.ASM defines its PROG_
symbol and includes LIB.INC.
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import u3an
import gen

CRLF = '\r\n'
# (padding start, library start, library end) in each file: LINK pads from the first to the
# second (PARA alignment)
RANGE = {'bootup': (0x1E34, 0x1E40, 0x4D74), 'ultima': (0x6113, 0x6120, 0x9054),
         'exodus': (0x298E, 0x2990, 0x58B4)}
LO, HI = RANGE['bootup'][1], RANGE['bootup'][2]
SIZE = HI - LO
# where EXODUS's version differs: BOOTUP range -> EXODUS range
COND = [((0x44B0, 0x4503), (0x5000, 0x504D)), ((0x4B76, 0x4B80), (0x56C0, 0x56C0))]
PROG = {'bootup': 'PROG_BOOTUP', 'ultima': 'PROG_ULTIMA', 'exodus': 'PROG_EXODUS'}


def to_t(t, b):
    """BOOTUP address b in the library -> the same place in target t (None inside COND)."""
    if t == 'bootup':
        return b
    if t == 'ultima':
        return b - LO + RANGE['ultima'][1]
    if b <= COND[0][0][0]:                     # the first region's start can carry a label
        return b + 0xB50
    if COND[0][0][1] <= b < COND[1][0][0]:
        return b + 0xB4A
    if b >= COND[1][0][1]:
        return b + 0xB40
    return None


def from_t(t, a):
    """Address a inside target t's library -> BOOTUP address (None inside COND)."""
    if t == 'bootup':
        return a
    if t == 'ultima':
        return a - RANGE['ultima'][1] + LO
    if a <= COND[0][1][0]:
        return a - 0xB50
    if COND[0][1][1] <= a < COND[1][1][0]:
        return a - 0xB4A
    if a >= COND[1][1][1]:
        return a - 0xB40
    return None


def in_cond(b):
    return any(b0 <= b < b1 for (b0, b1), _ in COND)


def in_lib(t, a, end=False):
    lo, hi = RANGE[t][1], RANGE[t][2]
    return lo <= a < hi or (end and a == hi)


class LibGen(gen.Gen):
    """gen.Gen over BOOTUP.BIN's copy, with the operands the copies prove to be addresses."""

    def __init__(self, analysis, fix):
        super().__init__('bootup', set(), analysis)
        self.fix = fix                          # BOOTUP byte address of a word -> ('int', addr) / ('ext', name)

    def fixtext(self, f):
        return self.sym(f[1]) if f[0] == 'int' else f[1]

    def memtext(self, ins, op):
        if op.disp_size != 2:
            return None
        pos = ins.address + ins.disp_offset
        if pos not in self.fix:
            return None
        regs = [r for r in (op.base, op.index) if r]
        seg = u3an.prefix_seg(ins)
        return (seg + ':' if seg else '') + self.fixtext(self.fix[pos]) + ('[' + '+'.join(regs) + ']' if regs else '')

    def conv(self, ins):
        r = super().conv(ins)
        if r is None or u3an.is_branch(ins) or not ins.imm_size:
            return r
        pos = ins.address + ins.imm_offset
        if pos in self.fix:
            skip = 0
            if isinstance(r, tuple):
                r, skip = r
            imm = [p for p in u3an.operands(ins) if p.type == 'imm'][0].imm
            h = gen.hx(imm)
            i = r.rindex(h)
            r = r[:i] + 'offset ' + self.fixtext(self.fix[pos]) + r[i + len(h):]
            return (r, skip) if skip else r
        return r


class Lib:
    def __init__(self):
        self.img = {t: u3an.load(t) for t in RANGE}
        B = self.img['bootup']
        assert RANGE['ultima'][2] - RANGE['ultima'][1] == SIZE
        # coverage: what any of the three reaches, decoded in BOOTUP's copy
        self.an = {t: u3an.analyse(t) for t in RANGE}
        extra = set()
        for t in ('ultima', 'exodus'):
            a = self.an[t]
            for x in list(a.insn) + list(a.targets):
                if in_lib(t, x):
                    b = from_t(t, x)
                    if b is not None and (t == 'ultima' or not in_cond(b)):   # ULTIMA's copy = BOOTUP's
                        extra.add(b)
        self.ba = u3an.analyse('bootup', extra_entries=sorted(extra))
        self.find_fixups()
        self.g = LibGen(self.ba, self.fix)
        self.program_refs()
        self.lines = self.make()

    # ---- which words are addresses
    def word(self, t, a):
        im = self.img[t]
        return im[a] | im[a + 1] << 8

    def classify(self, vals):
        """vals {t: word} -> ('int', BOOTUP addr) or ('ext', vals) or None."""
        c = {}
        for t, v in vals.items():
            if in_lib(t, v, end=True):
                b = from_t(t, v) if v < RANGE[t][2] else HI
                c[t] = b
            else:
                c[t] = None
        if all(x is not None for x in c.values()) and len(set(c.values())) == 1:
            return ('int', c['bootup'])
        if all(x is None for x in c.values()):
            return ('ext', vals)
        return None

    def find_fixups(self):
        B, ba = self.img['bootup'], self.ba
        diff = set()
        for b in range(LO, HI):
            if in_cond(b):
                continue
            if any(self.img[t][to_t(t, b)] != B[b] for t in ('ultima', 'exodus')):
                diff.add(b)
        self.fix, self.ext = {}, {}             # ext: name -> {t: value}
        covered = set()

        def add(pos, vals):
            k = self.classify(vals)
            if k is None:
                raise SystemExit('genlib: word at BOOTUP %04X is neither internal nor external: %s' % (
                    pos, {t: '%04X' % v for t, v in vals.items()}))
            if k[0] == 'ext':
                name = 'X%04X' % vals['bootup']
                if self.ext.setdefault(name, vals) != vals:
                    raise SystemExit('genlib: %s has two meanings' % name)
                k = ('ext', name)
            self.fix[pos] = k
            covered.update((pos, pos + 1))
        for pc, ins in ba.insn.items():
            if not LO <= pc < HI:
                continue
            span = set(range(pc, pc + ins.size))
            if not span & diff:
                continue
            fields = []
            if ins.disp_size == 2:
                fields.append(pc + ins.disp_offset)
            if ins.imm_size == 2 and not u3an.is_branch(ins):
                fields.append(pc + ins.imm_offset)
            for f in fields:
                if {f, f + 1} & diff:
                    add(f, {t: self.word(t, to_t(t, f)) for t in RANGE})
            tg = u3an.direct_target(ins)
            if tg is not None:                  # a relative branch across EXODUS's shorter parts
                same = True
                for t in ('ultima', 'exodus'):
                    a = to_t(t, pc)
                    ti = next(u3an.md.disasm(self.img[t][a:a + 8], a))
                    tt = u3an.direct_target(ti)
                    same &= ti.size == ins.size and tt is not None and in_lib(t, tt) and from_t(t, tt) == tg
                if same:
                    covered.update(span)
            left = (span & diff) - covered
            if left:
                raise SystemExit('genlib: %04X %s %s differs outside an address field' % (pc, ins.mnemonic, ins.op_str))
        tw = set()
        for tb, n in u3an.TARGETS['bootup']['tables'].items():
            if LO <= tb < HI:
                for i in range(n):
                    p = tb + 2 * i
                    tw.update((p, p + 1))
                    k = self.classify({t: self.word(t, to_t(t, p)) for t in RANGE})
                    assert k and k[0] == 'int', hex(p)
        for p in sorted(diff - covered - tw):
            if p in covered:
                continue
            for s in (p, p - 1):
                k = self.classify({t: self.word(t, to_t(t, s)) for t in RANGE})
                if k and k[0] == 'int':
                    add(s, {t: self.word(t, to_t(t, s)) for t in RANGE})
                    break
            else:
                raise SystemExit('genlib: data byte at BOOTUP %04X differs and is no internal pointer' % p)
        incode = set()
        for pc, ins in ba.insn.items():
            incode.update(range(pc, pc + ins.size))
        self.datafix = sorted(p for p in self.fix if p not in incode)

    # ---- what the programs reference in the library
    def program_refs(self):
        self.refs = {t: {} for t in RANGE}      # t -> {addr in t: 'Lxxxx' text in BOOTUP terms}
        for t in RANGE:
            a = self.an[t]
            pad, lo, hi = RANGE[t]
            tw = {}
            for tb, n in u3an.TARGETS[t]['tables'].items():
                for i in range(n):
                    tw[tb + 2 * i] = self.word(t, tb + 2 * i)
            targets = set()
            for pc, ins in a.insn.items():
                if pad <= pc < hi:
                    continue
                tg = u3an.direct_target(ins)
                if tg is not None:
                    targets.add(tg)
                for op in u3an.operands(ins):
                    if op.type == 'mem' and op.disp_size == 2 and op.seg == 'ds' and u3an.prefix_seg(ins) is None:
                        targets.add(op.disp)
            for p, v in tw.items():
                if not pad <= p < hi:
                    targets.add(v)
            for x in targets:
                if lo <= x < hi:
                    b = from_t(t, x)
                    if b is None:
                        raise SystemExit('genlib: %s references %04X inside the differing part' % (t, x))
                    self.refs[t][x] = self.g.sym(b)
                elif pad <= x < lo:
                    raise SystemExit('genlib: %s references the padding at %04X' % (t, x))

    # ---- text
    def kname(self, text):
        return re.sub(r'\bL([0-9A-F]{4})\b', lambda m: 'K%04X' % (int(m.group(1), 16) - LO), text)

    def ref(self, t, x):
        return self.kname(self.refs[t][x])

    def is_code(self, kname):
        return int(kname[1:], 16) + LO in self.ba.insn

    def make(self):
        g, B = self.g, self.img['bootup']
        for pc in g.starts:                     # collect labels
            if LO <= pc < HI:
                g.conv(g.a.insn[pc])
        for p in self.datafix:
            g.dataptr[p] = 'dw ' + g.fixtext(self.fix[p])
        X = self.img['exodus']
        for (b0, b1), (x0, x1) in COND:
            for t in ('ultima',):
                assert self.img[t][to_t(t, b0) if False else b0 - LO + RANGE[t][1]:b1 - LO + RANGE[t][1]] == B[b0:b1]
            L = ['L%04X label near' % b0] if b0 in g.labels else []
            L.append('IFDEF PROG_EXODUS')
            if x1 > x0:
                g.dbl(L.append, X[x0:x1], b0)
            L.append('ELSE')
            g.dbl(L.append, B[b0:b1], b0)
            L.append('ENDIF')
            g.special[b0] = (L, b1)
        body = []
        g.emit(body.append, LO, HI)
        body = [self.kname(l) for l in body]
        pub = set()
        for t in RANGE:
            for x in self.refs[t].values():
                pub.add(self.kname(x).split('+')[0])
        L = []
        w = L.append
        w('; LIB.INC: the library linked into all three Ultima III programs (screen, text, keyboard,')
        w('; files, sound). Generated by tools/genlib.py from the three copies; each program\'s LIB.ASM')
        w('; defines PROG_ULTIMA, PROG_BOOTUP or PROG_EXODUS and includes this. Kxxxx = offset from the')
        w('; library start in BOOTUP.BIN; Xxxxx = a symbol of the program (value in BOOTUP.BIN).')
        w('CODE SEGMENT PARA PUBLIC')
        w('ASSUME CS:CODE, DS:CODE, ES:CODE, SS:CODE')
        for x in sorted(self.ext):
            w('EXTRN %s:BYTE' % x)
        for x in sorted(pub, key=lambda s: int(s[1:], 16)):
            w('PUBLIC %s' % x)
        L.extend(body)
        w('CODE ENDS')
        return L

    def wrapper(self, t):
        return ['; The shared library (src/LIB.INC) as linked into %s.' % u3an.TARGETS[t]['file'],
                '%s EQU 1' % PROG[t], 'INCLUDE LIB.INC', 'END']


_lib = None


def get():
    global _lib
    if _lib is None:
        _lib = Lib()
    return _lib


def main():
    out = sys.argv[1]
    lib = get()
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, 'LIB.INC'), 'w', newline='').write(CRLF.join(lib.lines) + CRLF)
    print('LIB.INC: %d lines, %d address words (%d external: %s), %d labels used by the programs' % (
        len(lib.lines), len(lib.fix), sum(1 for f in lib.fix.values() if f[0] == 'ext'),
        ' '.join(sorted(lib.ext)), sum(len(r) for r in lib.refs.values())))


if __name__ == '__main__':
    main()
