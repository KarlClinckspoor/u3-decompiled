#!/usr/bin/env python3
"""List what is still a number in the program modules but might be an address (phase 3).

    python3 tools/cands.py [TARGET ...] [--all]

1. 16-bit immediates (not branches) whose value lies inside the image, or just past it.
2. Memory operands with a segment prefix (cs:/ss:/es:) and a 16-bit displacement inside the
   image, and DS operands whose displacement lies past the end of the file.
3. Words in data areas whose value is a code label or a labelled data address.
Each line: address, instruction or bytes, value, and what is at that value.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import u3an, genlib


def main():
    targets = [a for a in sys.argv[1:] if not a.startswith('-')] or ['ultima', 'bootup', 'exodus']
    for t in targets:
        a = u3an.analyse(t)
        pad, lo, hi = genlib.RANGE[t]
        end = a.end
        img = a.img
        inlib = lambda x: pad <= x < hi
        targets_ = a.targets
        print('==== %s (end %04X, library %04X-%04X)' % (t, end, lo, hi))

        def what(v):
            if inlib(v):
                return 'library'
            if v in a.insn:
                return 'code entry' if v in targets_ else 'code'
            if 0x100 <= v < end:
                k = a.kind[v]
                return {0: 'data', 2: 'mid-insn', 3: 'table'}.get(k, '?')
            return 'past end' if v >= end else 'psp'
        print('-- immediates')
        for pc in sorted(a.insn):
            if inlib(pc):
                continue
            ins = a.insn[pc]
            if u3an.is_branch(ins) or ins.imm_size != 2:
                continue
            for op in u3an.operands(ins):
                if op.type == 'imm' and 0x100 <= op.imm < end + 0x4000:
                    print('  %04X  %-28s %04X  %s' % (pc, ins.mnemonic + ' ' + ins.op_str, op.imm, what(op.imm)))
        print('-- prefixed or past-end memory operands')
        for pc in sorted(a.insn):
            if inlib(pc):
                continue
            ins = a.insn[pc]
            for op in u3an.operands(ins):
                if op.type == 'mem' and op.disp_size == 2:
                    seg = u3an.prefix_seg(ins)
                    if (seg and 0x100 <= op.disp < end + 0x4000) or (not seg and op.seg == 'ds' and op.disp >= end):
                        print('  %04X  %-28s %04X  %s' % (pc, ins.mnemonic + ' ' + ins.op_str, op.disp, what(op.disp)))
        print('-- data words that hit a code entry')
        for p in range(0x100, end - 1):
            if inlib(p) or a.kind[p] or a.kind[p + 1]:
                continue
            v = img[p] | img[p + 1] << 8
            if v in targets_ and v in a.insn:
                print('  %04X  dw %04X  %s' % (p, v, what(v)))


if __name__ == '__main__':
    main()
