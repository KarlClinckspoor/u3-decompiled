#!/usr/bin/env python3
"""Relocation test: build every target with padding inserted in each program module, then check
that the result is the original with every address moved and nothing else changed.

    python3 tools/shift.py [TARGET ...] [--pad N,N,...] [--out DIR]

Padding (NOPs) goes into each program module of src/TARGET/NAME.lnk: in the first module after
the line at 0100 (ULTIMA's and BOOTUP's entry `jmp` must stay at 0100; in EXODUS after the
entry vector at 1328, since the map buffer before it is a fixed 1228h bytes that BOOTUP's
`jmp word ptr [1328h]` relies on), in the others at their first line (a routine entry). The
amounts are odd and differ per module (default 19, 5, 7, 11, ...): 19 bytes before the library
move it by one or two paragraphs, so the library is relocated too.

The check: the shifted file is predicted from the original by moving every byte to its new
place, then comparing. Every difference must be a word (or a relative displacement) whose
original value, moved, gives the new value: an address. Relative branches and calls must reach
the moved target. Anything else is reported.

What this can't see: an address the source still writes as a number keeps its value in both
builds, so it looks like a constant. Play the shifted build (tools/play.py) to catch those.
Output: build/shift/TARGET/ (runnable files).
"""
import argparse, os, re, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import build, u3an, genlib, syms

TAG = re.compile(r';@([0-9A-F]{4})')


def pad_lines(n):
    return ['\tdb ' + ','.join(['90h'] * min(16, n - i)) for i in range(0, n, 16)]


def first_tag(lines):
    for l in lines:
        m = TAG.search(l)
        if m:
            return int(m.group(1), 16)
    return None


def prepare(target, pads, work):
    """Copy src/TARGET with padding inserted; returns [(original address, bytes inserted)]."""
    src = os.path.join(build.SRC, target)
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    name = os.path.splitext(u3an.TARGETS[target]['file'])[0]
    mods = [l.split(';')[0].strip() for l in open(os.path.join(src, name + '.lnk')) if l.strip()]
    ins, k = [], 0
    for f in os.listdir(src):
        shutil.copy(os.path.join(src, f), os.path.join(work, f))
    for f in os.listdir(build.SRC):
        if f.upper().endswith('.INC'):
            shutil.copy(os.path.join(build.SRC, f), os.path.join(work, f))
    for m in mods:
        if m.upper() == 'LIB.ASM':
            continue
        n = pads[k % len(pads)]
        k += 1
        p = os.path.join(work, m)
        lines = open(p, 'rb').read().decode('latin1').split('\r\n')
        if 'ORG 100h' in lines:
            # after the line at 0100 (ULTIMA, BOOTUP) or after the entry vector (EXODUS)
            key = '1328' if target == 'exodus' else '0100'
            at = next(i for i, l in enumerate(lines) if TAG.search(l) and TAG.search(l).group(1) == key) + 1
            addr = int(key, 16) + 2 if target == 'exodus' else 0x100 + u3an.analyse(target).insn[0x100].size
        else:
            at = next(i for i, l in enumerate(lines) if TAG.search(l) or (syms.SYMDEF.match(l) and not syms.SYMDEF.match(l).group(4)))
            addr = first_tag(lines[at:])
        lines[at:at] = pad_lines(n)
        open(p, 'wb').write('\r\n'.join(lines).encode('latin1'))
        ins.append((addr, n))
    return ins


def mover(target, ins):
    """Old address -> new address, from the insertions and the library's paragraph alignment."""
    pad, lo, hi = genlib.RANGE[target]
    ins = sorted(ins)

    def before(a):                             # program padding inserted before address a
        return sum(n for x, n in ins if x <= a)
    newpad = pad + before(pad - 1)
    newlo = (newpad + 15) & ~15
    dlib = newlo - lo

    def f(a):
        if a < pad:
            return a + before(a)
        if a < hi:
            return a + dlib if a >= lo else None
        return a + dlib + sum(n for x, n in ins if hi <= x <= a)
    return f


def check(target, ins, new):
    old = u3an.load(target)
    new = bytes(0x100) + new
    f = mover(target, ins)
    pad, lo, hi = genlib.RANGE[target]
    pred = bytearray(len(new))
    have = bytearray(len(new))
    for a in range(0x100, len(old)):
        b = f(a)
        if b is None:
            continue
        if b >= len(new):
            return ['%04X moves to %04X, past the end of the new file (%04X)' % (a, b, len(new))]
        pred[b] = old[a]
        have[b] = 1
    for x, n in ins:                           # the padding itself
        b = f(x) - n
        for i in range(n):
            pred[b + i] = 0x90
            have[b + i] = 1
    problems, explained = [], set()
    an = u3an.analyse(target)
    lib = genlib.get()
    # relative branches: the moved target
    insns = dict(an.insn)
    for pc, i in lib.ba.insn.items():          # the library's code, in this target's addresses
        if genlib.LO <= pc < genlib.HI and not genlib.in_cond(pc):
            a = genlib.to_t(target, pc)
            insns.setdefault(a, next(u3an.md.disasm(old[a:a + 8], a)))
    for pc, i in insns.items():
        if f(pc) is None or pc + i.size > len(old):
            continue
        t = u3an.direct_target(i)
        if t is not None and i.bytes[0] in (0xE8, 0xE9, 0xEB) or (t is not None and (0x70 <= i.bytes[0] <= 0x7F or 0xE0 <= i.bytes[0] <= 0xE3)):
            nb = f(pc)
            ft = f(t) if t < len(old) else None
            if ft is None:
                continue
            size = i.size
            disp = ft - (nb + size)
            if i.bytes[0] in (0xE8, 0xE9):
                pred[nb + 1:nb + 3] = (disp & 0xFFFF).to_bytes(2, 'little')
                explained.update((nb + 1, nb + 2))
            else:
                if not -128 <= disp <= 127:
                    problems.append('%04X: short branch to %04X out of reach after the shift' % (pc, t))
                pred[nb + 1] = disp & 0xFF
                explained.add(nb + 1)
    # words that differ: moved addresses
    b = 0x100
    while b < len(new):
        if have[b] and pred[b] != new[b]:
            ok = False
            for s in (b, b - 1):
                if s + 1 < len(new) and have[s] and have[s + 1]:
                    ow = pred[s] | pred[s + 1] << 8
                    nw = new[s] | new[s + 1] << 8
                    if 0x100 <= ow <= len(old) and f(min(ow, len(old) - 1)) is not None and (
                            f(min(ow, len(old) - 1)) + (ow - min(ow, len(old) - 1))) == nw:
                        pred[s], pred[s + 1] = new[s], new[s + 1]
                        ok = True
                        break
            if not ok:
                problems.append('new %04X: expected %02X, built %02X' % (b, pred[b], new[b]))
                if len(problems) > 30:
                    break
        b += 1
    for b in range(0x100, len(new)):
        if not have[b] and new[b] != 0:
            problems.append('new %04X: unexpected byte %02X (alignment padding should be 0)' % (b, new[b]))
            break
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('targets', nargs='*', default=['ultima', 'bootup', 'exodus'])
    ap.add_argument('--pad', default='19,5,7,11')
    ap.add_argument('--out', default=os.path.join(ROOT, 'build', 'shift'))
    a = ap.parse_args()
    pads = [int(x) for x in a.pad.split(',')]
    bad = False
    for t in a.targets:
        work = os.path.join(a.out, t + '_src')
        ins = prepare(t, pads, work)
        save = build.SRC
        try:
            # build() reads SRC/TARGET and SRC/*.INC: point SRC at a copy holding the padded sources
            tmp = os.path.join(a.out, 'src')
            shutil.rmtree(tmp, ignore_errors=True)
            os.makedirs(tmp)
            shutil.copytree(work, os.path.join(tmp, t))
            for f in os.listdir(save):
                if f.upper().endswith('.INC'):
                    shutil.copy(os.path.join(save, f), os.path.join(tmp, f))
            build.SRC = tmp
            path = build.build(t, os.path.join(a.out, t))
        finally:
            build.SRC = save
        new = open(path, 'rb').read()
        probs = check(t, ins, new)
        f = mover(t, ins)
        pad, lo, hi = genlib.RANGE[t]
        print('%s: inserted %s; library %04X -> %04X; %d -> %d bytes: %s' % (
            t, ', '.join('%d at %04X' % (n, x) for x, n in ins), lo, f(lo), len(u3an.load(t)) - 0x100,
            len(new), 'OK, only addresses moved' if not probs else '%d PROBLEMS' % len(probs)))
        for p in probs[:30]:
            print('   ', p)
        bad |= bool(probs)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
