#!/usr/bin/env python3
"""Generate a MASM source for one Ultima III image from the original file.

    gen.py TARGET OUTDIR [FORCEFILE] [LIMIT]       TARGET: ultima, bootup or exodus

Writes OUTDIR/NAME.ASM, or NAME1.ASM, NAME2.ASM, ... when LIMIT (a rough module size in bytes)
splits the image into modules; OUTDIR/NAME.lnk lists the modules in link order and NAME.ins
the unit starts (for tools/regen.py).

One segment, as in a COM program: CODE (BYTE PUBLIC, so LINK joins the modules' pieces with no
gaps) with ORG 100h in the first module, ASSUME CS/DS/ES/SS:CODE. Code is found by recursive
disassembly (tools/u3an.py); everything else is db (runs of zeros as dup).

Symbols:
  Lxxxx     every branch target, every jump-table entry, and every offset that a DS operand
            with a 16-bit displacement names inside the image (direct [1234h] or with a base
            or index register, L1234[bx]). A reference into the middle of an instruction or a
            table word is written Lxxxx+n. Across modules: EXTRN/PUBLIC.
  L00xx     offsets in the PSP (below 0100) that a DS operand or a branch names: labels
            placed with ORG before the ORG 100h of the first module (a relocatable symbol
            also keeps MASM from shortening [bx+0000] to [bx]).
Displacements past the end of the file, 8-bit displacements, immediates and es:/ss:/cs:
operands stay numbers for now (making them symbols is phase 3 of docs/PLAN.md). Jump tables
(TARGETS[...]['tables']) are dw Lxxxx. A call or jump into a data area (EXODUS calls 0100,
where SOSARIA.ULT is loaded) is written near ptr to that data label.
Modules start at routine entries that no 8-bit relative branch crosses (MASM cannot make a
short jump to an external).
Instructions MASM can't reproduce, or listed in FORCEFILE, are written as db. Each line is
tagged ;@addr (its address in the original) for tools/regen.py.
"""
import bisect, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import u3an

CRLF = '\r\n'


def hx(v):
    s = '%X' % v
    return ('0' + s if s[0] in 'ABCDEF' else s) + 'h'


STR = {'movsb', 'movsw', 'stosb', 'stosw', 'lodsb', 'lodsw', 'cmpsb', 'cmpsw', 'scasb', 'scasw'}
OK = set('''mov add adc sub sbb and or xor cmp test inc dec neg not push pop call jmp ret
 shl shr sal sar rol ror rcl rcr mul imul div idiv cbw cwd lea xchg in out int nop
 stc clc cmc std cld sti cli pushf popf lahf sahf jcxz loop loope loopne iret daa das aaa aas
 jo jno jb jae je jne jbe ja js jns jp jnp jl jge jle jg hlt'''.split())
LABEL = re.compile(r'\bL[0-9A-F]{4}\b')
DEFLABEL = re.compile(r'^(L[0-9A-F]{4})\b')
LINEADDR = re.compile(r';@([0-9A-F]{4})')


class Gen:
    def __init__(self, name, force):
        self.t = u3an.TARGETS[name]
        self.a = u3an.analyse(name)
        self.img, self.end = self.a.img, self.a.end
        self.force = force
        self.starts = sorted(self.a.insn)
        self.tablewords = {}                   # addr -> target of each jump-table word
        for tb, n in self.t['tables'].items():
            for i in range(n):
                self.tablewords[tb + 2 * i] = int.from_bytes(self.img[tb + 2 * i:tb + 2 * i + 2], 'little')
        # atomic units (a label can only sit at their start): instructions and table words
        self.units = sorted(set(self.starts) | set(self.tablewords))
        self.usize = {pc: self.a.insn[pc].size for pc in self.starts}
        self.usize.update({pc: 2 for pc in self.tablewords})
        self.labels = {x for x in self.a.targets if x in self.a.insn}
        self.labels |= {v for v in self.tablewords.values() if v in self.a.insn}
        self.breaks = set()
        self.cuts = []
        self.low = set()                       # offsets below 0100 (PSP) that get a label
        self.lowcode = set()                   # ... of which branch targets

    def sym(self, t):
        """Symbol text for offset t inside the image (registers the label)."""
        i = bisect.bisect_right(self.units, t) - 1
        if i >= 0:
            u = self.units[i]
            if u < t < u + self.usize[u]:
                self.labels.add(u)
                return 'L%04X+%d' % (u, t - u)
        self.labels.add(t)
        return 'L%04X' % t

    def memtext(self, ins, op):
        """Symbolic text for a memory operand, or None to keep it numeric."""
        if op.disp_size != 2 or op.seg != 'ds' or u3an.prefix_seg(ins) is not None:
            return None
        regs = [r for r in (op.base, op.index) if r]
        idx = '[' + '+'.join(regs) + ']' if regs else ''
        if op.disp < 0x100:                    # the PSP (a label placed with ORG)
            self.low.add(op.disp)
            return 'L%04X' % op.disp + idx
        if op.disp >= self.end:
            return None
        return self.sym(op.disp) + idx

    def conv(self, ins):
        """MASM text for ins, or None for db. May return (text, skip)."""
        m, o = ins.mnemonic, ins.op_str
        if m.startswith('rep'):
            parts = m.split()
            if len(parts) == 2 and parts[1] in STR:
                if 'cs:' in o or 'ss:' in o or ('es:' in o and parts[1].startswith('lods')):
                    return None
                if parts[1].startswith(('movs', 'lods')) and re.search(r'(cs|ss|es):\[si\]', o):
                    return None
                return parts[0] + ' ' + parts[1]
            return None
        if m in STR:
            if re.search(r'(cs|ss|es):\[si\]', o):
                return None
            return m
        if ins.bytes in (b'\x98', b'\x99'):     # capstone prints the 32-bit names
            return 'cbw' if ins.bytes == b'\x98' else 'cwd'
        if m == 'aam' and ins.bytes == b'\xd4\x0a':
            return 'aam'
        if m == 'aad' and ins.bytes == b'\xd5\x0a':
            return 'aad'
        if m not in OK:
            return None
        if u3an.is_branch(ins):
            t = u3an.direct_target(ins)
            if t is not None:
                if t not in self.a.insn:
                    if m not in ('jmp', 'call') or ins.bytes[0] not in (0xE8, 0xE9):
                        return None
                    if t < 0x100:              # into the PSP: a label placed with ORG
                        self.low.add(t)
                        self.lowcode.add(t)
                        return '%s near ptr L%04X' % (m, t)
                    if t < self.end:           # into a data area (a file is loaded there)
                        return '%s near ptr %s' % (m, self.sym(t))
                    return None
                self.labels.add(t)
                lab = 'L%04X' % t
                if m == 'jmp':
                    op, fwd = ins.bytes[0], t > ins.address
                    if op == 0xEB:
                        if fwd:
                            nop = ins.address + 2 < self.end and self.img[ins.address + 2] == 0x90
                            return ('jmp ' + lab, 1) if nop else 'jmp short ' + lab
                        return 'jmp ' + lab
                    if op == 0xE9:
                        d = t - (ins.address + 3)
                        if -128 <= d <= 127:
                            return None             # MASM would make it short
                        return 'jmp ' + lab
                    return None
                if m == 'call' and ins.bytes[0] != 0xE8:
                    return None
                return m + ' ' + lab
        ops = u3an.operands(ins)
        if m == 'xchg' and ins.bytes[0] in (0x86, 0x87) and all(p.type == 'reg' for p in ops):
            # MASM puts the first operand in the reg field: swap capstone's rm,reg order
            return 'xchg %s, %s' % (ops[1].base, ops[0].base)
        mems = [p for p in ops if p.type == 'mem']
        o = re.sub(r'0x([0-9a-f]+)', lambda mm: hx(int(mm.group(1), 16)), o)
        if mems:
            new = self.memtext(ins, mems[0])
            if new is None:
                def mem(mm):
                    seg, inner = mm.group(1), mm.group(2)
                    if re.search(r'\b(bx|bp|si|di)\b', inner):
                        return (seg or '') + '[' + inner.replace(' ', '') + ']'
                    return (seg or 'ds:') + '[' + inner.replace(' ', '') + ']'
                o = re.sub(r'((?:cs|ds|es|ss):)?\[([^\]]+)\]', mem, o)
            else:
                o = re.sub(r'((?:cs|ds|es|ss):)?\[([^\]]+)\]', lambda mm: new, o, count=1)
            if m == 'lea' and ' ptr ' in o:
                o = re.sub(r'\b(byte|word|dword) ptr ', '', o)
        return (m + ' ' + o).strip()

    # ---- modules
    def crossing(self):
        """bad[c] = 1 where an 8-bit relative branch crosses address c (no module may start there)."""
        bad = bytearray(self.end + 1)
        for pc, ins in self.a.insn.items():
            b0 = ins.bytes[0]
            if b0 == 0xEB or 0x70 <= b0 <= 0x7F or 0xE0 <= b0 <= 0xE3:
                t = u3an.direct_target(ins)
                for c in range(min(pc, t) + 1, max(pc, t) + 1):
                    bad[c] = 1
        return bad

    def choose_cuts(self, limit):
        """Module starts at routine entries (call targets) no short branch crosses, so that no
        module holds much more than `limit` bytes (zero runs count 1/16)."""
        if not limit:
            return []
        bad = self.crossing()
        calls = {u3an.direct_target(i) for i in self.a.insn.values() if i.mnemonic == 'call'}
        cand = sorted(c for c in calls if c in self.a.insn and not bad[c])
        wt = [1.0 if b else 1.0 / 16 for b in self.img]
        cuts, last, weight, best, ci = [], 0x100, 0.0, None, 0
        for pc in range(0x100, self.end):
            weight += wt[pc]
            while ci < len(cand) and cand[ci] <= pc:
                best = cand[ci]
                ci += 1
            if weight > limit and best and best > last:
                cuts.append(best)
                last = best
                weight = sum(wt[best:pc + 1])
        return cuts

    def run(self, limit=0):
        a = self.a
        for pc in self.starts:                 # pass 1: collect labels
            if pc not in self.force:
                self.conv(a.insn[pc])
        self.cuts = self.choose_cuts(limit)
        self.breaks = set(self.cuts)
        self.labels |= self.breaks
        body = []
        self.nforced = self.emit(body.append)

        def addr(line):                        # every line carries its address
            m = LINEADDR.search(line) or re.match(r'L([0-9A-F]{4})', line)
            return int(m.group(1), 16)
        bounds = [0x100] + self.cuts + [self.end]
        mods = [[] for _ in range(len(bounds) - 1)]
        k = 0
        for line in body:
            while addr(line) >= bounds[k + 1]:
                k += 1
            mods[k].append(line)
        defs = [set(DEFLABEL.match(l).group(1) for l in m if DEFLABEL.match(l)) for m in mods]
        defs[0] |= {'L%04X' % x for x in self.low}    # placed with ORG in the first module
        uses = [set(x for l in m for x in LABEL.findall(DEFLABEL.sub('', l).split(';')[0])) for m in mods]
        out = []
        for i, m in enumerate(mods):
            L = []
            w = L.append
            w('; %s: Ultima III (Origin 1983, PC version by James R. Van Artsdalen).' % self.t['file'])
            w('; Generated by tools/gen.py; tools/build.py builds it (MASM, LINK, then the image from 0100).')
            if len(mods) > 1:
                w('; Module %d of %d: %04X-%04X.' % (i + 1, len(mods), bounds[i], bounds[i + 1]))
            w('CODE SEGMENT BYTE PUBLIC')
            w('ASSUME CS:CODE, DS:CODE, ES:CODE, SS:CODE')
            others = set()
            for j in range(len(mods)):
                if j != i:
                    others |= uses[j]
            for x in sorted(uses[i] - defs[i]):
                w('EXTRN %s:%s' % (x, 'NEAR' if int(x[1:], 16) in a.insn else 'BYTE'))
            for x in sorted(defs[i] & others):
                w('PUBLIC %s' % x)
            if i == 0:
                for x in sorted(self.low):     # branch targets in the PSP
                    w('ORG %s' % hx(x))
                    w("L%04X label %s" % (x, "near" if x in self.lowcode else "byte"))
                w('ORG 100h')
            L.extend(m)
            w('CODE ENDS')
            w('END')
            out.append(L)
        return out

    # ---- output
    def dbl(self, w, bs, at):
        i = 0
        while i < len(bs):
            j = i
            while j < len(bs) and bs[j] == 0:
                j += 1
            if j - i >= 16:
                w('\tdb %d dup (0)\t;@%04X' % (j - i, at + i))
                i = j
                continue
            k = min(i + 16, len(bs))
            w('\tdb ' + ','.join(hx(b) for b in bs[i:k]) + '\t;@%04X' % (at + i))
            i = k

    def emit(self, w):
        a, img = self.a, self.img
        pc, buf, nforced = 0x100, [], 0
        start = [0x100]

        def flush():
            if buf:
                self.dbl(w, bytes(buf), start[0])
                del buf[:]
        if 0x100 not in a.insn:
            self.labels.add(0x100)
        while pc < self.end:
            if pc in self.breaks:
                flush()
            if pc in self.tablewords:
                flush()
                v = self.tablewords[pc]
                lab = 'L%04X' % pc if pc in self.labels else ''
                w(lab + ('\tdw L%04X' % v if v in a.insn else '\tdw %s' % hx(v)) + '\t;@%04X' % pc)
                pc += 2
                continue
            if a.kind[pc] == 1 and pc in a.insn:
                ins = a.insn[pc]
                r = None if pc in self.force else self.conv(ins)
                skip = 0
                if isinstance(r, tuple):
                    r, skip = r
                if r is None:
                    if pc in self.labels:
                        flush()
                        w('L%04X:' % pc)
                    if not buf:
                        start[0] = pc
                    buf.extend(ins.bytes)
                    pc += ins.size
                    nforced += 1
                    continue
                flush()
                lab = 'L%04X:' % pc if pc in self.labels else ''
                w(lab + '\t' + r + '\t;@%04X' % pc)
                pc += ins.size + skip
            else:
                if pc in self.labels:
                    flush()
                    w('L%04X label byte' % pc)
                if not buf:
                    start[0] = pc
                buf.append(img[pc])
                pc += 1
        flush()
        return nforced


def main():
    name, outdir = sys.argv[1], sys.argv[2]
    force = set()
    if len(sys.argv) > 3 and os.path.exists(sys.argv[3]):
        force = {int(x, 16) for x in open(sys.argv[3]).read().split()}
    limit = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    g = Gen(name, force)
    mods = g.run(limit)
    stem = os.path.splitext(g.t['file'])[0]
    names = [stem + '.ASM'] if len(mods) == 1 else ['%s%d.ASM' % (stem, i + 1) for i in range(len(mods))]
    os.makedirs(outdir, exist_ok=True)
    for n, lines in zip(names, mods):
        open(os.path.join(outdir, n), 'w', newline='').write(CRLF.join(lines) + CRLF)
    open(os.path.join(outdir, stem + '.lnk'), 'w').write(''.join(n + '\n' for n in names))
    open(os.path.join(outdir, stem + '.ins'), 'w').write(' '.join(str(x) for x in g.units))
    print('instructions %d, as db %d, labels %d, modules %d %s' % (
        len(g.starts), g.nforced, len(g.labels), len(mods), ' '.join('%04X' % c for c in g.cuts)))


if __name__ == '__main__':
    main()
