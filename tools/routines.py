#!/usr/bin/env python3
"""Survey of a program's routines for the split into modules (phase 5).

    python3 tools/routines.py TARGET [FROM [TO]]       TARGET: exodus, bootup or ultima

A routine starts at a call target or a jump-table entry (plus the entries in TARGETS). For each:
address, size, number of callers, the library routines it calls, the first strings it prints
(`lea si, label` followed by a call, or a string pointer table entry) and the dispatch table
that reaches it. Addresses of the library are not listed as routines.
"""
import collections, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import u3an, genlib


def string_at(img, a, end):
    if not 0x100 <= a < end:
        return None
    e = img.find(b'\0', a, min(end, a + 60))
    s = img[a:e if e >= 0 else a + 40]
    if len(s) >= 3 and all(c in (10, 13) or 32 <= c < 127 for c in s):
        return s.decode('latin1').replace('\n', '/')[:28]
    return None


def survey(target):
    a = u3an.analyse(target)
    t = u3an.TARGETS[target]
    pad, lo, hi = genlib.RANGE[target]
    inlib = lambda x: pad <= x < hi
    calls = collections.defaultdict(set)
    for pc, i in a.insn.items():
        if i.mnemonic == 'call':
            tg = u3an.direct_target(i)
            if tg is not None:
                calls[tg].add(pc)
    entries = set(calls) | set(t['entries'])
    via = {}
    for tb, n in t['tables'].items():
        for k in range(n):
            v = a.img[tb + 2 * k] | a.img[tb + 2 * k + 1] << 8
            entries.add(v)
            via.setdefault(v, []).append('%04X[%d]' % (tb, k))
    # fall-through code that is not a call target is part of the routine before it
    entries = sorted(e for e in entries if e in a.insn and not inlib(e))
    out = []
    for k, e in enumerate(entries):
        nxt = entries[k + 1] if k + 1 < len(entries) else a.end
        if e < pad <= nxt:
            nxt = pad
        # the routine's last instruction: walk from e to nxt over instructions
        pcs = [p for p in sorted(a.insn) if e <= p < nxt]
        size = (pcs[-1] + a.insn[pcs[-1]].size - e) if pcs else 0
        libcalls, strs, callees = [], [], []
        for p in pcs:
            i = a.insn[p]
            tg = u3an.direct_target(i)
            if i.mnemonic == 'call' and tg is not None:
                (libcalls if inlib(tg) else callees).append(tg)
            if i.mnemonic == 'lea':
                for op in u3an.operands(i):
                    if op.type == 'mem' and op.disp_size == 2 and not (op.base or op.index):
                        pass
                if i.op_str.startswith('si, [0x'):
                    v = int(i.op_str[7:-1], 16)
                    s = string_at(a.img, v, a.end)
                    if s:
                        strs.append(s)
        out.append(dict(addr=e, size=size, callers=len(calls.get(e, ())), via=via.get(e, []),
                        lib=sorted(set(libcalls)), callees=sorted(set(callees)), strs=strs))
    return a, out


def main():
    target = sys.argv[1]
    lo = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0
    hi = int(sys.argv[3], 16) if len(sys.argv) > 3 else 1 << 20
    a, rs = survey(target)
    for r in rs:
        if lo <= r['addr'] < hi:
            print('%04X %5d  callers %-3d %-14s %s' % (
                r['addr'], r['size'], r['callers'], ','.join(r['via'][:2]),
                ' | '.join(r['strs'][:3])))


if __name__ == '__main__':
    main()
